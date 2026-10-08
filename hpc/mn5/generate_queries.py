"""
Bulk chat completions with vLLM on MareNostrum 5, for `rsetl synthetic-queries`.

Reads the requests file written by `rsetl synthetic-queries export` -- one JSON
object per line with a stable `id`, chat `messages`, and optionally a
`json_schema` the answer must follow -- and appends one line per request to the
results file: the request's fields minus `messages`/`json_schema`, plus
`completion`, `model` and `attempts` (or `error`, with the raw output kept for
debugging).

The script knows nothing about software records. The prompt is built, and the
completion validated in depth, by the pipeline, so both live in one place and are
shared with the online Gepeto path. What is checked here is only what can be
retried cheaply while the engine is up: that an answer requested as JSON parses.

Designed for bulk throughput and recoverability:

- one engine per job; prompts go to vLLM in large chunks and it schedules them
  (chunks exist only as checkpoints);
- results are appended and flushed chunk by chunk; ids already answered are
  skipped, so a job killed by the Slurm time limit resumes when resubmitted;
- `--num-shards/--shard-index` split the input by id, so replicas (e.g. two TP=2
  engines on one node) or a Slurm array each write their own part file;
- sampling is seeded per record and attempt, so an answer does not depend on how
  requests were batched;
- a manifest records model, versions, sampling, prompt version and job id.

Standalone on purpose: it imports nothing from the pipeline, only vLLM. Compute
nodes are offline -- the model must already be on /gpfs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Iterator, List, Optional, Tuple

logger = logging.getLogger("mn5-queries")

# A request that cannot fit the context is recorded as failed, not retried.
PROMPT_TOO_LONG = "prompt_too_long"
INVALID_JSON = "invalid_json"


# --------------------------------------------------------------------------- I/O


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    # A job killed mid-write can leave a truncated last line.
                    logger.warning("Skipping unparseable line in %s", path)


def done_ids(results_path: Path) -> set[str]:
    """Ids already answered successfully; failed ones are retried on resubmission."""
    if not results_path.exists():
        return set()
    return {
        str(row["id"])
        for row in read_jsonl(results_path)
        if "id" in row and not row.get("error")
    }


def in_shard(request_id: str, num_shards: int, shard_index: int) -> bool:
    digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
    return int(digest, 16) % num_shards == shard_index


def pending_requests(
    requests_path: Path, results_path: Path, num_shards: int = 1, shard_index: int = 0
) -> List[dict]:
    finished = done_ids(results_path)
    return [
        r
        for r in read_jsonl(requests_path)
        if str(r["id"]) not in finished
        and in_shard(str(r["id"]), num_shards, shard_index)
    ]


def append_rows(results_path: Path, rows: Iterable[dict]) -> None:
    with results_path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def chunked(items: List[dict], size: int) -> Iterator[List[dict]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


# ------------------------------------------------------------------- validation


def request_seed(request_id: str, base_seed: int, attempt: int) -> int:
    """Per-record seed: reproducible whatever the batching, fresh on each retry."""
    digest = hashlib.sha256(f"{base_seed}:{request_id}:{attempt}".encode()).digest()
    return int.from_bytes(digest[:4], "little")


def is_valid(request: dict, completion: str) -> bool:
    """Only structural: a request that asked for JSON must get parseable JSON."""
    if not completion or not completion.strip():
        return False
    if "json_schema" not in request:
        return True
    text = completion.strip()
    if text.startswith("```"):
        text = text.strip("`").removeprefix("json").strip()
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return False
    return True


def result_row(
    request: dict,
    model: str,
    *,
    completion: Optional[str] = None,
    error: Optional[str] = None,
    attempts: int = 1,
) -> dict:
    row = {k: v for k, v in request.items() if k not in ("messages", "json_schema")}
    row["model"] = model
    row["attempts"] = attempts
    if error is not None:
        row["error"] = error
        if completion is not None:
            row["raw_output"] = completion
    else:
        row["completion"] = completion
    return row


# ----------------------------------------------------------------------- engine


class VllmEngine:
    """One vLLM engine for the whole job."""

    def __init__(self, args: argparse.Namespace) -> None:
        import vllm
        from vllm import LLM, SamplingParams

        self.vllm = vllm
        self.SamplingParams = SamplingParams
        self.args = args
        self.llm = LLM(
            model=args.model_path,
            tensor_parallel_size=args.tensor_parallel,
            dtype="bfloat16",
            trust_remote_code=True,
            max_model_len=args.max_model_len,
            gpu_memory_utilization=args.gpu_memory_utilization,
            seed=args.seed,
        )
        self.tokenizer = self.llm.get_tokenizer()
        self._structured = self._structured_factory() if args.structured else None
        if args.structured and self._structured is None:
            logger.warning(
                "This vLLM has no structured-output API this script knows; "
                "falling back to unconstrained decoding plus JSON validation."
            )

    def _structured_factory(self):
        """Structured decoding moved between vLLM versions; support both spellings."""
        try:
            from vllm.sampling_params import StructuredOutputsParams

            return lambda schema: {
                "structured_outputs": StructuredOutputsParams(json=schema)
            }
        except ImportError:
            pass
        try:
            from vllm.sampling_params import GuidedDecodingParams

            return lambda schema: {"guided_decoding": GuidedDecodingParams(json=schema)}
        except ImportError:
            return None

    def versions(self) -> dict:
        info = {"vllm": getattr(self.vllm, "__version__", None)}
        for name in ("torch", "transformers"):
            try:
                info[name] = __import__(name).__version__
            except Exception:
                info[name] = None
        return info

    def _chat_kwargs(self) -> dict:
        # Hybrid-reasoning chat templates (Qwen3.x) think unless told not to; the
        # pipeline only wants the JSON. Templates that ignore the flag are unaffected.
        return {"enable_thinking": self.args.enable_thinking}

    def prompt_tokens(self, messages: list) -> int:
        # Render then encode: with tokenize=True, newer transformers may return a
        # BatchEncoding (a dict), whose len() is not the token count.
        text = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, **self._chat_kwargs()
        )
        return len(self.tokenizer.encode(text, add_special_tokens=False))

    def generate(self, requests: List[dict], attempt: int) -> List[Tuple[str, int]]:
        params = []
        for request in requests:
            extra: dict = {}
            if self._structured is not None and "json_schema" in request:
                extra = self._structured(request["json_schema"])
            params.append(
                self.SamplingParams(
                    temperature=self.args.temperature,
                    top_p=self.args.top_p,
                    max_tokens=self.args.max_new_tokens,
                    seed=request_seed(str(request["id"]), self.args.seed, attempt),
                    **extra,
                )
            )
        outputs = self.llm.chat(
            [r["messages"] for r in requests],
            params,
            chat_template_kwargs=self._chat_kwargs(),
            use_tqdm=False,
        )
        return [(o.outputs[0].text, len(o.outputs[0].token_ids)) for o in outputs]


# -------------------------------------------------------------------------- run


def process_chunk(
    engine: Any, chunk: List[dict], model_name: str, max_retries: int, stats: dict
) -> List[dict]:
    """Generate one chunk, retrying invalid answers up to `max_retries` times."""
    rows: List[dict] = []
    budget = engine.args.max_model_len - engine.args.max_new_tokens
    todo = []
    for request in chunk:
        if engine.prompt_tokens(request["messages"]) > budget:
            rows.append(result_row(request, model_name, error=PROMPT_TOO_LONG))
        else:
            todo.append(request)

    last_output: dict = {}
    for attempt in range(max_retries + 1):
        if not todo:
            break
        answers = engine.generate(todo, attempt)
        retry = []
        for request, (text, n_tokens) in zip(todo, answers):
            stats["generated_tokens"] += n_tokens
            if is_valid(request, text):
                rows.append(
                    result_row(
                        request, model_name, completion=text, attempts=attempt + 1
                    )
                )
            else:
                last_output[request["id"]] = text
                retry.append(request)
        todo = retry
    for request in todo:
        rows.append(
            result_row(
                request,
                model_name,
                completion=last_output.get(request["id"]),
                error=INVALID_JSON,
                attempts=max_retries + 1,
            )
        )
    return rows


def shard_path(path: Path, args: argparse.Namespace) -> Path:
    if args.num_shards == 1:
        return path
    return path.with_name(f"{path.stem}.part-{args.shard_index:03d}{path.suffix}")


def run(args: argparse.Namespace, engine_factory=VllmEngine) -> int:
    requests_path = Path(args.input)
    results_path = shard_path(Path(args.output), args)
    results_path.parent.mkdir(parents=True, exist_ok=True)

    todo = pending_requests(
        requests_path, results_path, args.num_shards, args.shard_index
    )
    if args.limit:
        todo = todo[: args.limit]
    logger.info("%d requests pending for %s", len(todo), results_path.name)
    if not todo:
        return 0

    started = time.time()
    engine = engine_factory(args)
    startup = time.time() - started
    model_name = args.model_name or Path(args.model_path).name

    manifest = {
        "model": args.model_path,
        "model_name": model_name,
        **{f"{k}_version": v for k, v in engine.versions().items()},
        "tensor_parallel_size": args.tensor_parallel,
        "max_model_len": args.max_model_len,
        "max_new_tokens": args.max_new_tokens,
        "temperature": args.temperature,
        "top_p": args.top_p,
        "seed": args.seed,
        "structured_output": bool(getattr(engine, "_structured", None)),
        "enable_thinking": args.enable_thinking,
        "prompt_versions": sorted({str(r.get("prompt_version")) for r in todo}),
        "input": str(requests_path),
        "input_sha256": file_sha256(requests_path),
        "output": str(results_path),
        "shard": f"{args.shard_index}/{args.num_shards}",
        "slurm_job_id": os.environ.get("SLURM_JOB_ID"),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "engine_startup_s": round(startup, 1),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
    }
    manifest_path = results_path.with_suffix(".manifest.json")

    stats = {"generated_tokens": 0, "ok": 0, "failed": 0}
    generation_started = time.time()
    for chunk in chunked(todo, args.chunk_size):
        rows = process_chunk(engine, chunk, model_name, args.max_retries, stats)
        append_rows(results_path, rows)
        stats["ok"] += sum(1 for r in rows if "error" not in r)
        stats["failed"] += sum(1 for r in rows if "error" in r)
        elapsed = max(time.time() - generation_started, 1e-9)
        done = stats["ok"] + stats["failed"]
        logger.info(
            "%d/%d done, %d failed | %.2f records/s, %.0f gen tokens/s | ~%.0f min left",
            done,
            len(todo),
            stats["failed"],
            done / elapsed,
            stats["generated_tokens"] / elapsed,
            (len(todo) - done) / (done / elapsed) / 60,
        )

    elapsed = time.time() - generation_started
    manifest.update(
        {
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "generation_s": round(elapsed, 1),
            "records_ok": stats["ok"],
            "records_failed": stats["failed"],
            "generated_tokens": stats["generated_tokens"],
            "records_per_s": round((stats["ok"] + stats["failed"]) / elapsed, 3),
            "gen_tokens_per_s": round(stats["generated_tokens"] / elapsed, 1),
        }
    )
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    logger.info("Manifest: %s", manifest_path)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--input", "-i", required=True, help="Requests JSONL (export).")
    ap.add_argument(
        "--output",
        "-o",
        required=True,
        help="Results JSONL (appended; sharded runs add .part-NNN).",
    )
    ap.add_argument("--model-path", required=True, help="Local model directory.")
    ap.add_argument(
        "--model-name",
        default=None,
        help="Name recorded with each result (default: the model directory name).",
    )
    ap.add_argument("--tensor-parallel", type=int, default=4)
    ap.add_argument(
        "--max-model-len",
        type=int,
        default=4096,
        help="Context cap. Exported prompts are ~1-2k tokens; the model's 262k "
        "default only costs memory.",
    )
    ap.add_argument("--gpu-memory-utilization", type=float, default=0.90)
    ap.add_argument("--max-new-tokens", type=int, default=384)
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--top-p", type=float, default=0.9)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument(
        "--no-structured",
        dest="structured",
        action="store_false",
        help="Do not constrain decoding to the request's JSON schema.",
    )
    ap.add_argument(
        "--enable-thinking",
        action="store_true",
        help="Leave reasoning on for hybrid models (off: slower, and only the JSON "
        "is wanted).",
    )
    ap.add_argument(
        "--max-retries",
        type=int,
        default=2,
        help="In-job retries (fresh seed) for answers that are not valid JSON.",
    )
    ap.add_argument(
        "--chunk-size",
        type=int,
        default=1024,
        help="Requests handed to vLLM per call; also the checkpoint granularity.",
    )
    ap.add_argument("--num-shards", type=int, default=1)
    ap.add_argument("--shard-index", type=int, default=0)
    ap.add_argument("--limit", type=int, default=None, help="Only the first N pending.")
    return ap


def main(argv: list[str] | None = None, engine_factory=VllmEngine) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    args = build_parser().parse_args(argv)
    if not 0 <= args.shard_index < args.num_shards:
        raise SystemExit("--shard-index must be in [0, --num-shards)")
    return run(args, engine_factory)


if __name__ == "__main__":
    sys.exit(main())

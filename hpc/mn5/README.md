# Synthetic queries on MareNostrum 5 (vLLM)

Bulk generation of the synthetic search queries stored in `semantic_search`.
MN5 compute nodes cannot reach MongoDB (or the internet), so the pipeline hands
the job a file and takes a file back:

```
local:  rsetl synthetic-queries export  ->  data/semantic_search/query_requests.jsonl
MN5:    sbatch generate_queries.sbatch  ->  query_results[.part-NNN].jsonl + .manifest.json
local:  rsetl synthetic-queries import  <-  those result files
```

Division of labour:

- **The pipeline** (`src/application/services/semantic_search/synthetic_queries.py`)
  owns the software record -> prompt step (field selection, deterministic
  truncation of long descriptions, the prompt and its `PROMPT_VERSION`, the JSON
  schema of the answer), and the full validation on import: the JSON schema, 3-15
  words per query, no tool name, no duplicates, at most 6 queries. The online
  Gepeto path (`rsetl synthetic-queries generate`) goes through the same code.
  `export` produces prompt version 2 by default: the record plus the tool's
  GitHub README, read from the README cache (`data/semantic_search/readmes.jsonl`)
  and fetched through the github-metadata-api when missing (needs `GITHUB_TOKEN`).
  `--prompt-version 1` exports the record alone.
- **`generate_queries.py`** is a generic, resumable vLLM batch runner. It starts
  one engine per job and submits prompts in large chunks, constraining decoding to
  the exported JSON schema. Answers that still do not parse are retried in-job
  with a fresh seed. It writes results incrementally and records a manifest.

Tested environment (from the infrastructure smoke test): ACC node with 4x H100
64 GB, venv `/gpfs/home/bsc/bsc619075/envs/vllm` (vLLM 0.30.0, torch
2.13.0+cu130, transformers 5.17.0; no CUDA module or `nvcc` needed), and model
`/gpfs/projects/bsc23/models/Qwen3.6-27B` (51.75 GiB).

## 1. Export (local)

```sh
rsetl synthetic-queries export              # tools with no queries, or whose input changed
rsetl synthetic-queries export --limit 500  # a trial batch
rsetl synthetic-queries export --force      # everything (e.g. after changing model)
```

A README fetch takes ~7 s; the first v2 export of the 2026-10 corpus fetched
about 4k of the 8.8k eligible repositories (the rest were seeded from an earlier
crawl). Repositories with no README are cached too, as null; `--refetch-missing-readmes`
retries them (the client cannot tell "none" from a failed fetch), and
`--no-readme-fetch` uses the cache alone.

Export also stores tools too thin to prompt as `insufficient`, and removes the
documents of tools that no longer exist.

## 2. Copy to MN5 (transfer nodes)

```sh
WORK=/gpfs/scratch/bsc23/bsc619075/semantic_search
ssh bsc619075@transfer1.bsc.es "mkdir -p $WORK/logs"   # Slurm does not create the log dir
scp data/semantic_search/query_requests.jsonl \
    hpc/mn5/generate_queries.py hpc/mn5/generate_queries.sbatch \
    bsc619075@transfer1.bsc.es:$WORK/
```

## 3. Run (MN5)

Check the `#SBATCH --account/--qos` lines first. The default QoS is `acc_bscls`,
which is an assumption; use whatever `bsc23` has.

**Smoke-test the real prompts first** (debug queue, 500 records). The log shows
whether structured output is active, and the manifest records records/s and
generated tokens/s:

```sh
cd $WORK
LIMIT=500 sbatch --qos=acc_debug --time=00:30:00 generate_queries.sbatch
```

Then inspect a few results locally with import, which reports
generated/insufficient/failed counts, or read `query_results.jsonl` directly.
Fix the prompt in the pipeline and bump `PROMPT_VERSION` if needed.

**Benchmark the layout.** Tensor parallelism is not assumed to be optimal. Each
`REPLICAS` value splits the node's 4 GPUs into independent engines of `4/REPLICAS`
GPUs each:

```sh
LIMIT=2000 REPLICAS=1 RESULTS=$WORK/bench_tp4.jsonl sbatch --qos=acc_debug --time=00:30:00 generate_queries.sbatch
LIMIT=1000 REPLICAS=2 RESULTS=$WORK/bench_tp2.jsonl sbatch --qos=acc_debug --time=00:30:00 generate_queries.sbatch
LIMIT=500  REPLICAS=4 RESULTS=$WORK/bench_tp1.jsonl sbatch --qos=acc_debug --time=00:30:00 generate_queries.sbatch
```

Compare `records_per_s` summed over the manifests of one job. TP=1 holds the
51.75 GiB of weights on one 64 GB GPU with little KV-cache room; if it fails to
start, lower `MAX_MODEL_LEN`. `CHUNK_SIZE` (default 1024) is how many requests
vLLM gets per call, and also how much work a time-out can lose.

**Full run**, with the winning layout:

```sh
REPLICAS=2 sbatch generate_queries.sbatch
```

It is resumable: requests already answered are skipped, so after a time-out you
just resubmit the same command. Rows recorded with an `error` are retried on
resubmission. With `REPLICAS>1`, each engine writes its own
`query_results.part-NNN.jsonl`; a Slurm array would work the same way with
`--num-shards/--shard-index`.

Knobs (environment variables of the sbatch): `MODEL_DIR`, `REPLICAS`,
`MAX_MODEL_LEN` (4096; exported prompts are about 1-2k tokens), `CHUNK_SIZE`,
`TEMPERATURE` (0.7), `TOP_P` (0.9), `SEED`, `LIMIT`. See
`python generate_queries.py -h` for the rest, e.g. `--no-structured` and
`--enable-thinking` (off by default, because only the JSON is wanted).

The vLLM/torch.compile cache is kept on GPFS
(`/gpfs/scratch/bsc23/vllm_cache/$USER`), so compilation and CUDA-graph capture
(about 3.5 of the 5 minutes of startup) are not redone every job. Keep one cache
per environment.

## 4. Import (local)

```sh
scp 'bsc619075@transfer1.bsc.es:/gpfs/scratch/bsc23/bsc619075/semantic_search/results.jsonl' data/semantic_search/
rsetl synthetic-queries import -i data/semantic_search/results.jsonl
```

Import recomputes each tool's `input_hash` with the README *cache* (it fetches
nothing), so import against the same cache the export used; a README that changed
in between makes that tool `stale`.

Import skips results whose tool changed or disappeared since the export
(`stale`); the next export picks those tools up again. Importing the same files
twice is harmless. Answers that fail validation are not stored, so they are
exported again next time.

# Running the pipeline on a small test set

A full `rsetl run` reads ~235k raw documents from `alambiqueDev` and writes to
the live `*Dev` collections. That is too slow for iterating on the pipeline and
would pollute production data. This directory lets you run the **whole pipeline,
every stage**, against a few thousand sampled documents in isolated `*_test`
collections.

Two pieces:

1. A **sampled raw collection** (`alambique_test`) built from `alambiqueDev`.
2. A set of **`_test` output collections** the pipeline writes to, set via
   environment variables — no code changes, because every collection name in
   `PipelineConfig` is env-overridable and `rsetl run` copies the environment
   into each stage subprocess.

## What is / isn't redirected

The pipeline both **reads reference collections** and **writes output
collections**. Only the write targets are redirected; the read-only references
stay pointed at real data, or the pipeline loses inputs it needs.

| Collection | Env var | Test run uses | Why |
| --- | --- | --- | --- |
| Raw source | `ALAMBIQUE` | `alambique_test` | Sampled subset (see below) |
| License lookup | `LICENSES_MAPPING` | **real** (`licensesMapping`) | Read-only SPDX lookup table |
| Publications | `PUBLICATIONS_COLLECTION` | **real** (`publicationsMetadataDev`) | Read during disambiguation scoring, FAIR scores, stats trends; populated by the separate `enrich-publications` command |
| pretools | `PRETOOLS` | `pretools_test` | Written by transformation |
| tools (live) | `MONGO_TOOLS_COLL` | `tools_test` | Promoted by merge |
| tools (staging) | `MONGO_TOOLS_STAGING_COLL` | `tools_test_next` | Merge builds here first |
| tools (archive) | `MONGO_TOOLS_ARCHIVE_PREFIX` | `tools_test_archive_` | Archived pre-promotion |
| computations | `COMPUTATIONS` | `computations_test` | FAIR scores |
| similarities | `SIMILARITIES` | `similarities_test` | Similarity stage |

`finalize_run` handles a missing live `tools_test` on the first run (it only
archives when the live collection exists), so no manual setup of the test
collections is needed — Mongo creates them on first write.

## The sample set

`sample_alambique.py` draws a **random per-source sample** from `alambiqueDev`
into `alambique_test`. Default caps (edit `CAPS` in the script to resize):

| source | docs | | source | docs |
| --- | --- | --- | --- | --- |
| biotools | 1500 | | toolshed | 300 |
| bioconda_recipes | 600 | | sourceforge | 200 |
| github | 500 | | galaxy | 200 |
| bioconductor | 400 | | opeb_metrics | 800 |
| galaxy_metadata | 400 | | **total** | **~4900** |

`opeb_metrics` are metrics that *attach* to tools rather than create them (and
are 113k of the 235k total), so only a modest slice is included.

**Caveat:** because the sample is random per source, cross-source groups are
sparser than in production — related entries may not all land in the sample. The
set is meant to exercise every stage and check speed/correctness, **not** to
judge grouping/merge quality. Don't read much into the merge counts from a
sample run.

## Commands

### 1. Build the sample collection (once, or to resize)

```bash
python scripts/testing/sample_alambique.py
# or a different destination:
python scripts/testing/sample_alambique.py --dst alambique_test
```

### 2. Launch the test run

```bash
export ALAMBIQUE=alambique_test
export PRETOOLS=pretools_test \
       MONGO_TOOLS_COLL=tools_test \
       MONGO_TOOLS_STAGING_COLL=tools_test_next \
       MONGO_TOOLS_ARCHIVE_PREFIX=tools_test_archive_ \
       COMPUTATIONS=computations_test \
       SIMILARITIES=similarities_test

rsetl check-env                              # verify env + connectivity first
rsetl run --dry-run-disambiguation --no-human-updates --tag test-sample
```

`--dry-run-disambiguation` is important: without it, the disambiguation stage
opens **real GitHub issues** for ambiguous cases. `--tag test-sample` labels the
run directory under `data/integration/runs/` so it is easy to spot.

`--no-human-updates` is recommended for a test run: the `human_updates` stage runs
`git pull` and applies curator decisions from git annotations — a test set has
none, and you don't want it touching the working tree. Skipping it is correct for
a test. (Historically dry-run also *crashed* this stage; that bug is fixed — see
"Fixes this depends on" below — so the flag is now a convenience, not a
workaround.)

To run a subset of stages while iterating, add `--only <stage>`,
`--from-stage <stage>`, or `--until <stage>`.

## What a successful run produces

With the sample set, a clean end-to-end run lands roughly:

| Collection | Result | Written by |
| --- | --- | --- |
| `tools_test` | ~3,900 tool documents | merge → `finalize_run` promotes `tools_test_next` |
| `computations_test` | one FAIR computation per tool | fairsoft (`createdFrom = [str(tool._id)]`) |
| `similarities_test` | pairwise similarities | similarity stage |

Merge prints an identity summary. On the **first** run into an empty `tools_test`
it reads `preserved 0 / new ~3900 / retired 0 / contested 0`, and finalize logs
`Promoted tools_test_next -> tools_test` with **no archive** (there was no live
collection to archive). A **second** run archives the previous `tools_test` as
`tools_test_archive_<run_id>` before promoting, keeping the newest
`TOOLS_ARCHIVE_KEEP` (default 2). `contested` is the number to watch on real
runs; on a random sample it is not meaningful (groups are fragmented).

## Faster iteration: reuse pretools, re-run downstream only

Transformation is the slow stage (~20 min: per-entry publication processing).
Once `pretools_test` is populated, you can iterate on everything after it without
re-running it, using `--resume-run` against the existing run directory:

```bash
# same exports as above (ALAMBIQUE + the _test collections), then:
rsetl run --resume-run <run_id_or_dir> --from-stage disambiguation \
          --dry-run-disambiguation --no-human-updates
```

Two gotchas when resuming into `--from-stage disambiguation`:

- Disambiguation *appends* to its output file (it loads existing keys and skips
  them). To regenerate cleanly, empty the file first:
  `: > data/integration/runs/<run_id>/disambiguation.<run_id>.jsonl`
- The pre-flight check (`pipeline_full.py`) requires that disambiguation output
  file to *exist* whenever `merge` is in range, even though disambiguation is the
  stage that produces it. Emptying the file (rather than deleting it) satisfies
  the check.

## Fixes this depends on

Two branch regressions blocked a fresh run from reaching merge; both are fixed on
this branch, and reproduction assumes those fixes are present:

- **Publication ids** (`infrastructure/db/mongo/publications_repository.py`): the
  `find_by_*` lookups must return the raw doc with its `ObjectId` `_id` (as on
  `main`), not a stringified one. Transformation stores that id in
  `pretools.data.publication`, which the merge model requires to be `ObjectId`.
- **Dry-run disambiguation output** (`.../disambiguation/disambiguator.py`): in
  dry-run, manual-review candidates must **not** be written to the disambiguation
  JSONL (they are flat diagnostic dicts that corrupt the loader). The file write
  now applies the same guard as the in-memory update.

## Troubleshooting

- **`localhost:27018 Operation not permitted`** during `check-env`/run: the
  command sandbox is blocking Mongo. Re-run with the sandbox disabled (or manage
  it via `/sandbox`).
- **`404 No endpoints found for mistralai/mixtral-8x7b-instruct`** during
  disambiguation: that OpenRouter model is retired, so LLM pair-scoring silently
  no-ops. Update the model id in the disambiguation config. Non-fatal.
- **GitLab `401`** in `check-env`: `GITLAB_TOKEN` is stale. Non-fatal — only
  GitLab link-enrichment during disambiguation is affected.
- **`pretools_test` keeps growing after you drop it / re-run**: an orphaned
  `transformation --sources all` from a *killed* earlier run may still be writing.
  Killing `rsetl run` does not always kill its stage subprocess. Check with
  `pgrep -fl "transformation --sources"` and kill the stray PID.

## Cleanup

The `_test` collections are safe to drop between runs:

```javascript
// in mongosh
["pretools_test","tools_test","tools_test_next","computations_test","similarities_test"]
  .forEach(c => db.getCollection(c).drop());
db.getCollectionNames().filter(n => n.startsWith("tools_test_archive_"))
  .forEach(c => db.getCollection(c).drop());
// alambique_test can be kept and reused, or dropped and rebuilt from the script
```

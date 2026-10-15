#!/bin/bash
# Synthetic search queries with vLLM on one MN5 ACC node (4x H100).
#
#   sbatch generate_queries.sbatch                                # 1 engine, TP=4
#   REPLICAS=2 sbatch generate_queries.sbatch                     # 2 engines, TP=2 each
#   LIMIT=2000 sbatch --qos=acc_debug --time=00:30:00 generate_queries.sbatch   # benchmark
#
# Resumable: after a time-out, resubmit the same command and it continues.
# MN5 requires 20 CPUs per requested GPU (80 for 4).
#SBATCH --job-name=rsetl_queries
#SBATCH --account=bsc23
#SBATCH --qos=acc_bscls
#SBATCH --time=12:00:00
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=80
#SBATCH --gres=gpu:4
#SBATCH --output=/gpfs/scratch/bsc23/bsc619075/semantic_search/logs/%x_%j.out
#SBATCH --error=/gpfs/scratch/bsc23/bsc619075/semantic_search/logs/%x_%j.err

set -euo pipefail

# --- Paths (override from the environment) -----------------------------------
VENV=${VENV:-/gpfs/home/bsc/bsc619075/envs/vllm}
MODEL_DIR=${MODEL_DIR:-/gpfs/projects/bsc23/models/Qwen3.6-27B}
WORK_DIR=${WORK_DIR:-/gpfs/scratch/bsc23/bsc619075/semantic_search}
SCRIPT=${SCRIPT:-$WORK_DIR/generate_queries.py}
REQUESTS=${REQUESTS:-$WORK_DIR/query_requests.jsonl}
RESULTS=${RESULTS:-$WORK_DIR/query_results.jsonl}

# --- Engine layout -------------------------------------------------------------
# REPLICAS=1 -> one TP=4 engine; REPLICAS=2 -> two TP=2 engines on GPUs 0,1 / 2,3,
# each writing its own shard (query_results.part-00N.jsonl). Benchmark both.
REPLICAS=${REPLICAS:-1}
TP=$((4 / REPLICAS))
MAX_MODEL_LEN=${MAX_MODEL_LEN:-4096}
CHUNK_SIZE=${CHUNK_SIZE:-1024}
TEMPERATURE=${TEMPERATURE:-0.7}
TOP_P=${TOP_P:-0.9}
SEED=${SEED:-0}
LIMIT_ARG=${LIMIT:+--limit $LIMIT}

export SRUN_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK}
# 80 CPUs are required for 4 GPUs, but torch does not need 80 OpenMP threads.
export OMP_NUM_THREADS=$((20 / REPLICAS > 0 ? 20 / REPLICAS : 1))

export PYTHONNOUSERSITE=1
unset PYTHONPATH
source "$VENV/bin/activate"

# Node-local temp and HF caches; persistent vLLM/torch.compile cache on GPFS so
# compilation and CUDA-graph work is not redone every job (keep one cache per
# environment -- do not share it with a different vLLM/torch install).
export TMPDIR=/scratch/tmp/${SLURM_JOB_ID}
mkdir -p "$TMPDIR"
export HF_HOME="$TMPDIR/hf_home"
export XDG_CACHE_HOME=${XDG_CACHE_HOME:-/gpfs/scratch/bsc23/vllm_cache/${USER}}
mkdir -p "$XDG_CACHE_HOME" "$WORK_DIR/logs"

# Compute nodes are offline.
export HF_HUB_OFFLINE=1
export TRANSFORMERS_OFFLINE=1
export HF_HUB_DISABLE_TELEMETRY=1

echo "=== $SLURMD_NODENAME | job $SLURM_JOB_ID | replicas=$REPLICAS tp=$TP ==="
nvidia-smi --query-gpu=index,name,memory.total --format=csv
python -c "import vllm, torch, transformers; print('vLLM', vllm.__version__, '| torch', torch.__version__, '| transformers', transformers.__version__)"

cd "$WORK_DIR"

limit_args=()
if [[ -n "${LIMIT:-}" ]]; then
    limit_args=(--limit "$LIMIT")
fi

pids=()

for ((i = 0; i < REPLICAS; i++)); do
    first=$((i * TP))

    devices=$first
    for ((g = first + 1; g < first + TP; g++)); do
        devices+=",$g"
    done

    shard_args=()
    if ((REPLICAS > 1)); then
        shard_args=(--num-shards "$REPLICAS" --shard-index "$i")
    fi

    CUDA_VISIBLE_DEVICES="$devices" \
    srun --exclusive \
        --ntasks=1 \
        --cpus-per-task=$((80 / REPLICAS)) \
        python "$SCRIPT" \
            --input "$REQUESTS" \
            --output "$RESULTS" \
            --model-path "$MODEL_DIR" \
            --tensor-parallel "$TP" \
            --max-model-len "$MAX_MODEL_LEN" \
            --chunk-size "$CHUNK_SIZE" \
            --temperature "$TEMPERATURE" \
            --top-p "$TOP_P" \
            --seed "$SEED" \
            "${shard_args[@]}" \
            "${limit_args[@]}" \
        > "$WORK_DIR/logs/replica_${SLURM_JOB_ID}_${i}.log" 2>&1 &

    pids+=("$!")
done

# The replicas run in the background: wait for them, or the batch script ends
# here and Slurm kills them with it. Fail the job if any replica failed.
status=0
for i in "${!pids[@]}"; do
    if ! wait "${pids[$i]}"; then
        status=1
        echo "Replica $i failed; see $WORK_DIR/logs/replica_${SLURM_JOB_ID}_${i}.log" >&2
    fi
done

echo "=== finished (status $status) ==="
exit "$status"

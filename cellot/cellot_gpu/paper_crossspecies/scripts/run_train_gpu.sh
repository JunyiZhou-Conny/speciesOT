#!/bin/bash
# GPU remainder training for paper cross-species LPS replication (250k iters each).
# Skips models with cache/status=done (e.g. rat scGen finished on CPU).
# Run via paper_crossspecies/sbatch/run_full_pipeline_gpu.sbatch
set -euo pipefail

source "$(dirname "$0")/../env.sh"
cd "${CELLOT_GPU}"
export PYTHONPATH=.

DEVICE="${PAPER_CROSSSPECIES_DEVICE:-cuda}"

module load python
mamba activate "${CELLOT_ENV}"

train_one() {
  local tag="$1"
  local holdout="$2"
  local scgen_dir="./results/${tag}/scgen"
  local impact_dir="./results/${tag}/impact_cellot"

  if [[ -f "${scgen_dir}/cache/status" ]] && [[ "$(cat "${scgen_dir}/cache/status")" == "done" ]]; then
    echo "=== skip scgen ${tag} (status=done) ==="
  else
    echo "=== Training scgen ${tag} on ${DEVICE} ==="
    python ./scripts/train.py \
      --outdir "${scgen_dir}" \
      --config "${scgen_dir}/config.yaml" \
      --config.device "${DEVICE}"
  fi

  if [[ -f "${impact_dir}/cache/status" ]] && [[ "$(cat "${impact_dir}/cache/status")" == "done" ]]; then
    echo "=== skip impact_cellot ${tag} (status=done) ==="
  else
    echo "=== Training impact_cellot ${tag} on ${DEVICE} ==="
    python ./scripts/train.py \
      --outdir "${impact_dir}" \
      --config "${impact_dir}/config.yaml" \
      --config.device "${DEVICE}"
  fi
}

train_one "paper_crossspecies_rat_ood" rat
train_one "paper_crossspecies_mouse_ood" mouse

echo "=== Paper cross-species GPU training complete ==="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
bash "${SCRIPT_DIR}/run_eval.sh"

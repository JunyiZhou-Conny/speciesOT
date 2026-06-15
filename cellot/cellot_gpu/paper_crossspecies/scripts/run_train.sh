#!/bin/bash
# Sequential paper replication training (250k iters each).
set -euo pipefail

source "$(dirname "$0")/../env.sh"
cd "${CELLOT_GPU}"
export PYTHONPATH=.

module load python
mamba activate CellOT

train_one() {
  local tag="$1"
  local holdout="$2"
  local scgen_dir="./results/${tag}/scgen"
  local impact_dir="./results/${tag}/impact_cellot"

  if [[ -f "${scgen_dir}/cache/status" ]] && [[ "$(cat "${scgen_dir}/cache/status")" == "done" ]]; then
    echo "=== skip scgen ${tag} (status=done) ==="
  else
    echo "=== Training scgen ${tag} ==="
    python ./scripts/train.py \
      --outdir "${scgen_dir}" \
      --config "${scgen_dir}/config.yaml" \
      --config.device cpu
  fi

  if [[ -f "${impact_dir}/cache/status" ]] && [[ "$(cat "${impact_dir}/cache/status")" == "done" ]]; then
    echo "=== skip impact_cellot ${tag} (status=done) ==="
  else
    echo "=== Training impact_cellot ${tag} ==="
    python ./scripts/train.py \
      --outdir "${impact_dir}" \
      --config "${impact_dir}/config.yaml" \
      --config.device cpu
  fi
}

train_one "paper_crossspecies_rat_ood" rat
train_one "paper_crossspecies_mouse_ood" mouse

echo "=== Paper cross-species training complete ==="

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
bash "${SCRIPT_DIR}/run_eval.sh"

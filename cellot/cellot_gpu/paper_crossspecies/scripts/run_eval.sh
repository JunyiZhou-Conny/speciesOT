#!/bin/bash
# Paper-faithful eval + extended_metrics for cross-species LPS replication.
set -euo pipefail

source "$(dirname "$0")/../env.sh"
cd "${CELLOT_GPU}"
export PYTHONPATH=.

module load python
mamba activate "${CELLOT_ENV}"

run_evals() {
  local tag="$1"
  local model="$2"
  local emb=""
  if [[ "$model" == "impact_cellot" ]]; then
    emb="--embedding ae"
  fi
  for setting in ood iid; do
    echo "=== eval ${tag}/${model} ${setting} ==="
    python ./scripts/evaluate.py \
      --outdir "./results/${tag}/${model}" \
      --setting "$setting" \
      --where data_space \
      $emb \
      --n_markers 50 \
      --n_cells 500,1000 \
      --n_reps 10 \
      --evalprefix "evals_${setting}_data_space_paper"
  done
  echo "=== extended_metrics ${tag}/${model} ood ==="
  python ./scripts/extended_metrics.py \
    --outdir "./results/${tag}/${model}" \
    --setting ood \
    --where data_space \
    $emb \
    --evalprefix evals_ood_data_space_paper \
    --n_cells 500,1000 \
    --n_markers 50
}

for tag in paper_crossspecies_rat_ood paper_crossspecies_mouse_ood; do
  for model in scgen impact_cellot; do
    run_evals "$tag" "$model"
  done
done

echo "=== Paper cross-species eval complete ==="

# Hub sidecars (optional; discovers runs under results/paper_crossspecies_*)
if [[ -x "${SPECIESOT_ROOT}/hub" ]]; then
  for tag in paper_crossspecies_rat_ood paper_crossspecies_mouse_ood; do
  for model in scgen impact_cellot; do
    run_id="gpu/${tag}/${model}"
    if [[ -d "./results/${tag}/${model}" ]]; then
      echo "=== hub metrics ${run_id} ==="
      (cd "${SPECIESOT_ROOT}" && ./hub metrics "${run_id}" 2>/dev/null) || true
    fi
  done
  done
fi

#!/bin/bash
#SBATCH -J uotA_lps
#SBATCH -p gpu_requeue
#SBATCH --gres=gpu:1
#SBATCH --constraint=h100|h200
#SBATCH -t 24:00:00
#SBATCH -c 4
#SBATCH --mem=48G
#SBATCH -o /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/scgen-cellot-unbalanced/results/lps_rat/logs/%x_%A_%a.out
#SBATCH -e /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/scgen-cellot-unbalanced/results/lps_rat/logs/%x_%A_%a.err
#SBATCH --array=0-3

# Option A LPS rat: same CellOT knobs as Bunne IMPACT; only sampling weights differ.
# Array:
#   0 = balanced parity (stock DataLoader, no reweight)
#   1 = louvain_match α=0.25
#   2 = louvain_match α=0.5
#   3 = louvain_match α=1.0

set -euo pipefail

ROOT=/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/scgen-cellot-unbalanced
CELLOT_GPU=/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu
OUT=$ROOT/results/lps_rat
CFG=$ROOT/configs/option_a/lps_rat_balanced.yaml

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate CellOT_gpu
export PYTHONPATH=$CELLOT_GPU:$ROOT
cd "$ROOT"

NAMES=(balanced_parity option_a_louvain_alpha0.25 option_a_louvain_alpha0.5 option_a_louvain_alpha1)
WEIGHTS=(
  ""
  "$OUT/weights/weights_louvain_match_alpha0.25.npz"
  "$OUT/weights/weights_louvain_match_alpha0.5.npz"
  "$OUT/weights/weights_louvain_match_alpha1.npz"
)

NAME=${NAMES[$SLURM_ARRAY_TASK_ID]}
W=${WEIGHTS[$SLURM_ARRAY_TASK_ID]}
OUTDIR=$OUT/$NAME
mkdir -p "$OUTDIR" "$OUT/logs"

echo "[$(date)] host=$(hostname) task=$SLURM_ARRAY_TASK_ID name=$NAME cuda=${CUDA_VISIBLE_DEVICES:-}"
nvidia-smi -L || true

ARGS=(--config "$CFG" --outdir "$OUTDIR" --seed 0)
if [[ -n "$W" ]]; then
  ARGS+=(--weights "$W")
fi

python scripts/train_option_a.py "${ARGS[@]}"

# Eval after train (decoded north-star + uot sidecar)
EVAL_ARGS=(--outdir "$OUTDIR" --run-eval)
if [[ -n "$W" ]]; then
  EVAL_ARGS+=(--weights "$W")
fi
python scripts/eval_option_a.py "${EVAL_ARGS[@]}"

echo "[$(date)] done $NAME"

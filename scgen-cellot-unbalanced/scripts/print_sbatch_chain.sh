#!/usr/bin/env bash
# Print (do NOT submit) the Option-A LPS rat chain.
# Human / agent copies these after review. Hub never auto-submits.

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REPO="$(cd "$ROOT/.." && pwd)"
CELLOT_GPU="$REPO/cellot/cellot_gpu"
OUT="$ROOT/results/lps_rat"
ENV_ACTIVATE='source "$(conda info --base)/etc/profile.d/conda.sh" && conda activate CellOT_gpu'

cat <<EOF
# =============================================================================
# Option A — LPS rat OOD (freeze AE at paper_crossspecies_rat_ood/scgen)
# Work root: $ROOT
# Submit manually after review. Do not start Option C.
# =============================================================================

# --- 0) Estimate weight artifacts (CPU, minutes) ---
cd $ROOT
$ENV_ACTIVATE
export PYTHONPATH=$CELLOT_GPU:\$PWD

python scripts/estimate_weights.py --config configs/option_a/lps_rat_balanced.yaml \\
  --method uniform --alpha 0.0 --outdir $OUT/weights

python scripts/estimate_weights.py --config configs/option_a/lps_rat_balanced.yaml \\
  --method louvain_match --alpha 0.0 --outdir $OUT/weights

python scripts/estimate_weights.py --config configs/option_a/lps_rat_balanced.yaml \\
  --method louvain_match --alpha 0.25 --outdir $OUT/weights

python scripts/estimate_weights.py --config configs/option_a/lps_rat_balanced.yaml \\
  --method louvain_match --alpha 0.5 --outdir $OUT/weights

python scripts/estimate_weights.py --config configs/option_a/lps_rat_balanced.yaml \\
  --method louvain_match --alpha 1.0 --outdir $OUT/weights

python scripts/estimate_weights.py --config configs/option_a/lps_rat_balanced.yaml \\
  --method density_ratio --alpha 1.0 --outdir $OUT/weights --device cpu

# --- 1) Example sbatch: parity (uniform α=0) ---
# sbatch <<'SBATCH'
# #!/bin/bash
# #SBATCH -J uotA_parity
# #SBATCH -p gpu_requeue
# #SBATCH --gres=gpu:1
# #SBATCH --constraint=h100|h200
# #SBATCH -t 24:00:00
# #SBATCH -c 4
# #SBATCH --mem=32G
# #SBATCH -o $OUT/logs/parity_%j.out
# #SBATCH -e $OUT/logs/parity_%j.err
# $ENV_ACTIVATE
# cd $ROOT
# export PYTHONPATH=$CELLOT_GPU:\$PWD
# python scripts/train_option_a.py \\
#   --config configs/option_a/lps_rat_balanced.yaml \\
#   --outdir $OUT/balanced_parity \\
#   --weights $OUT/weights/weights_uniform_alpha0.npz
# python scripts/eval_option_a.py --outdir $OUT/balanced_parity \\
#   --weights $OUT/weights/weights_uniform_alpha0.npz --run-eval
# SBATCH

# --- 2) Example sbatch: louvain_match α∈{0.25,0.5,1.0} ---
# for A in 0.25 0.5 1.0; do
#   sbatch ... train_option_a.py --outdir $OUT/option_a_louvain_alpha\${A} \\
#     --weights $OUT/weights/weights_louvain_match_alpha\${A}.npz
# done

# Parity target (existing hub run, no retrain needed for baseline column):
#   ./hub show gpu/paper_crossspecies_rat_ood/impact_cellot
#   fgc_decoded @ ncells=80  ≈ 0.076
#   fgc_decoded @ ncells=500 ≈ 0.092
# Tolerance for uniform retrain: |Δ| ≤ 0.03 on fgc_decoded @ 80
EOF

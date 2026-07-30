#!/usr/bin/env bash
# SLURM sketch for Plan C VAE train. PRINT / copy-paste — do not auto-submit from hub.
# Fence: outputs only under atlas-paper-vae/results/atlas_paper_vae_*
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/atlas-paper-vae/results/atlas_paper_vae_m2_v08_ood"
LOGDIR="$ROOT/atlas-paper-vae/logs"
mkdir -p "$OUT" "$LOGDIR"

cat <<EOF
# --- copy-paste submit (after reviewing) ---
sbatch <<'SBATCH'
#!/bin/bash
#SBATCH -J atlas_paper_vae_m2
#SBATCH -p shared
#SBATCH -c 8
#SBATCH --mem=32G
#SBATCH -t 12:00:00
#SBATCH -o ${LOGDIR}/train_%j.out
#SBATCH -e ${LOGDIR}/train_%j.err
# Optional GPU (if tensorflow-gpu in scgen_tf1):
# #SBATCH -p gpu_requeue
# #SBATCH --gres=gpu:1
# #SBATCH --constraint=h100|h200

set -euo pipefail
source ~/.bashrc
conda activate scgen_tf1
export PYTHONUNBUFFERED=1
export PYTHONPATH="${ROOT}/scgen-cellot-ablation/scgen-reproducibility/code:\${PYTHONPATH:-}"
cd "${ROOT}"
python atlas-paper-vae/scripts/01_train_vae.py --go
python atlas-paper-vae/scripts/02_eval_metrics.py --go
SBATCH
# --- end ---
EOF

echo
echo "Result root (fence): $OUT"
echo "Never write: cellot/cellot_gpu/results/hvg_pearson_residuals_*_v08_ood/scgen/"

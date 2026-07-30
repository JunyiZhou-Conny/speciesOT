#!/bin/bash
# Plan C: TF VAEArith train + honest-metrics eval on M1 v08 OOD.
# Fence: writes only under atlas-paper-vae/results/atlas_paper_vae_m1_v08_ood/
#SBATCH -J atlas_paper_vae_m1
#SBATCH -p shared
#SBATCH -c 8
#SBATCH --mem=32G
#SBATCH -t 24:00:00
#SBATCH -o /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/atlas-paper-vae/logs/train_m1_%j.out
#SBATCH -e /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/atlas-paper-vae/logs/train_m1_%j.err

set -eo pipefail
ROOT="/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT"
CFG="${ROOT}/atlas-paper-vae/configs/m1_v08.yaml"
cd "$ROOT"
mkdir -p atlas-paper-vae/logs atlas-paper-vae/results/atlas_paper_vae_m1_v08_ood

source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate scgen_tf1
export PYTHONUNBUFFERED=1
export PYTHONPATH="${ROOT}/scgen-cellot-ablation/scgen-reproducibility/code:${PYTHONPATH:-}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
set -u

echo "=== atlas paper VAE M1 job ${SLURM_JOB_ID:-local} started $(date) ==="
echo "config=$CFG"
python -c "import tensorflow as tf; print('TF', tf.__version__)"

python atlas-paper-vae/scripts/01_train_vae.py --config "$CFG" --go
python atlas-paper-vae/scripts/02_eval_metrics.py --config "$CFG" --go

echo "=== done $(date) ==="
ls -la atlas-paper-vae/results/atlas_paper_vae_m1_v08_ood/
test -f atlas-paper-vae/results/atlas_paper_vae_m1_v08_ood/metrics.json
echo "metrics.json present"

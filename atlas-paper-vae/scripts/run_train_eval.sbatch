#!/bin/bash
# Plan C Phase 2: TF VAEArith train + honest-metrics eval on M2 v08 OOD.
# Fence: writes only under atlas-paper-vae/results/atlas_paper_vae_m2_v08_ood/
#SBATCH -J atlas_paper_vae_m2
#SBATCH -p shared
#SBATCH -c 8
#SBATCH --mem=32G
#SBATCH -t 24:00:00
#SBATCH -o /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/atlas-paper-vae/logs/train_%j.out
#SBATCH -e /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/atlas-paper-vae/logs/train_%j.err

set -eo pipefail
ROOT="/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT"
cd "$ROOT"
mkdir -p atlas-paper-vae/logs atlas-paper-vae/results/atlas_paper_vae_m2_v08_ood

# Avoid `set -u` + ~/.bashrc (BASHRCSOURCED unbound). Use conda.sh directly.
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate scgen_tf1
export PYTHONUNBUFFERED=1
export PYTHONPATH="${ROOT}/scgen-cellot-ablation/scgen-reproducibility/code:${PYTHONPATH:-}"
export OMP_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
export MKL_NUM_THREADS="${SLURM_CPUS_PER_TASK:-8}"
set -u

echo "=== atlas paper VAE job ${SLURM_JOB_ID:-local} started $(date) ==="
echo "host=$(hostname) cpus=${SLURM_CPUS_PER_TASK:-?} mem=${SLURM_MEM_PER_NODE:-?}"
python -c "import tensorflow as tf; print('TF', tf.__version__)"

# Full train (Stage-0 knobs: 300 epochs, z=100, α=5e-5) then Stage-0-like metrics.json
python atlas-paper-vae/scripts/01_train_vae.py --go
python atlas-paper-vae/scripts/02_eval_metrics.py --go

echo "=== done $(date) ==="
ls -la atlas-paper-vae/results/atlas_paper_vae_m2_v08_ood/
test -f atlas-paper-vae/results/atlas_paper_vae_m2_v08_ood/metrics.json
echo "metrics.json present"

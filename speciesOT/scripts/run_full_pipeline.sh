#!/bin/bash
# run_full_pipeline.sh
# End-to-end reproduction of the May-8 atlas-full + BCG-prediction pipeline.
# Total wall time: ~60-90 min (most of it waiting for sbatch trainings).
#
# Usage:
#   bash scripts/run_full_pipeline.sh
#
# Phases (each is also runnable standalone — see commented commands inline):
#   A. Atlas data prep (no holdout, 2 HVG flavors)            ~5 min CPU
#   B. Submit 4 trainings (2 flavors x scGen + IMPACT)         ~30+35 min sbatch
#   C. BCG mouse preprocessing                                 ~3 min CPU
#   D. BCG prediction via 4 trained models                     ~3 min CPU
#   E. Paper-style figure F + G replicas                       ~1 min CPU

set -euo pipefail
BASE="/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT"
ANALYSIS_PY="/n/home01/jzhou1125/miniforge3/envs/analysis/bin/python"
NB_DIR="$BASE/speciesOT/baseline/analysis"

cd "$BASE"
echo "=== speciesOT pipeline starting at $(date) ==="

# ------------------------------------------------------------------
# Phase A: atlas data prep (no holdout)
# ------------------------------------------------------------------
echo ""
echo "=== A. Atlas full-data preprocessing (notebook 15) ==="
$ANALYSIS_PY -m nbconvert --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=3600 \
    --ExecutePreprocessor.kernel_name=python3 \
    "$NB_DIR/15_data_prep_full_atlas_no_holdout.ipynb"
echo "Phase A done."

# ------------------------------------------------------------------
# Phase B: train 4 models
# ------------------------------------------------------------------
echo ""
echo "=== B. Generating + submitting 4 atlas-full trainings ==="
$ANALYSIS_PY scripts/generate_atlas_full_configs.py

JOB_IDS=""
for flavor in seurat_v3 pearson_residuals; do
    SC=$(sbatch --parsable sbatch/train/train_atlas_full_${flavor}_scgen.sbatch)
    IM=$(sbatch --parsable --dependency=afterok:$SC \
                sbatch/train/train_atlas_full_${flavor}_impact_cellot.sbatch)
    echo "  $flavor: scgen=$SC impact=$IM"
    JOB_IDS="$JOB_IDS $SC $IM"
done

# Wait for all 4 trainings to finish
echo ""
echo "Waiting for trainings (poll every 60 s)..."
while true; do
    PENDING=0
    for j in $JOB_IDS; do
        ST=$(sacct -j "$j" --format=State -X --noheader -P 2>/dev/null | head -1)
        case "$ST" in
            COMPLETED|FAILED|CANCELLED*|TIMEOUT|NODE_FAIL) ;;
            *) PENDING=$((PENDING + 1)) ;;
        esac
    done
    if [[ "$PENDING" -eq 0 ]]; then
        echo "  all trainings finished"; break
    fi
    echo "  $PENDING/4 still running... ($(date +%H:%M:%S))"
    sleep 60
done

# Sanity-check: verify cache/model.pt exists for each
for flavor in seurat_v3 pearson_residuals; do
    for model in scgen impact_cellot; do
        ckpt="$BASE/cellot/cellot_gpu/results/atlas_full_${flavor}/${model}/cache/model.pt"
        if [[ ! -f "$ckpt" ]]; then
            echo "ERROR: missing $ckpt — training likely failed"
            exit 1
        fi
    done
done
echo "Phase B done."

# ------------------------------------------------------------------
# Phase C: BCG mouse preprocessing
# ------------------------------------------------------------------
echo ""
echo "=== C. BCG mouse preprocessing (notebook 16) ==="
$ANALYSIS_PY -m nbconvert --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=1800 \
    --ExecutePreprocessor.kernel_name=python3 \
    "$NB_DIR/16_bcg_mouse_data_prep.ipynb"
echo "Phase C done."

# ------------------------------------------------------------------
# Phase D: BCG prediction
# ------------------------------------------------------------------
echo ""
echo "=== D. BCG prediction (notebook 17) ==="
$ANALYSIS_PY -m nbconvert --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=1800 \
    --ExecutePreprocessor.kernel_name=python3 \
    "$NB_DIR/17_bcg_prediction.ipynb"
echo "Phase D done."

# ------------------------------------------------------------------
# Phase E: paper-style figures from existing matrix
# ------------------------------------------------------------------
echo ""
echo "=== E. Figure F + G replicas (notebook 18) ==="
$ANALYSIS_PY -m nbconvert --to notebook --execute --inplace \
    --ExecutePreprocessor.timeout=1800 \
    --ExecutePreprocessor.kernel_name=python3 \
    "$NB_DIR/18_paper_figure_F_G_replica.ipynb"
echo "Phase E done."

echo ""
echo "=== ALL DONE at $(date) ==="
echo ""
echo "Outputs:"
echo "  Atlas datasets:     $BASE/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_*_atlas_full_v07.h5ad"
echo "  BCG aligned:        $BASE/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/bcg_mouse_aligned_*_v07.h5ad"
echo "  BCG predictions:    $BASE/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/bcg_predicted_human_*.h5ad"
echo "  UMAP overlays:      $NB_DIR/bcg_prediction_outputs/figures/"
echo "  Figure F+G:         $NB_DIR/paper_figure_replica_outputs/figures/"
echo "  HVG selection:      $NB_DIR/atlas_full_outputs/hvg_atlas_full_*.csv"
echo "  BCG coverage:       $NB_DIR/bcg_mouse_outputs/bcg_atlas_hvg_coverage.csv"

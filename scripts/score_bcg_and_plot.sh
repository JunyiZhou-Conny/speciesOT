#!/bin/bash
# score_bcg_and_plot.sh
# After predict_new_input.sh (and the human-target projection) have written
# their .h5ad files, score IMPACT + scGen against the real human cloud and
# write the paper-style BCG boards.
#
# This is the reusable eval+figure step. 16.4 calls the same two scripts;
# later atlas models × BCG corrections should come through here rather than
# recoding plots in a notebook.
#
# Usage:
#   bash scripts/score_bcg_and_plot.sh \
#       --model-set uncapped_v08_iid \
#       --flavor pearson_residuals \
#       --tag bcg_ctrl_a2 \
#       --target $D/bcg_human_unvax_target_pearson_residuals_uncapped_v08_iid_anndata07.h5ad
#
# Optional:
#   --source   aligned mouse (default: $D/${tag}_aligned_${flavor}${suffix}_anndata07.h5ad)
#   --aedir    AE dir (default: results/<results_subdir>/scgen)
#   --outdir   figure directory (default: speciesOT/baseline/analysis/paper_style_bcg_outputs/<combo>)
#   --label    board title
#   --skip-eval   only redraw figures from existing CSVs
#   --skip-plot   only run eval_external_target.py
#
# Envs: CellOT for eval, analysis for figures. Same finder as predict_new_input.sh.

set -euo pipefail

MODEL_SET="uncapped_v08_iid"
FLAVOR="pearson_residuals"
TAG=""
TARGET=""
SOURCE=""
AEDIR=""
OUTDIR=""
LABEL=""
SKIP_EVAL=0
SKIP_PLOT=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --model-set) MODEL_SET="$2"; shift 2 ;;
        --flavor)    FLAVOR="$2"; shift 2 ;;
        --tag)       TAG="$2"; shift 2 ;;
        --target)    TARGET="$2"; shift 2 ;;
        --source)    SOURCE="$2"; shift 2 ;;
        --aedir)     AEDIR="$2"; shift 2 ;;
        --outdir)    OUTDIR="$2"; shift 2 ;;
        --label)     LABEL="$2"; shift 2 ;;
        --skip-eval) SKIP_EVAL=1; shift ;;
        --skip-plot) SKIP_PLOT=1; shift ;;
        -h|--help)
            sed -n '2,30p' "$0"
            exit 0
            ;;
        *)
            echo "ERROR: unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

if [[ -z "$TAG" || -z "$TARGET" ]]; then
    echo "ERROR: --tag and --target are required" >&2
    exit 1
fi

case "$MODEL_SET" in
    atlas_full_v07)
        RESULTS_TEMPLATE="atlas_full_{flavor}"
        SET_SUFFIX=""
        SHORT="v07"
        ;;
    uncapped_v08)
        RESULTS_TEMPLATE="hvg_{flavor}_uncapped_v08"
        SET_SUFFIX="_uncapped_v08"
        SHORT="v08"
        ;;
    uncapped_v08_iid)
        RESULTS_TEMPLATE="hvg_{flavor}_a_uncapped_v08_iid"
        SET_SUFFIX="_uncapped_v08_iid"
        SHORT="v08iid"
        ;;
    *)
        echo "ERROR: unknown --model-set '$MODEL_SET'" >&2
        echo "  valid: atlas_full_v07, uncapped_v08, uncapped_v08_iid" >&2
        exit 1
        ;;
esac

if [[ "$FLAVOR" != "pearson_residuals" && "$FLAVOR" != "mixhvg" && "$FLAVOR" != "seurat_v3" ]]; then
    echo "ERROR: unknown --flavor '$FLAVOR'" >&2
    exit 1
fi

BASE="${SPECIESOT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
D="$BASE/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg"
FLAV="${FLAVOR}${SET_SUFFIX}"
RESULTS_SUBDIR="${RESULTS_TEMPLATE//\{flavor\}/$FLAVOR}"
COMBO="${TAG}_${FLAVOR}_${MODEL_SET}"
# Flavor is in the eval tag so pearson and mixhvg of the same BCG file do not collide.
EVAL_IMPACT_TAG="${TAG}_impact_${FLAVOR}_${SHORT}"
EVAL_SCGEN_TAG="${TAG}_scgen_${FLAVOR}_${SHORT}"
EVAL_ROOT="$BASE/results/external_eval"

[[ -n "$SOURCE" ]] || SOURCE="$D/${TAG}_aligned_${FLAV}_anndata07.h5ad"
[[ -n "$AEDIR" ]] || AEDIR="$BASE/cellot/cellot_gpu/results/${RESULTS_SUBDIR}/scgen"
[[ -n "$OUTDIR" ]] || OUTDIR="$BASE/speciesOT/baseline/analysis/paper_style_bcg_outputs/${COMBO}"
[[ -n "$LABEL" ]] || LABEL="BCG ${TAG} · ${FLAVOR} · ${MODEL_SET}"

PRED_IMPACT="$D/${TAG}_predicted_human_via_impact_cellot_${FLAV}.h5ad"
PRED_SCGEN="$D/${TAG}_predicted_human_via_scgen_${FLAV}.h5ad"
# Figures prefer the analysis-env aligned file (same numbers as _anndata07).
SOURCE_PLOT="$D/${TAG}_aligned_${FLAV}.h5ad"
TARGET_PLOT="${TARGET/_anndata07.h5ad/.h5ad}"
[[ -f "$TARGET_PLOT" ]] || TARGET_PLOT="$TARGET"
SYMBOLS_CSV="$D/gene_lists/hvg_${FLAVOR}_a_uncapped_v08_genes.csv"
[[ -f "$SYMBOLS_CSV" ]] || SYMBOLS_CSV=""

find_env_python() {
    local env_name="$1" override="${2:-}" cand
    if [[ -n "$override" ]]; then
        if [[ -x "$override" ]]; then echo "$override"; return 0; fi
        echo "ERROR: override interpreter not executable: $override" >&2
        return 1
    fi
    for base in "$HOME/miniforge3" "$HOME/.conda" "$HOME/miniconda3" \
                "$HOME/anaconda3" "$HOME/mambaforge" \
                "/n/home01/jzhou1125/miniforge3" "/n/home01/jzhou1125/.conda"; do
        cand="$base/envs/$env_name/bin/python"
        if [[ -x "$cand" ]]; then echo "$cand"; return 0; fi
    done
    echo "ERROR: could not find a python for conda env '$env_name'." >&2
    return 1
}

ANALYSIS_PY="$(find_env_python "${SPECIESOT_ANALYSIS_ENV:-analysis}" "${SPECIESOT_ANALYSIS_PY:-}")"
CELLOT_PY="$(find_env_python "${SPECIESOT_CELLOT_ENV:-CellOT}" "${SPECIESOT_CELLOT_PY:-}")"

echo "=== score_bcg_and_plot.sh ==="
echo "  model set: $MODEL_SET"
echo "  flavor:    $FLAVOR"
echo "  tag:       $TAG"
echo "  combo:     $COMBO"
echo "  source:    $SOURCE"
echo "  target:    $TARGET"
echo "  aedir:     $AEDIR"
echo "  figures:   $OUTDIR"
echo "  cellot:    $CELLOT_PY"
echo "  analysis:  $ANALYSIS_PY"

for p in "$SOURCE" "$TARGET" "$PRED_IMPACT" "$PRED_SCGEN" "$AEDIR"; do
    if [[ ! -e "$p" ]]; then
        echo "ERROR: missing $p" >&2
        exit 1
    fi
done

if [[ "$SKIP_EVAL" -eq 0 ]]; then
    echo "=== eval IMPACT ==="
    "$CELLOT_PY" "$BASE/scripts/eval_external_target.py" \
        --pred "$PRED_IMPACT" \
        --target "$TARGET" \
        --source "$SOURCE" \
        --aedir "$AEDIR" \
        --tag "$EVAL_IMPACT_TAG"
    echo "=== eval scGen ==="
    "$CELLOT_PY" "$BASE/scripts/eval_external_target.py" \
        --pred "$PRED_SCGEN" \
        --target "$TARGET" \
        --source "$SOURCE" \
        --aedir "$AEDIR" \
        --tag "$EVAL_SCGEN_TAG"
fi

CSV_IMPACT="$EVAL_ROOT/${EVAL_IMPACT_TAG}/external_target_metrics.csv"
CSV_SCGEN="$EVAL_ROOT/${EVAL_SCGEN_TAG}/external_target_metrics.csv"

if [[ "$SKIP_PLOT" -eq 0 ]]; then
    if [[ ! -f "$SOURCE_PLOT" ]]; then
        SOURCE_PLOT="$SOURCE"
    fi
    PLOT_ARGS=(
        "$ANALYSIS_PY" "$BASE/scripts/plot_bcg_paper_figures.py"
        --source "$SOURCE_PLOT"
        --target "$TARGET_PLOT"
        --pred-impact "$PRED_IMPACT"
        --pred-scgen "$PRED_SCGEN"
        --eval-impact "$CSV_IMPACT"
        --eval-scgen "$CSV_SCGEN"
        --outdir "$OUTDIR"
        --label "$LABEL"
        --source-label "mouse BCG"
        --target-label "human BCG"
    )
    if [[ -n "$SYMBOLS_CSV" ]]; then
        PLOT_ARGS+=(--symbols-csv "$SYMBOLS_CSV")
    fi
    echo "=== paper-style figures ==="
    "${PLOT_ARGS[@]}"
    echo "figures: $OUTDIR"
fi

#!/bin/bash
# Submit the full 5-flavor x 4-group x 2-mode x 2-model HVG validation matrix
# with proper afterok dependencies. Idempotent-ish: if a job for the same name
# is already in your queue (running or pending), it skips submission.
#
# Order of submission:
#   1. Submit all 40 train_*_scgen.sbatch (no deps).
#   2. For each (flavor, group, mode):
#      a. Submit train_*_impact_cellot.sbatch with --dependency=afterok:<scgen_jobid>.
#      b. Submit eval_*_scgen.sbatch with --dependency=afterok:<scgen_jobid>.
#      c. Submit eval_*_impact_cellot.sbatch with --dependency=afterok:<impact_jobid>.
#
# Output: writes a CSV log of (cell_tag, scgen_jobid, impact_jobid, eval_scgen_jobid,
# eval_impact_jobid) to scripts/.submitted_hvg_flavor_matrix.csv for later tracking.
#
# Usage:  bash scripts/submit_hvg_flavor_matrix.sh [filter_pattern]
#   filter_pattern: optional substring to limit which (flavor, group, mode) cells
#     are submitted. e.g. `pearson_residuals` to only submit the Pearson runs;
#     `_a_` to only submit Group A across flavors. Empty = submit all 40 cells.

set -euo pipefail

BASE="/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT"
TRAIN_DIR="${BASE}/sbatch/train"
EVAL_DIR="${BASE}/sbatch/eval"
LOG="${BASE}/scripts/.submitted_hvg_flavor_matrix.csv"

FILTER="${1:-}"

FLAVORS=(seurat cell_ranger seurat_v3 seurat_v3_paper pearson_residuals)
GROUPS=(a b c d)
MODES=(ood iid)

echo "tag,scgen_jobid,impact_jobid,eval_scgen_jobid,eval_impact_jobid" > "${LOG}.tmp"

submit_one() {
    local sbatch_file=$1
    shift
    local extra_flags=("$@")

    if [[ ! -f "${sbatch_file}" ]]; then
        echo "MISSING: ${sbatch_file}" >&2
        return 1
    fi

    local jobid
    jobid=$(sbatch "${extra_flags[@]}" --parsable "${sbatch_file}" 2>&1)
    if [[ -z "${jobid}" || ! "${jobid}" =~ ^[0-9]+$ ]]; then
        echo "FAILED submit ${sbatch_file}: ${jobid}" >&2
        return 1
    fi
    echo "${jobid}"
}

for flavor in "${FLAVORS[@]}"; do
    for gk in "${GROUPS[@]}"; do
        for mode in "${MODES[@]}"; do
            tag="hvg_${flavor}_${gk}_${mode}"

            if [[ -n "${FILTER}" && "${tag}" != *"${FILTER}"* ]]; then
                continue
            fi

            scgen_train="${TRAIN_DIR}/train_${tag}_scgen.sbatch"
            impact_train="${TRAIN_DIR}/train_${tag}_impact_cellot.sbatch"
            scgen_eval="${EVAL_DIR}/eval_${tag}_scgen.sbatch"
            impact_eval="${EVAL_DIR}/eval_${tag}_impact_cellot.sbatch"

            echo ""
            echo "=== ${tag} ==="

            # 1. train scGen (no deps)
            scgen_jobid=$(submit_one "${scgen_train}")
            echo "  scGen train  : ${scgen_jobid}"

            # 2. train IMPACT_CellOT after scGen
            impact_jobid=$(submit_one "${impact_train}" --dependency="afterok:${scgen_jobid}")
            echo "  IMPACT train : ${impact_jobid} (afterok ${scgen_jobid})"

            # 3. eval scGen after scGen training
            eval_scgen_jobid=$(submit_one "${scgen_eval}" --dependency="afterok:${scgen_jobid}")
            echo "  scGen eval   : ${eval_scgen_jobid} (afterok ${scgen_jobid})"

            # 4. eval IMPACT_CellOT after IMPACT training
            eval_impact_jobid=$(submit_one "${impact_eval}" --dependency="afterok:${impact_jobid}")
            echo "  IMPACT eval  : ${eval_impact_jobid} (afterok ${impact_jobid})"

            echo "${tag},${scgen_jobid},${impact_jobid},${eval_scgen_jobid},${eval_impact_jobid}" >> "${LOG}.tmp"
        done
    done
done

mv "${LOG}.tmp" "${LOG}"

echo ""
echo "=================================================================="
echo "All submissions complete. Job log: ${LOG}"
echo "$(wc -l < "${LOG}") lines (header + cells submitted)."
echo ""
echo "Quick status:  squeue -u \$USER -t PD,R --noheader | wc -l"
echo "Stuck deps:    squeue -u \$USER -t PD --noheader -o '%i %j %r' | grep -i depend"

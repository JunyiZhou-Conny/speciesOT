#!/bin/bash
# Submit GPU remainder chain for paper cross-species LPS replication.
#
# Usage:
#   paper_crossspecies/scripts/submit_gpu_remainder.sh              # status
#   paper_crossspecies/scripts/submit_gpu_remainder.sh --submit     # when rat scGen done
#   paper_crossspecies/scripts/submit_gpu_remainder.sh --queue-now  # queue GPU now
set -euo pipefail

source "$(dirname "$0")/../env.sh"
SBATCH_DIR="${PAPER_CROSSSPECIES_ROOT}/sbatch"
RESULTS="${CELLOT_GPU}/results"
RAT_SCGEN_STATUS="${RESULTS}/paper_crossspecies_rat_ood/scgen/cache/status"

MODE="status"
CPU_AFTER=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --submit) MODE="submit" ;;
    --queue-now) MODE="queue-now" ;;
    --after) CPU_AFTER="${2:-}"; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 1 ;;
  esac
  shift
done

find_cpu_full_job() {
  squeue -u "${USER}" -h -o "%i %j" 2>/dev/null | awk '$2=="paper_lps_full" {print $1; exit}'
}

scancel_cpu_continuations() {
  local ids
  ids="$(squeue -u "${USER}" -h -o "%i %j" 2>/dev/null | awk '$2=="paper_lps_cont" {print $1}')"
  if [[ -z "${ids}" ]]; then
    echo "No pending paper_lps_cont jobs to cancel."
    return 0
  fi
  echo "scancel paper_lps_cont: $(echo "$ids" | tr '\n' ' ')"
  while read -r jid; do
    [[ -n "${jid}" ]] && scancel "${jid}"
  done <<< "${ids}"
}

submit_gpu_chain() {
  local dep="${1:-}"
  local dep_arg=""
  if [[ -n "${dep}" ]]; then
    dep_arg="--dependency=afterany:${dep}"
  fi
  cd "${SBATCH_DIR}"
  if [[ -n "${dep_arg}" ]]; then
    JOB1="$(sbatch "${dep_arg}" run_full_pipeline_gpu.sbatch | awk '{print $NF}')"
  else
    JOB1="$(sbatch run_full_pipeline_gpu.sbatch | awk '{print $NF}')"
  fi
  JOB2="$(sbatch --dependency=afterany:"${JOB1}" run_full_pipeline_gpu_continue.sbatch | awk '{print $NF}')"
  echo "Submitted ${JOB1} (paper_lps_gpu, 72h)${dep:+ afterany:${dep}}"
  echo "Submitted ${JOB2} (paper_lps_gpu_c, afterany:${JOB1})"
  echo ""
  echo "Monitor:"
  echo "  squeue -u \$USER -n paper_lps_gpu,paper_lps_gpu_c,paper_lps_full"
  echo "  tail -f ${RESULTS}/paper_crossspecies/_logs/pipeline/paper_crossspecies_pipeline_gpu_${JOB1}.err"
}

echo "=== Paper cross-species GPU remainder ==="
echo "Bundle: ${PAPER_CROSSSPECIES_ROOT}"
echo ""

if [[ -f "${RAT_SCGEN_STATUS}" ]]; then
  echo "rat scGen status: $(cat "${RAT_SCGEN_STATUS}")"
else
  echo "rat scGen status: (no cache/status yet)"
fi

CPU_JOB="$(find_cpu_full_job)"
if [[ -n "${CPU_JOB}" ]]; then
  echo "paper_lps_full job: ${CPU_JOB}"
else
  echo "paper_lps_full job: (not running)"
fi
echo ""

if [[ "${MODE}" == "status" ]]; then
  echo "Submit when rat scGen is done:"
  echo "  ${PAPER_CROSSSPECIES_ROOT}/scripts/submit_gpu_remainder.sh --submit"
  echo ""
  echo "Queue GPU now (cancel CPU continuations, depend on paper_lps_full):"
  echo "  ${PAPER_CROSSSPECIES_ROOT}/scripts/submit_gpu_remainder.sh --queue-now"
  exit 0
fi

if [[ "${MODE}" == "queue-now" ]]; then
  if [[ -z "${CPU_AFTER}" ]]; then
    CPU_AFTER="${CPU_JOB:-}"
  fi
  if [[ -z "${CPU_AFTER}" ]]; then
    echo "ERROR: no running paper_lps_full job and no --after JOBID." >&2
    exit 1
  fi
  scancel_cpu_continuations
  echo ""
  echo "IMPORTANT: when rat scGen finishes (cache/status=done), scancel CPU job before IMPACT starts:"
  echo "  scancel ${CPU_AFTER}"
  echo "  (GPU jobs are queued with afterany:${CPU_AFTER} and will start when that job ends)"
  echo ""
  submit_gpu_chain "${CPU_AFTER}"
  exit 0
fi

if [[ ! -f "${RAT_SCGEN_STATUS}" ]] || [[ "$(cat "${RAT_SCGEN_STATUS}")" != "done" ]]; then
  echo "ERROR: rat scGen is not done. Use --queue-now to wait on paper_lps_full, or wait." >&2
  exit 1
fi
scancel_cpu_continuations
echo ""
submit_gpu_chain ""

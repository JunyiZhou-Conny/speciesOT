#!/bin/bash
# Poll smoke GPU job; on success submit production pipeline; on failure alert in log.
set -euo pipefail

source "$(dirname "$0")/../env.sh"
SMOKE_JOB="${1:-}"
LOG="${CELLOT_GPU}/results/paper_crossspecies/_logs/monitor_smoke.log"
BENCH="${CELLOT_GPU}/results/paper_crossspecies/_logs/gpu_benchmark.json"

log() { echo "$(date -Iseconds) $*" | tee -a "${LOG}"; }

if [[ -z "${SMOKE_JOB}" ]]; then
  SMOKE_JOB=$(squeue -u "${USER}" -h -o "%i %j" | awk '$2 ~ /^pc_smoke/ {print $1; exit}')
fi

if [[ -z "${SMOKE_JOB}" ]]; then
  log "no smoke job found in queue"
  exit 1
fi

log "monitoring smoke job ${SMOKE_JOB}"

while squeue -j "${SMOKE_JOB}" -h 2>/dev/null | grep -q .; do
  st=$(squeue -j "${SMOKE_JOB}" -h -o "%T %R" 2>/dev/null)
  log "state: ${st}"
  sleep 60
done

state=$(sacct -j "${SMOKE_JOB}" --format=State -n 2>/dev/null | head -1 | tr -d ' ')
log "smoke finished state=${state}"

if [[ "${state}" != "COMPLETED" ]]; then
  log "SMOKE FAILED — check smoke_gpu_${SMOKE_JOB}.err"
  exit 1
fi

if [[ -f "${BENCH}" ]]; then
  log "benchmark: $(cat "${BENCH}")"
fi

OUT="${CELLOT_GPU}/results/_smoke_gpu_impact/cache/status"
if [[ ! -f "${OUT}" ]] || [[ "$(cat "${OUT}")" != "done" ]]; then
  log "smoke training status not done"
  exit 1
fi

log "smoke PASSED — submitting production GPU pipeline"
"${PAPER_CROSSSPECIES_ROOT}/scripts/submit_gpu_remainder.sh" --submit 2>&1 | tee -a "${LOG}"

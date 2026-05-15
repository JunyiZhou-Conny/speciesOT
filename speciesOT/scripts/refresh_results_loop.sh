#!/bin/bash
# Every REFRESH_SEC, clear + re-execute notebook 13_hvg_flavor_results.ipynb
# so figures pick up newly landed eval csvs. Stops after MAX_HOURS.

REFRESH_SEC=${REFRESH_SEC:-1200}   # 20 minutes
MAX_HOURS=${MAX_HOURS:-6}

NB="/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/speciesOT/baseline/analysis/13_hvg_flavor_results.ipynb"
PY="/n/home01/jzhou1125/miniforge3/envs/analysis/bin/python"
LOG="/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/scripts/refresh_results_loop.log"

deadline=$(( $(date +%s) + MAX_HOURS * 3600 ))

ts() { date +"%Y-%m-%dT%H:%M:%S"; }

echo "[$(ts)] refresh loop started; refresh every ${REFRESH_SEC}s for ${MAX_HOURS}h" >> "$LOG"

while [ $(date +%s) -lt $deadline ]; do
    n_eval=$(find /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/hvg_*/ -name evals.csv 2>/dev/null | wc -l)
    n_done=$(find /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/hvg_*/ -path '*/cache/status' -exec grep -l '^done$' {} \; 2>/dev/null | wc -l)

    echo "[$(ts)] re-executing analysis notebook (n_eval_csv=$n_eval, n_train_done=$n_done)" >> "$LOG"

    "$PY" -c "
import json
nb = json.load(open('$NB'))
for c in nb['cells']:
    if c['cell_type']=='code':
        c['outputs']=[]; c['execution_count']=None
json.dump(nb, open('$NB','w'), indent=1)
" >> "$LOG" 2>&1

    "$PY" -m nbconvert --to notebook --execute --inplace \
        --ExecutePreprocessor.timeout=900 \
        --ExecutePreprocessor.kernel_name=python3 \
        "$NB" >> "$LOG" 2>&1

    echo "[$(ts)] running standalone figure renderer" >> "$LOG"
    "$PY" /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/scripts/render_results_figures.py >> "$LOG" 2>&1

    echo "[$(ts)] refresh done; sleeping ${REFRESH_SEC}s" >> "$LOG"
    sleep "$REFRESH_SEC"
done

echo "[$(ts)] refresh loop ended" >> "$LOG"

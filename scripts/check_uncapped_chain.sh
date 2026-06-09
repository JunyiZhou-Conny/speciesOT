#!/bin/bash
# One-shot status check for the uncapped CD8-OOD chain.
# Usage: ./check_uncapped_chain.sh
set -euo pipefail

CHAIN_CSV="/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/scripts/.submitted_uncapped_a_ood_chain.csv"
RESULTS_DIR="/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/hvg_pearson_residuals_a_ood_uncapped"
BASELINE_DIR="/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/hvg_pearson_residuals_a_ood"

JIDS=$(cat "$CHAIN_CSV")
echo "=== Uncapped CD8-OOD chain (JIDs: $JIDS) ==="
echo
echo "--- sacct status ---"
sacct -j "$JIDS" --format=JobID%10,JobName%24,State,Elapsed,Start,End,ExitCode \
    | grep -v '\.batch\|\.extern' || true
echo
echo "--- result files ---"
for sub in scgen impact_cellot; do
    echo "[$sub]"
    if [ -d "$RESULTS_DIR/$sub" ]; then
        ls -la "$RESULTS_DIR/$sub" | grep -E "model.pt|evals|imputed|train_|eval_" || echo "  (no result files yet)"
    fi
done
echo
echo "--- eval comparison (if uncapped evals exist) ---"
for sub in scgen impact_cellot; do
    BASE_CSV="$BASELINE_DIR/$sub/evals_ood_data_space/evals.csv"
    NEW_CSV="$RESULTS_DIR/$sub/evals_ood_data_space/evals.csv"
    if [ -f "$NEW_CSV" ]; then
        echo "[$sub]  baseline (capped) vs new (uncapped) -- r2-means rows:"
        echo "    baseline:"
        grep "r2-means" "$BASE_CSV" 2>/dev/null | sed 's/^/      /'
        echo "    uncapped:"
        grep "r2-means" "$NEW_CSV" | sed 's/^/      /'
    fi
done

# scripts/

Automation scripts referenced by the speciesOT pipeline. See `../HOW_TO_RUN_NEW_INPUT.txt` (or `.md`) for the full step-by-step.

## Canonical vs runtime location

These versioned copies live inside the git repo at `speciesOT/scripts/`. The runtime working tree on the cluster also has a `scripts/` folder at the workspace root (`/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/scripts/`) — that's where the cron loops, sbatch wrappers, and BioMart cache files actually live. The two stay in sync by hand for now.

When editing a script, edit the version inside the git repo first, then `cp` it to the workspace-root location to pick up the new behavior at runtime.

## Files

### Top-level wrappers (run these directly)

- `run_full_pipeline.sh` — end-to-end reproduction of the May-8 atlas-full + BCG pipeline. ~60-90 min wall time.
- `predict_new_input.sh <mouse.h5ad> [tag]` — predict on a brand-new mouse single-cell file using the existing trained models. ~50 sec wall time. Auto-detects ENSMUSG vs symbol var_names.

### Config + sbatch generators (one-shot, idempotent)

- `generate_atlas_full_configs.py` — emits 4 configs + 4 sbatch scripts for atlas-full training (2 flavors × scGen + IMPACT_CellOT).
- `generate_hvg_flavor_configs.py` — emits the 80-cell matrix configs (5 HVG flavors × 4 holdout groups × 2 modes × 2 models).
- `generate_toggle_configs.py` — earlier toggle_ood matrix generator (superseded by `generate_hvg_flavor_configs.py`).
- `generate_data_space_eval_sbatches.py` — emits per-cell data-space eval sbatches.

### Submitters and orchestration

- `submit_hvg_flavor_matrix.sh` — submits the 80-cell matrix with afterok dependency chains.
- `regenerate_hvg_flavor_run_matrix.py` — regenerates `hvg_flavor_run_matrix.{csv,md}` from the configs (keeps the matrix manifest in sync).

### Runtime helpers

- `biomart_watchdog.py` — polls BioMart and generates missing HVG datasets when service recovers. Used overnight when BioMart was flaky.
- `refresh_results_loop.sh` — periodically re-renders matrix figures via `render_results_figures.py` so they stay current as evals trickle in.

### Renderers + inventories

- `render_results_figures.py` — produces matrix-wide R²/MMD heatmaps, gap scatter, biomarker density, and the reusable `plot_metric_bars()` and `plot_marginals_paper_style()` functions used by notebook 18.
- `build_experiments_inventory.py` — scans `cellot/cellot_gpu/results/` and writes a CSV inventory of all training runs and their states.

## Files NOT versioned

The `.gitignore` excludes:
- `.biomart_*.csv`, `.bcg_symbol_*.csv` — BioMart caches, regenerated on demand
- `.submitted_*.csv` — per-run job-submission logs
- `*.log`, `*.pid` — loop and watcher runtime state
- `__pycache__/`, `*.pyc` — Python bytecode

If any of these go missing on the cluster, the scripts will recreate them on next run.

# speciesOT — interspecies CellOT baseline

Single-cell transport experiments (human–mouse baseline, HVG flavors, IID/OOD, BCG TB extension) centered on notebooks under `speciesOT/baseline/analysis/`, Slurm scripts under `scripts/` and `sbatch/`, and the embedded **CellOT** fork in `cellot/cellot_gpu/`.

This repository underwent **Tier 1 (cosmetic) reorganization on 2026-05-15**: logs and archives have dedicated folders; historical notebooks moved under `speciesOT/baseline/analysis/archive/`; exploratory `e*.ipynb` notebooks moved to `speciesOT/archive/exploratory_notebooks/`; reference PDFs under `reference/`. See **`REFACTOR_PLAN_2026-05-05.md`** for full scope and Tier 2+ options.

## Layout (high level)

| Path | Role |
|------|------|
| `speciesOT/baseline/analysis/` | **Active** analysis notebooks (`01.*`–`18`, BCG, preparation) |
| `speciesOT/baseline/analysis/archive/` | Older / superseded baseline notebooks (moved only, not deleted) |
| `speciesOT/archive/exploratory_notebooks/` | Earlier `e1`–`e18` exploration |
| `scripts/` | Config generators, submitters, watchers, inventory, rendering |
| `cellot/cellot_gpu/` | Fork used for train/eval (configs, code, upstream scripts) |
| `cellot/_archive/` | Unused CPU CellOT mirror (was `cellot/cellot/`); see `archive/old_notes/cellot_cell_py_cpu_vs_gpu.diff` |
| `logs/research_logs/` | Dated narrative logs (`research_log_YYYY-MM-DD.txt`) |
| `logs/mentor_meetings/` | Mentor notes and briefings |
| `logs/NOTEBOOK_INDEX.md` | Map: notebooks ↔ logs ↔ outputs |
| `reference/` | Key papers (`Bunne et al - 2023.pdf`, `scGen.pdf`) |
| `autospeciesOT/` | Older small experiment bundle |

## Entry-point notebooks (typical workflow)

- **Data:** `01.3_data_prep_all_holdouts_renorm.ipynb`, `01.5_data_prep_all_holdouts_hvg_flavors.ipynb`, `09_data_prep_toggle_experiments.ipynb`
- **Aggregation / figures:** `13_hvg_flavor_results.ipynb`, `14_hvg_flavor_notebook6_replica.ipynb`
- **BCG TB line:** `16_bcg_mouse_data_prep.ipynb`, `16.1_*`, `17_bcg_prediction.ipynb`
- **Presentation:** `presentation_preparation.ipynb`

## Git and nested repositories

Version control for this **workspace root** was initialized during Tier 1. Previously, separate `.git` directories lived under `speciesOT/` (inner project) and `cellot/cellot_gpu/`. Those directories were **moved** to `archive/git_backups/` (saved as `speciesOT_inner_dot_git`, `cellot_cellot_gpu_dot_git`) so the root repo can track all files without “embedded repository” gitlinks. To restore upstream-style `git pull` inside `cellot/cellot_gpu/`, rename that backup back to `.git` inside that directory.

## Environment

Use the **analysis** conda env for Scanpy-heavy notebooks and the **CellOT** env for training/eval (see project notes and `REFACTOR_PLAN` Section 6 for anndata version constraints).

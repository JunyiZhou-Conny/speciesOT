# Notebooks ↔ logs ↔ outputs

Use this as a bridge between **dated research logs** (`logs/research_logs/research_log_*.txt`) and **notebooks**. When you finish a session, add one line to the day’s log: notebook path, what you ran, and output directory (if any).

## Active baseline (`speciesOT/baseline/analysis/`)

| Notebook | Role | Typical outputs (under `baseline/analysis/`) |
|----------|------|-------------------------------------|
| `01.2_pipeline_comparison.ipynb` | UMAP / pipeline reference | (varies) |
| `01.3_data_prep_all_holdouts_renorm.ipynb` | Renorm holdout prep | `baseline/results/` (see notebook) |
| `01.4_hvg_flavor_comparison.ipynb` | HVG flavor (Group A) | `hvg_flavor_outputs/` |
| `01.5_data_prep_all_holdouts_hvg_flavors.ipynb` | 5-flavor × group prep | `hvg_flavor_outputs/` |
| `02_scgen_training_analysis.ipynb` | scGen training / checkpoint choice | (figures in notebook or results) |
| `06_cd8_holdout_evaluation.ipynb` | Headline CD8 eval template | `interactive_plots/`, etc. |
| `08.1_renorm_vs_stale_comparison.ipynb` | Renorm vs stale | (varies) |
| `09_data_prep_toggle_experiments.ipynb` | Toggle IID/OOD prep | (see notebook) |
| `10_iid_vs_ood_evaluation.ipynb` | IID vs OOD eval | (see notebook) |
| `13_hvg_flavor_results.ipynb` | HVG matrix aggregation | `hvg_flavor_results_outputs/` |
| `14_hvg_flavor_notebook6_replica.ipynb` | Per-cell figures | `hvg_flavor_nb14_outputs/` |
| `15_data_prep_full_atlas_no_holdout.ipynb` | Atlas full prep | `atlas_full_outputs/` |
| `16_bcg_mouse_data_prep.ipynb` | BCG × mouse HVG QC | `bcg_mouse_outputs/` |
| `16.1_bcg_mouse_data_prep_atlas_hvg_intersection.ipynb` | BCG atlas intersection | `bcg_mouse_outputs/` (or sibling) |
| `17_bcg_prediction.ipynb` | BCG prediction viz | `bcg_prediction_outputs/` |
| `18_paper_figure_F_G_replica.ipynb` | Paper figure replica | `paper_figure_replica_outputs/` |
| `presentation_preparation.ipynb` | Slides / talk figures | `presentation_figure_outputs/` |

## Archived baseline (`baseline/analysis/archive/`)

Historical / superseded notebooks (00, 01, 01.1, 03–05, 06.1–06.5, 07–08, 11–12); see **`REFACTOR_PLAN_2026-05-05.md`** Q3 for rationale.

## Exploratory notebooks (`speciesOT/archive/exploratory_notebooks/`)

`e1_perturbot_interspecies.ipynb` through `e18_confirming_cellot_identities.ipynb` (plus `e9_immune_cell_dimensionality.ipynb`).

## Other

- `speciesOT/tb1_mouse_setup.ipynb` — TB / mouse setup (not moved in Tier 1).

Update this file when you add a new numbered notebook or a new `*_outputs/` directory.

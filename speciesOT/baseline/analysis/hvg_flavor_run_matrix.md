# 5-Flavor HVG Validation Run Matrix

Final design as implemented by `01.5_data_prep_all_holdouts_hvg_flavors.ipynb` and `scripts/generate_hvg_flavor_configs.py`. See `research_log_2026-05-04.txt` for the four design decisions and their justification.

## Counts

- Trained models: 80 (40 scGen + 40 IMPACT_CellOT). No Normal CellOT, no monocyte groups.
- Sbatch scripts: 160 (40 train scGen + 40 train IMPACT + 40 eval scGen + 40 eval IMPACT).
- Dataset files: 20 (one combined file per (flavor, group); shared between scGen and IMPACT and between IID and OOD modes; the IID/OOD split happens at training time via `datasplit.name=toggle_ood`).

## Axes

- HVG flavors: `seurat`, `cell_ranger`, `seurat_v3`, `seurat_v3_paper`, `pearson_residuals`
- Holdout groups:
  - **A** = `cd8` (CD8 only): holdout = [CL:0000625]
  - **B** = `cd8_thymo` (CD8 + thymocyte combined): holdout = [CL:0000625, CL:0000893]
  - **C** = `tcell_subtypes` (CD4 + CD8 + thymocyte combined): holdout = [CL:0000624, CL:0000625, CL:0000893]
  - **D** = `cd4` (CD4 only): holdout = [CL:0000624]
- Modes: `ood`, `iid` (toggle_ood semantics; eval set fixed across modes).
- Models: `scgen`, `impact_cellot` (no `cellot` / Normal CellOT in this matrix).

## Per-flavor HVG input layer

| flavor | input layer | requires raw counts |
|---|---|---|
| `seurat` | `X (log-norm)` | False |
| `cell_ranger` | `X (log-norm)` | False |
| `seurat_v3` | `layers['counts']` | True |
| `seurat_v3_paper` | `layers['counts']` | True |
| `pearson_residuals` | `layers['counts']` | True |

## Flavor row counts

- `seurat`: 16 rows (4 groups x 2 modes x 2 models)
- `cell_ranger`: 16 rows (4 groups x 2 modes x 2 models)
- `seurat_v3`: 16 rows (4 groups x 2 modes x 2 models)
- `seurat_v3_paper`: 16 rows (4 groups x 2 modes x 2 models)
- `pearson_residuals`: 16 rows (4 groups x 2 modes x 2 models)

## First 12 rows (preview)

| flavor | group | mode | model | data file | result dir |
|---|---|---|---|---|---|
| `seurat` | a | ood | scGen | `datasets/speciesot-human-mouse-hvg/hvg_seurat_a_v07.h5ad` | `results/hvg_seurat_a_ood/scgen` |
| `seurat` | a | ood | IMPACT_CellOT | `datasets/speciesot-human-mouse-hvg/hvg_seurat_a_v07.h5ad` | `results/hvg_seurat_a_ood/impact_cellot` |
| `seurat` | a | iid | scGen | `datasets/speciesot-human-mouse-hvg/hvg_seurat_a_v07.h5ad` | `results/hvg_seurat_a_iid/scgen` |
| `seurat` | a | iid | IMPACT_CellOT | `datasets/speciesot-human-mouse-hvg/hvg_seurat_a_v07.h5ad` | `results/hvg_seurat_a_iid/impact_cellot` |
| `seurat` | b | ood | scGen | `datasets/speciesot-human-mouse-hvg/hvg_seurat_b_v07.h5ad` | `results/hvg_seurat_b_ood/scgen` |
| `seurat` | b | ood | IMPACT_CellOT | `datasets/speciesot-human-mouse-hvg/hvg_seurat_b_v07.h5ad` | `results/hvg_seurat_b_ood/impact_cellot` |
| `seurat` | b | iid | scGen | `datasets/speciesot-human-mouse-hvg/hvg_seurat_b_v07.h5ad` | `results/hvg_seurat_b_iid/scgen` |
| `seurat` | b | iid | IMPACT_CellOT | `datasets/speciesot-human-mouse-hvg/hvg_seurat_b_v07.h5ad` | `results/hvg_seurat_b_iid/impact_cellot` |
| `seurat` | c | ood | scGen | `datasets/speciesot-human-mouse-hvg/hvg_seurat_c_v07.h5ad` | `results/hvg_seurat_c_ood/scgen` |
| `seurat` | c | ood | IMPACT_CellOT | `datasets/speciesot-human-mouse-hvg/hvg_seurat_c_v07.h5ad` | `results/hvg_seurat_c_ood/impact_cellot` |
| `seurat` | c | iid | scGen | `datasets/speciesot-human-mouse-hvg/hvg_seurat_c_v07.h5ad` | `results/hvg_seurat_c_iid/scgen` |
| `seurat` | c | iid | IMPACT_CellOT | `datasets/speciesot-human-mouse-hvg/hvg_seurat_c_v07.h5ad` | `results/hvg_seurat_c_iid/impact_cellot` |

Full matrix is in `hvg_flavor_run_matrix.csv`.

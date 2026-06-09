# Handoff manifest — `gpu/hvg_pearson_residuals_m1_ood/impact_cellot`

Generated 2026-06-04T06:44:54.380982. The in-vitro (atlas) top-track deliverable for the downstream (BCG / batch-correction / prediction) track.

## 1. Processed dataset

| Field | Value |
|---|---|
| data_file | `datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_m1_v07.h5ad` |
| exists | True |
| size (bytes) | 53067650 |

## 2. Preprocessing description

| Field | Value |
|---|---|
| source_datasets | `{'mouse': '/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_muris/sampled_mouse_shared.h5ad', 'human': '/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_sapiens/sampled_human_shared.h5ad'}` |
| assay_filter | `{'mouse': ['chromium_v2'], 'human': ['chromium_v3']}` |
| cap_cells_per_type | `{'mouse': 1000, 'human': 1000}` |
| ortholog_source | `biomart` |
| hvg_method | `pearson_residuals` |
| hvg_n_top | `1000` |
| hvg_input_layer | `layers['counts']` |
| hvg_batch_key | `species` |
| log1p_applied | `True` |
| holdout_cell_types | `['CL:0000875']` |
| holdout_species | `—` |
| datasplit_strategy | `toggle_ood` |
| mode | `ood` |
| test_size | `0.2` |
| random_state | `0` |

## 3. Model spec

| Field | Value |
|---|---|
| family | `impact_cellot` |
| model_name | `cellot` |
| hidden_units | `[64, 64, 64, 64]` |
| latent_dim | `50` |
| lr | `0.0001` |
| batch_size | `128` |
| n_iters | `50000` |
| n_inner_iters | `10` |
| optimizer | `Adam` |
| ae_emb_path | `./results/hvg_pearson_residuals_m1_ood/scgen/` |

## 4. Evaluations

| eval | R² | MMD | floor | ceiling | frac closed | mean JS |
|---|---|---|---|---|---|---|
| `evals_ood_data_space` | 0.9407 | 0.1375 | 0.0238 | 0.0902 | -0.7072 | 0.4653 |
| `evals_ood_latent_space` | 0.7187 | 0.0709 | — | — | — | — |

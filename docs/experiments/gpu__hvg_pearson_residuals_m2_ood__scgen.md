---
experiment_id: "gpu__hvg_pearson_residuals_m2_ood__scgen"
run_id: "gpu/hvg_pearson_residuals_m2_ood/scgen"
family: "scgen"
status: "done"
hvg_method: "pearson_residuals"
framing: "species"
source: "mouse"
target: "human"
holdout:
  - "CL:0000875"
  - "CL:0000576"
mode: "ood"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_m2_v07.h5ad"
eval_space: "data_space"
r2: 0.891568
mmd: 0.145818
mmd_floor: 0.0237219
mmd_ceiling: 0.0867197
frac_gap_closed: -0.942907
mean_js: 0.473615
tags:
  - "scgen"
  - "hvg/pearson_residuals"
  - "mode/ood"
  - "framing/species"
  - "data/v07"
---

# gpu/hvg_pearson_residuals_m2_ood/scgen

**scGen** · status `done` · holdout `CL:0000875, CL:0000576` · mode `ood`

**Sibling in this experiment:** [[gpu__hvg_pearson_residuals_m2_ood__impact_cellot]]

**Concepts this run touches:** [[scGen]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]] · [[MMD floor and ceiling]] · [[frac_gap_closed]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.8916 |
| MMD | 0.1458 |
| MMD floor / ceiling | 0.0237 / 0.0867 |
| frac_gap_closed | -0.9429 |
| mean per-gene JS | 0.4736 |
| n_cells present | 30, 50, 80 |

_Other evals on disk: `evals_ood_latent_space`._

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/hvg_pearson_residuals_m2_ood/scgen`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__hvg_pearson_residuals_m2_ood__scgen.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

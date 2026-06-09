---
experiment_id: "gpu__hvg_pearson_residuals_m1_v08_ood__impact_cellot"
run_id: "gpu/hvg_pearson_residuals_m1_v08_ood/impact_cellot"
family: "impact_cellot"
status: "done"
hvg_method: "pearson_residuals"
framing: "species"
source: "mouse"
target: "human"
holdout:
  - "CL:0000875"
mode: "ood"
data_version: "v08"
data_file: "datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_m1_v08.h5ad"
eval_space: "data_space"
r2: 0.918822
mmd: 0.103482
mmd_floor: 0.0236093
mmd_ceiling: 0.108747
frac_gap_closed: 0.0608088
mean_js: 0.449233
tags:
  - "impact_cellot"
  - "hvg/pearson_residuals"
  - "mode/ood"
  - "framing/species"
  - "data/v08"
---

# gpu/hvg_pearson_residuals_m1_v08_ood/impact_cellot

**IMPACT_CellOT** · status `done` · holdout `CL:0000875` · mode `ood`

**Sibling in this experiment:** [[gpu__hvg_pearson_residuals_m1_v08_ood__scgen]]

**Concepts this run touches:** [[IMPACT_CellOT]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]] · [[MMD floor and ceiling]] · [[frac_gap_closed]] · [[AE round-trip tax]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.9188 |
| MMD | 0.1035 |
| MMD floor / ceiling | 0.0236 / 0.1087 |
| frac_gap_closed | 0.0608 |
| mean per-gene JS | 0.4492 |
| n_cells present | 30, 50, 80 |

_Other evals on disk: `evals_ood_latent_space`._

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/hvg_pearson_residuals_m1_v08_ood/impact_cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__hvg_pearson_residuals_m1_v08_ood__impact_cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

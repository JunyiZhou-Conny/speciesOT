---
experiment_id: "gpu__hvg_pearson_residuals_a_iid__impact_cellot"
run_id: "gpu/hvg_pearson_residuals_a_iid/impact_cellot"
family: "impact_cellot"
status: "done"
hvg_method: "pearson_residuals"
framing: "species"
source: "mouse"
target: "human"
holdout:
  - "CL:0000625"
mode: "iid"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_a_v07.h5ad"
eval_space: "data_space"
r2: 0.75266
mmd: 0.0538793
tags:
  - "impact_cellot"
  - "hvg/pearson_residuals"
  - "mode/iid"
  - "framing/species"
  - "data/v07"
---

# gpu/hvg_pearson_residuals_a_iid/impact_cellot

**IMPACT_CellOT** · status `done` · holdout `CL:0000625` · mode `iid`

**Sibling in this experiment:** [[gpu__hvg_pearson_residuals_a_iid__scgen]]

**Concepts this run touches:** [[IMPACT_CellOT]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]] · [[AE round-trip tax]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.7527 |
| MMD | 0.0539 |
| n_cells present | 30, 50, 80 |

_Other evals on disk: `evals_ood_latent_space`._

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/hvg_pearson_residuals_a_iid/impact_cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__hvg_pearson_residuals_a_iid__impact_cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

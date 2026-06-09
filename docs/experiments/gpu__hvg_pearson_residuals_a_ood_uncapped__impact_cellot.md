---
experiment_id: "gpu__hvg_pearson_residuals_a_ood_uncapped__impact_cellot"
run_id: "gpu/hvg_pearson_residuals_a_ood_uncapped/impact_cellot"
family: "impact_cellot"
status: "done"
hvg_method: "pearson_residuals"
framing: "species"
source: "mouse"
target: "human"
holdout:
  - "CL:0000625"
mode: "ood"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_a_uncapped_v07.h5ad"
eval_space: "data_space"
r2: 0.847934
mmd: 0.051261
tags:
  - "impact_cellot"
  - "hvg/pearson_residuals"
  - "mode/ood"
  - "framing/species"
  - "data/v07"
---

# gpu/hvg_pearson_residuals_a_ood_uncapped/impact_cellot

**IMPACT_CellOT** · status `done` · holdout `CL:0000625` · mode `ood`

**Sibling in this experiment:** [[gpu__hvg_pearson_residuals_a_ood_uncapped__scgen]]

**Concepts this run touches:** [[IMPACT_CellOT]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]] · [[AE round-trip tax]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.8479 |
| MMD | 0.0513 |
| n_cells present | 30, 50, 80 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/hvg_pearson_residuals_a_ood_uncapped/impact_cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__hvg_pearson_residuals_a_ood_uncapped__impact_cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

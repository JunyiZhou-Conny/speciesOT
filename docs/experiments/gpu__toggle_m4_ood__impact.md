---
experiment_id: "gpu__toggle_m4_ood__impact"
run_id: "gpu/toggle_m4_ood/impact"
family: "impact_cellot"
status: "done"
framing: "species"
source: "mouse"
target: "human"
holdout:
  - "CL:0000860"
mode: "ood"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse/toggle_m4_holdout_v07.h5ad"
eval_space: "latent_space"
r2: 0.714206
mmd: 0.0506314
tags:
  - "impact_cellot"
  - "mode/ood"
  - "framing/species"
  - "data/v07"
---

# gpu/toggle_m4_ood/impact

**IMPACT_CellOT** · status `done` · holdout `CL:0000860` · mode `ood`

**Sibling in this experiment:** [[gpu__toggle_m4_ood__scgen]]

**Concepts this run touches:** [[IMPACT_CellOT]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]]

## Headline metrics — `evals_ood_latent_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.7142 |
| MMD | 0.0506 |
| n_cells present | 10, 20, 30 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/toggle_m4_ood/impact`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__toggle_m4_ood__impact.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

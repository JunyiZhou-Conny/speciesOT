---
experiment_id: "gpu__toggle_t1_ood__impact"
run_id: "gpu/toggle_t1_ood/impact"
family: "impact_cellot"
status: "done"
framing: "species"
source: "mouse"
target: "human"
holdout:
  - "CL:0000625"
mode: "ood"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse/toggle_t1_holdout_v07.h5ad"
eval_space: "latent_space"
r2: 0.840798
mmd: 0.0221101
tags:
  - "impact_cellot"
  - "mode/ood"
  - "framing/species"
  - "data/v07"
---

# gpu/toggle_t1_ood/impact

**IMPACT_CellOT** · status `done` · holdout `CL:0000625` · mode `ood`

**Sibling in this experiment:** [[gpu__toggle_t1_ood__scgen]]

**Concepts this run touches:** [[IMPACT_CellOT]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]]

## Headline metrics — `evals_ood_latent_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.8408 |
| MMD | 0.0221 |
| n_cells present | 25, 50, 80 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/toggle_t1_ood/impact`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__toggle_t1_ood__impact.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

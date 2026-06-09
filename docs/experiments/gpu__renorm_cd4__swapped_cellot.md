---
experiment_id: "gpu__renorm_cd4__swapped_cellot"
run_id: "gpu/renorm_cd4/swapped_cellot"
family: "impact_cellot"
status: "done"
framing: "species"
source: "mouse"
target: "human"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse-renorm/cd4_holdout_renorm_v07.h5ad"
eval_space: "latent_space"
r2: 0.815761
mmd: 0.0441892
tags:
  - "impact_cellot"
  - "framing/species"
  - "data/v07"
---

# gpu/renorm_cd4/swapped_cellot

**IMPACT_CellOT** · status `done`

**Sibling in this experiment:** [[gpu__renorm_cd4__scgen]]

**Concepts this run touches:** [[IMPACT_CellOT]] · [[assay filter]]

## Headline metrics — `evals_ood_latent_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.8158 |
| MMD | 0.0442 |
| n_cells present | 50, 80 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/renorm_cd4/swapped_cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__renorm_cd4__swapped_cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

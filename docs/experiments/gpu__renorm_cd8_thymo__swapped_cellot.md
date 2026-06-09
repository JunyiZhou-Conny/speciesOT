---
experiment_id: "gpu__renorm_cd8_thymo__swapped_cellot"
run_id: "gpu/renorm_cd8_thymo/swapped_cellot"
family: "impact_cellot"
status: "done"
framing: "species"
source: "mouse"
target: "human"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse-renorm/cd8_thymo_holdout_renorm_v07.h5ad"
eval_space: "latent_space"
r2: 0.746771
mmd: 0.0569793
tags:
  - "impact_cellot"
  - "framing/species"
  - "data/v07"
---

# gpu/renorm_cd8_thymo/swapped_cellot

**IMPACT_CellOT** · status `done`

**Sibling in this experiment:** [[gpu__renorm_cd8_thymo__scgen]]

**Concepts this run touches:** [[IMPACT_CellOT]] · [[assay filter]]

## Headline metrics — `evals_ood_latent_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.7468 |
| MMD | 0.0570 |
| n_cells present | 100 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/renorm_cd8_thymo/swapped_cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__renorm_cd8_thymo__swapped_cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

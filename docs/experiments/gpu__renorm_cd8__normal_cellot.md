---
experiment_id: "gpu__renorm_cd8__normal_cellot"
run_id: "gpu/renorm_cd8/normal_cellot"
family: "cellot_celltype"
status: "done"
framing: "cell_type"
source: "non_cd8"
target: "cd8"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse-renorm/cd8_holdout_swapped_renorm_v07.h5ad"
eval_space: "latent_space"
r2: 0.729899
mmd: 0.0859411
tags:
  - "cellot_celltype"
  - "framing/cell_type"
  - "data/v07"
---

# gpu/renorm_cd8/normal_cellot

**CellOT (cell-type framing, abandoned)** · status `done`

**Sibling in this experiment:** [[gpu__renorm_cd8__scgen]]

**Concepts this run touches:** [[CellOT cell-type framing]] · [[assay filter]]

## Headline metrics — `evals_ood_latent_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.7299 |
| MMD | 0.0859 |
| n_cells present | 100 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/renorm_cd8/normal_cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__renorm_cd8__normal_cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

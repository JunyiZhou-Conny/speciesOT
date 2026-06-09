---
experiment_id: "gpu__renorm_cd4__normal_cellot"
run_id: "gpu/renorm_cd4/normal_cellot"
family: "cellot_celltype"
status: "done"
framing: "cell_type"
source: "non_cd4"
target: "cd4"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse-renorm/cd4_holdout_swapped_renorm_v07.h5ad"
eval_space: "latent_space"
r2: 0.769434
mmd: 0.0567746
tags:
  - "cellot_celltype"
  - "framing/cell_type"
  - "data/v07"
---

# gpu/renorm_cd4/normal_cellot

**CellOT (cell-type framing, abandoned)** · status `done`

**Sibling in this experiment:** [[gpu__renorm_cd4__scgen]]

**Concepts this run touches:** [[CellOT cell-type framing]] · [[assay filter]]

## Headline metrics — `evals_ood_latent_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.7694 |
| MMD | 0.0568 |
| n_cells present | 50, 80 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/renorm_cd4/normal_cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__renorm_cd4__normal_cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

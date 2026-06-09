---
experiment_id: "gpu__speciesot_cd8__cellot"
run_id: "gpu/speciesot_cd8/cellot"
family: "cellot_celltype"
status: "done"
framing: "cell_type"
source: "non_cd8"
target: "cd8"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse/cd8_holdout_swapped_v07.h5ad"
eval_space: "data_space"
r2: 0.624143
mmd: 0.108981
tags:
  - "cellot_celltype"
  - "framing/cell_type"
  - "data/v07"
---

# gpu/speciesot_cd8/cellot

**CellOT (cell-type framing, abandoned)** · status `done`

**Concepts this run touches:** [[CellOT cell-type framing]] · [[assay filter]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.6241 |
| MMD | 0.1090 |
| n_cells present | 100 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/speciesot_cd8/cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__speciesot_cd8__cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

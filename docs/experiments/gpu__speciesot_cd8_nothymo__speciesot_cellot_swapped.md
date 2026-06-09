---
experiment_id: "gpu__speciesot_cd8_nothymo__speciesot_cellot_swapped"
run_id: "gpu/speciesot_cd8_nothymo/speciesot_cellot_swapped"
family: "cellot_celltype"
status: "done"
framing: "cell_type"
source: "non_cd8"
target: "cd8"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse/cd8_nothymo_holdout_swapped_v07.h5ad"
eval_space: "data_space"
r2: 0.558426
mmd: 0.112734
tags:
  - "cellot_celltype"
  - "framing/cell_type"
  - "data/v07"
---

# gpu/speciesot_cd8_nothymo/speciesot_cellot_swapped

**CellOT (cell-type framing, abandoned)** · status `done`

**Concepts this run touches:** [[CellOT cell-type framing]] · [[assay filter]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.5584 |
| MMD | 0.1127 |
| n_cells present | 100 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/speciesot_cd8_nothymo/speciesot_cellot_swapped`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__speciesot_cd8_nothymo__speciesot_cellot_swapped.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

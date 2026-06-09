---
experiment_id: "gpu__speciesot_cd4__speciesot_cellot_swapped"
run_id: "gpu/speciesot_cd4/speciesot_cellot_swapped"
family: "cellot_celltype"
status: "done"
framing: "cell_type"
source: "non_cd4"
target: "cd4"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse/cd4_holdout_swapped_v07.h5ad"
eval_space: "data_space"
r2: 0.572179
mmd: 0.120899
tags:
  - "cellot_celltype"
  - "framing/cell_type"
  - "data/v07"
---

# gpu/speciesot_cd4/speciesot_cellot_swapped

**CellOT (cell-type framing, abandoned)** · status `done`

**Concepts this run touches:** [[CellOT cell-type framing]] · [[assay filter]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.5722 |
| MMD | 0.1209 |
| n_cells present | 50, 80 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/speciesot_cd4/speciesot_cellot_swapped`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__speciesot_cd4__speciesot_cellot_swapped.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

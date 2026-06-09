---
experiment_id: "gpu__speciesot_tcell_subtypes__speciesot_cellot_swapped"
run_id: "gpu/speciesot_tcell_subtypes/speciesot_cellot_swapped"
family: "cellot_celltype"
status: "done"
framing: "cell_type"
source: "non_tcell_subtype"
target: "tcell_subtype"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse/tcell_subtypes_holdout_swapped_v07.h5ad"
eval_space: "data_space"
r2: 0.507379
mmd: 0.0525194
tags:
  - "cellot_celltype"
  - "framing/cell_type"
  - "data/v07"
---

# gpu/speciesot_tcell_subtypes/speciesot_cellot_swapped

**CellOT (cell-type framing, abandoned)** · status `done`

**Concepts this run touches:** [[CellOT cell-type framing]] · [[assay filter]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.5074 |
| MMD | 0.0525 |
| n_cells present | 100, 250, 500 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/speciesot_tcell_subtypes/speciesot_cellot_swapped`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__speciesot_tcell_subtypes__speciesot_cellot_swapped.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

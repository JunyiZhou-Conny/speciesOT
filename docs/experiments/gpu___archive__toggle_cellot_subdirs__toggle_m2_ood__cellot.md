---
experiment_id: "gpu___archive__toggle_cellot_subdirs__toggle_m2_ood__cellot"
run_id: "gpu/_archive/toggle_cellot_subdirs/toggle_m2_ood/cellot"
family: "cellot_celltype"
status: "done"
framing: "cell_type"
source: "non_nonclassical_generic_mono"
target: "nonclassical_generic_mono"
mode: "ood"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse/toggle_m2_holdout_swapped_v07.h5ad"
eval_space: "latent_space"
r2: 0.680338
mmd: 0.0900601
tags:
  - "cellot_celltype"
  - "mode/ood"
  - "framing/cell_type"
  - "data/v07"
---

# gpu/_archive/toggle_cellot_subdirs/toggle_m2_ood/cellot

**CellOT (cell-type framing, abandoned)** · status `done` · mode `ood`

**Concepts this run touches:** [[CellOT cell-type framing]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]]

## Headline metrics — `evals_ood_latent_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.6803 |
| MMD | 0.0901 |
| n_cells present | 100 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/_archive/toggle_cellot_subdirs/toggle_m2_ood/cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu___archive__toggle_cellot_subdirs__toggle_m2_ood__cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

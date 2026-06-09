---
experiment_id: "gpu___archive__toggle_cellot_subdirs__toggle_m3_ood__cellot"
run_id: "gpu/_archive/toggle_cellot_subdirs/toggle_m3_ood/cellot"
family: "cellot_celltype"
status: "done"
framing: "cell_type"
source: "non_mono_subtype"
target: "mono_subtype"
mode: "ood"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse/toggle_m3_holdout_swapped_v07.h5ad"
eval_space: "latent_space"
r2: 0.458104
mmd: 0.09705
tags:
  - "cellot_celltype"
  - "mode/ood"
  - "framing/cell_type"
  - "data/v07"
---

# gpu/_archive/toggle_cellot_subdirs/toggle_m3_ood/cellot

**CellOT (cell-type framing, abandoned)** · status `done` · mode `ood`

**Concepts this run touches:** [[CellOT cell-type framing]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]]

## Headline metrics — `evals_ood_latent_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.4581 |
| MMD | 0.0971 |
| n_cells present | 100, 250, 500 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/_archive/toggle_cellot_subdirs/toggle_m3_ood/cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu___archive__toggle_cellot_subdirs__toggle_m3_ood__cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

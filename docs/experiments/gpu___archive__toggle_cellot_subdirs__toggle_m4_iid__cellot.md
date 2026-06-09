---
experiment_id: "gpu___archive__toggle_cellot_subdirs__toggle_m4_iid__cellot"
run_id: "gpu/_archive/toggle_cellot_subdirs/toggle_m4_iid/cellot"
family: "cellot_celltype"
status: "done"
framing: "cell_type"
source: "non_classical_mono"
target: "classical_mono"
mode: "iid"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse/toggle_m4_holdout_swapped_v07.h5ad"
eval_space: "latent_space"
r2: 0.775973
mmd: 0.0578892
tags:
  - "cellot_celltype"
  - "mode/iid"
  - "framing/cell_type"
  - "data/v07"
---

# gpu/_archive/toggle_cellot_subdirs/toggle_m4_iid/cellot

**CellOT (cell-type framing, abandoned)** · status `done` · mode `iid`

**Concepts this run touches:** [[CellOT cell-type framing]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]]

## Headline metrics — `evals_ood_latent_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.7760 |
| MMD | 0.0579 |
| n_cells present | 10, 20, 30 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/_archive/toggle_cellot_subdirs/toggle_m4_iid/cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu___archive__toggle_cellot_subdirs__toggle_m4_iid__cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

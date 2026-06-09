---
experiment_id: "gpu__renorm_tcell_subtypes__normal_cellot"
run_id: "gpu/renorm_tcell_subtypes/normal_cellot"
family: "cellot_celltype"
status: "done"
framing: "cell_type"
source: "non_tcell_subtype"
target: "tcell_subtype"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse-renorm/tcell_subtypes_holdout_swapped_renorm_v07.h5ad"
eval_space: "latent_space"
r2: 0.484347
mmd: 0.0739244
tags:
  - "cellot_celltype"
  - "framing/cell_type"
  - "data/v07"
---

# gpu/renorm_tcell_subtypes/normal_cellot

**CellOT (cell-type framing, abandoned)** · status `done`

**Sibling in this experiment:** [[gpu__renorm_tcell_subtypes__scgen]]

**Concepts this run touches:** [[CellOT cell-type framing]] · [[assay filter]]

## Headline metrics — `evals_ood_latent_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.4843 |
| MMD | 0.0739 |
| n_cells present | 100, 250, 500 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/renorm_tcell_subtypes/normal_cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__renorm_tcell_subtypes__normal_cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

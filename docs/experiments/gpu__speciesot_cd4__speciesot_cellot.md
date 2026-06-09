---
experiment_id: "gpu__speciesot_cd4__speciesot_cellot"
run_id: "gpu/speciesot_cd4/speciesot_cellot"
family: "impact_cellot"
status: "done"
framing: "species"
source: "mouse"
target: "human"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse/cd4_holdout_v07.h5ad"
eval_space: "data_space"
r2: 0.597237
mmd: 0.0816769
tags:
  - "impact_cellot"
  - "framing/species"
  - "data/v07"
---

# gpu/speciesot_cd4/speciesot_cellot

**IMPACT_CellOT** · status `done`

**Concepts this run touches:** [[IMPACT_CellOT]] · [[assay filter]] · [[AE round-trip tax]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.5972 |
| MMD | 0.0817 |
| n_cells present | 50, 80 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/speciesot_cd4/speciesot_cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__speciesot_cd4__speciesot_cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

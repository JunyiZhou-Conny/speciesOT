---
experiment_id: "gpu__speciesot_cd8__impact_or"
run_id: "gpu/speciesot_cd8/impact_or"
family: "impact_cellot"
status: "done"
framing: "species"
source: "mouse"
target: "human"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse/cd8_holdout_v07.h5ad"
eval_space: "data_space"
r2: 0.685349
mmd: 0.0796755
tags:
  - "impact_cellot"
  - "framing/species"
  - "data/v07"
---

# gpu/speciesot_cd8/impact_or

**IMPACT_CellOT** · status `done`

**Concepts this run touches:** [[IMPACT_CellOT]] · [[assay filter]] · [[AE round-trip tax]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.6853 |
| MMD | 0.0797 |
| n_cells present | 100 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/speciesot_cd8/impact_or`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__speciesot_cd8__impact_or.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

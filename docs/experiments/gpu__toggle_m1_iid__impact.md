---
experiment_id: "gpu__toggle_m1_iid__impact"
run_id: "gpu/toggle_m1_iid/impact"
family: "impact_cellot"
status: "done"
framing: "species"
source: "mouse"
target: "human"
holdout:
  - "CL:0000875"
mode: "iid"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse/toggle_m1_holdout_v07.h5ad"
eval_space: "latent_space"
r2: 0.789886
mmd: 0.0317274
tags:
  - "impact_cellot"
  - "mode/iid"
  - "framing/species"
  - "data/v07"
---

# gpu/toggle_m1_iid/impact

**IMPACT_CellOT** · status `done` · holdout `CL:0000875` · mode `iid`

**Sibling in this experiment:** [[gpu__toggle_m1_iid__scgen]]

**Concepts this run touches:** [[IMPACT_CellOT]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]]

## Headline metrics — `evals_ood_latent_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.7899 |
| MMD | 0.0317 |
| n_cells present | 100 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/toggle_m1_iid/impact`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__toggle_m1_iid__impact.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

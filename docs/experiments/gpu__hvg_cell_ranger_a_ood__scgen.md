---
experiment_id: "gpu__hvg_cell_ranger_a_ood__scgen"
run_id: "gpu/hvg_cell_ranger_a_ood/scgen"
family: "scgen"
status: "done"
hvg_method: "cell_ranger"
framing: "species"
source: "mouse"
target: "human"
holdout:
  - "CL:0000625"
mode: "ood"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse-hvg/hvg_cell_ranger_a_v07.h5ad"
eval_space: "data_space"
r2: 0.834888
mmd: 0.128378
tags:
  - "scgen"
  - "hvg/cell_ranger"
  - "mode/ood"
  - "framing/species"
  - "data/v07"
---

# gpu/hvg_cell_ranger_a_ood/scgen

**scGen** · status `done` · holdout `CL:0000625` · mode `ood`

**Sibling in this experiment:** [[gpu__hvg_cell_ranger_a_ood__impact_cellot]]

**Concepts this run touches:** [[scGen]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.8349 |
| MMD | 0.1284 |
| n_cells present | 30, 50, 80 |

_Other evals on disk: `evals_ood_latent_space`._

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/hvg_cell_ranger_a_ood/scgen`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__hvg_cell_ranger_a_ood__scgen.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

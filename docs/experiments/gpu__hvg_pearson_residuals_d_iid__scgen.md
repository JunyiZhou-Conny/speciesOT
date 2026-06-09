---
experiment_id: "gpu__hvg_pearson_residuals_d_iid__scgen"
run_id: "gpu/hvg_pearson_residuals_d_iid/scgen"
family: "scgen"
status: "done"
hvg_method: "pearson_residuals"
framing: "species"
source: "mouse"
target: "human"
holdout:
  - "CL:0000624"
mode: "iid"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_d_v07.h5ad"
eval_space: "data_space"
r2: 0.877777
mmd: 0.121373
tags:
  - "scgen"
  - "hvg/pearson_residuals"
  - "mode/iid"
  - "framing/species"
  - "data/v07"
---

# gpu/hvg_pearson_residuals_d_iid/scgen

**scGen** · status `done` · holdout `CL:0000624` · mode `iid`

**Sibling in this experiment:** [[gpu__hvg_pearson_residuals_d_iid__impact_cellot]]

**Concepts this run touches:** [[scGen]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.8778 |
| MMD | 0.1214 |
| n_cells present | 20, 30, 40 |

_Other evals on disk: `evals_ood_latent_space`._

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/hvg_pearson_residuals_d_iid/scgen`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__hvg_pearson_residuals_d_iid__scgen.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

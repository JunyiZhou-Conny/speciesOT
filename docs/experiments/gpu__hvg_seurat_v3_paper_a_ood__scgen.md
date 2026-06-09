---
experiment_id: "gpu__hvg_seurat_v3_paper_a_ood__scgen"
run_id: "gpu/hvg_seurat_v3_paper_a_ood/scgen"
family: "scgen"
status: "done"
hvg_method: "seurat_v3_paper"
framing: "species"
source: "mouse"
target: "human"
holdout:
  - "CL:0000625"
mode: "ood"
data_version: "v07"
data_file: "datasets/speciesot-human-mouse-hvg/hvg_seurat_v3_paper_a_v07.h5ad"
eval_space: "data_space"
r2: 0.840119
mmd: 0.112004
tags:
  - "scgen"
  - "hvg/seurat_v3_paper"
  - "mode/ood"
  - "framing/species"
  - "data/v07"
---

# gpu/hvg_seurat_v3_paper_a_ood/scgen

**scGen** · status `done` · holdout `CL:0000625` · mode `ood`

**Sibling in this experiment:** [[gpu__hvg_seurat_v3_paper_a_ood__impact_cellot]]

**Concepts this run touches:** [[scGen]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.8401 |
| MMD | 0.1120 |
| n_cells present | 30, 50, 80 |

_Other evals on disk: `evals_ood_latent_space`._

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/hvg_seurat_v3_paper_a_ood/scgen`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__hvg_seurat_v3_paper_a_ood__scgen.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

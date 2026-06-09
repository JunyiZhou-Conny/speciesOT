---
experiment_id: "gpu__hvg_seurat_v3_paper_a_ood__impact_cellot"
run_id: "gpu/hvg_seurat_v3_paper_a_ood/impact_cellot"
family: "impact_cellot"
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
r2: 0.772622
mmd: 0.0562311
tags:
  - "impact_cellot"
  - "hvg/seurat_v3_paper"
  - "mode/ood"
  - "framing/species"
  - "data/v07"
---

# gpu/hvg_seurat_v3_paper_a_ood/impact_cellot

**IMPACT_CellOT** · status `done` · holdout `CL:0000625` · mode `ood`

**Sibling in this experiment:** [[gpu__hvg_seurat_v3_paper_a_ood__scgen]]

**Concepts this run touches:** [[IMPACT_CellOT]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]] · [[AE round-trip tax]]

## Headline metrics — `evals_ood_data_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.7726 |
| MMD | 0.0562 |
| n_cells present | 30, 50, 80 |

_Other evals on disk: `evals_ood_latent_space`._

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/hvg_seurat_v3_paper_a_ood/impact_cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__hvg_seurat_v3_paper_a_ood__impact_cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

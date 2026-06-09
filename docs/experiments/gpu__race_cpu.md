---
experiment_id: "gpu__race_cpu"
run_id: "gpu/race_cpu"
family: "cellot_legacy"
status: "done"
framing: "legacy"
source: "unst"
target: "LPS6"
mode: "ood"
data_file: "datasets/scrna-crossspecies/hvg-top1k-train-only.h5ad"
eval_space: "latent_space"
r2: 0.715208
mmd: 0.215857
tags:
  - "cellot_legacy"
  - "mode/ood"
  - "framing/legacy"
---

# gpu/race_cpu

**CellOT (legacy crossspecies)** · status `done` · mode `ood`

**Concepts this run touches:** [[CellOT legacy crossspecies]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]]

## Headline metrics — `evals_ood_latent_space`

| Metric | Value |
|---|---|
| R² (means, squared) | 0.7152 |
| MMD | 0.2159 |
| n_cells present | 100, 250, 500, 1000, 1500 |

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/race_cpu`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__race_cpu.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

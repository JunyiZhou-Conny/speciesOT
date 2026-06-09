---
experiment_id: "gpu__speciesot_cpu__speciesot_cellot"
run_id: "gpu/speciesot_cpu/speciesot_cellot"
family: "impact_cellot"
status: "done"
framing: "species"
source: "human"
target: "mouse"
holdout:
  - "CL:0000084"
mode: "ood"
data_file: "datasets/speciesot-human-mouse/hvg-top1k.h5ad"
tags:
  - "impact_cellot"
  - "mode/ood"
  - "framing/species"
---

# gpu/speciesot_cpu/speciesot_cellot

**IMPACT_CellOT** · status `done` · holdout `CL:0000084` · mode `ood`

**Concepts this run touches:** [[IMPACT_CellOT]] · [[assay filter]] · [[OOD vs IID evaluation]] · [[OOD split stratification]]

_No evaluations on disk yet._

## On-disk references (HPC)

- Model dir: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/speciesot_cpu/speciesot_cellot`
- Rich card (figures, HPC-only): `docs/model_cards/gpu__speciesot_cpu__speciesot_cellot.md`
- Regenerate this note: `./hub vault`

---
See also: [[Hub Experiments MOC]] · [[conceptual_framework]]

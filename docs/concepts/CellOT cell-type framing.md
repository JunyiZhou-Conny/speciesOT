---
title: CellOT cell-type framing
type: concept
tags:
  - concept
  - model
  - abandoned
source_doc: "conceptual_framework.md §1.2, §2.1"
---

# CellOT (cell-type framing) — abandoned

An early framing: source = non-CD8 cells, target = CD8 T cells, condition = cell type.
The OOD test held out **species** (train non-CD8→CD8 on mouse, test on human). **Dead.**

## Why abandoned

1. **Size imbalance.** Non-CD8 vastly outnumbers CD8; an ICNN *deterministic* map forces
   a many-to-one squash from the large source onto the small target — mathematically fine,
   biologically meaningless ("this monocyte becomes that CD8 cell" isn't how identity
   works). See also OT-doesn't-need-equal-sizes (§5.1).
2. **No coherent biological question.** "Other cell types" aren't a control version of
   CD8 — cell types aren't perturbations of each other. And it conflated two
   generalization axes (cell-type transform *and* cross-species transfer).

## On-disk fossils (all stale)

`results/toggle_*/cellot/`, configs with `datasplit.key: species` /
`holdout: 'human'`, paths containing `_holdout_swapped_v07.h5ad`. Catalogued by the hub
as family `cellot_celltype` so you can still inspect them — ignore for new work.

## Related

- The framing that replaced it: [[IMPACT_CellOT]]
- Overview: [[the three model variants]]
- The other dead branch: [[CellOT legacy crossspecies]]

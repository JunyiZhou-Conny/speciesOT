---
title: the three model variants
type: concept
tags:
  - concept
  - overview
source_doc: "conceptual_framework.md §1"
---

# the three model variants

One architecture (CellOT's ICNN-parameterized OT), three jobs — distinguished **only**
by what plays source vs target:

| Framing | Source → Target | Models | Status |
|---|---|---|---|
| CellOT (paper-original) | control → drug-treated | a **drug effect** | never run here (no drug data) |
| CellOT (cell-type) | non-CD8 → CD8 | a **cell-type effect** | **abandoned** (size imbalance, no coherent biology) |
| [[IMPACT_CellOT]] | mouse → human | a **species effect** | **current main task** |

Plus one baseline that isn't OT at all: [[scGen]] (a VAE with an additive latent shift).

The cell-type framing is dead: non-CD8 vastly outnumbers CD8, forcing a many-to-one
squash that isn't biologically meaningful, and "other cell types" aren't a "control"
version of CD8. On-disk fossils (`toggle_*/cellot/`, `datasplit.key: species`) are stale.

## Why naming matters even though the math is identical

Same ICNN loop, different *claim* and different *generalization axis*. Saying "we used
CellOT" implies drug perturbation; "IMPACT_CellOT" signals the species adaptation. See
[[OOD vs IID evaluation]] for the axis overload.

## Related

- The endgame that needs both a drug-transport and a species-transport: [[the four-corner goal]]
- Browse runs by family: [[Hub Experiments MOC]]

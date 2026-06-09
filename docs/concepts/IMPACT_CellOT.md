---
title: IMPACT_CellOT
type: concept
tags:
  - concept
  - model
source_doc: "conceptual_framework.md §1.3, §2"
---

# IMPACT_CellOT

The project's **main model**: Bunne et al. 2023's CellOT (an optimal-transport map
parameterized by Input Convex Neural Networks) re-pointed at a **species** question.

|  |  |
|---|---|
| Source cloud | **mouse** cells |
| Target cloud | **human** cells |
| Condition | species (mouse vs human) |
| Generalization axis | held-out **cell type** (train on most types, test on an unseen one) |

The architecture is *identical* to paper-original CellOT (which models a drug effect,
source = control, target = drug-treated). Only the biological claim changes, so the
name changes: `IMPACT_` signals "this is the species framing, not the drug framing."
See [[the three model variants]].

## Why it's not just "CellOT"

- Different biological claim: a *species* effect is a billion years of evolution, not a
  chemist's intervention.
- Different generalization axis: paper-CellOT generalizes across *cells* within a fixed
  perturbation; IMPACT generalizes across *cell types* within a fixed mouse→human
  direction. "OOD" means different things — see [[OOD vs IID evaluation]].

## How it's evaluated

IMPACT operates in a **50-d autoencoder latent space** (the AE is its scGen sibling).
Data-space evaluation must decode 50-d → 1000-d, which costs the [[AE round-trip tax]]
and distorts the raw [[MMD floor and ceiling]] frame (→ misleading [[frac_gap_closed]]
until decoded-space references land). Judge it by `gap_above_floor` / `frac_gap_closed`
(MMD) and `frac_r2_closed` (means), not raw R²/MMD.

## Related

- Baseline it must beat: [[scGen]]
- The endgame it's a building block for: [[the four-corner goal]]
- Data treatment it depends on: [[assay filter]]
- Split subtlety: [[OOD split stratification]]
- Browse all IMPACT runs: [[Hub Experiments MOC]]

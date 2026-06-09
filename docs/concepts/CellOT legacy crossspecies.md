---
title: CellOT legacy crossspecies
type: concept
tags:
  - concept
  - model
  - legacy
source_doc: "conceptual_framework.md §2.1"
---

# CellOT (legacy crossspecies)

The earliest direct-CellOT runs: mouse→human optimal transport in **raw 1000-dim
ortholog space**, with **no [[scGen]] autoencoder** in the loop. The hub catalogs these
as family `cellot_legacy` (top-level `cross_species_ood/` and `race_*/` dirs).

## How it differs from current [[IMPACT_CellOT]]

| | legacy crossspecies | current IMPACT |
|---|---|---|
| Space | raw 1000-d HVG | 50-d scGen AE latent |
| AE sibling | none | `scgen/` + `model-scgen` symlink |
| Status | superseded | active |

Because there's no autoencoder, legacy runs don't pay the [[AE round-trip tax]] — but
they also lose the smoothing/denoising the latent space provides, and predate the
floor/ceiling metric framework.

## Status

Superseded by the AE-based IMPACT pipeline. Kept in the catalog for provenance; not part
of the current matrix.

## Related

- The current model: [[IMPACT_CellOT]]
- Overview: [[the three model variants]]
- The other dead branch: [[CellOT cell-type framing]]

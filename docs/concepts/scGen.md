---
title: scGen
type: concept
tags:
  - concept
  - model
source_doc: "conceptual_framework.md §1.4"
---

# scGen

The **baseline** (Lotfollahi et al.) and, simultaneously, the **autoencoder that
[[IMPACT_CellOT]] transports inside**. A CellOT experiment dir always has a `scgen/`
sibling + a `model-scgen` symlink — that's the contract that lets IMPACT find its AE.

## How it predicts

A VAE. It computes a single shift vector `δ = mean(latent_target) − mean(latent_source)`
on training cells, then for a new source cell returns `decode(encode(cell) + δ)`.

## The criticism (your mentor's)

scGen is **linear / additive**: it applies the *same* shift to every cell. If the
species effect behaves differently for monocytes vs T cells (it almost certainly does),
scGen can't capture that — [[IMPACT_CellOT]]'s nonlinear map can.

## Why keep it

A fair bar. If nonlinear OT can't beat a fixed additive shift on our data, the extra
machinery isn't earning its keep. In practice IMPACT beats scGen on most cells, but the
margin varies by HVG flavor and holdout — and scGen often **overshoots distributionally**
(good mean, wrong spread; see [[MMD floor and ceiling]]).

## The AE double-duty has consequences

Because scGen *is* IMPACT's AE, scGen's reconstruction quality sets the floor on what
IMPACT can achieve in decoded gene space — the [[AE round-trip tax]].

## Related

- The model it benchmarks: [[IMPACT_CellOT]]
- Overview: [[the three model variants]]
- Browse all scGen runs: [[Hub Experiments MOC]]

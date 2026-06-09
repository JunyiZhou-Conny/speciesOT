---
title: MMD floor and ceiling
type: concept
tags:
  - concept
  - metric
source_doc: "conceptual_framework.md §5.9"
---

# MMD floor and ceiling

Raw MMD (a two-sample distance between the real human cloud and the model's predicted
cloud, in 1000-d gene space, averaged over 50 RBF bandwidths) is **meaningless without a
reference frame** — even a perfect resample of real cells gets MMD > 0 from finite-sample
bias, and the value isn't comparable across `ncells`. So we bracket it:

| Reference | What it is | Computed as |
|---|---|---|
| **floor** | best achievable at this `ncells` | self-MMD of the real target, split-half |
| **ceiling** | the no-transport / identity gap | MMD(mouse control, real human) |

On the MMD axis (lower = better):

```
floor  ◄──── the model should move this way ────►  ceiling
(perfect resample)                          (raw mouse vs human, no transport)
```

Two derived headline numbers (in `extended_metrics.csv`):

- **`gap_above_floor` = model − floor** — the error that *isn't* sampling noise. Flat
  across `ncells` when the estimator works; this is the cross-model comparison number.
- **[[frac_gap_closed]] = (ceiling − model) / (ceiling − floor)** — fraction of the
  identity→floor gap the model closed.

## The gamma asymmetry (why we average 50 bandwidths)

The discriminative signal lives in the *middle* bandwidth. High γ → MMD → 2/n (blind,
diagonal-only); low γ → MMD → 0 (everything looks alike). M2 OOD peaks near γ≈0.005–0.007.

## The catch for AE models

For [[IMPACT_CellOT]], `model` is measured on **decoded** clouds but floor/ceiling on
**raw** clouds — the [[AE round-trip tax]] makes raw `frac_gap_closed` go spuriously
negative. Use decoded-space references, or fall back to `frac_r2_closed`.

## Related

- The fraction metric: [[frac_gap_closed]]
- The AE distortion: [[AE round-trip tax]]
- Why we keep MMD *and* R²: MMD sees the full distribution; R² only the mean.
- Runs with these metrics: [[Hub Experiments MOC]]

---
title: frac_gap_closed
type: concept
tags:
  - concept
  - metric
source_doc: "conceptual_framework.md §5.9"
---

# frac_gap_closed

The **headline MMD metric**. Fraction of the identity→floor gap the model closed:

```
frac_gap_closed = (mmd_ceiling − mmd_model) / (mmd_ceiling − mmd_floor)
```

(See [[MMD floor and ceiling]] for the two references.)

- **1.0** = reached the floor (best possible at this `ncells`).
- **0.0** = no better than identity (mouse-as-is).
- **negative** = *worse* than identity — the transport overshot, landing farther from
  human than untransported mouse.

Use this (and `gap_above_floor`) as the comparison metric, **not raw MMD** — it's the
rule in `AGENTS.md` and the v08 scorecard.

## The trap on IMPACT runs

For [[IMPACT_CellOT]], `mmd_model` is on **decoded** clouds while floor/ceiling are on
**raw** clouds. The [[AE round-trip tax]] (~0.083 for m1 v08) pushes the decoded model
above the *raw* ceiling → **spuriously negative** `frac_gap_closed`, even when transport
helps. In honest **decoded-space** references, m1 v08 IMPACT closes ~91%.

> **Rule of thumb:** a negative `frac_gap_closed` on an IMPACT run is *suspect*, not
> damning, until decoded-space references land. Cross-check `frac_r2_closed` (mean-based,
> AE-robust). E.g. M2 v08 IMPACT: `frac_r2_closed ≈ 0.85` while raw `frac_gap_closed ≈ −0.13`.

## Why it revealed a real win

The v08 cut ([[assay filter]] + [[OOD split stratification]]) moved m1 IMPACT
`frac_gap_closed` from **−0.71 → +0.06** — a genuine improvement raw R²/MMD had hidden.
That's *why this metric exists*.

## Related

- The reference frame: [[MMD floor and ceiling]]
- The distortion to watch: [[AE round-trip tax]]
- The data cut that moved it: [[assay filter]]

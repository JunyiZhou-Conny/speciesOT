---
title: hub metrics
type: hub-command
tags:
  - hub
---

# `./hub metrics <run_id>`

Writes the `extended_metrics.csv` sidecar next to a run's `evals.csv` — the floor/ceiling
framework that turns raw MMD/R² into honest headline numbers.

```bash
./hub metrics hvg_pearson_residuals_m1_v08_ood/impact_cellot
```

## What it computes

- **MMD** [[MMD floor and ceiling]]: `mmd_floor` (self-MMD split-half), `mmd_ceiling`
  (mouse vs human, no transport), `gap_above_floor`, [[frac_gap_closed]].
- **R² analog**: `r2_self`, `r2_identity`, `frac_r2_closed` (mean-based, AE-robust).
- **`mean_js`**: per-gene Jensen-Shannon divergence (the marginal view).

Under the hood: `dump_eval_clouds.py` caches `treated/imputed/control` to
`eval_clouds.npz`; `extended_metrics.py` recomputes from that (no torch reload). The
catalog then surfaces these in `show` / `compare` / [[hub vault]].

## Read the output with care

For [[IMPACT_CellOT]], raw `frac_gap_closed` is distorted by the [[AE round-trip tax]] —
cross-check `frac_r2_closed`. **TODO:** add decoded-space references so the sidecar is
honest by default.

## Next / related

- Feeds: [[hub vault]] (frontmatter metrics), [[hub show]], [[hub compare]]
- Back to: [[Hub Operations MOC]]

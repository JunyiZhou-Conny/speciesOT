---
title: hub compare
type: hub-command
tags:
  - hub
---

# `./hub compare A B`

Side-by-side diff of two runs: **spec differences (the cause)** + **metric differences
(the effect)**, with identical fields collapsed at the bottom so the deltas are the focus.

```bash
./hub compare hvg_pearson_residuals_m2_ood/impact_cellot \
              hvg_seurat_v3_m2_ood/impact_cellot
./hub compare A B --out compare.md
```

Example payoff: "only `hvg_method` differs; pearson wins in data_space (R² 0.93 vs 0.90)
but seurat_v3 wins in latent_space" — instantly isolating which knob moved which metric.

## Use it to

- Sanity-check a v07 → v08 change ([[assay filter]] + [[OOD split stratification]]).
- Confirm [[IMPACT_CellOT]] vs its [[scGen]] sibling on the same cell.
- Read [[frac_gap_closed]] deltas (shown when the sidecar exists — see [[hub metrics]]).

## Related

- [[hub list]] · [[hub show]] · back to [[Hub Operations MOC]]

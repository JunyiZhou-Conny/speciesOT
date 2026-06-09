---
title: hub show
type: hub-command
tags:
  - hub
---

# `./hub show <run_id>`

Full detail for one run: identity, data provenance, framing, holdout, architecture,
lineage, and every evaluation (with floor/ceiling + [[frac_gap_closed]] when the
[[hub metrics]] sidecar exists). Accepts the unique suffix, so you can drop the `gpu/`
prefix.

```bash
./hub show hvg_seurat_d_ood/impact_cellot
./hub show hvg_pearson_residuals_m2_iid/impact_cellot
```

> The Obsidian equivalent is the run's note in `experiments/` — same data, but clickable
> into the [[IMPACT_CellOT]]/[[scGen]] sibling and the concepts it touches.

## Related

- Browse: [[hub list]] · diff: [[hub compare]] · graph: [[Hub Experiments MOC]]
- Back to [[Hub Operations MOC]]

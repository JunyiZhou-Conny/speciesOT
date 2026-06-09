---
title: hub list
type: hub-command
tags:
  - hub
---

# `./hub list`

The catalog browser. Walks `cellot/cellot_gpu/results/` + `speciesOT/baseline/results/`,
catalogs every dir with a `config.yaml` (≈175 runs across 4 families), and prints a
filterable/sortable table.

```bash
./hub list
./hub list --filter family=impact_cellot
./hub list --filter hvg_method=pearson_residuals --filter status=done
./hub list --sort hvg_method                  # or --sort run_id --desc
./hub list --filter family=impact_cellot | wc -l   # quick counts
```

Filterable fields: `family`, `hvg_method`, `status`, `framing`, `normalization`,
`data_source`, `train_includes_holdout`, `datasplit_strategy`, `model_name`,
`latent_dim`, `n_iters`, `batch_size`, …

> In Obsidian, the same browsing is the [[Hub Experiments MOC]] (Dataview tables) — the
> graph is the visual version of `./hub list`.

## Related

- Drill into one: [[hub show]] · diff two: [[hub compare]]
- Back to [[Hub Operations MOC]]

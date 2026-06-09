---
title: hub spec
type: hub-command
tags:
  - hub
  - gotcha
---

# `./hub spec dump <run_id>`

Bootstraps a YAML spec from a trained run's `config.yaml` (+ filename heuristics +
sibling). The starting point for a new experiment: dump, copy, edit a few fields, then
[[hub prep]] → [[hub generate]].

```bash
./hub spec dump hvg_pearson_residuals_m2_ood/impact_cellot --out specs/m2_baseline.yaml
cp specs/m2_baseline.yaml specs/m1_modern.yaml      # then edit tag, data_file, holdout
```

## ⚠ It is lossy — the key gotcha

`spec dump` reconstructs from `config.yaml`, **not** from any YAML. Fields *not* in
config.yaml fall back to **defaults**: `assay_filter`, `cap_cells_per_type`,
`source_datasets`, `ortholog_source`, `datasplit_stratify`, `impact_train_device`,
`random_state`, `test_size`, `notes`.

> **So when those "intent" fields matter, clone the spec *file* (`cp specs/...`) rather
> than re-dumping.** `specs/*.yaml` are the source of truth, not the dumped config.

This matters directly for [[assay filter]] and [[OOD split stratification]] — both are
intent fields a dump won't recover.

## Related

- Then: [[hub prep]] → [[hub generate]]
- Back to [[Hub Operations MOC]]

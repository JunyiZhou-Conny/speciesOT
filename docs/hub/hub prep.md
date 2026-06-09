---
title: hub prep
type: hub-command
tags:
  - hub
---

# `./hub prep <spec.yaml>`

Builds the training `.h5ad` named by the spec's `data_file`. A faithful port of notebook
`01.5` — no more hand-editing a `GROUPS` dict and run-all.

```bash
./hub prep specs/m1_modern.yaml             # build
./hub prep specs/m1_modern.yaml --force     # overwrite existing
```

## What it does (step by step)

1. Load `source_datasets.{mouse,human}`, promote `.raw` → `.X` (recover UMI counts).
2. **Enforce the [[assay filter]]** — keep one droplet platform per species, drop
   Smart-seq2 etc. *before* ortholog matching / HVG.
3. Ortholog-align mouse↔human (cached BioMart table).
4. Match cells by `(cell_type, tissue)` with the spec's `random_state`.
5. Snapshot counts → `.layers['counts']`, set `.X = log1p(normalize_total(counts, 1e4))`.
6. Select top `hvg_n_top` HVG with `hvg_method` on **non-holdout** cells.
7. Subset to HVG (keeping holdout cells — split at train time), round-trip through
   anndata 0.7.

## Two-env dance

Needs `scanpy ≥ 1.12` (Pearson residuals) → shells out to the **analysis** env, then back
to **CellOT** for the anndata-0.7 round-trip. Override interpreters with
`SPECIESOT_ANALYSIS_PY` / `SPECIESOT_CELLOT_PY`.

## Gotchas

- Refuses to overwrite an existing `.h5ad` without `--force`.
- The **43 GB full atlas** must use the backed path (`source_backed: true`,
  `prep_backed.py`) as a high-mem batch job — never full-load on the login node.

## Next / related

- Then: [[hub generate]] → submit → [[hub metrics]]
- Concept it enforces: [[assay filter]] · [[OOD split stratification]]
- Back to: [[Hub Operations MOC]]

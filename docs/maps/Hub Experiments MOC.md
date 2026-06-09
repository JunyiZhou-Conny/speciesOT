---
title: Hub Experiments MOC
type: moc
tags:
  - moc
---

# Hub Experiments MOC

The live dashboard over every run the hub catalogs. The tables below are
**[[Dataview]]** queries — install the Dataview community plugin (see
[[obsidian_setup]] §4) and they render as sortable tables that refresh whenever you
`./hub vault` + `git pull`. Without Dataview you'll see the raw code blocks; the static
fallback is [[_experiments_index]].

> Notes in `experiments/` are **auto-generated** — don't hand-edit them. Write prose in
> [[Concepts MOC|concepts]] and link out to runs.

## IMPACT_CellOT — by mean accuracy

```dataview
TABLE r2 AS "R²", mmd AS "MMD", frac_gap_closed AS "frac_gap", mode, hvg_method AS "HVG", status
FROM "experiments"
WHERE family = "impact_cellot" AND r2 != null
SORT r2 DESC
```

## Suspicious: negative frac_gap_closed (mostly the AE round-trip artifact)

See [[AE round-trip tax]] / [[frac_gap_closed]] before trusting these as "overshoot".

```dataview
TABLE r2 AS "R²", mmd AS "MMD", frac_gap_closed AS "frac_gap", family
FROM "experiments"
WHERE frac_gap_closed != null AND frac_gap_closed < 0
SORT frac_gap_closed ASC
```

## scGen baselines

```dataview
TABLE r2 AS "R²", mmd AS "MMD", mode, hvg_method AS "HVG", status
FROM "experiments"
WHERE family = "scgen" AND r2 != null
SORT r2 DESC
```

## The v08 cut (assay filter + stratified split)

```dataview
TABLE family, r2 AS "R²", frac_gap_closed AS "frac_gap", mode
FROM "experiments"
WHERE data_version = "v08"
SORT run_id ASC
```

## Counts by family

```dataview
TABLE length(rows) AS "count"
FROM "experiments"
WHERE family != null
GROUP BY family
```

## See also

- The science behind the metrics: [[MMD floor and ceiling]] · [[frac_gap_closed]] · [[AE round-trip tax]]
- How runs are produced: [[Hub Operations MOC]]
- The concept web: [[Concepts MOC]]

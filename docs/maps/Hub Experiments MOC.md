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

## Leaderboard — by NORTH-STAR (frac_gap_closed_decoded)

The headline ranking. `frac_gap_closed_decoded` is the AE-honest metric (all clouds
round-tripped through the scGen AE); it is what `./hub scorecard` sorts on and the
answer to "are we improving?". The old raw `frac_gap_closed` flips sign for measurement
reasons — see [[AE round-trip tax]] / [[frac_gap_closed]].

```dataview
TABLE frac_gap_closed_decoded AS "fgc_dec", frac_r2_closed_decoded AS "fr2_dec", r2 AS "R²", mean_js AS "JS", family, mode, status
FROM "experiments"
WHERE frac_gap_closed_decoded != null
SORT frac_gap_closed_decoded DESC
```

## IMPACT_CellOT — by north-star

```dataview
TABLE frac_gap_closed_decoded AS "fgc_dec", frac_r2_closed_decoded AS "fr2_dec", r2 AS "R²", mmd AS "MMD", mode, hvg_method AS "HVG", status
FROM "experiments"
WHERE family = "impact_cellot" AND frac_gap_closed_decoded != null
SORT frac_gap_closed_decoded DESC
```

## scGen baselines — by north-star

```dataview
TABLE frac_gap_closed_decoded AS "fgc_dec", frac_r2_closed_decoded AS "fr2_dec", r2 AS "R²", mmd AS "MMD", mode, hvg_method AS "HVG", status
FROM "experiments"
WHERE family = "scgen" AND frac_gap_closed_decoded != null
SORT frac_gap_closed_decoded DESC
```

## Raw-frame frac_gap_closed (DIAGNOSTIC ONLY — do not rank on this)

The raw-frame metric is kept only to show the measurement artifact. Negative values
here are usually the AE round-trip tax, NOT overshoot. Judge on the decoded leaderboard
above. See [[AE round-trip tax]].

```dataview
TABLE frac_gap_closed_raw AS "fgc_raw", frac_gap_closed_decoded AS "fgc_dec", family
FROM "experiments"
WHERE frac_gap_closed_raw != null AND frac_gap_closed_raw < 0
SORT frac_gap_closed_raw ASC
```

## The v08 cut (assay filter + stratified split)

```dataview
TABLE family, r2 AS "R²", frac_gap_closed_decoded AS "fgc_dec", frac_r2_closed_decoded AS "fr2_dec", mode
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

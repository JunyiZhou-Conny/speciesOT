---
title: assay filter
type: concept
tags:
  - concept
  - preprocessing
  - enforced
source_doc: "conceptual_framework.md §5.10"
---

# assay filter

An **enforced** preprocessing treatment (not optional metadata): keep exactly one
droplet platform per species and drop everything else.

- mouse → `10x 3' v2` (`EFO:0009899`)
- human → `10x 3' v3` (`EFO:0009922`)

## Why it exists

The atlas `_v07` datasets **mix sequencing platforms within each species**. Smart-seq2
(plate-based, full-length, no UMIs) has a fundamentally different expression distribution
from 10x droplet 3'. Investigation of the M1 held-out monocytes (notebook 21) found:
**~77% of the "scattered" cells were Smart-seq2**, and the one fully-detached UMAP cluster
was 100% Smart-seq2. The apparent "donor effect" was a proxy — those donors just had more
Smart-seq2. So the heterogeneity inflating M1's MMD was a **preprocessing artifact, not
biology**.

## Where it's enforced

`speciesOT/hub/prep.py:_apply_assay_filter` (and `prep_backed.py`), applied right after
the source files load, **before** ortholog matching / HVG. Recorded in
`ExperimentSpec.assay_filter` (defaults to the values above). Previously recorded-as-intent
but never applied — that gap is now closed. An empty filter skips with a loud warning.

## Why it matters for results

Part of the **v08 cut**. Dropping Smart-seq2 *raised* the [[MMD floor and ceiling]]
ceiling (un-masked the true cross-species gap) and moved m1 IMPACT
[[frac_gap_closed]] from −0.71 → +0.06. Datasets built before enforcement (`_v07`) still
contain Smart-seq2; applying the treatment needs a `./hub prep` rebuild (`_v08`).

## Related

- Its partner in the v08 cut: [[OOD split stratification]]
- The metric it moved: [[frac_gap_closed]]
- Where prep runs: [[hub prep]]

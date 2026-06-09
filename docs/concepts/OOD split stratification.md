---
title: OOD split stratification
type: concept
tags:
  - concept
  - preprocessing
  - gotcha
source_doc: "conceptual_framework.md §5.7"
---

# OOD split stratification

The 50/50 ignore/ood split of the holdout pool was **unstratified by species**, so the
species counts drift apart (M2: 261 mouse / 248 human in OOD, mirror in IGNORE) even
though the upstream matching guarantees exactly 509/509.

## Where

Two layers split; only one stratified:

| Layer | Function | Stratified by species? |
|---|---|---|
| 80/20 train/test | `split_cell_data_train_test` | **yes** (loops over groups) |
| 50/50 ignore/ood | `split_cell_data_toggle_ood` | **no** (single `train_test_split`) |

`sklearn`'s `train_test_split` without `stratify=` just shuffles and slices — no concept
of `condition`. Expected 254.5 mouse; observed 261 is normal sampling variance (~0.6 SD).

## Does it bite?

**Not the current metrics.** R²-of-means and MMD are *two-sample* statistics that
estimate each side's population independently — per-cell pairing isn't required, and the
imbalance only nudges the noise floor (~1.2%). It *would* bite per-cell paired error,
donor-matched comparisons, or figure caption counts ("n=261 mouse vs n=248 human").

## The fix (now opt-in)

`cell.py:split_cell_data_toggle_ood` takes `stratify=`; the spec field
`datasplit_stratify: condition` turns it on. Applied as part of the v08 cut (so direct
comparison to the unstratified matrix is intentionally broken — different cells land in
OOD vs IGNORE).

## Related

- Its partner in the v08 cut: [[assay filter]]
- The OOD-word overload: [[OOD vs IID evaluation]]
- The result it helped move: [[frac_gap_closed]]

---
title: OOD vs IID evaluation
type: concept
tags:
  - concept
  - evaluation
  - gotcha
source_doc: "conceptual_framework.md §5.4"
---

# OOD vs IID evaluation

"OOD" is overloaded — it means two different things in two places, and an "IID-mode
sbatch that calls `--setting ood`" looks like a bug but isn't.

| Term | Lives in | Means |
|---|---|---|
| **`mode`** (`iid`/`ood`) | config + results dir names (`..._m2_ood/`) | **what data trained** the model. `ood`: the held-out cell type was fully excluded. `iid`: the "ignored" half was added back in. |
| **`--setting`** (`iid`/`ood`) | `evaluate.py` CLI flag | **which slice to evaluate**. We **always** use `--setting ood` (the held-out cell type, test half). |

So:

- **IID-trained + setting ood** = model saw similar cells in training → near in-sample
  fit → an upper bound.
- **OOD-trained + setting ood** = model never saw any of the held-out type → true
  generalization.

The difference between them is roughly the **generalization gap**.

## What the current matrix doesn't tell us (§5.8)

We never surface a within-distribution (`--setting iid`) R² anchor, so "OOD R² = 0.86"
has no baseline — we can't say how much of the 14% gap is OOD-specific vs intrinsic. A
cheap fix (add `--setting iid` evals, no retraining) is filed.

## The other overloaded axis

The 50/50 holdout split (ignore vs ood) is a *different* axis from source/target — see
[[OOD split stratification]].

## Related

- The split-balance issue: [[OOD split stratification]]
- The model under test: [[IMPACT_CellOT]]

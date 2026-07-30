"""Correctness guards for the synthetic mechanism proof.

Each guard is a single number with an unambiguous "good" direction, so the harness can
assert the mechanism rather than eyeball a plot. Definitions:

- shared_map_mse : mean ||T(x) - Phi(x)||^2 over SHARED source cells (the cells that
  truly have a human counterpart). Lower is better. This is the core accuracy of the
  transport on the part of the distribution both species share.

- blob_leakage    : mean transported mass placed by the BLOB (mouse-only) cells,
  normalized by mean shared-cell mass. Balanced OT must dump the blob into the human
  cloud (leakage ~1); a good UOT discards it (leakage -> 0).

- keptmass_auroc  : AUROC using (1 - kept_mass) to classify blob vs shared cells. 1.0 =
  the map's own mass bookkeeping perfectly identifies the species-unique cells; 0.5 =
  uninformative (the balanced case, where every cell keeps full mass).
"""

from __future__ import annotations

import numpy as np


def shared_map_mse(mapped, Phi, X, shared_mask) -> float:
    tgt = Phi(X[shared_mask])
    d = mapped[shared_mask] - tgt
    return float(np.mean(np.sum(d * d, axis=1)))


def blob_leakage(kept_mass, shared_mask) -> float:
    blob = ~shared_mask
    if blob.sum() == 0:
        return float("nan")
    shared_mean = kept_mass[shared_mask].mean() + 1e-12
    return float(kept_mass[blob].mean() / shared_mean)


def keptmass_auroc(kept_mass, shared_mask) -> float:
    """AUROC of score=(-kept_mass) for detecting blob cells. Rank-based, no sklearn."""
    score = -np.asarray(kept_mass, float)
    y = (~shared_mask).astype(int)
    pos, neg = score[y == 1], score[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    allscore = np.concatenate([pos, neg])
    # average ranks (ties -> mean rank) so an uninformative score gives AUROC ~ 0.5
    order = np.argsort(allscore, kind="mergesort")
    sorted_s = allscore[order]
    ranks_sorted = np.empty(len(allscore), float)
    i = 0
    while i < len(sorted_s):
        j = i
        while j + 1 < len(sorted_s) and sorted_s[j + 1] == sorted_s[i]:
            j += 1
        ranks_sorted[i : j + 1] = 0.5 * (i + j) + 1.0  # 1-based average rank
        i = j + 1
    ranks = np.empty(len(allscore), float)
    ranks[order] = ranks_sorted
    r_pos = ranks[: len(pos)].sum()
    auc = (r_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))
    return float(auc)


def eval_map(mapped, kept_mass, toy) -> dict:
    return {
        "shared_map_mse": shared_map_mse(mapped, toy.Phi, toy.X, toy.shared_mask),
        "blob_leakage": blob_leakage(kept_mass, toy.shared_mask),
        "keptmass_auroc": keptmass_auroc(kept_mass, toy.shared_mask),
    }

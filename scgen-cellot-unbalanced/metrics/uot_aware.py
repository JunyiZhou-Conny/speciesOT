"""Mass-aware metrics for Option A / UOT evaluation.

North-star ``frac_gap_closed_decoded`` compares full predicted vs full target
clouds and can punish correct mass-dropping. These sidecars answer the UOT
question without replacing the north-star.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

# Prefer vendored honest_metrics MMD when available.
try:
    from honest_metrics import DEFAULT_GAMMAS, mmd_distance
except Exception:  # pragma: no cover
    DEFAULT_GAMMAS = np.logspace(1, -3, num=50)

    def mmd_distance(x, y, gamma):  # type: ignore
        from sklearn.metrics.pairwise import rbf_kernel

        xx = rbf_kernel(x, x, gamma)
        xy = rbf_kernel(x, y, gamma)
        yy = rbf_kernel(y, y, gamma)
        return float(xx.mean() + yy.mean() - 2.0 * xy.mean())


def _weighted_resample(
    X: np.ndarray,
    weights: np.ndarray,
    n: int,
    rng: np.random.Generator,
) -> np.ndarray:
    w = np.asarray(weights, dtype=np.float64)
    w = w / w.sum()
    idx = rng.choice(len(X), size=n, replace=True, p=w)
    return X[idx]


def composition_matched_mmd(
    pred: np.ndarray,
    target: np.ndarray,
    pred_labels: np.ndarray,
    target_labels: np.ndarray,
    *,
    ncells: int = 80,
    n_reps: int = 10,
    gammas=DEFAULT_GAMMAS,
    random_state: int = 0,
) -> dict:
    """MMD after resampling both clouds to the shared-label geometric-mean mix.

    Labels present on only one side are excluded (shared structure only).
    """
    pred = np.asarray(pred)
    target = np.asarray(target)
    pred_labels = np.asarray(pred_labels)
    target_labels = np.asarray(target_labels)

    shared = sorted(
        set(pred_labels.tolist()) & set(target_labels.tolist()), key=str
    )
    if not shared:
        return {
            "composition_matched_mmd": float("nan"),
            "n_shared_labels": 0,
            "ncells": ncells,
        }

    def _props(labels):
        return {c: float(np.mean(labels == c)) for c in shared}

    pp, pt = _props(pred_labels), _props(target_labels)
    pstar = {
        c: float(np.sqrt(max(pp[c], 1e-12) * max(pt[c], 1e-12))) for c in shared
    }
    z = sum(pstar.values()) or 1.0
    pstar = {c: v / z for c, v in pstar.items()}

    def _weights(labels):
        w = np.zeros(len(labels), dtype=np.float64)
        for i, lab in enumerate(labels):
            if lab in pstar and pstar[lab] > 0:
                emp = max(float(np.mean(labels == lab)), 1e-12)
                w[i] = pstar[lab] / emp
        if w.sum() <= 0:
            w[:] = 1.0
        return w / w.sum()

    wp, wt = _weights(pred_labels), _weights(target_labels)
    rng = np.random.default_rng(random_state)
    scores = []
    for r in range(n_reps):
        A = _weighted_resample(pred, wp, ncells, rng)
        B = _weighted_resample(target, wt, ncells, rng)
        scores.append(float(np.mean([mmd_distance(A, B, g) for g in gammas])))
    return {
        "composition_matched_mmd": float(np.mean(scores)),
        "composition_matched_mmd_std": float(np.std(scores)),
        "n_shared_labels": len(shared),
        "ncells": ncells,
    }


def kept_mass_report(
    source_weights: np.ndarray,
    *,
    source_labels: Optional[np.ndarray] = None,
    keep_quantile: float = 0.5,
) -> dict:
    """Summarize Option-A source mass: who is up-/down-weighted.

    For reweight-then-balanced, ``source_weights`` *are* the kept-mass proxy
    (high weight = more transport mass). Uniform weights → effective_kept ≈ 1.
    """
    w = np.asarray(source_weights, dtype=np.float64)
    w = w[w > 0]
    if len(w) == 0:
        return {"effective_kept_mass": 0.0, "weight_entropy": 0.0}

    p = w / w.sum()
    # effective sample size / n  ∈ (0, 1]; 1 = uniform
    ess = float(1.0 / np.sum(p**2) / len(p))
    # normalized entropy
    ent = float(-(p * np.log(p + 1e-300)).sum() / np.log(len(p)))

    out = {
        "effective_kept_mass": ess,
        "weight_entropy": ent,
        "weight_min": float(w.min()),
        "weight_max": float(w.max()),
        "weight_cv": float(w.std() / (w.mean() + 1e-12)),
    }

    if source_labels is not None:
        labels = np.asarray(source_labels)
        # align: caller should pass labels only for positive-weight cells
        if len(labels) == len(source_weights):
            labels = labels[np.asarray(source_weights) > 0]
        thr = np.quantile(w, keep_quantile)
        keep = w >= thr
        # fraction of each label among kept vs all
        cats = sorted(set(labels.tolist()), key=str)
        for c in cats:
            mask = labels == c
            out[f"frac_kept_label_{c}"] = float(keep[mask].mean()) if mask.any() else float("nan")
            out[f"mass_share_label_{c}"] = float(p[mask].sum()) if mask.any() else 0.0

    return out

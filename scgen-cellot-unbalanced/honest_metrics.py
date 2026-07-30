#!/usr/bin/env python3
"""Honest gap-closed metrics for autoresearch experiments.

The raw scalar metrics in ``experiments.csv`` (r2_all, r_50, ...) are
uninterpretable in isolation: R^2 = 0.85 *relative to what*? The honest question
is always **what fraction of the source->target gap did the model close**, in a
frame where the comparison is apples-to-apples.

This module is SELF-CONTAINED (vendors the MMD + per-gene JS kernels from the main
speciesOT hub, ``cellot/cellot_gpu/cellot/losses/{mmd,divergence}.py``) so it has
no dependency on the ablation CellOT library having them. It operates on plain
numpy clouds plus (optionally) AE ``encode``/``decode`` callables, so it can run
in any environment for the self-test and inside ``run_one_experiment`` for real.

Frames
------
- raw      : MMD(pred, target) vs raw refs. DIAGNOSTIC ONLY (AE round-trip tax can
             flip its sign; see docs/conceptual_framework.md 5.9).
- decoded  : references round-tripped through the AE -> the honest NORTH-STAR for
             AE-decoded predictions. ``frac_gap_closed_decoded`` is the headline.
- encoded  : gap closed in AE latent space (where the model operates).

Guardrails
----------
- frac_r2_closed[_decoded] : did the per-gene mean come out right?
- mean_js                  : per-gene Jensen-Shannon (KL-style) marginal divergence.

References (definitions mirrored, verified June 2026):
  cellot/cellot_gpu/cellot/losses/mmd.py          (mmd_distance, compute_mmd_two_sample)
  cellot/cellot_gpu/cellot/losses/divergence.py   (compute_marginal_divergence)
  cellot/cellot_gpu/scripts/extended_metrics.py   (raw frame + frac_r2_closed)
  cellot/cellot_gpu/scripts/decoded_frame_metrics.py (decoded north-star)
"""

from __future__ import annotations

from typing import Callable

import numpy as np

# Match the hub eval exactly so numbers are comparable in spirit.
DEFAULT_GAMMAS = np.logspace(1, -3, num=50)
DEFAULT_NCELLS = (30, 50, 80)


# --------------------------------------------------------------------------- MMD
def _rbf_kernel(x: np.ndarray, y: np.ndarray, gamma: float) -> np.ndarray:
    """RBF kernel matrix; vendored to avoid a hard sklearn dependency.

    Falls back to sklearn if present (identical result), else computes directly.
    """
    try:
        from sklearn.metrics.pairwise import rbf_kernel

        return rbf_kernel(x, y, gamma)
    except Exception:
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        x2 = np.sum(x * x, axis=1)[:, None]
        y2 = np.sum(y * y, axis=1)[None, :]
        sq = x2 + y2 - 2.0 * (x @ y.T)
        np.maximum(sq, 0, out=sq)
        return np.exp(-gamma * sq)


def mmd_distance(x: np.ndarray, y: np.ndarray, gamma: float) -> float:
    xx = _rbf_kernel(x, x, gamma)
    xy = _rbf_kernel(x, y, gamma)
    yy = _rbf_kernel(y, y, gamma)
    return float(xx.mean() + yy.mean() - 2.0 * xy.mean())


def mmd_two_sample_mean(
    A,
    B=None,
    *,
    ncells_list=DEFAULT_NCELLS,
    gammas=DEFAULT_GAMMAS,
    n_reps: int = 10,
    random_state: int = 0,
    split_half: bool = False,
) -> dict[int, float]:
    """Subsampled MMD averaged over gammas+reps, per ncells.

    Returns {ncells: mean_mmd}. Mirrors hub ``compute_mmd_two_sample`` aggregation
    (the hub returns long-form rows; we collapse to the per-ncells mean the
    sidecars ultimately report).
    """
    gammas = np.asarray(list(gammas))
    A = np.asarray(A, dtype=np.float64)
    rng = np.random.default_rng(random_state)
    out: dict[int, float] = {}

    if split_half:
        n = len(A)
        all_idx = np.arange(n)
        for ncells in ncells_list:
            ncells = int(ncells)
            if ncells > n:
                continue
            reps = []
            for _ in range(n_reps):
                idx_a = rng.choice(n, size=ncells, replace=False)
                remaining = np.setdiff1d(all_idx, idx_a, assume_unique=False)
                idx_b = (
                    rng.choice(remaining, size=ncells, replace=False)
                    if len(remaining) >= ncells
                    else rng.choice(n, size=ncells, replace=False)
                )
                reps.append(np.mean([mmd_distance(A[idx_a], A[idx_b], g) for g in gammas]))
            out[ncells] = float(np.mean(reps))
        return out

    if B is None:
        raise ValueError("B is required unless split_half=True")
    B = np.asarray(B, dtype=np.float64)
    nmin = min(len(A), len(B))
    for ncells in ncells_list:
        ncells = int(ncells)
        if ncells > nmin:
            continue
        reps = []
        for _ in range(n_reps):
            idx_a = rng.choice(len(A), size=ncells, replace=False)
            idx_b = rng.choice(len(B), size=ncells, replace=False)
            reps.append(np.mean([mmd_distance(A[idx_a], B[idx_b], g) for g in gammas]))
        out[ncells] = float(np.mean(reps))
    return out


# --------------------------------------------------------------- per-gene JS / KL
def compute_mean_js(treated, imputed, n_bins: int = 50, eps: float = 1e-6) -> float:
    """Mean per-gene Jensen-Shannon divergence (natural log, in [0, ln2])."""
    T = np.asarray(treated, dtype=float)
    I = np.asarray(imputed, dtype=float)
    if T.shape[1] != I.shape[1]:
        raise ValueError(f"gene-axis mismatch: {T.shape[1]} vs {I.shape[1]}")
    n_genes = T.shape[1]
    js = np.zeros(n_genes)
    for g in range(n_genes):
        tg, ig = T[:, g], I[:, g]
        lo = min(tg.min(), ig.min())
        hi = max(tg.max(), ig.max())
        if not (hi > lo):
            continue
        bins = np.linspace(lo, hi, n_bins + 1)
        ph, _ = np.histogram(tg, bins=bins)
        qh, _ = np.histogram(ig, bins=bins)
        p = ph.astype(float) + eps
        q = qh.astype(float) + eps
        p /= p.sum()
        q /= q.sum()
        m = 0.5 * (p + q)
        js[g] = 0.5 * np.sum(p * np.log(p / m)) + 0.5 * np.sum(q * np.log(q / m))
    return float(js.mean())


# ------------------------------------------------------------------------ R^2 gap
def _r2_means(A, B) -> float:
    a, b = np.asarray(A).mean(0), np.asarray(B).mean(0)
    r = np.corrcoef(a, b)[0, 1]
    return float(r * r)


def _split_half_r2(cloud, n_reps: int, rng: np.random.Generator) -> float:
    cloud = np.asarray(cloud)
    n = len(cloud)
    return float(
        np.mean(
            [
                _r2_means(cloud[perm[: n // 2]], cloud[perm[n // 2 :]])
                for perm in (rng.permutation(n) for _ in range(n_reps))
            ]
        )
    )


def _frac(ceiling: float, model: float, floor: float) -> float:
    if ceiling is None or model is None or floor is None:
        return float("nan")
    if not np.isfinite(ceiling) or not np.isfinite(model) or not np.isfinite(floor):
        return float("nan")
    if ceiling <= floor:
        return float("nan")
    return (ceiling - model) / (ceiling - floor)


def _feasible_ncells(*sizes: int, ncells_list=DEFAULT_NCELLS) -> tuple[int, ...]:
    nmin = min(sizes)
    feasible = tuple(int(n) for n in ncells_list if n <= nmin)
    return feasible


# --------------------------------------------------------------------- public API
def compute_honest_metrics(
    pred: np.ndarray,
    target: np.ndarray,
    source: np.ndarray,
    *,
    encode: Callable[[np.ndarray], np.ndarray] | None = None,
    decode: Callable[[np.ndarray], np.ndarray] | None = None,
    imputed_latent: np.ndarray | None = None,
    ncells_list=DEFAULT_NCELLS,
    n_reps: int = 10,
    random_state: int = 0,
) -> dict:
    """Compute the honest metric set for one experiment.

    Parameters
    ----------
    pred    : (n_pred, n_genes) decoded model prediction ("imputed")
    target  : (n_tgt,  n_genes) ground-truth target cloud ("treated")
    source  : (n_src,  n_genes) source / identity-baseline cloud ("control")
    encode/decode : AE projector callables (numpy->numpy). If given, the DECODED
                    north-star + encoded-frame metrics are computed.
    imputed_latent : optional pure transport-latent prediction. If absent and
                    ``encode`` is given, falls back to ``encode(pred)`` (diagnostic).

    Returns a flat dict of scalars (headline at the largest feasible ncells) plus
    a nested ``per_ncells`` block, ready for metrics.json + experiments.csv.
    """
    pred = np.asarray(pred, dtype=np.float64)
    target = np.asarray(target, dtype=np.float64)
    source = np.asarray(source, dtype=np.float64)
    rng = np.random.default_rng(random_state)

    feasible = _feasible_ncells(len(pred), len(target), len(source), ncells_list=ncells_list)
    headline_nc = feasible[-1] if feasible else None
    kw = dict(ncells_list=feasible or ncells_list, n_reps=n_reps, random_state=random_state)

    out: dict = {"honest_ncells": list(feasible), "headline_ncells": headline_nc,
                 "honest_notes": []}

    def _note_if_illdefined(frame: str, ceiling: float, floor: float) -> None:
        # A gap-closed frac is only defined when the no-transport ceiling sits ABOVE
        # the irreducible floor. When ceiling<=floor the frame is ill-defined (common
        # for an UNDERTRAINED AE: the round-trip tax inflates the decoded floor to ~the
        # ceiling). We return NaN AND record why, rather than silently emitting NaN.
        if ceiling is not None and floor is not None and np.isfinite(ceiling) and np.isfinite(floor):
            if ceiling <= floor:
                out["honest_notes"].append(
                    f"{frame}: ill-defined (ceiling {ceiling:.4f} <= floor {floor:.4f}); "
                    f"likely undertrained AE — expect this to resolve at full n_iters"
                )

    def headline(d: dict[int, float]) -> float:
        if headline_nc is not None and headline_nc in d:
            return d[headline_nc]
        return next(iter(sorted(d.items())), (None, float("nan")))[1] if d else float("nan")

    # ---- raw frame (diagnostic) -------------------------------------------------
    if feasible:
        mmd_model = mmd_two_sample_mean(pred, target, **kw)
        mmd_floor = mmd_two_sample_mean(target, split_half=True, **kw)
        mmd_ceiling = mmd_two_sample_mean(source, target, **kw)
        m, f, c = headline(mmd_model), headline(mmd_floor), headline(mmd_ceiling)
        _note_if_illdefined("raw", c, f)
        out.update(
            mmd_model=m,
            mmd_floor=f,
            mmd_ceiling=c,
            frac_gap_closed=_frac(c, m, f),  # diagnostic; sign can flip (AE tax)
        )
        per_ncells_raw = {
            nc: _frac(mmd_ceiling.get(nc), mmd_model.get(nc), mmd_floor.get(nc))
            for nc in feasible
        }
    else:
        per_ncells_raw = {}

    # ---- R^2 gap (raw means; AE tax does NOT apply to first moments) -----------
    r2_self = _split_half_r2(target, n_reps, rng)
    r2_identity = _r2_means(source, target)
    r2_model = _r2_means(pred, target)
    out["frac_r2_closed"] = (
        (r2_model - r2_identity) / (r2_self - r2_identity)
        if (np.isfinite(r2_identity) and r2_self > r2_identity)
        else float("nan")
    )
    out["r2_self"] = r2_self
    out["r2_identity"] = r2_identity
    out["r2_model"] = r2_model

    # ---- per-gene JS guardrail --------------------------------------------------
    try:
        out["mean_js"] = compute_mean_js(target, pred)
    except Exception:
        out["mean_js"] = float("nan")

    # ---- decoded frame (NORTH-STAR) + encoded frame ----------------------------
    if encode is not None and decode is not None:
        treated_dec = np.asarray(decode(encode(target)), dtype=np.float64)
        control_dec = np.asarray(decode(encode(source)), dtype=np.float64)

        if feasible:
            mmd_model_d = mmd_two_sample_mean(pred, target, **kw)  # same as raw model
            mmd_aerec = mmd_two_sample_mean(treated_dec, target, **kw)  # decoded floor
            mmd_ceil_d = mmd_two_sample_mean(control_dec, target, **kw)  # decoded ceiling
            m, f, c = headline(mmd_model_d), headline(mmd_aerec), headline(mmd_ceil_d)
            _note_if_illdefined("decoded", c, f)
            out.update(
                mmd_ae_recon_floor=f,
                mmd_decoded_ceiling=c,
                frac_gap_closed_decoded=_frac(c, m, f),  # <-- the north-star
            )
            per_ncells_dec = {
                nc: _frac(mmd_ceil_d.get(nc), mmd_model_d.get(nc), mmd_aerec.get(nc))
                for nc in feasible
            }
        else:
            per_ncells_dec = {}

        # decoded R^2 references
        r2_self_dec = _split_half_r2(treated_dec, n_reps, rng)
        r2_identity_dec = _r2_means(control_dec, treated_dec)
        r2_model_dec = _r2_means(pred, treated_dec)
        out["frac_r2_closed_decoded"] = (
            (r2_model_dec - r2_identity_dec) / (r2_self_dec - r2_identity_dec)
            if r2_self_dec > r2_identity_dec
            else float("nan")
        )

        # encoded (latent) frame: where the model operates
        imp_lat = imputed_latent if imputed_latent is not None else encode(pred)
        imp_lat = np.asarray(imp_lat, dtype=np.float64)
        tgt_lat = np.asarray(encode(target), dtype=np.float64)
        src_lat = np.asarray(encode(source), dtype=np.float64)
        feas_lat = _feasible_ncells(len(imp_lat), len(tgt_lat), len(src_lat), ncells_list=ncells_list)
        if feas_lat:
            kwl = dict(ncells_list=feas_lat, n_reps=n_reps, random_state=random_state)
            mmd_model_l = mmd_two_sample_mean(imp_lat, tgt_lat, **kwl)
            mmd_floor_l = mmd_two_sample_mean(tgt_lat, split_half=True, **kwl)
            mmd_ceil_l = mmd_two_sample_mean(src_lat, tgt_lat, **kwl)
            hn = feas_lat[-1]
            _note_if_illdefined("latent", mmd_ceil_l.get(hn), mmd_floor_l.get(hn))
            out.update(
                mmd_model_latent=mmd_model_l.get(hn, float("nan")),
                mmd_floor_latent=mmd_floor_l.get(hn, float("nan")),
                mmd_ceiling_latent=mmd_ceil_l.get(hn, float("nan")),
                frac_gap_closed_latent=_frac(
                    mmd_ceil_l.get(hn), mmd_model_l.get(hn), mmd_floor_l.get(hn)
                ),
                latent_via=("transport" if imputed_latent is not None else "encode_of_pred"),
            )
        out["per_ncells"] = {"raw": per_ncells_raw, "decoded": per_ncells_dec}
    else:
        out["per_ncells"] = {"raw": per_ncells_raw}

    return out


# --------------------------------------------------------------------- self-test
def _selftest() -> int:
    """Synthetic sanity check (no torch). A model that nails the target should
    close ~all of the gap; a do-nothing (predict source) model should close ~0."""
    rng = np.random.default_rng(0)
    n, d = 400, 20
    shift = rng.normal(0, 1, size=d) * 2.0
    source = rng.normal(0, 1, size=(n, d))
    target = rng.normal(0, 1, size=(n, d)) + shift

    good_pred = rng.normal(0, 1, size=(n, d)) + shift  # ~ target distribution
    null_pred = source.copy()  # do-nothing baseline

    # identity AE (decode(encode(x)) == x) so decoded frame == raw frame here.
    ident = lambda x: np.asarray(x, dtype=np.float64)

    good = compute_honest_metrics(good_pred, target, source, encode=ident, decode=ident,
                                  ncells_list=(30, 50, 80), n_reps=5)
    null = compute_honest_metrics(null_pred, target, source, encode=ident, decode=ident,
                                  ncells_list=(30, 50, 80), n_reps=5)

    print("=== honest_metrics self-test ===")
    for label, res in [("GOOD (matches target)", good), ("NULL (predicts source)", null)]:
        print(f"\n[{label}]")
        for k in ("frac_gap_closed", "frac_gap_closed_decoded", "frac_gap_closed_latent",
                  "frac_r2_closed", "frac_r2_closed_decoded", "mean_js",
                  "mmd_model", "mmd_floor", "mmd_ceiling"):
            if k in res:
                print(f"  {k:26} = {res[k]:.4f}")

    ok = True
    # Good model closes most of the gap; null model closes ~none (<~0.2).
    if not (good["frac_gap_closed"] > 0.6):
        print("FAIL: good model frac_gap_closed not > 0.6"); ok = False
    if not (null["frac_gap_closed"] < 0.25):
        print("FAIL: null model frac_gap_closed not < 0.25"); ok = False
    if not (good["frac_r2_closed"] > 0.5):
        print("FAIL: good model frac_r2_closed not > 0.5"); ok = False
    if not (good["mean_js"] < null["mean_js"]):
        print("FAIL: good model mean_js not < null model mean_js"); ok = False
    print("\nSELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())

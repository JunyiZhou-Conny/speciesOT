"""Minimal balanced and unbalanced OT solvers (pure numpy, no POT/ott dependency).

These are for the synthetic mechanism proof only. The real pipeline (Option A/B/C in
PLAN.md) will use the CellOT ICNN stack and/or a mature solver; here we just need a
faithful, readable balanced-vs-unbalanced contrast.

Solver: log-domain Sinkhorn. The *only* difference between balanced and unbalanced is
the marginal-update exponent ``fi = rho/(rho+eps)``:
  - ``rho -> inf``  => ``fi -> 1``  => hard marginals  => BALANCED OT.
  - finite ``rho``  => ``fi < 1``   => KL-relaxed marginals => UNBALANCED OT.
  - ``rho -> 0``    => ``fi -> 0``  => nothing transported.
So a single ``rho`` sweep interpolates balanced <-> unbalanced, which is exactly the
knob the plan calls ``tau``.
"""

from __future__ import annotations

import numpy as np


def squared_cost(X: np.ndarray, Y: np.ndarray) -> np.ndarray:
    x2 = np.sum(X * X, axis=1)[:, None]
    y2 = np.sum(Y * Y, axis=1)[None, :]
    C = x2 + y2 - 2.0 * (X @ Y.T)
    np.maximum(C, 0, out=C)
    return C


def _logsumexp(M: np.ndarray, axis: int) -> np.ndarray:
    m = np.max(M, axis=axis, keepdims=True)
    out = m + np.log(np.sum(np.exp(M - m), axis=axis, keepdims=True))
    return np.squeeze(out, axis=axis)


def sinkhorn(
    X: np.ndarray,
    Y: np.ndarray,
    eps: float = 0.05,
    rho: float | None = None,
    a: np.ndarray | None = None,
    b: np.ndarray | None = None,
    n_iter: int = 2000,
    tol: float = 1e-9,
    cost_scale: bool = True,
) -> np.ndarray:
    """Return the transport plan ``P`` (shape n x m).

    ``rho=None`` -> balanced OT (hard marginals). Finite ``rho`` -> unbalanced (KL
    marginal relaxation with strength ``rho``, our ``tau``). ``a``/``b`` default to
    uniform; pass a non-uniform ``a`` for the reweight-then-balanced (Option A) bridge.
    """
    n, m = len(X), len(Y)
    a = np.full(n, 1.0 / n) if a is None else np.asarray(a, float)
    b = np.full(m, 1.0 / m) if b is None else np.asarray(b, float)
    loga, logb = np.log(a), np.log(b)

    C = squared_cost(X, Y)
    if cost_scale:
        C = C / (C.mean() + 1e-12)
    K = -C / eps  # log-kernel

    f = np.zeros(n)
    g = np.zeros(m)
    fi = 1.0 if rho is None else rho / (rho + eps)

    for _ in range(n_iter):
        f_prev = f
        # f update: row marginal
        lse_row = _logsumexp(K + (g + logb)[None, :], axis=1)
        f = fi * (loga - lse_row)
        # g update: column marginal
        lse_col = _logsumexp(K + (f + loga)[:, None], axis=0)
        g = fi * (logb - lse_col)
        if np.max(np.abs(f - f_prev)) < tol:
            break

    logP = (f + loga)[:, None] + (g + logb)[None, :] + K
    return np.exp(logP)


def barycentric_map(P: np.ndarray, Y: np.ndarray, eps: float = 1e-12):
    """Barycentric projection T(x_i) = sum_j P_ij y_j / sum_j P_ij.

    Returns (mapped, kept_mass) where ``kept_mass[i] = sum_j P_ij`` is the transported
    mass of source cell i (its row sum). For unbalanced OT, small kept_mass flags a cell
    the map chose to (partly) discard -- e.g. a species-unique cell.
    """
    row = P.sum(axis=1)
    denom = np.where(row > eps, row, eps)[:, None]
    mapped = (P @ Y) / denom
    return mapped, row

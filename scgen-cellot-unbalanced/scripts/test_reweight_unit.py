#!/usr/bin/env python3
"""CPU unit tests for Option-A weight estimators (no CellOT / no GPU)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from uot.reweight import (
    blend_weights,
    density_ratio_weights,
    estimate_weights,
    louvain_match_weights,
    normalize_weights,
    uniform_weights,
)


def test_uniform_and_blend():
    u = uniform_weights(10)
    assert np.isclose(u.sum(), 1.0)
    w = normalize_weights(np.arange(1, 11, dtype=float))
    b0 = blend_weights(w, 0.0)
    assert np.allclose(b0, u, atol=1e-10)
    b1 = blend_weights(w, 1.0)
    assert np.allclose(b1, w, atol=1e-10)


def test_louvain_match_downweights_unique():
    # source has extra cluster "blob"; target does not
    ls = np.array(["A", "A", "B", "blob", "blob"])
    lt = np.array(["A", "A", "A", "B", "B"])
    ws, wt = louvain_match_weights(ls, lt, mode="geometric_mean")
    assert ws[ls == "blob"].mean() < ws[ls == "A"].mean()
    assert np.isclose(ws.sum(), 1.0) and np.isclose(wt.sum(), 1.0)


def test_density_ratio_shapes():
    rng = np.random.default_rng(0)
    Xs = rng.normal(size=(40, 8))
    Xt = rng.normal(loc=0.5, size=(30, 8))
    ws, wt = density_ratio_weights(Xs, Xt, k=5)
    assert ws.shape == (40,) and wt.shape == (30,)
    assert np.isclose(ws.sum(), 1.0)


def test_artifact_roundtrip(tmp_path=None):
    n = 20
    obs = np.array([f"c{i}" for i in range(n)])
    sm = np.zeros(n, dtype=bool)
    tm = np.zeros(n, dtype=bool)
    sm[:10] = True
    tm[10:] = True
    labels = np.array(["A"] * 5 + ["B"] * 5 + ["A"] * 5 + ["B"] * 5)
    art = estimate_weights(
        method="louvain_match",
        alpha=0.5,
        source_mask=sm,
        target_mask=tm,
        obs_names=obs,
        labels=labels,
    )
    out = ROOT / "results" / "lps_rat" / "_unit_weights.npz"
    art.save(out)
    art2 = type(art).load(out)
    assert art2.method == "louvain_match"
    assert np.isclose(art2.alpha, 0.5)
    assert np.allclose(art2.source_weights[sm].sum(), 1.0)
    out.unlink(missing_ok=True)


if __name__ == "__main__":
    test_uniform_and_blend()
    test_louvain_match_downweights_unique()
    test_density_ratio_shapes()
    test_artifact_roundtrip()
    print("OK — all Option-A unit tests passed")

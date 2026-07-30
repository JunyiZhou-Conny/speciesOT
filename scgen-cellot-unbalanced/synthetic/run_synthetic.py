"""Synthetic mechanism proof: does unbalanced OT fix what balanced OT breaks?

Runs balanced OT and a sweep of unbalanced OT (varying rho == tau) on the toy, scores
the correctness guards, writes a CSV + a diagnostic figure, and asserts the mechanism:

  1. tau-parity   : at large rho, unbalanced ~ balanced (the PLAN.md 5.2 parity guard).
  2. corruption   : balanced OT has high blob_leakage and non-trivial shared_map_mse.
  3. recovery     : some finite rho lowers shared_map_mse AND blob_leakage, with
                    keptmass_auroc close to 1 (UOT identifies the species-unique cells).
  4. option-A bridge: feeding UOT kept-mass back as the source marginal into a BALANCED
                    solver (reweight-then-balanced) also recovers the map -- the signal
                    Option A's weight estimator must reproduce on real data.

Usage:  python run_synthetic.py [--outdir results]
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from toy_data import make_toy
from ot_solvers import sinkhorn, barycentric_map
from guards import eval_map


def run(outdir: Path, eps: float = 0.05, seed: int = 0):
    outdir.mkdir(parents=True, exist_ok=True)
    toy = make_toy(seed=seed)

    rows = []

    # Balanced OT (hard marginals).
    Pb = sinkhorn(toy.X, toy.Y, eps=eps, rho=None)
    mb, kb = barycentric_map(Pb, toy.Y)
    gb = eval_map(mb, kb, toy)
    gb.update(method="balanced", rho=np.inf)
    rows.append(gb)

    # Unbalanced sweep over rho (== tau). Small rho = aggressive unbalancing.
    rho_grid = [0.02, 0.05, 0.1, 0.2, 0.5, 1.0, 5.0, 50.0]
    uot_results = {}
    for rho in rho_grid:
        P = sinkhorn(toy.X, toy.Y, eps=eps, rho=rho)
        mp, kp = barycentric_map(P, toy.Y)
        g = eval_map(mp, kp, toy)
        g.update(method="unbalanced", rho=rho)
        rows.append(g)
        uot_results[rho] = (P, mp, kp, g)

    # Option-A bridge: use a mid-rho UOT's kept-mass as the source marginal weights,
    # renormalize, and run a BALANCED solver with those weights.
    rho_star = 0.1
    _, _, k_star, _ = uot_results[rho_star]
    a_reweight = k_star / k_star.sum()
    Pa = sinkhorn(toy.X, toy.Y, eps=eps, rho=None, a=a_reweight)
    ma, ka = barycentric_map(Pa, toy.Y)
    ga = eval_map(ma, ka, toy)
    ga.update(method="reweight_then_balanced", rho=rho_star)
    rows.append(ga)

    # ---- write CSV
    csv_path = outdir / "synthetic_guards.csv"
    with open(csv_path, "w", newline="") as fh:
        w = csv.DictWriter(
            fh, fieldnames=["method", "rho", "shared_map_mse", "blob_leakage", "keptmass_auroc"]
        )
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # ---- figure
    _figure(toy, mb, uot_results[rho_star], ma, rows, rho_grid, uot_results, outdir)

    # ---- assert the mechanism
    best_rho = min(rho_grid, key=lambda r: uot_results[r][3]["shared_map_mse"])
    best = uot_results[best_rho][3]
    large = uot_results[50.0][3]

    summary = {
        "balanced": gb,
        "best_uot_rho": best_rho,
        "best_uot": best,
        "large_rho_parity": large,
        "reweight_then_balanced": ga,
    }
    _report(summary)
    _assertions(gb, best, large, ga)
    return summary


def _figure(toy, mb, uot_star, ma, rows, rho_grid, uot_results, outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    _, m_star, _, _ = uot_star
    shared = toy.shared_mask
    fig, ax = plt.subplots(2, 3, figsize=(16, 10))

    def scatter_clouds(a):
        a.scatter(toy.Y[:, 0], toy.Y[:, 1], s=8, c="lightgray", label="human (target)")
        a.scatter(toy.X[shared, 0], toy.X[shared, 1], s=8, c="tab:blue", alpha=0.5, label="mouse shared")
        a.scatter(toy.X[~shared, 0], toy.X[~shared, 1], s=10, c="tab:red", alpha=0.6, label="mouse-only blob")

    # panel 0: setup
    scatter_clouds(ax[0, 0])
    ax[0, 0].set_title("Toy setup: composition skew + mouse-only blob")
    ax[0, 0].legend(fontsize=7, loc="upper right")

    # panel 1: balanced map
    ax[0, 1].scatter(toy.Y[:, 0], toy.Y[:, 1], s=8, c="lightgray")
    ax[0, 1].scatter(mb[shared, 0], mb[shared, 1], s=8, c="tab:blue", alpha=0.5)
    ax[0, 1].scatter(mb[~shared, 0], mb[~shared, 1], s=12, c="tab:red", alpha=0.7)
    tgt = toy.Phi(toy.X[shared])
    ax[0, 1].scatter(tgt[:, 0], tgt[:, 1], s=4, c="k", alpha=0.15, marker="x")
    ax[0, 1].set_title("BALANCED: blob dumped into human cloud (red)\nblack x = true Phi(shared)")

    # panel 2: unbalanced map (rho*)
    ax[0, 2].scatter(toy.Y[:, 0], toy.Y[:, 1], s=8, c="lightgray")
    ax[0, 2].scatter(m_star[shared, 0], m_star[shared, 1], s=8, c="tab:blue", alpha=0.5)
    ax[0, 2].scatter(m_star[~shared, 0], m_star[~shared, 1], s=12, c="tab:red", alpha=0.7)
    ax[0, 2].scatter(tgt[:, 0], tgt[:, 1], s=4, c="k", alpha=0.15, marker="x")
    ax[0, 2].set_title("UNBALANCED (rho=0.1): shared cells hit Phi,\nblob mass discarded")

    # panel 3: guards vs rho
    mse = [uot_results[r][3]["shared_map_mse"] for r in rho_grid]
    leak = [uot_results[r][3]["blob_leakage"] for r in rho_grid]
    auroc = [uot_results[r][3]["keptmass_auroc"] for r in rho_grid]
    bal = next(r for r in rows if r["method"] == "balanced")
    ax[1, 0].plot(rho_grid, mse, "o-", label="shared_map_mse")
    ax[1, 0].axhline(bal["shared_map_mse"], ls="--", c="gray", label="balanced")
    ax[1, 0].set_xscale("log"); ax[1, 0].set_xlabel("rho (tau)"); ax[1, 0].legend(fontsize=8)
    ax[1, 0].set_title("Shared-map error vs rho (lower=better)")

    ax[1, 1].plot(rho_grid, leak, "o-", c="tab:red", label="blob_leakage")
    ax[1, 1].axhline(bal["blob_leakage"], ls="--", c="gray", label="balanced")
    ax[1, 1].set_xscale("log"); ax[1, 1].set_xlabel("rho (tau)"); ax[1, 1].legend(fontsize=8)
    ax[1, 1].set_title("Blob leakage vs rho (lower=better)")

    ax[1, 2].plot(rho_grid, auroc, "o-", c="tab:green")
    ax[1, 2].axhline(0.5, ls="--", c="gray")
    ax[1, 2].set_xscale("log"); ax[1, 2].set_xlabel("rho (tau)"); ax[1, 2].set_ylim(0.4, 1.02)
    ax[1, 2].set_title("Kept-mass AUROC: UOT finds species-unique cells")

    fig.tight_layout()
    fig.savefig(outdir / "synthetic_mechanism.png", dpi=130)
    plt.close(fig)


def _report(s):
    b, best, large, ga = s["balanced"], s["best_uot"], s["large_rho_parity"], s["reweight_then_balanced"]
    print("\n=== Synthetic mechanism proof ===")
    fmt = lambda g: f"mse={g['shared_map_mse']:.3f}  leak={g['blob_leakage']:.3f}  auroc={g['keptmass_auroc']:.3f}"
    print(f"balanced                 : {fmt(b)}")
    print(f"unbalanced rho={s['best_rho'] if False else s['best_uot_rho']:<6} (best): {fmt(best)}")
    print(f"unbalanced rho=50 (parity): {fmt(large)}")
    print(f"reweight_then_balanced   : {fmt(ga)}")


def _assertions(bal, best, large, ga):
    ok = True
    def check(name, cond):
        nonlocal ok
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        ok = ok and cond
    print("\n--- mechanism assertions ---")
    check("tau-parity: large rho ~ balanced (mse within 20%)",
          abs(large["shared_map_mse"] - bal["shared_map_mse"]) <= 0.2 * bal["shared_map_mse"] + 1e-6)
    check("corruption: balanced leaks the blob (leakage > 0.5)", bal["blob_leakage"] > 0.5)
    check("recovery: best UOT beats balanced on shared_map_mse", best["shared_map_mse"] < bal["shared_map_mse"])
    check("recovery: best UOT reduces blob leakage below 0.5", best["blob_leakage"] < 0.5)
    check("detection: best UOT kept-mass AUROC > 0.9", best["keptmass_auroc"] > 0.9)
    check("option-A bridge: reweight_then_balanced beats balanced", ga["shared_map_mse"] < bal["shared_map_mse"])
    print(f"\n{'ALL GUARDS PASSED' if ok else 'SOME GUARDS FAILED'}\n")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=str(Path(__file__).parent / "results"))
    ap.add_argument("--eps", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    run(Path(args.outdir), eps=args.eps, seed=args.seed)

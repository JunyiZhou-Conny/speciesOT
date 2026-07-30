"""Didactic illustration of (1) "same shape up to a deformation" and (2) a Brenier map.

Everything here is ANALYTIC and exact (no solver): for two Gaussians the optimal
transport map for squared-Euclidean cost is the affine Bures map
    T(x) = m1 + A (x - m0),   A = Σ0^{-1/2} (Σ0^{1/2} Σ1 Σ0^{1/2})^{1/2} Σ0^{-1/2}
which is exactly the gradient of the convex quadratic potential
    phi(x) = 1/2 (x - m0)^T A (x - m0) + m1^T x   =>   grad phi = T.
A is symmetric positive-definite, so phi is convex => T is a Brenier map.

This mirrors what CellOT's ICNN learns in general (T = grad of a convex potential); the
Gaussian case just lets us write it in closed form so the figure is trustworthy.
"""

from __future__ import annotations

from pathlib import Path
import numpy as np


def sqrtm_spd(M):
    w, V = np.linalg.eigh(M)
    return (V * np.sqrt(np.clip(w, 0, None))) @ V.T


def invsqrtm_spd(M):
    w, V = np.linalg.eigh(M)
    return (V * (1.0 / np.sqrt(np.clip(w, 1e-12, None)))) @ V.T


def bures_map(m0, S0, m1, S1):
    """Return (A, T) for the Gaussian OT (Brenier) map T(x) = m1 + A (x - m0)."""
    S0h = sqrtm_spd(S0)
    inner = sqrtm_spd(S0h @ S1 @ S0h)
    S0ih = invsqrtm_spd(S0)
    A = S0ih @ inner @ S0ih
    A = 0.5 * (A + A.T)  # symmetrize against numerical drift
    def T(x):
        return m1 + (np.asarray(x) - m0) @ A.T
    return A, T


def phi(x, m0, m1, A):
    """Convex potential whose gradient is T. Returns scalar per row of x."""
    xc = np.asarray(x) - m0
    quad = 0.5 * np.einsum("ni,ij,nj->n", xc, A, xc)
    return quad + np.asarray(x) @ m1


def main(outdir: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rng = np.random.default_rng(0)

    # Source and target Gaussians (2-D), chosen so the deformation is visible:
    # rotation + anisotropic stretch + translation.
    m0 = np.array([0.0, 0.0])
    S0 = np.array([[1.0, 0.0], [0.0, 1.0]])
    m1 = np.array([4.0, 2.0])
    theta = np.deg2rad(55)
    R = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    S1 = R @ np.diag([2.2**2, 0.5**2]) @ R.T

    A, T = bures_map(m0, S0, m1, S1)

    # Samples.
    L0 = sqrtm_spd(S0); L1 = sqrtm_spd(S1)
    n = 400
    Xs = m0 + rng.standard_normal((n, 2)) @ L0.T
    Yt = m1 + rng.standard_normal((n, 2)) @ L1.T
    TXs = T(Xs)

    fig, ax = plt.subplots(2, 2, figsize=(14, 12))

    # ---------- Panel A: "same shape up to a deformation" (warped grid) ----------
    a = ax[0, 0]
    g = np.linspace(-2.6, 2.6, 13)
    gx, gy = np.meshgrid(g, g)
    grid = np.c_[gx.ravel(), gy.ravel()]
    Tg = T(grid)
    Tgx = Tg[:, 0].reshape(gx.shape); Tgy = Tg[:, 1].reshape(gy.shape)
    # source grid (light) and its image (colored): a smooth, mass-preserving warp
    for i in range(gx.shape[0]):
        a.plot(gx[i, :], gy[i, :], color="0.8", lw=0.8)
        a.plot(gx[:, i], gy[:, i], color="0.8", lw=0.8)
    for i in range(Tgx.shape[0]):
        a.plot(Tgx[i, :], Tgy[i, :], color="tab:orange", lw=0.9)
        a.plot(Tgx[:, i], Tgy[:, i], color="tab:orange", lw=0.9)
    a.scatter(Xs[:, 0], Xs[:, 1], s=6, c="0.55", label="source grid/cloud")
    a.set_title('"Same shape up to a deformation":\nthe map smoothly warps the source grid (gray) into the target frame (orange)')
    a.set_aspect("equal"); a.legend(fontsize=8, loc="upper left")

    # ---------- Panel B: the convex potential + its gradient = the Brenier map ----------
    b = ax[0, 1]
    lo, hi = -3.0, 3.0
    xx, yy = np.meshgrid(np.linspace(lo, hi, 200), np.linspace(lo, hi, 200))
    P = phi(np.c_[xx.ravel(), yy.ravel()], m0, m1, A).reshape(xx.shape)
    cs = b.contourf(xx, yy, P, levels=30, cmap="viridis", alpha=0.85)
    fig.colorbar(cs, ax=b, fraction=0.046, pad=0.04, label="phi(x) (convex)")
    # gradient field grad phi = T - x mapped as displacement arrows at grid points
    qg = np.linspace(-2.4, 2.4, 9)
    qx, qy = np.meshgrid(qg, qg)
    q = np.c_[qx.ravel(), qy.ravel()]
    Tq = T(q)
    b.quiver(q[:, 0], q[:, 1], (Tq - q)[:, 0], (Tq - q)[:, 1],
             angles="xy", scale_units="xy", scale=1, color="white", width=0.004, alpha=0.9)
    b.set_title("The Brenier map T = grad(phi):\nphi is a convex bowl; its gradient (white arrows) IS the transport map")
    b.set_aspect("equal"); b.set_xlim(lo, hi); b.set_ylim(lo, hi)

    # ---------- Panel C: push-forward check + non-crossing transport rays ----------
    c = ax[1, 0]
    c.scatter(Yt[:, 0], Yt[:, 1], s=14, c="lightgray", label="target ν (human)")
    c.scatter(Xs[:, 0], Xs[:, 1], s=10, c="tab:blue", alpha=0.6, label="source μ (mouse)")
    c.scatter(TXs[:, 0], TXs[:, 1], s=10, c="tab:orange", alpha=0.6, label="T#μ (mapped)")
    idx = rng.choice(n, 40, replace=False)
    for i in idx:
        c.plot([Xs[i, 0], TXs[i, 0]], [Xs[i, 1], TXs[i, 1]], color="0.5", lw=0.5, alpha=0.7)
    c.set_title("Push-forward T#μ = ν (orange lands on gray).\nTransport rays never cross — the hallmark of a Brenier map (monotone)")
    c.set_aspect("equal"); c.legend(fontsize=8, loc="upper left")

    # ---------- Panel D: a DIFFERENT transport map (also μ→ν) that is NOT Brenier ----------
    d = ax[1, 1]
    # Compose T with an extra rotation about the target mean: still pushes a Gaussian
    # to (approximately) the same target for the isotropic-source case, but the rays
    # now cross => higher cost, not the gradient of a convex function.
    phi_tw = np.deg2rad(140)
    Rtw = np.array([[np.cos(phi_tw), -np.sin(phi_tw)], [np.sin(phi_tw), np.cos(phi_tw)]])
    # twist source around its own mean before applying T (source is isotropic => T#(twisted)=ν too)
    Xtw = m0 + (Xs - m0) @ Rtw.T
    TXtw = T(Xtw)
    d.scatter(Yt[:, 0], Yt[:, 1], s=14, c="lightgray", label="target ν")
    d.scatter(Xs[:, 0], Xs[:, 1], s=10, c="tab:blue", alpha=0.6, label="source μ")
    for i in idx:
        d.plot([Xs[i, 0], TXtw[i, 0]], [Xs[i, 1], TXtw[i, 1]], color="tab:red", lw=0.5, alpha=0.7)
    d.set_title("A NON-optimal transport map (also pushes μ→ν):\nrays CROSS, costs more — a valid transport map but NOT the Brenier map")
    d.set_aspect("equal"); d.legend(fontsize=8, loc="upper left")

    fig.tight_layout()
    out = outdir / "brenier_illustration.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    print(f"wrote {out}")
    print(f"Bures map A =\n{A}")
    print(f"mean transport cost (Brenier)     = {np.mean(np.sum((TXs-Xs)**2,1)):.3f}")
    print(f"mean transport cost (twisted map) = {np.mean(np.sum((TXtw-Xs)**2,1)):.3f}")


if __name__ == "__main__":
    main(Path(__file__).parent / "results")

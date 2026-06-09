"""Per-gene marginal divergences (KL / Jensen-Shannon) between two cell clouds.

Why marginal (per-gene) and not joint:
- A full 1000-d KL would need joint density estimation, which is infeasible in
  high dimensions and undefined wherever the two supports do not overlap.
- The biologically interpretable, Figure-G-style quantity is the *marginal*
  divergence: for each gene, compare the 1-D distribution of `treated` vs
  `imputed` (binned), then summarize across genes.

MMD remains the joint metric (it captures gene-gene structure that marginals
miss); KL/JS here is the complementary per-gene view.

Conventions:
- KL is asymmetric and unstable when a bin has zero mass, so we histogram both
  clouds on a *shared* binning and add a small `eps` (Laplace smoothing).
- Jensen-Shannon (`js`) is symmetric and bounded; with natural log it lies in
  [0, ln 2 ~= 0.693]. It is the headline number.
"""

import numpy as np


def _hist_prob(x, bins, eps):
    h, _ = np.histogram(x, bins=bins)
    p = h.astype(float) + eps
    return p / p.sum()


def compute_marginal_divergence(treated, imputed, n_bins=50, eps=1e-6):
    """Per-gene KL/JS between the `treated` and `imputed` marginal distributions.

    Parameters
    ----------
    treated, imputed : array-like, shape (n_cells, n_genes)
        Must share the same gene axis (same n_genes, same order).
    n_bins : int
        Number of shared histogram bins per gene.
    eps : float
        Laplace smoothing added to every bin to keep KL finite.

    Returns
    -------
    dict with:
        per_gene : np.ndarray (n_genes, 3) columns [kl_treated_imputed,
                   kl_imputed_treated, js]
        kl_treated_imputed, kl_imputed_treated, js : per-gene arrays
        mean_kl_treated_imputed, mean_kl_imputed_treated, mean_js : floats
    """
    T = np.asarray(treated, dtype=float)
    I = np.asarray(imputed, dtype=float)
    if T.shape[1] != I.shape[1]:
        raise ValueError(f"gene-axis mismatch: {T.shape[1]} vs {I.shape[1]}")
    n_genes = T.shape[1]

    kl_ti = np.zeros(n_genes)
    kl_it = np.zeros(n_genes)
    js = np.zeros(n_genes)

    for g in range(n_genes):
        tg, ig = T[:, g], I[:, g]
        lo = min(tg.min(), ig.min())
        hi = max(tg.max(), ig.max())
        if not (hi > lo):  # constant gene across both clouds -> zero divergence
            continue
        bins = np.linspace(lo, hi, n_bins + 1)
        p = _hist_prob(tg, bins, eps)
        q = _hist_prob(ig, bins, eps)
        m = 0.5 * (p + q)
        kl_ti[g] = float(np.sum(p * np.log(p / q)))
        kl_it[g] = float(np.sum(q * np.log(q / p)))
        js[g] = float(0.5 * np.sum(p * np.log(p / m)) + 0.5 * np.sum(q * np.log(q / m)))

    return {
        "per_gene": np.stack([kl_ti, kl_it, js], axis=1),
        "kl_treated_imputed": kl_ti,
        "kl_imputed_treated": kl_it,
        "js": js,
        "mean_kl_treated_imputed": float(kl_ti.mean()),
        "mean_kl_imputed_treated": float(kl_it.mean()),
        "mean_js": float(js.mean()),
    }

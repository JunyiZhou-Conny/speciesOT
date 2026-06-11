"""Build mentor-ready transport UMAP panels from cached eval clouds.

For each v08 cut we load eval_clouds.npz (control = mouse start, treated = real
human, imputed = model prediction), fit ONE shared UMAP on the concatenation
(PCA->UMAP), and plot the three clouds in that shared embedding. The money shot:
how far the model moved mouse cells toward the real human population.

Run with the analysis env python (has umap-learn):
    /n/home01/jzhou1125/miniforge3/envs/analysis/bin/python scripts/make_transport_umaps.py
"""
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import umap

ROOT = Path("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT")
RESULTS = ROOT / "cellot/cellot_gpu/results"
OUTDIR = ROOT / "speciesOT/baseline/analysis/v08_transport_umaps"
OUTDIR.mkdir(parents=True, exist_ok=True)

CUTS = [
    ("m1 v08 OOD", "hvg_pearson_residuals_m1_v08_ood"),
    ("m2 v08 OOD", "hvg_pearson_residuals_m2_v08_ood"),
    ("uncapped v08 OOD", "hvg_pearson_residuals_a_uncapped_v08_ood"),
]

COLORS = {
    "mouse start":   "#9aa0a6",   # grey
    "real human":    "#1a73e8",   # blue
    "model pred":    "#e8710a",   # orange
}


def r2_of_means(a, b):
    r = np.corrcoef(np.asarray(a).mean(0), np.asarray(b).mean(0))[0, 1]
    return float(r * r)


def embed(control, treated, imputed, seed=0):
    X = np.vstack([control, treated, imputed]).astype(np.float32)
    Xs = StandardScaler().fit_transform(X)
    n_comp = min(50, Xs.shape[0] - 1, Xs.shape[1])
    Xp = PCA(n_components=n_comp, random_state=seed).fit_transform(Xs)
    reducer = umap.UMAP(n_neighbors=15, min_dist=0.3, random_state=seed)
    emb = reducer.fit_transform(Xp)
    nc, nt = len(control), len(treated)
    return emb[:nc], emb[nc:nc + nt], emb[nc + nt:]


# Two rows: raw frame (the misleading one) on top, honest decoded frame below.
fig, axes = plt.subplots(2, len(CUTS), figsize=(6.0 * len(CUTS), 11.0))

for col, (label, tag) in enumerate(CUTS):
    base = RESULTS / tag / "impact_cellot/evals_ood_data_space"
    z = np.load(base / "eval_clouds.npz", allow_pickle=False)
    zd = np.load(base / "eval_clouds_decoded.npz", allow_pickle=False)
    control, treated, imputed = z["control"], z["treated"], z["imputed"]
    control_dec, treated_dec = zd["control_decoded"], zd["treated_decoded"]

    # --- Row 0: RAW frame (imputed is decoded, refs are raw -> apples-to-oranges) ---
    e_ctrl, e_treat, e_imp = embed(control, treated, imputed)
    ax = axes[0, col]
    ax.scatter(e_ctrl[:, 0], e_ctrl[:, 1], s=22, alpha=0.5, c=COLORS["mouse start"],
               label="mouse start (raw)", edgecolors="none")
    ax.scatter(e_treat[:, 0], e_treat[:, 1], s=26, alpha=0.7, c=COLORS["real human"],
               label="real human (raw)", edgecolors="none")
    ax.scatter(e_imp[:, 0], e_imp[:, 1], s=26, alpha=0.7, c=COLORS["model pred"],
               label="model pred (decoded)", edgecolors="none")
    ax.set_title(f"{label} — RAW frame (misleading)", fontsize=11)
    ax.set_xticks([]); ax.set_yticks([])

    # --- Row 1: DECODED frame (all clouds AE round-tripped -> fair) ---
    e_ctrl2, e_treat2, e_imp2 = embed(control_dec, treated_dec, imputed)
    ax2 = axes[1, col]
    ax2.scatter(e_ctrl2[:, 0], e_ctrl2[:, 1], s=22, alpha=0.5, c=COLORS["mouse start"],
                label="mouse start (decoded)", edgecolors="none")
    ax2.scatter(e_treat2[:, 0], e_treat2[:, 1], s=26, alpha=0.7, c=COLORS["real human"],
                label="real human (decoded = honest target)", edgecolors="none")
    ax2.scatter(e_imp2[:, 0], e_imp2[:, 1], s=26, alpha=0.7, c=COLORS["model pred"],
                label="model pred (decoded)", edgecolors="none")
    r2_model = r2_of_means(imputed, treated)
    r2_identity = r2_of_means(control, treated)
    ax2.set_title(f"{label} — DECODED frame (fair)\n"
                  f"R²(pred,human)={r2_model:.2f}  vs  R²(mouse,human)={r2_identity:.2f}",
                  fontsize=11)
    ax2.set_xticks([]); ax2.set_yticks([])
    print(f"{label}: n={len(control)}/{len(treated)}/{len(imputed)}  "
          f"R2_model={r2_model:.3f} R2_identity={r2_identity:.3f}", flush=True)

axes[0, 0].legend(loc="best", fontsize=8, framealpha=0.9)
axes[1, 0].legend(loc="best", fontsize=8, framealpha=0.9)
fig.suptitle(
    "Cross-species transport (mouse \u2192 human), v08 held-out monocytes\n"
    "TOP: raw frame — prediction (orange) can't overlap raw human (blue) because of the AE "
    "offset (the artifact).\n"
    "BOTTOM: same clouds in decoded space — orange now lands on blue = the model actually "
    "transports mouse onto human.",
    fontsize=12, y=1.01)
fig.tight_layout()
out = OUTDIR / "transport_umap_v08_panel.png"
fig.savefig(out, dpi=150, bbox_inches="tight")
print(f"\nwrote {out}", flush=True)

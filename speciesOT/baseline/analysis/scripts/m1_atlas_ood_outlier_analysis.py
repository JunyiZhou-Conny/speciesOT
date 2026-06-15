#!/usr/bin/env python
"""Atlas-reference outlier investigation for M1 human OOD non-classical monocytes.

Focus: the 207 red dots in umap_atlas_ref_m1_ood_pearson_scgen_impact.png.
Outputs -> speciesOT/baseline/analysis/m1_atlas_ood_investigation/
"""
from __future__ import annotations

from pathlib import Path

import anndata as ad
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scanpy as sc
from sklearn.model_selection import train_test_split
from sklearn.neighbors import NearestNeighbors

REPO = Path("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT")
CELL_GPU = REPO / "cellot/cellot_gpu"
OUT = REPO / "speciesOT/baseline/analysis/m1_atlas_ood_investigation"
OUT.mkdir(parents=True, exist_ok=True)

HOLDOUT = "CL:0000875"
CT = "cell_type_ontology_term_id"
SRC = {
    "mouse": "/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_muris/sampled_mouse_shared.h5ad",
    "human": "/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_sapiens/sampled_human_shared.h5ad",
}


def _x_dense(X):
    return X.toarray() if hasattr(X, "toarray") else np.asarray(X)


def add_transport(adata, source="mouse", target="human", condition_col="condition"):
    m = {source: "source", target: "target"}
    out = adata.copy()
    out.obs = out.obs.copy()
    out.obs["transport"] = out.obs[condition_col].map(m)
    return out[out.obs["transport"].notna()].copy()


def split_toggle_ood(adata, groupby, holdout, key, mode, random_state=0, test_size=0.2):
    split = pd.Series(index=adata.obs_names, dtype=object)
    for _, idx in adata.obs.groupby(groupby, observed=False).groups.items():
        tr, te = train_test_split(idx, random_state=random_state, test_size=test_size)
        split.loc[tr] = "train"
        split.loc[te] = "test"
    hv = [holdout] if isinstance(holdout, str) else list(holdout)
    ood_ix = adata.obs_names[adata.obs[key].isin(hv)]
    a, b = train_test_split(ood_ix, random_state=random_state, test_size=0.5)
    if mode == "ood":
        split.loc[a] = "ignore"
        split.loc[b] = "ood"
    else:
        split.loc[a] = "train"
        split.loc[b] = "ood"
    adata.obs["split"] = split.astype("category")
    return adata


def lookup_assay(obs_names, condition):
    assay = pd.Series(index=obs_names, dtype=object)
    for sp, p in SRC.items():
        s = ad.read_h5ad(p, backed="r")
        nm = obs_names[condition == sp]
        inter = nm.intersection(s.obs_names)
        assay.loc[inter] = s.obs.loc[inter, "assay"].astype(str).values
    return assay


def project_onto_ref_umap(pred_X, ref_adata, n_neighbors=10, return_knn=False):
    pcs = ref_adata.varm["PCs"]
    ref_pca = ref_adata.obsm["X_pca"]
    ref_umap = ref_adata.obsm["X_umap"]
    ref_mean = np.asarray(ref_adata.X.mean(axis=0)).ravel()
    pred_X = np.asarray(pred_X, dtype=np.float32)
    pred_pca = (pred_X - ref_mean) @ pcs
    k = min(n_neighbors, max(1, ref_pca.shape[0] - 1))
    nn = NearestNeighbors(n_neighbors=k, metric="euclidean")
    nn.fit(ref_pca)
    dists, idxs = nn.kneighbors(pred_pca)
    w = 1.0 / (dists + 1e-8)
    w = w / w.sum(axis=1, keepdims=True)
    umap = np.array([(w[i, :, None] * ref_umap[idxs[i]]).sum(axis=0) for i in range(len(pred_pca))])
    if return_knn:
        return umap, pred_pca, dists[:, 0], idxs[:, 0]
    return umap


def build_atlas_ref(h5_path):
    d = split_toggle_ood(
        add_transport(ad.read_h5ad(h5_path)), groupby="condition", holdout=HOLDOUT,
        key=CT, mode="ood", random_state=0, test_size=0.2,
    )
    ref = d[d.obs["split"] == "train"].copy()
    ref.X = _x_dense(ref.X).astype(np.float32)
    tr = ref.obs["transport"].astype(str)
    ref.obs["atlas_species"] = np.where(tr == "source", "mouse", "human")
    n_pcs = int(min(50, ref.n_vars - 1, max(2, ref.n_obs - 1)))
    sc.pp.pca(ref, n_comps=n_pcs)
    sc.pp.neighbors(ref, n_neighbors=min(15, max(2, ref.n_obs - 1)), n_pcs=n_pcs)
    sc.tl.umap(ref, min_dist=0.3, random_state=42)
    return d, ref


def flag_outliers(umap_coords, pca_coords, quantile=0.85):
    """Edge cells in projected UMAP + PCA within-holdout distance."""
    centroid_u = umap_coords.mean(axis=0)
    dist_u = np.linalg.norm(umap_coords - centroid_u, axis=1)
    thr_u = np.quantile(dist_u, quantile)
    centroid_p = pca_coords.mean(axis=0)
    dist_p = np.linalg.norm(pca_coords - centroid_p, axis=1)
    thr_p = np.quantile(dist_p, quantile)
    edge_umap = dist_u > thr_u
    edge_pca = dist_p > thr_p
    return dist_u, dist_p, edge_umap, edge_pca


def analyze_dataset(label, h5_path):
    d, ref = build_atlas_ref(h5_path)
    ct = d.obs[CT].astype(str)
    ood_h_mask = (d.obs["split"] == "ood") & ct.eq(HOLDOUT) & (d.obs["transport"] == "target")
    human = d[ood_h_mask].copy()
    human.X = _x_dense(human.X).astype(np.float32)

    u_proj, pred_pca, knn1_dist, knn1_idx = project_onto_ref_umap(
        human.X, ref, return_knn=True,
    )
    # Isolated embedding (human OOD only, no atlas dilution)
    iso = human.copy()
    n_pcs = int(min(50, iso.n_obs - 1, iso.n_vars - 1))
    sc.pp.pca(iso, n_comps=n_pcs)
    sc.pp.neighbors(iso, n_neighbors=min(15, max(2, iso.n_obs - 1)), n_pcs=min(30, n_pcs))
    sc.tl.umap(iso, min_dist=0.3, random_state=42)

    dist_u, dist_p, edge_umap, edge_pca = flag_outliers(u_proj, pred_pca)
    assay = lookup_assay(human.obs_names, human.obs["condition"].astype(str))
    nn_species = ref.obs["atlas_species"].astype(str).values[knn1_idx]

    tbl = human.obs.copy()
    tbl["umap1_proj"] = u_proj[:, 0]
    tbl["umap2_proj"] = u_proj[:, 1]
    tbl["umap1_iso"] = iso.obsm["X_umap"][:, 0]
    tbl["umap2_iso"] = iso.obsm["X_umap"][:, 1]
    tbl["dist_umap_proj"] = dist_u
    tbl["dist_pca_holdout"] = dist_p
    tbl["knn1_pca_dist"] = knn1_dist
    tbl["knn1_atlas_species"] = nn_species
    tbl["edge_umap_top15pct"] = edge_umap
    tbl["edge_pca_top15pct"] = edge_pca
    tbl["assay"] = assay.values
    tbl["tech"] = np.where(tbl["assay"].astype(str).str.contains("Smart", na=False), "Smart-seq2", "10x")
    tbl["edge_either"] = edge_umap | edge_pca
    tbl["dataset"] = label
    return tbl, ref, u_proj, iso


def main():
    datasets = {
        "m1_v07": CELL_GPU / "datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_m1_v07.h5ad",
        "m1_v08": CELL_GPU / "datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_m1_v08.h5ad",
    }

    tables = []
    refs = {}
    umaps = {}
    isos = {}
    for label, path in datasets.items():
        if not path.exists():
            print(f"skip {label}: missing {path}")
            continue
        tbl, ref, u_proj, iso = analyze_dataset(label, path)
        tables.append(tbl)
        refs[label] = ref
        umaps[label] = u_proj
        isos[label] = iso
        tbl.to_csv(OUT / f"human_ood_cell_table_{label}.csv")
        print(f"\n=== {label}: n={len(tbl)} human OOD ===")
        print("assay counts:\n", tbl["assay"].value_counts(dropna=False))
        print("\nedge_umap top15%:", int(tbl["edge_umap_top15pct"].sum()))
        print("edge_pca top15%:", int(tbl["edge_pca_top15pct"].sum()))
        print("Smart-seq2 fraction:", (tbl["tech"] == "Smart-seq2").mean())
        print("\nedge_umap x tech:\n", pd.crosstab(tbl["edge_umap_top15pct"], tbl["tech"]))
        print("\ndonor x edge_umap (donors with >=5 cells):")
        ddon = tbl.groupby("donor_id").agg(
            n=("donor_id", "size"),
            edge_frac=("edge_umap_top15pct", "mean"),
            smart_frac=("tech", lambda s: (s == "Smart-seq2").mean()),
        )
        print(ddon[ddon["n"] >= 5].sort_values("edge_frac", ascending=False).head(12).round(3))

    if not tables:
        return

    # --- Figure 1: v07 atlas-ref with outlier flags + assay ---
    tbl = tables[0]
    label0 = list(datasets.keys())[0]
    ref = refs[label0]
    u_proj = umaps[label0]
    cmap = plt.get_cmap("tab20")

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    ur = ref.obsm["X_umap"]
    for sp, c in [("mouse", "#aec7e8"), ("human", "#98df8a")]:
        m = ref.obs["atlas_species"].astype(str) == sp
        axes[0, 0].scatter(ur[m, 0], ur[m, 1], s=4, c=c, alpha=0.25, edgecolors="none")
    for flag, c, lab in [(False, "#d62728", "core blob"), (True, "#ff7f0e", "UMAP edge (top 15%)")]:
        m = tbl["edge_umap_top15pct"].values == flag
        axes[0, 0].scatter(u_proj[m, 0], u_proj[m, 1], s=28, c=c, alpha=0.9, edgecolors="none", label=f"{lab} (n={m.sum()})")
    axes[0, 0].set_title("Atlas-ref: human OOD colored by UMAP-edge flag")
    axes[0, 0].legend(fontsize=8)

    for i, tech in enumerate(["10x", "Smart-seq2"]):
        m = (tbl["tech"] == tech).values
        axes[0, 1].scatter(u_proj[m, 0], u_proj[m, 1], s=28, color=cmap(i), alpha=0.9, edgecolors="none",
                           label=f"{tech} (n={m.sum()})")
    axes[0, 1].set_title("Atlas-ref: colored by sequencing tech")
    axes[0, 1].legend(fontsize=8)

    # TSP2 vs others
    is_tsp2 = (tbl["donor_id"].astype(str) == "TSP2").values
    axes[1, 0].scatter(u_proj[~is_tsp2, 0], u_proj[~is_tsp2, 1], s=20, c="#bdbdbd", alpha=0.7, edgecolors="none", label=f"other donors (n={(~is_tsp2).sum()})")
    axes[1, 0].scatter(u_proj[is_tsp2, 0], u_proj[is_tsp2, 1], s=28, c="#e6550d", alpha=0.9, edgecolors="none", label=f"TSP2 (n={is_tsp2.sum()})")
    axes[1, 0].set_title("Atlas-ref: TSP2 vs other donors")
    axes[1, 0].legend(fontsize=8)

    # kNN projection distance (PCA distance to nearest atlas cell)
    sca = axes[1, 1].scatter(u_proj[:, 0], u_proj[:, 1], s=28, c=tbl["knn1_pca_dist"], cmap="viridis", alpha=0.9, edgecolors="none")
    plt.colorbar(sca, ax=axes[1, 1], label="PCA dist to nearest atlas cell")
    axes[1, 1].set_title("Atlas-ref: kNN projection stretch")

    for ax in axes.ravel():
        ax.set_xlabel("UMAP1")
        ax.set_ylabel("UMAP2")
    fig.suptitle("M1 v07 — 207 human OOD non-classical monocytes (atlas-reference UMAP)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "fig1_atlas_ref_outlier_flags_v07.png", dpi=200, bbox_inches="tight")
    print(f"\nsaved {OUT / 'fig1_atlas_ref_outlier_flags_v07.png'}")

    # --- Figure 2: projected vs isolated embedding ---
    iso = isos[label0]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
    Uiso = iso.obsm["X_umap"]
    for flag, c, lab in [(False, "#d62728", "core"), (True, "#ff7f0e", "UMAP edge")]:
        m = tbl["edge_umap_top15pct"].values == flag
        axes[0].scatter(u_proj[m, 0], u_proj[m, 1], s=24, c=c, alpha=0.9, edgecolors="none", label=lab)
        axes[1].scatter(Uiso[m, 0], Uiso[m, 1], s=24, c=c, alpha=0.9, edgecolors="none", label=lab)
    axes[0].set_title("Projected onto atlas UMAP (train-only fit)")
    axes[1].set_title("Isolated UMAP (human OOD only, 207 cells)")
    for ax in axes:
        ax.set_xlabel("UMAP1"); ax.set_ylabel("UMAP2"); ax.legend(fontsize=8)
    fig.suptitle("Same edge flags: is scatter a projection artifact?", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "fig2_projected_vs_isolated_v07.png", dpi=200, bbox_inches="tight")
    print(f"saved {OUT / 'fig2_projected_vs_isolated_v07.png'}")

    # --- Figure 3: v07 vs v08 if both exist ---
    if len(tables) == 2:
        t07, t08 = tables
        fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
        for ax, t, title in [
            (axes[0], t07, f"v07 unfiltered (n={len(t07)})"),
            (axes[1], t08, f"v08 assay-filtered (n={len(t08)})"),
        ]:
            u = t[["umap1_proj", "umap2_proj"]].values
            for tech, c in [("10x", "#d62728"), ("Smart-seq2", "#ff7f0e")]:
                m = (t["tech"] == tech).values
                ax.scatter(u[m, 0], u[m, 1], s=24, c=c, alpha=0.9, edgecolors="none", label=f"{tech} (n={m.sum()})")
            ax.set_title(title); ax.legend(fontsize=8)
            ax.set_xlabel("UMAP1"); ax.set_ylabel("UMAP2")
        fig.suptitle("Assay filter effect on human OOD atlas-ref coordinates", fontweight="bold")
        fig.tight_layout()
        fig.savefig(OUT / "fig3_v07_vs_v08_assay_filter.png", dpi=200, bbox_inches="tight")
        print(f"saved {OUT / 'fig3_v07_vs_v08_assay_filter.png'}")

        # Summary table
        summary_rows = []
        for t, lab in [(t07, "m1_v07"), (t08, "m1_v08")]:
            summary_rows.append({
                "dataset": lab,
                "n_human_ood": len(t),
                "n_smartseq2": int((t["tech"] == "Smart-seq2").sum()),
                "pct_smartseq2": round((t["tech"] == "Smart-seq2").mean() * 100, 1),
                "n_umap_edge": int(t["edge_umap_top15pct"].sum()),
                "pct_umap_edge": round(t["edge_umap_top15pct"].mean() * 100, 1),
                "mean_knn1_pca_dist": round(t["knn1_pca_dist"].mean(), 3),
                "median_umap_dist": round(t["dist_umap_proj"].median(), 3),
            })
        summary = pd.DataFrame(summary_rows)
        summary.to_csv(OUT / "v07_v08_summary.csv", index=False)
        print("\nv07 vs v08 summary:\n", summary.to_string(index=False))

    # --- Figure 4: joint UMAP (OOD included in fit) vs atlas-ref ---
    h5 = datasets["m1_v07"]
    d, _ = build_atlas_ref(h5)
    ct = d.obs[CT].astype(str)
    ood_h = (d.obs["split"] == "ood") & ct.eq(HOLDOUT) & (d.obs["transport"] == "target")
    train = d[d.obs["split"] == "train"].copy()
    hold = d[ood_h].copy()
    joint = ad.concat([train, hold], join="inner")
    joint.X = _x_dense(joint.X).astype(np.float32)
    joint.obs["role"] = np.where(joint.obs_names.isin(hold.obs_names), "human_ood", "atlas_train")
    n_pcs = int(min(50, joint.n_vars - 1, max(2, joint.n_obs - 1)))
    sc.pp.pca(joint, n_comps=n_pcs)
    sc.pp.neighbors(joint, n_neighbors=15, n_pcs=n_pcs)
    sc.tl.umap(joint, min_dist=0.3, random_state=42)
    Uj = joint.obsm["X_umap"]
    is_ood = joint.obs["role"].astype(str) == "human_ood"

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    m = ~is_ood.values
    axes[0].scatter(Uj[m, 0], Uj[m, 1], s=3, c="#cccccc", alpha=0.3, edgecolors="none")
    axes[0].scatter(u_proj[:, 0], u_proj[:, 1], s=24, c="#d62728", alpha=0.9, edgecolors="none", label="human OOD (projected)")
    axes[0].set_title("Atlas-ref projection (train-only UMAP fit)")
    axes[1].scatter(Uj[~is_ood.values, 0], Uj[~is_ood.values, 1], s=3, c="#cccccc", alpha=0.3, edgecolors="none")
    axes[1].scatter(Uj[is_ood.values, 0], Uj[is_ood.values, 1], s=24, c="#d62728", alpha=0.9, edgecolors="none", label="human OOD (joint fit)")
    axes[1].set_title("Joint UMAP (OOD cells included in fit)")
    for ax in axes:
        ax.set_xlabel("UMAP1"); ax.set_ylabel("UMAP2"); ax.legend(fontsize=8)
    fig.suptitle("Does kNN projection create the tail? (v07)", fontweight="bold")
    fig.tight_layout()
    fig.savefig(OUT / "fig4_projection_vs_joint_umap.png", dpi=200, bbox_inches="tight")
    print(f"saved {OUT / 'fig4_projection_vs_joint_umap.png'}")

    # TSP2 within-donor edge analysis
    tsp2 = tbl[tbl["donor_id"].astype(str) == "TSP2"].copy()
    if len(tsp2) > 0:
        tsp2_report = tsp2.groupby("edge_umap_top15pct").agg(
            n=("donor_id", "size"),
            mean_knn_dist=("knn1_pca_dist", "mean"),
            smartseq2=("tech", lambda s: (s == "Smart-seq2").sum()),
        )
        tsp2_report.to_csv(OUT / "tsp2_edge_breakdown.csv")
        print("\nTSP2 edge breakdown:\n", tsp2_report)

    # List the actual edge cells for manual inspection
    edge_cells = tbl[tbl["edge_umap_top15pct"]].sort_values("dist_umap_proj", ascending=False)
    edge_cells.to_csv(OUT / "edge_cells_ranked_v07.csv")
    print(f"\nTop edge cells saved ({len(edge_cells)} rows) -> edge_cells_ranked_v07.csv")
    print(edge_cells[["donor_id", "assay", "tech", "dist_umap_proj", "knn1_pca_dist", "knn1_atlas_species"]].head(15).to_string())


if __name__ == "__main__":
    main()

"""
Reusable UMAP visualization pipeline for speciesOT.

Two-step workflow:
  1. compute_and_save_umap() — PCA, neighbors, UMAP, marker genes, projection.
     Saves everything to a single .npz file.
  2. generate_interactive_plots() — loads .npz, produces Plotly HTML files.

Both steps run in the `analysis` conda env.
"""

import numpy as np
import pandas as pd
import anndata
import scanpy as sc
from pathlib import Path
from scipy import sparse


# ─── Step 1: Compute ──────────────────────────────────────────────────────────

def _to_dense(X):
    if sparse.issparse(X):
        return np.array(X.todense())
    return np.array(X)


def compute_and_save_umap(
    data_path,
    output_path,
    predictions=None,
    n_comps=50,
    n_neighbors=15,
    min_dist=0.3,
    random_state=42,
    marker_groupby="cell_type",
    n_marker_genes=10,
):
    """Compute reference UMAP + marker genes, project predictions, save to .npz.

    Parameters
    ----------
    data_path : str or Path
        Path to the full dataset h5ad file.
    output_path : str or Path
        Where to save the .npz file.
    predictions : dict or None
        Mapping of model_name -> path to imputed.h5ad.
    n_comps : int
        Number of PCA components (default 50, scanpy default).
    n_neighbors : int
        Number of neighbors for the neighbor graph (default 15, scanpy default).
    min_dist : float
        UMAP min_dist parameter (default 0.3).
    random_state : int
        Random seed for reproducibility.
    marker_groupby : str
        obs column for rank_genes_groups.
    n_marker_genes : int
        Number of top marker genes per group to save.
    """
    data_path = Path(data_path)
    output_path = Path(output_path)

    print(f"Loading data from {data_path} ...")
    full_data = anndata.read_h5ad(str(data_path))

    ref = full_data.copy()
    ref.X = _to_dense(ref.X).astype(np.float32)

    print(f"Computing PCA (n_comps={n_comps}) ...")
    sc.pp.pca(ref, n_comps=n_comps)

    print(f"Computing neighbors (n_neighbors={n_neighbors}, n_pcs={n_comps}) ...")
    sc.pp.neighbors(ref, n_pcs=n_comps, n_neighbors=n_neighbors)

    print(f"Computing UMAP (min_dist={min_dist}, random_state={random_state}) ...")
    sc.tl.umap(ref, min_dist=min_dist, random_state=random_state)

    print(f"UMAP done: {ref.obsm['X_umap'].shape}")

    print(f"Computing marker genes (groupby={marker_groupby}) ...")
    try:
        sc.tl.rank_genes_groups(ref, groupby=marker_groupby, method="wilcoxon")
        marker_results = {}
        for group in ref.obs[marker_groupby].unique():
            df = sc.get.rank_genes_groups_df(ref, group=group).head(n_marker_genes)
            marker_results[group] = {
                "names": df["names"].tolist(),
                "scores": df["scores"].tolist(),
                "logfoldchanges": df["logfoldchanges"].tolist(),
            }
    except Exception as e:
        print(f"  Warning: rank_genes_groups failed: {e}")
        marker_results = {}

    save_dict = {
        "ref_umap": ref.obsm["X_umap"],
        "ref_X": ref.X,
        "ref_pca": ref.obsm["X_pca"],
        "pcs": ref.varm["PCs"],
        "var_names": np.array(ref.var_names.tolist(), dtype=str),
    }

    obs_cols = [c for c in ref.obs.columns if ref.obs[c].dtype == object or str(ref.obs[c].dtype) == "category"]
    for col in obs_cols:
        save_dict[f"obs_{col}"] = np.array(ref.obs[col].astype(str).tolist(), dtype=str)
    save_dict["obs_index"] = np.array(ref.obs.index.astype(str).tolist(), dtype=str)
    save_dict["obs_columns"] = np.array(obs_cols, dtype=str)

    if predictions:
        for model_name, pred_path in predictions.items():
            pred_path = Path(pred_path)
            if not pred_path.exists():
                print(f"  {model_name}: {pred_path} not found, skipping")
                continue
            pred = anndata.read_h5ad(str(pred_path))
            pred.var_names = ref.var_names.copy()
            query = pred.copy()
            query.X = _to_dense(query.X).astype(np.float32)
            print(f"  Projecting {model_name} ({query.n_obs} cells) via sc.tl.ingest ...")
            sc.tl.ingest(query, ref, embedding_method=("umap", "pca"))
            save_dict[f"pred_{model_name}_umap"] = query.obsm["X_umap"]
            save_dict[f"pred_{model_name}_n"] = np.array([query.n_obs])
            print(f"  {model_name}: projected")

    import json
    save_dict["marker_results_json"] = np.array([json.dumps(marker_results)], dtype=str)

    np.savez_compressed(str(output_path), **save_dict)
    print(f"\nSaved to {output_path} ({output_path.stat().st_size / 1e6:.1f} MB)")


# ─── Step 2: Visualize ────────────────────────────────────────────────────────

def _load_npz(npz_path):
    """Load .npz and reconstruct obs DataFrame."""
    data = np.load(str(npz_path), allow_pickle=True)

    obs_cols = data["obs_columns"].tolist()
    obs_dict = {col: data[f"obs_{col}"].tolist() for col in obs_cols}
    obs_df = pd.DataFrame(obs_dict, index=data["obs_index"].tolist())

    import json
    markers_json = data["marker_results_json"][0]
    marker_results = json.loads(markers_json) if markers_json else {}

    pred_names = []
    for key in data.files:
        if key.startswith("pred_") and key.endswith("_umap"):
            name = key[5:-5]
            pred_names.append(name)

    return {
        "ref_umap": data["ref_umap"],
        "ref_X": data["ref_X"],
        "obs": obs_df,
        "var_names": data["var_names"].tolist(),
        "marker_results": marker_results,
        "predictions": {name: data[f"pred_{name}_umap"] for name in pred_names},
    }


def generate_interactive_plots(npz_path, output_dir, holdout_ct_id=None):
    """Generate all interactive Plotly HTML files from saved .npz.

    Parameters
    ----------
    npz_path : str or Path
        Path to the .npz from compute_and_save_umap.
    output_dir : str or Path
        Directory to write HTML files.
    holdout_ct_id : str or None
        Cell type ontology ID for holdout (e.g. "CL:0000625" for CD8).
        Used to color source/target/predicted in model prediction plots.
    """
    import plotly.graph_objects as go

    npz_path = Path(npz_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    d = _load_npz(npz_path)
    umap = d["ref_umap"]
    obs = d["obs"]

    ct_col = "cell_type" if "cell_type" in obs.columns else "cell_type_ontology_term_id"

    # ── A. All cell types (interactive, toggle via legend) ─────────────────
    fig = go.Figure()
    cell_types = obs[ct_col].unique()
    for ct in sorted(cell_types):
        mask = obs[ct_col].values == ct
        n = mask.sum()
        hover = [
            f"<b>{ct}</b><br>Condition: {c}<br>Tissue: {t}<br>Donor: {dn}<br>UMAP: ({x:.2f}, {y:.2f})"
            for c, t, dn, x, y in zip(
                obs.get("condition", pd.Series(["N/A"] * len(obs))).values[mask],
                obs.get("tissue", pd.Series(["N/A"] * len(obs))).values[mask],
                obs.get("donor_id", pd.Series(["N/A"] * len(obs))).values[mask],
                umap[mask, 0], umap[mask, 1],
            )
        ]
        fig.add_trace(go.Scattergl(
            x=umap[mask, 0], y=umap[mask, 1],
            mode="markers", marker=dict(size=4, opacity=0.7),
            name=f"{ct} (n={n})",
            hovertext=hover, hoverinfo="text",
        ))

    fig.update_layout(
        title="All Cell Types — Click legend to toggle",
        xaxis_title="UMAP 1", yaxis_title="UMAP 2",
        plot_bgcolor="white", width=1200, height=900,
        legend=dict(font=dict(size=10), itemsizing="constant"),
        xaxis=dict(showgrid=False, zeroline=False),
        yaxis=dict(showgrid=False, zeroline=False),
    )
    out = output_dir / "interactive_all_celltypes.html"
    fig.write_html(str(out), auto_open=False)
    print(f"Saved: {out}")

    # ── B. Species overlay (toggle mouse/human) ───────────────────────────
    if "condition" in obs.columns:
        fig = go.Figure()
        for cond, color in [("mouse", "#4A90D9"), ("human", "#D94A4A")]:
            mask = obs["condition"].values == cond
            hover = [
                f"<b>{cond}</b><br>Cell type: {ct}<br>Tissue: {t}<br>UMAP: ({x:.2f}, {y:.2f})"
                for ct, t, x, y in zip(
                    obs[ct_col].values[mask],
                    obs.get("tissue", pd.Series(["N/A"] * len(obs))).values[mask],
                    umap[mask, 0], umap[mask, 1],
                )
            ]
            fig.add_trace(go.Scattergl(
                x=umap[mask, 0], y=umap[mask, 1],
                mode="markers", marker=dict(size=4, color=color, opacity=0.6),
                name=f"{cond} (n={mask.sum()})",
                hovertext=hover, hoverinfo="text",
            ))

        fig.update_layout(
            title="Species Overlay — Click legend to toggle mouse/human",
            xaxis_title="UMAP 1", yaxis_title="UMAP 2",
            plot_bgcolor="white", width=1100, height=900,
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=False, zeroline=False),
        )
        out = output_dir / "interactive_species_overlay.html"
        fig.write_html(str(out), auto_open=False)
        print(f"Saved: {out}")

    # ── C. Marker gene expression (dropdown per gene) ─────────────────────
    if d["marker_results"] and len(d["ref_X"]) > 0:
        all_genes = set()
        for group, info in d["marker_results"].items():
            all_genes.update(info["names"][:6])
        gene_list = sorted(all_genes)
        var_names = d["var_names"]

        fig = go.Figure()
        for i, gene in enumerate(gene_list):
            if gene in var_names:
                gene_idx = var_names.index(gene)
                expr = d["ref_X"][:, gene_idx]
            else:
                continue

            hover = [
                f"<b>{gene}</b>: {e:.2f}<br>{obs[ct_col].values[j]}<br>UMAP: ({umap[j,0]:.2f}, {umap[j,1]:.2f})"
                for j, e in enumerate(expr)
            ]
            fig.add_trace(go.Scattergl(
                x=umap[:, 0], y=umap[:, 1],
                mode="markers",
                marker=dict(
                    size=4, color=expr, colorscale="Viridis",
                    showscale=(i == 0), opacity=0.7,
                    colorbar=dict(title="Expression"),
                ),
                name=gene, visible=(i == 0),
                hovertext=hover, hoverinfo="text",
            ))

        buttons = []
        for i, gene in enumerate(gene_list):
            vis = [False] * len(gene_list)
            vis[i] = True
            buttons.append(dict(label=gene, method="update",
                                args=[{"visible": vis}, {"title": f"Expression: {gene}"}]))

        fig.update_layout(
            updatemenus=[dict(buttons=buttons, direction="down",
                              x=0.01, xanchor="left", y=1.12, yanchor="top")],
            title=f"Expression: {gene_list[0]}",
            xaxis_title="UMAP 1", yaxis_title="UMAP 2",
            plot_bgcolor="white", width=1100, height=900,
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=False, zeroline=False),
        )
        out = output_dir / "interactive_marker_genes.html"
        fig.write_html(str(out), auto_open=False)
        print(f"Saved: {out}")

    # ── D. Model predictions ──────────────────────────────────────────────
    CT_ID_COL = "cell_type_ontology_term_id"
    for model_name, pred_umap in d["predictions"].items():
        fig = go.Figure()

        if holdout_ct_id and CT_ID_COL in obs.columns:
            holdout_mask = obs[CT_ID_COL].values == holdout_ct_id
            source_mask = obs.get("condition", pd.Series()).values == "mouse"
            target_mask = obs.get("condition", pd.Series()).values == "human"
            bg = ~holdout_mask
            src = holdout_mask & source_mask
            tgt = holdout_mask & target_mask
        else:
            bg = np.ones(len(obs), dtype=bool)
            src = np.zeros(len(obs), dtype=bool)
            tgt = np.zeros(len(obs), dtype=bool)

        fig.add_trace(go.Scattergl(
            x=umap[bg, 0], y=umap[bg, 1],
            mode="markers", marker=dict(size=3, color="#d0d0d0", opacity=0.3),
            name="Other cell types",
            hovertext=[f"{obs[ct_col].values[i]}<br>{obs.get('condition', pd.Series()).values[i] if 'condition' in obs.columns else ''}"
                       for i in np.where(bg)[0]],
            hoverinfo="text",
        ))

        if src.sum() > 0:
            hover_src = [f"<b>Mouse source</b><br>{obs[ct_col].values[i]}<br>Donor: {obs.get('donor_id', pd.Series()).values[i] if 'donor_id' in obs.columns else 'N/A'}<br>Tissue: {obs.get('tissue', pd.Series()).values[i] if 'tissue' in obs.columns else 'N/A'}"
                         for i in np.where(src)[0]]
            fig.add_trace(go.Scattergl(
                x=umap[src, 0], y=umap[src, 1],
                mode="markers", marker=dict(size=8, color="dodgerblue", opacity=0.8),
                name=f"Mouse source (n={src.sum()})",
                hovertext=hover_src, hoverinfo="text",
            ))

        if tgt.sum() > 0:
            hover_tgt = [f"<b>Human actual</b><br>{obs[ct_col].values[i]}<br>Donor: {obs.get('donor_id', pd.Series()).values[i] if 'donor_id' in obs.columns else 'N/A'}<br>Tissue: {obs.get('tissue', pd.Series()).values[i] if 'tissue' in obs.columns else 'N/A'}<br>Index: {obs.index[i]}"
                         for i in np.where(tgt)[0]]
            fig.add_trace(go.Scattergl(
                x=umap[tgt, 0], y=umap[tgt, 1],
                mode="markers", marker=dict(size=8, color="limegreen", opacity=0.8),
                name=f"Human actual (n={tgt.sum()})",
                hovertext=hover_tgt, hoverinfo="text",
            ))

        fig.add_trace(go.Scattergl(
            x=pred_umap[:, 0], y=pred_umap[:, 1],
            mode="markers", marker=dict(size=8, color="orangered", opacity=0.8),
            name=f"Predicted — {model_name} (n={len(pred_umap)})",
            hovertext=[f"<b>Predicted ({model_name})</b><br>UMAP: ({x:.2f}, {y:.2f})"
                       for x, y in pred_umap],
            hoverinfo="text",
        ))

        fig.update_layout(
            title=f"{model_name}: Predictions in Full Context — Click legend to toggle",
            xaxis_title="UMAP 1", yaxis_title="UMAP 2",
            plot_bgcolor="white", width=1200, height=900,
            legend=dict(font=dict(size=12), itemsizing="constant"),
            xaxis=dict(showgrid=False, zeroline=False),
            yaxis=dict(showgrid=False, zeroline=False),
        )
        out = output_dir / f"interactive_{model_name.lower().replace('-', '_')}.html"
        fig.write_html(str(out), auto_open=False)
        print(f"Saved: {out}")

    print(f"\nAll interactive plots saved to {output_dir}/")

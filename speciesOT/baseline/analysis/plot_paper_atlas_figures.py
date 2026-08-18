"""Paper-style atlas figures for the frozen v08 OOD cuts.

Reuses the scGen Fig. 5 mean-scatter recipe (linregress R², all genes + top 100
Wilcoxon DEGs) and the CellOT plot.py / viz.py recipes for MMD bars, marker
KDEs, joint UMAP, and a Fig. 4e-style dot plot.

USAGE (analysis env):
    python speciesOT/baseline/analysis/plot_paper_atlas_figures.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import anndata as ad
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scanpy as sc
import seaborn as sns
from matplotlib.lines import Line2D
from scipy import stats
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")
mpl.use("Agg")
sc.settings.verbosity = 0

REPO = Path("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT")
CELLOT = REPO / "cellot" / "cellot_gpu"
RESULTS = CELLOT / "results"
DATA = CELLOT / "datasets" / "speciesot-human-mouse-hvg"
BIOMART = REPO / "scripts" / ".biomart_ortholog_cache.csv"
OUT = REPO / "speciesOT" / "baseline" / "analysis" / "paper_style_atlas_outputs"

# CellOT paper palette (scripts/plot.py)
COLORS = {
    "impact_cellot": "#F2545B",
    "scgen": "#C3BABA",
    "treated": "#114083",
    "control": "#A7BED3",
    "observed": "#9A8F97",
}
LABELS = {"impact_cellot": "IMPACT", "scgen": "scGen"}

MARKER_TCELL = {
    "PTPRC": "ENSG00000081237",
    "CD3E": "ENSG00000198851",
    "CD4": "ENSG00000010610",
    "CD8A": "ENSG00000153563",
    "CD5": "ENSG00000110448",
    "CD7": "ENSG00000173762",
    "CCR7": "ENSG00000126353",
    "NCAM1": "ENSG00000149294",
    "MS4A1": "ENSG00000156738",
    "CD14": "ENSG00000170458",
    "ITGAM": "ENSG00000169896",
}
MARKER_MYELOID = {
    "FCGR3A": "ENSG00000143543",
    "MS4A7": "ENSG00000166926",
    "LILRB1": "ENSG00000104972",
    "LILRB2": "ENSG00000131042",
    "CX3CR1": "ENSG00000168329",
    "IFITM3": "ENSG00000185885",
    "TNF": "ENSG00000232810",
    "HLA-DRA": "ENSG00000204287",
    "HLA-DRB1": "ENSG00000196126",
    "ITGAX": "ENSG00000137776",
    "SELL": "ENSG00000188404",
    "NR4A1": "ENSG00000123358",
    "S100A10": "ENSG00000197747",
}

CUTS = [
    {
        "tag": "hvg_pearson_residuals_m1_v08_ood",
        "label": "M1 Pearson",
        "panel": "myeloid",
        "data": "hvg_pearson_residuals_m1_v08.h5ad",
    },
    {
        "tag": "hvg_pearson_residuals_m2_v08_ood",
        "label": "M2 Pearson",
        "panel": "myeloid",
        "data": "hvg_pearson_residuals_m2_v08.h5ad",
    },
    {
        "tag": "hvg_pearson_residuals_a_uncapped_v08_ood",
        "label": "CD8 Pearson",
        "panel": "tcell",
        "data": "hvg_pearson_residuals_a_uncapped_v08.h5ad",
    },
    {
        "tag": "hvg_mixhvg_m1_v08_ood",
        "label": "M1 mixHVG",
        "panel": "myeloid",
        "data": "hvg_mixhvg_m1_v08.h5ad",
    },
    {
        "tag": "hvg_mixhvg_m2_v08_ood",
        "label": "M2 mixHVG",
        "panel": "myeloid",
        "data": "hvg_mixhvg_m2_v08.h5ad",
    },
    {
        "tag": "hvg_mixhvg_a_uncapped_v08_ood",
        "label": "CD8 mixHVG",
        "panel": "tcell",
        "data": "hvg_mixhvg_a_uncapped_v08.h5ad",
    },
]


def _toggle_ood(data, holdout, key, mode, random_state=0, stratify=None, **kwargs):
    """Same split as cellot.data.cell.split_cell_data_toggle_ood."""
    split = pd.Series(None, index=data.obs.index, dtype=object)
    groups = data.obs.groupby(kwargs.get("groupby")).groups if kwargs.get("groupby") else {None: data.obs.index}
    tt_kwargs = {k: v for k, v in kwargs.items() if k != "groupby"}
    for _, index in groups.items():
        trainobs, testobs = train_test_split(index, random_state=random_state, **tt_kwargs)
        split.loc[trainobs] = "train"
        split.loc[testobs] = "test"
    value = holdout if isinstance(holdout, list) else [holdout]
    ood = data.obs_names[data.obs[key].isin(value)]
    strat = None
    if stratify is not None and stratify in data.obs.columns:
        strat = data.obs.loc[ood, stratify].astype(str)
        if strat.nunique() < 2 or strat.value_counts().min() < 2:
            strat = None
    try:
        trainobs, testobs = train_test_split(ood, random_state=random_state, test_size=0.5, stratify=strat)
    except ValueError:
        trainobs, testobs = train_test_split(ood, random_state=random_state, test_size=0.5)
    if mode == "ood":
        split.loc[trainobs] = "ignore"
        split.loc[testobs] = "ood"
    else:
        split.loc[trainobs] = "train"
        split.loc[testobs] = "ood"
    return split


def _to_df(adata: ad.AnnData) -> pd.DataFrame:
    x = adata.X
    if hasattr(x, "toarray"):
        x = x.toarray()
    return pd.DataFrame(np.asarray(x), index=adata.obs_names, columns=adata.var_names.astype(str))


def load_symbols() -> dict[str, str]:
    if not BIOMART.exists():
        return {}
    df = pd.read_csv(BIOMART)
    return dict(zip(df["human_ensembl_id"].astype(str), df["human_gene_name"].astype(str)))


def symbol(ensg: str, lut: dict[str, str]) -> str:
    return lut.get(str(ensg), str(ensg))


def load_cut(cut: dict, symbols: dict[str, str]) -> dict:
    tag = cut["tag"]
    cfg_path = RESULTS / tag / "impact_cellot" / "config.yaml"
    import yaml

    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    ds = cfg["datasplit"]
    adata = ad.read_h5ad(DATA / cut["data"])
    adata.obs["split"] = _toggle_ood(
        adata,
        holdout=ds["holdout"],
        key=ds["key"],
        mode=ds.get("mode", "ood"),
        random_state=int(ds.get("random_state", 0)),
        stratify=ds.get("stratify"),
        groupby=ds.get("groupby"),
        test_size=ds.get("test_size", 0.2),
    )
    ood = adata[adata.obs["split"] == "ood"].copy()
    control = _to_df(ood[ood.obs["condition"] == "mouse"])
    treated = _to_df(ood[ood.obs["condition"] == "human"])
    models = {}
    for model in ("impact_cellot", "scgen"):
        imp = ad.read_h5ad(RESULTS / tag / model / "evals_ood_data_space" / "imputed.h5ad")
        models[model] = _to_df(imp)
    genes = [str(g) for g in treated.columns]
    panel = MARKER_TCELL if cut["panel"] == "tcell" else MARKER_MYELOID
    present = {name: ensg for name, ensg in panel.items() if ensg in genes}
    # Wilcoxon DEGs: human vs mouse on the OOD slice (scGen analog of stim vs ctrl)
    deg_ad = ood.copy()
    deg_ad.obs["condition"] = deg_ad.obs["condition"].astype(str)
    sc.tl.rank_genes_groups(deg_ad, groupby="condition", groups=["human"], reference="mouse", method="wilcoxon")
    top100 = [str(g) for g in deg_ad.uns["rank_genes_groups"]["names"]["human"][:100]]
    return {
        "cut": cut,
        "control": control,
        "treated": treated,
        "models": models,
        "genes": genes,
        "markers": present,
        "top100": [g for g in top100 if g in genes],
        "symbols": symbols,
        "ood": ood,
    }


def eval_mmd(tag: str, model: str, ncells: int = 80) -> tuple[float, float]:
    path = RESULTS / tag / model / "evals_ood_data_space" / "evals.csv"
    df = pd.read_csv(path)
    sub = df[(df["metric"] == "mmd") & (df["ncells"] == ncells)]
    return float(sub["value"].mean()), float(sub["value"].std())


def ext_bounds(tag: str, ncells: int = 80) -> tuple[float, float]:
    path = RESULTS / tag / "impact_cellot" / "evals_ood_data_space" / "extended_metrics.csv"
    if not path.exists():
        return np.nan, np.nan
    df = pd.read_csv(path)
    row = df[df["ncells"] == ncells].iloc[0]
    return float(row["mmd_floor"]), float(row["mmd_ceiling"])


def pearson_r2(a: np.ndarray, b: np.ndarray) -> float:
    r = stats.linregress(a, b).rvalue
    return float(r * r)


def plot_scatter(bundle: dict, outdir: Path) -> dict[str, float]:
    """scGen Fig. 5: sns.regplot + R²_all + R²_top100 DEGs (linregress, squared)."""
    treated = bundle["treated"]
    top100 = bundle["top100"]
    markers = bundle["markers"]
    lut = bundle["symbols"]
    y = treated.mean(0).to_numpy(dtype=float)
    genes = list(treated.columns)
    stats_out = {}

    sns.set()
    fig, axes = plt.subplots(1, 2, figsize=(10.6, 5.0), sharex=True, sharey=True)
    for ax, model in zip(axes, ("scgen", "impact_cellot")):
        pred = bundle["models"][model].reindex(columns=genes)
        x = pred.mean(0).to_numpy(dtype=float)
        r2_all = pearson_r2(x, y)
        r2_deg = pearson_r2(x[[genes.index(g) for g in top100]], y[[genes.index(g) for g in top100]])
        stats_out[f"{model}_r2_all"] = r2_all
        stats_out[f"{model}_r2_deg100"] = r2_deg
        df = pd.DataFrame({"Predicted": x, "Observed": y})
        sns.regplot(
            data=df, x="Predicted", y="Observed", ax=ax,
            scatter_kws={"s": 14, "alpha": 0.35, "color": "0.35", "rasterized": True},
            line_kws={"color": "#2ca02c", "lw": 1.4},
        )
        for name, ensg in markers.items():
            j = genes.index(ensg)
            ax.plot(x[j], y[j], "o", color="#d62728", markersize=5, zorder=5)
            ax.annotate(name, (x[j], y[j]), fontsize=8, color="black")
        ax.set_title(LABELS[model], fontsize=14)
        ax.set_xlabel("Predicted", fontsize=13)
        ax.set_ylabel("Observed human", fontsize=13)
        lo = min(float(np.min(x)), float(np.min(y)))
        hi = max(float(np.max(x)), float(np.max(y)))
        pad = 0.05 * (hi - lo + 1e-6)
        ax.set_xlim(lo - pad, hi + pad)
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_aspect("equal", adjustable="box")
        xmax, ymax = float(np.max(x)), float(np.max(y))
        ax.text(xmax * 0.08, ymax * 0.92, r"$\mathrm{R^2_{\mathrm{\mathsf{all\ genes}}}}$= " + f"{r2_all:.2f}", fontsize=13)
        ax.text(xmax * 0.08, ymax * 0.80, r"$\mathrm{R^2_{\mathrm{\mathsf{top\ 100\ DEGs}}}}$= " + f"{r2_deg:.2f}", fontsize=13)
    fig.suptitle(f"{bundle['cut']['label']}  —  mean-vector scatter (scGen Fig. 5 recipe)", fontsize=13, y=1.02)
    fig.tight_layout()
    fig.savefig(outdir / "scatter_mean_r2.pdf", bbox_inches="tight")
    fig.savefig(outdir / "scatter_mean_r2.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    sns.reset_orig()
    return stats_out


def plot_mmd(bundle: dict, outdir: Path) -> dict[str, float]:
    """CellOT Fig. 2/4 style: MMD bars + identity / observed dashed lines."""
    tag = bundle["cut"]["tag"]
    floor, ceiling = ext_bounds(tag, 80)
    rows = []
    out = {"mmd_floor": floor, "mmd_ceiling": ceiling}
    for model in ("impact_cellot", "scgen"):
        m, s = eval_mmd(tag, model, 80)
        rows.append({"model": LABELS[model], "mmd": m, "sd": s, "color": COLORS[model]})
        out[f"{model}_mmd80"] = m
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(4.2, 4.4))
    x = np.arange(len(df))
    ax.bar(x, df["mmd"], yerr=df["sd"], color=df["color"], capsize=4, edgecolor="0.2", lw=0.4, width=0.62)
    if np.isfinite(ceiling):
        ax.axhline(ceiling, ls="--", color=COLORS["control"], lw=1.2, label="Identity")
    if np.isfinite(floor):
        ax.axhline(floor, ls="--", color=COLORS["treated"], lw=1.2, label="Observed")
    ax.set_xticks(x)
    ax.set_xticklabels(df["model"])
    ax.set_ylabel("MMD  ↓")
    ax.set_yscale("log")
    ax.set_title(bundle["cut"]["label"])
    ax.legend(frameon=False, fontsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(outdir / "mmd_bars.pdf", bbox_inches="tight")
    fig.savefig(outdir / "mmd_bars.png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out


def _display_genes(bundle: dict, k: int = 8) -> list[tuple[str, str]]:
    """Curated markers first, then top Wilcoxon DEGs, so every cut has a full panel."""
    seen = set(bundle["markers"].values())
    genes = list(bundle["markers"].items())
    lut = bundle["symbols"]
    for ensg in bundle["top100"]:
        if ensg in seen:
            continue
        genes.append((symbol(ensg, lut), ensg))
        seen.add(ensg)
        if len(genes) >= k:
            break
    return genes[:k]


def plot_kde(bundle: dict, outdir: Path) -> None:
    """CellOT viz.plot_marginals: control / treated / IMPACT / scGen."""
    markers = _display_genes(bundle, k=8)
    if not markers:
        return
    genes = [ensg for _, ensg in markers]
    titles = [name for name, _ in markers]
    dfs = {
        "control": bundle["control"][genes],
        "treated": bundle["treated"][genes],
        "cellot": bundle["models"]["impact_cellot"][genes],
        "scgen": bundle["models"]["scgen"][genes],
    }
    for k, df in dfs.items():
        df.columns = titles
    long = pd.concat(dfs, names=["layer"]).reset_index("layer")
    colors = {
        "cellot": COLORS["impact_cellot"],
        "treated": COLORS["treated"],
        "control": COLORS["control"],
        "scgen": COLORS["scgen"],
    }
    order = ["cellot", "treated", "control", "scgen"]
    n = len(titles)
    fig, axes = plt.subplots(1, n, figsize=(2.7 * n, 2.8), sharey=False)
    if n == 1:
        axes = [axes]
    for ax, gene in zip(axes, titles):
        sub = long[["layer", gene]].copy()
        lo, hi = sub[gene].quantile(0.01), sub[gene].quantile(0.99)
        sub[gene] = sub[gene].clip(lo, hi)
        sns.kdeplot(
            data=sub, x=gene, hue="layer", common_norm=False, ax=ax, legend=False,
            palette=colors, hue_order=order, clip=(0, None), lw=1.6,
        )
        ax.set_title(gene, fontstyle="italic", fontsize=11)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    handles = [Line2D([0], [0], color=colors[k], lw=2, label={"cellot": "IMPACT", "treated": "Treated", "control": "Control", "scgen": "scGen"}[k]) for k in order]
    axes[-1].legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False, fontsize=9)
    fig.suptitle(f"{bundle['cut']['label']}  —  marker KDEs (CellOT Fig. 2/4g)", fontsize=12, y=1.04)
    fig.tight_layout()
    fig.savefig(outdir / "kde_markers.pdf", bbox_inches="tight")
    fig.savefig(outdir / "kde_markers.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_umap(bundle: dict, outdir: Path) -> None:
    """CellOT Fig. 2c/f: joint UMAP of observed treated + predictions (equal n)."""
    treated = bundle["treated"]
    rng = np.random.default_rng(0)
    # CellOT Fig. 2: observed treated = grey, predictions = dark blue (same in every panel).
    # Identity uses mouse (control) as the "prediction" so the gap is visible.
    panels = [
        ("Identity", bundle["control"], COLORS["control"]),
        ("scGen", bundle["models"]["scgen"], COLORS["treated"]),
        ("IMPACT", bundle["models"]["impact_cellot"], COLORS["impact_cellot"]),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(11.4, 3.6))
    n_obs = len(treated)
    for ax, (title, other, color) in zip(axes, panels):
        n = min(n_obs, len(other), 2500)
        t_idx = rng.choice(n_obs, n, replace=False)
        o_idx = rng.choice(len(other), n, replace=False)
        t = treated.iloc[t_idx].to_numpy(dtype=np.float32)
        o = other.iloc[o_idx].to_numpy(dtype=np.float32)
        x = np.vstack([t, o])
        obs = pd.DataFrame({"is_pred": [False] * n + [True] * n})
        um = ad.AnnData(x, obs=obs)
        sc.pp.pca(um, n_comps=min(30, x.shape[1] - 1, x.shape[0] - 1))
        sc.pp.neighbors(um, n_neighbors=min(15, n - 1))
        sc.tl.umap(um, min_dist=0.3)
        xy = um.obsm["X_umap"]
        ax.scatter(xy[:n, 0], xy[:n, 1], s=7, c="#BDBDBD", alpha=0.7, rasterized=True, label="Observed treated")
        ax.scatter(xy[n:, 0], xy[n:, 1], s=7, c=color, alpha=0.7, rasterized=True, label=title)
        ax.set_title(title, fontsize=13)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("UMAP1")
        ax.set_ylabel("UMAP2" if ax is axes[0] else "")
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.legend(frameon=False, loc="upper right", markerscale=2.0, fontsize=8)
    fig.suptitle(f"{bundle['cut']['label']}  —  joint UMAP (CellOT Fig. 2c/f)", fontsize=12, y=1.03)
    fig.tight_layout()
    fig.savefig(outdir / "umap_joint.pdf", bbox_inches="tight")
    fig.savefig(outdir / "umap_joint.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_dots(bundle: dict, outdir: Path) -> None:
    """Fig. 4e-style marker dots: size = fraction > 0, color = mean."""
    markers = _display_genes(bundle, k=8)
    if not markers:
        return
    layers = [
        ("Control", bundle["control"]),
        ("Treated", bundle["treated"]),
        ("IMPACT o.o.d.", bundle["models"]["impact_cellot"]),
        ("scGen o.o.d.", bundle["models"]["scgen"]),
    ]
    names = [n for n, _ in markers]
    ensgs = [e for _, e in markers]
    means, fracs = [], []
    for _, df in layers:
        sub = df[ensgs]
        means.append(sub.mean(0).to_numpy(dtype=float))
        fracs.append((sub.to_numpy(dtype=float) > 0).mean(0))
    means = np.vstack(means)
    fracs = np.vstack(fracs)
    fig, ax = plt.subplots(figsize=(max(7.5, 0.7 * len(names) + 2.2), 3.4))
    vmax = max(float(np.nanmax(means)), 1e-6)
    norm = mpl.colors.Normalize(0, vmax)
    cmap = plt.cm.Blues
    for yi in range(len(layers)):
        for xi in range(len(names)):
            ax.scatter(
                xi, yi, s=36 + 400 * fracs[yi, xi],
                c=[cmap(norm(means[yi, xi]))],
                edgecolors="0.25", linewidths=0.4, zorder=2,
            )
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=40, ha="right")
    ax.set_yticks(range(len(layers)))
    ax.set_yticklabels([lab for lab, _ in layers])
    ax.set_ylim(len(layers) - 0.55, -0.55)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02, label="Mean expression")
    ax.set_title(f"{bundle['cut']['label']}  —  marker panel")
    fig.tight_layout()
    fig.savefig(outdir / "dotplot_markers.pdf", bbox_inches="tight")
    fig.savefig(outdir / "dotplot_markers.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def plot_summary(rows: list[dict]) -> None:
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "summary.csv", index=False)
    fig, axes = plt.subplots(1, 3, figsize=(13.2, 4.2))
    cuts = df["label"].tolist()
    x = np.arange(len(cuts))
    w = 0.36
    pairs = [
        (axes[0], "r2_all", r"$\mathrm{R^2}$ all genes  ↑", False),
        (axes[1], "r2_deg100", r"$\mathrm{R^2}$ top 100 DEGs  ↑", False),
        (axes[2], "mmd80", "MMD  ↓", True),
    ]
    for ax, key, ylab, logy in pairs:
        ax.bar(x - w / 2, df[f"scgen_{key}"], w, color=COLORS["scgen"], label="scGen", edgecolor="0.2", lw=0.4)
        ax.bar(x + w / 2, df[f"impact_cellot_{key}"], w, color=COLORS["impact_cellot"], label="IMPACT", edgecolor="0.2", lw=0.4)
        ax.set_xticks(x)
        ax.set_xticklabels(cuts, rotation=30, ha="right")
        ax.set_ylabel(ylab)
        if logy:
            ax.set_yscale("log")
        else:
            ax.set_ylim(0, 1.05)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    axes[0].legend(frameon=False)
    fig.suptitle("Frozen v08 OOD — paper metrics (honest R², ncells=80 MMD)", fontsize=13)
    fig.tight_layout()
    fig.savefig(OUT / "summary_board.pdf", bbox_inches="tight")
    fig.savefig(OUT / "summary_board.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    symbols = load_symbols()
    print(f"[atlas-figures] {len(symbols)} gene symbols from BioMart cache")
    rows = []
    for cut in CUTS:
        print(f"\n=== {cut['label']}  {cut['tag']} ===", flush=True)
        bundle = load_cut(cut, symbols)
        print(
            f"  control={len(bundle['control'])} treated={len(bundle['treated'])} "
            f"impact={len(bundle['models']['impact_cellot'])} scgen={len(bundle['models']['scgen'])} "
            f"markers={list(bundle['markers'])}  DEGs={len(bundle['top100'])}",
            flush=True,
        )
        outdir = OUT / cut["tag"]
        outdir.mkdir(parents=True, exist_ok=True)
        scatter = plot_scatter(bundle, outdir)
        mmd = plot_mmd(bundle, outdir)
        plot_kde(bundle, outdir)
        plot_umap(bundle, outdir)
        plot_dots(bundle, outdir)
        row = {"label": cut["label"], "tag": cut["tag"], **scatter, **mmd}
        rows.append(row)
        print(
            f"  R² all  IMPACT={scatter['impact_cellot_r2_all']:.3f}  scGen={scatter['scgen_r2_all']:.3f}  "
            f"R² DEG  IMPACT={scatter['impact_cellot_r2_deg100']:.3f}  scGen={scatter['scgen_r2_deg100']:.3f}  "
            f"MMD80  IMPACT={mmd['impact_cellot_mmd80']:.4f}  scGen={mmd['scgen_mmd80']:.4f}",
            flush=True,
        )
    plot_summary(rows)
    print(f"\n[atlas-figures] wrote {OUT}")


if __name__ == "__main__":
    main()

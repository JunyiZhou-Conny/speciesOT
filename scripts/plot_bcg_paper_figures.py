#!/usr/bin/env python3
"""Paper-style BCG figures for an external species-transport eval.

This is the figure half of the BCG predict → eval → score pipeline. Numbers
live in ``results/external_eval/<tag>/external_target_metrics.csv`` (from
``eval_external_target.py``). These boards are the biological read of the same
run: mean-R² scatter, decoded-frame MMD bars, marker KDEs, joint UMAP, and a
mean-only marker panel.

Atlas recipes in ``speciesOT/baseline/analysis/plot_paper_atlas_figures.py``
are the visual source, but the labels and gene panel are BCG-specific:

* Wilcoxon DEGs are **human BCG vs mouse BCG**, not atlas human vs mouse.
* Highlighted genes are **HSC / HSPC** markers present on this axis — not
  CD3/CD8/FCGR3A.
* MMD bars are taken from the eval CSV so they match the scorecard (decoded
  floor / ceiling / model). They are not re-estimated here.
* Cloud labels are ``mouse BCG`` / ``human BCG`` / IMPACT / scGen. Do not
  call a vaccinated mouse file "Treated" on an unvaccinated-human board.
* After scANVI the posed matrix is almost never exactly zero, so a Fig. 4e
  "% expressed" size encoding saturates. The dot panel keeps **mean color
  only**.

USAGE (analysis env)::

    python scripts/plot_bcg_paper_figures.py \\
        --source  $D/${tag}_aligned_${flav}.h5ad \\
        --target  $D/bcg_human_unvax_target_${flav}.h5ad \\
        --pred-impact $D/${tag}_predicted_human_via_impact_cellot_${flav}.h5ad \\
        --pred-scgen  $D/${tag}_predicted_human_via_scgen_${flav}.h5ad \\
        --eval-impact results/external_eval/${tag}_impact_.../external_target_metrics.csv \\
        --eval-scgen  results/external_eval/${tag}_scgen_.../external_target_metrics.csv \\
        --outdir speciesOT/baseline/analysis/paper_style_bcg_outputs/<combo>/ \\
        --label "BCG unvax LT-HSC · pearson · uncapped_v08_iid"

Importable: ``run_figures(...)`` returns the stats dict and writes the files.
"""

from __future__ import annotations

import argparse
import json
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

warnings.filterwarnings("ignore")
mpl.use("Agg")
sc.settings.verbosity = 0

REPO = Path(__file__).resolve().parent.parent
BIOMART = REPO / "scripts" / ".biomart_ortholog_cache.csv"
DEFAULT_OUT = REPO / "speciesOT" / "baseline" / "analysis" / "paper_style_bcg_outputs"

# CellOT paper palette (scripts/plot.py / plot_paper_atlas_figures.py)
COLORS = {
    "impact_cellot": "#F2545B",
    "scgen": "#C3BABA",
    "human": "#114083",
    "mouse": "#A7BED3",
    "observed": "#9A8F97",
}
MODEL_LABELS = {"impact_cellot": "IMPACT", "scgen": "scGen"}

# HSC / HSPC candidates. Only genes present on *this* axis are drawn.
# Classic LT-HSC genes (CD34, AVP, HLF, …) are listed even when they miss
# the v08 Pearson 1000 — they light up automatically on a future axis.
HSC_MARKERS = {
    "CRHBP": "ENSG00000145708",
    "MECOM": "ENSG00000085276",
    "HOPX": "ENSG00000171476",
    "KIT": "ENSG00000157404",
    "THY1": "ENSG00000154096",
    "PROCR": "ENSG00000101000",
    "EMCN": "ENSG00000164035",
    "ITGA2B": "ENSG00000005961",
    "HLA-DRA": "ENSG00000204287",
    "ANXA1": "ENSG00000135046",
    "CD52": "ENSG00000169442",
    "CD34": "ENSG00000108091",
    "PROM1": "ENSG00000007062",
    "AVP": "ENSG00000101200",
    "HLF": "ENSG00000108924",
    "MLLT3": "ENSG00000171843",
    "HOXA9": "ENSG00000078399",
    "GATA2": "ENSG00000179348",
    "SPINK2": "ENSG00000106682",
    "RUNX1": "ENSG00000159216",
    "CD27": "ENSG00000139193",
    "FGD5": "ENSG00000154783",
}


def _strip(g) -> str:
    g = str(g)
    if g.startswith("ENS") and "." in g:
        return g.split(".")[0]
    return g


def _to_df(path: Path) -> pd.DataFrame:
    adata = ad.read_h5ad(path)
    x = adata.X
    if hasattr(x, "toarray"):
        x = x.toarray()
    cols = [_strip(g) for g in adata.var_names.astype(str)]
    return pd.DataFrame(np.asarray(x, dtype=np.float64), columns=cols)


def _align(df: pd.DataFrame, genes: list[str]) -> pd.DataFrame:
    return df.reindex(columns=genes).fillna(0.0)


def load_symbols(extra_csv: Path | None = None) -> dict[str, str]:
    lut: dict[str, str] = {}
    if BIOMART.exists():
        df = pd.read_csv(BIOMART)
        if {"human_ensembl_id", "human_gene_name"} <= set(df.columns):
            lut.update(
                zip(df["human_ensembl_id"].map(_strip), df["human_gene_name"].astype(str))
            )
    if extra_csv is not None and extra_csv.exists():
        df = pd.read_csv(extra_csv)
        ensg_col = next(
            (c for c in ("human_ensembl_id", "ensg", "gene") if c in df.columns),
            df.columns[0],
        )
        name_col = next(
            (c for c in ("human_gene_name", "symbol", "gene_name") if c in df.columns),
            None,
        )
        if name_col is not None:
            lut.update(zip(df[ensg_col].map(_strip), df[name_col].astype(str)))
    return lut


def symbol(ensg: str, lut: dict[str, str]) -> str:
    return lut.get(_strip(ensg), _strip(ensg))


def pearson_r2(a: np.ndarray, b: np.ndarray) -> float:
    if a.size < 3 or np.allclose(a, a[0]) or np.allclose(b, b[0]):
        return float("nan")
    r = stats.linregress(a, b).rvalue
    return float(r * r)


def wilcoxon_top(
    mouse: pd.DataFrame, human: pd.DataFrame, genes: list[str], k: int = 100
) -> list[str]:
    """Top Wilcoxon DEGs: human BCG vs mouse BCG on the shared axis."""
    combined = pd.concat([human[genes], mouse[genes]], axis=0, ignore_index=True)
    obs = pd.DataFrame(
        {"species": ["human"] * len(human) + ["mouse"] * len(mouse)}
    )
    deg = ad.AnnData(combined.to_numpy(dtype=np.float32), obs=obs)
    deg.var_names = pd.Index(genes)
    deg.obs["species"] = deg.obs["species"].astype("category")
    sc.tl.rank_genes_groups(
        deg, groupby="species", groups=["human"], reference="mouse", method="wilcoxon"
    )
    names = [str(g) for g in deg.uns["rank_genes_groups"]["names"]["human"]]
    return [g for g in names if g in genes][:k]


def present_markers(genes: list[str], extra: dict[str, str] | None = None) -> dict[str, str]:
    panel = dict(HSC_MARKERS)
    if extra:
        panel.update(extra)
    gene_set = set(genes)
    return {name: ensg for name, ensg in panel.items() if ensg in gene_set}


def _headline_row(csv_path: Path, ncells: int | None) -> pd.Series:
    df = pd.read_csv(csv_path)
    if "ncells" not in df.columns:
        return df.iloc[-1]
    if ncells is None:
        return df.sort_values("ncells").iloc[-1]
    hit = df[df["ncells"] == ncells]
    if hit.empty:
        return df.sort_values("ncells").iloc[-1]
    return hit.iloc[0]


def _display_genes(markers: dict[str, str], top100: list[str], lut: dict[str, str], k: int = 8):
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for name, ensg in markers.items():
        if ensg in seen:
            continue
        out.append((name, ensg))
        seen.add(ensg)
        if len(out) >= k:
            return out
    for ensg in top100:
        if ensg in seen:
            continue
        out.append((symbol(ensg, lut), ensg))
        seen.add(ensg)
        if len(out) >= k:
            break
    return out


def _save(fig, outdir: Path, stem: str) -> dict[str, str]:
    pdf = outdir / f"{stem}.pdf"
    png = outdir / f"{stem}.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return {"pdf": str(pdf), "png": str(png)}


def plot_scatter(bundle: dict, outdir: Path) -> dict:
    human = bundle["human"]
    genes = bundle["genes"]
    top100 = bundle["top100"]
    markers = bundle["markers"]
    y = human.mean(0).to_numpy(dtype=float)
    stats_out: dict[str, float] = {}
    models = [m for m in ("impact_cellot", "scgen") if m in bundle["models"]]
    if not models:
        return stats_out

    sns.set()
    fig, axes = plt.subplots(1, len(models), figsize=(5.3 * len(models), 5.0), sharex=True, sharey=True)
    if len(models) == 1:
        axes = [axes]
    for ax, model in zip(axes, models):
        pred = bundle["models"][model].reindex(columns=genes)
        x = pred.mean(0).to_numpy(dtype=float)
        r2_all = pearson_r2(x, y)
        deg_idx = [genes.index(g) for g in top100 if g in genes]
        r2_deg = pearson_r2(x[deg_idx], y[deg_idx]) if deg_idx else float("nan")
        stats_out[f"{model}_r2_all"] = r2_all
        stats_out[f"{model}_r2_deg100"] = r2_deg
        df = pd.DataFrame({"Predicted": x, "Observed": y})
        sns.regplot(
            data=df, x="Predicted", y="Observed", ax=ax,
            scatter_kws={"s": 14, "alpha": 0.35, "color": "0.35", "rasterized": True},
            line_kws={"color": "#2ca02c", "lw": 1.4},
        )
        for name, ensg in markers.items():
            if ensg not in genes:
                continue
            j = genes.index(ensg)
            ax.plot(x[j], y[j], "o", color="#d62728", markersize=5, zorder=5)
            ax.annotate(name, (x[j], y[j]), fontsize=8, color="black")
        ax.set_title(MODEL_LABELS[model], fontsize=14)
        ax.set_xlabel("Predicted", fontsize=13)
        ax.set_ylabel(f"Observed {bundle['target_label']}", fontsize=13)
        lo = min(float(np.min(x)), float(np.min(y)))
        hi = max(float(np.max(x)), float(np.max(y)))
        pad = 0.05 * (hi - lo + 1e-6)
        ax.set_xlim(lo - pad, hi + pad)
        ax.set_ylim(lo - pad, hi + pad)
        ax.set_aspect("equal", adjustable="box")
        xmax, ymax = float(np.max(x)), float(np.max(y))
        ax.text(xmax * 0.08, ymax * 0.92, r"$\mathrm{R^2_{\mathrm{\mathsf{all\ genes}}}}$= " + f"{r2_all:.2f}", fontsize=13)
        ax.text(xmax * 0.08, ymax * 0.80, r"$\mathrm{R^2_{\mathrm{\mathsf{top\ 100\ DEGs}}}}$= " + f"{r2_deg:.2f}", fontsize=13)
    fig.suptitle(f"{bundle['label']}  —  mean-vector scatter (scGen Fig. 5 recipe)", fontsize=12, y=1.02)
    fig.tight_layout()
    bundle.setdefault("files", {})["scatter_mean_r2"] = _save(fig, outdir, "scatter_mean_r2")
    sns.reset_orig()
    return stats_out


def plot_mmd(bundle: dict, outdir: Path) -> dict:
    ev = bundle["eval_rows"]
    if not ev:
        return {}
    rows = []
    out: dict[str, float] = {}
    floor = ceiling = float("nan")
    for model, row in ev.items():
        m = float(row.get("mmd_model", np.nan))
        floor = float(row.get("mmd_ae_recon_floor", floor))
        ceiling = float(row.get("mmd_decoded_ceiling", ceiling))
        rows.append({"model": MODEL_LABELS[model], "mmd": m, "color": COLORS[model]})
        out[f"{model}_mmd"] = m
        if "model_over_floor" in row:
            out[f"{model}_model_over_floor"] = float(row["model_over_floor"])
    out["mmd_floor"] = floor
    out["mmd_ceiling"] = ceiling
    df = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(4.4, 4.4))
    x = np.arange(len(df))
    ax.bar(x, df["mmd"], color=df["color"], edgecolor="0.2", lw=0.4, width=0.62)
    if np.isfinite(ceiling):
        ax.axhline(ceiling, ls="--", color=COLORS["mouse"], lw=1.2, label="Identity (decoded mouse)")
    if np.isfinite(floor):
        ax.axhline(floor, ls="--", color=COLORS["human"], lw=1.2, label="AE recon floor")
    ax.set_xticks(x)
    ax.set_xticklabels(df["model"])
    ax.set_ylabel("MMD  ↓  (decoded frame)")
    if df["mmd"].min() > 0:
        ax.set_yscale("log")
    ncells = bundle.get("ncells")
    ax.set_title(f"{bundle['label']}" + (f"  (ncells={ncells})" if ncells else ""))
    ax.legend(frameon=False, fontsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    bundle.setdefault("files", {})["mmd_bars"] = _save(fig, outdir, "mmd_bars")
    return out


def plot_kde(bundle: dict, outdir: Path) -> None:
    genes = _display_genes(bundle["markers"], bundle["top100"], bundle["symbols"], k=8)
    if not genes:
        return
    ensgs = [e for _, e in genes]
    titles = [n for n, _ in genes]
    layers = {
        "mouse": bundle["mouse"][ensgs],
        "human": bundle["human"][ensgs],
    }
    for model, df in bundle["models"].items():
        layers[model] = df[ensgs]
    for df in layers.values():
        df.columns = titles
    long = pd.concat(layers, names=["layer"]).reset_index("layer")
    palette = {
        "mouse": COLORS["mouse"],
        "human": COLORS["human"],
        "impact_cellot": COLORS["impact_cellot"],
        "scgen": COLORS["scgen"],
    }
    order = [k for k in ("impact_cellot", "human", "mouse", "scgen") if k in layers]
    pretty = {
        "impact_cellot": "IMPACT",
        "scgen": "scGen",
        "human": bundle["target_label"],
        "mouse": bundle["source_label"],
    }
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
            palette=palette, hue_order=order, clip=(0, None), lw=1.6,
        )
        ax.set_title(gene, fontstyle="italic", fontsize=11)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    handles = [Line2D([0], [0], color=palette[k], lw=2, label=pretty[k]) for k in order]
    axes[-1].legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False, fontsize=9)
    fig.suptitle(
        f"{bundle['label']}  —  marker KDEs (HSC panel + top DEGs; scANVI is smoother than raw UMIs)",
        fontsize=11, y=1.06,
    )
    fig.tight_layout()
    bundle.setdefault("files", {})["kde_markers"] = _save(fig, outdir, "kde_markers")


def plot_umap(bundle: dict, outdir: Path) -> None:
    human = bundle["human"]
    rng = np.random.default_rng(0)
    panels = [("Identity", bundle["mouse"], COLORS["mouse"])]
    if "scgen" in bundle["models"]:
        panels.append(("scGen", bundle["models"]["scgen"], COLORS["human"]))
    if "impact_cellot" in bundle["models"]:
        panels.append(("IMPACT", bundle["models"]["impact_cellot"], COLORS["impact_cellot"]))
    fig, axes = plt.subplots(1, len(panels), figsize=(3.8 * len(panels), 3.6))
    if len(panels) == 1:
        axes = [axes]
    n_obs = len(human)
    for ax, (title, other, color) in zip(axes, panels):
        n = min(n_obs, len(other), 2500)
        if n < 10:
            ax.set_title(f"{title} (too few cells)")
            ax.set_xticks([])
            ax.set_yticks([])
            continue
        t_idx = rng.choice(n_obs, n, replace=False)
        o_idx = rng.choice(len(other), n, replace=False)
        t = human.iloc[t_idx].to_numpy(dtype=np.float32)
        o = other.iloc[o_idx].to_numpy(dtype=np.float32)
        x = np.vstack([t, o])
        um = ad.AnnData(x, obs=pd.DataFrame({"is_pred": [False] * n + [True] * n}))
        sc.pp.pca(um, n_comps=min(30, x.shape[1] - 1, x.shape[0] - 1))
        sc.pp.neighbors(um, n_neighbors=min(15, n - 1))
        sc.tl.umap(um, min_dist=0.3)
        xy = um.obsm["X_umap"]
        ax.scatter(xy[:n, 0], xy[:n, 1], s=7, c="#BDBDBD", alpha=0.7, rasterized=True, label=bundle["target_label"])
        ax.scatter(xy[n:, 0], xy[n:, 1], s=7, c=color, alpha=0.7, rasterized=True, label=title)
        ax.set_title(title, fontsize=13)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_xlabel("UMAP1")
        ax.set_ylabel("UMAP2" if ax is axes[0] else "")
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.legend(frameon=False, loc="upper right", markerscale=2.0, fontsize=8)
    fig.suptitle(
        f"{bundle['label']}  —  joint UMAP (grey = observed {bundle['target_label']})",
        fontsize=12, y=1.03,
    )
    fig.tight_layout()
    bundle.setdefault("files", {})["umap_joint"] = _save(fig, outdir, "umap_joint")


def plot_dots(bundle: dict, outdir: Path) -> None:
    """Mean-color marker panel. Size is *not* % expressed — scANVI saturates it."""
    genes = _display_genes(bundle["markers"], bundle["top100"], bundle["symbols"], k=8)
    if not genes:
        return
    layers = [(bundle["source_label"], bundle["mouse"]), (bundle["target_label"], bundle["human"])]
    if "impact_cellot" in bundle["models"]:
        layers.append(("IMPACT", bundle["models"]["impact_cellot"]))
    if "scgen" in bundle["models"]:
        layers.append(("scGen", bundle["models"]["scgen"]))
    names = [n for n, _ in genes]
    ensgs = [e for _, e in genes]
    means = np.vstack([df[ensgs].mean(0).to_numpy(dtype=float) for _, df in layers])
    fig, ax = plt.subplots(figsize=(max(7.5, 0.7 * len(names) + 2.2), 3.6))
    vmax = max(float(np.nanmax(means)), 1e-6)
    norm = mpl.colors.Normalize(0, vmax)
    cmap = plt.cm.Blues
    for yi in range(len(layers)):
        for xi in range(len(names)):
            ax.scatter(
                xi, yi, s=220,
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
    ax.set_title(
        f"{bundle['label']}  —  marker means\n"
        "(size unused: after scANVI almost no exact zeros, so % expressed saturates)",
        fontsize=11,
    )
    fig.tight_layout()
    bundle.setdefault("files", {})["dotplot_markers"] = _save(fig, outdir, "dotplot_markers")


def build_bundle(args) -> dict:
    mouse = _to_df(args.source)
    human = _to_df(args.target)
    genes = [_strip(g) for g in human.columns]
    mouse = _align(mouse, genes)
    models = {}
    if args.pred_impact is not None:
        models["impact_cellot"] = _align(_to_df(args.pred_impact), genes)
    if args.pred_scgen is not None:
        models["scgen"] = _align(_to_df(args.pred_scgen), genes)
    if not models:
        raise SystemExit("need at least one of --pred-impact / --pred-scgen")

    lut = load_symbols(args.symbols_csv)
    extra = {}
    if args.markers:
        for item in args.markers:
            if "=" in item:
                name, ensg = item.split("=", 1)
                extra[name.strip()] = _strip(ensg.strip())
    markers = present_markers(genes, extra)
    top100 = wilcoxon_top(mouse, human, genes, k=100)

    eval_rows = {}
    ncells_used = args.ncells
    for model, path in (("impact_cellot", args.eval_impact), ("scgen", args.eval_scgen)):
        if path is None:
            continue
        row = _headline_row(path, args.ncells)
        eval_rows[model] = row.to_dict()
        if ncells_used is None and "ncells" in row:
            ncells_used = int(row["ncells"])

    return {
        "label": args.label,
        "source_label": args.source_label,
        "target_label": args.target_label,
        "mouse": mouse,
        "human": human,
        "models": models,
        "genes": genes,
        "markers": markers,
        "top100": top100,
        "symbols": lut,
        "eval_rows": eval_rows,
        "ncells": ncells_used,
        "files": {},
        "n_mouse": int(len(mouse)),
        "n_human": int(len(human)),
        "n_hsc_markers": len(markers),
    }


def run_figures(args) -> dict:
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    bundle = build_bundle(args)
    stats_out: dict = {
        "label": bundle["label"],
        "n_mouse": bundle["n_mouse"],
        "n_human": bundle["n_human"],
        "n_genes": len(bundle["genes"]),
        "n_hsc_markers_present": bundle["n_hsc_markers"],
        "hsc_markers_present": list(bundle["markers"].keys()),
        "ncells": bundle["ncells"],
        "source_label": bundle["source_label"],
        "target_label": bundle["target_label"],
    }
    stats_out.update(plot_scatter(bundle, outdir))
    stats_out.update(plot_mmd(bundle, outdir))
    plot_kde(bundle, outdir)
    plot_umap(bundle, outdir)
    plot_dots(bundle, outdir)
    stats_out["files"] = bundle["files"]
    stats_out["top10_deg_human_vs_mouse"] = [
        symbol(g, bundle["symbols"]) for g in bundle["top100"][:10]
    ]

    json_path = outdir / "figure_stats.json"
    csv_path = outdir / "figure_stats.csv"
    flat = {k: v for k, v in stats_out.items() if k not in {"files", "hsc_markers_present", "top10_deg_human_vs_mouse"}}
    json_path.write_text(json.dumps(stats_out, indent=2, default=str))
    pd.DataFrame([flat]).to_csv(csv_path, index=False)

    notes = outdir / "README.txt"
    notes.write_text(
        "BCG paper-style boards for one (atlas model × BCG correction) combo.\n"
        f"label: {bundle['label']}\n"
        f"mouse cells: {bundle['n_mouse']}   human cells: {bundle['n_human']}   "
        f"genes: {len(bundle['genes'])}\n"
        f"HSC markers present on this axis: {', '.join(bundle['markers']) or '(none)'}\n"
        "\n"
        "How to read\n"
        "  scatter_mean_r2  pred mean vs real human; red = HSC markers in the axis.\n"
        "                   R²_top100 = Wilcoxon human-BCG vs mouse-BCG DEGs.\n"
        "  mmd_bars         decoded-frame numbers from eval_external_target.py.\n"
        "                   Trust model_over_floor in figure_stats.json, not gap-closed.\n"
        "  kde_markers      mouse BCG / human BCG / IMPACT / scGen. scANVI is smoother.\n"
        "  umap_joint       grey = observed human; color = identity(mouse) or a model.\n"
        "  dotplot_markers  color = mean. Size is unused (scANVI zeros saturate).\n"
    )
    print(f"[bcg-figures] wrote {outdir}")
    for stem, paths in bundle["files"].items():
        print(f"  {stem}: {paths['png']}")
    print(f"  stats: {json_path}")
    return stats_out


def _parse_args(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--source", required=True, type=Path, help="aligned mouse BCG .h5ad (log1p on the model axis)")
    ap.add_argument("--target", required=True, type=Path, help="human BCG ground truth on the same axis")
    ap.add_argument("--pred-impact", dest="pred_impact", type=Path, default=None)
    ap.add_argument("--pred-scgen", dest="pred_scgen", type=Path, default=None)
    ap.add_argument("--eval-impact", dest="eval_impact", type=Path, default=None,
                    help="external_target_metrics.csv for IMPACT (decoded-frame MMD)")
    ap.add_argument("--eval-scgen", dest="eval_scgen", type=Path, default=None,
                    help="external_target_metrics.csv for scGen")
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--label", default="BCG external", help="board title")
    ap.add_argument("--source-label", dest="source_label", default="mouse BCG")
    ap.add_argument("--target-label", dest="target_label", default="human BCG")
    ap.add_argument("--ncells", type=int, default=None,
                    help="eval-CSV row to draw (default: largest ncells in the file)")
    ap.add_argument("--symbols-csv", dest="symbols_csv", type=Path, default=None,
                    help="optional gene-list CSV with human_ensembl_id, human_gene_name")
    ap.add_argument("--markers", nargs="*", default=None,
                    help="extra SYMBOL=ENSG pairs to force onto the panel")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    for label, path in (
        ("source", args.source),
        ("target", args.target),
        ("pred-impact", args.pred_impact),
        ("pred-scgen", args.pred_scgen),
        ("eval-impact", args.eval_impact),
        ("eval-scgen", args.eval_scgen),
    ):
        if path is not None and not path.exists():
            raise SystemExit(f"missing {label}: {path}")
    run_figures(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

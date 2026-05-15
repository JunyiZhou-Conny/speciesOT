#!/usr/bin/env python3
"""Standalone (non-notebook) results figure generator. Mirrors notebook 13 logic
but uses matplotlib's Agg backend explicitly so figures are guaranteed to land on
disk. Idempotent: safe to re-run as more eval csvs land.

Outputs under speciesOT/baseline/analysis/hvg_flavor_results_outputs/figures/:
  - r2_means_heatmap_per_flavor.{pdf,png}
  - mmd_heatmap_per_flavor.{pdf,png}
  - method_gap_vs_distribution_gap_R2.{pdf,png}
  - method_gap_vs_distribution_gap_MMD.{pdf,png}
  - biomarker_density_PTPRC_CD3E.{pdf,png}  (if best (flavor, group, mode) cell
                                              has both scgen and impact imputed)

NOTE on R^2 metric semantics
----------------------------
The upstream cellot/cellot_gpu/scripts/evaluate.py emits a metric labeled
"r2-means" (and "r2-stds", "r2-pairwise_feat_corrs") in every evals.csv, but the
underlying call is pd.Series.corr(...) which returns the raw Pearson correlation
coefficient r in [-1, 1] — NOT R^2. Earlier revisions of this script consumed
that value as if it were R^2, which silently inflated every reported number.

This script now squares all r2-* metric values immediately after reading
evals.csv, so every downstream pivot, heatmap, and scatter reports true R^2
(coefficient of determination, in [0, 1]).
"""
import os
import warnings
from pathlib import Path
from itertools import product

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT")
RESULTS_DIR = BASE / "cellot/cellot_gpu/results"
OUT_DIR = BASE / "speciesOT/baseline/analysis/hvg_flavor_results_outputs"
FIG_DIR = OUT_DIR / "figures"
OUT_DIR.mkdir(parents=True, exist_ok=True)
FIG_DIR.mkdir(parents=True, exist_ok=True)

FLAVORS = ["seurat", "cell_ranger", "seurat_v3", "seurat_v3_paper", "pearson_residuals"]
GROUPS = ["a", "b", "c", "d"]
MODES = ["ood", "iid"]
MODELS = ["scgen", "impact_cellot"]
MODEL_LABEL = {"scgen": "scGen", "impact_cellot": "IMPACT_CellOT"}
EVAL_SUBDIR = "evals_ood_latent_space"
HOLDOUT_LUT = {
    "a": ["CL:0000625"],
    "b": ["CL:0000625", "CL:0000893"],
    "c": ["CL:0000624", "CL:0000625", "CL:0000893"],
    "d": ["CL:0000624"],
}
MARKERS = {"PTPRC (CD45)": "ENSG00000081237", "CD3E": "ENSG00000198851"}


def cell_eval_path(flavor, gk, mode, model):
    return RESULTS_DIR / f"hvg_{flavor}_{gk}_{mode}" / model / EVAL_SUBDIR / "evals.csv"


def cell_imputed_path(flavor, gk, mode, model):
    return RESULTS_DIR / f"hvg_{flavor}_{gk}_{mode}" / model / EVAL_SUBDIR / "imputed.h5ad"


R2_METRICS = {"r2-means", "r2-stds", "r2-pairwise_feat_corrs"}


def gather_long():
    rows = []
    for flavor, gk, mode, model in product(FLAVORS, GROUPS, MODES, MODELS):
        p = cell_eval_path(flavor, gk, mode, model)
        if not p.exists() or p.stat().st_size < 200:
            continue
        df = pd.read_csv(p)
        # evaluate.py mislabels Pearson r as r2-* — square here to get true R^2
        is_r2 = df["metric"].isin(R2_METRICS)
        df.loc[is_r2, "value"] = df.loc[is_r2, "value"] ** 2
        df["flavor"] = flavor
        df["group"] = gk
        df["mode"] = mode
        df["model"] = model
        rows.append(df)
    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True)


def headline(long_df, metric):
    sub = long_df[long_df["metric"] == metric].copy()
    if sub.empty:
        return pd.DataFrame()
    agg = sub.groupby(["flavor", "group", "mode", "model", "ncells"], as_index=False)["value"].mean()
    largest = agg.sort_values("ncells").drop_duplicates(["flavor", "group", "mode", "model"], keep="last")
    pivot = largest.pivot_table(index=["flavor", "group", "mode"], columns="model", values="value")
    return pivot.reindex(columns=MODELS)


def plot_per_flavor_heatmap(pivot, metric_label, cmap, vmin, vmax, fmt, out_stem):
    if pivot.empty:
        print(f"  no data for {metric_label}; skipping")
        return
    rows = [(gk, mode) for gk in GROUPS for mode in MODES]
    row_labels = [f"{gk.upper()} {mode.upper()}" for gk, mode in rows]
    n = len(FLAVORS)
    fig, axes = plt.subplots(1, n, figsize=(2.6 * n, 4.2), sharey=True)
    if n == 1:
        axes = [axes]
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    for ax, flavor in zip(axes, FLAVORS):
        mat = np.full((len(rows), len(MODELS)), np.nan)
        if flavor in pivot.index.get_level_values(0):
            sub = pivot.xs(flavor, level="flavor", drop_level=True)
            for i, (gk, mode) in enumerate(rows):
                for j, model in enumerate(MODELS):
                    if (gk, mode) in sub.index and model in sub.columns:
                        v = sub.loc[(gk, mode), model]
                        if pd.notna(v):
                            mat[i, j] = v
        ax.imshow(mat, cmap=cmap, norm=norm, aspect="auto")
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                v = mat[i, j]
                txt = fmt.format(v) if pd.notna(v) else "—"
                color = "white" if (pd.notna(v) and norm(v) > 0.55) else "black"
                ax.text(j, i, txt, ha="center", va="center", color=color, fontsize=8)
        ax.set_xticks(range(len(MODELS)))
        ax.set_xticklabels([MODEL_LABEL[m] for m in MODELS], fontsize=9, rotation=15)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels(row_labels, fontsize=8)
        ax.set_title(flavor, fontsize=10)
    fig.suptitle(metric_label, fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    pdf_path = FIG_DIR / f"{out_stem}.pdf"
    png_path = FIG_DIR / f"{out_stem}.png"
    fig.savefig(pdf_path, dpi=150, bbox_inches="tight")
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {pdf_path.exists() and pdf_path.stat().st_size > 1000}  {pdf_path}")
    print(f"  saved: {png_path.exists() and png_path.stat().st_size > 1000}  {png_path}")


def gap_scatter(pivot, metric_label, out_stem, lower_is_better=False):
    if pivot.empty:
        return None
    sign = -1 if lower_is_better else 1
    rows_data = []
    for flavor in FLAVORS:
        if flavor not in pivot.index.get_level_values(0):
            continue
        sub = pivot.xs(flavor, level="flavor", drop_level=True)
        for gk in GROUPS:
            try:
                ood_scgen = sub.loc[(gk, "ood"), "scgen"]
                ood_impact = sub.loc[(gk, "ood"), "impact_cellot"]
                iid_scgen = sub.loc[(gk, "iid"), "scgen"]
                iid_impact = sub.loc[(gk, "iid"), "impact_cellot"]
            except KeyError:
                continue
            if any(pd.isna(v) for v in (ood_scgen, ood_impact, iid_scgen, iid_impact)):
                continue
            rows_data.append({
                "flavor": flavor, "group": gk,
                "method_gap_OOD":   sign * (ood_impact - ood_scgen),
                "method_gap_IID":   sign * (iid_impact - iid_scgen),
                "dist_gap_scgen":   sign * (iid_scgen - ood_scgen),
                "dist_gap_impact":  sign * (iid_impact - ood_impact),
            })
    if not rows_data:
        return None
    df = pd.DataFrame(rows_data)
    df.to_csv(OUT_DIR / f"{out_stem}.csv", index=False)
    fig, ax = plt.subplots(figsize=(6.5, 5))
    color_map = {f: c for f, c in zip(FLAVORS, plt.cm.tab10(np.linspace(0, 1, len(FLAVORS))))}
    marker_map = {"a": "o", "b": "s", "c": "^", "d": "D"}
    for _, r in df.iterrows():
        ax.scatter(r["dist_gap_impact"], r["method_gap_OOD"],
                   c=[color_map[r["flavor"]]], marker=marker_map[r["group"]],
                   s=120, edgecolors="black", linewidths=0.5)
        ax.annotate(f"{r['flavor'][:3]}-{r['group'].upper()}",
                    (r["dist_gap_impact"], r["method_gap_OOD"]),
                    fontsize=7, alpha=0.8, xytext=(4, 4), textcoords="offset points")
    ax.axhline(0, color="grey", lw=0.5)
    ax.axvline(0, color="grey", lw=0.5)
    ax.set_xlabel("distribution gap (IMPACT, IID − OOD)")
    ax.set_ylabel(f"method gap OOD ({metric_label})\nIMPACT − scGen")
    ax.set_title(f"{metric_label}: how much does OT help, vs how much does OOD hurt?")
    handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=color_map[f], markersize=8, label=f) for f in FLAVORS]
    handles += [plt.Line2D([0], [0], marker=marker_map[g], color="grey", markersize=8, lw=0, label=f"Group {g.upper()}") for g in GROUPS]
    ax.legend(handles=handles, fontsize=7, loc="best", ncol=2)
    fig.tight_layout()
    pdf_path = FIG_DIR / f"{out_stem}.pdf"
    png_path = FIG_DIR / f"{out_stem}.png"
    fig.savefig(pdf_path, dpi=150, bbox_inches="tight")
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved: {pdf_path.exists() and pdf_path.stat().st_size > 1000}  {pdf_path}")
    return df


def biomarker_density_plot(flavor, gk, mode, out_stem):
    try:
        import anndata as ad
    except ImportError:
        print("anndata not available")
        return None
    DATA_DIR = BASE / "cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg"
    src_path = DATA_DIR / f"hvg_{flavor}_{gk}_v07.h5ad"
    if not src_path.exists():
        print(f"  src missing: {src_path}")
        return None
    impact_p = cell_imputed_path(flavor, gk, mode, "impact_cellot")
    scgen_p = cell_imputed_path(flavor, gk, mode, "scgen")
    impact_a = ad.read_h5ad(impact_p) if impact_p.exists() else None
    scgen_a = ad.read_h5ad(scgen_p) if scgen_p.exists() else None
    if impact_a is None and scgen_a is None:
        print(f"  no imputed for {flavor}/{gk}/{mode}; skipping density")
        return None
    src = ad.read_h5ad(src_path)
    is_holdout = src.obs["cell_type_ontology_term_id"].astype(str).isin(HOLDOUT_LUT[gk])
    actual_mouse = src[(src.obs["condition"] == "mouse") & is_holdout]
    actual_human = src[(src.obs["condition"] == "human") & is_holdout]

    fig, axes = plt.subplots(1, len(MARKERS), figsize=(5.5 * len(MARKERS), 4))
    if len(MARKERS) == 1:
        axes = [axes]
    for ax, (label, ensg) in zip(axes, MARKERS.items()):
        if ensg not in src.var_names:
            ax.text(0.5, 0.5, f"{label}\nnot in {flavor}\ntop-1000",
                    ha="center", va="center", transform=ax.transAxes)
            ax.set_xticks([]); ax.set_yticks([])
            continue
        gi = list(src.var_names).index(ensg)
        traces = []
        if len(actual_mouse) > 0:
            traces.append(("actual mouse", np.asarray(actual_mouse.X[:, gi]).ravel(), "tab:blue"))
        if len(actual_human) > 0:
            traces.append(("actual human", np.asarray(actual_human.X[:, gi]).ravel(), "tab:green"))
        if scgen_a is not None and ensg in scgen_a.var_names:
            gj = list(scgen_a.var_names).index(ensg)
            traces.append(("scGen pred", np.asarray(scgen_a.X[:, gj]).ravel(), "tab:orange"))
        if impact_a is not None and ensg in impact_a.var_names:
            gj = list(impact_a.var_names).index(ensg)
            traces.append(("IMPACT pred", np.asarray(impact_a.X[:, gj]).ravel(), "tab:red"))
        for name, vals, color in traces:
            if len(vals) == 0:
                continue
            ax.hist(vals, bins=40, density=True, alpha=0.4, color=color, label=name)
        ax.set_title(f"{label} ({ensg})")
        ax.legend(fontsize=8)
        ax.set_xlabel("expression (log-norm)")
        ax.set_ylabel("density")
    fig.suptitle(f"{flavor} / Group {gk.upper()} / {mode.upper()}")
    fig.tight_layout(rect=[0, 0, 1, 0.95])
    pdf_path = FIG_DIR / f"{out_stem}.pdf"
    png_path = FIG_DIR / f"{out_stem}.png"
    fig.savefig(pdf_path, dpi=150, bbox_inches="tight")
    fig.savefig(png_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  saved biomarker {png_path.exists()}: {png_path}")
    return True


# ===========================================================================
# Reusable presentation functions (added 2026-05-08 for paper figure F + G replicas)
# These are designed to be called from notebooks with arbitrary results sources,
# not just the matrix in this script. See notebook 18 for usage examples.
# ===========================================================================

def plot_metric_bars(
    long_df,
    metric,
    *,
    group_by="group",
    hue_by="model",
    facet_by="flavor",
    facet_order=None,
    group_order=None,
    hue_order=None,
    hue_palette=None,
    facet_label=None,
    metric_label=None,
    ylim=None,
    figsize_per_facet=(2.4, 3.3),
    out_path=None,
):
    """Reusable bar-plot replica of CellOT paper figure F.

    `long_df` is any DataFrame with columns including {`metric`, `value`, group_by,
    hue_by, facet_by}. Typically obtained from `gather_long(...)` or by reading
    `evals.csv` files and tagging with the relevant categorical columns.

    Layout: one subplot per `facet_by` value. Within each subplot, x-axis groups
    by `group_by`, with bars at each x position colored by `hue_by`.

    Parameters
    ----------
    long_df : pd.DataFrame
    metric : str (e.g. 'r2-means' or 'mmd')
    group_by, hue_by, facet_by : str column names
    facet_order, group_order, hue_order : optional explicit orderings
    hue_palette : optional dict {hue_value: matplotlib_color}
    facet_label, metric_label : human-readable axis labels
    ylim : optional (low, high) tuple
    figsize_per_facet : (width, height) per subplot
    out_path : if given, save to {out_path}.pdf and {out_path}.png
    """
    sub = long_df[long_df["metric"] == metric].copy()
    if sub.empty:
        print(f"plot_metric_bars: no rows with metric={metric!r}; skipping")
        return None

    # Aggregate over reps within (group, hue, facet) and pick the largest n_cells
    # as the headline (matches `headline()` convention).
    if "ncells" in sub.columns:
        agg = sub.groupby([facet_by, group_by, hue_by, "ncells"], as_index=False)["value"].mean()
        largest = agg.sort_values("ncells").drop_duplicates([facet_by, group_by, hue_by], keep="last")
    else:
        largest = sub.groupby([facet_by, group_by, hue_by], as_index=False)["value"].mean()

    facets = facet_order or sorted(largest[facet_by].unique())
    groups = group_order or sorted(largest[group_by].unique())
    hues = hue_order or sorted(largest[hue_by].unique())
    if hue_palette is None:
        cm = plt.cm.tab10(np.linspace(0, 1, max(len(hues), 3)))
        hue_palette = {h: cm[i] for i, h in enumerate(hues)}

    n = len(facets)
    fig, axes = plt.subplots(1, n, figsize=(figsize_per_facet[0] * n, figsize_per_facet[1]),
                              sharey=True)
    if n == 1:
        axes = [axes]

    bar_w = 0.8 / max(len(hues), 1)
    x_indices = np.arange(len(groups))

    for ax, facet in zip(axes, facets):
        sub_facet = largest[largest[facet_by] == facet]
        for j, hue in enumerate(hues):
            row = sub_facet[sub_facet[hue_by] == hue]
            vals = []
            for grp in groups:
                v = row[row[group_by] == grp]["value"]
                vals.append(float(v.iloc[0]) if len(v) else np.nan)
            offset = (j - (len(hues) - 1) / 2) * bar_w
            ax.bar(x_indices + offset, vals, bar_w, color=hue_palette[hue],
                   edgecolor="black", linewidth=0.4, label=str(hue))
        ax.set_xticks(x_indices)
        ax.set_xticklabels([str(g) for g in groups], rotation=30, ha="right", fontsize=9)
        ax.set_title(str(facet), fontsize=11)
        if ylim:
            ax.set_ylim(ylim)
        ax.tick_params(axis="y", labelsize=9)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    axes[0].set_ylabel(metric_label or metric, fontsize=11)
    if facet_label:
        fig.text(0.5, -0.02, facet_label, ha="center", fontsize=11)
    axes[-1].legend(fontsize=9, frameon=False, loc="best")
    fig.tight_layout()

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        for ext in ("pdf", "png"):
            full = out_path.with_suffix(f".{ext}")
            fig.savefig(full, dpi=150, bbox_inches="tight")
            print(f"  saved {full}")
    return fig


def plot_marginals_paper_style(
    actual_target,
    predicted_traces,
    gene_panel,
    var_index_lookup,
    *,
    actual_source=None,
    palette=None,
    n_cols=2,
    figsize_per_panel=(3.4, 2.8),
    title=None,
    out_path=None,
):
    """Reusable density-overlay replica of CellOT paper figure G.

    Parameters
    ----------
    actual_target : np.ndarray (n_cells, n_genes) — the true target distribution
    predicted_traces : dict {label: np.ndarray (n_cells, n_genes)}
        e.g. {"scGen pred": ..., "IMPACT pred": ...}
    gene_panel : dict {pretty_label: ENSG_or_index}
    var_index_lookup : dict {ENSG_id: column_index_in_actual_target}
    actual_source : optional np.ndarray for the source distribution (e.g. mouse) overlay
    palette : optional dict {label: color}
    n_cols : grid columns
    figsize_per_panel : (w, h) per subplot
    title : suptitle
    out_path : if given, save to {out_path}.{pdf,png}
    """
    n_panels = len(gene_panel)
    n_rows = (n_panels + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols,
                              figsize=(figsize_per_panel[0] * n_cols,
                                       figsize_per_panel[1] * n_rows))
    axes = np.array(axes).flatten() if n_panels > 1 else [axes]

    if palette is None:
        palette = {
            "actual mouse": "tab:blue",
            "actual human (target)": "darkgreen",
            "actual target": "darkgreen",
            "scGen pred": "tab:orange",
            "IMPACT pred": "tab:red",
        }

    for ax, (label, key) in zip(axes, gene_panel.items()):
        # Resolve column index
        if key in var_index_lookup:
            col = var_index_lookup[key]
        else:
            ax.text(0.5, 0.5, f"{label}\nnot in gene set",
                    ha="center", va="center", transform=ax.transAxes,
                    color="grey", fontsize=10, fontstyle="italic")
            ax.set_xticks([]); ax.set_yticks([])
            ax.set_title(label, fontsize=10, color="grey")
            continue

        bins = 30
        # Source overlay (mouse) if provided
        if actual_source is not None and len(actual_source) > 0:
            ax.hist(actual_source[:, col], bins=bins, density=True, alpha=0.4,
                    color=palette.get("actual mouse", "tab:blue"), label="actual mouse")
        # Always plot actual target
        ax.hist(actual_target[:, col], bins=bins, density=True, alpha=0.55,
                color=palette.get("actual target", palette.get("actual human (target)", "darkgreen")),
                label="actual target")
        for trace_label, X in predicted_traces.items():
            if X is None or len(X) == 0:
                continue
            ax.hist(X[:, col], bins=bins, density=True, alpha=0.45,
                    color=palette.get(trace_label, "grey"), label=trace_label)
        ax.set_title(label, fontsize=10, fontweight="bold")
        ax.set_xlabel("expression (log-norm)", fontsize=8)
        ax.set_ylabel("density", fontsize=8)
        ax.legend(fontsize=7)
        ax.tick_params(axis="both", labelsize=7)

    # Hide unused axes
    for ax in axes[n_panels:]:
        ax.axis("off")

    if title:
        fig.suptitle(title, fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96] if title else None)

    if out_path is not None:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        for ext in ("pdf", "png"):
            full = out_path.with_suffix(f".{ext}")
            fig.savefig(full, dpi=150, bbox_inches="tight")
            print(f"  saved {full}")
    return fig


def main():
    long_df = gather_long()
    if long_df.empty:
        print("No eval csvs found; nothing to plot.")
        return 1
    print(f"Loaded {len(long_df)} rows from {long_df['flavor'].nunique()} flavors x {long_df['group'].nunique()} groups")
    long_df.to_csv(OUT_DIR / "results_long.csv", index=False)

    r2_pivot = headline(long_df, "r2-means")
    mmd_pivot = headline(long_df, "mmd")
    r2_pivot.to_csv(OUT_DIR / "results_pivot_R2_means.csv")
    mmd_pivot.to_csv(OUT_DIR / "results_pivot_MMD.csv")

    print("\n=== R2 of means ===")
    print(r2_pivot.round(4).to_string())
    print("\n=== MMD ===")
    print(mmd_pivot.round(4).to_string())

    print("\n=== Plots ===")
    plot_per_flavor_heatmap(r2_pivot, "R² of means (latent space)", "viridis",
                             vmin=0.0, vmax=1.0, fmt="{:.3f}",
                             out_stem="r2_means_heatmap_per_flavor")
    plot_per_flavor_heatmap(mmd_pivot, "MMD (latent space) — lower is better", "viridis_r",
                             vmin=float(mmd_pivot.min().min()) if not mmd_pivot.empty and mmd_pivot.notna().any().any() else 0.0,
                             vmax=float(mmd_pivot.max().max()) if not mmd_pivot.empty and mmd_pivot.notna().any().any() else 1.0,
                             fmt="{:.4f}", out_stem="mmd_heatmap_per_flavor")
    gap_scatter(r2_pivot, "R²", "method_gap_vs_distribution_gap_R2")
    gap_scatter(mmd_pivot, "MMD", "method_gap_vs_distribution_gap_MMD", lower_is_better=True)

    if not r2_pivot.empty and "impact_cellot" in r2_pivot.columns:
        impact_only = r2_pivot["impact_cellot"].dropna()
        if len(impact_only):
            best = impact_only.idxmax()
            print(f"\nBest IMPACT cell: {best}, R²={float(impact_only.max()):.4f}")
            biomarker_density_plot(*best, "biomarker_density_PTPRC_CD3E")

    print("\nDone.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())

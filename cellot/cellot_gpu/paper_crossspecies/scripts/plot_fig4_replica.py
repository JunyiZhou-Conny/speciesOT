"""Paper-style Fig. 4e–g from the local LPS cross-species replication.

Uses saved imputed.h5ad + the same toggle_ood split as training. Does not reload
models. Panel f plots Pearson r (evaluate.py ``r2-means``), which is what the
paper axis labeled r².

USAGE (from repo root, CellOT env):
    PYTHONPATH=cellot/cellot_gpu python cellot/cellot_gpu/paper_crossspecies/scripts/plot_fig4_replica.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import anndata as ad
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.lines import Line2D

REPO = Path(__file__).resolve().parents[4]
CELLOT = REPO / "cellot" / "cellot_gpu"
RESULTS = CELLOT / "results"
DATA = CELLOT / "datasets" / "scrna-crossspecies" / "hvg-top1k-train-only.h5ad"
PAPER_CSV = REPO / "scgen-cellot-ablation" / "species.csv"
OUT = REPO / "speciesOT" / "baseline" / "analysis" / "paper_crossspecies_fig4_outputs"
FIG = OUT / "figures_paperstyle"

if str(CELLOT) not in sys.path:
    sys.path.insert(0, str(CELLOT))

from cellot.data.cell import split_cell_data  # noqa: E402

COLORS = {
    "cellot": "#F2545B",
    "scgen": "#C3BABA",
    "cae": "#9A8F97",
    "treated": "#114083",
    "control": "#A7BED3",
}
TAGS = {
    "rat": "paper_crossspecies_rat_ood",
    "mouse": "paper_crossspecies_mouse_ood",
}
# Paper Fig. 4e column order. Nfkbia / Mmp12 are absent from our re-HVG set.
PAPER_GENES_E = [
    "Nfkbia", "Oasl1", "Tnfaip6", "Mmp12", "Sdc4", "Ch25h", "Acsl1", "Slc7a2", "Cxcl5",
]
PAPER_GENES_G = ["Oasl1", "Sdc4", "Acsl1", "Slc7a2"]
ALIASES = {"Nfkb1a": "Nfkbia", "Nfkbia": "Nfkbia"}


def resolve_gene(columns, name: str) -> str | None:
    for cand in (name, ALIASES.get(name, name)):
        if cand in columns:
            return cand
    return None


def ood_control_treated(adata: ad.AnnData, holdout: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    data = adata[adata.obs["condition"].isin(["unst", "LPS6"])].copy()
    data.obs["split"] = split_cell_data(
        data,
        name="toggle_ood",
        key="species",
        holdout=holdout,
        mode="ood",
        groupby=["species", "condition"],
        random_state=0,
        test_size=500,
        stratify="condition",
    )
    ood = data[data.obs["split"] == "ood"]
    control = ood[ood.obs["condition"] == "unst"].to_df()
    treated = ood[ood.obs["condition"] == "LPS6"].to_df()
    return control, treated


def read_imputed(tag: str, model: str, setting: str) -> pd.DataFrame:
    path = RESULTS / tag / model / f"evals_{setting}_data_space_paper" / "imputed.h5ad"
    return ad.read_h5ad(path).to_df()


def eval_stats(tag: str, model: str, setting: str, metric: str, ncells: int = 1000) -> tuple[float, float]:
    path = RESULTS / tag / model / f"evals_{setting}_data_space_paper" / "evals.csv"
    df = pd.read_csv(path)
    sub = df[(df["metric"] == metric) & (df["ncells"] == ncells)]
    if "nfeatures" in sub.columns:
        sub = sub[sub["nfeatures"].astype(str) == "50"]
    return float(sub["value"].mean()), float(sub["value"].std())


def paper_stats(paper: pd.DataFrame, holdout: str, model: str, metric: str) -> tuple[float, float]:
    sub = paper[
        (paper["experiment"] == "species-ood")
        & (paper["holdout"] == holdout)
        & (paper["mode"] == "ood")
        & (paper["model"] == model)
        & (paper["metric"] == metric)
    ]
    if sub.empty:
        return np.nan, np.nan
    return float(sub["value"].mean()), float(sub["value"].std())


def layer_stats(df: pd.DataFrame, genes: list[str]) -> pd.DataFrame:
    rows = []
    for g in genes:
        col = resolve_gene(df.columns, g)
        if col is None:
            rows.append({"gene": g, "mean": np.nan, "frac": np.nan, "present": False})
            continue
        x = df[col].to_numpy(dtype=float)
        rows.append({
            "gene": g,
            "mean": float(np.mean(x)),
            "frac": float(np.mean(x > 0)),
            "present": True,
        })
    return pd.DataFrame(rows)


def plot_fig4e(clouds: dict, genes: list[str], present: list[str]) -> None:
    row_order = [
        ("control", "Control"),
        ("treated", "Treated"),
        ("cellot_ood", "CellOT o.o.d."),
        ("scgen_ood", "scGen o.o.d."),
    ]
    holdouts = ["rat", "mouse"]
    fig, axes = plt.subplots(2, 1, figsize=(10.5, 6.2), sharex=True)
    vmax = 0.0
    stats = {}
    for h in holdouts:
        for key, _ in row_order:
            st = layer_stats(clouds[h][key], genes)
            stats[(h, key)] = st
            vmax = max(vmax, float(np.nanmax(st["mean"].to_numpy())))
    norm = mcolors.Normalize(vmin=0.0, vmax=max(vmax, 1e-6))
    cmap = plt.cm.Blues

    for ax, h in zip(axes, holdouts):
        for yi, (key, label) in enumerate(row_order):
            st = stats[(h, key)]
            for xi, g in enumerate(genes):
                row = st[st["gene"] == g].iloc[0]
                if not row["present"] or not np.isfinite(row["mean"]):
                    ax.scatter(xi, yi, s=18, facecolors="none", edgecolors="#bbbbbb", linewidths=0.6)
                    continue
                ax.scatter(
                    xi, yi,
                    s=40 + 420 * row["frac"],
                    c=[cmap(norm(row["mean"]))],
                    edgecolors="0.25",
                    linewidths=0.4,
                    zorder=2,
                )
        ax.set_yticks(range(len(row_order)))
        ax.set_yticklabels([lab for _, lab in row_order])
        ax.set_ylim(len(row_order) - 0.6, -0.6)
        ax.set_xlim(-0.6, len(genes) - 0.4)
        ax.set_ylabel(h.capitalize(), rotation=0, labelpad=28, va="center", fontweight="bold")
        ax.tick_params(axis="x", length=0)
        ax.tick_params(axis="y", length=0)
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.axhline(-0.5, color="0.9", lw=0.5)

    axes[1].set_xticks(range(len(genes)))
    labels = [g if g in present else f"{g}*" for g in genes]
    axes[1].set_xticklabels(labels, rotation=40, ha="right")
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=axes, fraction=0.03, pad=0.02)
    cbar.set_label("Mean gene expression")
    size_handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor="0.55",
               markeredgecolor="0.25", markersize=np.sqrt(40 + 420 * f),
               label=f"{int(f * 100)}%")
        for f in (0.2, 0.6, 1.0)
    ]
    axes[0].legend(handles=size_handles, title="Fraction of cells > 0",
                   loc="upper left", bbox_to_anchor=(1.18, 1.05), frameon=False)
    fig.suptitle("Fig. 4e replica — LPS marker genes (our OOD models)", y=1.02, fontsize=13)
    fig.text(
        0.01, -0.02,
        "*Nfkbia and Mmp12 are not in our re-selected 1000-HVG set. "
        "IID rows omitted: we trained OOD models only.",
        fontsize=8, color="0.35",
    )
    fig.savefig(FIG / "fig4e_dotplot.pdf", bbox_inches="tight")
    fig.savefig(FIG / "fig4e_dotplot.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_fig4f(repl: pd.DataFrame, paper: pd.DataFrame) -> None:
    holdouts = ["rat", "mouse"]
    fig, axes = plt.subplots(2, 2, figsize=(9.6, 6.4), sharex="col")
    specs = [
        (0, "r2-means", "Pearson r of feature means\n(paper labeled this $r^2$)", (0, 0.75), False),
        (1, "mmd", "MMD  ↓", (0, 0.38), True),
    ]
    width = 0.36
    for row, metric, ylabel, ylim, lower_better in specs:
        for col, (title, src, models, colors) in enumerate([
            ("Paper species.csv", paper, ["cellot", "scgen", "cae"],
             [COLORS["cellot"], COLORS["scgen"], COLORS["cae"]]),
            ("Our replication", repl, ["cellot", "scgen"],
             [COLORS["cellot"], COLORS["scgen"]]),
        ]):
            ax = axes[row, col]
            x = np.arange(len(holdouts))
            n = len(models)
            for i, (model, color) in enumerate(zip(models, colors)):
                means, sds = [], []
                for h in holdouts:
                    sub = src[(src["holdout"] == h) & (src["model"] == model) & (src["metric"] == metric)]
                    means.append(float(sub["mean"].iloc[0]) if len(sub) else np.nan)
                    sds.append(float(sub["sd"].iloc[0]) if len(sub) else 0.0)
                offset = (i - (n - 1) / 2) * width
                ax.bar(
                    x + offset, means, width * 0.92, yerr=sds, color=color,
                    capsize=3, label={"cellot": "CellOT", "scgen": "scGen", "cae": "cAE"}[model],
                    edgecolor="0.2", linewidth=0.4,
                )
            ax.set_xticks(x)
            ax.set_xticklabels([h.capitalize() for h in holdouts])
            ax.set_ylim(*ylim)
            if col == 0:
                ax.set_ylabel(ylabel)
            if row == 0:
                ax.set_title(title)
            if row == 0:
                ax.legend(frameon=False, loc="lower right")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
    fig.suptitle(
        "Fig. 4f — OOD LPS, ncells=1000, 50 DE genes, 10 bootstraps\n"
        "Left: paper source data. Right: our paper_crossspecies_*_ood evals.csv (unsquared r2-means).",
        y=1.03, fontsize=12,
    )
    fig.tight_layout()
    fig.savefig(FIG / "fig4f_ood_bars_paper_vs_ours.pdf", bbox_inches="tight")
    fig.savefig(FIG / "fig4f_ood_bars_paper_vs_ours.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def plot_fig4g(clouds: dict, genes: list[str]) -> None:
    present = [g for g in genes if resolve_gene(clouds["rat"]["treated"].columns, g)]
    fig, axes = plt.subplots(2, len(present), figsize=(3.1 * len(present), 5.6), sharey=False)
    if len(present) == 1:
        axes = np.array([[axes[0]], [axes[1]]])
    for row, holdout in enumerate(["rat", "mouse"]):
        for col, gene in enumerate(present):
            ax = axes[row, col]
            gcol = resolve_gene(clouds[holdout]["treated"].columns, gene)
            series = {
                "treated": clouds[holdout]["treated"][gcol],
                "cellot": clouds[holdout]["cellot_ood"][gcol],
                "scgen": clouds[holdout]["scgen_ood"][gcol],
            }
            df = pd.concat(series, names=["layer"]).reset_index(level=0).rename(columns={gcol: "expr"})
            sns.kdeplot(
                data=df, x="expr", hue="layer", common_norm=False, ax=ax, legend=False,
                palette={"treated": COLORS["treated"], "cellot": COLORS["cellot"], "scgen": COLORS["scgen"]},
                hue_order=["treated", "cellot", "scgen"],
                clip=(0, None),
            )
            if row == 0:
                ax.set_title(gene, fontstyle="italic")
            ax.set_xlabel("")
            ax.set_ylabel(holdout.capitalize() if col == 0 else "")
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
    handles = [
        Line2D([0], [0], color=COLORS["treated"], lw=2, label="Treated"),
        Line2D([0], [0], color=COLORS["cellot"], lw=2, label="CellOT o.o.d."),
        Line2D([0], [0], color=COLORS["scgen"], lw=2, label="scGen o.o.d."),
    ]
    axes[0, -1].legend(handles=handles, loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False)
    fig.suptitle("Fig. 4g replica — OOD marginals on the paper’s four genes", y=1.02, fontsize=13)
    fig.tight_layout()
    fig.savefig(FIG / "fig4g_ood_marginals.pdf", bbox_inches="tight")
    fig.savefig(FIG / "fig4g_ood_marginals.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    sns.set_context("talk", font_scale=0.85)
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "white"

    print(f"[fig4] reading {DATA}")
    adata = ad.read_h5ad(DATA)
    present_e = [g for g in PAPER_GENES_E if resolve_gene(adata.var_names, g)]
    missing_e = [g for g in PAPER_GENES_E if g not in present_e]
    print(f"[fig4] marker genes present: {present_e}")
    print(f"[fig4] marker genes missing from HVG set: {missing_e}")

    clouds = {}
    for holdout, tag in TAGS.items():
        print(f"[fig4] loading {holdout} clouds")
        control, treated = ood_control_treated(adata, holdout)
        cellot = read_imputed(tag, "impact_cellot", "ood")
        scgen = read_imputed(tag, "scgen", "ood")
        print(
            f"  {holdout}: control={len(control)} treated={treated.shape[0]} "
            f"cellot={len(cellot)} scgen={len(scgen)} "
            f"control∩imputed={len(set(control.index) & set(cellot.index))}"
        )
        clouds[holdout] = {
            "control": control,
            "treated": treated,
            "cellot_ood": cellot,
            "scgen_ood": scgen,
        }

    paper_raw = pd.read_csv(PAPER_CSV)
    paper_rows, repl_rows = [], []
    for holdout, tag in TAGS.items():
        for model, local in [("cellot", "impact_cellot"), ("scgen", "scgen"), ("cae", None)]:
            for metric in ("r2-means", "mmd"):
                pm, ps = paper_stats(paper_raw, holdout, model, metric)
                paper_rows.append({"holdout": holdout, "model": model, "metric": metric, "mean": pm, "sd": ps})
                if local is None:
                    continue
                rm, rs = eval_stats(tag, local, "ood", metric)
                repl_rows.append({"holdout": holdout, "model": model, "metric": metric, "mean": rm, "sd": rs})
    paper = pd.DataFrame(paper_rows)
    repl = pd.DataFrame(repl_rows)
    cmp = paper.merge(repl, on=["holdout", "model", "metric"], how="left", suffixes=("_paper", "_ours"))
    cmp.to_csv(OUT / "fig4f_paper_vs_ours.csv", index=False)
    print("\nFig. 4f numbers (Pearson r / MMD, 50 genes, ncells=1000)")
    print(cmp.round(4).to_string(index=False))

    plot_fig4e(clouds, PAPER_GENES_E, present_e)
    plot_fig4f(repl, paper)
    plot_fig4g(clouds, PAPER_GENES_G)
    print(f"\n[fig4] wrote {FIG}")


if __name__ == "__main__":
    main()

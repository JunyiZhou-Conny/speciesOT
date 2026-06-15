"""Helpers for notebook 23 — Bunne Fig. 4 cross-species LPS replication plots.

Uses the same loading paths as ``cellot/cellot_gpu/scripts/plot.py`` and
``cellot.utils.viz.plot_marginals``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

# Paper palette from scripts/plot.py
PAPER_COLORS = {
    "cellot": "#F2545B",
    "impact_cellot": "#F2545B",
    "treated": "#114083",
    "control": "#A7BED3",
    "cae": "#9A8F97",
    "scgen": "#C3BABA",
}

MODEL_ORDER = ["impact_cellot", "scgen"]
MODEL_LABEL = {
    "impact_cellot": "CellOT",
    "scgen": "scGen",
    "cellot": "CellOT",
    "cae": "cAE",
}

PAPER_MARKERS_FIG4E = [
    "Nfkbia", "Oasl1", "Tnfaip6", "Mmp12", "Sdc4", "Ch25h", "Acsl1", "Slc7a2", "Cxcl5",
]
PAPER_MARKERS_FIG4G = ["Oasl1", "Sdc4", "Acsl1", "Slc7a2"]

TAGS = {
    "rat": "paper_crossspecies_rat_ood",
    "mouse": "paper_crossspecies_mouse_ood",
}

EVAL_PREFIX = "evals_{setting}_data_space_paper"


def repo_paths(base: Path) -> Dict[str, Path]:
    base = base.resolve()
    cellot_gpu = base / "cellot" / "cellot_gpu"
    return {
        "base": base,
        "cellot_gpu": cellot_gpu,
        "results": cellot_gpu / "results",
        "out": base / "speciesOT" / "baseline" / "analysis" / "paper_crossspecies_fig4_outputs",
    }


def model_dir(results: Path, tag: str, model: str) -> Path:
    return results / tag / model


def eval_dir(results: Path, tag: str, model: str, setting: str) -> Path:
    return model_dir(results, tag, model) / EVAL_PREFIX.format(setting=setting)


def load_evals_csv(results: Path, tag: str, model: str, setting: str) -> pd.DataFrame:
    path = eval_dir(results, tag, model, setting) / "evals.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def load_extended_metrics(results: Path, tag: str, model: str) -> pd.DataFrame:
    path = eval_dir(results, tag, model, "ood") / "extended_metrics.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def summarize_eval_reps(
    df: pd.DataFrame,
    metric: str,
    ncells: int = 1000,
    nfeatures: Optional[int] = 50,
) -> Tuple[float, float]:
    sub = df[(df["metric"] == metric) & (df["ncells"] == ncells)]
    if nfeatures is not None:
        sub = sub[sub["nfeatures"] == nfeatures]
    if sub.empty:
        return np.nan, np.nan
    return float(sub["value"].mean()), float(sub["value"].std())


def paper_r2_all_genes(expdir: Path, setting: str, ncells: int = 1000, n_reps: int = 10) -> Tuple[float, float]:
    """Pearson r of per-gene means on all HVGs (paper Fig. 4f top)."""
    import sys

    cellot_gpu = expdir.parents[2]
    if str(cellot_gpu) not in sys.path:
        sys.path.insert(0, str(cellot_gpu))
    from cellot.utils.evaluate import load_conditions

    _, treated, imputed = load_conditions(expdir, "data_space", setting, embedding=None)
    tdf = treated if isinstance(treated, pd.DataFrame) else treated.to_df()
    idf = imputed if isinstance(imputed, pd.DataFrame) else imputed.to_df()
    vals = []
    for r in range(n_reps):
        trt = tdf.sample(ncells, random_state=r)
        imp = idf.sample(ncells, random_state=r)
        vals.append(trt.mean().corr(imp.mean()))
    return float(np.mean(vals)), float(np.std(vals))


def build_headline_table(results: Path, ncells: int = 1000) -> pd.DataFrame:
    rows = []
    for holdout, tag in TAGS.items():
        for model in MODEL_ORDER:
            for setting in ("ood", "iid"):
                df = load_evals_csv(results, tag, model, setting)
                if df.empty:
                    continue
                mmd_m, mmd_s = summarize_eval_reps(df, "mmd", ncells=ncells, nfeatures=50)
                r50_m, r50_s = summarize_eval_reps(df, "r2-means", ncells=ncells, nfeatures=50)
                expdir = model_dir(results, tag, model)
                if setting == "ood":
                    r_all_m, r_all_s = paper_r2_all_genes(expdir, setting, ncells=ncells)
                else:
                    r_all_m, r_all_s = paper_r2_all_genes(expdir, setting, ncells=ncells)
                ext = load_extended_metrics(results, tag, model)
                ext_row = {}
                if not ext.empty:
                    sub = ext[ext["ncells"] == ncells]
                    if len(sub):
                        ext_row = sub.iloc[0].to_dict()
                rows.append(
                    {
                        "holdout": holdout,
                        "model": MODEL_LABEL.get(model, model),
                        "setting": setting,
                        "r_mean_all_genes": r_all_m,
                        "r_mean_all_genes_sd": r_all_s,
                        "r_mean_50_markers": r50_m,
                        "r_mean_50_markers_sd": r50_s,
                        "mmd_50_markers": mmd_m,
                        "mmd_50_markers_sd": mmd_s,
                        "frac_gap_closed": ext_row.get("frac_gap_closed"),
                        "mmd_floor": ext_row.get("mmd_floor"),
                        "mmd_ceiling": ext_row.get("mmd_ceiling"),
                    }
                )
    return pd.DataFrame(rows)


def ensure_plot_symlinks(tag_dir: Path) -> None:
    """Layout expected by scripts/plot.py: model-cellot, model-scgen."""
    mapping = {
        "model-cellot": "impact_cellot",
        "model-scgen": "scgen",
    }
    for link_name, target in mapping.items():
        link = tag_dir / link_name
        dest = tag_dir / target
        if not dest.exists():
            continue
        if link.exists() or link.is_symlink():
            continue
        link.symlink_to(target, target_is_directory=True)


def load_dfs_for_marginals(
    tag_dir: Path,
    model_key: str,
    setting: str,
    n_markers: int = 50,
) -> Dict[str, pd.DataFrame]:
    """Mirror scripts/plot.py load_single_dfs via model-* subdirs."""
    from scripts.plot import load_single_dfs

    ensure_plot_symlinks(tag_dir)
    plot_model = "cellot" if model_key == "impact_cellot" else model_key
    expdir = tag_dir / f"model-{plot_model}"
    control, treated, imputed = load_single_dfs(
        expdir, setting=setting, where="data_space", n_markers=n_markers
    )
    return {
        "control": control,
        "treated": treated,
        plot_model: imputed,
    }


def mean_expression_panel(
    tag_dir: Path,
    genes: List[str],
    setting: str,
    n_markers: int = 50,
) -> pd.DataFrame:
    """Fig. 4e style: mean log-expression per gene for control/treated/model."""
    rows = []
    for model_key in MODEL_ORDER:
        dfs = load_dfs_for_marginals(tag_dir, model_key, setting, n_markers=n_markers)
        plot_key = "cellot" if model_key == "impact_cellot" else model_key
        for layer, df in [("control", dfs["control"]), ("treated", dfs["treated"]), (plot_key, dfs[plot_key])]:
            means = df.mean()
            for g in genes:
                if g not in means.index:
                    continue
                rows.append(
                    {
                        "gene": g,
                        "layer": layer,
                        "model": MODEL_LABEL.get(model_key, model_key),
                        "mean_expr": float(means[g]),
                    }
                )
    return pd.DataFrame(rows)

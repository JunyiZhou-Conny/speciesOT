"""Parsers for config.yaml, cache/status, and evals_*/evals.csv."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import yaml


# Upstream evaluate.py mislabels Pearson r as r2-*. Square these to get true R².
# See docs/conceptual_framework.md §5.5.
_R2_METRIC_NAMES: set[str] = {"r2-means", "r2-stds", "r2-pairwise_feat_corrs"}


def read_config(config_path: Path) -> dict[str, Any]:
    """Parse a model's config.yaml. Returns {} if missing or unparseable."""
    if not config_path.exists():
        return {}
    try:
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    except yaml.YAMLError:
        return {}


def read_status(model_dir: Path) -> str:
    """Read cache/status. One of {done, running, aborted, never_started, unknown}."""
    status_file = model_dir / "cache" / "status"
    if status_file.exists():
        try:
            txt = status_file.read_text().strip()
            return txt if txt else "unknown"
        except OSError:
            return "unknown"
    return "never_started"


def read_evals_csv(csv_path: Path) -> Optional[pd.DataFrame]:
    """Read an evals.csv and square the Pearson-r rows mislabeled as r2-*.

    Returns None if missing or empty. Columns are
    (ncells, nfeatures, metric, value) with `value` squared for r2-* rows.
    """
    if not csv_path.exists() or csv_path.stat().st_size < 50:
        return None
    try:
        df = pd.read_csv(csv_path)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        return None

    if "metric" not in df.columns or "value" not in df.columns:
        return df  # unexpected schema; pass through unchanged

    mask = df["metric"].isin(_R2_METRIC_NAMES)
    df.loc[mask, "value"] = df.loc[mask, "value"] ** 2
    return df


def parse_evals_subdir_name(name: str) -> tuple[Optional[str], Optional[str]]:
    """Parse 'evals_ood_data_space' → (space='data_space', setting='ood').

    Best effort. Returns (None, None) for unrecognized formats.
    """
    if not name.startswith("evals_"):
        return None, None
    body = name[len("evals_"):]
    # Expected pattern: <setting>_<space> where space contains an underscore.
    if body.startswith("ood_"):
        setting = "ood"
        space_part = body[len("ood_"):]
    elif body.startswith("iid_"):
        setting = "iid"
        space_part = body[len("iid_"):]
    else:
        return None, None
    space = space_part if space_part in {"data_space", "latent_space"} else None
    return space, setting


def headline_metrics(
    df: Optional[pd.DataFrame],
) -> tuple[Optional[float], Optional[float], list[int]]:
    """Extract (mean R²-of-means, mean MMD, n_cells values present) from evals.csv.

    Headline = at the largest n_cells × nfeatures='all', averaged across reps.
    """
    if df is None or df.empty:
        return None, None, []

    n_cells_values = sorted(
        {int(x) for x in df["ncells"].unique() if str(x).isdigit()}
    )
    if not n_cells_values:
        return None, None, []

    largest_n = max(n_cells_values)
    sub = df[(df["ncells"] == largest_n) & (df["nfeatures"] == "all")]

    def mean_metric(name: str) -> Optional[float]:
        m = sub[sub["metric"] == name]["value"]
        return float(m.mean()) if not m.empty else None

    return mean_metric("r2-means"), mean_metric("mmd"), n_cells_values


def read_extended_metrics(
    eval_dir: Path,
) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """Read the optional `extended_metrics.csv` sidecar (written by
    scripts/extended_metrics.py / `./hub metrics`).

    Returns (mmd_floor, mmd_ceiling, frac_gap_closed, mean_js) at the largest
    ncells, or all-None if the sidecar is absent/unreadable.
    """
    p = eval_dir / "extended_metrics.csv"
    if not p.exists():
        return None, None, None, None
    try:
        df = pd.read_csv(p)
    except (pd.errors.EmptyDataError, pd.errors.ParserError, OSError):
        return None, None, None, None
    if df.empty or "ncells" not in df.columns:
        return None, None, None, None
    row = df.loc[df["ncells"].idxmax()]

    def g(key: str) -> Optional[float]:
        return float(row[key]) if key in df.columns and pd.notna(row[key]) else None

    return g("mmd_floor"), g("mmd_ceiling"), g("frac_gap_closed"), g("mean_js")


def mtime(path: Path) -> Optional[datetime]:
    """File mtime as datetime, or None if path doesn't exist."""
    if not path.exists():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime)

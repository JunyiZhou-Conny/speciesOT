"""Shared data loading for atlas-paper-vae (legacy pack preferred under scgen_tf1)."""

from __future__ import annotations

from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd


def load_atlas(repo: Path, cfg: dict) -> ad.AnnData:
    """Load M2 v08 expression + obs.

    Prefer ``data_legacy_dir`` (npz1 / anndata 0.6 safe). Fall back to
    ``data_h5ad`` only if legacy pack is missing (modern analysis env).
    """
    legacy = cfg.get("data_legacy_dir")
    if legacy:
        d = (repo / legacy).resolve()
        npz = d / "X.npz"
        if npz.exists():
            X = np.load(npz)["X"].astype(np.float32)
            obs = pd.read_csv(d / "obs.csv", index_col=0)
            var = pd.read_csv(d / "var.csv", index_col=0)
            return ad.AnnData(X=X, obs=obs, var=var)

    h5ad = (repo / cfg["data_h5ad"]).resolve()
    return ad.read_h5ad(h5ad)

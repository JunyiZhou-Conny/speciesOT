#!/usr/bin/env python3
"""Dry-run: load v08 M2 h5ad, mirror toggle_ood, print split table. No training.

Usage (analysis or CellOT env — scanpy/sklearn only):
  conda run -n analysis python atlas-paper-vae/scripts/00_dry_run_split.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

REPO = Path(__file__).resolve().parents[2]
DEFAULT_H5AD = (
    REPO
    / "cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg"
    / "hvg_pearson_residuals_m2_v08.h5ad"
)
DEFAULT_OUT = (
    REPO
    / "atlas-paper-vae/results/atlas_paper_vae_m2_v08_ood"
    / "dry_run_split.txt"
)
HOLDOUT = ["CL:0000875", "CL:0000576"]


def toggle_ood_split(
    adata: ad.AnnData,
    *,
    holdout: list[str],
    key: str = "cell_type_ontology_term_id",
    test_size: float = 0.2,
    random_state: int = 0,
    stratify: str = "condition",
    mode: str = "ood",
) -> pd.Series:
    """Mirror cellot.data.cell.split_cell_data_toggle_ood (ood mode)."""
    split = pd.Series(None, index=adata.obs.index, dtype=object)
    trainobs, testobs = train_test_split(
        adata.obs.index, random_state=random_state, test_size=test_size
    )
    split.loc[trainobs] = "train"
    split.loc[testobs] = "test"

    ood = adata.obs_names[adata.obs[key].isin(holdout)]
    strat_vals = None
    if stratify in adata.obs.columns:
        strat_vals = adata.obs.loc[ood, stratify].astype(str)
        counts = strat_vals.value_counts()
        if strat_vals.nunique() < 2 or counts.min() < 2:
            strat_vals = None
    try:
        train_h, test_h = train_test_split(
            ood, random_state=random_state, test_size=0.5, stratify=strat_vals
        )
    except ValueError:
        train_h, test_h = train_test_split(
            ood, random_state=random_state, test_size=0.5
        )

    if mode == "ood":
        split.loc[train_h] = "ignore"
        split.loc[test_h] = "ood"
    else:
        raise ValueError(f"dry-run only implements mode=ood, got {mode}")
    return split


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--h5ad", type=Path, default=DEFAULT_H5AD)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    lines: list[str] = []

    def log(msg: str = "") -> None:
        print(msg, flush=True)
        lines.append(msg)

    h5ad = args.h5ad.resolve()
    if not h5ad.exists():
        raise FileNotFoundError(h5ad)

    adata = ad.read_h5ad(h5ad)
    X = adata.X
    if hasattr(X, "A"):
        X = X.A
    X = np.asarray(X)

    log("=== Plan C dry-run: atlas paper VAE / M2 v08 ===")
    log(f"h5ad: {h5ad}")
    log(f"shape: {adata.shape}")
    log(f"X dtype={X.dtype} min={float(X.min()):.4f} max={float(X.max()):.4f} "
        f"mean={float(X.mean()):.4f} sparsity={(X == 0).mean():.4f}")
    log(f"condition: {adata.obs['condition'].value_counts().to_dict()}")
    log(f"holdout types: {HOLDOUT}")
    for cl in HOLDOUT:
        m = adata.obs["cell_type_ontology_term_id"] == cl
        name = adata.obs.loc[m, "cell_type"].unique().tolist() if m.any() else []
        log(f"  {cl}: n={int(m.sum())} names={name} "
            f"by_cond={adata.obs.loc[m, 'condition'].value_counts().to_dict() if m.any() else {}}")

    split = toggle_ood_split(adata, holdout=HOLDOUT)
    obs = adata.obs.copy()
    obs["split"] = split
    obs["is_holdout"] = obs["cell_type_ontology_term_id"].isin(HOLDOUT)

    log("")
    log("=== split value counts ===")
    log(split.value_counts().to_string())
    log("")
    log("=== split x condition ===")
    log(pd.crosstab(obs["split"], obs["condition"]).to_string())
    log("")
    log("=== split x is_holdout ===")
    log(pd.crosstab(obs["split"], obs["is_holdout"]).to_string())
    log("")
    log("=== OOD cell_type x condition ===")
    ood = obs["split"] == "ood"
    log(pd.crosstab(obs.loc[ood, "cell_type"], obs.loc[ood, "condition"]).to_string())
    log("")
    train = obs["split"] == "train"
    log(f"VAE train mask (split==train): n={int(train.sum())}")
    log(f"  condition: {obs.loc[train, 'condition'].value_counts().to_dict()}")
    log(f"  holdout types in train? {bool(obs.loc[train, 'is_holdout'].any())}")
    log(f"Transport eval OOD: {obs.loc[ood, 'condition'].value_counts().to_dict()}")
    log("")
    log("Prediction rule (Phase 2): single_species_delta on OOD mouse → human")
    log("Fence: results only under atlas-paper-vae/results/atlas_paper_vae_*")
    log("=== dry-run OK ===")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n")
    print(f"\nWrote {args.out}", flush=True)


if __name__ == "__main__":
    main()

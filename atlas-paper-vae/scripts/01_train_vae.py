#!/usr/bin/env python3
"""Train Lotfollahi-like TF VAEArith on M2 v08 atlas (Plan C).

STUB / Phase-2 entrypoint. Does not run unless --go is passed.

Fence: writes ONLY under atlas-paper-vae/results/atlas_paper_vae_* .
Never touches cellot/.../hvg_*_v08_ood/scgen/ .

Env:
  conda activate scgen_tf1
  export PYTHONPATH=<repo>/scgen-cellot-ablation/scgen-reproducibility/code:$PYTHONPATH

Usage:
  # print plan only (default):
  python atlas-paper-vae/scripts/01_train_vae.py
  # full train (Phase 2):
  python atlas-paper-vae/scripts/01_train_vae.py --go
  # tiny smoke (≤1000 cells, 2 epochs) — NOT a result:
  python atlas-paper-vae/scripts/01_train_vae.py --go --smoke
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.model_selection import train_test_split

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from _data import load_atlas  # noqa: E402

DEFAULT_CFG = REPO / "atlas-paper-vae/configs/m2_v08.yaml"


def _dense(X):
    return X.A if hasattr(X, "A") else np.asarray(X)


def toggle_ood_split(adata, holdout, key, test_size, random_state, stratify, mode):
    split = pd.Series(None, index=adata.obs.index, dtype=object)
    trainobs, testobs = train_test_split(
        adata.obs.index, random_state=random_state, test_size=test_size
    )
    split.loc[trainobs] = "train"
    split.loc[testobs] = "test"
    ood = adata.obs_names[adata.obs[key].isin(holdout)]
    strat_vals = adata.obs.loc[ood, stratify].astype(str)
    train_h, test_h = train_test_split(
        ood, random_state=random_state, test_size=0.5, stratify=strat_vals
    )
    if mode != "ood":
        raise ValueError(mode)
    split.loc[train_h] = "ignore"
    split.loc[test_h] = "ood"
    return split


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CFG)
    parser.add_argument("--go", action="store_true", help="Actually train (Phase 2)")
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Overfit smoke: ≤1000 train cells, 2 epochs (not a result)",
    )
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    result_dir = (REPO / cfg["result_dir"]).resolve()
    # Hard fence: refuse hub scgen paths
    forbidden = "hvg_pearson_residuals_"
    if forbidden in str(result_dir) and "/scgen" in str(result_dir):
        raise SystemExit(f"FENCE: refusing result_dir={result_dir}")
    if "atlas_paper_vae" not in str(result_dir):
        raise SystemExit(
            f"FENCE: result_dir must contain atlas_paper_vae, got {result_dir}"
        )

    scgen_code = (REPO / cfg["eval"]["scgen_code_path"]).resolve()
    vae = cfg["vae"]
    ds = cfg["datasplit"]
    legacy = cfg.get("data_legacy_dir")

    print("=== 01_train_vae plan ===", flush=True)
    print(f"data:    legacy={legacy} | h5ad={cfg['data_h5ad']}", flush=True)
    print(f"out:     {result_dir}", flush=True)
    print(f"scgen:   {scgen_code}", flush=True)
    print(
        f"arch:    z={vae['z_dimension']} alpha={vae['alpha']} "
        f"dropout={vae['dropout_rate']} epochs={vae['n_epochs']} "
        f"batch={vae['batch_size']}",
        flush=True,
    )
    print(f"split:   toggle_ood mode={ds['mode']} seed={ds['random_state']}", flush=True)
    print(f"predict: {cfg['prediction']['rule']}", flush=True)
    if not args.go:
        print("\nDry plan only. Re-run with --go to train (Phase 2).", flush=True)
        return

    sys.path.insert(0, str(scgen_code))
    import scgen  # noqa: E402

    adata = load_atlas(REPO, cfg)
    print(f"loaded AnnData {adata.shape}", flush=True)
    split = toggle_ood_split(
        adata,
        holdout=cfg["holdout_cell_types"],
        key=cfg["cell_type_key"],
        test_size=ds["test_size"],
        random_state=ds["random_state"],
        stratify=ds["stratify"],
        mode=ds["mode"],
    )
    train = adata[split == "train"].copy()
    valid = adata[split == "test"].copy()

    n_epochs = int(vae["n_epochs"])
    if args.smoke:
        rng = np.random.default_rng(0)
        n = min(1000, train.n_obs)
        idx = rng.choice(train.n_obs, n, replace=False)
        train = train[idx].copy()
        valid = valid[: min(200, valid.n_obs)].copy()
        n_epochs = 2
        result_dir = result_dir / "smoke"
        print(f"[smoke] train_n={train.n_obs} epochs={n_epochs} → {result_dir}", flush=True)

    result_dir.mkdir(parents=True, exist_ok=True)
    model_path = result_dir / "model" / "scgen"
    model_path.parent.mkdir(parents=True, exist_ok=True)

    # Persist split for eval reproducibility
    split.to_frame("split").to_csv(result_dir / "split.csv")

    network = scgen.VAEArith(
        x_dimension=train.n_vars,
        z_dimension=int(vae["z_dimension"]),
        alpha=float(vae["alpha"]),
        dropout_rate=float(vae["dropout_rate"]),
        learning_rate=float(vae["learning_rate"]),
        model_path=str(model_path),
    )
    # Upstream API expects AnnData; ensure dense float32
    train.X = _dense(train.X).astype(np.float32)
    valid.X = _dense(valid.X).astype(np.float32)
    network.train(
        train,
        use_validation=True,
        valid_data=valid,
        n_epochs=n_epochs,
        batch_size=int(vae["batch_size"]),
    )
    network.sess.close()
    print(f"Saved checkpoint prefix: {model_path}", flush=True)
    if args.smoke:
        print("[smoke] NOT a scoreboard result.", flush=True)


if __name__ == "__main__":
    main()

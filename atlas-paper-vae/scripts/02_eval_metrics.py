#!/usr/bin/env python3
"""Eval paper VAE on M2 v08 OOD → Stage-0-like metrics.json (Plan C).

STUB / Phase-2 entrypoint. Requires a trained checkpoint from 01_train_vae.py.

Writes ONLY:
  atlas-paper-vae/results/atlas_paper_vae_m2_v08_ood/metrics.json

Mirrors scgen-cellot-ablation/scripts/04_stage0_fig5_eval.py:
  - honest_metrics.compute_honest_metrics(...)
  - deterministic posterior mean (network.mu) for decoded-frame refs
  - primary prediction: single_species_delta (not Fig.5 two-path)

Usage:
  conda activate scgen_tf1
  export PYTHONPATH=<repo>/scgen-cellot-ablation/scgen-reproducibility/code:$PYTHONPATH
  python atlas-paper-vae/scripts/02_eval_metrics.py          # plan only
  python atlas-paper-vae/scripts/02_eval_metrics.py --go     # run eval
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import yaml
from scipy import stats
from sklearn.model_selection import train_test_split

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from _data import load_atlas  # noqa: E402

DEFAULT_CFG = REPO / "atlas-paper-vae/configs/m2_v08.yaml"


def _dense(X):
    return X.A if hasattr(X, "A") else np.asarray(X)


def _pergene_r2(X: np.ndarray, Xhat: np.ndarray) -> float:
    xc = X - X.mean(0)
    yc = Xhat - Xhat.mean(0)
    numerator = (xc * yc).sum(0)
    denominator = np.sqrt((xc**2).sum(0) * (yc**2).sum(0))
    valid = denominator > 1e-12
    return float(np.mean((numerator[valid] / denominator[valid]) ** 2))


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
    parser.add_argument("--go", action="store_true")
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.read_text())
    result_dir = (REPO / cfg["result_dir"]).resolve()
    if "atlas_paper_vae" not in str(result_dir):
        raise SystemExit(f"FENCE: bad result_dir {result_dir}")
    model_path = result_dir / "model" / "scgen"
    out_json = result_dir / "metrics.json"
    scgen_code = (REPO / cfg["eval"]["scgen_code_path"]).resolve()
    honest_dir = (REPO / cfg["eval"]["honest_metrics_path"]).resolve().parent
    vae = cfg["vae"]
    ds = cfg["datasplit"]
    cond_col = cfg["condition_column"]
    source, target = cfg["source"], cfg["target"]
    seed = int(cfg["eval"]["seed"])

    print("=== 02_eval_metrics plan ===", flush=True)
    print(f"model:   {model_path}", flush=True)
    print(f"out:     {out_json}", flush=True)
    print(f"rule:    {cfg['prediction']['rule']}", flush=True)
    print(
        f"ncells:  {cfg['eval']['ncells']} headline={cfg['eval']['headline_ncells']}",
        flush=True,
    )
    if not args.go:
        print("\nDry plan only. Re-run with --go after training.", flush=True)
        return

    if not model_path.with_suffix(".index").exists():
        raise FileNotFoundError(
            f"Missing checkpoint {model_path}.index — run 01_train_vae.py --go first"
        )

    sys.path.insert(0, str(scgen_code))
    sys.path.insert(0, str(honest_dir))
    import scgen  # noqa: E402
    import honest_metrics  # noqa: E402

    adata = load_atlas(REPO, cfg)
    print(f"loaded AnnData {adata.shape}", flush=True)
    split_csv = result_dir / "split.csv"
    if split_csv.exists():
        split = pd.read_csv(split_csv, index_col=0)["split"]
        split = split.reindex(adata.obs_names)
    else:
        split = toggle_ood_split(
            adata,
            holdout=cfg["holdout_cell_types"],
            key=cfg["cell_type_key"],
            test_size=ds["test_size"],
            random_state=ds["random_state"],
            stratify=ds["stratify"],
            mode=ds["mode"],
        )

    train = adata[split == "train"]
    ood = adata[split == "ood"]
    mouse_tr = train[train.obs[cond_col] == source]
    human_tr = train[train.obs[cond_col] == target]
    mouse_ood = ood[ood.obs[cond_col] == source]
    human_ood = ood[ood.obs[cond_col] == target]

    network = scgen.VAEArith(
        x_dimension=adata.n_vars,
        z_dimension=int(vae["z_dimension"]),
        alpha=float(vae["alpha"]),
        dropout_rate=float(vae["dropout_rate"]),
        learning_rate=float(vae["learning_rate"]),
        model_path=str(model_path),
    )
    network.restore_model()

    # Deterministic posterior mean (Stage 0); to_latent samples and is noisier.
    def encode_mean(X):
        X = np.asarray(X, dtype=np.float32)
        return network.sess.run(
            network.mu,
            feed_dict={network.x: X, network.is_training: False},
        )

    def decode(Z):
        return network.reconstruct(np.asarray(Z, dtype=np.float32), use_data=True)

    src_raw = _dense(mouse_ood.X).astype(np.float64)
    tgt_raw = _dense(human_ood.X).astype(np.float64)
    train_X = _dense(train.X).astype(np.float64)

    z_m = encode_mean(mouse_tr.X)
    z_h = encode_mean(human_tr.X)
    delta = z_h.mean(0) - z_m.mean(0)
    z_src = encode_mean(mouse_ood.X)
    pred_latent = z_src + delta
    pred = np.asarray(decode(pred_latent), dtype=np.float64)

    honest = honest_metrics.compute_honest_metrics(
        pred,
        tgt_raw,
        src_raw,
        encode=encode_mean,
        decode=decode,
        imputed_latent=pred_latent,
        random_state=seed,
    )
    pearson = stats.pearsonr(pred.mean(0), tgt_raw.mean(0))
    r_all = float(pearson.statistic if hasattr(pearson, "statistic") else pearson[0])
    honest.update(
        {
            "prediction": "single_species_delta",
            "r_all": r_all,
            "r2_all": r_all**2,
            "n_pred_cells": int(len(pred)),
            "n_true_cells": int(len(tgt_raw)),
            "n_genes": int(adata.n_vars),
            "headline_ncells": int(cfg["eval"]["headline_ncells"]),
            "honest_ncells": list(cfg["eval"]["ncells"]),
        }
    )

    train_hat = decode(encode_mean(train_X))
    target_hat = decode(encode_mean(tgt_raw))
    target_recon_mmd = honest_metrics.mmd_two_sample_mean(
        target_hat,
        tgt_raw,
        ncells_list=tuple(cfg["eval"]["ncells"]),
        random_state=seed,
    )
    headline = int(cfg["eval"]["headline_ncells"])
    reconstruction = {
        "recon_train_mse": float(np.mean((train_X - train_hat) ** 2)),
        "recon_train_r2_pergene": _pergene_r2(train_X, train_hat),
        "recon_target_mse": float(np.mean((tgt_raw - target_hat) ** 2)),
        "recon_target_r2_pergene": _pergene_r2(tgt_raw, target_hat),
        "recon_target_mmd_self": float(target_recon_mmd.get(headline, np.nan)),
    }

    payload = {
        "model": "TensorFlow scgen.VAEArith",
        "architecture": (
            f"{adata.n_vars}-800-800-{vae['z_dimension']}-800-800-{adata.n_vars}"
        ),
        "experiment_tag": cfg["experiment_tag"],
        "training": {
            "held_out": cfg["holdout_cell_types"],
            "alpha": vae["alpha"],
            "dropout": vae["dropout_rate"],
            "learning_rate": vae["learning_rate"],
            "epochs": vae["n_epochs"],
            "split": "toggle_ood ood; train on split==train",
        },
        "primary_prediction": "single_species_delta",
        "reconstruction": reconstruction,
        "predictions": {"single_species_delta": honest},
        "evaluation_note": (
            "Single species δ = mean(z|human,train)−mean(z|mouse,train); "
            "decoded-frame refs use posterior mean. Identity baseline is in "
            "honest_metrics (r2_identity). Not a Fig.5 two-path claim."
        ),
        "fence": "results under atlas-paper-vae only; hub v08 scgen untouched",
    }

    result_dir.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2) + "\n")
    ad.AnnData(
        pred.astype(np.float32), obs=mouse_ood.obs.copy(), var=adata.var.copy()
    ).write_h5ad(result_dir / "pred_single_species_delta.h5ad")
    network.sess.close()
    print(f"Wrote {out_json}", flush=True)
    print(
        "Phase 2 next: metric-atlas-canvas → atlas-paper-vae-m2-v08-metrics",
        flush=True,
    )


if __name__ == "__main__":
    main()

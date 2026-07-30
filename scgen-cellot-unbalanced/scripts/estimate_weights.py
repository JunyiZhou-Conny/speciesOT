#!/usr/bin/env python3
"""Estimate Option-A mass weights on a frozen AE latent (LPS rat OOD default).

Writes ``results/<run>/weights_<method>_alpha<α>.npz`` consumed by train_option_a.py.

Usage (from repo root or this directory; CellOT env)::

  cd scgen-cellot-unbalanced
  PYTHONPATH=../cellot/cellot_gpu:$PWD python scripts/estimate_weights.py \\
      --config configs/option_a/lps_rat_balanced.yaml \\
      --method louvain_match --alpha 1.0
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from uot.reweight import estimate_weights  # noqa: E402


def _repo_cellot_gpu() -> Path:
    return ROOT.parent / "cellot" / "cellot_gpu"


def _load_yaml(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def _resolve_path(p: str, base: Path) -> Path:
    path = Path(p)
    if path.is_absolute():
        return path
    # configs use paths relative to cellot_gpu
    cand = base / path
    if cand.exists():
        return cand
    return (ROOT / path).resolve()


def encode_latent(adata, ae_dir: Path, device: str = "cpu"):
    """Encode cells with the frozen scGen AE (byte-identical to IMPACT)."""
    sys.path.insert(0, str(_repo_cellot_gpu()))
    from cellot.models.ae import load_autoencoder_model
    from cellot.utils import load_config

    cfg = load_config(ae_dir / "config.yaml")
    model_kwargs = {"input_dim": adata.n_vars}
    model, _ = load_autoencoder_model(
        cfg, restore=ae_dir / "cache" / "model.pt", device=torch.device(device), **model_kwargs
    )
    X = adata.X if not hasattr(adata.X, "todense") else np.asarray(adata.X.todense())
    if hasattr(X, "A"):
        X = X.A
    X = np.asarray(X, dtype=np.float32)
    with torch.no_grad():
        z = model.eval().encode(torch.from_numpy(X).to(device)).cpu().numpy()
    return z


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument(
        "--method",
        choices=["uniform", "louvain_match", "density_ratio"],
        default="louvain_match",
    )
    ap.add_argument("--alpha", type=float, default=1.0, help="0=uniform parity, 1=full reweight")
    ap.add_argument("--label-key", default="louvain")
    ap.add_argument("--outdir", type=Path, default=None)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--knn-k", type=int, default=20)
    args = ap.parse_args()

    cfg = _load_yaml(args.config)
    cellot_root = _repo_cellot_gpu()
    data_path = _resolve_path(cfg["data"]["path"], cellot_root)
    ae_path = _resolve_path(cfg["data"]["ae_emb"]["path"], cellot_root)

    import anndata as ad

    print(f"[estimate_weights] loading {data_path}")
    adata = ad.read_h5ad(data_path)
    cond_key = cfg["data"].get("condition", "condition")
    source = cfg["data"]["source"]
    target = cfg["data"]["target"]

    # Train-side cells only for weight estimation (exclude OOD holdout species).
    # Mirror toggle_ood: holdout species is rat → train on non-rat.
    holdout = None
    ds = cfg.get("datasplit", {})
    if ds.get("name") == "toggle_ood" and ds.get("key") == "species":
        holdout = ds.get("holdout")
        if isinstance(holdout, list):
            holdout = holdout[0]
    if holdout is not None and "species" in adata.obs:
        train_mask = adata.obs["species"].astype(str) != str(holdout)
        print(f"[estimate_weights] excluding holdout species={holdout}: keep {train_mask.sum()}/{len(adata)}")
        adata = adata[train_mask].copy()

    source_mask = (adata.obs[cond_key].astype(str) == str(source)).values
    target_mask = (adata.obs[cond_key].astype(str) == str(target)).values
    print(f"[estimate_weights] source={source_mask.sum()} target={target_mask.sum()}")

    labels = None
    latent = None
    if args.method == "louvain_match":
        if args.label_key not in adata.obs:
            raise SystemExit(f"label key {args.label_key!r} missing from obs")
        labels = adata.obs[args.label_key].astype(str).values
    if args.method == "density_ratio":
        print(f"[estimate_weights] encoding with frozen AE at {ae_path}")
        latent = encode_latent(adata, ae_path, device=args.device)

    art = estimate_weights(
        method=args.method,
        alpha=args.alpha,
        source_mask=source_mask,
        target_mask=target_mask,
        obs_names=adata.obs_names.values,
        labels=labels,
        latent=latent,
        knn_k=args.knn_k,
    )

    outdir = args.outdir or (ROOT / "results" / "lps_rat" / "weights")
    outdir = Path(outdir)
    out_path = outdir / f"weights_{args.method}_alpha{args.alpha:g}.npz"
    art.save(out_path)
    print(f"[estimate_weights] wrote {out_path}")
    print(f"  method={art.method} alpha={art.alpha} meta={art.meta}")


if __name__ == "__main__":
    main()

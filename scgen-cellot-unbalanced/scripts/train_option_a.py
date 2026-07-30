#!/usr/bin/env python3
"""Train balanced CellOT with Option-A reweighted sampling (same ICNN dual).

Does **not** modify production ``cellot_gpu``. Imports CellOT read-only via
PYTHONPATH and rebuilds train loaders with ``WeightedRandomSampler``.

Parity gate: ``--weights`` omitted or uniform/alpha=0 must match the frozen
balanced IMPACT decoded number within tolerance (see DELIVERABLE).

Usage::

  cd scgen-cellot-unbalanced
  PYTHONPATH=../cellot/cellot_gpu:$PWD python scripts/train_option_a.py \\
      --config configs/option_a/lps_rat_balanced.yaml \\
      --outdir results/lps_rat/balanced_parity \\
      --weights results/lps_rat/weights/weights_uniform_alpha0.npz
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.utils.data import DataLoader, WeightedRandomSampler

ROOT = Path(__file__).resolve().parents[1]
CELLOT_GPU = ROOT.parent / "cellot" / "cellot_gpu"


def _ensure_paths():
    for p in (str(CELLOT_GPU), str(ROOT)):
        if p not in sys.path:
            sys.path.insert(0, p)


def _load_yaml(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def _rewrite_config_paths(cfg: dict, cellot_root: Path) -> dict:
    """Make data/ae paths absolute so training works from any cwd."""
    cfg = dict(cfg)
    data = dict(cfg["data"])
    path = Path(data["path"])
    if not path.is_absolute():
        data["path"] = str((cellot_root / path).resolve())
    if "ae_emb" in data:
        ae = dict(data["ae_emb"])
        ap = Path(ae["path"])
        if not ap.is_absolute():
            ae["path"] = str((cellot_root / ap).resolve())
        data["ae_emb"] = ae
    cfg["data"] = data
    return cfg


def _weights_for_dataset(dataset, weight_by_name: dict, side: str) -> torch.Tensor:
    """Map AnnDataDataset row order → sampling weights via obs_names."""
    # AnnDataDataset stores adata; cellot uses .adata or index into X
    adata = getattr(dataset, "adata", None)
    if adata is None:
        # fallback: AnnDataDataset in this codebase keeps data on .data
        adata = getattr(dataset, "data", None)
    if adata is None and hasattr(dataset, "dataset"):
        adata = dataset.dataset

    # cellot AnnDataDataset: look at source
    from cellot.data.cell import AnnDataDataset

    if isinstance(dataset, AnnDataDataset):
        names = list(dataset.adata.obs_names.astype(str))
    else:
        raise TypeError(f"unsupported dataset type {type(dataset)}")

    w = np.array([float(weight_by_name.get(n, np.nan)) for n in names], dtype=np.float64)
    missing = np.isnan(w)
    if missing.any():
        # cells not in the artifact (e.g. holdout) → uniform among missing
        fill = 1.0 / max(len(names), 1)
        w[missing] = fill
    if not np.any(w > 0):
        raise RuntimeError(f"all-zero weights for side={side} (n={len(names)})")
    # WeightedRandomSampler wants relative weights, not necessarily normalized
    return torch.as_tensor(w, dtype=torch.double)


def _rebuild_loader_with_weights(loader_tree, art, batch_size: int, drop_last: bool = True):
    """Replace train.source / train.target DataLoaders with weighted samplers."""
    from cellot.utils.helpers import flat_dict, nest_dict

    source_map = {
        n: float(w)
        for n, w, m in zip(art.obs_names, art.source_weights, art.source_mask)
        if m
    }
    target_map = {
        n: float(w)
        for n, w, m in zip(art.obs_names, art.target_weights, art.target_mask)
        if m
    }

    flat = flat_dict(loader_tree)
    new_flat = {}
    for key, dl in flat.items():
        # key like "train.source" or "test.target"
        parts = key.split(".")
        is_train = parts[0] == "train"
        side = parts[1] if len(parts) > 1 else None
        if is_train and side in ("source", "target"):
            ds = dl.dataset
            wmap = source_map if side == "source" else target_map
            weights = _weights_for_dataset(ds, wmap, side)
            sampler = WeightedRandomSampler(
                weights, num_samples=len(ds), replacement=True
            )
            new_flat[key] = DataLoader(
                ds,
                batch_size=min(batch_size, len(ds)),
                sampler=sampler,
                drop_last=drop_last and len(ds) >= batch_size,
            )
        else:
            # keep test loaders uniform (eval must stay apples-to-apples)
            new_flat[key] = dl
    return nest_dict(new_flat, as_dot_dict=True)


def main():
    _ensure_paths()
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--weights", type=Path, default=None, help="WeightArtifact .npz")
    ap.add_argument("--n-iters", type=int, default=None, help="override training.n_iters")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    from cellot.utils import load_config
    from cellot.utils.loaders import load, resolve_device
    from cellot.models.cellot import compute_loss_f, compute_loss_g, compute_w2_distance
    from cellot.train.summary import Logger
    from cellot.data.utils import cast_loader_to_iterator
    from cellot import losses
    from tqdm import trange

    from uot.reweight import WeightArtifact

    # Write a resolved yaml into outdir so CellOT load_config works
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    cachedir = outdir / "cache"
    cachedir.mkdir(exist_ok=True)

    raw = _load_yaml(args.config)
    raw = _rewrite_config_paths(raw, CELLOT_GPU)
    if args.n_iters is not None:
        raw.setdefault("training", {})["n_iters"] = int(args.n_iters)
    cfg_path = outdir / "config.yaml"
    with open(cfg_path, "w") as fh:
        yaml.safe_dump(raw, fh, default_flow_style=False)

    config = load_config(cfg_path)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)

    device = resolve_device(config)
    (f, g), opts, loader = load(config, restore=cachedir / "last.pt")

    if args.weights is not None:
        art = WeightArtifact.load(args.weights)
        # α=0 / uniform → keep stock CellOT DataLoaders (shuffle, no replacement)
        # so the balanced end is byte-identical in sampling to Bunne/IMPACT.
        use_reweight = not (
            art.method == "uniform" or float(art.alpha) <= 0.0
        )
        print(
            f"[train_option_a] method={art.method} alpha={art.alpha} "
            f"reweight_sampler={use_reweight}"
        )
        if use_reweight:
            bs = int(config.dataloader.get("batch_size", 256))
            loader = _rebuild_loader_with_weights(loader, art, batch_size=bs)
    else:
        print("[train_option_a] no --weights → stock balanced CellOT (parity)")

    iterator = cast_loader_to_iterator(loader, cycle_all=True)
    logger = Logger(cachedir / "scalars")

    def state_dict(f, g, opts, **kwargs):
        state = {
            "g_state": g.state_dict(),
            "f_state": f.state_dict(),
            "opt_g_state": opts.g.state_dict(),
            "opt_f_state": opts.f.state_dict(),
        }
        state.update(kwargs)
        return state

    def load_item(path, key, default):
        path = Path(path)
        if not path.exists():
            return default
        ckpt = torch.load(path, map_location=device)
        return ckpt.get(key, default)

    n_iters = int(config.training.n_iters)
    step = int(load_item(cachedir / "last.pt", "step", 0))
    minmmd = float(load_item(cachedir / "model.pt", "minmmd", np.inf))

    ticker = trange(step, n_iters, initial=step, total=n_iters)
    for step in ticker:
        target = next(iterator.train.target).to(device)
        for _ in range(int(config.training.n_inner_iters)):
            source = next(iterator.train.source).to(device).requires_grad_(True)
            opts.g.zero_grad()
            gl = compute_loss_g(f, g, source).mean()
            if not g.softplus_W_kernels and g.fnorm_penalty > 0:
                gl = gl + g.penalize_w()
            gl.backward()
            opts.g.step()

        source = next(iterator.train.source).to(device).requires_grad_(True)
        opts.f.zero_grad()
        fl = compute_loss_f(f, g, source, target).mean()
        fl.backward()
        opts.f.step()
        f.clamp_w()

        if step % int(config.training.logs_freq) == 0:
            logger.log("train", gloss=float(gl.item()), floss=float(fl.item()), step=step)

        if step % int(config.training.eval_freq) == 0:
            t = next(iterator.test.target).to(device)
            s = next(iterator.test.source).to(device).requires_grad_(True)
            transport = g.transport(s).detach()
            with torch.no_grad():
                mmd = losses.compute_scalar_mmd(
                    t.cpu().numpy(), transport.cpu().numpy()
                )
            logger.log("eval", mmd=mmd, step=step)
            if mmd < minmmd:
                minmmd = mmd
                torch.save(
                    state_dict(f, g, opts, step=step, minmmd=minmmd),
                    cachedir / "model.pt",
                )

        if step % int(config.training.cache_freq) == 0:
            torch.save(state_dict(f, g, opts, step=step), cachedir / "last.pt")
            logger.flush()

    torch.save(state_dict(f, g, opts, step=step), cachedir / "last.pt")
    if not (cachedir / "model.pt").exists():
        torch.save(state_dict(f, g, opts, step=step, minmmd=minmmd), cachedir / "model.pt")
    logger.flush()
    print(f"[train_option_a] done → {outdir}")


if __name__ == "__main__":
    main()

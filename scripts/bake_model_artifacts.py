#!/usr/bin/env python
"""Bake prediction-time artifacts beside a trained model set, so that predicting
on new cells no longer needs the training atlas .h5ad.

Two things in `scripts/predict_new_input.sh` used to force the 35 MB-per-flavor
training dataset into a handover:

  1. the 1,000 gene names -- read out of the training .h5ad purely to know the
     gene axis;
  2. the scGen latent shift -- `cache/model.pt` stores only
     model_state/optim_state/step/eval_loss, so the shift had to be recovered by
     re-encoding all ~90k training cells at prediction time.

This script writes both as sidecars. It never touches `cache/model.pt`.

  <results>/<tag>/genes.txt                 one gene id per line, in training
                                            var_names order
  <results>/<tag>/scgen/cache/scgen_shift.pt  torch dict with `code_means` plus
                                            provenance

Provenance is the point of the second file: a latent shift computed against a
different gene axis is silently wrong in exactly the way phase 0 of
predict_new_input.sh exists to prevent, so the sidecar records the gene-axis
sha256, the dataset it was computed from, and the checkpoint hash. The
consumer re-checks the axis hash before trusting the shift.

Usage (run under the `CellOT` env, or `CellOT_v3` which is also validated):

    python scripts/bake_model_artifacts.py --model-set atlas_full_v07
    python scripts/bake_model_artifacts.py cellot/cellot_gpu/results/atlas_full_seurat_v3
    python scripts/bake_model_artifacts.py --model-set atlas_full_v07 --verify

`--model-set` mirrors the table in predict_new_input.sh; a results directory can
also be named directly, which is how a model set that is not in the table yet
gets baked.
"""

import argparse
import getpass
import hashlib
import os
import platform
import socket
import sys
import time
from pathlib import Path

import h5py

# Same model-set table as scripts/predict_new_input.sh. {flavor} is substituted.
MODEL_SETS = {
    "atlas_full_v07": {
        "flavors": ["seurat_v3", "pearson_residuals"],
        "results_template": "atlas_full_{flavor}",
    },
    "uncapped_v08": {
        "flavors": ["pearson_residuals", "mixhvg"],
        "results_template": "hvg_{flavor}_uncapped_v08",
    },
    "uncapped_v08_iid": {
        "flavors": ["pearson_residuals", "mixhvg"],
        "results_template": "hvg_{flavor}_a_uncapped_v08_iid",
    },
}

SCHEMA_VERSION = 1


def gene_axis_sha256(genes):
    """Hash of a gene axis. Identical to sha256 of the genes.txt this writes."""
    h = hashlib.sha256()
    for g in genes:
        h.update(str(g).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def file_sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def h5ad_var_names(path):
    """Gene axis of an .h5ad read with h5py, so it is anndata-version agnostic
    and does not load X. Same reader as phase 0 of predict_new_input.sh."""
    with h5py.File(path, "r") as f:
        g = f["var"]
        key = g.attrs.get("_index", "index")
        key = key.decode() if isinstance(key, bytes) else key
        return [v.decode() if isinstance(v, bytes) else str(v) for v in g[key][:]]


def write_atomic(path, write_fn):
    """Write via a temp file in the same directory, then rename, so a reader
    never sees a half-written sidecar."""
    path = Path(path)
    tmp = path.with_name(path.name + f".tmp.{os.getpid()}")
    try:
        write_fn(tmp)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def resolve_train_path(config, cellot_dir):
    """config.data.path is relative to cellot/cellot_gpu (where training ran)."""
    p = str(config.data.path)
    return p if os.path.isabs(p) else os.path.join(cellot_dir, p)


def compute_code_means(config, results_dir, cellot_dir, input_dim, train_path):
    """Recover model.code_means exactly the way predict_new_input.sh phase 3
    does today: same loader, same eval-mode model, same compute_scgen_shift.

    model.eval() before encoding is load-bearing -- these autoencoders train
    with dropout 0.1, so encoding in train mode would give a random shift.
    """
    from cellot.utils import load_config  # noqa: F401  (kept for symmetry)
    from cellot.utils.loaders import load_data, resolve_device
    from cellot.models import load_autoencoder_model
    from cellot.models.ae import compute_scgen_shift

    config.data.path = train_path
    device = resolve_device(config)
    model, _ = load_autoencoder_model(
        config,
        restore=f"{results_dir}/cache/model.pt",
        device=device,
        input_dim=input_dim,
    )
    model.eval()

    from_checkpoint = hasattr(model, "code_means")
    if not from_checkpoint:
        loader = load_data(config, return_as="loader")
        labels = loader.train.dataset.adata.obs[config.data.condition]
        compute_scgen_shift(model, loader.train.dataset, labels=labels, device=device)
        n_cells = len(loader.train.dataset)
    else:
        n_cells = None

    code_means = {str(k): v.detach().cpu().clone() for k, v in model.code_means.items()}
    return code_means, device, n_cells, from_checkpoint


def bake_one(tag_dir, cellot_dir, force=False, verify=False):
    from cellot.utils import load_config

    tag_dir = Path(tag_dir).resolve()
    tag = tag_dir.name
    scgen_dir = tag_dir / "scgen"
    cfg_path = scgen_dir / "config.yaml"
    ckpt_path = scgen_dir / "cache" / "model.pt"

    print(f"=== {tag}")
    for p in (cfg_path, ckpt_path):
        if not p.exists():
            print(f"  ERROR missing {p} -- not a trained scgen model set. Skipping.")
            return False

    config = load_config(str(cfg_path))
    train_path = resolve_train_path(config, cellot_dir)
    if not os.path.exists(train_path):
        print(f"  ERROR training dataset named in {cfg_path} does not exist:")
        print(f"        {train_path}")
        print("        The dataset is needed ONCE, to bake; after that it is not.")
        return False

    genes = h5ad_var_names(train_path)
    axis_sha = gene_axis_sha256(genes)
    print(f"  dataset : {train_path}")
    print(f"  axis    : {len(genes)} genes, sha256 {axis_sha[:16]}...")

    genes_txt = tag_dir / "genes.txt"
    shift_pt = scgen_dir / "cache" / "scgen_shift.pt"

    if verify:
        return verify_one(genes_txt, shift_pt, genes, axis_sha, config,
                          str(scgen_dir), cellot_dir, train_path)

    if not force and genes_txt.exists() and shift_pt.exists():
        print(f"  SKIP    both sidecars already exist (use --force to rewrite)")
        return True

    # --- genes.txt --------------------------------------------------------
    body = "".join(f"{g}\n" for g in genes)
    write_atomic(genes_txt, lambda p: p.write_text(body))
    assert file_sha256(genes_txt) == axis_sha, "genes.txt hash != gene axis hash"
    print(f"  wrote   {genes_txt} ({len(genes)} lines)")

    # --- scgen_shift.pt ---------------------------------------------------
    import torch
    import anndata

    t0 = time.time()
    code_means, device, n_cells, from_ckpt = compute_code_means(
        config, str(scgen_dir), cellot_dir, len(genes), train_path
    )
    elapsed = time.time() - t0

    ckpt_meta = torch.load(str(ckpt_path), map_location="cpu")
    latent_dim = int(config.model.get("latent_dim", 50))
    for key, vec in code_means.items():
        if tuple(vec.shape) != (latent_dim,):
            print(f"  ERROR code_means[{key}] has shape {tuple(vec.shape)}, "
                  f"expected ({latent_dim},)")
            return False

    payload = {
        "schema_version": SCHEMA_VERSION,
        "code_means": code_means,
        # --- what the shift is defined against -------------------------
        "gene_axis_sha256": axis_sha,
        "n_genes": len(genes),
        "genes_file": genes_txt.name,
        "latent_dim": latent_dim,
        "condition": str(config.data.condition),
        "source_label": str(config.data.source),
        "target_label": str(config.data.target),
        "code_means_keys": sorted(code_means),
        # --- where it came from ----------------------------------------
        "source_dataset_path": str(train_path),
        "source_dataset_sha256": file_sha256(train_path),
        "source_dataset_bytes": os.path.getsize(train_path),
        "split_used": "all (from checkpoint)" if from_ckpt else "train",
        "n_cells_encoded": n_cells,
        "datasplit": dict(config.get("datasplit", {})),
        "model_checkpoint_path": str(ckpt_path),
        "model_checkpoint_sha256": file_sha256(ckpt_path),
        "model_checkpoint_step": int(ckpt_meta.get("step", -1)),
        # --- how it was computed ---------------------------------------
        "device": str(device),
        "torch_version": torch.__version__,
        "anndata_version": anndata.__version__,
        "python_version": platform.python_version(),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "created_by": f"scripts/bake_model_artifacts.py (schema {SCHEMA_VERSION})",
        "created_on_host": socket.gethostname(),
        "created_by_user": getpass.getuser(),
        "compute_seconds": round(elapsed, 2),
    }
    write_atomic(shift_pt, lambda p: torch.save(payload, str(p)))
    keys = ", ".join(f"{k}[{tuple(v.shape)}]" for k, v in sorted(code_means.items()))
    print(f"  wrote   {shift_pt}")
    print(f"          code_means: {keys}  ({n_cells} cells, {elapsed:.1f}s, {device})")
    shift = code_means[str(config.data.target)] - code_means[str(config.data.source)]
    print(f"          shift norm ({config.data.target}-{config.data.source}): "
          f"{float(shift.norm()):.6f}")
    return True


def verify_one(genes_txt, shift_pt, genes, axis_sha, config, scgen_dir,
               cellot_dir, train_path):
    """Recompute both sidecars and compare against what is on disk."""
    import torch

    ok = True
    if not genes_txt.exists():
        print(f"  MISSING {genes_txt}")
        ok = False
    else:
        on_disk = genes_txt.read_text().split("\n")
        on_disk = [g for g in on_disk if g != ""]
        if on_disk == list(map(str, genes)):
            print(f"  OK      genes.txt matches the dataset axis ({len(genes)} genes)")
        else:
            print(f"  FAIL    genes.txt does NOT match {train_path}")
            ok = False

    if not shift_pt.exists():
        print(f"  MISSING {shift_pt}")
        return False

    saved = torch.load(str(shift_pt), map_location="cpu")
    if saved.get("gene_axis_sha256") != axis_sha:
        print(f"  FAIL    recorded gene_axis_sha256 {saved.get('gene_axis_sha256')}")
        print(f"          != dataset axis           {axis_sha}")
        return False
    print("  OK      recorded gene_axis_sha256 matches the dataset axis")

    fresh, _, n_cells, _ = compute_code_means(
        config, scgen_dir, cellot_dir, len(genes), train_path
    )
    for key in sorted(set(fresh) | set(saved["code_means"])):
        if key not in fresh or key not in saved["code_means"]:
            print(f"  FAIL    code_means key '{key}' present in only one of the two")
            ok = False
            continue
        d = float((fresh[key] - saved["code_means"][key]).abs().max())
        verdict = "OK     " if d == 0.0 else "FAIL   "
        if d != 0.0:
            ok = False
        print(f"  {verdict} code_means['{key}'] max|diff| = {d:.3e}")
    return ok


def main():
    here = Path(__file__).resolve().parent
    repo = here.parent
    cellot_dir = repo / "cellot" / "cellot_gpu"

    ap = argparse.ArgumentParser(
        description="Bake genes.txt + scgen_shift.pt beside trained models.",
        epilog="Model sets: " + ", ".join(sorted(MODEL_SETS)),
    )
    ap.add_argument("results_dirs", nargs="*",
                    help="results directories to bake, e.g. "
                         "cellot/cellot_gpu/results/atlas_full_seurat_v3")
    ap.add_argument("--model-set", action="append", default=[],
                    help="expand a named model set into its per-flavor results "
                         "dirs (repeatable)")
    ap.add_argument("--results-root", default=str(cellot_dir / "results"),
                    help="root the --model-set templates are resolved under")
    ap.add_argument("--cellot-dir", default=str(cellot_dir),
                    help="cellot/cellot_gpu, used to resolve config.data.path")
    ap.add_argument("--force", action="store_true",
                    help="rewrite sidecars that already exist")
    ap.add_argument("--verify", action="store_true",
                    help="recompute and compare against existing sidecars; "
                         "writes nothing")
    args = ap.parse_args()

    sys.path.insert(0, args.cellot_dir)

    targets = list(args.results_dirs)
    for name in args.model_set:
        if name not in MODEL_SETS:
            ap.error(f"unknown --model-set '{name}'; "
                     f"valid: {', '.join(sorted(MODEL_SETS))}")
        spec = MODEL_SETS[name]
        for flavor in spec["flavors"]:
            sub = spec["results_template"].replace("{flavor}", flavor)
            targets.append(os.path.join(args.results_root, sub))

    if not targets:
        ap.error("nothing to do: pass a results dir or --model-set")

    print(f"cellot dir : {args.cellot_dir}")
    print(f"mode       : {'verify' if args.verify else 'bake'}")
    print("")

    ok = True
    for t in targets:
        ok = bake_one(t, args.cellot_dir, force=args.force, verify=args.verify) and ok
        print("")

    if not ok:
        print("FAILED -- see above.")
        return 1
    print("All requested model sets " + ("verified." if args.verify else "baked."))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
autospeciesOT — single entry-point script for one experiment cycle.

Orchestrates: data preparation → scGen training → CellOT/IMPACT training → evaluation.
Invokes the existing cellot scripts as subprocesses; does NOT reimplement training.

Usage:
    python run_experiment.py \
        --tag baseline_cd8 \
        --holdout CL:0000625 \
        --also-exclude CL:0000893 \
        --model-framing impact \
        --scgen-iters 50000 \
        --cellot-iters 50000

Reads data from the cellot codebase, writes results under ./experiments/<tag>/.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

CELLOT_ROOT = Path(__file__).resolve().parent.parent / "cellot" / "cellot_gpu"
SPECIESOT_ROOT = Path(__file__).resolve().parent.parent / "speciesOT"
DATASETS_DIR = CELLOT_ROOT / "datasets" / "speciesot-human-mouse"
EXPERIMENTS_DIR = Path(__file__).resolve().parent / "experiments"

SCGEN_CONFIG_TEMPLATE = CELLOT_ROOT / "configs" / "models" / "scgen.yaml"
CELLOT_CONFIG_TEMPLATE = CELLOT_ROOT / "configs" / "models" / "cellot.yaml"

T_CELL_FAMILY = {
    "CL:0000084": "T cell",
    "CL:0000893": "thymocyte",
    "CL:0000624": "CD4-positive, alpha-beta T cell",
    "CL:0000625": "CD8-positive, alpha-beta T cell",
}


def parse_args():
    p = argparse.ArgumentParser(description="Run one autospeciesOT experiment")
    p.add_argument("--tag", required=True, help="Experiment tag (e.g. baseline_cd8)")
    p.add_argument("--holdout", required=True,
                   help="Cell ontology term ID(s) to hold out, comma-separated")
    p.add_argument("--also-exclude", default="",
                   help="Additional cell type IDs to exclude from training, comma-separated")
    p.add_argument("--model-framing", choices=["impact", "cellot"], default="impact",
                   help="impact = condition=species; cellot = condition=cell_type_status")
    p.add_argument("--scgen-iters", type=int, default=50000)
    p.add_argument("--cellot-iters", type=int, default=50000)
    p.add_argument("--skip-scgen", action="store_true",
                   help="Skip scGen training (reuse existing checkpoint)")
    p.add_argument("--scgen-from", default="",
                   help="Path to existing scGen results dir to reuse")
    p.add_argument("--device", default="auto",
                   help="'cpu', 'cuda', or 'auto' (detect)")
    p.add_argument("--source-species", default="mouse")
    p.add_argument("--target-species", default="human")
    return p.parse_args()


def resolve_device(requested):
    if requested == "auto":
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"
    return requested


def prepare_datasets(args, exp_dir):
    """Prepare scGen and CellOT h5ad datasets based on holdout configuration."""
    import anndata
    import scanpy as sc

    sys.path.insert(0, str(SPECIESOT_ROOT))
    from speciesot_helpers import (
        match_cells_by_celltype_tissue,
        align_adatas_biomart_one2one,
    )

    holdout_ids = [x.strip() for x in args.holdout.split(",") if x.strip()]
    exclude_ids = [x.strip() for x in args.also_exclude.split(",") if x.strip()]
    all_excluded = set(holdout_ids + exclude_ids)

    data_dir = exp_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    ae_path = data_dir / "ae_training.h5ad"
    cellot_path = data_dir / "cellot_matched.h5ad"

    if ae_path.exists() and cellot_path.exists():
        print(f"[data] Datasets already prepared at {data_dir}")
        cellot_data = anndata.read_h5ad(cellot_path)
        ae_data = anndata.read_h5ad(ae_path)
        print(f"[data] AE training: {ae_data.n_obs} cells")
        print(f"[data] CellOT matched: {cellot_data.n_obs} cells")
        return ae_path, cellot_path

    print("[data] Preparing datasets...")
    print(f"[data] Holdout cell types: {holdout_ids}")
    print(f"[data] Also excluded: {exclude_ids}")

    # Load the existing matched and expanded datasets
    # Try the v07 datasets first (from iteration 2), fall back to finding available ones
    expanded_candidates = sorted(DATASETS_DIR.glob("ae_training_expanded*.h5ad"), reverse=True)
    matched_candidates = sorted(DATASETS_DIR.glob("cd8_holdout*.h5ad"), reverse=True)

    if not expanded_candidates:
        print("[data] ERROR: No ae_training_expanded h5ad found in", DATASETS_DIR)
        print("[data] Available files:", list(DATASETS_DIR.glob("*.h5ad")))
        sys.exit(1)

    # Use the full expanded dataset as the base for scGen
    full_expanded = anndata.read_h5ad(expanded_candidates[0])
    print(f"[data] Loaded full expanded dataset: {full_expanded.n_obs} cells from {expanded_candidates[0].name}")

    # For scGen: exclude all holdout + also-excluded cell types
    ct_col = "cell_type_ontology_term_id"
    mask_keep = ~full_expanded.obs[ct_col].astype(str).isin(all_excluded)
    ae_data = full_expanded[mask_keep].copy()
    print(f"[data] AE training after exclusions: {ae_data.n_obs} cells "
          f"(removed {(~mask_keep).sum()} cells)")

    # Ensure condition column exists for scGen
    if "condition" not in ae_data.obs.columns and "species" in ae_data.obs.columns:
        ae_data.obs["condition"] = ae_data.obs["species"].copy()

    ae_data.write_h5ad(ae_path)
    print(f"[data] Saved AE training data: {ae_path}")

    # For CellOT: use matched dataset, set up condition based on framing
    if matched_candidates:
        cellot_base = anndata.read_h5ad(matched_candidates[0])
        print(f"[data] Loaded matched dataset: {cellot_base.n_obs} cells from {matched_candidates[0].name}")
    else:
        print("[data] WARNING: No pre-matched dataset found, using expanded dataset")
        cellot_base = full_expanded.copy()

    if args.model_framing == "impact":
        # IMPACT: condition = species, holdout = cell type
        if "condition" not in cellot_base.obs.columns:
            cellot_base.obs["condition"] = cellot_base.obs["species"].copy()
        else:
            cellot_base.obs["condition"] = cellot_base.obs["species"].astype(str)
    else:
        # CellOT: condition = cell_type_status (holdout vs non-holdout)
        is_holdout = cellot_base.obs[ct_col].astype(str).isin(holdout_ids)
        cellot_base.obs["condition"] = np.where(
            is_holdout,
            "holdout",
            "non_holdout"
        )

    cellot_base.write_h5ad(cellot_path)
    print(f"[data] Saved CellOT data: {cellot_path}")

    return ae_path, cellot_path


def write_task_config(exp_dir, args, ae_path, cellot_path, device):
    """Write YAML task configs for scGen and CellOT training."""
    import yaml

    config_dir = exp_dir / "configs"
    config_dir.mkdir(parents=True, exist_ok=True)

    holdout_ids = [x.strip() for x in args.holdout.split(",") if x.strip()]

    # scGen task config
    scgen_task = {
        "data": {
            "type": "cell",
            "source": args.source_species,
            "target": args.target_species,
            "condition": "condition",
            "path": str(ae_path),
        },
        "dataloader": {"batch_size": 256, "shuffle": True},
        "datasplit": {
            "groupby": "condition",
            "name": "train_test",
            "test_size": 0.2,
            "random_state": 0,
        },
        "device": device,
    }
    scgen_task_path = config_dir / "scgen_task.yaml"
    with open(scgen_task_path, "w") as f:
        yaml.dump(scgen_task, f, default_flow_style=False)

    # CellOT task config
    if args.model_framing == "impact":
        cellot_task = {
            "data": {
                "type": "cell",
                "source": args.source_species,
                "target": args.target_species,
                "condition": "condition",
                "path": str(cellot_path),
                "ae_emb": {"path": str(exp_dir / "scgen")},
            },
            "dataloader": {"batch_size": 128, "shuffle": True},
            "datasplit": {
                "groupby": "condition",
                "name": "train_test",
                "holdout": {"cell_type_ontology_term_id": holdout_ids[0] if len(holdout_ids) == 1 else holdout_ids},
                "test_size": 0.2,
                "random_state": 0,
            },
            "device": device,
        }
    else:
        cellot_task = {
            "data": {
                "type": "cell",
                "source": "non_holdout",
                "target": "holdout",
                "condition": "condition",
                "path": str(cellot_path),
                "ae_emb": {"path": str(exp_dir / "scgen")},
            },
            "dataloader": {"batch_size": 128, "shuffle": True},
            "datasplit": {
                "groupby": "condition",
                "name": "train_test",
                "holdout": {"species": args.target_species},
                "test_size": 0.2,
                "random_state": 0,
            },
            "device": device,
        }

    cellot_task_path = config_dir / "cellot_task.yaml"
    with open(cellot_task_path, "w") as f:
        yaml.dump(cellot_task, f, default_flow_style=False)

    return scgen_task_path, cellot_task_path


def run_training(script, outdir, configs, extra_args=None, cwd=None):
    """Run a cellot training script as a subprocess."""
    cmd = [sys.executable, str(script), f"--outdir={outdir}"]
    for cfg in configs:
        cmd.append(f"--config={cfg}")
    if extra_args:
        cmd.extend(extra_args)

    print(f"[train] Running: {' '.join(cmd)}")
    print(f"[train] Working dir: {cwd or '.'}")

    t0 = time.time()
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    elapsed = time.time() - t0

    if result.stdout:
        print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
    if result.returncode != 0:
        print(f"[train] FAILED (exit code {result.returncode}) after {elapsed:.1f}s")
        if result.stderr:
            print(result.stderr[-3000:] if len(result.stderr) > 3000 else result.stderr)
        return False, elapsed
    else:
        print(f"[train] Completed in {elapsed:.1f}s")
        return True, elapsed


def run_evaluation(script, outdir, setting, where, embedding=None, cwd=None):
    """Run cellot evaluation script as a subprocess."""
    cmd = [
        sys.executable, str(script),
        f"--outdir={outdir}",
        f"--setting={setting}",
        f"--where={where}",
    ]
    if embedding:
        cmd.append(f"--embedding={embedding}")

    print(f"[eval] Running: {' '.join(cmd)}")

    t0 = time.time()
    result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    elapsed = time.time() - t0

    if result.stdout:
        print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
    if result.returncode != 0:
        print(f"[eval] FAILED (exit code {result.returncode}) after {elapsed:.1f}s")
        if result.stderr:
            print(result.stderr[-3000:] if len(result.stderr) > 3000 else result.stderr)
        return False, elapsed
    else:
        print(f"[eval] Completed in {elapsed:.1f}s")
        return True, elapsed


def compute_summary_metrics(exp_dir, model_name):
    """Read evals.csv and compute summary metrics."""
    eval_dir = exp_dir / model_name / "evals_ood_data_space"
    evals_csv = eval_dir / "evals.csv"

    if not evals_csv.exists():
        print(f"[metrics] evals.csv not found at {evals_csv}")
        return None

    evals = pd.read_csv(evals_csv)

    metrics = {}
    for metric_name in ["r2-means", "r2-stds", "l2-means", "mmd", "enrichment-k50"]:
        vals = evals[evals["metric"] == metric_name]["value"]
        if len(vals) > 0:
            metrics[metric_name] = vals.mean()

    return metrics


def print_summary(args, metrics, total_seconds, peak_mem_mb=0):
    """Print the final summary in a format grep can parse."""
    print("---")
    print(f"r2_means:       {metrics.get('r2-means', 0):.6f}")
    print(f"r2_stds:        {metrics.get('r2-stds', 0):.6f}")
    print(f"mmd:            {metrics.get('mmd', 0):.6f}")
    print(f"enrichment_k50: {metrics.get('enrichment-k50', 0):.6f}")
    print(f"l2_means:       {metrics.get('l2-means', 0):.6f}")
    print(f"peak_mem_mb:    {peak_mem_mb:.1f}")
    print(f"train_seconds:  {total_seconds:.1f}")
    print(f"holdout:        {args.holdout}")
    print(f"also_excluded:  {args.also_exclude or 'none'}")
    print(f"model_framing:  {args.model_framing}")
    print(f"scgen_iters:    {args.scgen_iters}")
    print(f"cellot_iters:   {args.cellot_iters}")


def main():
    args = parse_args()
    device = resolve_device(args.device)
    print(f"[setup] Device: {device}")

    exp_dir = EXPERIMENTS_DIR / args.tag
    exp_dir.mkdir(parents=True, exist_ok=True)
    print(f"[setup] Experiment directory: {exp_dir}")

    train_script = CELLOT_ROOT / "scripts" / "train.py"
    eval_script = CELLOT_ROOT / "scripts" / "evaluate.py"

    if not train_script.exists():
        print(f"[setup] ERROR: train.py not found at {train_script}")
        sys.exit(1)

    t_total_start = time.time()

    # Step 1: Prepare datasets
    print("\n" + "=" * 60)
    print("STEP 1: Data Preparation")
    print("=" * 60)
    ae_path, cellot_path = prepare_datasets(args, exp_dir)

    # Step 2: Write configs
    print("\n" + "=" * 60)
    print("STEP 2: Writing Configs")
    print("=" * 60)
    scgen_task_path, cellot_task_path = write_task_config(
        exp_dir, args, ae_path, cellot_path, device
    )
    print(f"[config] scGen task: {scgen_task_path}")
    print(f"[config] CellOT task: {cellot_task_path}")

    # Step 3: Train scGen
    scgen_dir = exp_dir / "scgen"
    scgen_status = scgen_dir / "cache" / "status"

    if args.skip_scgen and scgen_status.exists() and scgen_status.read_text().strip() == "done":
        print("\n" + "=" * 60)
        print("STEP 3: scGen Training — SKIPPED (reusing existing)")
        print("=" * 60)
    elif args.scgen_from and Path(args.scgen_from).exists():
        print("\n" + "=" * 60)
        print(f"STEP 3: scGen Training — LINKING from {args.scgen_from}")
        print("=" * 60)
        scgen_dir.mkdir(parents=True, exist_ok=True)
        # Symlink the cache directory
        src_cache = Path(args.scgen_from) / "cache"
        dst_cache = scgen_dir / "cache"
        if not dst_cache.exists() and src_cache.exists():
            os.symlink(src_cache, dst_cache)
            print(f"[scgen] Linked {src_cache} → {dst_cache}")
    else:
        print("\n" + "=" * 60)
        print("STEP 3: scGen Training")
        print("=" * 60)

        ok, elapsed = run_training(
            train_script,
            outdir=str(scgen_dir),
            configs=[str(scgen_task_path), str(SCGEN_CONFIG_TEMPLATE)],
            extra_args=[
                f"--config.model.hidden_units=[256, 256]",
                f"--config.model.dropout=0.1",
                f"--config.training.n_iters={args.scgen_iters}",
                "--config.training.eval_freq=1000",
                "--config.training.logs_freq=100",
                "--config.training.cache_freq=5000",
            ],
            cwd=CELLOT_ROOT,
        )
        if not ok:
            print("[scgen] Training FAILED")
            print_summary(args, {}, time.time() - t_total_start)
            sys.exit(1)

    # Create model-scgen symlink for CellOT's ae_emb.path resolution
    model_scgen_link = exp_dir / "model-scgen"
    if not model_scgen_link.exists():
        os.symlink(scgen_dir, model_scgen_link)

    # Step 4: Train CellOT/IMPACT
    print("\n" + "=" * 60)
    print(f"STEP 4: {'IMPACT' if args.model_framing == 'impact' else 'CellOT'} Training")
    print("=" * 60)

    cellot_dir = exp_dir / args.model_framing
    ok, elapsed = run_training(
        train_script,
        outdir=str(cellot_dir),
        configs=[str(cellot_task_path), str(CELLOT_CONFIG_TEMPLATE)],
        extra_args=[
            f"--config.training.n_iters={args.cellot_iters}",
            f"--config.data.ae_emb.path={scgen_dir}",
        ],
        cwd=CELLOT_ROOT,
    )
    if not ok:
        print(f"[cellot] Training FAILED")
        print_summary(args, {}, time.time() - t_total_start)
        sys.exit(1)

    # Step 5: Evaluate
    print("\n" + "=" * 60)
    print("STEP 5: OOD Evaluation (data space)")
    print("=" * 60)

    ok, elapsed = run_evaluation(
        eval_script,
        outdir=str(cellot_dir),
        setting="ood",
        where="data_space",
        embedding="ae",
        cwd=CELLOT_ROOT,
    )
    if not ok:
        print("[eval] Evaluation FAILED")
        print_summary(args, {}, time.time() - t_total_start)
        sys.exit(1)

    # Step 6: Compute and print summary
    print("\n" + "=" * 60)
    print("STEP 6: Results")
    print("=" * 60)

    metrics = compute_summary_metrics(exp_dir, args.model_framing)
    if metrics is None:
        print("[metrics] Could not compute metrics")
        print_summary(args, {}, time.time() - t_total_start)
        sys.exit(1)

    total_seconds = time.time() - t_total_start

    try:
        import torch
        peak_mem_mb = torch.cuda.max_memory_allocated() / 1024 / 1024 if torch.cuda.is_available() else 0
    except Exception:
        peak_mem_mb = 0

    print_summary(args, metrics, total_seconds, peak_mem_mb)


if __name__ == "__main__":
    main()

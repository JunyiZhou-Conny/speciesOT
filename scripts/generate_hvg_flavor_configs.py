#!/usr/bin/env python3
"""Generate configs and sbatch scripts for HVG-flavor × holdout-group × mode × model.

Default (no flags): original **4 T-cell groups** × **5 flavors** × 2 modes × 2 models
= 80 trained-model cells (`hvg_flavor_run_matrix.md`).

``--m2-two-flavors``: **monocyte M2** (`toggle_m2`-equivalent holdout) ×
(`seurat_v3`, `pearson_residuals`) only — configs under
``results/hvg_{flavor}_m2_{iid|ood}/`` matching ``01.5`` outputs
``hvg_{flavor}_m2_v07.h5ad``. Also writes **eval_dataspace** sbatches
(`evals_ood_data_space/`) alongside the legacy latent-space eval scripts.

Training uses ``datasplit.name=toggle_ood`` everywhere (same ``random_state`` as CD8).

This script writes files only. It does NOT submit any sbatch jobs.
"""

import argparse
from pathlib import Path

BASE = Path("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT")
CELLOT_DIR = BASE / "cellot" / "cellot_gpu"
RESULTS_DIR = CELLOT_DIR / "results"
SBATCH_DIR = BASE / "sbatch"
DATA_REL = "datasets/speciesot-human-mouse-hvg"  # relative to CELLOT_DIR

FLAVORS = ["seurat", "cell_ranger", "seurat_v3", "seurat_v3_paper", "pearson_residuals"]

# Original T-cell holdout matrix only (omit m2 unless --m2-two-flavors).
GROUPS_CORE = {
    "a": {"name": "cd8", "holdout": ["CL:0000625"]},
    "b": {"name": "cd8_thymo", "holdout": ["CL:0000625", "CL:0000893"]},
    "c": {"name": "tcell_subtypes", "holdout": ["CL:0000624", "CL:0000625", "CL:0000893"]},
    "d": {"name": "cd4", "holdout": ["CL:0000624"]},
}

# Same ontology pair as speciesOT/baseline/analysis/09_data_prep_toggle_experiments (toggle_m2).
GROUPS_M2 = {
    "m2": {"name": "toggle_m2", "holdout": ["CL:0000875", "CL:0000576"]},
}

MODES = ["ood", "iid"]


def _holdout_yaml(holdout_list):
    """Render the `holdout` field as either a single quoted string or a YAML list."""
    if len(holdout_list) == 1:
        return f"  holdout: '{holdout_list[0]}'"
    lines = ["  holdout:"]
    for h in holdout_list:
        lines.append(f"  - '{h}'")
    return "\n".join(lines)


def make_scgen_config(flavor, gk, mode, groups):
    g = groups[gk]
    holdout_block = _holdout_yaml(g["holdout"])
    data_path = f"{DATA_REL}/hvg_{flavor}_{gk}_v07.h5ad"
    return f"""\
data:
  condition: condition
  path: {data_path}
  source: mouse
  target: human
  type: cell
dataloader:
  batch_size: 256
  shuffle: true
datasplit:
  name: toggle_ood
  key: cell_type_ontology_term_id
{holdout_block}
  mode: {mode}
  groupby: condition
  random_state: 0
  test_size: 0.2
device: cuda
model:
  beta: 0.0
  dropout: 0.1
  hidden_units:
  - 256
  - 256
  latent_dim: 50
  name: scgen
optim:
  lr: 0.001
  optimizer: Adam
  weight_decay: 1.0e-05
scheduler:
  gamma: 0.5
  step_size: 100000
training:
  cache_freq: 5000
  eval_freq: 1000
  logs_freq: 100
  n_iters: 50000
"""


def make_impact_config(flavor, gk, mode, groups):
    g = groups[gk]
    holdout_block = _holdout_yaml(g["holdout"])
    data_path = f"{DATA_REL}/hvg_{flavor}_{gk}_v07.h5ad"
    return f"""\
data:
  ae_emb:
    path: ./results/hvg_{flavor}_{gk}_{mode}/scgen/
  condition: condition
  path: {data_path}
  source: mouse
  target: human
  type: cell
dataloader:
  batch_size: 128
  shuffle: true
datasplit:
  name: toggle_ood
  key: cell_type_ontology_term_id
{holdout_block}
  mode: {mode}
  groupby: condition
  random_state: 0
  test_size: 0.2
device: cuda
model:
  g:
    fnorm_penalty: 1
  hidden_units:
  - 64
  - 64
  - 64
  - 64
  kernel_init_fxn:
    b: 0.1
    name: uniform
  latent_dim: 50
  name: cellot
  softplus_W_kernels: false
optim:
  beta1: 0.5
  beta2: 0.9
  lr: 0.0001
  optimizer: Adam
  weight_decay: 0
training:
  cache_freq: 1000
  eval_freq: 250
  logs_freq: 50
  n_inner_iters: 10
  n_iters: 50000
"""


def _sbatch_header(jobname, time, partition, mem, logdir_result_subdir, prefix, gres=None):
    """logdir_result_subdir: RESULTS_DIR / tag / model_dir (training logs land there)."""
    lines = [
        "#!/bin/bash",
        f"#SBATCH -J {jobname}",
        "#SBATCH -c 4",
        f"#SBATCH -t {time}",
        f"#SBATCH -p {partition}",
    ]
    if gres:
        lines.append(f"#SBATCH --gres={gres}")
    log_base = Path(logdir_result_subdir)
    lines += [
        f"#SBATCH --mem={mem}",
        f"#SBATCH -o {log_base}/{prefix}_%j.out",
        f"#SBATCH -e {log_base}/{prefix}_%j.err",
    ]
    return "\n".join(lines)


PREAMBLE = """\
cd /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/

module load python
mamba activate CellOT"""


def _train_sbatch(flavor, gk, mode, model_dir, jobsuffix, gpu=False):
    tag = f"hvg_{flavor}_{gk}_{mode}"
    out_sub = RESULTS_DIR / tag / model_dir
    short = f"{flavor[:2]}_{gk}_{mode}_{jobsuffix}"
    header = _sbatch_header(
        short,
        "12:00:00" if gpu else "4:00:00",
        "gpu_requeue" if gpu else "shared",
        "32G",
        out_sub,
        "train",
        gres="gpu:1" if gpu else None,
    )
    return f"""{header}

{PREAMBLE}

python ./scripts/train.py \\
    --outdir ./results/{tag}/{model_dir} \\
    --config ./results/{tag}/{model_dir}/config.yaml
"""


def _eval_sbatch(flavor, gk, mode, model_dir, jobsuffix, embedding_flag=""):
    tag = f"hvg_{flavor}_{gk}_{mode}"
    out_sub = RESULTS_DIR / tag / model_dir
    short = f"{flavor[:2]}_{gk}_{mode}_{jobsuffix}"
    header = _sbatch_header(short, "1:00:00", "shared", "32G", out_sub, "eval")
    extra = f" {embedding_flag.strip()}" if embedding_flag else ""
    return f"""{header}

{PREAMBLE}

python ./scripts/evaluate.py \\
    --outdir ./results/{tag}/{model_dir} \\
    --setting ood \\
    --where latent_space{extra}
"""


def _eval_dataspace_sbatch(flavor, gk, mode, model_dir):
    """Gene-space metrics + imputed.h5ad (`evals_ood_data_space`); matches CD8 slide pipeline."""
    tag = f"hvg_{flavor}_{gk}_{mode}"
    out_sub = RESULTS_DIR / tag / model_dir
    suffix = "imds" if model_dir == "impact_cellot" else "scds"
    short = f"{flavor[:2]}_{gk}_{mode}_{suffix}"
    header = _sbatch_header(short, "1:00:00", "shared", "32G", out_sub, "eval_dataspace")
    emb = ""
    if model_dir == "impact_cellot":
        emb = "    --embedding ae \\\n"
    return f"""{header}

{PREAMBLE}

python ./scripts/evaluate.py \\
    --outdir ./results/{tag}/{model_dir} \\
    --setting ood \\
    --where data_space \\
{emb}    --n_cells 30,50,80 \\
    --evalprefix evals_ood_data_space
"""


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def write_matrix(flavors, groups, *, write_eval_dataspace=False):
    counts = {"dirs": 0, "configs": 0, "sbatch": 0, "symlinks": 0, "dataspace": 0}
    train_dir = SBATCH_DIR / "train"
    eval_dir = SBATCH_DIR / "eval"
    eval_ds_dir = SBATCH_DIR / "eval_dataspace"

    for flavor in flavors:
        for gk in groups:
            for mode in MODES:
                tag = f"hvg_{flavor}_{gk}_{mode}"
                exp = RESULTS_DIR / tag

                for d in ["scgen", "impact_cellot"]:
                    (exp / d).mkdir(parents=True, exist_ok=True)
                    counts["dirs"] += 1

                link = exp / "model-scgen"
                if link.exists() or link.is_symlink():
                    link.unlink()
                link.symlink_to("scgen")
                counts["symlinks"] += 1

                write_file(exp / "scgen" / "config.yaml", make_scgen_config(flavor, gk, mode, groups))
                write_file(
                    exp / "impact_cellot" / "config.yaml",
                    make_impact_config(flavor, gk, mode, groups),
                )
                counts["configs"] += 2

                write_file(
                    train_dir / f"train_{tag}_scgen.sbatch",
                    _train_sbatch(flavor, gk, mode, "scgen", "sg"),
                )
                write_file(
                    train_dir / f"train_{tag}_impact_cellot.sbatch",
                    _train_sbatch(flavor, gk, mode, "impact_cellot", "imp", gpu=True),
                )
                counts["sbatch"] += 2

                write_file(
                    eval_dir / f"eval_{tag}_scgen.sbatch",
                    _eval_sbatch(flavor, gk, mode, "scgen", "esg", embedding_flag="--embedding ae"),
                )
                write_file(
                    eval_dir / f"eval_{tag}_impact_cellot.sbatch",
                    _eval_sbatch(flavor, gk, mode, "impact_cellot", "eimp"),
                )
                counts["sbatch"] += 2

                if write_eval_dataspace:
                    write_file(
                        eval_ds_dir / f"eval_{tag}_scgen_dataspace.sbatch",
                        _eval_dataspace_sbatch(flavor, gk, mode, "scgen"),
                    )
                    write_file(
                        eval_ds_dir / f"eval_{tag}_impact_cellot_dataspace.sbatch",
                        _eval_dataspace_sbatch(flavor, gk, mode, "impact_cellot"),
                    )
                    counts["dataspace"] += 2

    nf, ng = len(flavors), len(groups)
    print(
        f"Created: {counts['dirs']} dirs, {counts['symlinks']} symlinks, "
        f"{counts['configs']} configs, {counts['sbatch']} standard sbatch scripts"
        + (
            f", {counts['dataspace']} eval_dataspace scripts"
            if write_eval_dataspace
            else ""
        )
    )
    expected_dirs = nf * ng * len(MODES) * 2
    expected_configs = nf * ng * len(MODES) * 2
    expected_sbatch_std = nf * ng * len(MODES) * 4
    print(
        f"Expected this matrix: dirs={expected_dirs}, configs={expected_configs}, "
        f"standard sbatch={expected_sbatch_std}"
        + (
            f", dataspace sbatch={nf * ng * len(MODES) * 2}"
            if write_eval_dataspace
            else ""
        )
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--m2-two-flavors",
        action="store_true",
        help=(
            "Write only group m2 × flavors (seurat_v3, pearson_residuals) × (iid, ood); "
            "include sbatch/eval_dataspace/ scripts."
        ),
    )
    args = parser.parse_args()

    if args.m2_two_flavors:
        write_matrix(["seurat_v3", "pearson_residuals"], GROUPS_M2, write_eval_dataspace=True)
    else:
        write_matrix(FLAVORS, GROUPS_CORE, write_eval_dataspace=False)


if __name__ == "__main__":
    main()

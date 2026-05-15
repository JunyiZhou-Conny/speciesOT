#!/usr/bin/env python3
"""Generate configs and sbatch scripts for the FULL-ATLAS (no-holdout) training:
2 HVG flavors (seurat_v3, pearson_residuals) x 2 models (scgen, impact_cellot) = 4 trainings.

Differs from generate_hvg_flavor_configs.py in:
- No groups, no modes — just per-flavor training on the full matched atlas.
- datasplit.name=train_test (not toggle_ood) since there's no holdout to toggle.
- Result dirs: results/atlas_full_{flavor}/{scgen,impact_cellot}/
- Data path: datasets/speciesot-human-mouse-hvg/hvg_{flavor}_atlas_full_v07.h5ad

This script writes files only — no sbatch submissions.
"""

from pathlib import Path

BASE = Path("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT")
CELLOT_DIR = BASE / "cellot" / "cellot_gpu"
RESULTS_DIR = CELLOT_DIR / "results"
SBATCH_DIR = BASE / "sbatch"
DATA_REL = "datasets/speciesot-human-mouse-hvg"

FLAVORS = ["seurat_v3", "pearson_residuals"]


def make_scgen_config(flavor):
    return f"""\
data:
  condition: condition
  path: {DATA_REL}/hvg_{flavor}_atlas_full_v07.h5ad
  source: mouse
  target: human
  type: cell
dataloader:
  batch_size: 256
  shuffle: true
datasplit:
  name: train_test
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


def make_impact_config(flavor):
    return f"""\
data:
  ae_emb:
    path: ./results/atlas_full_{flavor}/scgen/
  condition: condition
  path: {DATA_REL}/hvg_{flavor}_atlas_full_v07.h5ad
  source: mouse
  target: human
  type: cell
dataloader:
  batch_size: 128
  shuffle: true
datasplit:
  name: train_test
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


def _sbatch_header(jobname, time, partition, mem, outdir, prefix, gres=None):
    lines = [
        "#!/bin/bash",
        f"#SBATCH -J {jobname}",
        "#SBATCH -c 4",
        f"#SBATCH -t {time}",
        f"#SBATCH -p {partition}",
    ]
    if gres:
        lines.append(f"#SBATCH --gres={gres}")
    lines += [
        f"#SBATCH --mem={mem}",
        f"#SBATCH -o {outdir}/{prefix}_%j.out",
        f"#SBATCH -e {outdir}/{prefix}_%j.err",
    ]
    return "\n".join(lines)


PREAMBLE = """\
cd /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/

module load python
mamba activate CellOT"""


def _train_sbatch(flavor, model_dir, jobsuffix, gpu=False):
    tag = f"atlas_full_{flavor}"
    outdir = f"{RESULTS_DIR}/{tag}/{model_dir}"
    short = f"af_{flavor[:2]}_{jobsuffix}"
    header = _sbatch_header(
        short,
        "12:00:00" if gpu else "4:00:00",
        "gpu_requeue" if gpu else "shared",
        "32G", outdir, "train",
        gres="gpu:1" if gpu else None,
    )
    return f"""{header}

{PREAMBLE}

python ./scripts/train.py \\
    --outdir ./results/{tag}/{model_dir} \\
    --config ./results/{tag}/{model_dir}/config.yaml
"""


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def main():
    counts = {"dirs": 0, "configs": 0, "sbatch": 0, "symlinks": 0}
    train_dir = SBATCH_DIR / "train"

    for flavor in FLAVORS:
        tag = f"atlas_full_{flavor}"
        exp = RESULTS_DIR / tag

        for d in ["scgen", "impact_cellot"]:
            (exp / d).mkdir(parents=True, exist_ok=True)
            counts["dirs"] += 1

        link = exp / "model-scgen"
        if link.exists() or link.is_symlink():
            link.unlink()
        link.symlink_to("scgen")
        counts["symlinks"] += 1

        write_file(exp / "scgen" / "config.yaml", make_scgen_config(flavor))
        write_file(exp / "impact_cellot" / "config.yaml", make_impact_config(flavor))
        counts["configs"] += 2

        write_file(
            train_dir / f"train_{tag}_scgen.sbatch",
            _train_sbatch(flavor, "scgen", "sg"),
        )
        write_file(
            train_dir / f"train_{tag}_impact_cellot.sbatch",
            _train_sbatch(flavor, "impact_cellot", "imp", gpu=True),
        )
        counts["sbatch"] += 2

    print(f"Created: {counts['dirs']} dirs, {counts['symlinks']} symlinks, "
          f"{counts['configs']} configs, {counts['sbatch']} sbatch scripts")


if __name__ == "__main__":
    main()

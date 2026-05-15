#!/usr/bin/env python3
"""Generate all config.yaml files and sbatch scripts for toggle_ood experiments.

Naming convention: everything uses the group key (t1, t2, ..., m1, m2, ...).
  Directories: toggle_t1_ood/, toggle_t1_iid/, etc.
  Data files:  toggle_t1_holdout_v07.h5ad, toggle_t1_ae_training_ood_v07.h5ad, etc.
  Sbatch:      train_toggle_t1_ood_scgen.sbatch, etc.
"""

from pathlib import Path

BASE = Path("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT")
CELLOT_DIR = BASE / "cellot" / "cellot_gpu"
RESULTS_DIR = CELLOT_DIR / "results"
SBATCH_DIR = BASE / "sbatch"

GROUPS = {
    "t1": {"name": "CD8", "label": "cd8", "holdout": ["CL:0000625"]},
    "t2": {"name": "CD8 + thymocyte", "label": "cd8_thymo", "holdout": ["CL:0000625", "CL:0000893"]},
    "t3": {"name": "All T cell subtypes", "label": "tcell_subtype", "holdout": ["CL:0000624", "CL:0000625", "CL:0000893"]},
    "t4": {"name": "CD4", "label": "cd4", "holdout": ["CL:0000624"]},
    "m1": {"name": "Non-classical monocyte", "label": "nonclassical_mono", "holdout": ["CL:0000875"]},
    "m2": {"name": "Non-classical + generic monocyte", "label": "nonclassical_generic_mono", "holdout": ["CL:0000875", "CL:0000576"]},
    "m3": {"name": "All monocyte subtypes", "label": "mono_subtype", "holdout": ["CL:0000875", "CL:0000860", "CL:0002393", "CL:0000576"]},
    "m4": {"name": "Classical monocyte", "label": "classical_mono", "holdout": ["CL:0000860"]},
}

MODES = ["ood", "iid"]


def _holdout_yaml(holdout_list):
    if len(holdout_list) == 1:
        return f"  holdout: '{holdout_list[0]}'"
    lines = ["  holdout:"]
    for h in holdout_list:
        lines.append(f"  - '{h}'")
    return "\n".join(lines)


def make_scgen_config(gk, mode):
    return f"""\
data:
  condition: condition
  path: datasets/speciesot-human-mouse/toggle_{gk}_ae_training_{mode}_v07.h5ad
  source: mouse
  target: human
  type: cell
dataloader:
  batch_size: 256
  shuffle: true
datasplit:
  groupby: condition
  name: train_test
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


def make_impact_config(gk, mode):
    g = GROUPS[gk]
    holdout_block = _holdout_yaml(g["holdout"])
    return f"""\
data:
  ae_emb:
    path: ./results/toggle_{gk}_{mode}/scgen/
  condition: condition
  path: datasets/speciesot-human-mouse/toggle_{gk}_holdout_v07.h5ad
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


def make_cellot_config(gk, mode):
    g = GROUPS[gk]
    label = g["label"]
    return f"""\
data:
  ae_emb:
    path: ./results/toggle_{gk}_{mode}/scgen/
  condition: condition
  path: datasets/speciesot-human-mouse/toggle_{gk}_holdout_swapped_v07.h5ad
  source: non_{label}
  target: {label}
  type: cell
dataloader:
  batch_size: 128
  shuffle: true
datasplit:
  name: toggle_ood
  key: species
  holdout: 'human'
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


def _train_sbatch(gk, mode, model_dir, jobsuffix, gpu=False):
    tag = f"toggle_{gk}_{mode}"
    outdir = f"{RESULTS_DIR}/{tag}/{model_dir}"
    header = _sbatch_header(
        f"{gk}_{mode}_{jobsuffix}",
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


def _eval_sbatch(gk, mode, model_dir, jobsuffix):
    tag = f"toggle_{gk}_{mode}"
    outdir = f"{RESULTS_DIR}/{tag}/{model_dir}"
    header = _sbatch_header(f"{gk}_{mode}_{jobsuffix}", "1:00:00", "shared", "32G", outdir, "eval")
    return f"""{header}

{PREAMBLE}

python ./scripts/evaluate.py \\
    --outdir ./results/{tag}/{model_dir} \\
    --setting ood \\
    --where latent_space
"""


def write_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)


def main():
    n = {"dirs": 0, "configs": 0, "sbatch": 0, "symlinks": 0}

    for gk in GROUPS:
        for mode in MODES:
            tag = f"toggle_{gk}_{mode}"
            exp = RESULTS_DIR / tag

            for d in ["scgen", "impact", "cellot"]:
                (exp / d).mkdir(parents=True, exist_ok=True)
                n["dirs"] += 1

            link = exp / "model-scgen"
            if link.exists() or link.is_symlink():
                link.unlink()
            link.symlink_to("scgen")
            n["symlinks"] += 1

            write_file(exp / "scgen" / "config.yaml", make_scgen_config(gk, mode))
            write_file(exp / "impact" / "config.yaml", make_impact_config(gk, mode))
            write_file(exp / "cellot" / "config.yaml", make_cellot_config(gk, mode))
            n["configs"] += 3

            train = SBATCH_DIR / "train"
            write_file(train / f"train_{tag}_scgen.sbatch", _train_sbatch(gk, mode, "scgen", "sg"))
            write_file(train / f"train_{tag}_impact.sbatch", _train_sbatch(gk, mode, "impact", "imp", gpu=True))
            write_file(train / f"train_{tag}_cellot.sbatch", _train_sbatch(gk, mode, "cellot", "cot", gpu=True))
            n["sbatch"] += 3

            evl = SBATCH_DIR / "eval"
            write_file(evl / f"eval_{tag}_impact.sbatch", _eval_sbatch(gk, mode, "impact", "eimp"))
            write_file(evl / f"eval_{tag}_cellot.sbatch", _eval_sbatch(gk, mode, "cellot", "ecot"))
            n["sbatch"] += 2

    print(f"Created: {n['dirs']} dirs, {n['symlinks']} symlinks, {n['configs']} configs, {n['sbatch']} sbatch scripts")


if __name__ == "__main__":
    main()

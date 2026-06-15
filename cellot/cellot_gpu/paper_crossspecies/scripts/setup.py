"""Materialize configs + sbatches for Bunne et al. cross-species LPS replication.

Writes per-holdout experiment dirs under results/paper_crossspecies_{holdout}_ood/
and sbatch scripts under paper_crossspecies/sbatch/.

USAGE (from cellot_gpu/):
    python paper_crossspecies/scripts/setup.py --holdout rat
    python paper_crossspecies/scripts/setup.py --holdout mouse
"""

from __future__ import annotations

import argparse
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1]
CELLOT = BUNDLE.parent
REPO = CELLOT.parent.parent
RESULTS = CELLOT / "results"
SBATCH = BUNDLE / "sbatch"
DATA_PATH = "datasets/scrna-crossspecies/hvg-top1k-train-only.h5ad"

_PREAMBLE = f"""\
cd {CELLOT}/

module load python
mamba activate CellOT

export PYTHONPATH={CELLOT}:$PYTHONPATH"""


def _sbatch_header(jobname: str, time: str, partition: str, mem: str,
                   outdir: Path, log_prefix: str, gres: str | None = None) -> str:
    lines = [
        "#!/bin/bash",
        f"#SBATCH -J {jobname}",
        "#SBATCH -c 4",
        f"#SBATCH -t {time}",
        f"#SBATCH -p {partition}",
    ]
    if gres:
        lines.append(f"#SBATCH --gres={gres}")
        lines.append("#SBATCH --constraint=v100")
    lines += [
        f"#SBATCH --mem={mem}",
        f"#SBATCH -o {outdir}/{log_prefix}_%j.out",
        f"#SBATCH -e {outdir}/{log_prefix}_%j.err",
    ]
    return "\n".join(lines)


def render_scgen_config(tag: str, holdout: str) -> str:
    return f"""\
# Paper cross-species LPS replication (scGen AE sibling)
data:
  condition: condition
  path: {DATA_PATH}
  source: unst
  target: LPS6
  type: cell
dataloader:
  batch_size: 256
  shuffle: true
datasplit:
  name: toggle_ood
  key: species
  holdout: {holdout}
  mode: ood
  groupby:
  - species
  - condition
  random_state: 0
  test_size: 500
  stratify: condition
device: cpu
model:
  beta: 0.0
  dropout: 0.0
  hidden_units:
  - 512
  - 512
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
  cache_freq: 10000
  eval_freq: 2500
  logs_freq: 250
  n_iters: 250000
"""


def render_impact_config(tag: str, holdout: str) -> str:
    return f"""\
# Paper cross-species LPS replication (CellOT in scGen latent space)
data:
  ae_emb:
    path: ./results/{tag}/scgen/
  condition: condition
  path: {DATA_PATH}
  source: unst
  target: LPS6
  type: cell
dataloader:
  batch_size: 256
  shuffle: true
datasplit:
  name: toggle_ood
  key: species
  holdout: {holdout}
  mode: ood
  groupby:
  - species
  - condition
  random_state: 0
  test_size: 500
  stratify: condition
device: cpu
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
  n_iters: 250000
"""


def materialize(holdout: str) -> list[Path]:
    tag = f"paper_crossspecies_{holdout}_ood"
    exp_dir = RESULTS / tag
    scgen_dir = exp_dir / "scgen"
    impact_dir = exp_dir / "impact_cellot"
    scgen_dir.mkdir(parents=True, exist_ok=True)
    impact_dir.mkdir(parents=True, exist_ok=True)

    (scgen_dir / "config.yaml").write_text(render_scgen_config(tag, holdout))
    (impact_dir / "config.yaml").write_text(render_impact_config(tag, holdout))

    link = exp_dir / "model-scgen"
    if link.exists() or link.is_symlink():
        link.unlink()
    link.symlink_to("scgen")

    SBATCH.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    train_scgen = SBATCH / f"train_{tag}_scgen.sbatch"
    train_scgen.write_text(f"""\
{_sbatch_header(f"pc_{holdout}_sg", "72:00:00", "shared", "64G", scgen_dir, "train")}

{_PREAMBLE}

python ./scripts/train.py \\
    --outdir ./results/{tag}/scgen \\
    --config ./results/{tag}/scgen/config.yaml \\
    --config.device cpu
""")
    written.append(train_scgen)

    train_impact = SBATCH / f"train_{tag}_impact.sbatch"
    train_impact.write_text(f"""\
{_sbatch_header(f"pc_{holdout}_imp", "72:00:00", "shared", "64G", impact_dir, "train")}

{_PREAMBLE}

python ./scripts/train.py \\
    --outdir ./results/{tag}/impact_cellot \\
    --config ./results/{tag}/impact_cellot/config.yaml \\
    --config.device cpu
""")
    written.append(train_impact)

    for model_dir, short in [("scgen", "sg"), ("impact_cellot", "imp")]:
        for setting in ("ood", "iid"):
            eval_sb = SBATCH / f"eval_{tag}_{model_dir}_{setting}_paper.sbatch"
            emb = " --embedding ae" if model_dir == "impact_cellot" else ""
            eval_sb.write_text(f"""\
{_sbatch_header(f"pc_{holdout}_{short}_{setting[:3]}", "2:00:00", "shared", "32G", RESULTS / tag / model_dir, f"eval_{setting}")}

{_PREAMBLE}

python ./scripts/evaluate.py \\
    --outdir ./results/{tag}/{model_dir} \\
    --setting {setting} \\
    --where data_space{emb} \\
    --n_markers 50 \\
    --n_cells 500,1000 \\
    --n_reps 10 \\
    --evalprefix evals_{setting}_data_space_paper
""")
            written.append(eval_sb)

        ext_sb = SBATCH / f"ext_{tag}_{model_dir}_ood_paper.sbatch"
        emb_flag = " --embedding ae" if model_dir == "impact_cellot" else ""
        ext_sb.write_text(f"""\
{_sbatch_header(f"pc_{holdout}_{short}_ext", "1:00:00", "shared", "32G", RESULTS / tag / model_dir, "ext_metrics")}

{_PREAMBLE}

python ./scripts/extended_metrics.py \\
    --outdir ./results/{tag}/{model_dir} \\
    --setting ood \\
    --where data_space{emb_flag} \\
    --evalprefix evals_ood_data_space_paper \\
    --n_cells 500,1000 \\
    --n_markers 50
""")
        written.append(ext_sb)

    chain = SBATCH / f"submit_chain_{tag}.sh"
    chain.write_text(f"""\
#!/bin/bash
# Paper cross-species LPS — submit chain for holdout={holdout}
set -euo pipefail
cd {SBATCH}
JOB_SG=$(sbatch --parsable {train_scgen.name})
echo "scgen train job: $JOB_SG"
JOB_IMP=$(sbatch --parsable --dependency=afterok:$JOB_SG {train_impact.name})
echo "impact train job: $JOB_IMP"
for f in eval_{tag}_*_paper.sbatch ext_{tag}_*_paper.sbatch; do
  sbatch --dependency=afterok:$JOB_IMP "$f"
done
echo "Submitted eval + extended_metrics with afterok:$JOB_IMP"
""")
    written.append(chain)

    print(f"[paper-setup] {tag}: configs + {len(written)} sbatches")
    print(f"  submit: bash {chain}")
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--holdout", nargs="+", default=["rat", "mouse"])
    args = ap.parse_args()
    for h in args.holdout:
        materialize(h)


if __name__ == "__main__":
    main()

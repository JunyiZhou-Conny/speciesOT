#!/usr/bin/env python3
"""Generate data-space eval sbatches for the 5-flavor x 4-group x 2-mode x 2-model
matrix. Per-group n_cells values are chosen to fit the eval pool size for each
group with a shared n_cells=30 across all groups for cross-group comparison.

Outputs sbatch scripts to sbatch/eval_dataspace/.
"""

from pathlib import Path

BASE = Path("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT")
RESULTS_DIR = BASE / "cellot/cellot_gpu/results"
SBATCH_DIR = BASE / "sbatch/eval_dataspace"
SBATCH_DIR.mkdir(parents=True, exist_ok=True)

FLAVORS = ["seurat", "cell_ranger", "seurat_v3", "seurat_v3_paper", "pearson_residuals"]
GROUPS = ["a", "b", "c", "d"]
MODES = ["ood", "iid"]
MODELS = ["scgen", "impact_cellot"]

# Per-group n_cells. Common value 30 across all groups; group-specific larger
# values where eval pool size allows. Eval pool ~= holdout cells per species / 2.
N_CELLS_PER_GROUP = {
    "a": "30,50,80",        # eval pool ~97 per species
    "b": "30,80,200,300",   # eval pool ~325
    "c": "30,80,200,300",   # eval pool ~373
    "d": "20,30,40",        # eval pool ~48
}


def write_sbatch(flavor, gk, mode, model):
    tag = f"hvg_{flavor}_{gk}_{mode}"
    outdir = f"{RESULTS_DIR}/{tag}/{model}"
    short = f"{flavor[:2]}_{gk}_{mode}_{model[:2]}ds"
    n_cells = N_CELLS_PER_GROUP[gk]
    if model == "scgen":
        # scGen + data_space: no --embedding ae needed; scGen produces gene-space output
        # via encode + shift + decode by default
        extra = ""
    else:
        extra = ""
    content = f"""#!/bin/bash
#SBATCH -J {short}
#SBATCH -c 4
#SBATCH -t 1:00:00
#SBATCH -p shared
#SBATCH --mem=32G
#SBATCH -o {outdir}/eval_dataspace_%j.out
#SBATCH -e {outdir}/eval_dataspace_%j.err

cd /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/

module load python
mamba activate CellOT

python ./scripts/evaluate.py \\
    --outdir ./results/{tag}/{model} \\
    --setting ood \\
    --where data_space \\
    --n_cells {n_cells} \\
    --evalprefix evals_ood_data_space{extra}
"""
    path = SBATCH_DIR / f"eval_{tag}_{model}_dataspace.sbatch"
    path.write_text(content)
    return path


def main():
    n = 0
    for flavor in FLAVORS:
        for gk in GROUPS:
            for mode in MODES:
                for model in MODELS:
                    write_sbatch(flavor, gk, mode, model)
                    n += 1
    print(f"wrote {n} data-space eval sbatches to {SBATCH_DIR}")
    print(f"per-group n_cells: {N_CELLS_PER_GROUP}")


if __name__ == "__main__":
    main()

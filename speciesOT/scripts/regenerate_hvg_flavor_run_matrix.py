#!/usr/bin/env python3
"""Regenerate `speciesOT/baseline/analysis/hvg_flavor_run_matrix.{csv,md}` from
the same `(FLAVORS, GROUPS, MODES)` source of truth as
`generate_hvg_flavor_configs.py`. Reflects the final design:

  - Group B = combined holdout [CD8, thymocyte] (no separate exclude_from_ae).
  - One combined data file per (flavor, group):
    `datasets/speciesot-human-mouse-hvg/hvg_{flavor}_{gk}_v07.h5ad`.
  - Both scGen and IMPACT use `datasplit.name=toggle_ood` against the same
    file with the same random_state; IID/OOD split happens at training time.
  - 4 sbatch scripts per (flavor, group, mode): train scGen, train IMPACT,
    eval scGen, eval IMPACT.
  - No Normal CellOT, no monocyte groups.
"""

import csv
from pathlib import Path

BASE = Path("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT")
OUT_DIR = BASE / "speciesOT/baseline/analysis"
DATA_REL = "datasets/speciesot-human-mouse-hvg"

FLAVORS = ["seurat", "cell_ranger", "seurat_v3", "seurat_v3_paper", "pearson_residuals"]

FLAVOR_INPUT = {
    "seurat":             ("X (log-norm)",      False),
    "cell_ranger":        ("X (log-norm)",      False),
    "seurat_v3":          ("layers['counts']",  True),
    "seurat_v3_paper":    ("layers['counts']",  True),
    "pearson_residuals":  ("layers['counts']",  True),
}

GROUPS = {
    "a": {"name": "cd8",            "holdout": ["CL:0000625"],                                     "label": "CD8 only"},
    "b": {"name": "cd8_thymo",      "holdout": ["CL:0000625", "CL:0000893"],                       "label": "CD8 + thymocyte combined"},
    "c": {"name": "tcell_subtypes", "holdout": ["CL:0000624", "CL:0000625", "CL:0000893"],         "label": "CD4 + CD8 + thymocyte combined"},
    "d": {"name": "cd4",            "holdout": ["CL:0000624"],                                     "label": "CD4 only"},
}

MODES = {
    "ood": "OOD: model sees zero holdout cells; eval on fixed held-out half",
    "iid": "IID: model sees half holdout cells in training; eval on the other (fixed) half",
}

MODELS = [
    {
        "name": "scgen",
        "label": "scGen",
        "condition": "condition",
        "source": "mouse",
        "target": "human",
    },
    {
        "name": "impact_cellot",
        "label": "IMPACT_CellOT",
        "condition": "condition",
        "source": "mouse",
        "target": "human",
    },
]


def main():
    rows = []
    for flavor in FLAVORS:
        hvg_input, raw_required = FLAVOR_INPUT[flavor]
        for gk, g in GROUPS.items():
            data_file = f"{DATA_REL}/hvg_{flavor}_{gk}_v07.h5ad"
            for mode, mode_desc in MODES.items():
                tag = f"hvg_{flavor}_{gk}_{mode}"
                for model in MODELS:
                    train_sbatch = f"sbatch/train/train_{tag}_{model['name']}.sbatch"
                    eval_sbatch = f"sbatch/eval/eval_{tag}_{model['name']}.sbatch"
                    eval_extra = "--embedding ae" if model["name"] == "scgen" else ""
                    rows.append({
                        "flavor": flavor,
                        "hvg_input": hvg_input,
                        "raw_counts_required": raw_required,
                        "group": gk,
                        "group_name": g["name"],
                        "group_label": g["label"],
                        "holdout_ids": ";".join(g["holdout"]),
                        "mode": mode,
                        "mode_description": mode_desc,
                        "model": model["name"],
                        "model_label": model["label"],
                        "condition": model["condition"],
                        "source": model["source"],
                        "target": model["target"],
                        "data_file": data_file,
                        "result_tag": tag,
                        "result_dir": f"results/{tag}/{model['name']}",
                        "train_sbatch": train_sbatch,
                        "eval_sbatch": eval_sbatch,
                        "eval_flags": f"--setting ood --where latent_space {eval_extra}".strip(),
                    })

    csv_path = OUT_DIR / "hvg_flavor_run_matrix.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {csv_path}  ({len(rows)} rows)")

    md_path = OUT_DIR / "hvg_flavor_run_matrix.md"
    flavor_counts = {f: 0 for f in FLAVORS}
    for r in rows:
        flavor_counts[r["flavor"]] += 1

    n_train_scgen = len(FLAVORS) * len(GROUPS) * len(MODES)
    n_train_impact = n_train_scgen
    n_eval_scgen = n_train_scgen
    n_eval_impact = n_train_scgen
    n_total_sbatch = n_train_scgen + n_train_impact + n_eval_scgen + n_eval_impact
    n_trained_models = n_total_sbatch // 2  # train sbatches only
    n_dataset_files = len(FLAVORS) * len(GROUPS)

    lines = [
        "# 5-Flavor HVG Validation Run Matrix",
        "",
        "Final design as implemented by `01.5_data_prep_all_holdouts_hvg_flavors.ipynb` and `scripts/generate_hvg_flavor_configs.py`. See `research_log_2026-05-04.txt` for the four design decisions and their justification.",
        "",
        "## Counts",
        "",
        f"- Trained models: {n_trained_models} ({n_train_scgen} scGen + {n_train_impact} IMPACT_CellOT). No Normal CellOT, no monocyte groups.",
        f"- Sbatch scripts: {n_total_sbatch} ({n_train_scgen} train scGen + {n_train_impact} train IMPACT + {n_eval_scgen} eval scGen + {n_eval_impact} eval IMPACT).",
        f"- Dataset files: {n_dataset_files} (one combined file per (flavor, group); shared between scGen and IMPACT and between IID and OOD modes; the IID/OOD split happens at training time via `datasplit.name=toggle_ood`).",
        "",
        "## Axes",
        "",
        "- HVG flavors: " + ", ".join(f"`{f}`" for f in FLAVORS),
        "- Holdout groups:",
    ]
    for gk, g in GROUPS.items():
        lines.append(f"  - **{gk.upper()}** = `{g['name']}` ({g['label']}): holdout = [{', '.join(g['holdout'])}]")
    lines += [
        "- Modes: `ood`, `iid` (toggle_ood semantics; eval set fixed across modes).",
        "- Models: `scgen`, `impact_cellot` (no `cellot` / Normal CellOT in this matrix).",
        "",
        "## Per-flavor HVG input layer",
        "",
        "| flavor | input layer | requires raw counts |",
        "|---|---|---|",
    ]
    for f in FLAVORS:
        layer, raw = FLAVOR_INPUT[f]
        lines.append(f"| `{f}` | `{layer}` | {raw} |")

    lines += [
        "",
        "## Flavor row counts",
        "",
    ]
    for f in FLAVORS:
        lines.append(f"- `{f}`: {flavor_counts[f]} rows (4 groups x 2 modes x 2 models)")

    lines += [
        "",
        "## First 12 rows (preview)",
        "",
        "| flavor | group | mode | model | data file | result dir |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows[:12]:
        lines.append(
            f"| `{r['flavor']}` | {r['group']} | {r['mode']} | {r['model_label']} | "
            f"`{r['data_file']}` | `{r['result_dir']}` |"
        )

    lines += [
        "",
        "Full matrix is in `hvg_flavor_run_matrix.csv`.",
        "",
    ]

    md_path.write_text("\n".join(lines))
    print(f"wrote {md_path}")


if __name__ == "__main__":
    main()

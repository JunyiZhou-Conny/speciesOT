#!/usr/bin/env python3
"""Compare Bunne paper source data (species.csv) vs local paper_crossspecies replication.

Usage:
    python speciesOT/baseline/analysis/compare_paper_replication.py \\
        --paper-csv ~/Desktop/species.csv

Fair comparisons:
  - Paper `r2-means` ↔ replication `evals.csv` metric `r2-means` at nfeatures=50 (NOT r_mean_all_genes)
  - Paper `mmd` ↔ replication `mmd` at nfeatures=50, ncells=1000

Fig 4f top panel is labeled "all genes" in the caption; species.csv likely stores the
evaluate.py bootstrap table (often 50-marker slice when --n_markers 50). The notebook's
`r_mean_all_genes` is a separate post-hoc metric — do not compare it to species.csv.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]  # .../speciesOT/speciesOT
DEFAULT_PAPER_CSV = Path.home() / "Desktop" / "species.csv"
DEFAULT_REPL_HEADLINE = (
    REPO / "speciesOT/baseline/analysis/paper_crossspecies_fig4_outputs/headline_metrics.csv"
)
RESULTS = REPO / "cellot/cellot_gpu/results"

MODEL_MAP = {"cellot": "impact_cellot", "scgen": "scgen", "cae": "cae"}
HEADLINE_MODEL = {"cellot": "CellOT", "scgen": "scGen", "cae": "cAE"}
FIG4_HOLDOUTS = ("rat", "mouse")
FIG4_MODELS = ("cellot", "scgen", "cae")


def stats(vals: list[float]) -> tuple[float, float, int]:
    n = len(vals)
    m = sum(vals) / n
    var = sum((x - m) ** 2 for x in vals) / n
    return m, math.sqrt(var), n


def load_paper(path: Path) -> dict[tuple, tuple[float, float, int]]:
    groups: dict[tuple, list[float]] = defaultdict(list)
    with path.open() as f:
        for row in csv.DictReader(f):
            if row.get("experiment") != "species-ood":
                continue
            key = (row["holdout"], row["mode"], row["model"], row["metric"])
            groups[key].append(float(row["value"]))
    return {k: stats(v) for k, v in groups.items()}


def load_replication_headline(path: Path) -> dict[tuple, dict[str, float]]:
    out: dict[tuple, dict[str, float]] = {}
    if not path.exists():
        return out
    with path.open() as f:
        for row in csv.DictReader(f):
            key = (row["holdout"], row["setting"], row["model"])
            out[key] = row
    return out


def load_replication_evals(tag: str, model: str, setting: str) -> dict[tuple, tuple[float, float, int]]:
    """Read evals_*_data_space_paper/evals.csv if present on disk."""
    eval_path = (
        RESULTS / tag / model / f"evals_{setting}_data_space_paper" / "evals.csv"
    )
    groups: dict[tuple, list[float]] = defaultdict(list)
    if not eval_path.exists():
        return {}
    with eval_path.open() as f:
        for row in csv.DictReader(f):
            if row["ncells"] != "1000":
                continue
            nf = row["nfeatures"]
            if nf not in ("50", "all"):
                continue
            key = (row["metric"], nf)
            groups[key].append(float(row["value"]))
    return {k: stats(v) for k, v in groups.items()}


def print_config_diff_checklist() -> None:
    print("\n" + "=" * 72)
    print("PREPROCESSING / PIPELINE DIFF CHECKLIST (paper vs your replication)")
    print("=" * 72)
    items = [
        (
            "HIGH",
            "Input matrix",
            "Paper: ETH bundle h5ad (10.3929/ethz-b-000609681). "
            "Yours: re-prep from 6619-gene backup via prep_data.py (research_log 2026-06-13; ETH not used).",
        ),
        (
            "HIGH",
            "HVG gene list",
            "prep_data.py re-runs scanpy highly_variable_genes(seurat, n=1000) on full 62k cells. "
            "Paper HVG set may differ even with same recipe if input matrix differs.",
        ),
        (
            "HIGH",
            "Top-50 DE genes (MMD + eval r2-means)",
            "prep_data.py rebuilds Wilcoxon rank_genes_groups → varm marker_genes-condition-rank. "
            "Different ranks → different 50-gene slice → both r and MMD shift.",
        ),
        (
            "MEDIUM",
            "Holdout 50/50 split",
            "Original crossspecies-ood.yaml: no stratify. "
            "Your setup.py adds stratify: condition (balances unst/LPS6 in holdout half).",
        ),
        (
            "MEDIUM",
            "CellOT training iters",
            "Paper default cellot.yaml: 100k. Your replication: 250k (setup.py).",
        ),
        (
            "MEDIUM",
            "batch_size",
            "Original crossspecies-ood.yaml: 128. Replication: 256.",
        ),
        (
            "LOW",
            "Eval subsample seed",
            "evaluate.py uses .sample(ncells) without random_state; "
            "paper_r2_all_genes uses random_state=r. Affects rep variance, not mean much.",
        ),
        (
            "METRIC",
            "r_mean_all_genes in notebook 23",
            "Post-hoc Pearson r on ALL 1000 HVGs — NOT in species.csv. "
            "Compare species.csv r2-means to evals.csv nfeatures=50 instead.",
        ),
    ]
    for sev, title, detail in items:
        print(f"\n[{sev}] {title}\n  {detail}")


def print_investigation_steps() -> None:
    print("\n" + "=" * 72)
    print("RECOMMENDED INVESTIGATION STEPS (in order)")
    print("=" * 72)
    steps = [
        "1. Align metrics: compare paper r2-means/mmd to evals.csv (50 genes, ncells=1000), "
        "not headline r_mean_all_genes.",
        "2. Obtain ETH h5ad (or ask authors) and diff var_names + marker rank varm against your h5ad.",
        "3. Re-run ONE rat OOD model with original crossspecies-ood.yaml (no stratify, batch 128, cellot 100k iters).",
        "4. Re-run eval only on frozen imputed.h5ad from paper (if available) to isolate preprocessing vs training.",
        "5. Diff OOD cell barcodes: toggle_ood with vs without stratify: condition on same h5ad.",
    ]
    for s in steps:
        print(f"  {s}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--paper-csv", type=Path, default=DEFAULT_PAPER_CSV)
    ap.add_argument("--repl-headline", type=Path, default=DEFAULT_REPL_HEADLINE)
    args = ap.parse_args()

    if not args.paper_csv.exists():
        raise SystemExit(f"Paper CSV not found: {args.paper_csv}")

    paper = load_paper(args.paper_csv)
    headline = load_replication_headline(args.repl_headline)

    print("=" * 72)
    print("FIG 4 METRIC ALIGNMENT: species.csv (paper) vs replication")
    print("=" * 72)
    print(f"Paper source: {args.paper_csv}")
    print(f"Replication headline: {args.repl_headline} (exists={args.repl_headline.exists()})")
    print()
    print(
        f"{'holdout':<7} {'mode':<4} {'model':<7} {'metric':<10} "
        f"{'paper_mean':>10} {'repl_50g':>10} {'repl_allg':>10} {'Δ(50g)':>8}  notes"
    )
    print("-" * 95)

    tags = {"rat": "paper_crossspecies_rat_ood", "mouse": "paper_crossspecies_mouse_ood"}

    for holdout in FIG4_HOLDOUTS:
        for mode in ("ood", "iid"):
            for model in FIG4_MODELS:
                repl_model = MODEL_MAP[model]
                tag = tags[holdout]
                evals = load_replication_evals(tag, repl_model, mode)

                for metric in ("r2-means", "mmd"):
                    pk = (holdout, mode, model, metric)
                    if pk not in paper:
                        continue
                    pm, ps, pn = paper[pk]

                    repl_50 = evals.get((metric, "50"), (float("nan"), float("nan"), 0))[0]
                    repl_all = evals.get((metric, "all"), (float("nan"), float("nan"), 0))[0]

                    # Fall back to headline CSV for 50-gene metrics
                    hk = (holdout, mode, HEADLINE_MODEL.get(model, model))
                    if math.isnan(repl_50) and hk in headline:
                        if metric == "r2-means":
                            repl_50 = float(headline[hk].get("r_mean_50_markers", "nan"))
                        elif metric == "mmd":
                            repl_50 = float(headline[hk].get("mmd_50_markers", "nan"))

                    delta = repl_50 - pm if not math.isnan(repl_50) else float("nan")
                    notes = ""
                    if hk in headline and metric == "r2-means":
                        rag = float(headline[hk].get("r_mean_all_genes", "nan"))
                        if not math.isnan(rag):
                            notes = f"all-genes r={rag:.3f} (≠ paper col)"

                    print(
                        f"{holdout:<7} {mode:<4} {model:<7} {metric:<10} "
                        f"{pm:10.4f} {repl_50:10.4f} {repl_all:10.4f} {delta:8.4f}  {notes}"
                    )

    print("\n" + "-" * 95)
    print("Rat OOD CellOT — your visual read vs sources:")
    pk_r = paper.get(("rat", "ood", "cellot", "r2-means"), (None, None, None))
    pk_m = paper.get(("rat", "ood", "cellot", "mmd"), (None, None, None))
    hk = ("rat", "ood", "CellOT")
    h = headline.get(hk, {})
    print(f"  Eyeball from figure:     r²≈0.65,  MMD≈0.22")
    if pk_r[0] is not None:
        print(f"  Paper species.csv:       r2-means={pk_r[0]:.4f}, MMD={pk_m[0]:.4f}")
    if h:
        print(
            f"  Your headline_metrics:   r_50={float(h.get('r_mean_50_markers', 'nan')):.4f}, "
            f"MMD_50={float(h.get('mmd_50_markers', 'nan')):.4f}, "
            f"r_all={float(h.get('r_mean_all_genes', 'nan')):.4f}"
        )

    eval_path = RESULTS / tags["rat"] / "impact_cellot" / "evals_ood_data_space_paper/evals.csv"
    print(f"\n  Raw evals.csv on disk:   {eval_path} (exists={eval_path.exists()})")

    print_config_diff_checklist()
    print_investigation_steps()


if __name__ == "__main__":
    main()

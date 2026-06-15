"""Summarize paper cross-species replication metrics into a markdown table.

USAGE (from cellot_gpu/):
    python paper_crossspecies/scripts/collect_results.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CELLOT = Path(__file__).resolve().parents[2]
RESULTS = CELLOT / "results"
TAGS = ["paper_crossspecies_rat_ood", "paper_crossspecies_mouse_ood"]
MODELS = ["scgen", "impact_cellot"]


def _headline_eval(eval_dir: Path) -> dict:
    row = {"r2_means_ood": None, "mmd_ood": None, "r2_means_iid": None, "mmd_iid": None}
    for setting in ("ood", "iid"):
        csv = eval_dir / f"evals_{setting}_data_space_paper" / "evals.csv"
        if not csv.exists():
            continue
        df = pd.read_csv(csv)
        sub = df[(df["metric"] == "r2-means") & (df["ncells"] == 1000)]
        if len(sub):
            row[f"r2_means_{setting}"] = float(sub["value"].mean())
        sub_m = df[(df["metric"] == "mmd") & (df["ncells"] == 1000)]
        if len(sub_m):
            row[f"mmd_{setting}"] = float(sub_m["value"].mean())
    ext = eval_dir / "evals_ood_data_space_paper" / "extended_metrics.csv"
    if ext.exists():
        em = pd.read_csv(ext)
        nc = em[em["ncells"] == 1000].iloc[0]
        row.update({
            "mmd_floor": nc.get("mmd_floor"),
            "mmd_ceiling": nc.get("mmd_ceiling"),
            "frac_gap_closed": nc.get("frac_gap_closed"),
            "frac_r2_closed": nc.get("frac_r2_closed"),
        })
    return row


def main() -> None:
    rows = []
    for tag in TAGS:
        holdout = "rat" if "rat" in tag else "mouse"
        for model in MODELS:
            eval_dir = RESULTS / tag / model
            if not eval_dir.exists():
                continue
            stats = _headline_eval(eval_dir)
            rows.append({"holdout": holdout, "model": model, **stats})
    if not rows:
        print("[collect-paper] no eval artifacts found yet")
        return
    df = pd.DataFrame(rows)
    print(df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    main()

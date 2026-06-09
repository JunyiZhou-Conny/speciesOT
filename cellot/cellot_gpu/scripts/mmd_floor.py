"""Compute the "MMD floor" (self-MMD) for a trained model's eval and compare it
to the model's reported MMD.

WHY
---
The eval (`scripts/evaluate.py`) reports MMD between the real target cells
(`treated`) and the model's predictions (`imputed`), computed on subsamples of
size `ncells`, averaged over reps, with `gammas = np.logspace(1, -3, num=50)`.

Even a perfect model cannot reach MMD = 0: the MMD between two finite samples of
the SAME distribution is strictly positive. That irreducible value is the
**MMD floor**. We estimate it by split-half sampling the real `treated` cells
(half A vs half B), at the SAME `ncells` and the SAME `gammas` the eval uses, so
the two numbers are directly comparable. A good model's MMD approaches the floor;
the gap above the floor is the meaningful error.

This script is intentionally standalone — it reuses `load_conditions`'s inputs to
get the exact `treated` cells but never re-runs or modifies the eval.

USAGE
-----
    python scripts/mmd_floor.py \
        --outdir ./results/hvg_pearson_residuals_m2_ood/impact_cellot \
        --setting ood --where data_space --embedding ae \
        --n_cells 30,50,80 --evalprefix evals_ood_data_space

Writes `<outdir>/<evalprefix>/mmd_floor.csv` and prints a model-vs-floor table.
"""

from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from cellot.utils import load_config
from cellot.utils.evaluate import load_all_inputs
from cellot.losses.mmd import compute_mmd_floor


def get_treated(expdir: Path, setting: str, where: str, embedding):
    """Return the real ground-truth target cells (`treated`) as an ndarray, in the
    same space the eval used. Mirrors the head of `load_conditions` but skips
    loading the transport model (we only need `treated`)."""
    config = load_config(expdir / "config.yaml")
    # Same ae_emb redirect load_conditions applies, so the dataset/space matches.
    if "ae_emb" in config.data:
        config.data.ae_emb.path = str(expdir.parent / "model-scgen")

    _, treated, _, _, _ = load_all_inputs(config, setting, embedding, where)
    return treated


def model_mmd_by_ncells(eval_dir: Path) -> pd.DataFrame:
    """Aggregate the model's reported MMD per ncells from evals.csv."""
    df = pd.read_csv(eval_dir / "evals.csv")
    mmd = df[df["metric"] == "mmd"].copy()
    mmd["ncells"] = mmd["ncells"].astype(int)
    return (
        mmd.groupby("ncells")["value"]
        .agg(model_mmd_mean="mean", model_mmd_std="std", reps="count")
        .reset_index()
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir", required=True, help="model directory (the expdir)")
    ap.add_argument("--setting", default="ood", choices=["iid", "ood"])
    ap.add_argument("--where", default="data_space",
                    choices=["data_space", "latent_space"])
    ap.add_argument("--embedding", default="ae", help="ae | pca | '' (None)")
    ap.add_argument("--n_cells", default="30,50,80",
                    help="comma-separated subsample sizes (mirror the eval)")
    ap.add_argument("--evalprefix", default=None,
                    help="eval subdir name (default: evals_<setting>_<where>)")
    ap.add_argument("--n_reps", type=int, default=10)
    ap.add_argument("--random_state", type=int, default=0)
    args = ap.parse_args()

    embedding = args.embedding or None
    if embedding is not None and len(embedding) == 0:
        embedding = None

    expdir = Path(args.outdir)
    prefix = args.evalprefix or f"evals_{args.setting}_{args.where}"
    eval_dir = expdir / prefix
    if not (eval_dir / "evals.csv").exists():
        raise SystemExit(f"[mmd-floor] no evals.csv at {eval_dir} — run the eval first.")

    ncells_list = [int(x) for x in args.n_cells.split(",")]

    print(f"[mmd-floor] loading treated cells for {expdir} ...", flush=True)
    treated = get_treated(expdir, args.setting, args.where, embedding)
    treated = np.asarray(treated)
    print(f"[mmd-floor] treated pool: {treated.shape[0]} cells x {treated.shape[1]} features",
          flush=True)

    print(f"[mmd-floor] computing floor at ncells={ncells_list}, n_reps={args.n_reps} ...",
          flush=True)
    floor_long = compute_mmd_floor(
        treated, ncells_list, n_reps=args.n_reps, random_state=args.random_state,
    )
    floor = (
        floor_long.groupby("ncells")["mmd_floor"]
        .agg(mmd_floor_mean="mean", mmd_floor_std="std")
        .reset_index()
    )

    model = model_mmd_by_ncells(eval_dir)
    summary = model.merge(floor, on="ncells", how="outer").sort_values("ncells")
    summary["mmd_above_floor"] = summary["model_mmd_mean"] - summary["mmd_floor_mean"]
    summary["mmd_ratio"] = summary["model_mmd_mean"] / summary["mmd_floor_mean"]

    out_csv = eval_dir / "mmd_floor.csv"
    summary.to_csv(out_csv, index=False)

    pd.set_option("display.float_format", lambda v: f"{v:.5f}")
    print(f"\n[mmd-floor] {expdir.parent.name}/{expdir.name}  ({prefix})")
    print(summary.to_string(index=False))
    print(f"\n[mmd-floor] wrote {out_csv}", flush=True)


if __name__ == "__main__":
    main()

"""Compute extended MMD / divergence metrics for a trained model's eval and write
an `extended_metrics.csv` sidecar that the hub reads alongside `evals.csv`.

Metrics (per ncells, at the eval's gammas = logspace(1,-3,50)):
  - mmd_model    : MMD(imputed, treated)              -- the model's discrepancy
  - mmd_floor    : self-MMD of treated (split-half)   -- best achievable
  - mmd_ceiling  : MMD(control, treated)              -- identity / no-transport gap
  - gap_above_floor = mmd_model - mmd_floor
  - frac_gap_closed = (mmd_ceiling - mmd_model) / (mmd_ceiling - mmd_floor)
  - mean_js      : mean per-gene Jensen-Shannon(treated, imputed) marginal divergence

Reuses `eval_clouds.npz` when present (fast, no torch); otherwise reconstructs
control/treated via the eval's `load_all_inputs` path and imputed from
`imputed.h5ad`. Run in the CellOT env, from cellot_gpu/ with PYTHONPATH=.

USAGE:
    PYTHONPATH=. python scripts/extended_metrics.py \
        --outdir ./results/hvg_pearson_residuals_m1_ood/impact_cellot \
        --setting ood --where data_space --embedding ae \
        --evalprefix evals_ood_data_space
"""

from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from cellot.losses import compute_mmd_two_sample, compute_marginal_divergence


def _load_clouds(expdir, setting, where, embedding, eval_dir):
    """Return (treated, imputed, control) arrays. Prefer the cached npz."""
    npz = eval_dir / "eval_clouds.npz"
    if npz.exists():
        z = np.load(npz, allow_pickle=False)
        control = z["control"] if "control" in z.files else None
        return z["treated"], z["imputed"], control

    import anndata as ad
    from cellot.utils import load_config
    from cellot.utils.evaluate import load_all_inputs

    config = load_config(expdir / "config.yaml")
    if "ae_emb" in config.data:
        config.data.ae_emb.path = str(expdir.parent / "model-scgen")
    control, treated, *_ = load_all_inputs(config, setting, embedding, where)
    imp = ad.read_h5ad(str(eval_dir / "imputed.h5ad"))
    X = imp.X
    imputed = np.asarray(X.todense()) if hasattr(X, "todense") else np.asarray(X)
    return np.asarray(treated), imputed, np.asarray(control)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--setting", default="ood", choices=["iid", "ood"])
    ap.add_argument("--where", default="data_space",
                    choices=["data_space", "latent_space"])
    ap.add_argument("--embedding", default="ae")
    ap.add_argument("--evalprefix", default=None)
    ap.add_argument("--n_cells", default="30,50,80")
    ap.add_argument("--n_reps", type=int, default=10)
    ap.add_argument("--random_state", type=int, default=0)
    args = ap.parse_args()

    embedding = args.embedding or None
    if embedding is not None and len(embedding) == 0:
        embedding = None

    expdir = Path(args.outdir)
    prefix = args.evalprefix or f"evals_{args.setting}_{args.where}"
    eval_dir = expdir / prefix
    if not (eval_dir / "imputed.h5ad").exists() and not (eval_dir / "eval_clouds.npz").exists():
        raise SystemExit(f"[extended-metrics] no imputed.h5ad / eval_clouds.npz at {eval_dir}")

    ncells_list = [int(x) for x in args.n_cells.split(",")]
    gammas = np.logspace(1, -3, num=50)

    print(f"[extended-metrics] loading clouds for {expdir} ...", flush=True)
    treated, imputed, control = _load_clouds(expdir, args.setting, args.where, embedding, eval_dir)

    kw = dict(ncells_list=ncells_list, gammas=gammas, n_reps=args.n_reps,
              random_state=args.random_state)
    print("[extended-metrics] computing floor / model / ceiling / JS ...", flush=True)
    floor = compute_mmd_two_sample(treated, split_half=True, **kw)
    model = compute_mmd_two_sample(imputed, treated, **kw)
    ceil = compute_mmd_two_sample(control, treated, **kw) if control is not None else None
    mean_js = compute_marginal_divergence(treated, imputed)["mean_js"]

    # --- R2-of-means floor/ceiling (analog of the MMD floor/ceiling) ---------
    # R2 is mean-based, so the AE-decode distortion that inflates MMD does NOT
    # apply here -> raw-space references are valid. Sign is flipped vs MMD:
    #   r2_self     = BEST achievable: corr^2 of split-half real-target means (~1)
    #   r2_identity = no-transport baseline: corr^2(mean(control), mean(treated))
    #   frac_r2_closed = (r2_model - r2_identity) / (r2_self - r2_identity)
    def _r2_means(A, B):
        a, b = np.asarray(A).mean(0), np.asarray(B).mean(0)
        r = np.corrcoef(a, b)[0, 1]
        return float(r * r)

    _rng = np.random.default_rng(args.random_state)
    _T, _n = np.asarray(treated), len(treated)
    r2_self = float(np.mean([
        _r2_means(_T[perm[:_n // 2]], _T[perm[_n // 2:]])
        for perm in (_rng.permutation(_n) for _ in range(args.n_reps))
    ]))
    r2_model = _r2_means(imputed, treated)
    r2_identity = _r2_means(control, treated) if control is not None else np.nan
    frac_r2 = ((r2_model - r2_identity) / (r2_self - r2_identity)
               if (np.isfinite(r2_identity) and r2_self > r2_identity) else np.nan)

    rows = []
    for nc in ncells_list:
        f = floor[floor["ncells"] == nc]["mmd"].mean()
        m = model[model["ncells"] == nc]["mmd"].mean()
        c = ceil[ceil["ncells"] == nc]["mmd"].mean() if ceil is not None else np.nan
        frac = (c - m) / (c - f) if (np.isfinite(c) and c > f) else np.nan
        rows.append({"ncells": nc, "mmd_model": m, "mmd_floor": f, "mmd_ceiling": c,
                     "gap_above_floor": m - f, "frac_gap_closed": frac, "mean_js": mean_js,
                     "r2_model": r2_model, "r2_self": r2_self, "r2_identity": r2_identity,
                     "frac_r2_closed": frac_r2})

    out = pd.DataFrame(rows)
    dst = eval_dir / "extended_metrics.csv"
    out.to_csv(dst, index=False)
    pd.set_option("display.float_format", lambda v: f"{v:.4f}")
    print(out.to_string(index=False))
    print(f"[extended-metrics] wrote {dst}", flush=True)


if __name__ == "__main__":
    main()

"""Compute MMD / R² floor/ceiling in the *decoded reference frame* for IMPACT-style
evals: round-trip control and treated through the scGen AE, then rebuild
frac_gap_closed and frac_r2_closed with honest references.

Raw-frame metrics (mixed decoded imputed vs raw treated for MMD model) live in
``extended_metrics.csv``. This script writes ``decoded_frame_metrics.csv`` beside
it with one row per ``ncells``.

Decoded MMD references (see docs/concepts/AE round-trip tax.md):
  - mmd_ae_recon_floor : MMD(decode(encode(treated)), treated)
  - mmd_model          : MMD(imputed, treated)  [same scalar as raw sidecar]
  - mmd_decoded_ceiling: MMD(decode(encode(control)), treated)

Decoded R² references (AE eliminated on control/treated means):
  - r2_self_dec     : split-half corr² on decode(encode(treated)) means
  - r2_identity_dec : corr²(mean(dec(control)), mean(dec(treated)))
  - r2_model_dec    : corr²(mean(imputed), mean(dec(treated)))

USAGE (CellOT env, from cellot_gpu/):
    PYTHONPATH=. python scripts/decoded_frame_metrics.py \\
        --outdir ./results/hvg_pearson_residuals_m1_v08_ood/impact_cellot \\
        --setting ood --where data_space --embedding ae \\
        --evalprefix evals_ood_data_space
"""

from pathlib import Path
import argparse

import numpy as np
import pandas as pd

from cellot.losses import compute_mmd_two_sample
from cellot.utils import load_config
from cellot.utils.evaluate import load_projectors


def _load_clouds(expdir, setting, where, embedding, eval_dir):
    npz = eval_dir / "eval_clouds.npz"
    if npz.exists():
        z = np.load(npz, allow_pickle=False)
        control = z["control"] if "control" in z.files else None
        genes = list(z["genes"]) if "genes" in z.files else None
        return z["treated"], z["imputed"], control, genes

    import anndata as ad
    from cellot.utils.evaluate import load_all_inputs

    config = load_config(expdir / "config.yaml")
    if "ae_emb" in config.data:
        config.data.ae_emb.path = str(expdir.parent / "model-scgen")
    control, treated, *_ = load_all_inputs(config, setting, embedding, where)
    imp = ad.read_h5ad(str(eval_dir / "imputed.h5ad"))
    X = imp.X
    imputed = np.asarray(X.todense()) if hasattr(X, "todense") else np.asarray(X)
    genes = [str(g) for g in imp.var_names]
    return np.asarray(treated), imputed, np.asarray(control), genes


def _as_df(X, genes):
    cols = genes if genes is not None else [f"g{i}" for i in range(X.shape[1])]
    return pd.DataFrame(np.asarray(X), columns=cols[: X.shape[1]])


def _roundtrip(X, encode, decode, genes):
    return np.asarray(decode(encode(_as_df(X, genes))).values, dtype=np.float64)


def _r2_means(A, B):
    a, b = np.asarray(A).mean(0), np.asarray(B).mean(0)
    r = np.corrcoef(a, b)[0, 1]
    return float(r * r)


def _split_half_r2(cloud, n_reps, rng):
    cloud = np.asarray(cloud)
    n = len(cloud)
    return float(np.mean([
        _r2_means(cloud[perm[: n // 2]], cloud[perm[n // 2 :]])
        for perm in (rng.permutation(n) for _ in range(n_reps))
    ]))


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
        raise SystemExit(f"[decoded-frame] no imputed.h5ad / eval_clouds.npz at {eval_dir}")

    ncells_list = [int(x) for x in args.n_cells.split(",")]
    gammas = np.logspace(1, -3, num=50)
    kw = dict(ncells_list=ncells_list, gammas=gammas, n_reps=args.n_reps,
              random_state=args.random_state)

    print(f"[decoded-frame] loading clouds for {expdir} ...", flush=True)
    treated, imputed, control, genes = _load_clouds(
        expdir, args.setting, args.where, embedding, eval_dir
    )
    if control is None:
        raise SystemExit("[decoded-frame] control cloud missing (regenerate eval_clouds.npz)")

    config = load_config(expdir / "config.yaml")
    aedir = expdir.parent / "model-scgen"
    if "ae_emb" in config.data:
        config.data.ae_emb.path = str(aedir)

    print(f"[decoded-frame] loading AE from {aedir} ...", flush=True)
    encode, decode = load_projectors(aedir, embedding or "ae", args.where)
    treated_dec = _roundtrip(treated, encode, decode, genes)
    control_dec = _roundtrip(control, encode, decode, genes)

    print("[decoded-frame] computing decoded MMD references ...", flush=True)
    mmd_model = compute_mmd_two_sample(imputed, treated, **kw)
    mmd_ae_recon = compute_mmd_two_sample(treated_dec, treated, **kw)
    mmd_dec_ceiling = compute_mmd_two_sample(control_dec, treated, **kw)

    rng = np.random.default_rng(args.random_state)
    r2_self_dec = _split_half_r2(treated_dec, args.n_reps, rng)
    r2_identity_dec = _r2_means(control_dec, treated_dec)
    r2_model_dec = _r2_means(imputed, treated_dec)
    frac_r2_dec = ((r2_model_dec - r2_identity_dec) / (r2_self_dec - r2_identity_dec)
                   if r2_self_dec > r2_identity_dec else np.nan)

    rows = []
    for nc in ncells_list:
        m = mmd_model[mmd_model["ncells"] == nc]["mmd"].mean()
        f = mmd_ae_recon[mmd_ae_recon["ncells"] == nc]["mmd"].mean()
        c = mmd_dec_ceiling[mmd_dec_ceiling["ncells"] == nc]["mmd"].mean()
        frac = (c - m) / (c - f) if np.isfinite(c) and c > f else np.nan
        rows.append({
            "ncells": nc,
            "mmd_model": m,
            "mmd_ae_recon_floor": f,
            "mmd_decoded_ceiling": c,
            "gap_above_ae_recon": m - f,
            "frac_gap_closed_decoded": frac,
            "r2_model_dec": r2_model_dec,
            "r2_self_dec": r2_self_dec,
            "r2_identity_dec": r2_identity_dec,
            "frac_r2_closed_decoded": frac_r2_dec,
        })

    out = pd.DataFrame(rows)
    dst = eval_dir / "decoded_frame_metrics.csv"
    out.to_csv(dst, index=False)
    pd.set_option("display.float_format", lambda v: f"{v:.4f}")
    print(out.to_string(index=False))
    print(f"[decoded-frame] wrote {dst}", flush=True)


if __name__ == "__main__":
    main()

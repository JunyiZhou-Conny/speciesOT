"""Dump the exact `treated` (real) and `imputed` (predicted) cell clouds for a
trained model's eval into a single .npz, so downstream analysis (e.g. the
gamma-sensitivity notebook) can run in any env with just numpy — no torch / no
cellot machinery / no model reload.

`treated` is reconstructed via the same `load_all_inputs` path the eval uses, so
it is byte-identical to what produced `evals.csv`. `imputed` is read straight
from the eval's saved `imputed.h5ad`.

USAGE (CellOT env, from cellot_gpu/):
    PYTHONPATH=. python scripts/dump_eval_clouds.py \
        --outdir ./results/hvg_pearson_residuals_m2_ood/impact_cellot \
        --setting ood --where data_space --embedding ae \
        --evalprefix evals_ood_data_space

Writes `<outdir>/<evalprefix>/eval_clouds.npz` with arrays `treated`, `imputed`,
`control` (the mouse source; used for the MMD ceiling = MMD(control, treated)),
and `genes` (the gene/var order, for per-gene marginal plots).
"""

from pathlib import Path
import argparse

import numpy as np
import anndata as ad

from cellot.utils import load_config
from cellot.utils.evaluate import load_all_inputs


def get_control_treated(expdir: Path, setting: str, where: str, embedding):
    """Reconstruct (control=mouse source, treated=human target) in the eval's space.

    Both come from the same `load_all_inputs` path the eval uses, so they are
    byte-identical to what produced `evals.csv`. `control` enables the MMD ceiling
    (the identity-baseline / cross-species gap).
    """
    config = load_config(expdir / "config.yaml")
    if "ae_emb" in config.data:
        config.data.ae_emb.path = str(expdir.parent / "model-scgen")
    control, treated, _, _, _ = load_all_inputs(config, setting, embedding, where)
    genes = [str(g) for g in getattr(treated, "columns", [])]
    return np.asarray(control), np.asarray(treated), genes


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--setting", default="ood", choices=["iid", "ood"])
    ap.add_argument("--where", default="data_space",
                    choices=["data_space", "latent_space"])
    ap.add_argument("--embedding", default="ae")
    ap.add_argument("--evalprefix", default=None)
    args = ap.parse_args()

    embedding = args.embedding or None
    if embedding is not None and len(embedding) == 0:
        embedding = None

    expdir = Path(args.outdir)
    prefix = args.evalprefix or f"evals_{args.setting}_{args.where}"
    eval_dir = expdir / prefix
    imputed_h5 = eval_dir / "imputed.h5ad"
    if not imputed_h5.exists():
        raise SystemExit(f"[dump-clouds] no imputed.h5ad at {eval_dir}")

    print(f"[dump-clouds] reconstructing control + treated for {expdir} ...", flush=True)
    control, treated, genes = get_control_treated(expdir, args.setting, args.where, embedding)

    print(f"[dump-clouds] reading imputed.h5ad ...", flush=True)
    imp = ad.read_h5ad(str(imputed_h5))
    imputed = imp.X
    imputed = np.asarray(imputed.todense()) if hasattr(imputed, "todense") else np.asarray(imputed)
    if not genes:
        genes = [str(g) for g in imp.var_names]

    out = eval_dir / "eval_clouds.npz"
    np.savez_compressed(out, treated=treated.astype(np.float32),
                        imputed=imputed.astype(np.float32),
                        control=control.astype(np.float32),
                        genes=np.asarray(genes, dtype="U32"))
    print(f"[dump-clouds] control {control.shape}  treated {treated.shape}  "
          f"imputed {imputed.shape}  genes {len(genes)}", flush=True)
    print(f"[dump-clouds] wrote {out}", flush=True)


if __name__ == "__main__":
    main()

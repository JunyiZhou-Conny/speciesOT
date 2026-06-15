"""Re-save an h5ad with the CellOT env's anndata for compatibility."""

from __future__ import annotations

import argparse
from pathlib import Path

import anndata as ad
import h5py
import numpy as np


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    args = ap.parse_args()
    path = args.path

    # Strip incompatible groups written by newer anndata if present.
    with h5py.File(path, "a") as f:
        for key in ("layers", "raw"):
            if key in f:
                del f[key]
                print(f"[resave] removed /{key}", flush=True)

    try:
        a = ad.read_h5ad(path)
    except Exception:
        # Fallback: read matrix + obs/var from analysis-written file via backed X only
        raise SystemExit("[resave] still cannot read; rebuild from backup with this script")

    X = a.X
    if hasattr(X, "toarray"):
        X = X.toarray()
    clean = ad.AnnData(
        X=np.asarray(X, dtype=np.float32),
        obs=a.obs.copy(),
        var=a.var.copy(),
    )
    for k in a.varm:
        clean.varm[k] = np.asarray(a.varm[k])

    tmp = path.with_suffix(".cellot_tmp.h5ad")
    clean.write_h5ad(tmp)
    ad.read_h5ad(tmp)  # verify
    tmp.replace(path)
    print(f"[resave] wrote compatible {path} shape={clean.shape}", flush=True)


if __name__ == "__main__":
    main()

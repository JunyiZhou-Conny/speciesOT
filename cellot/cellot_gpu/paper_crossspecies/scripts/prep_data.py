"""Build paper-faithful scrna-crossspecies h5ad: 1000 HVG + marker-gene varm.

Source: local 6619-gene ortholog pool (scGen / Hagai preprocessing), typically
``datasets/scrna-crossspecies/hvg-top1k-train-only.h5ad`` before this script runs.

Mirrors Bunne et al. 2023 Online Methods:
  - 1000 highly variable genes (scanpy, training pool only)
  - rank_genes_groups for marker genes (reference = unst control)

USAGE (analysis env recommended):
    python paper_crossspecies/scripts/prep_data.py \\
        --input datasets/scrna-crossspecies/hvg-top1k-train-only.h5ad \\
        --output datasets/scrna-crossspecies/hvg-top1k-train-only.h5ad \\
        --backup
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

import anndata as ad
import numpy as np
import pandas as pd
import scanpy as sc


def _file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _build_marker_rank_varm(adata: ad.AnnData, condition_key: str, reference: str) -> pd.DataFrame:
    """varm['marker_genes-<condition>-rank'] with one column per non-reference group."""
    sc.tl.rank_genes_groups(
        adata,
        groupby=condition_key,
        reference=reference,
        method="wilcoxon",
        use_raw=False,
    )
    groups = [g for g in adata.obs[condition_key].unique() if g != reference]
    varm = pd.DataFrame(index=adata.var_names)
    for group in groups:
        df = sc.get.rank_genes_groups_df(adata, group=group)
        rank_map = {name: i for i, name in enumerate(df["names"].astype(str))}
        varm[group] = [float(rank_map.get(g, len(adata.var_names))) for g in adata.var_names]
    return varm


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--input",
        default="datasets/scrna-crossspecies/hvg-top1k-train-only.h5ad",
        help="6619-gene source h5ad (or existing file to re-process)",
    )
    ap.add_argument(
        "--output",
        default="datasets/scrna-crossspecies/hvg-top1k-train-only.h5ad",
        help="Output path (1000 HVG + marker varm)",
    )
    ap.add_argument("--n-top", type=int, default=1000)
    ap.add_argument("--condition-key", default="condition")
    ap.add_argument("--reference", default="unst")
    ap.add_argument("--backup", action="store_true", help="Backup output path if it exists")
    args = ap.parse_args()

    inp = Path(args.input)
    out = Path(args.output)
    print(f"[prep-crossspecies] loading {inp}", flush=True)
    adata = ad.read_h5ad(inp)
    print(f"[prep-crossspecies] input shape {adata.shape}", flush=True)

    # Drop embedding artifacts not needed for training/eval.
    for key in ("X_pca", "X_umap"):
        if key in adata.obsm:
            del adata.obsm[key]
    for key in list(adata.obsp.keys()):
        del adata.obsp[key]
    if "neighbors" in adata.uns:
        del adata.uns["neighbors"]

    sc.pp.highly_variable_genes(
        adata,
        n_top_genes=args.n_top,
        flavor="seurat",
        subset=False,
    )
    n_hvg = int(adata.var["highly_variable"].sum())
    print(f"[prep-crossspecies] HVG selected: {n_hvg}", flush=True)
    adata = adata[:, adata.var["highly_variable"]].copy()

    varm = _build_marker_rank_varm(adata, args.condition_key, args.reference)
    key = f"marker_genes-{args.condition_key}-rank"
    adata.varm[key] = varm

    print(f"[prep-crossspecies] species x condition:", flush=True)
    print(pd.crosstab(adata.obs["species"], adata.obs[args.condition_key]), flush=True)
    print(f"[prep-crossspecies] varm keys: {list(adata.varm.keys())}", flush=True)

    if out.exists() and args.backup:
        backup = out.with_suffix(out.suffix + ".6619-backup.h5ad")
        if not backup.exists():
            out.rename(backup)
            print(f"[prep-crossspecies] backed up existing file to {backup}", flush=True)

    out.parent.mkdir(parents=True, exist_ok=True)
    # Re-save through CellOT anndata (analysis env writes formats CellOT cannot read).
    import subprocess

    export_npz = out.parent / "_crossspecies_export.npz"
    X = adata.X
    if hasattr(X, "toarray"):
        X = X.toarray()
    np.savez_compressed(export_npz, X=np.asarray(X, dtype=np.float32))
    adata.obs.to_csv(export_npz.with_suffix(".obs.csv"))
    adata.var.to_csv(export_npz.with_suffix(".var.csv"))
    adata.varm[key].to_csv(export_npz.with_suffix(".marker_rank.csv"))
    cellot_py = subprocess.check_output(
        ["conda", "run", "-n", "CellOT", "python", "-c", "import sys; print(sys.executable)"],
        text=True,
    ).strip()
    subprocess.run(
        [cellot_py, str(Path(__file__).parent / "_import_crossspecies_cellot.py")],
        cwd=str(Path(__file__).resolve().parents[1]),
        check=True,
    )
    sha = _file_sha256(out)
    print(f"[prep-crossspecies] wrote {out} shape={adata.shape} sha256={sha}", flush=True)


if __name__ == "__main__":
    main()

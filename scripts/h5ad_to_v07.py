#!/usr/bin/env python3
"""Convert any .h5ad into one the CellOT env (anndata 0.7.6) can read.

WHY THIS EXISTS

The two environments cannot exchange .h5ad files:

    analysis env   anndata 0.12  (scanpy >= 1.12, needed for data prep)
    CellOT env     anndata 0.7.6 (torch 1.11, runs the models and the evals)

A file written by anndata 0.12 fails in the CellOT env with

    AnnDataReadError: ... while reading key '/layers' ...
    KeyError: 'dict'

The cause is not the data. anndata 0.7.6's ``EncodingVersions`` enum knows
exactly one encoding type, ``raw``. Modern anndata tags every group with an
``encoding-type`` -- ``dict``, ``dataframe``, ``categorical``, ``csr_matrix`` --
and 0.7.6 raises a KeyError on the first one it meets. Stripping those
attributes is NOT sufficient: modern anndata also stores string columns as
*categorical groups* (``categories`` + ``codes``), which 0.7.6 tries to read as
a flat dataset and fails on differently.

The approach that does work is to ignore the anndata reader entirely and read
the file with h5py -- which is version-agnostic, since the HDF5 layout is
self-describing -- then rebuild the object and write it with anndata 0.7.

RUN THIS IN THE CellOT ENV (it must be the one doing the writing):

    conda activate CellOT
    python scripts/h5ad_to_v07.py input.h5ad output_v07.h5ad

This logic was previously inlined in phase 2 of scripts/predict_new_input.sh
for the mouse path only. It is factored out here so the human ground-truth path
and anything else can use it too.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from scipy import sparse


def _d(x):
    """h5py hands back bytes for strings; decode them."""
    return x.decode() if isinstance(x, (bytes, np.bytes_)) else x


def _decode_array(arr):
    if arr.dtype.kind in ("O", "S"):
        return np.array([_d(x) for x in arr])
    return arr


def _read_frame(group):
    """Rebuild a DataFrame from either the modern or the legacy h5 layout."""
    index_key = _d(group.attrs["_index"]) if "_index" in group.attrs else "index"
    index = [_d(x) for x in group[index_key][:]]

    columns = {}
    for name in group.keys():
        if name == index_key:
            continue
        node = group[name]
        # Modern anndata stores strings AND categoricals as a group of
        # categories + codes. This is the case attribute-stripping cannot fix.
        if isinstance(node, h5py.Group) and "categories" in node and "codes" in node:
            categories = [_d(c) for c in node["categories"][:]]
            columns[name] = pd.Categorical.from_codes(node["codes"][:], categories=categories)
        elif isinstance(node, h5py.Group):
            print(f"  [warn] skipping /{group.name}/{name}: unsupported group layout "
                  f"({list(node.keys())})", file=sys.stderr)
        else:
            columns[name] = _decode_array(node[:])

    # Preserve the original column order where anndata recorded it.
    order = group.attrs.get("column-order")
    if order is not None:
        order = [_d(c) for c in order]
        columns = {c: columns[c] for c in order if c in columns}

    return pd.DataFrame(columns, index=pd.Index(index, name=index_key))


def _read_matrix(node):
    """Dense dataset, or a sparse group in either encoding."""
    if isinstance(node, h5py.Group):
        data, indices, indptr = node["data"][:], node["indices"][:], node["indptr"][:]
        shape = node.attrs.get("shape", node.attrs.get("h5sparse_shape"))
        if shape is None:
            raise ValueError(f"sparse group {node.name} has no shape attribute")
        shape = tuple(int(s) for s in shape)
        encoding = _d(node.attrs.get("encoding-type", "csr_matrix"))
        cls = sparse.csc_matrix if "csc" in str(encoding) else sparse.csr_matrix
        return cls((data, indices, indptr), shape=shape)
    return node[:]


def convert(src: Path, dst: Path, keep_layers: bool = False) -> None:
    import anndata as ad

    if ad.__version__ >= "0.8":
        print(
            f"[h5ad-to-v07] WARNING: this interpreter has anndata {ad.__version__}. "
            "The output is only readable by anndata 0.7 if it is WRITTEN by "
            "anndata 0.7 -- run this in the CellOT env.",
            file=sys.stderr,
        )

    with h5py.File(src, "r") as f:
        obs = _read_frame(f["obs"])
        var = _read_frame(f["var"])
        X = _read_matrix(f["X"])
        layers = {}
        if keep_layers and "layers" in f:
            for name in f["layers"].keys():
                layers[name] = _read_matrix(f["layers"][name])

    adata = ad.AnnData(X=X, obs=obs, var=var)
    for name, matrix in layers.items():
        adata.layers[name] = matrix

    dst = Path(dst)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        os.remove(dst)
    adata.write(dst)

    print(f"[h5ad-to-v07] {src}")
    print(f"[h5ad-to-v07]   -> {dst}")
    print(f"[h5ad-to-v07]   shape={adata.shape} obs={list(adata.obs.columns)} "
          f"var={list(adata.var.columns)} layers={list(adata.layers)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path, help="input .h5ad (any anndata version)")
    ap.add_argument("dst", type=Path, help="output .h5ad readable by anndata 0.7")
    ap.add_argument("--keep-layers", action="store_true",
                    help="carry .layers across (dropped by default; the evals read .X)")
    args = ap.parse_args()

    if not args.src.exists():
        print(f"[h5ad-to-v07] input not found: {args.src}", file=sys.stderr)
        return 1
    convert(args.src, args.dst, keep_layers=args.keep_layers)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

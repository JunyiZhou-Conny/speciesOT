#!/usr/bin/env python
"""19 — Uncapped CD8-OOD data prep (pearson_residuals flavor).

Mirrors notebook 01.5 for the (pearson_residuals, group=a) cell, but reads from
the FULL atlas files (tabula_*_all.h5ad) instead of the upstream-capped
sampled_*_shared.h5ad. The only difference vs the existing
hvg_pearson_residuals_a baseline is the absence of the per-cell-type 1000-cap
applied in tabula_make_samples.ipynb.

Pipeline:
  1. Load tabula_muris_all.h5ad and tabula_sapiens_all.h5ad; promote .raw -> .X (raw counts).
  2. BioMart ortholog alignment (uses the cached table; no network needed).
  3. NO assay filter (matches 01.5).
  4. Match by (cell_type_ontology_term_id, tissue_ontology_term_id) 1:1 per identity.
  5. Concat, snapshot raw counts to .layers['counts'], normalize_total + log1p -> .X.
  6. HVG via pearson_residuals on .layers['counts'] with batch_key='species',
     computed on the non-CD8 subset (toggle_ood will hold CD8 out at training).
  7. Subset matched_full to top 1000 HVG (keeps CD8 cells in the file).
  8. clean_adata -> hvg_pearson_residuals_a_uncapped.h5ad.
  9. Round-trip via the CellOT env -> hvg_pearson_residuals_a_uncapped_v07.h5ad.

Outputs:
  - cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_a_uncapped.h5ad
  - cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_a_uncapped_v07.h5ad
  - speciesOT/baseline/analysis/uncapped_outputs/before_after_summary.csv
  - speciesOT/baseline/analysis/uncapped_outputs/per_celltype_counts.csv
  - speciesOT/baseline/analysis/uncapped_outputs/per_celltype_counts_comparison.png
"""

import os
import sys
import time
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import anndata as ad
import scanpy as sc
import scipy.sparse as sp_sparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/speciesOT")
from speciesot_helpers import (
    fetch_human_mouse_one2one_orthologs,
    subset_matched_adatas_by_ortholog_table,
    match_cells_by_celltype_tissue,
)

BASE_DIR = Path("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT")

# Full (uncapped) atlas files — these are the upstream of sampled_*_shared.h5ad
MOUSE_ALL = Path("/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_muris/tabula_muris_all.h5ad")
HUMAN_ALL = Path("/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_sapiens/tabula_sapiens_all.h5ad")

# Capped baseline files — used only for the before/after summary
MOUSE_CAPPED = Path("/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_muris/sampled_mouse_shared.h5ad")
HUMAN_CAPPED = Path("/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_sapiens/sampled_human_shared.h5ad")

DATASET_DIR = BASE_DIR / "cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg"
OUT_DIR = BASE_DIR / "speciesOT/baseline/analysis/uncapped_outputs"
ORTHO_CACHE = BASE_DIR / "scripts/.biomart_ortholog_cache.csv"
CELLOT_PY = "/n/home01/jzhou1125/.conda/envs/CellOT/bin/python"

CT_COL = "cell_type_ontology_term_id"
TISSUE_COL = "tissue_ontology_term_id"
N_HVG = 1000
RANDOM_STATE = 0

GROUP_KEY = "a"
GROUP_NAME = "cd8"
HOLDOUT_IDS = ["CL:0000625"]
FLAVOR = "pearson_residuals"

KEEP_OBS = [
    "condition",
    "species",
    "cell_type_ontology_term_id",
    "cell_type",
    "tissue_ontology_term_id",
    "tissue",
    "donor_id",
]

OUT_DIR.mkdir(parents=True, exist_ok=True)
DATASET_DIR.mkdir(parents=True, exist_ok=True)


def t(stage: str, t0: float) -> float:
    now = time.time()
    print(f"[{now - t0:7.1f}s] {stage}", flush=True)
    return now


def load_raw_atlas_backed(path: Path, label: str):
    """Open tabula_*_all.h5ad in backed mode (does not materialize .X).
    Returns the AnnData object; .obs and .var are loaded eagerly, .X is lazy.
    Caller is responsible for closing via `a.file.close()`."""
    print(f"  opening (backed) {label}: {path}", flush=True)
    a = sc.read_h5ad(str(path), backed="r")
    print(f"    backed shape {a.shape}", flush=True)
    return a


def read_obs_columns_h5(path: Path, cols: list[str], label: str) -> pd.DataFrame:
    """Read specific obs columns from an h5ad file using plain h5py.
    Handles AnnData's categorical encoding (codes + categories) and string arrays.
    Returns a DataFrame with the requested columns and a positional index.
    Avoids anndata's eager-load of all of obs, which is the OOM trigger for the
    45GB tabula_sapiens_all.h5ad."""
    import h5py
    print(f"  reading obs[{cols}] from {label}: {path}", flush=True)
    out = {}
    n_rows = None
    with h5py.File(str(path), "r") as f:
        gobs = f["obs"]
        # Determine row count from any column or from indexed _index
        for col in cols:
            if col not in gobs:
                raise KeyError(f"{label}: obs has no column {col!r}; available: {list(gobs.keys())}")
            node = gobs[col]
            if isinstance(node, h5py.Group) and "categories" in node and "codes" in node:
                codes = node["codes"][:]
                cats_raw = node["categories"][:]
                cats = np.array([c.decode() if isinstance(c, (bytes, np.bytes_)) else c for c in cats_raw])
                # -1 codes are NA; map to "" so downstream str-cast doesn't crash
                arr = np.where(codes >= 0, cats[np.maximum(codes, 0)], "")
                out[col] = arr
                n_rows = len(codes) if n_rows is None else n_rows
            else:
                arr = node[:]
                if arr.dtype.kind in ("O", "S"):
                    arr = np.array([x.decode() if isinstance(x, (bytes, np.bytes_)) else x for x in arr])
                out[col] = arr
                n_rows = len(arr) if n_rows is None else n_rows
    df = pd.DataFrame(out, index=pd.RangeIndex(n_rows, name="row"))
    print(f"    {label}: obs subset rows={len(df)}, cols={list(df.columns)}", flush=True)
    return df


def read_full_obs_h5(path: Path, label: str, row_idx: np.ndarray) -> pd.DataFrame:
    """Read the FULL obs DataFrame from an h5ad file using h5py, restricted to row_idx.
    Same encoding handling as read_obs_columns_h5. Returns a DataFrame indexed by
    the original obs index strings (preserves cell barcodes)."""
    import h5py
    row_idx_sorted = np.sort(row_idx)
    inv = np.argsort(np.argsort(row_idx))
    out = {}
    index_arr = None
    with h5py.File(str(path), "r") as f:
        gobs = f["obs"]
        idx_key = gobs.attrs.get("_index", None)
        if isinstance(idx_key, (bytes, np.bytes_)):
            idx_key = idx_key.decode()
        idx_key = idx_key or "_index"
        # Read the index for the row subset
        if idx_key in gobs:
            idx_raw = gobs[idx_key][:]
            if idx_raw.dtype.kind in ("O", "S"):
                idx_arr_full = np.array([x.decode() if isinstance(x, (bytes, np.bytes_)) else x for x in idx_raw])
            else:
                idx_arr_full = idx_raw
            index_arr = idx_arr_full[row_idx]
        else:
            index_arr = np.array([str(i) for i in row_idx])

        for col in gobs.keys():
            if col == idx_key:
                continue
            node = gobs[col]
            if isinstance(node, h5py.Group) and "categories" in node and "codes" in node:
                codes_full = node["codes"][:]
                cats_raw = node["categories"][:]
                cats = np.array([c.decode() if isinstance(c, (bytes, np.bytes_)) else c for c in cats_raw])
                codes = codes_full[row_idx]
                arr = np.where(codes >= 0, cats[np.maximum(codes, 0)], "")
                out[col] = arr
            else:
                arr_full = node[:]
                if arr_full.dtype.kind in ("O", "S"):
                    arr_full = np.array([x.decode() if isinstance(x, (bytes, np.bytes_)) else x for x in arr_full])
                out[col] = arr_full[row_idx]
    df = pd.DataFrame(out, index=pd.Index(index_arr, name=idx_key))
    print(f"  {label}: read full obs subset, shape={df.shape}", flush=True)
    return df


def materialize_raw_subset_from_path(path: Path, row_idx: np.ndarray,
                                     obs_sub: pd.DataFrame, label: str) -> ad.AnnData:
    """Materialize .raw.X for a row subset of an h5ad file using h5py directly.

    Reads the CSR `.raw/X/{data,indices,indptr}` chunks only for the requested rows.
    Returns an in-memory AnnData with .X = raw counts (float32, sparse).
    Carries the supplied obs_sub (must already be row-aligned to row_idx) and the
    file's .raw/var index as var_names.
    """
    import h5py
    from scipy import sparse

    n_rows = len(row_idx)
    obs_idx_array = np.asarray(row_idx, dtype=np.int64)
    obs_idx_sorted = np.sort(obs_idx_array)
    sort_order = np.argsort(obs_idx_array)
    inverse = np.empty_like(sort_order)
    inverse[sort_order] = np.arange(n_rows)

    with h5py.File(str(path), "r") as f:
        if "raw" not in f or "X" not in f["raw"]:
            raise RuntimeError(f"{label}: file has no .raw/X group at {path}")
        rawX = f["raw/X"]
        indptr_full = rawX["indptr"][:]
        if "shape" in rawX.attrs:
            n_cols = int(rawX.attrs["shape"][1])
        else:
            raise RuntimeError(f"{label}: raw/X has no shape attr")

        new_indptr = np.zeros(n_rows + 1, dtype=np.int64)
        data_chunks = []
        idx_chunks = []
        for out_pos, src_row in enumerate(obs_idx_sorted):
            start, end = int(indptr_full[src_row]), int(indptr_full[src_row + 1])
            if end > start:
                data_chunks.append(rawX["data"][start:end])
                idx_chunks.append(rawX["indices"][start:end])
            new_indptr[out_pos + 1] = new_indptr[out_pos] + (end - start)
        data_all = np.concatenate(data_chunks).astype(np.float32) if data_chunks else np.zeros(0, dtype=np.float32)
        idx_all = np.concatenate(idx_chunks).astype(np.int32) if idx_chunks else np.zeros(0, dtype=np.int32)
        X_sorted = sparse.csr_matrix((data_all, idx_all, new_indptr.astype(np.int32)),
                                     shape=(n_rows, n_cols))
        X = X_sorted[inverse, :]

        # Read .raw/var/_index for var_names
        vgrp = f["raw/var"]
        idx_key = vgrp.attrs.get("_index", b"_index")
        if isinstance(idx_key, (bytes, np.bytes_)):
            idx_key = idx_key.decode()
        if idx_key in vgrp:
            var_names = np.array([x.decode() if isinstance(x, (bytes, np.bytes_)) else x for x in vgrp[idx_key][:]])
        else:
            var_names = np.array([str(i) for i in range(n_cols)])

    out = ad.AnnData(
        X=X.astype(np.float32),
        obs=obs_sub.reset_index(drop=False).set_index(obs_sub.index.name or "index"),
        var=pd.DataFrame(index=pd.Index(var_names, name="ensembl_id")),
    )
    print(f"    {label}: materialized raw subset shape {out.shape}, X mean={float(out.X.mean()):.3f}", flush=True)
    return out


def get_uncapped_pool_stats(mouse_all: ad.AnnData, human_all: ad.AnnData) -> dict:
    return {
        "mouse_uncapped_cells": int(mouse_all.n_obs),
        "mouse_uncapped_genes": int(mouse_all.n_vars),
        "human_uncapped_cells": int(human_all.n_obs),
        "human_uncapped_genes": int(human_all.n_vars),
    }


def get_capped_pool_stats() -> dict:
    """Read just .obs from the capped files (avoid loading 45GB)."""
    out = {}
    for label, path in [("mouse", MOUSE_CAPPED), ("human", HUMAN_CAPPED)]:
        a = sc.read_h5ad(path, backed="r")
        out[f"{label}_capped_cells"] = int(a.n_obs)
        out[f"{label}_capped_genes"] = int(a.n_vars)
        a.file.close()
    return out


def match_pairs(mouse_aligned: ad.AnnData, human_aligned: ad.AnnData):
    """Same call signature as 01.5: no assay filter."""
    return match_cells_by_celltype_tissue(
        mouse_aligned, human_aligned,
        cell_type_key=CT_COL,
        tissue_key=TISSUE_COL,
        seed=RANDOM_STATE,
    )


def build_matched_full(mouse_matched: ad.AnnData, human_matched: ad.AnnData) -> ad.AnnData:
    mouse_m = mouse_matched.copy()
    human_m = human_matched.copy()
    mouse_m.obs["condition"] = "mouse"
    human_m.obs["condition"] = "human"
    matched_full = ad.concat([mouse_m, human_m], join="inner")
    matched_full.obs["species"] = matched_full.obs["condition"].values
    raw_X = matched_full.X
    if sp_sparse.issparse(raw_X):
        assert np.allclose(raw_X.data, np.round(raw_X.data))
        raw_int = raw_X.copy()
        raw_int.data = raw_int.data.astype(np.int32)
    else:
        assert np.allclose(raw_X, np.round(raw_X))
        raw_int = raw_X.astype(np.int32)
    matched_full.layers["counts"] = raw_int
    sc.pp.normalize_total(matched_full, target_sum=1e4)
    sc.pp.log1p(matched_full)
    return matched_full


def run_pearson_hvg(adata: ad.AnnData, n_top: int) -> list[str]:
    """Pearson residuals HVG on .layers['counts'] with batch_key='species'."""
    from scanpy.experimental.pp import highly_variable_genes as hvg_pr
    a = adata.copy()
    L = a.layers["counts"]
    if sp_sparse.issparse(L):
        if L.data.dtype != np.int32:
            L = L.copy()
            L.data = L.data.astype(np.int32)
            a.layers["counts"] = L
    else:
        if L.dtype != np.int32:
            a.layers["counts"] = L.astype(np.int32)
    hvg_pr(a, n_top_genes=n_top, flavor="pearson_residuals",
           batch_key="species", layer="counts")
    score_col = "residual_variances" if "residual_variances" in a.var.columns else "highly_variable_rank"
    df = a.var[["highly_variable"]].copy()
    df["score"] = a.var.get(score_col, np.nan)
    if "highly_variable_rank" in a.var.columns:
        df["rank"] = pd.to_numeric(a.var["highly_variable_rank"], errors="coerce").astype(float)
    else:
        df["rank"] = df["score"].rank(ascending=False, method="min").where(df["highly_variable"]).astype(float)
    hv_genes = df[df["highly_variable"]].sort_values("rank", na_position="last").index.tolist()[:n_top]
    return hv_genes


def clean_adata(adata: ad.AnnData) -> ad.AnnData:
    obs_cols = [c for c in KEEP_OBS if c in adata.obs.columns]
    X = adata.X
    if sp_sparse.issparse(X):
        X = np.array(X.todense())
    elif not isinstance(X, np.ndarray):
        X = np.array(X)
    return ad.AnnData(
        X=X.astype(np.float32),
        obs=adata.obs[obs_cols].copy(),
        var=pd.DataFrame(index=adata.var_names),
    )


def round_trip_via_cellot_env(src: Path) -> Path:
    dst = src.with_name(src.stem + "_v07.h5ad")
    if dst.exists():
        dst.unlink()
    shutil.copy2(str(src), str(dst))
    strip_script = r"""
import sys, h5py
EMPTY = ["layers","obsm","obsp","uns","varm","varp"]
for p in sys.argv[1:]:
    with h5py.File(p, "r+") as f:
        for g in EMPTY:
            if g in f and len(f[g].keys())==0:
                del f[g]
        for a in ("encoding-type","encoding-version"):
            if a in f.attrs:
                del f.attrs[a]
"""
    rewrite_script = r"""
import sys, os, h5py, numpy as np, pandas as pd, anndata as ad
from scipy import sparse
def _d(x): return x.decode() if isinstance(x,(bytes,np.bytes_)) else x
def load_obs(f):
    g = f["obs"]; idx = _d(g.attrs["_index"]) if "_index" in g.attrs else "index"
    index = [_d(x) for x in g[idx][:]]; cols={}
    for n in g.keys():
        if n==idx: continue
        node=g[n]
        if isinstance(node, h5py.Group) and "categories" in node and "codes" in node:
            cats=[_d(c) for c in node["categories"][:]]
            cols[n]=pd.Categorical.from_codes(node["codes"][:], categories=cats)
        else:
            arr=node[:]
            if arr.dtype.kind in ("O","S"):
                arr=np.array([_d(x) for x in arr])
            cols[n]=arr
    return pd.DataFrame(cols, index=pd.Index(index, name=idx))
def load_var(f):
    g = f["var"]; idx = _d(g.attrs["_index"]) if "_index" in g.attrs else "index"
    index = [_d(x) for x in g[idx][:]]
    cols={}
    for n in g.keys():
        if n==idx: continue
        node=g[n]
        arr = node[:]
        if arr.dtype.kind in ("O","S"):
            arr=np.array([_d(x) for x in arr])
        cols[n]=arr
    return pd.DataFrame(cols, index=pd.Index(index, name=idx))
def load_X(f):
    n=f["X"]
    if isinstance(n,h5py.Group):
        d=n["data"][:]; i=n["indices"][:]; p=n["indptr"][:]
        sh=tuple(n.attrs.get("shape", n.attrs.get("h5sparse_shape")))
        e=_d(n.attrs.get("encoding-type", b"csr_matrix"))
        return sparse.csc_matrix((d,i,p),shape=sh) if "csc" in e else sparse.csr_matrix((d,i,p),shape=sh)
    return n[:]
for p in sys.argv[1:]:
    with h5py.File(p,"r") as f:
        obs=load_obs(f); var=load_var(f); X=load_X(f)
    a=ad.AnnData(X=X,obs=obs,var=var)
    os.remove(p); a.write(p)
    print("rewrote",p,"shape",a.shape)
"""
    subprocess.run([CELLOT_PY, "-c", strip_script, str(dst)], check=True)
    subprocess.run([CELLOT_PY, "-c", rewrite_script, str(dst)], check=True)
    return dst


def per_celltype_counts(matched_full: ad.AnnData) -> pd.Series:
    return matched_full.obs["cell_type"].value_counts().rename_axis("cell_type")


def match_obs_only(mouse_obs: pd.DataFrame, human_obs: pd.DataFrame,
                   cell_type_key: str, tissue_key: str, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """Replicate match_cells_by_celltype_tissue's selection logic, but using only obs.
    Returns (mouse_row_idx, human_row_idx) — positional row indices into each original .obs.

    For each shared (cell_type, tissue) identity, keeps min(n_mouse, n_human) cells per side
    (uniformly sampled without replacement when one side has more), per the existing
    helper's semantics.
    """
    rng = np.random.default_rng(seed)

    def _prep(obs: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        ct = obs[cell_type_key].astype(str).to_numpy()
        ti = obs[tissue_key].astype(str).to_numpy()
        keep = ~(pd.isna(obs[cell_type_key]).to_numpy() | pd.isna(obs[tissue_key]).to_numpy())
        pos = np.arange(len(obs))[keep]
        keys = np.char.add(np.char.add(ct[keep], "|"), ti[keep])
        return pos, keys

    m_pos, m_keys = _prep(mouse_obs)
    h_pos, h_keys = _prep(human_obs)

    # Bucket positional indices by key
    def _bucket(pos: np.ndarray, keys: np.ndarray) -> dict[str, np.ndarray]:
        order = np.argsort(keys, kind="stable")
        sorted_keys = keys[order]
        sorted_pos = pos[order]
        uniq, starts = np.unique(sorted_keys, return_index=True)
        ends = np.r_[starts[1:], len(sorted_keys)]
        return {str(k): sorted_pos[s:e] for k, s, e in zip(uniq, starts, ends)}

    mb = _bucket(m_pos, m_keys)
    hb = _bucket(h_pos, h_keys)
    shared = sorted(set(mb.keys()) & set(hb.keys()))
    if not shared:
        return np.array([], dtype=np.int64), np.array([], dtype=np.int64)

    m_picks, h_picks = [], []
    for key in shared:
        am, ah = mb[key], hb[key]
        k = int(min(am.size, ah.size))
        if k <= 0:
            continue
        pm = am if am.size == k else rng.choice(am, size=k, replace=False)
        ph = ah if ah.size == k else rng.choice(ah, size=k, replace=False)
        m_picks.append(pm)
        h_picks.append(ph)
    return (np.concatenate(m_picks) if m_picks else np.array([], dtype=np.int64),
            np.concatenate(h_picks) if h_picks else np.array([], dtype=np.int64))


def main():
    t0 = time.time()
    print(f"=== 19 — Uncapped CD8-OOD data prep ({FLAVOR}, group {GROUP_KEY}/{GROUP_NAME}) ===")
    print(f"  holdout ids: {HOLDOUT_IDS}")
    print(f"  random_state: {RANDOM_STATE}", flush=True)

    capped_stats = get_capped_pool_stats()
    print(f"\nCapped pool (for reference): {capped_stats}", flush=True)

    last = t("Reading obs columns only (h5py-direct) — mouse + human", t0)
    mouse_obs_min = read_obs_columns_h5(MOUSE_ALL, [CT_COL, TISSUE_COL], "mouse")
    human_obs_min = read_obs_columns_h5(HUMAN_ALL, [CT_COL, TISSUE_COL], "human")
    last = t(f"  mouse obs subset: {mouse_obs_min.shape}, human obs subset: {human_obs_min.shape}", last)

    uncapped_stats = {
        "mouse_uncapped_cells": int(len(mouse_obs_min)),
        "human_uncapped_cells": int(len(human_obs_min)),
    }
    print(f"\nUncapped pool (cells): {uncapped_stats}", flush=True)

    last = t("Matching (1:1 per (cell_type, tissue), obs only, no assay filter)", last)
    m_idx, h_idx = match_obs_only(
        mouse_obs_min, human_obs_min,
        cell_type_key=CT_COL, tissue_key=TISSUE_COL, seed=RANDOM_STATE,
    )
    last = t(f"  matched indices: mouse={len(m_idx)}, human={len(h_idx)}", last)
    assert len(m_idx) == len(h_idx), "obs-only matcher should return paired counts"
    if len(m_idx) == 0:
        raise RuntimeError("No matched pairs — check (cell_type, tissue) overlap.")

    # Free the obs-min DataFrames; we'll re-read full obs only for matched rows
    del mouse_obs_min, human_obs_min

    last = t("Reading full obs for matched rows only (h5py-direct)", last)
    mouse_obs_full = read_full_obs_h5(MOUSE_ALL, "mouse", m_idx)
    human_obs_full = read_full_obs_h5(HUMAN_ALL, "human", h_idx)
    last = t(f"  mouse obs full subset: {mouse_obs_full.shape}, human obs full subset: {human_obs_full.shape}", last)

    last = t("Materializing .raw subset for matched cells (h5py-direct)", last)
    mouse_raw_sub = materialize_raw_subset_from_path(MOUSE_ALL, m_idx, mouse_obs_full, "mouse")
    human_raw_sub = materialize_raw_subset_from_path(HUMAN_ALL, h_idx, human_obs_full, "human")
    last = t(f"  mouse_raw_sub: {mouse_raw_sub.shape}, human_raw_sub: {human_raw_sub.shape}", last)

    last = t("BioMart ortholog alignment (cached) on matched subsets", last)
    if not ORTHO_CACHE.exists():
        raise RuntimeError(f"Ortholog cache missing: {ORTHO_CACHE}. Run notebook 15 first.")
    ortho_df = pd.read_csv(ORTHO_CACHE)
    print(f"  cache rows: {len(ortho_df)}", flush=True)
    if "orthology_type" in ortho_df.columns:
        ortho_df = ortho_df[ortho_df["orthology_type"] == "ortholog_one2one"].copy()
        print(f"  one2one only: {len(ortho_df)}", flush=True)
    mouse_matched, human_matched, ortho_used = subset_matched_adatas_by_ortholog_table(
        mouse_raw_sub, human_raw_sub, ortho_df,
    )
    last = t(f"  aligned: mouse {mouse_matched.shape}, human {human_matched.shape}", last)

    last = t("Concat + normalize + log1p (counts in layers)", last)
    matched_full = build_matched_full(mouse_matched, human_matched)
    last = t(f"  matched_full: {matched_full.shape}", last)

    last = t("Per-cell-type counts (matched_full)", last)
    vc_new = per_celltype_counts(matched_full)
    print(vc_new.head(40).to_string(), flush=True)

    last = t(f"HVG (pearson_residuals, top {N_HVG}) on non-CD8 subset", last)
    train_mask = ~matched_full.obs[CT_COL].astype(str).isin(HOLDOUT_IDS)
    hv_genes = run_pearson_hvg(matched_full[train_mask].copy(), n_top=N_HVG)
    last = t(f"  selected {len(hv_genes)} HVG genes (e.g. {hv_genes[:3]} ...)", last)

    last = t("Subset matched_full to top HVG (keeping CD8 cells)", last)
    sub = matched_full[:, hv_genes].copy()
    cleaned = clean_adata(sub)
    out_path = DATASET_DIR / f"hvg_{FLAVOR}_{GROUP_KEY}_uncapped.h5ad"
    cleaned.write_h5ad(out_path)
    last = t(f"  wrote {out_path}: {cleaned.n_obs} cells x {cleaned.n_vars} genes", last)

    last = t("Round-trip via CellOT env -> _v07.h5ad", last)
    v07_path = round_trip_via_cellot_env(out_path)
    last = t(f"  wrote {v07_path}", last)

    # Per-cell-type comparison summary
    summary_rows = []
    for k, v in {**capped_stats, **uncapped_stats}.items():
        summary_rows.append({"stage": k, "value": v})
    summary_rows.append({"stage": "matched_pairs_uncapped", "value": int(mouse_matched.n_obs)})
    summary = pd.DataFrame(summary_rows)
    summary_csv = OUT_DIR / "before_after_summary.csv"
    summary.to_csv(summary_csv, index=False)
    print(f"\nSummary written to {summary_csv}\n{summary.to_string(index=False)}", flush=True)

    # Per-cell-type counts table (and load capped equivalent if available for direct comparison)
    capped_pair_path = DATASET_DIR / "hvg_pearson_residuals_a_v07.h5ad"
    vc_old = None
    if capped_pair_path.exists():
        a_old = sc.read_h5ad(capped_pair_path)
        vc_old = a_old.obs["cell_type"].value_counts().rename_axis("cell_type")
    tbl = pd.DataFrame({"capped_n": vc_old, "uncapped_n": vc_new}).fillna(0).astype(int)
    tbl["delta_uncapped_minus_capped"] = tbl["uncapped_n"] - tbl["capped_n"]
    tbl = tbl.sort_values("uncapped_n", ascending=False)
    tbl_csv = OUT_DIR / "per_celltype_counts.csv"
    tbl.to_csv(tbl_csv)
    print(f"\nPer-cell-type counts written to {tbl_csv}\n{tbl.head(40).to_string()}", flush=True)

    # Plot
    fig, ax = plt.subplots(figsize=(10, max(4, 0.25 * len(tbl))))
    y = np.arange(len(tbl))
    ax.barh(y - 0.2, tbl["capped_n"], height=0.4, label="capped (current)", color="#888")
    ax.barh(y + 0.2, tbl["uncapped_n"], height=0.4, label="uncapped (new)", color="#f2555b")
    ax.set_yticks(y)
    ax.set_yticklabels(tbl.index, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Stacked cell count (mouse + human)")
    ax.set_title(f"Matched-pair counts per cell type — capped vs uncapped\n"
                 f"({FLAVOR}, group {GROUP_KEY}/{GROUP_NAME}, no assay filter)")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig_path = OUT_DIR / "per_celltype_counts_comparison.png"
    fig.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nPlot written to {fig_path}", flush=True)

    last = t(f"DONE — total {(time.time() - t0):.1f}s", t0)


if __name__ == "__main__":
    main()

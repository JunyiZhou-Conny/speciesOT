"""Backed-mode data prep for LARGE atlas sources (the full ``tabula_*_all.h5ad``).

`prep.py`'s default path does a full ``sc.read_h5ad`` of each source — fine for
the ~50k pre-sampled ``sampled_*_shared.h5ad`` files, but it OOMs on the **43 GB**
``tabula_sapiens_all.h5ad``. This module ports the proven backed pipeline from
``speciesOT/baseline/analysis/19_uncapped_cd8_ood_data_prep.py`` (h5py-level obs
reads + CSR-chunk materialization of only the matched cells) and **adds the
enforced assay filter** that notebook 19 lacked.

Triggered by ``spec.source_backed = True``; invoked from ``prep.prep_from_spec``.

Flow:
  1. h5py-read obs[cell_type, tissue, assay] for both species (cheap, no .X).
  2. ENFORCE the assay filter on those obs (keep one platform per species).
  3. Match 1:1 by (cell_type, tissue) on the filtered obs -> original row indices.
  4. h5py-read full obs for matched rows; materialize .raw CSR for matched rows.
  5. BioMart one2one ortholog alignment (cached) on the matched subsets.
  6. concat -> counts layer -> normalize_total -> log1p.
  7. flavor HVG on non-holdout cells; subset; clean; write; round-trip to anndata 0.7.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

# Reuse the in-memory-path helpers + constants so the two prep paths stay aligned.
from speciesOT.hub.prep import (
    PrepError,
    _log,
    _run_hvg_flavor,
    _clean_adata,
    _roundtrip_to_anndata07,
    _verify_output,
    _ASSAY_ALIASES,
    CELLOT_DIR,
    BIOMART_CACHE,
    CT_COL,
    TISSUE_COL,
)


# ---------------------------------------------------------------------------
# h5py-direct readers (ported verbatim from notebook 19 — handle 43GB safely)
# ---------------------------------------------------------------------------

def _read_obs_columns_h5(path: Path, cols: list[str], label: str) -> pd.DataFrame:
    """Read specific obs columns via h5py (categorical-aware), positional index."""
    import h5py
    _log(f"  reading obs{cols} from {label}: {path}")
    out = {}
    n_rows = None
    with h5py.File(str(path), "r") as f:
        gobs = f["obs"]
        for col in cols:
            if col not in gobs:
                raise PrepError(f"{label}: obs has no column {col!r}; available: {list(gobs.keys())}")
            node = gobs[col]
            if isinstance(node, h5py.Group) and "categories" in node and "codes" in node:
                codes = node["codes"][:]
                cats_raw = node["categories"][:]
                cats = np.array([c.decode() if isinstance(c, (bytes, np.bytes_)) else c for c in cats_raw])
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
    _log(f"    {label}: obs subset rows={len(df)}, cols={list(df.columns)}")
    return df


def _read_full_obs_h5(path: Path, label: str, row_idx: np.ndarray) -> pd.DataFrame:
    """Read the FULL obs restricted to row_idx (preserves cell barcodes as index)."""
    import h5py
    out = {}
    index_arr = None
    with h5py.File(str(path), "r") as f:
        gobs = f["obs"]
        idx_key = gobs.attrs.get("_index", None)
        if isinstance(idx_key, (bytes, np.bytes_)):
            idx_key = idx_key.decode()
        idx_key = idx_key or "_index"
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
                out[col] = np.where(codes >= 0, cats[np.maximum(codes, 0)], "")
            else:
                arr_full = node[:]
                if arr_full.dtype.kind in ("O", "S"):
                    arr_full = np.array([x.decode() if isinstance(x, (bytes, np.bytes_)) else x for x in arr_full])
                out[col] = arr_full[row_idx]
    df = pd.DataFrame(out, index=pd.Index(index_arr, name=idx_key))
    _log(f"  {label}: read full obs subset, shape={df.shape}")
    return df


def _materialize_raw_subset(path: Path, row_idx: np.ndarray, obs_sub: pd.DataFrame,
                            label: str):
    """Materialize .raw/X (CSR) for a row subset via h5py — only the matched rows."""
    import h5py
    import anndata as ad
    from scipy import sparse

    n_rows = len(row_idx)
    obs_idx_array = np.asarray(row_idx, dtype=np.int64)
    obs_idx_sorted = np.sort(obs_idx_array)
    sort_order = np.argsort(obs_idx_array)
    inverse = np.empty_like(sort_order)
    inverse[sort_order] = np.arange(n_rows)

    with h5py.File(str(path), "r") as f:
        if "raw" not in f or "X" not in f["raw"]:
            raise PrepError(f"{label}: file has no .raw/X group at {path}")
        rawX = f["raw/X"]
        indptr_full = rawX["indptr"][:]
        if "shape" in rawX.attrs:
            n_cols = int(rawX.attrs["shape"][1])
        else:
            raise PrepError(f"{label}: raw/X has no shape attr")

        new_indptr = np.zeros(n_rows + 1, dtype=np.int64)
        data_chunks, idx_chunks = [], []
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
        obs=obs_sub.copy(),
        var=pd.DataFrame(index=pd.Index(var_names, name="ensembl_id")),
    )
    _log(f"    {label}: materialized raw subset shape {out.shape}")
    return out


def _match_obs_only(mouse_obs, human_obs, cell_type_key, tissue_key, seed):
    """1:1 match by (cell_type, tissue); returns positional indices into each obs."""
    rng = np.random.default_rng(seed)

    def _prep(obs):
        ct = obs[cell_type_key].astype(str).to_numpy()
        ti = obs[tissue_key].astype(str).to_numpy()
        keep = ~(pd.isna(obs[cell_type_key]).to_numpy() | pd.isna(obs[tissue_key]).to_numpy())
        pos = np.arange(len(obs))[keep]
        keys = np.char.add(np.char.add(ct[keep], "|"), ti[keep])
        return pos, keys

    m_pos, m_keys = _prep(mouse_obs)
    h_pos, h_keys = _prep(human_obs)

    def _bucket(pos, keys):
        order = np.argsort(keys, kind="stable")
        sk, sp = keys[order], pos[order]
        uniq, starts = np.unique(sk, return_index=True)
        ends = np.r_[starts[1:], len(sk)]
        return {str(k): sp[s:e] for k, s, e in zip(uniq, starts, ends)}

    mb, hb = _bucket(m_pos, m_keys), _bucket(h_pos, h_keys)
    shared = sorted(set(mb.keys()) & set(hb.keys()))
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


# ---------------------------------------------------------------------------
# Assay filter on a backed obs frame (returns kept original row positions)
# ---------------------------------------------------------------------------

def _assay_keep_positions(obs: pd.DataFrame, allowed_tokens, species_label) -> np.ndarray:
    """Original row positions whose assay is allowed. Empty tokens -> keep all (warn)."""
    n = len(obs)
    if not allowed_tokens:
        _log(f"  WARNING: assay_filter[{species_label}] empty -> keeping all platforms")
        return np.arange(n)
    allowed = set()
    for tok in allowed_tokens:
        allowed |= _ASSAY_ALIASES.get(str(tok), {str(tok)})
    cols = [c for c in ("assay", "assay_ontology_term_id") if c in obs.columns]
    if not cols:
        raise PrepError(f"{species_label}: no assay column to filter on (have {list(obs.columns)})")
    mask = np.zeros(n, dtype=bool)
    for c in cols:
        mask |= obs[c].astype(str).isin(allowed).to_numpy()
    kept = int(mask.sum())
    _log(f"  assay filter [{species_label}]: keep {sorted(allowed_tokens)} -> {kept}/{n} cells")
    if kept == 0:
        seen = sorted(obs[cols[0]].astype(str).unique())[:8]
        raise PrepError(f"{species_label}: assay filter removed ALL cells; {cols[0]} values include {seen}")
    return np.arange(n)[mask]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def prep_backed_from_spec(spec, force: bool = False, keep_intermediate: bool = False) -> Path:
    """Materialize the training .h5ad from a LARGE (backed) atlas source per `spec`."""
    import anndata as ad
    import scanpy as sc
    import scipy.sparse as sp_sparse
    from speciesot_helpers import subset_matched_adatas_by_ortholog_table

    t0 = time.time()

    if not spec.data_file:
        raise PrepError("spec.data_file is empty; cannot determine output path.")
    out_path = (CELLOT_DIR / spec.data_file).resolve()
    if out_path.exists() and not force:
        raise PrepError(f"output already exists: {out_path}\nPass --force to overwrite.")
    if not spec.hvg_method:
        raise PrepError("spec.hvg_method is required (e.g. pearson_residuals).")

    mouse_path = Path(spec.source_datasets["mouse"])
    human_path = Path(spec.source_datasets["human"])
    for label, p in (("mouse", mouse_path), ("human", human_path)):
        if not p.exists():
            raise PrepError(f"source dataset ({label}) not found: {p}")

    _log(f"[BACKED] spec={spec.experiment_tag}  flavor={spec.hvg_method}  n_top={spec.hvg_n_top}")
    _log(f"holdout={spec.holdout_cell_types or '(none)'}  random_state={spec.random_state}")
    _log(f"output -> {out_path}")

    af = spec.assay_filter or {}
    assay_cols = ["assay", "assay_ontology_term_id"]

    # --- 1. obs-only read (+assay) -------------------------------------------
    def _read_min(path, label):
        import h5py
        with h5py.File(str(path), "r") as f:
            present = [c for c in assay_cols if c in f["obs"]]
        return _read_obs_columns_h5(path, [CT_COL, TISSUE_COL] + present, label)

    mouse_obs = _read_min(mouse_path, "mouse")
    human_obs = _read_min(human_path, "human")

    # --- 2. assay filter -> kept original positions --------------------------
    m_keep = _assay_keep_positions(mouse_obs, af.get("mouse"), "mouse")
    h_keep = _assay_keep_positions(human_obs, af.get("human"), "human")
    mouse_obs_f = mouse_obs.iloc[m_keep].reset_index(drop=True)
    human_obs_f = human_obs.iloc[h_keep].reset_index(drop=True)

    # --- 3. match 1:1 on filtered obs, map back to original file positions ----
    m_idx_f, h_idx_f = _match_obs_only(mouse_obs_f, human_obs_f, CT_COL, TISSUE_COL, spec.random_state)
    if len(m_idx_f) == 0:
        raise PrepError("No matched pairs after assay filter — check (cell_type, tissue) overlap.")
    m_idx = m_keep[m_idx_f]
    h_idx = h_keep[h_idx_f]
    _log(f"  matched: {len(m_idx)} pairs per species (post-assay-filter)")

    # --- 4. full obs + materialize raw for matched rows ----------------------
    mouse_obs_full = _read_full_obs_h5(mouse_path, "mouse", m_idx)
    human_obs_full = _read_full_obs_h5(human_path, "human", h_idx)
    mouse_raw = _materialize_raw_subset(mouse_path, m_idx, mouse_obs_full, "mouse")
    human_raw = _materialize_raw_subset(human_path, h_idx, human_obs_full, "human")

    # --- 5. ortholog alignment (cached, one2one) -----------------------------
    if not BIOMART_CACHE.exists():
        raise PrepError(f"ortholog cache missing: {BIOMART_CACHE}")
    ortho_df = pd.read_csv(BIOMART_CACHE)
    if "orthology_type" in ortho_df.columns:
        ortho_df = ortho_df[ortho_df["orthology_type"] == "ortholog_one2one"].copy()
    mouse_m, human_m, _ = subset_matched_adatas_by_ortholog_table(mouse_raw, human_raw, ortho_df)
    _log(f"  aligned: mouse {mouse_m.shape}  human {human_m.shape}")
    assert (mouse_m.var_names == human_m.var_names).all()

    # --- 6. concat + counts + normalize + log1p ------------------------------
    mouse_m.obs["condition"] = "mouse"
    human_m.obs["condition"] = "human"
    matched_full = ad.concat([mouse_m, human_m], join="inner")
    matched_full.obs["species"] = matched_full.obs["condition"].values
    raw_X = matched_full.X
    if sp_sparse.issparse(raw_X):
        assert np.allclose(raw_X.data, np.round(raw_X.data)), "raw .X is not integer-valued"
        raw_int = raw_X.copy()
        raw_int.data = raw_int.data.astype(np.int32)
    else:
        assert np.allclose(raw_X, np.round(raw_X)), "raw .X is not integer-valued"
        raw_int = raw_X.astype(np.int32)
    matched_full.layers["counts"] = raw_int
    sc.pp.normalize_total(matched_full, target_sum=1e4)
    sc.pp.log1p(matched_full)
    _log(f"  matched_full {matched_full.shape} (.X log-normalized, counts in layer)")

    # --- 7. HVG on non-holdout -> subset -> clean -> write -> round-trip -----
    holdout_ids = set(spec.holdout_cell_types or [])
    train_mask = ~matched_full.obs[CT_COL].astype(str).isin(holdout_ids)
    _log(f"  HVG on {int(train_mask.sum())} train-eligible cells "
         f"(holdout {int(matched_full.n_obs - train_mask.sum())} kept)")
    hvg_df = _run_hvg_flavor(matched_full[train_mask].copy(), spec.hvg_method,
                             n_top=spec.hvg_n_top, batch_key=spec.hvg_batch_key)
    hv_genes = hvg_df[hvg_df["highly_variable"]].sort_values("rank", na_position="last").index.tolist()
    hv_genes = hv_genes[: spec.hvg_n_top]
    _log(f"  selected {len(hv_genes)} HVG")

    cleaned = _clean_adata(matched_full[:, hv_genes].copy())
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = out_path.with_suffix(".prep1x.h5ad")
    cleaned.write_h5ad(str(tmp_path))
    _roundtrip_to_anndata07(tmp_path, out_path)
    if not keep_intermediate:
        try:
            tmp_path.unlink()
        except OSError:
            pass

    _verify_output(out_path)
    _log(f"[BACKED] DONE in {time.time() - t0:.1f}s -> {out_path}")
    return out_path

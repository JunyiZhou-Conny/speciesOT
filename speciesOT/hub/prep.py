"""Data preparation (v2): materialize a training `.h5ad` from an ExperimentSpec.

This is the `./hub prep <spec.yaml>` milestone. It ports the canonical procedure
from `speciesOT/baseline/analysis/01.5_data_prep_all_holdouts_hvg_flavors.ipynb`
(§1–§7) into a single, reproducible entry point:

    1. Load `source_datasets.mouse` / `source_datasets.human` AnnData objects.
    2. Promote `.raw` to `.X` so integer UMI counts are accessible.
    3. Ortholog-align mouse↔human onto a shared one-to-one axis (BioMart, with a
       local cache at `scripts/.biomart_ortholog_cache.csv`).
    4. Match cells by (cell_type_ontology_term_id, tissue_ontology_term_id).
    5. Concat, snapshot raw counts to `.layers['counts']`, log-normalize `.X`.
    6. Select HVG with the spec's flavor on the train-eligible (non-holdout) cells.
    7. Subset to the HVG (KEEPING holdout cells, which `toggle_ood` splits at
       train time), strip everything but `.X`/`.obs`, write the file, and
       round-trip it through the CellOT env's anndata 0.7 for downstream
       compatibility.

ENVIRONMENT
-----------
The heavy lifting requires `scanpy >= 1.12` (Pearson residuals, seurat_v3_paper),
which lives in the `analysis` conda env — NOT the `CellOT` env the rest of the
hub runs in. Hence:

  - `./hub prep` (in `cli.py`, CellOT env) shells out to the `analysis` python
    running `python -m speciesOT.hub.prep <spec.yaml>`.
  - This module is therefore standalone: it is NEVER imported by `cli.py` or any
    other CellOT-env hub module. It only imports `load_spec_yaml` (yaml + pandas,
    both present in `analysis`).

The final anndata-0.7 round-trip shells back out to the CellOT env's interpreter
(anndata 0.7.6), exactly as 01.5 §7 does.

Run directly:

    /path/to/analysis/python -m speciesOT.hub.prep specs/m1_modern.yaml [--force]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# --- Package import shim --------------------------------------------------
# Make `speciesOT.hub.spec` importable and expose the inner package dir so the
# `speciesot_helpers` top-level module (the 01.5 helpers) resolves.
_THIS = Path(__file__).resolve()
INNER_PKG_DIR = _THIS.parent.parent          # .../speciesOT/speciesOT
WORKSPACE_ROOT = INNER_PKG_DIR.parent        # .../speciesOT
for _p in (str(WORKSPACE_ROOT), str(INNER_PKG_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from speciesOT.hub.spec import ExperimentSpec, load_spec_yaml  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CELLOT_DIR = WORKSPACE_ROOT / "cellot" / "cellot_gpu"
BIOMART_CACHE = WORKSPACE_ROOT / "scripts" / ".biomart_ortholog_cache.csv"

CT_COL = "cell_type_ontology_term_id"
TISSUE_COL = "tissue_ontology_term_id"

# Obs columns carried into the written file (per 01.5 convention).
KEEP_OBS = [
    "condition",
    "species",
    "cell_type_ontology_term_id",
    "cell_type",
    "tissue_ontology_term_id",
    "tissue",
    "donor_id",
]

# Flavors whose HVG runs on raw counts (.layers['counts']) vs log-norm (.X).
_RAW_COUNT_FLAVORS = {"seurat_v3", "seurat_v3_paper", "pearson_residuals"}
_LOGNORM_FLAVORS = {"seurat", "cell_ranger"}

# CellOT-env interpreter (anndata 0.7.6) for the round-trip. Override with the
# SPECIESOT_CELLOT_PY env var. First existing candidate wins.
_CELLOT_PY_CANDIDATES = [
    os.environ.get("SPECIESOT_CELLOT_PY", ""),
    "/n/home01/jzhou1125/.conda/envs/CellOT/bin/python",
    "/n/home01/jzhou1125/miniforge3/envs/CellOT/bin/python",
]


class PrepError(RuntimeError):
    """Raised for any prep-stage failure that should abort loudly."""


def _log(msg: str) -> None:
    print(f"[hub prep] {msg}", flush=True)


def _resolve_cellot_py() -> str:
    for cand in _CELLOT_PY_CANDIDATES:
        if cand and Path(cand).exists():
            return cand
    raise PrepError(
        "Could not find a CellOT-env python (anndata 0.7) for the final round-trip. "
        "Set SPECIESOT_CELLOT_PY to a python with anndata<0.8. Tried: "
        + ", ".join(c for c in _CELLOT_PY_CANDIDATES if c)
    )


# ---------------------------------------------------------------------------
# HVG dispatcher + cleaner (ported verbatim from 01.5 §5)
# ---------------------------------------------------------------------------

def _run_hvg_flavor(adata, flavor, n_top, batch_key):
    """Run HVG for `flavor`, returning a per-gene DataFrame with `highly_variable`,
    `score`, `rank`. Input layer is dispatched per-flavor (01.5 §5)."""
    import numpy as np
    import pandas as pd
    import scanpy as sc
    import scipy.sparse as sp_sparse

    a = adata.copy()

    # Raw-count flavors need an integer `counts` layer; recast in place.
    if flavor in _RAW_COUNT_FLAVORS and "counts" in a.layers:
        L = a.layers["counts"]
        if sp_sparse.issparse(L):
            assert np.allclose(L.data, np.round(L.data)), "counts layer is not integer-valued"
            a.layers["counts"] = L.astype(np.int32)
        else:
            assert np.allclose(L, np.round(L)), "counts layer is not integer-valued"
            a.layers["counts"] = L.astype(np.int32)

    if flavor in ("seurat", "cell_ranger"):
        sc.pp.highly_variable_genes(a, n_top_genes=n_top, flavor=flavor, batch_key=batch_key)
        score_col = "dispersions_norm"
    elif flavor in ("seurat_v3", "seurat_v3_paper"):
        sc.pp.highly_variable_genes(
            a, n_top_genes=n_top, flavor=flavor, batch_key=batch_key, layer="counts",
        )
        score_col = "variances_norm"
    elif flavor == "pearson_residuals":
        from scanpy.experimental.pp import highly_variable_genes as hvg_pr
        hvg_pr(
            a, n_top_genes=n_top, flavor="pearson_residuals",
            batch_key=batch_key, layer="counts",
        )
        score_col = (
            "residual_variances"
            if "residual_variances" in a.var.columns
            else "highly_variable_rank"
        )
    else:
        raise PrepError(
            f"unknown hvg_method {flavor!r}. Supported: "
            f"{sorted(_LOGNORM_FLAVORS | _RAW_COUNT_FLAVORS)}"
        )

    df = a.var[["highly_variable"]].copy()
    df["score"] = a.var[score_col] if score_col in a.var.columns else np.nan
    df["flavor"] = flavor
    if "highly_variable_rank" in a.var.columns:
        df["rank"] = pd.to_numeric(a.var["highly_variable_rank"], errors="coerce").astype(float)
    else:
        df["rank"] = (
            df["score"].rank(ascending=False, method="min").where(df["highly_variable"]).astype(float)
        )
    return df


def _clean_adata(adata):
    """Strip layers/obsm/obsp/uns/varm/varp; densify X; keep KEEP_OBS columns only."""
    import anndata as ad
    import numpy as np
    import pandas as pd
    import scipy.sparse as sp_sparse

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


# ---------------------------------------------------------------------------
# anndata 0.7 round-trip (01.5 §7) — runs in the CellOT env
# ---------------------------------------------------------------------------

_ROUNDTRIP_SCRIPT = r"""
import sys, os
import h5py
import numpy as np
import pandas as pd
import anndata as ad
from scipy import sparse

def _decode(x):
    return x.decode() if isinstance(x, (bytes, np.bytes_)) else x

def _load_frame(grp):
    idx_key = _decode(grp.attrs["_index"]) if "_index" in grp.attrs else "index"
    index = [_decode(x) for x in grp[idx_key][:]]
    cols = {}
    for name in grp.keys():
        if name == idx_key:
            continue
        node = grp[name]
        if isinstance(node, h5py.Group) and "categories" in node and "codes" in node:
            cats = [_decode(c) for c in node["categories"][:]]
            cols[name] = pd.Categorical.from_codes(node["codes"][:], categories=cats)
        else:
            arr = node[:]
            if arr.dtype.kind in ("O", "S"):
                arr = np.array([_decode(x) for x in arr])
            cols[name] = arr
    return pd.DataFrame(cols, index=pd.Index(index, name=idx_key))

def load_X(f):
    node = f["X"]
    if isinstance(node, h5py.Group):
        data = node["data"][:]
        indices = node["indices"][:]
        indptr = node["indptr"][:]
        shape = tuple(node.attrs.get("shape", node.attrs.get("h5sparse_shape")))
        encoding = _decode(node.attrs.get("encoding-type", b"csr_matrix"))
        if "csc" in encoding:
            return sparse.csc_matrix((data, indices, indptr), shape=shape)
        return sparse.csr_matrix((data, indices, indptr), shape=shape)
    return node[:]

src, dst = sys.argv[1], sys.argv[2]
with h5py.File(src, "r") as f:
    obs_df = _load_frame(f["obs"])
    var_df = _load_frame(f["var"])
    X = load_X(f)
adata = ad.AnnData(X=X, obs=obs_df, var=var_df)
adata.write(dst)
print("anndata", ad.__version__, "shape", adata.shape)
"""


def _roundtrip_to_anndata07(src: Path, dst: Path) -> None:
    cellot_py = _resolve_cellot_py()
    _log(f"round-trip to anndata 0.7 via {cellot_py}")
    res = subprocess.run(
        [cellot_py, "-c", _ROUNDTRIP_SCRIPT, str(src), str(dst)],
        capture_output=True, text=True,
    )
    if res.returncode != 0:
        raise PrepError(
            "anndata 0.7 round-trip failed:\n"
            f"  stdout: {res.stdout.strip()}\n  stderr: {res.stderr.strip()}"
        )
    _log(f"  round-trip ok ({res.stdout.strip()})")


# ---------------------------------------------------------------------------
# Ortholog alignment
# ---------------------------------------------------------------------------

def _align_orthologs(mouse_all, human_all):
    """Return (mouse_aligned, human_aligned) on a shared one-to-one ortholog axis.

    Uses the cached BioMart table at `scripts/.biomart_ortholog_cache.csv` when
    present; otherwise queries BioMart live and writes the cache for next time.
    """
    import pandas as pd
    import speciesot_helpers as H

    if BIOMART_CACHE.exists():
        _log(f"ortholog: using cache {BIOMART_CACHE}")
        ortho_df = pd.read_csv(BIOMART_CACHE)
        mouse_aligned, human_aligned, _ = H.subset_matched_adatas_by_ortholog_table(
            mouse_all, human_all, ortho_df,
        )
    else:
        _log("ortholog: cache miss — querying BioMart live (slow)")
        mouse_aligned, human_aligned, ortho = H.align_adatas_biomart_one2one(
            mouse_all, human_all,
        )
        try:
            BIOMART_CACHE.parent.mkdir(parents=True, exist_ok=True)
            ortho.to_csv(BIOMART_CACHE, index=False)
            _log(f"ortholog: wrote cache {BIOMART_CACHE} ({len(ortho)} pairs)")
        except OSError as e:
            _log(f"ortholog: WARNING could not write cache: {e}")
    return mouse_aligned, human_aligned


# ---------------------------------------------------------------------------
# Assay filter (an ENFORCED preprocessing treatment for all atlas prep)
# ---------------------------------------------------------------------------
# Discovered via notebook 21 / docs/conceptual_framework.md: the atlas sources
# mix sequencing platforms (10x droplet vs Smart-seq2 plate-based), and the
# Smart-seq2 minority has a very different expression distribution that shows up
# as the OOD "scatter" and inflates MMD. We therefore keep ONE droplet platform
# per species (mouse 10x 3' v2, human 10x 3' v3) and drop the rest. This is a
# required treatment, not optional metadata.

# Map spec assay tokens -> the set of matching values in the source obs
# `assay` (human-readable) / `assay_ontology_term_id` (EFO) columns.
_ASSAY_ALIASES = {
    "chromium_v2": {"10x 3' v2", "EFO:0009899"},
    "chromium_v3": {"10x 3' v3", "EFO:0009922"},
    "10x 3' v2": {"10x 3' v2", "EFO:0009899"},
    "10x 3' v3": {"10x 3' v3", "EFO:0009922"},
    "EFO:0009899": {"10x 3' v2", "EFO:0009899"},
    "EFO:0009922": {"10x 3' v3", "EFO:0009922"},
}


def _apply_assay_filter(adata, allowed_tokens, species_label):
    """Subset `adata` to cells whose assay is in `allowed_tokens` (ENFORCED).

    Matches against the `assay` or `assay_ontology_term_id` obs column, expanding
    each token via `_ASSAY_ALIASES`. Raises if no assay column exists or the
    filter empties the set. An empty `allowed_tokens` skips with a loud warning
    (the single-platform treatment is meant to always run).
    """
    import pandas as pd

    if not allowed_tokens:
        _log(f"  WARNING: assay_filter[{species_label}] is empty -> NOT enforcing the "
             "single-platform treatment (Smart-seq2 etc. will leak in).")
        return adata

    allowed = set()
    for tok in allowed_tokens:
        allowed |= _ASSAY_ALIASES.get(str(tok), {str(tok)})

    cols = [c for c in ("assay", "assay_ontology_term_id") if c in adata.obs.columns]
    if not cols:
        raise PrepError(
            f"{species_label}: assay_filter requested ({allowed_tokens}) but the source "
            "obs has no 'assay' / 'assay_ontology_term_id' column to filter on."
        )

    mask = pd.Series(False, index=adata.obs_names)
    for c in cols:
        mask = mask | adata.obs[c].astype(str).isin(allowed)
    n_before, n_after = adata.n_obs, int(mask.sum())
    _log(f"  assay filter [{species_label}]: keep {sorted(allowed_tokens)} "
         f"-> {n_after}/{n_before} cells")
    if n_after == 0:
        seen = sorted(adata.obs[cols[0]].astype(str).unique())[:8]
        raise PrepError(
            f"{species_label}: assay filter removed ALL cells. Tokens {allowed_tokens} "
            f"matched nothing; source {cols[0]} values include {seen}."
        )
    return adata[mask].copy()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def prep_from_spec(spec: ExperimentSpec, force: bool = False,
                   keep_intermediate: bool = False) -> Path:
    """Materialize the training `.h5ad` for `spec`. Returns the output path."""
    # Large/full-atlas sources can't be full-loaded; use the backed pipeline.
    if getattr(spec, "source_backed", False):
        from speciesOT.hub.prep_backed import prep_backed_from_spec
        return prep_backed_from_spec(spec, force=force, keep_intermediate=keep_intermediate)

    import anndata as ad
    import numpy as np
    import scanpy as sc
    import scipy.sparse as sp_sparse

    import speciesot_helpers as H

    t0 = time.time()

    # --- Resolve + guard output path -------------------------------------
    if not spec.data_file:
        raise PrepError("spec.data_file is empty; cannot determine output path.")
    out_path = (CELLOT_DIR / spec.data_file).resolve()
    if out_path.exists() and not force:
        raise PrepError(
            f"output already exists: {out_path}\n"
            "Refusing to overwrite (big files = big mistakes). Pass --force to overwrite."
        )

    if (spec.ortholog_source or "biomart") != "biomart":
        raise PrepError(
            f"ortholog_source={spec.ortholog_source!r} not supported; only 'biomart'."
        )
    if not spec.hvg_method:
        raise PrepError("spec.hvg_method is required (e.g. pearson_residuals).")

    mouse_path = Path(spec.source_datasets["mouse"])
    human_path = Path(spec.source_datasets["human"])
    for label, p in (("mouse", mouse_path), ("human", human_path)):
        if not p.exists():
            raise PrepError(
                f"source dataset ({label}) not found: {p}\n"
                "These 'sampled_*_shared.h5ad' files live in Josh's data tree and are "
                "not part of this repo. Check source_datasets in the spec."
            )

    _log(f"spec={spec.experiment_tag}  flavor={spec.hvg_method}  n_top={spec.hvg_n_top}")
    _log(f"holdout={spec.holdout_cell_types or '(none)'}  random_state={spec.random_state}")
    _log(f"output -> {out_path}")

    # --- 1. Load + promote .raw to .X ------------------------------------
    _log("loading source files and promoting .raw to .X ...")
    mouse_full = sc.read_h5ad(str(mouse_path))
    human_full = sc.read_h5ad(str(human_path))
    if mouse_full.raw is None or human_full.raw is None:
        raise PrepError("source .raw is missing; cannot recover integer counts.")

    mouse_all = mouse_full.raw.to_adata()
    human_all = human_full.raw.to_adata()
    mouse_all.obs = mouse_full.obs.copy()
    human_all.obs = human_full.obs.copy()
    mouse_all.X = mouse_all.X.astype("float32")
    human_all.X = human_all.X.astype("float32")
    _log(f"  mouse {mouse_all.shape}  human {human_all.shape}")

    # --- 1b. Enforce assay filter (single platform per species) ----------
    af = spec.assay_filter or {}
    mouse_all = _apply_assay_filter(mouse_all, af.get("mouse"), "mouse")
    human_all = _apply_assay_filter(human_all, af.get("human"), "human")
    _log(f"  after assay filter: mouse {mouse_all.shape}  human {human_all.shape}")

    # --- 2. Ortholog alignment -------------------------------------------
    mouse_aligned, human_aligned = _align_orthologs(mouse_all, human_all)
    _log(f"  aligned: mouse {mouse_aligned.shape}  human {human_aligned.shape}")
    assert (mouse_aligned.var_names == human_aligned.var_names).all()

    # --- 3. Match cells by (cell_type, tissue) ---------------------------
    _log("matching cells by (cell_type, tissue) ...")
    mouse_matched, human_matched = H.match_cells_by_celltype_tissue(
        mouse_aligned, human_aligned,
        cell_type_key=CT_COL, tissue_key=TISSUE_COL, seed=spec.random_state,
    )
    _log(f"  matched: {mouse_matched.n_obs} pairs per species")
    assert mouse_matched.n_obs == human_matched.n_obs

    # --- 4. Concat, snapshot counts, log-normalize -----------------------
    mouse_m = mouse_matched.copy()
    human_m = human_matched.copy()
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

    # The written .X is ALWAYS log1p(normalize_total(counts)) — this is the fixed
    # 01.5 contract that scgen/IMPACT depend on, independent of the HVG flavor
    # (raw-count flavors read .layers['counts'] for *selection* only). If a spec
    # sets log1p_applied=False, that contradicts the pipeline contract; warn and
    # apply log1p anyway so the output matches what 01.5 would produce.
    sc.pp.normalize_total(matched_full, target_sum=1e4)
    if spec.log1p_applied is False:
        _log("  WARNING: spec.log1p_applied=false contradicts the 01.5 contract "
             "(.X must be log-normalized); applying log1p anyway.")
    sc.pp.log1p(matched_full)
    _log(f"  matched_full {matched_full.shape}  (.X log-normalized, counts in layer)")

    # --- 5. HVG on train-eligible (non-holdout) cells --------------------
    holdout_ids = set(spec.holdout_cell_types or [])
    train_mask = ~matched_full.obs[CT_COL].astype(str).isin(holdout_ids)
    n_train = int(train_mask.sum())
    n_holdout = int(matched_full.n_obs - n_train)
    _log(f"  HVG on {n_train} train-eligible cells (holdout {n_holdout} kept in file)")

    train_subset = matched_full[train_mask].copy()
    hvg_df = _run_hvg_flavor(
        train_subset, spec.hvg_method, n_top=spec.hvg_n_top, batch_key=spec.hvg_batch_key,
    )
    hv_genes = (
        hvg_df[hvg_df["highly_variable"]].sort_values("rank", na_position="last").index.tolist()
    )
    if len(hv_genes) > spec.hvg_n_top:
        hv_genes = hv_genes[: spec.hvg_n_top]
    _log(f"  selected {len(hv_genes)} HVG")

    # --- 6. Subset + clean -----------------------------------------------
    sub = matched_full[:, hv_genes].copy()
    cleaned = _clean_adata(sub)
    _log(f"  cleaned: {cleaned.n_obs} cells x {cleaned.n_vars} genes")

    # --- 7. Write + round-trip to anndata 0.7 ----------------------------
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
    _log(f"DONE in {time.time() - t0:.1f}s -> {out_path}")
    return out_path


def _verify_output(out_path: Path) -> None:
    """Read back the written file and sanity-check shape / .X / .obs."""
    import anndata as ad
    import numpy as np

    a = ad.read_h5ad(str(out_path))
    X = a.X
    xvals = X.data if hasattr(X, "data") else np.asarray(X).ravel()
    obs_cols = sorted(a.obs.columns.tolist())
    cond = (
        a.obs["condition"].astype(str).value_counts().to_dict()
        if "condition" in a.obs.columns else {}
    )
    n_layers = len(getattr(a, "layers", {}) or {})
    _log("verification:")
    _log(f"  shape={a.shape}  layers={n_layers} (expect 0)")
    _log(f"  X min={float(np.nanmin(xvals)):.4f} max={float(np.nanmax(xvals)):.4f} "
         f"mean={float(np.nanmean(xvals)):.4f}")
    _log(f"  obs columns: {obs_cols}")
    _log(f"  condition counts: {cond}")
    if n_layers != 0:
        _log("  WARNING: expected .layers to be empty after clean.")
    if cond and not ({"mouse", "human"} <= set(cond)):
        _log("  WARNING: condition is missing one of {mouse, human}.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="speciesOT.hub.prep",
        description="Materialize a training .h5ad from an ExperimentSpec (01.5 port).",
    )
    parser.add_argument("spec", type=Path, help="path to a spec YAML")
    parser.add_argument(
        "--force", action="store_true",
        help="overwrite the output .h5ad if it already exists",
    )
    parser.add_argument(
        "--keep-intermediate", action="store_true",
        help="keep the pre-round-trip anndata-1.x temp file",
    )
    args = parser.parse_args(argv)

    spec_path = args.spec
    if not spec_path.exists():
        print(f"[hub prep] spec not found: {spec_path}", file=sys.stderr)
        return 2
    spec = load_spec_yaml(spec_path)

    try:
        prep_from_spec(spec, force=args.force, keep_intermediate=args.keep_intermediate)
    except PrepError as e:
        print(f"[hub prep] ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    _rc = main()
    # `speciesot_helpers` pulls in torch/numba/umap, whose interpreter teardown
    # can block for minutes in uninterruptible I/O on the lab's network
    # filesystem. All output is flushed as it is produced, so skip the slow
    # finalizers and exit immediately with the right code.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_rc)

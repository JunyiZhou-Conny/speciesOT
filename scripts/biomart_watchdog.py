#!/usr/bin/env python3
"""Periodically retry BioMart. When it succeeds, regenerate the 12 missing
hvg_{flavor}_{group}_v07.h5ad files (seurat_v3, seurat_v3_paper, pearson_residuals
x 4 groups) and submit their 48 sbatch jobs (12 cells x 4 sbatch).

Skips flavors/groups whose dataset files already exist on disk.

Run with the analysis env Python:
  /n/home01/jzhou1125/miniforge3/envs/analysis/bin/python scripts/biomart_watchdog.py
"""

import os
import sys
import time
import subprocess
import warnings
import numpy as np
import pandas as pd
import anndata as ad
import scanpy as sc
import scipy.sparse as sp_sparse

warnings.filterwarnings("ignore")
sys.path.insert(0, "/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/speciesOT")

BASE = "/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT"
DATA_DIR = os.path.join(BASE, "cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg")
SBATCH_TRAIN = os.path.join(BASE, "sbatch/train")
SBATCH_EVAL = os.path.join(BASE, "sbatch/eval")
LOG = os.path.join(BASE, "scripts/.submitted_v3_pearson_chain.csv")
CELLOT_PY = "/n/home01/jzhou1125/.conda/envs/CellOT/bin/python"

MOUSE_H5AD = "/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_muris/sampled_mouse_shared.h5ad"
HUMAN_H5AD = "/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_sapiens/sampled_human_shared.h5ad"

CT_COL = "cell_type_ontology_term_id"
TISSUE_COL = "tissue_ontology_term_id"
N_HVG = 1000

MISSING_FLAVORS = ["seurat_v3", "seurat_v3_paper", "pearson_residuals"]
GROUPS = {
    "a": {"name": "cd8",            "holdout": ["CL:0000625"]},
    "b": {"name": "cd8_thymo",      "holdout": ["CL:0000625", "CL:0000893"]},
    "c": {"name": "tcell_subtypes", "holdout": ["CL:0000624", "CL:0000625", "CL:0000893"]},
    "d": {"name": "cd4",            "holdout": ["CL:0000624"]},
}

KEEP_OBS = [
    "condition", "species",
    "cell_type_ontology_term_id", "cell_type",
    "tissue_ontology_term_id", "tissue",
    "donor_id",
]


def log(msg):
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    print(f"[biomart_watchdog {ts}] {msg}", flush=True)


def biomart_alive():
    """Quick BioMart probe — single attempt per host, no retries, fail fast."""
    from speciesot_helpers import fetch_human_mouse_one2one_orthologs
    try:
        df = fetch_human_mouse_one2one_orthologs(max_attempts_per_host=1, retry_pause_sec=1.0)
        log(f"BioMart up; orthologs={len(df)}")
        return True
    except Exception as e:
        log(f"BioMart still down: {type(e).__name__}: {str(e)[:200]}")
        return False


def make_matched_full():
    """Replicate 01.5 cells 1-9 to produce matched_full with .X log-norm and
    .layers['counts'] int32."""
    from speciesot_helpers import (
        align_adatas_biomart_one2one,
        match_cells_by_celltype_tissue,
    )

    log("loading source files...")
    mouse_full = sc.read_h5ad(MOUSE_H5AD)
    human_full = sc.read_h5ad(HUMAN_H5AD)
    mouse_all = mouse_full.raw.to_adata()
    human_all = human_full.raw.to_adata()
    mouse_all.obs = mouse_full.obs.copy()
    human_all.obs = human_full.obs.copy()
    mouse_all.X = mouse_all.X.astype("float32")
    human_all.X = human_all.X.astype("float32")

    log("ortholog alignment...")
    mouse_aligned, human_aligned, _ = align_adatas_biomart_one2one(mouse_all, human_all)

    log("matching cells by (cell_type, tissue)...")
    mouse_matched, human_matched = match_cells_by_celltype_tissue(
        mouse_aligned, human_aligned,
        cell_type_key=CT_COL, tissue_key=TISSUE_COL, seed=0,
    )

    mouse_m = mouse_matched.copy(); mouse_m.obs["condition"] = "mouse"
    human_m = human_matched.copy(); human_m.obs["condition"] = "human"
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
    log(f"matched_full: {matched_full.shape}; layers[counts] sparse={sp_sparse.issparse(matched_full.layers['counts'])}")
    return matched_full


def run_hvg_flavor(adata, flavor, n_top=N_HVG, batch_key="species"):
    a = adata.copy()
    if "counts" in a.layers and flavor in ("seurat_v3", "seurat_v3_paper", "pearson_residuals"):
        L = a.layers["counts"]
        if sp_sparse.issparse(L):
            if L.data.dtype != np.int32:
                L_int = L.copy()
                L_int.data = L_int.data.astype(np.int32)
                a.layers["counts"] = L_int
        else:
            if L.dtype != np.int32:
                a.layers["counts"] = L.astype(np.int32)
    if flavor in ("seurat_v3", "seurat_v3_paper"):
        sc.pp.highly_variable_genes(
            a, n_top_genes=n_top, flavor=flavor, batch_key=batch_key, layer="counts",
        )
        score_col = "variances_norm"
    elif flavor == "pearson_residuals":
        from scanpy.experimental.pp import highly_variable_genes as hvg_pr
        hvg_pr(a, n_top_genes=n_top, flavor="pearson_residuals", batch_key=batch_key, layer="counts")
        score_col = "residual_variances" if "residual_variances" in a.var.columns else "highly_variable_rank"
    else:
        raise ValueError(flavor)
    df = a.var[["highly_variable"]].copy()
    df["score"] = a.var.get(score_col, np.nan)
    if "highly_variable_rank" in a.var.columns:
        # ranks can be float (median across species batches in v3/pearson); keep as float
        df["rank"] = pd.to_numeric(a.var["highly_variable_rank"], errors="coerce").astype(float)
    else:
        df["rank"] = df["score"].rank(ascending=False, method="min").where(df["highly_variable"]).astype(float)
    return df


def clean_adata(adata):
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


def write_one(matched_full, flavor, gk):
    holdout_ids = set(GROUPS[gk]["holdout"])
    train_mask = ~matched_full.obs[CT_COL].astype(str).isin(holdout_ids)
    train_subset = matched_full[train_mask].copy()
    df = run_hvg_flavor(train_subset, flavor)
    hv = df[df["highly_variable"]].sort_values("rank", na_position="last").index.tolist()[:N_HVG]
    sub = matched_full[:, hv].copy()
    cleaned = clean_adata(sub)
    out_path = os.path.join(DATA_DIR, f"hvg_{flavor}_{gk}.h5ad")
    cleaned.write_h5ad(out_path)
    log(f"  wrote {os.path.basename(out_path)} ({cleaned.n_obs}x{cleaned.n_vars})")
    return out_path


def round_trip(paths):
    """Strip empty groups + rewrite via CellOT env's anndata 0.7 (mirrors 01.5 §7)."""
    v07_paths = []
    for src in paths:
        dst = src.replace(".h5ad", "_v07.h5ad")
        if os.path.exists(dst):
            os.remove(dst)
        import shutil; shutil.copy2(src, dst)
        v07_paths.append(dst)
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
    g = f["obs"]
    idx = _d(g.attrs["_index"]) if "_index" in g.attrs else "index"
    index = [_d(x) for x in g[idx][:]]
    cols={}
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
    g = f["var"]
    idx = _d(g.attrs["_index"]) if "_index" in g.attrs else "index"
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
    subprocess.run([CELLOT_PY, "-c", strip_script, *v07_paths], check=True)
    subprocess.run([CELLOT_PY, "-c", rewrite_script, *v07_paths], check=True)
    return v07_paths


def submit_chain(flavor, gk):
    sub = []
    for mode in ("ood", "iid"):
        tag = f"hvg_{flavor}_{gk}_{mode}"
        sc_path = f"{SBATCH_TRAIN}/train_{tag}_scgen.sbatch"
        im_path = f"{SBATCH_TRAIN}/train_{tag}_impact_cellot.sbatch"
        se_path = f"{SBATCH_EVAL}/eval_{tag}_scgen.sbatch"
        ie_path = f"{SBATCH_EVAL}/eval_{tag}_impact_cellot.sbatch"
        SC = subprocess.check_output(["sbatch", "--parsable", sc_path]).decode().strip()
        IM = subprocess.check_output(["sbatch", "--parsable", f"--dependency=afterok:{SC}", im_path]).decode().strip()
        SE = subprocess.check_output(["sbatch", "--parsable", f"--dependency=afterok:{SC}", se_path]).decode().strip()
        IE = subprocess.check_output(["sbatch", "--parsable", f"--dependency=afterok:{IM}", ie_path]).decode().strip()
        sub.append((tag, SC, IM, SE, IE))
        log(f"submitted {tag}: scgen={SC} impact={IM} eval_scgen={SE} eval_impact={IE}")
    return sub


def needed():
    """Return list of (flavor, gk) for which the v07 file does not yet exist."""
    out = []
    for flavor in MISSING_FLAVORS:
        for gk in GROUPS:
            v07 = os.path.join(DATA_DIR, f"hvg_{flavor}_{gk}_v07.h5ad")
            if not os.path.exists(v07):
                out.append((flavor, gk))
    return out


def main():
    SLEEP_SEC = int(os.environ.get("BIOMART_SLEEP_SEC", "900"))  # 15 min
    MAX_HOURS = float(os.environ.get("BIOMART_MAX_HOURS", "5"))
    deadline = time.time() + MAX_HOURS * 3600
    log(f"watchdog started; will retry BioMart every {SLEEP_SEC}s for {MAX_HOURS}h")
    while time.time() < deadline:
        miss = needed()
        if not miss:
            log("nothing missing; exiting")
            return 0
        log(f"{len(miss)} (flavor, group) cells still missing: {miss}")
        if biomart_alive():
            log("BioMart up — generating missing datasets...")
            try:
                matched_full = make_matched_full()
                paths = []
                for flavor, gk in miss:
                    out_path = write_one(matched_full, flavor, gk)
                    paths.append(out_path)
                round_trip(paths)
                # group by flavor for submission
                already_submitted = set()
                with open(LOG, "a") as f:
                    if os.path.getsize(LOG) == 0:
                        f.write("tag,scgen,impact,eval_scgen,eval_impact\n")
                    for flavor, gk in miss:
                        if (flavor, gk) in already_submitted:
                            continue
                        for entry in submit_chain(flavor, gk):
                            f.write(",".join(entry) + "\n")
                        already_submitted.add((flavor, gk))
                log("DONE: missing datasets generated and chains submitted.")
                return 0
            except Exception as e:
                import traceback
                log(f"ERROR during dataset generation: {e}")
                traceback.print_exc()
                log(f"sleeping {SLEEP_SEC}s and retrying")
        time.sleep(SLEEP_SEC)
    log(f"timed out after {MAX_HOURS}h; giving up")
    return 1


if __name__ == "__main__":
    if not os.path.exists(LOG):
        open(LOG, "w").close()
    sys.exit(main())

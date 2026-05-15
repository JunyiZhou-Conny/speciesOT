#!/bin/bash
# predict_new_input.sh
# Run a NEW mouse single-cell file through the already-trained May-8 atlas-full
# models and write predicted human cells.
#
# Usage:
#   bash scripts/predict_new_input.sh <path_to_mouse.h5ad> [output_tag]
#
# Example:
#   bash scripts/predict_new_input.sh ~/my_new_mouse.h5ad my_experiment_2026
#
# Requirements for input file:
#   - AnnData h5ad with mouse cells.
#   - Gene names in .var_names: either mouse Ensembl (ENSMUSG*) or symbols.
#     If symbols, they will be mapped via the cached BioMart table.
#   - Raw integer counts in .layers['counts'] (preferred). If not present,
#     we use .X (which must be raw integer counts).
#
# Total wall time: ~3 min (CPU only, no sbatch).

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: bash scripts/predict_new_input.sh <path_to_mouse.h5ad> [output_tag]"
    exit 1
fi

INPUT_H5AD="$1"
TAG="${2:-$(basename "$INPUT_H5AD" .h5ad)}"

if [[ ! -f "$INPUT_H5AD" ]]; then
    echo "ERROR: input file not found: $INPUT_H5AD"
    exit 1
fi

BASE="/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT"
ANALYSIS_PY="/n/home01/jzhou1125/miniforge3/envs/analysis/bin/python"
CELLOT_PY="/n/home01/jzhou1125/.conda/envs/CellOT/bin/python"

# Sanity-check: trained models exist
for flavor in seurat_v3 pearson_residuals; do
    for model in scgen impact_cellot; do
        ckpt="$BASE/cellot/cellot_gpu/results/atlas_full_${flavor}/${model}/cache/model.pt"
        if [[ ! -f "$ckpt" ]]; then
            echo "ERROR: missing trained model at $ckpt"
            echo "Run scripts/run_full_pipeline.sh first to train, or generate_atlas_full_configs.py"
            exit 1
        fi
    done
done

echo "=== predict_new_input.sh ==="
echo "  input:  $INPUT_H5AD"
echo "  tag:    $TAG"

OUTDIR="$BASE/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg"
mkdir -p "$OUTDIR"

# Phase 1: preprocess into atlas namespace per flavor (analysis env)
echo ""
echo "=== Phase 1: preprocess into atlas HVG namespace ==="
$ANALYSIS_PY - "$INPUT_H5AD" "$TAG" "$OUTDIR" <<'PY'
import sys, os
from pathlib import Path
import numpy as np
import pandas as pd
import anndata as ad
import scanpy as sc
import scipy.sparse as sp_sparse

INPUT_H5AD, TAG, OUTDIR = sys.argv[1], sys.argv[2], sys.argv[3]
ORTHO_CACHE = "/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/scripts/.biomart_ortholog_cache.csv"
SYMBOL_CACHE = "/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/scripts/.bcg_symbol_to_ensmusg.csv"

src = sc.read_h5ad(INPUT_H5AD)
print(f"  loaded: {src.shape}, var sample: {list(src.var_names[:3])}")

# Get raw counts into .X
if "counts" in src.layers:
    src.X = src.layers["counts"].astype("float32")
src.obs_names_make_unique()
src.obs["condition"] = "mouse"
src.obs["species"] = "mouse"

# Ensure integer counts
xs = src.X[:50].toarray().ravel() if sp_sparse.issparse(src.X) else src.X[:50].ravel()
assert np.allclose(xs, np.round(xs)), "input .X (or .layers['counts']) must be raw integer counts"

# Map var_names to ENSG (handle both ENSMUSG and symbols)
var_names = list(src.var_names.astype(str))
is_ensembl = all(v.startswith("ENSMUSG") for v in var_names[:10])
print(f"  detected var_names: {'ENSMUSG' if is_ensembl else 'symbols'}")

# Load ortholog cache (mouse Ensembl -> human Ensembl)
ortho = pd.read_csv(ORTHO_CACHE)
ensmusg2ensg = dict(zip(ortho["mouse_ensembl_id"].astype(str), ortho["human_ensembl_id"].astype(str)))

if is_ensembl:
    var2ensg = {v: ensmusg2ensg.get(v) for v in var_names}
else:
    # symbols -> ENSMUSG via cache (or BioMart if missing). For now require cache.
    if not os.path.exists(SYMBOL_CACHE):
        print(f"ERROR: symbol cache missing at {SYMBOL_CACHE}.")
        print("  Run notebook 16 once on any symbol-keyed mouse file to populate.")
        sys.exit(1)
    sym_df = pd.read_csv(SYMBOL_CACHE)
    sym2ensmusg = dict(zip(sym_df["symbol"], sym_df["ensmusg"]))
    var2ensg = {}
    for v in var_names:
        ensmusg = sym2ensmusg.get(v)
        if ensmusg is not None:
            var2ensg[v] = ensmusg2ensg.get(ensmusg)

src_var_idx = {v: i for i, v in enumerate(var_names)}

# For each flavor, project onto atlas HVG list
for flavor in ["seurat_v3", "pearson_residuals"]:
    atlas_path = f"{OUTDIR}/hvg_{flavor}_atlas_full_v07.h5ad"
    atlas = sc.read_h5ad(atlas_path)
    target_genes = list(atlas.var_names.astype(str))

    cols = []
    for ensg in target_genes:
        match = None
        for v, e in var2ensg.items():
            if e == ensg:
                match = src_var_idx.get(v); break
        cols.append(match if match is not None else -1)
    n_present = sum(1 for c in cols if c is not None and c >= 0)

    Xs = src.X.toarray() if sp_sparse.issparse(src.X) else src.X
    Xn = np.zeros((src.n_obs, len(target_genes)), dtype=np.float32)
    for j, c in enumerate(cols):
        if c is not None and c >= 0:
            Xn[:, j] = Xs[:, c]

    a = ad.AnnData(X=Xn, obs=src.obs.copy(),
                   var=pd.DataFrame(index=pd.Index(target_genes, name="ensg")))
    sc.pp.normalize_total(a, target_sum=1e4); sc.pp.log1p(a)

    keep = [c for c in ["condition","species","cell_type","study","_scvi_batch"] if c in a.obs.columns]
    a = ad.AnnData(X=a.X, obs=a.obs[keep].copy(), var=a.var.copy())
    out = f"{OUTDIR}/{TAG}_aligned_{flavor}.h5ad"
    a.write_h5ad(out)
    print(f"  {flavor}: coverage {n_present}/{len(target_genes)} ({100*n_present/len(target_genes):.1f}%) -> {out}")
PY

# Phase 2: round-trip via CellOT env (anndata 0.7) to v07 files
echo ""
echo "=== Phase 2: round-trip to anndata 0.7 ==="
for flavor in seurat_v3 pearson_residuals; do
    src="$OUTDIR/${TAG}_aligned_${flavor}.h5ad"
    dst="$OUTDIR/${TAG}_aligned_${flavor}_v07.h5ad"
    [[ -f "$dst" ]] && rm -f "$dst"
    cp "$src" "$dst"
done

$CELLOT_PY - "$OUTDIR" "$TAG" <<'PY'
import sys, os, h5py, numpy as np, pandas as pd, anndata as ad
from scipy import sparse
OUTDIR, TAG = sys.argv[1], sys.argv[2]

# Strip empty groups
for flavor in ("seurat_v3","pearson_residuals"):
    p = f"{OUTDIR}/{TAG}_aligned_{flavor}_v07.h5ad"
    with h5py.File(p, "r+") as f:
        for g in ("layers","obsm","obsp","uns","varm","varp"):
            if g in f and len(f[g].keys())==0: del f[g]
        for a in ("encoding-type","encoding-version"):
            if a in f.attrs: del f.attrs[a]

# Re-write via anndata 0.7
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
    index = [_d(x) for x in g[idx][:]]; cols={}
    for n in g.keys():
        if n==idx: continue
        arr=g[n][:]
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

for flavor in ("seurat_v3","pearson_residuals"):
    p = f"{OUTDIR}/{TAG}_aligned_{flavor}_v07.h5ad"
    with h5py.File(p,"r") as f:
        obs=load_obs(f); var=load_var(f); X=load_X(f)
    a=ad.AnnData(X=X,obs=obs,var=var)
    os.remove(p); a.write(p)
    print(f"  rewrote {p}: shape {a.shape}")
PY

# Phase 3: predict via each (flavor, model) combo
echo ""
echo "=== Phase 3: predict via 4 trained models ==="
$CELLOT_PY - "$OUTDIR" "$TAG" "$BASE/cellot/cellot_gpu" <<'PY'
import sys, os
sys.path.insert(0, sys.argv[3])
import torch, numpy as np, anndata as ad
from cellot.utils import load_config
from cellot.utils.loaders import load_data, load_model, resolve_device
from cellot.models import load_autoencoder_model
from cellot.models.ae import compute_scgen_shift

OUTDIR, TAG, CELLOT_DIR = sys.argv[1], sys.argv[2], sys.argv[3]
RESULTS = f"{CELLOT_DIR}/results"

for flavor in ("seurat_v3","pearson_residuals"):
    atlas_path = f"{OUTDIR}/hvg_{flavor}_atlas_full_v07.h5ad"
    src_path = f"{OUTDIR}/{TAG}_aligned_{flavor}_v07.h5ad"
    src = ad.read(src_path)
    Xs = src.X.toarray() if hasattr(src.X, "toarray") else src.X
    inputs = torch.tensor(Xs, dtype=torch.float32)

    for model_name in ("scgen","impact_cellot"):
        results_dir = f"{RESULTS}/atlas_full_{flavor}/{model_name}"
        config = load_config(f"{results_dir}/config.yaml")
        device = resolve_device(config)
        config.data.path = atlas_path
        if "ae_emb" in config.data:
            config.data.ae_emb.path = f"{RESULTS}/atlas_full_{flavor}/model-scgen"

        if model_name == "scgen":
            a = ad.read(atlas_path)
            model, _ = load_autoencoder_model(config, restore=f"{results_dir}/cache/model.pt",
                                              device=device, input_dim=a.n_vars)
            model.eval()
            if not hasattr(model, "code_means"):
                loader = load_data(config, return_as="loader")
                labels = loader.train.dataset.adata.obs[config.data.condition]
                compute_scgen_shift(model, loader.train.dataset, labels=labels, device=device)
            shift = model.code_means["human"] - model.code_means["mouse"]
            codes = model.encode(inputs.to(device))
            pred = model.decode(codes + shift).detach().cpu().numpy()
        else:
            latent = config.model.get("latent_dim", 50)
            model, *_ = load_model(config, restore=f"{results_dir}/cache/model.pt",
                                   device=device, input_dim=latent)
            ae_config = load_config(f"{config.data.ae_emb.path}/config.yaml")
            ae, _ = load_autoencoder_model(ae_config,
                                           restore=f"{config.data.ae_emb.path}/cache/model.pt",
                                           device=device, input_dim=src.n_vars)
            ae.eval()
            f, g = model; g.eval()
            codes = ae.encode(inputs.to(device))
            t = g.transport(codes.requires_grad_(True))
            pred = ae.decode(t.detach()).detach().cpu().numpy()

        out_path = f"{OUTDIR}/{TAG}_predicted_human_via_{model_name}_{flavor}.h5ad"
        ad.AnnData(X=pred.astype(np.float32),
                   obs=src.obs.copy(), var=src.var.copy()).write(out_path)
        print(f"  wrote {out_path}: shape {pred.shape}")
PY

echo ""
echo "=== DONE ==="
echo ""
echo "Predictions written to:"
ls -1 "$OUTDIR/${TAG}_predicted_human_via_"*.h5ad 2>/dev/null | sed 's/^/  /'
echo ""
echo "Coverage info: shown above in Phase 1 output"

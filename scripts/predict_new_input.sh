#!/bin/bash
# predict_new_input.sh
# Run a NEW mouse single-cell file through an already-trained atlas model set
# and write predicted human cells.
#
# Usage:
#   bash scripts/predict_new_input.sh [--model-set NAME] [--posed-ensg] \
#       <path_to_mouse.h5ad> [output_tag]
#
# Example:
#   bash scripts/predict_new_input.sh ~/my_new_mouse.h5ad my_experiment_2026
#   bash scripts/predict_new_input.sh --model-set uncapped_v08 ~/my_new_mouse.h5ad exp2
#   bash scripts/predict_new_input.sh --model-set uncapped_v08_iid --posed-ensg \
#       bcg_control_scanvi.h5ad bcg_ctrl_a2
#
# Model sets (--model-set, default atlas_full_v07):
#   atlas_full_v07     the May-8 deployment models, flavors seurat_v3 + pearson_residuals
#   uncapped_v08       the v08 train_test deployment models (all cell types in the
#                      train pool; 5% monitor split). flavors pearson_residuals + mixhvg
#   uncapped_v08_iid   the v08 toggle_ood-iid twins (interim until uncapped_v08
#                      checkpoints exist). flavors pearson_residuals + mixhvg
# Each set has its OWN gene axis per flavor, and each model may ONLY be fed cells
# projected onto its own axis: hvg_pearson_residuals_atlas_full_v07.h5ad and
# hvg_pearson_residuals_a_uncapped_v08.h5ad share only 721 of their 1000 genes, so
# crossing them would not error -- it would silently predict from the wrong genes.
# The preflight below asserts axis == checkpoint and aborts if they disagree.
#
# Baked sidecars (optional, but they remove the training atlas from the handover):
#   results/<tag>/genes.txt                  the model's 1,000-gene axis
#   results/<tag>/scgen/cache/scgen_shift.pt the scGen latent shift (code_means)
# Written by scripts/bake_model_artifacts.py. When both are present this script
# never opens the 35 MB-per-flavor training .h5ad: phase 1 projects onto
# genes.txt, and phase 3 reads the shift instead of re-encoding the whole
# training set. The shift records the gene-axis sha256 it was computed against
# and is refused if that does not match the axis in use. When the sidecars are
# absent the original behaviour (read the atlas, recompute the shift) is used, so
# model sets that have not been baked still work unchanged.
#
# Requirements for input file (default, raw mouse):
#   - AnnData h5ad with mouse cells.
#   - Gene names in .var_names: either mouse Ensembl (ENSMUSG*) or symbols.
#     If symbols, they will be mapped via the cached BioMart table.
#   - Raw integer counts in .layers['counts'] (preferred). If not present,
#     we use .X (which must be raw integer counts).
#
# --posed-ensg  (scANVI / attempt 2):
#   Use this when the file is already human ENSG and .layers['counts'] is
#   atlas-posed count-scale expression (continuous; freq * library size).
#   Skips the integer assert and the mouse→human ortholog hop. Still runs
#   normalize_total + log1p, so do NOT log1p the file yourself first.
#   Still prefers .layers['counts'] over .X; does not use counts_original.
#
# Environment (all optional; defaults reproduce the historical behaviour):
#   SPECIESOT_ROOT         repo root, if the code and the results tree live apart
#   SPECIESOT_ANALYSIS_PY  interpreter for the `analysis` env (phase 1)
#   SPECIESOT_CELLOT_PY    interpreter for the model env (phases 2-3)
#   SPECIESOT_CELLOT_ENV   conda env name for the model env; default CellOT
#   SPECIESOT_ANALYSIS_ENV conda env name for the prep env; default analysis
# Otherwise the two interpreters are probed under $HOME (miniforge3, .conda,
# miniconda3, anaconda3, mambaforge) before falling back to the original
# author's absolute paths.
#
# SPECIESOT_CELLOT_ENV=CellOT_v3 runs phases 2-3 under the modern env
# (python 3.11 / anndata 0.10.9 / torch 2.3.1), which reads BOTH old and modern
# .h5ad files and was validated numerically against the legacy CellOT env
# (predictions agree to 8.3e-07 scGen / 4.8e-06 IMPACT; the scGen shift is
# bit-identical). Under CellOT_v3 the phase-2 anndata round-trip is no longer
# NEEDED -- it is kept, and still runs, because the legacy CellOT env
# (anndata 0.7.6) cannot read a modern file at all.
#
# Total wall time: ~3 min (CPU only, no sbatch).

set -euo pipefail

MODEL_SET="atlas_full_v07"
INPUT_MODE="raw_mouse"
POSITIONAL=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model-set)
            if [[ $# -lt 2 ]]; then
                echo "ERROR: --model-set needs a value"
                exit 1
            fi
            MODEL_SET="$2"
            shift 2
            ;;
        --model-set=*)
            MODEL_SET="${1#*=}"
            shift
            ;;
        --posed-ensg)
            INPUT_MODE="posed_ensg"
            shift
            ;;
        -h|--help)
            # the header comment block, minus the leading '# '
            awk 'NR>1 && /^#/ {sub(/^# ?/, ""); print; next} NR>1 {exit}' "${BASH_SOURCE[0]}"
            exit 0
            ;;
        *)
            POSITIONAL+=("$1")
            shift
            ;;
    esac
done
set -- ${POSITIONAL[@]+"${POSITIONAL[@]}"}

if [[ $# -lt 1 ]]; then
    echo "Usage: bash scripts/predict_new_input.sh [--model-set NAME] [--posed-ensg] <path_to_mouse.h5ad> [output_tag]"
    exit 1
fi

INPUT_H5AD="$1"
TAG="${2:-$(basename "$INPUT_H5AD" .h5ad)}"

if [[ ! -f "$INPUT_H5AD" ]]; then
    echo "ERROR: input file not found: $INPUT_H5AD"
    exit 1
fi

# ---------------------------------------------------------------------------
# Model set table. Everything that differs between trained model sets lives
# here: the gene-selection flavors, the results subdirectory, and the gene axis
# each flavor's models were trained on. {flavor} is substituted below.
# ---------------------------------------------------------------------------
case "$MODEL_SET" in
    atlas_full_v07)
        FLAVORS=(seurat_v3 pearson_residuals)
        RESULTS_TEMPLATE="atlas_full_{flavor}"
        AXIS_TEMPLATE="hvg_{flavor}_atlas_full_v07.h5ad"
        # Empty on purpose: this is the historical default and its output
        # filenames must stay exactly what they have always been.
        SET_SUFFIX=""
        ;;
    uncapped_v08)
        FLAVORS=(pearson_residuals mixhvg)
        RESULTS_TEMPLATE="hvg_{flavor}_uncapped_v08"
        AXIS_TEMPLATE="hvg_{flavor}_a_uncapped_v08.h5ad"
        SET_SUFFIX="_uncapped_v08"
        ;;
    uncapped_v08_iid)
        FLAVORS=(pearson_residuals mixhvg)
        RESULTS_TEMPLATE="hvg_{flavor}_a_uncapped_v08_iid"
        AXIS_TEMPLATE="hvg_{flavor}_a_uncapped_v08.h5ad"
        # Non-default sets tag their outputs, because `pearson_residuals` names
        # a DIFFERENT gene axis in each set and the files must not collide.
        SET_SUFFIX="_uncapped_v08_iid"
        ;;
    *)
        echo "ERROR: unknown --model-set '$MODEL_SET'"
        echo "  valid: atlas_full_v07, uncapped_v08, uncapped_v08_iid"
        exit 1
        ;;
esac
FLAVORS_STR="${FLAVORS[*]}"

subst_flavor() {  # subst_flavor <template> <flavor>
    echo "${1//\{flavor\}/$2}"
}

# ---------------------------------------------------------------------------
# Paths. Derived from this script's location so a clone on another account
# works with no editing; see speciesOT/hub/paths.py for the same convention.
# ---------------------------------------------------------------------------
BASE="${SPECIESOT_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

find_env_python() {  # find_env_python <conda_env_name> <override_path_or_empty>
    local env_name="$1" override="${2:-}" cand
    if [[ -n "$override" ]]; then
        if [[ -x "$override" ]]; then echo "$override"; return 0; fi
        echo "ERROR: override interpreter not executable: $override" >&2
        return 1
    fi
    for base in "$HOME/miniforge3" "$HOME/.conda" "$HOME/miniconda3" \
                "$HOME/anaconda3" "$HOME/mambaforge" \
                "/n/home01/jzhou1125/miniforge3" "/n/home01/jzhou1125/.conda"; do
        cand="$base/envs/$env_name/bin/python"
        if [[ -x "$cand" ]]; then echo "$cand"; return 0; fi
    done
    echo "ERROR: could not find a python for conda env '$env_name'." >&2
    echo "  Set the override env var, e.g. SPECIESOT_CELLOT_PY=\$(conda run -n $env_name which python)" >&2
    return 1
}

ANALYSIS_ENV="${SPECIESOT_ANALYSIS_ENV:-analysis}"
CELLOT_ENV="${SPECIESOT_CELLOT_ENV:-CellOT}"
ANALYSIS_PY="$(find_env_python "$ANALYSIS_ENV" "${SPECIESOT_ANALYSIS_PY:-}")"
CELLOT_PY="$(find_env_python "$CELLOT_ENV" "${SPECIESOT_CELLOT_PY:-}")"

echo "=== predict_new_input.sh ==="
echo "  input:      $INPUT_H5AD"
echo "  tag:        $TAG"
echo "  model set:  $MODEL_SET  (flavors: $FLAVORS_STR)"
echo "  base:       $BASE"
echo "  analysis:   $ANALYSIS_PY"
echo "  model env:  $CELLOT_PY"

# Sanity-check: trained models exist
for flavor in "${FLAVORS[@]}"; do
    results_subdir="$(subst_flavor "$RESULTS_TEMPLATE" "$flavor")"
    for model in scgen impact_cellot; do
        ckpt="$BASE/cellot/cellot_gpu/results/${results_subdir}/${model}/cache/model.pt"
        if [[ ! -f "$ckpt" ]]; then
            echo "ERROR: missing trained model at $ckpt"
            echo "  (model set '$MODEL_SET' is not fully trained, or --model-set is wrong)"
            echo "Run scripts/run_full_pipeline.sh first to train, or generate_atlas_full_configs.py"
            exit 1
        fi
    done
done

OUTDIR="$BASE/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg"
mkdir -p "$OUTDIR"

# Phase 0: assert every checkpoint's own training gene axis is the axis we are
# about to project onto. This runs BEFORE anything is written, so a mismatch
# costs nothing and, more importantly, cannot produce a plausible-looking file.
#
# The axis of record is <results>/<tag>/genes.txt when it exists (written by
# scripts/bake_model_artifacts.py), because it lives inside the checkpoint's own
# directory and so cannot be crossed with another model set's axis. When both it
# and the training .h5ad are present they must agree, and when only the sidecar
# is present the training dataset is not needed at all.
echo ""
echo "=== Phase 0: preflight -- gene axis must match the checkpoints ==="
$CELLOT_PY - "$OUTDIR" "$BASE/cellot/cellot_gpu" "$FLAVORS_STR" \
             "$RESULTS_TEMPLATE" "$AXIS_TEMPLATE" <<'PY'
import sys, os, hashlib, h5py, yaml

OUTDIR, CELLOT_DIR, FLAVORS, RESULTS_TEMPLATE, AXIS_TEMPLATE = sys.argv[1:6]
FLAVORS = FLAVORS.split()


def var_names(path):
    """Gene axis of an .h5ad, read with h5py so it is anndata-version agnostic."""
    with h5py.File(path, "r") as f:
        g = f["var"]
        key = g.attrs.get("_index", "index")
        key = key.decode() if isinstance(key, bytes) else key
        return [v.decode() if isinstance(v, bytes) else str(v) for v in g[key][:]]


def read_gene_list(path):
    with open(path) as fh:
        return [line for line in fh.read().split("\n") if line != ""]


def gene_axis_sha256(genes):
    """Must stay identical to bake_model_artifacts.gene_axis_sha256."""
    h = hashlib.sha256()
    for g in genes:
        h.update(str(g).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


ok = True
for flavor in FLAVORS:
    results_subdir = RESULTS_TEMPLATE.replace("{flavor}", flavor)
    tag_dir = f"{CELLOT_DIR}/results/{results_subdir}"
    axis_path = f"{OUTDIR}/{AXIS_TEMPLATE.replace('{flavor}', flavor)}"
    genes_txt = f"{tag_dir}/genes.txt"

    axis_genes, axis_source = None, None
    if os.path.exists(genes_txt):
        axis_genes, axis_source = read_gene_list(genes_txt), genes_txt
    if os.path.exists(axis_path):
        h5_genes = var_names(axis_path)
        if axis_genes is None:
            axis_genes, axis_source = h5_genes, axis_path
        elif h5_genes != axis_genes:
            print(f"  ERROR [{flavor}] SIDECAR/DATASET AXIS MISMATCH")
            print(f"          {genes_txt} ({len(axis_genes)} genes)")
            print(f"          disagrees with {axis_path} ({len(h5_genes)} genes)")
            print( "          One of the two is stale. Re-run")
            print( "          scripts/bake_model_artifacts.py --force. Refusing to run.")
            ok = False
            continue
    if axis_genes is None:
        print(f"  ERROR [{flavor}] no gene axis available: neither {genes_txt}")
        print(f"          nor {axis_path} exists")
        ok = False
        continue
    axis_sha = gene_axis_sha256(axis_genes)

    for model_name in ("scgen", "impact_cellot"):
        cfg_path = f"{tag_dir}/{model_name}/config.yaml"
        with open(cfg_path) as fh:
            cfg = yaml.safe_load(fh)
        # config.data.path is relative to cellot/cellot_gpu (where training ran).
        train_path = cfg["data"]["path"]
        if not os.path.isabs(train_path):
            train_path = os.path.join(CELLOT_DIR, train_path)
        if not os.path.exists(train_path):
            if axis_source == genes_txt:
                # Sidecar handover: the axis came out of the checkpoint's own
                # directory, so there is nothing left for the atlas to prove.
                print(f"  OK    [{flavor}/{model_name}] {len(axis_genes)} genes "
                      f"(axis from genes.txt; training dataset absent, not needed)")
            else:
                print(f"  ERROR [{flavor}/{model_name}] training dataset named in "
                      f"{cfg_path} does not exist: {train_path}")
                print( "          and no genes.txt sidecar is present to stand in for it.")
                print( "          Run scripts/bake_model_artifacts.py while the dataset")
                print( "          is still available, or restore the dataset.")
                ok = False
            continue
        train_genes = var_names(train_path)

        if train_genes == axis_genes:
            same = "same file" if os.path.realpath(train_path) == os.path.realpath(axis_source) else "same axis"
            print(f"  OK    [{flavor}/{model_name}] {len(axis_genes)} genes ({same} "
                  f"as {os.path.basename(axis_source)})")
        else:
            shared = len(set(train_genes) & set(axis_genes))
            print(f"  ERROR [{flavor}/{model_name}] GENE AXIS MISMATCH")
            print(f"          projecting onto : {axis_source} ({len(axis_genes)} genes)")
            print(f"          model trained on: {train_path} ({len(train_genes)} genes)")
            print(f"          genes in common : {shared}")
            print( "          Vector positions would mean different genes, so the")
            print( "          prediction would be silently wrong. Refusing to run.")
            ok = False

    # The scGen shift sidecar carries the axis it was computed against. Check it
    # here too, so a stale shift aborts before anything is written rather than in
    # phase 3 after the aligned files exist.
    shift_pt = f"{tag_dir}/scgen/cache/scgen_shift.pt"
    if os.path.exists(shift_pt):
        import torch
        rec = torch.load(shift_pt, map_location="cpu").get("gene_axis_sha256")
        if rec == axis_sha:
            print(f"  OK    [{flavor}/scgen] scgen_shift.pt axis sha256 matches "
                  f"({axis_sha[:12]}...)")
        else:
            print(f"  ERROR [{flavor}/scgen] scgen_shift.pt WAS COMPUTED ON A "
                  f"DIFFERENT GENE AXIS")
            print(f"          sidecar records : {rec}")
            print(f"          axis in use     : {axis_sha}  ({axis_source})")
            print( "          The latent shift would be applied to the wrong genes.")
            print( "          Re-bake with scripts/bake_model_artifacts.py --force.")
            ok = False

if not ok:
    print("")
    print("Preflight FAILED -- nothing was written. Fix --model-set (or the model's")
    print("config.data.path) so the projection axis and the checkpoint agree.")
    sys.exit(1)
PY

# Phase 1: preprocess into atlas namespace per flavor (analysis env)
echo ""
echo "=== Phase 1: preprocess into atlas HVG namespace ==="
$ANALYSIS_PY - "$INPUT_H5AD" "$TAG" "$OUTDIR" "$BASE" "$FLAVORS_STR" \
               "$AXIS_TEMPLATE" "$SET_SUFFIX" "$RESULTS_TEMPLATE" "$INPUT_MODE" <<'PY'
import sys, os
from pathlib import Path
import numpy as np
import pandas as pd
import anndata as ad
import scanpy as sc
import scipy.sparse as sp_sparse

(INPUT_H5AD, TAG, OUTDIR, BASE, FLAVORS, AXIS_TEMPLATE, SET_SUFFIX,
 RESULTS_TEMPLATE, INPUT_MODE) = sys.argv[1:10]
FLAVORS = FLAVORS.split()
RESULTS = f"{BASE}/cellot/cellot_gpu/results"
ORTHO_CACHE = f"{BASE}/scripts/.biomart_ortholog_cache.csv"
SYMBOL_CACHE = f"{BASE}/scripts/.bcg_symbol_to_ensmusg.csv"


def _strip_ens(x):
    x = str(x)
    return x.split(".")[0] if x.startswith("ENS") and "." in x else x


src = sc.read_h5ad(INPUT_H5AD)
print(f"  loaded: {src.shape}, var sample: {list(src.var_names[:3])}")
print(f"  input mode: {INPUT_MODE}")

# Get expression into .X. Prefer layers['counts'] in both modes (posed
# scANVI writes the atlas-batch matrix there; counts_original is ignored).
if "counts" in src.layers:
    src.X = src.layers["counts"].astype("float32")
    print("  using layers['counts']")
src.obs_names_make_unique()
src.obs["condition"] = "mouse"
src.obs["species"] = "mouse"

xs = src.X[:50].toarray().ravel() if sp_sparse.issparse(src.X) else src.X[:50].ravel()
xs = np.asarray(xs)

if INPUT_MODE == "posed_ensg":
    var_names = [_strip_ens(v) for v in src.var_names.astype(str)]
    n_ensg = sum(v.startswith("ENSG") for v in var_names[:20])
    if n_ensg < 10:
        print("ERROR: --posed-ensg expects human ENSG ids in .var_names.")
        print(f"  first names: {var_names[:5]}")
        sys.exit(1)
    print(f"  detected var_names: human ENSG (no ortholog hop)")
    print("  skipping integer-count check (scANVI posed counts are continuous)")
    src_var_idx = {}
    for i, v in enumerate(var_names):
        if v not in src_var_idx:
            src_var_idx[v] = i
    var2ensg = {v: v for v in src_var_idx}
else:
    if not np.allclose(xs, np.round(xs)):
        print("ERROR: input .X (or .layers['counts']) must be raw integer counts.")
        print("  This file looks continuous (scANVI posed counts usually are).")
        print("  If .var_names are already human ENSG, re-run with --posed-ensg")
        print("  and do NOT log1p the file first — the script still does that.")
        sys.exit(1)
    var_names = list(src.var_names.astype(str))
    is_ensembl = all(v.startswith("ENSMUSG") for v in var_names[:10])
    print(f"  detected var_names: {'ENSMUSG' if is_ensembl else 'symbols'}")

    ortho = pd.read_csv(ORTHO_CACHE)
    ensmusg2ensg = dict(zip(
        [_strip_ens(x) for x in ortho["mouse_ensembl_id"].astype(str)],
        [_strip_ens(x) for x in ortho["human_ensembl_id"].astype(str)],
    ))

    if is_ensembl:
        var2ensg = {v: ensmusg2ensg.get(_strip_ens(v)) for v in var_names}
    else:
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
                var2ensg[v] = ensmusg2ensg.get(_strip_ens(ensmusg))

    src_var_idx = {v: i for i, v in enumerate(var_names)}

# For each flavor, project onto that flavor's atlas HVG list. The list comes from
# the model's own genes.txt sidecar when it exists, which is the whole reason a
# handover does not need the 35 MB training .h5ad; otherwise from the atlas file.
for flavor in FLAVORS:
    atlas_path = f"{OUTDIR}/{AXIS_TEMPLATE.replace('{flavor}', flavor)}"
    genes_txt = f"{RESULTS}/{RESULTS_TEMPLATE.replace('{flavor}', flavor)}/genes.txt"
    if os.path.exists(genes_txt):
        with open(genes_txt) as fh:
            target_genes = [g for g in fh.read().split("\n") if g != ""]
        print(f"  {flavor}: gene axis from {genes_txt} ({len(target_genes)} genes)")
    else:
        target_genes = list(sc.read_h5ad(atlas_path).var_names.astype(str))
        print(f"  {flavor}: gene axis from {atlas_path} ({len(target_genes)} genes)")

    cols = []
    for ensg in target_genes:
        key = _strip_ens(ensg)
        match = None
        for v, e in var2ensg.items():
            if e is not None and _strip_ens(e) == key:
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
    out = f"{OUTDIR}/{TAG}_aligned_{flavor}{SET_SUFFIX}.h5ad"
    a.write_h5ad(out)
    print(f"  {flavor}: coverage {n_present}/{len(target_genes)} ({100*n_present/len(target_genes):.1f}%) -> {out}")
PY

# Phase 2: rewrite for the CellOT env (anndata 0.7.6). Suffix is _anndata07
# so it cannot be confused with the atlas_full_v07 *model set*.
# Required for the legacy CellOT env, harmless (but unnecessary) under CellOT_v3.
echo ""
echo "=== Phase 2: round-trip to anndata 0.7 format (_anndata07) ==="
for flavor in "${FLAVORS[@]}"; do
    src="$OUTDIR/${TAG}_aligned_${flavor}${SET_SUFFIX}.h5ad"
    dst="$OUTDIR/${TAG}_aligned_${flavor}${SET_SUFFIX}_anndata07.h5ad"
    [[ -f "$dst" ]] && rm -f "$dst"
    cp "$src" "$dst"
done

$CELLOT_PY - "$OUTDIR" "$TAG" "$FLAVORS_STR" "$SET_SUFFIX" <<'PY'
import sys, os, h5py, numpy as np, pandas as pd, anndata as ad
from scipy import sparse
OUTDIR, TAG, FLAVORS, SET_SUFFIX = sys.argv[1:5]
FLAVORS = FLAVORS.split()

# Strip empty groups
for flavor in FLAVORS:
    p = f"{OUTDIR}/{TAG}_aligned_{flavor}{SET_SUFFIX}_anndata07.h5ad"
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

for flavor in FLAVORS:
    p = f"{OUTDIR}/{TAG}_aligned_{flavor}{SET_SUFFIX}_anndata07.h5ad"
    with h5py.File(p,"r") as f:
        obs=load_obs(f); var=load_var(f); X=load_X(f)
    a=ad.AnnData(X=X,obs=obs,var=var)
    os.remove(p); a.write(p)
    print(f"  rewrote {p}: shape {a.shape}")
PY

# Phase 3: predict via each (flavor, model) combo
echo ""
echo "=== Phase 3: predict via ${#FLAVORS[@]}x2 trained models ==="
$CELLOT_PY - "$OUTDIR" "$TAG" "$BASE/cellot/cellot_gpu" "$FLAVORS_STR" \
             "$RESULTS_TEMPLATE" "$AXIS_TEMPLATE" "$SET_SUFFIX" <<'PY'
import sys, os, hashlib
sys.path.insert(0, sys.argv[3])
import torch, numpy as np, anndata as ad
from cellot.utils import load_config
from cellot.utils.loaders import load_data, load_model, resolve_device
from cellot.models import load_autoencoder_model
from cellot.models.ae import compute_scgen_shift

OUTDIR, TAG, CELLOT_DIR, FLAVORS, RESULTS_TEMPLATE, AXIS_TEMPLATE, SET_SUFFIX = sys.argv[1:8]
FLAVORS = FLAVORS.split()
RESULTS = f"{CELLOT_DIR}/results"


def gene_axis_sha256(genes):
    """Must stay identical to bake_model_artifacts.gene_axis_sha256."""
    h = hashlib.sha256()
    for g in genes:
        h.update(str(g).encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


for flavor in FLAVORS:
    results_subdir = RESULTS_TEMPLATE.replace("{flavor}", flavor)
    atlas_path = f"{OUTDIR}/{AXIS_TEMPLATE.replace('{flavor}', flavor)}"
    genes_txt = f"{RESULTS}/{results_subdir}/genes.txt"
    src_path = f"{OUTDIR}/{TAG}_aligned_{flavor}{SET_SUFFIX}_anndata07.h5ad"
    src = ad.read(src_path)

    # Second half of the phase-0 contract: the cells we are about to feed the
    # model must sit on the axis the model was trained on, gene for gene. The
    # axis comes from genes.txt when the model has been baked, else from the
    # atlas .h5ad -- which is also the only reason that file would be needed.
    if os.path.exists(genes_txt):
        with open(genes_txt) as fh:
            atlas_genes = [g for g in fh.read().split("\n") if g != ""]
        axis_source = genes_txt
    else:
        atlas_genes = [str(g) for g in ad.read(atlas_path).var_names]
        axis_source = atlas_path
    axis_sha = gene_axis_sha256(atlas_genes)
    src_genes = [str(g) for g in src.var_names]
    if src_genes != atlas_genes:
        print(f"  ERROR [{flavor}] aligned input is not on the model's gene axis:")
        print(f"          {src_path} ({len(src_genes)} genes)")
        print(f"          vs {axis_source} ({len(atlas_genes)} genes)")
        print( "          Delete the stale aligned file and re-run. Refusing to predict.")
        sys.exit(1)

    Xs = src.X.toarray() if hasattr(src.X, "toarray") else src.X
    inputs = torch.tensor(Xs, dtype=torch.float32)

    for model_name in ("scgen","impact_cellot"):
        results_dir = f"{RESULTS}/{results_subdir}/{model_name}"
        config = load_config(f"{results_dir}/config.yaml")
        device = resolve_device(config)
        config.data.path = atlas_path
        if "ae_emb" in config.data:
            # model-scgen is a symlink to scgen; fall back if a set lacks it.
            ae_dir = f"{RESULTS}/{results_subdir}/model-scgen"
            if not os.path.isdir(ae_dir):
                ae_dir = f"{RESULTS}/{results_subdir}/scgen"
            config.data.ae_emb.path = ae_dir

        if model_name == "scgen":
            model, _ = load_autoencoder_model(config, restore=f"{results_dir}/cache/model.pt",
                                              device=device, input_dim=len(atlas_genes))
            model.eval()
            shift_pt = f"{results_dir}/cache/scgen_shift.pt"
            if not hasattr(model, "code_means") and os.path.exists(shift_pt):
                # Baked latent shift: skip re-encoding the whole training atlas.
                # A shift computed on a different gene axis would be applied to
                # the wrong genes without erroring, so the axis hash is checked
                # before the shift is allowed anywhere near the model.
                sidecar = torch.load(shift_pt, map_location=device)
                rec = sidecar.get("gene_axis_sha256")
                if rec != axis_sha:
                    print(f"  ERROR [{flavor}/scgen] {shift_pt} was computed on a "
                          f"different gene axis:")
                    print(f"          sidecar records : {rec} "
                          f"({sidecar.get('n_genes')} genes)")
                    print(f"          axis in use     : {axis_sha} "
                          f"({len(atlas_genes)} genes, {axis_source})")
                    print( "          Refusing to predict. Re-bake with")
                    print( "          scripts/bake_model_artifacts.py --force.")
                    sys.exit(1)
                missing = {"human", "mouse"} - set(sidecar.get("code_means", {}))
                if missing:
                    print(f"  ERROR [{flavor}/scgen] {shift_pt} has no code_means for "
                          f"{sorted(missing)}")
                    sys.exit(1)
                model.code_means = {k: v.to(device)
                                    for k, v in sidecar["code_means"].items()}
                print(f"    [{flavor}/scgen] latent shift from scgen_shift.pt "
                      f"(baked {sidecar.get('created_utc')}, "
                      f"{sidecar.get('n_cells_encoded')} cells) -- training atlas not read")
            if not hasattr(model, "code_means"):
                print(f"    [{flavor}/scgen] no scgen_shift.pt sidecar -- recomputing "
                      f"the latent shift from {config.data.path}")
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

        out_path = f"{OUTDIR}/{TAG}_predicted_human_via_{model_name}_{flavor}{SET_SUFFIX}.h5ad"
        ad.AnnData(X=pred.astype(np.float32),
                   obs=src.obs.copy(), var=src.var.copy()).write(out_path)
        print(f"  wrote {out_path}: shape {pred.shape}")
PY

echo ""
echo "=== DONE ==="
echo ""
echo "Predictions written to:"
ls -1 "$OUTDIR/${TAG}_predicted_human_via_"*"${SET_SUFFIX}.h5ad" 2>/dev/null | sed 's/^/  /'
echo ""
echo "Coverage info: shown above in Phase 1 output"

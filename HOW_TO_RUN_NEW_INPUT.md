# How to Run New Input Through the Cross-Species Pipeline

A practical guide for running mouse single-cell input through a trained cross-species model and getting predicted human cells, plus optional evaluation and figures.

**Intended audience**: anyone (Junyi, mentor, future-self) who wants to take a new mouse single-cell `.h5ad` file and get predicted human-cell expression for it, using one of the models we trained in May 2026.

---

## 0. TL;DR — copy-paste this to reproduce the May-8 BCG pipeline end-to-end

```bash
cd /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT
bash scripts/run_full_pipeline.sh
```

This single command does everything: prepares atlas-full data → submits 4 trainings (waits for them) → preprocesses your input file → predicts → renders figures. About 60–90 minutes wall time end-to-end. See `scripts/run_full_pipeline.sh` for the actual steps if you want to run them piecewise.

If you want to skip the training step and only run NEW input through ALREADY-TRAINED models (the common case for the mentor), use:

```bash
cd /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT
bash scripts/predict_new_input.sh /path/to/your_mouse.h5ad
```

---

## 1. The 30-second mental model

```
mouse cells (1000-d gene exp)
        ↓ scGen encoder (50-d code)
        ↓ scGen baseline:  + fixed shift = code_means["human"] - code_means["mouse"]
        ↓ IMPACT_CellOT:   transport map g(z): R^50 -> R^50 (learned via OT)
        ↓ scGen decoder
predicted human cells (1000-d gene exp)
```

- One scGen autoencoder is trained per (HVG-flavor, dataset) configuration. It serves both as the standalone baseline AND as the encoder/decoder for IMPACT_CellOT.
- IMPACT_CellOT learns a transport map `g(z)` in the AE's latent space, on top of the same scGen.
- Two flavors used in the May-8 atlas-full setup: `seurat_v3` and `pearson_residuals`.
- Two models per flavor: `scgen` and `impact_cellot`. So 4 trainings total.

---

## 2. Required environments

This project uses two conda envs because the upstream cellot library was pinned to old anndata.

| Env | Where it lives | Used for |
|---|---|---|
| `analysis` | `/n/home01/jzhou1125/miniforge3/envs/analysis` | scanpy 1.12, anndata 0.12, BioMart, plotting, all preprocessing notebooks |
| `CellOT` | `/n/home01/jzhou1125/.conda/envs/CellOT` | scanpy 1.8.1, anndata 0.7, the cellot package; `train.py` and `evaluate.py` |

**Rule of thumb**: anything in `speciesOT/baseline/analysis/` runs in `analysis`. Anything under `cellot/cellot_gpu/scripts/` runs in `CellOT`.

To activate: `mamba activate analysis` or `mamba activate CellOT` (after `module load python` if you're on a fresh shell).

---

## 3. Required artifacts on disk

For any prediction run you need:
1. **Trained model weights**: `cellot/cellot_gpu/results/<run_tag>/<model>/cache/model.pt`
2. **The AE encoder** (for IMPACT only): pointed to via the `model-scgen` symlink under `<run_tag>/`
3. **The data file** that defines the gene namespace: `cellot/cellot_gpu/datasets/.../<dataset>_v07.h5ad`. The model was trained against this dataset's columns; any new input has to be projected into the same column space.

The May-8 atlas-full models live at:
```
cellot/cellot_gpu/results/atlas_full_seurat_v3/{scgen,impact_cellot}/cache/model.pt
cellot/cellot_gpu/results/atlas_full_pearson_residuals/{scgen,impact_cellot}/cache/model.pt
```
And their column-space anchors at:
```
cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_seurat_v3_atlas_full_v07.h5ad
cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_atlas_full_v07.h5ad
```

---

## 4. End-to-end recipe (worked example: BCG mouse → predicted human)

### Step 4.1 — Get your raw mouse `.h5ad` file ready

You need:
- An AnnData with mouse cells in `.X` or `.layers['counts']`. **Raw integer counts**, not normalized.
- `var_names` should be either Ensembl IDs (ENSMUSG*) or gene symbols. If symbols, you'll BioMart-map to ENSMUSG in step 4.2.

For the BCG worked example: source is `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/tb/data/bcg_mouse_aligned_050626.h5ad` (1,406 cells, mouse symbols, raw in `.layers['counts']`).

### Step 4.2 — Project new input onto the atlas's gene namespace

```bash
mamba activate analysis
jupyter nbconvert --to notebook --execute --inplace \
    speciesOT/baseline/analysis/16_bcg_mouse_data_prep.ipynb
```

Or, if you have your own input, copy notebook 16 and edit the source path. The notebook does:
1. Load your raw mouse cells.
2. Map gene symbols → ENSMUSG (BioMart, cached to `scripts/.bcg_symbol_to_ensmusg.csv`).
3. Use the cached BioMart ortholog table (`scripts/.biomart_ortholog_cache.csv`, written by notebook 15) for ENSMUSG → ENSG.
4. For each flavor, subset to the atlas's per-flavor 1000 ENSG list. Genes missing from your input are filled with zero. Coverage is reported.
5. `normalize_total + log1p`.
6. CellOT-env round-trip (anndata 0.7 compat).

Outputs land at `cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/<your_dataset>_<flavor>_v07.h5ad`.

### Step 4.3 — (Optional) Train the cross-species model from scratch

If you don't already have `model.pt`, regenerate the configs and submit:
```bash
python scripts/generate_atlas_full_configs.py
# This creates 4 sbatch scripts under sbatch/train/

# Submit scGen first (it's the AE encoder for IMPACT)
SC1=$(sbatch --parsable sbatch/train/train_atlas_full_seurat_v3_scgen.sbatch)
SC2=$(sbatch --parsable sbatch/train/train_atlas_full_pearson_residuals_scgen.sbatch)

# Then IMPACT, with afterok dependency on its scGen
sbatch --dependency=afterok:$SC1 sbatch/train/train_atlas_full_seurat_v3_impact_cellot.sbatch
sbatch --dependency=afterok:$SC2 sbatch/train/train_atlas_full_pearson_residuals_impact_cellot.sbatch
```
Wall times: scGen ~25 min on `shared` (CPU), IMPACT ~35 min on `gpu_requeue` (GPU).

### Step 4.4 — Predict on your new input

```bash
mamba activate analysis
jupyter nbconvert --to notebook --execute --inplace \
    speciesOT/baseline/analysis/17_bcg_prediction.ipynb
```

The notebook:
- Shells out to the `CellOT` env Python (because that's where the cellot library is installed).
- For each (flavor, model), loads `model.pt`, computes `code_means` from the atlas training data (for scGen), runs the forward pass on your new mouse cells, decodes back to gene space.
- Writes `bcg_predicted_human_via_{model}_{flavor}.h5ad` to the datasets dir.
- Renders a qualitative UMAP overlay per flavor (atlas mouse / atlas human / BCG mouse / scGen pred / IMPACT pred) — figures land under `bcg_prediction_outputs/figures/`.

For your own input, copy notebook 17 and change the input/output path strings.

### Step 4.5 — (Optional) Quantitative evaluation against ground truth

Skip this step if you don't have real human cells to compare against. We don't have BCG-real-human integrated yet, so the May-8 deliverable stops at step 4.4.

If you DO have ground truth, the cellot-env `evaluate.py` is the canonical entry point:
```bash
mamba activate CellOT
cd cellot/cellot_gpu
python ./scripts/evaluate.py \
    --outdir ./results/<run_tag>/<model> \
    --setting ood \
    --where data_space \
    --n_cells 30,50,80 \
    --embedding ae    # IMPORTANT for IMPACT data-space eval; without it the decoder is skipped
```
This writes `evals.csv` and `imputed.h5ad` to `<run_tag>/<model>/evals_ood_data_space/`.

---

## 5. Generating the meeting figures

### From the existing 5-flavor matrix (notebooks 13, 14, 18)

```bash
mamba activate analysis
jupyter nbconvert --to notebook --execute --inplace speciesOT/baseline/analysis/13_hvg_flavor_results.ipynb  # matrix-wide heatmaps + biomarker matrix
jupyter nbconvert --to notebook --execute --inplace speciesOT/baseline/analysis/14_hvg_flavor_notebook6_replica.ipynb  # per-cell deep dives
jupyter nbconvert --to notebook --execute --inplace speciesOT/baseline/analysis/18_paper_figure_F_G_replica.ipynb  # paper-figure F + G replicas

# Or invoke the standalone matplotlib-Agg renderer (writes PDFs/PNGs without needing nbconvert):
python scripts/render_results_figures.py
```

Outputs:
- `speciesOT/baseline/analysis/hvg_flavor_results_outputs/figures/` — matrix-wide heatmaps, gap scatter, biomarker selection matrix, biomarker density (best cell).
- `speciesOT/baseline/analysis/hvg_flavor_nb14_outputs/figures/` — per-cell scatter, UMAP overlay, density panels.
- `speciesOT/baseline/analysis/paper_figure_replica_outputs/figures/` — paper-style figure F (R²/MMD bar plots) and figure G (per-marker density).

### Reusable plotting functions (the modular part)

Two functions in `scripts/render_results_figures.py` accept any results DataFrame:
```python
from scripts.render_results_figures import plot_metric_bars, plot_marginals_paper_style

# Figure F: bar plot. Works on any long-form results CSV.
plot_metric_bars(
    long_df=my_eval_dataframe,           # cols: ['metric', 'value', flavor, group, mode, model]
    metric="r2-means",
    group_by="group", hue_by="model", facet_by="flavor",
    metric_label="R² of means",
    out_path="my_figure_F.pdf",
)

# Figure G: per-marker density. Works on any (target, predictions, source) triple.
plot_marginals_paper_style(
    actual_target=human_X,                # np array (n_cells, n_genes)
    predicted_traces={"scGen pred": pred1_X, "IMPACT pred": pred2_X},
    gene_panel={"PTPRC (CD45)": "ENSG00000081237", ...},
    var_index_lookup={ensg_id: column_index, ...},
    actual_source=mouse_X,                # optional
    title="My title",
    out_path="my_figure_G.pdf",
)
```
When the BCG-vs-real-human comparison becomes available, point these same functions at that data and you get the same figures.

---

## 6. Outputs explained

| File | What it is |
|---|---|
| `<run_tag>/<model>/cache/model.pt` | Trained model weights. For scGen, also contains `code_means` after `compute_scgen_shift`. For IMPACT, contains the f and g networks. |
| `<run_tag>/<model>/cache/last.pt` | Last-iteration checkpoint (probably not the best). Used only for resume-from-checkpoint. |
| `<run_tag>/<model>/cache/scalars` | HDF5 / PyTables file with logged training and eval metrics per step. Read with h5py + the `eval/table` and `train/table` keys. |
| `<run_tag>/<model>/evals_ood_<where>/imputed.h5ad` | Predicted human cells from the OOD source half. Shape depends on `--where`: 50-d for `latent_space`, 1000-d for `data_space` (only if `--embedding ae` was passed for IMPACT). |
| `<run_tag>/<model>/evals_ood_<where>/evals.csv` | Long-form metric values: `[ncells, nfeatures, metric, value]`. Multiple rows per `(ncells, metric)` because `n_reps=10` subsamples are run. |

---

## HVG correctness — what each flavor consumes (per scanpy docs)

The [scanpy docs](https://scanpy.readthedocs.io/en/stable/generated/scanpy.pp.highly_variable_genes.html) specify that `highly_variable_genes` "expects logarithmized data, except when `flavor='seurat_v3'`/`'seurat_v3_paper'`, in which count data is expected." `pearson_residuals` (in `scanpy.experimental.pp`) likewise expects raw counts. We honor this contract:

| Flavor | Expected input | Our dispatcher passes |
|---|---|---|
| `seurat` | log-normalized | `.X` (after `normalize_total + log1p`) |
| `cell_ranger` | log-normalized | `.X` (after `normalize_total + log1p`) |
| `seurat_v3` | **raw counts** | `layer="counts"` (int32 raw) |
| `seurat_v3_paper` | **raw counts** | `layer="counts"` (int32 raw) |
| `pearson_residuals` | **raw counts** | `layer="counts"` (int32 raw) |

The dispatcher logic lives in `01.5_data_prep_all_holdouts_hvg_flavors.ipynb` (matrix experiments) and `15_data_prep_full_atlas_no_holdout.ipynb` (atlas-full, the May-8 setup) — both share the same `run_hvg_flavor()` function. All flavors use `batch_key="species"` so HVG selection is balanced across mouse and human.

Notebook 16 does NOT re-select HVG on BCG. It inherits the atlas's per-flavor 1000-gene list (read from `hvg_{flavor}_atlas_full_v07.h5ad`'s `var_names`) and projects BCG onto it. That's the correct cross-species recipe — you cannot reselect HVG on the test set, the model expects exactly the column space it trained on.

## What HVGs were actually selected (May-8 atlas-full)

Top-15 per flavor (human gene symbols), full lists at `speciesOT/baseline/analysis/atlas_full_outputs/hvg_atlas_full_{seurat_v3,pearson_residuals}.csv`:

| Rank | seurat_v3 | pearson_residuals |
|---|---|---|
| 1 | SFTPC (lung surfactant) | LYZ (monocyte) |
| 2 | MYL9 (smooth muscle) | FAU (ribosomal) |
| 3 | TNFRSF4 (OX40) | SFTPC |
| 4 | ACTA2 (smooth muscle) | BACH2 (T/B cell TF) |
| 5 | TNNI3 (cardiac) | CD74 (MHC II) |
| 6 | MYL7 (cardiac) | LAMA2 |
| 7 | A2M | S100A8 (myeloid) |
| 8 | CYTL1 (HSC niche) | PDE4D |
| 9 | PI16 | PRKG1 |
| 10 | TNNT2 (cardiac) | UBA52 (ribosomal) |
| 11 | S100A8 | TMSB4Y |
| 12 | SOSTDC1 | KCNQ5 |
| 13 | TAGLN (smooth muscle) | VCAN |
| 14 | SFTPB (lung) | RPL37A (ribosomal) |
| 15 | NPPA (cardiac) | MACROD2 |

Of the 12 curated immune-marker panel (`PTPRC/CD3E/CD4/CD8A/CD5/CD7/CCR7/NCAM1/MS4A1/CD19/CD14/ITGAM`):
- `seurat_v3` selected 8/12 (CCR7, CD4, CD5, CD7, CD8A, CD14, CD19, MS4A1, NCAM1)
- `pearson_residuals` selected 6/12 — and uniquely **PTPRC (CD45)** and **CD3E**, the most lineage-defining markers
- Neither selected ITGAM (CD11b)

Pivot table at `atlas_full_outputs/biomarker_selection_atlas_full.csv`.

## BCG coverage of each flavor's HVG list

| Flavor | Atlas HVG present in BCG | Zero-filled |
|---|---|---|
| seurat_v3 | **531 / 1000 (53.1%)** | 469 |
| pearson_residuals | **650 / 1000 (65.0%)** | 350 |

**This is a big practical reason to prefer `pearson_residuals` for the BCG pipeline.** The atlas's seurat_v3 HVG are dominated by tissue-specific structural genes (lung, heart, smooth muscle) which the BCG dataset doesn't measure (BCG was filtered to immune-relevant genes). Pearson picks more lineage/immune genes that overlap with what BCG actually has on disk. Full table at `speciesOT/baseline/analysis/bcg_mouse_outputs/bcg_atlas_hvg_coverage.csv`.

## Known limitations of the May-8 setup (call out to mentor)

1. **Zero-fill on missing genes** is biased toward "not expressed". Better long-term fix: re-select HVG on the intersection of (atlas-measured ∩ BCG-measured) and re-train. Code path is in `15_data_prep_full_atlas_no_holdout.ipynb` §3 — change `run_hvg_flavor`'s candidate gene set before calling it.
2. **No batch correction between atlas and BCG.** They were preprocessed independently. The whole point of scGen + IMPACT is to bridge that gap, but the bridge was learned from atlas-internal mouse↔human pairs, not from atlas↔BCG pairs.
3. **scGen shift is a single fixed vector** in 50-d latent. All 1,406 BCG cells get shifted by the exact same direction. The fact that we see two output islands in the predicted-human UMAP (one per BCG treatment status) is purely because the encoder produced two source islands first; the shift just translated them in unison.
4. **BCG cell identity (`LT-HSC` vs `LT-HSC treated`) is preserved through the pipeline** because notebook 16 keeps the `cell_type` obs column. Color the UMAP by `cell_type` to see treatment-vs-baseline; color by `condition` to see species/cohort.

## 7. Common pitfalls (we've hit these — don't repeat)

1. **The `r2-*` columns in `evals.csv` are Pearson r, NOT R².** Upstream `evaluate.py` calls `pd.Series.corr(...)` which returns the raw correlation. Square the value to get true R². Notebook 13, 14, 18 and the standalone renderer all square automatically (see "R² semantics" notes in those notebooks).

2. **`--where data_space` for IMPACT_CellOT requires `--embedding ae`**, otherwise the decoder is silently skipped and `imputed.h5ad` stays in 50-d latent space. scGen's data-space eval works without the flag because scGen has its own internal encoder/decoder; IMPACT needs the AE projector loaded explicitly.

3. **`--n_cells` defaults are too large for our held-out pools.** Default is `100,250,500,1000,1500`. Group A has ~97 eval cells, Group D has ~48. Pass `--n_cells 30,50,80` (or `20,30,40` for D) instead.

4. **The CellOT env (`anndata 0.7`) cannot read `.h5ad` files written by the analysis env (`anndata 0.12`)** without a strip + rewrite step. See notebook 16 §5 for the canonical strip+rewrite snippet (uses h5py to remove empty placeholder groups, then re-saves via the CellOT env).

5. **Mouse gene symbols must be mapped to ENSG (human Ensembl) before being fed to a trained model.** Two-step: `mouse_symbol → ENSMUSG (BioMart)` then `ENSMUSG → ENSG (BioMart ortholog one2one)`. Both queries cached on disk to handle BioMart flakiness.

6. **`raw counts must be int32` for `seurat_v3`/`seurat_v3_paper`/`pearson_residuals` HVG.** scanpy's safe-cast check rejects float32 even when the values are integer-equivalent. Cast `.layers['counts']` to int32 at source.

7. **Don't trust `model.pt` from runs where `model-scgen` symlink is missing in the result dir.** IMPACT's `evaluate.py` looks for `expdir.parent / "model-scgen"` to find the AE; without it, projector loading silently falls back to identity functions and the data-space numbers are wrong.

---

## 8. Quick reference: which notebook does what?

| Notebook | Role |
|---|---|
| `01.5_data_prep_all_holdouts_hvg_flavors.ipynb` | 5-flavor x 4-group HVG matrix data prep (the original 80-experiment matrix) |
| `13_hvg_flavor_results.ipynb` | Aggregator + heatmaps + gap scatter + biomarker selection matrix for the matrix |
| `14_hvg_flavor_notebook6_replica.ipynb` | Per-cell deep-dive figures (scatter + UMAP + 12-marker density) for the matrix |
| `15_data_prep_full_atlas_no_holdout.ipynb` | NEW: data prep for the no-holdout atlas-full training (2 flavors only) |
| `16_bcg_mouse_data_prep.ipynb` | NEW: align BCG mouse data to atlas gene space |
| `17_bcg_prediction.ipynb` | NEW: predict human cells from BCG mouse using trained models, qualitative UMAP overlay |
| `18_paper_figure_F_G_replica.ipynb` | NEW: paper-style figure F (R²/MMD bars) and figure G (biomarker density) using reusable functions |

---

## 9. The minimal command sequence (no thinking required)

```bash
# 0. Activate conda; if you need to run from scratch
mamba activate analysis

# 1. Generate the no-holdout atlas datasets (writes to cellot/cellot_gpu/datasets/...)
jupyter nbconvert --to notebook --execute --inplace \
    speciesOT/baseline/analysis/15_data_prep_full_atlas_no_holdout.ipynb

# 2. Generate config + sbatch + submit 4 atlas-full trainings
python scripts/generate_atlas_full_configs.py
SC1=$(sbatch --parsable sbatch/train/train_atlas_full_seurat_v3_scgen.sbatch)
SC2=$(sbatch --parsable sbatch/train/train_atlas_full_pearson_residuals_scgen.sbatch)
sbatch --dependency=afterok:$SC1 sbatch/train/train_atlas_full_seurat_v3_impact_cellot.sbatch
sbatch --dependency=afterok:$SC2 sbatch/train/train_atlas_full_pearson_residuals_impact_cellot.sbatch
# Wait for trainings to finish (~30 min for scGen + ~35 min for IMPACT)

# 3. Preprocess BCG mouse to match atlas gene space
jupyter nbconvert --to notebook --execute --inplace \
    speciesOT/baseline/analysis/16_bcg_mouse_data_prep.ipynb

# 4. Predict human cells from BCG mouse + render qualitative UMAP
jupyter nbconvert --to notebook --execute --inplace \
    speciesOT/baseline/analysis/17_bcg_prediction.ipynb

# 5. Generate paper-style figures from the existing 5-flavor matrix
jupyter nbconvert --to notebook --execute --inplace \
    speciesOT/baseline/analysis/18_paper_figure_F_G_replica.ipynb
```

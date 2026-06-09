# Mentor meeting briefing — 2026-05-26

**Theme for this meeting**: shift from "Does IMPACT_CellOT learn the species transport?" (held-out cell-type framing — done) to "Can IMPACT_CellOT learn the drug effect using BCG?" (atlas-full framing — in progress). The summer's most impactful lever is **improving the size and balancedness of the atlas training set**, because the current atlas matrix is much smaller and more cell-type-skewed than is widely realized.

---

## 1. Where we are

### What's been delivered (recap, no new content needed here)

- **HVG-flavor × holdout × IID/OOD × model** matrix is complete (notebooks `01.5`, `13`, `14`, `presentation_preparation.ipynb`). Headline: IMPACT_CellOT wins IID handily; scGen often catches up on OOD. Pearson residuals is the only HVG flavor that rescues PTPRC into the top-1000.
- **Presentation Figures F, G, R² scatter, UMAPs, IID-vs-OOD bars** all rendered for CD8 holdout and M2-monocyte holdout, both flavors. Files under `speciesOT/baseline/analysis/presentation_figure_outputs/`.

### What's new in the last two weeks (and what this meeting should land)

| Notebook | What it does | Status |
|---|---|---|
| `15_data_prep_full_atlas_no_holdout.ipynb` | Re-prep atlas with **no holdout** (so the model sees every cell type, then can be queried on BCG). Two flavors: `seurat_v3`, `pearson_residuals`. | **Done, produced 4 trained models** (`atlas_full_{flavor}/{scgen,impact_cellot}`). |
| `16_bcg_mouse_data_prep.ipynb` | Project BCG mouse cells onto the atlas HVG namespace so they can be pushed through the trained model. | **Done but design-debt**: uses mentor's scANVI `.X` (not Scanpy `log1p`) → normalization mismatches the training matrix; only 43–58% of atlas HVGs exist in BCG → other 42–57% are zero-filled. |
| `16.1_bcg_mouse_data_prep_atlas_hvg_intersection.ipynb` | Alternative: re-derive raw counts → `log1p` (matches atlas) and keep **only** HVGs that exist in BCG. | **Done**, but the output has ~600 columns instead of 1000 — incompatible with the existing trained checkpoint. |
| `17_bcg_prediction.ipynb` | Push BCG → predicted human via both models × both flavors. | **Mostly done**; one run errored mid-pipeline. Outputs four `bcg_predicted_human_via_*.h5ad` + UMAP overlays. No quantitative eval yet (no real human BCG data integrated). |

**Honest status**: the BCG line works end-to-end but the data prep has unresolved issues (see §3). The big-picture decision the meeting needs is *not* "fix BCG plumbing now" — it's "what's the right shape of the atlas training set, before we re-train and re-run BCG through it."

---

## 2. The improvement axes — ranked by what's most actionable this summer

From the list:

1. Hyperparameter optimization
2. Model design
3. **Improving size and balancedness of the training dataset** ← *this meeting*
4. Unbalanced OT in CellOT
5. Use CellOT transport plan to do supervised ML using non-orthologs / PCA space (different in/out dims)
6. Compare neural OT vs standard OT + supervised ML in latent space

**Why (3) goes first**: the atlas training matrix is **smaller and more imbalanced than the labels suggest**, and we don't need any architectural change or external library to fix it — just rerun `15` with different filters. (1), (2), (4)–(6) are all downstream of having a defensible training matrix.

---

## 3. The dataset audit — concrete numbers from `15_data_prep_full_atlas_no_holdout.ipynb`

The "full atlas no holdout" matrix that `atlas_full_{flavor}` was trained on is **8,610 cells total (4,305 mouse + 4,305 human)** over 1,000 HVG. Three things compound to get us there.

### 3a. The 1000-cells-per-type cap (upstream, applied before this repo even sees the data)

In `speciesOT/tabula_make_samples.ipynb`, `sample_cells_by_type(..., max_per_type=1000, ...)` is run on each of `tabula_muris_all.h5ad` (mouse) and `tabula_sapiens_all.h5ad` (human). Any cell type with >1000 cells is uniformly subsampled to 1000. The result is then filtered to the shared cell-type set to give us:

- `sampled_mouse_shared.h5ad`: **47,807** cells, 40 donors
- `sampled_human_shared.h5ad`: **58,931** cells, 24 donors

Direct evidence the cap is binding (from notebook 15 §1c output):
- Mouse `hematopoietic stem cell`: **exactly n = 1000** in the sampled file (993 Smart-seq2 + 7 v2). It is not a coincidence.

So before we ever start matching, we have already thrown away a large fraction of the original Tabula data on the high-count cell types.

### 3b. The (cell_type_ontology, tissue) one-to-one match (in notebook 15, `match_cells_by_celltype_tissue`)

For each shared `(cell_type, tissue)` identity, keeps `min(n_mouse, n_human)` cells from each species. This is what guarantees the two species have identical multisets — but it's also what causes the dominant loss.

Before/after, after the v2/v3 assay filter:
- mouse v2 aligned: **30,326** cells
- human v3 aligned: **51,192** cells
- after matching: **4,305 / 4,305** ← *that is 86% of mouse data and 92% of human data discarded by the matcher alone*

### 3c. The resulting per-cell-type distribution (matched, mouse side; same on human side)

From notebook 15, cell 4 output:

```
HSPC                            891
intermediate monocyte           504
non-classical monocyte          365
natural killer cell             351
vein endothelial cell           278
fibroblast of cardiac tissue    242
thymocyte                       226
bronchial smooth muscle cell    187
endothelial cell                153
B cell                          153
basophil                        143
plasma cell                     132
pulmonary alveolar type 2 cell  125
large intestine goblet cell      93
T cell                           76
classical monocyte               74
macrophage                       69
pericyte                         61
monocyte                         36
CD8-positive, alpha-beta T cell  31
smooth muscle cell               27
plasmacytoid dendritic cell      27
fibroblast                       26
CD4-positive, alpha-beta T cell  25
myeloid dendritic cell            5
neutrophil                        4
erythrocyte                       1
```

- The top type (HSPC) is **891× the bottom** (erythrocyte).
- BCG cells are **LT-HSC** — i.e., we will be querying the model with cells that map closest to HSPC. The training matrix has 891 HSPC pairs (good news) but only 25–31 CD4/CD8 T-cell pairs (which matters whenever we expect drug effects to differ across the T/myeloid axes the BCG paper highlights).

### 3d. The drop-by-stage waterfall (suggested figure for the meeting)

| Stage | Mouse cells | Human cells |
|---|---|---|
| `tabula_muris_all` / `tabula_sapiens_all` (original) | hundreds of thousands | hundreds of thousands |
| After `max_per_type=1000` cap → `sampled_*_1000.h5ad` | — | — |
| After shared-cell-type filter → `sampled_*_shared.h5ad` | 47,807 | 58,931 |
| After BioMart one-to-one ortholog align (gene-side; cells unchanged) | 47,807 | 58,931 |
| After HSPC merge (relabeling only; cells unchanged) | 47,807 | 58,931 |
| After v2/v3 assay subset | 30,326 | 51,192 |
| After `match_cells_by_celltype_tissue` (1:1 by `(cell_type, tissue)`) | **4,305** | **4,305** |

We are training on ~4% of the originally sampled cells, with ~30× imbalance across the cell types that survive.

---

## 4. Three concrete proposals to grow / re-balance the atlas

Each is a small modification to notebook 15 — no new code architecture required. Numbers below are the rough yield improvement; exact numbers can be locked in by re-running the relevant cells.

### Proposal A: raise the per-type cap upstream (low effort, biggest single lever)

- Re-run `tabula_make_samples.ipynb` with `max_per_type` set to e.g. **5000** or `None`.
- Expected effect: the matched output should grow from ~4,305 pairs to roughly **15–25k pairs** (capped by the smaller side per identity, mostly mouse for many types).
- Risk: HVG selection becomes dominated by the most populous types (esp. HSPC). Mitigation: keep the cap in place but raise the ceiling to e.g. 3000 instead of 1000.

### Proposal B: drop the v2/v3 assay filter (medium effort, restores cross-protocol diversity)

- The notebook already builds the comparison: §1b shows **no-assay-filter** gives **6,495 matched pairs vs 4,305** for v2/v3 — a **~51% increase** without retraining anything upstream.
- Cost: mixed Smart-seq2 + 10x v2/v3 introduces batch effects. Mitigation: pass `batch_key='assay'` (or `'assay × species'`) to HVG selection and possibly to the normalization step.
- This is essentially a 5-line change in notebook 15 cell 3 and an extra batch_key in cell 14.

### Proposal C: stratified subsampling instead of `min(n1, n2)` matching (low effort, fixes the 891-vs-1 ratio)

- The current `match_cells_by_celltype_tissue` is implicitly "pool maximization" — for each identity it keeps `min(n_mouse, n_human)`.
- Replace with a quota: e.g. "keep at most K=200 pairs per `(cell_type, tissue)`, but require at least 5 to keep an identity." Rare types get all their data, common types stop dominating the gradient.
- Helper to swap is already in `speciesot_helpers.py` (look at the `cell_number` arg on `match_cells_by_celltype_tissue` — currently it samples *globally*, not per identity; modifying to per-identity is ~20 lines).

### Combining all three

| Combination | Approx. matched-pair count | Per-type max | Per-type min (after merge of rare-into-Other) |
|---|---|---|---|
| Current (cap=1000, v2/v3 only, min-match) | 4,305 | 891 | 1 |
| A only (raise cap to 5000, keep v2/v3) | ~15k | ~3k | similar (rare types unchanged) |
| B only (no assay filter, keep cap=1000) | ~6,500 | similar | similar |
| C only (quota K=200, keep v2/v3) | ~3k | 200 | 5+ |
| A + B (raise cap + drop filter) | ~25k+ | ~5k | similar |
| **A + B + C** (raise cap + drop filter + per-type quota K=500) | **~10–15k**, balanced | 500 | 5+ |

The recommended starting point is **A + B + C with K=500**: keeps total size large (~10k+ matched pairs vs current 4,305), caps per-type at 500 so no single type dominates, and uses all assays for diversity.

---

## 5. What this meeting needs to decide

1. **OK to re-prep the atlas with one of the above combinations** (default proposal: A + B + C, K=500). I'll modify `15_data_prep_full_atlas_no_holdout.ipynb` to produce a `_v2` set of outputs, retrain the four `atlas_full_{flavor}` models, and re-run notebook 17's BCG → human prediction with the new models. End-to-end this is one or two work days of GPU time.
2. **Acknowledge the unresolved BCG normalization mismatch** (`16` uses scANVI `.X`, `16.1` uses Scanpy `log1p` on raw counts but breaks the 1000-gene shape). The clean fix is: in the new notebook `15_v2`, select HVGs from `intersection(atlas_HVG_candidate_pool, BCG_genes)` so the trained model and the BCG query object share the same gene list. This is also a one-line conceptual change but needs to land alongside (1).
3. **Defer the other improvement axes** (hyperparameters, model design, unbalanced OT, transport-plan-as-features, neural-OT vs. classical-OT comparison) until after the new atlas matrix is trained, so we have a stable baseline to measure them against.

---

## 6. Open questions to put to the mentor

- **HSPC cap**: tabula_muris has only ~1000 HSC (most Smart-seq2). Even if we raise the upstream cap, mouse HSPC count stays small. Should we accept that or augment from another atlas?
- **Smart-seq2 inclusion (Proposal B)**: yes/no for mixing in the training matrix? If yes, do we trust an `assay`-batched HVG selection to absorb the chemistry differences?
- **Quota K** for Proposal C: what's a defensible per-type cap? 200, 500, 1000? Anything larger essentially reproduces the current behavior on the populous types.
- **Per-`(cell_type, tissue)` vs per-`cell_type` quota**: tissue-stratified preserves anatomical diversity; cell-type-stratified is simpler. Which does the meeting prefer?

---

## 7. After this meeting (logistics)

If the meeting greenlights the re-prep:
1. Add `cell_number_per_identity` / `min_per_identity` args to `match_cells_by_celltype_tissue` in `speciesot_helpers.py`.
2. Fork `15_data_prep_full_atlas_no_holdout.ipynb` → `15.1_data_prep_full_atlas_balanced.ipynb` with the new sampling rule and an `intersection(atlas_pool, BCG_genes)` HVG selection.
3. Re-run `generate_atlas_full_configs.py` pointing at the new `_v07` files; trigger 4 trainings (2 flavors × 2 models).
4. Re-run notebook 16 and 17 against the new models; produce a `bcg_predictions_v2/` figure set.

Estimated end-to-end: 1–2 days, dominated by IMPACT_CellOT training (12 h on `gpu_requeue` per flavor).

---

## 8. Controlled A/B experiment — staged for the meeting

To answer the natural follow-up — "OK but does removing the cap actually move the R²?" — we set up a **single controlled experiment** that's apples-to-apples against an already-trained baseline.

| | Baseline (existing) | New (uncapped) |
|---|---|---|
| Data source | `sampled_*_shared.h5ad` (capped at 1000/type upstream) | `tabula_*_all.h5ad` (uncapped) |
| Pipeline | `01.5` (no assay filter, matched 1:1) | identical |
| HVG flavor | `pearson_residuals`, top 1000, batch_key=`species` | identical |
| Holdout group | a (`CD8`, `CL:0000625`) | identical |
| Train mode | `toggle_ood`, mode=`ood`, `random_state=0` | identical |
| Model | `impact_cellot` + `scgen` baseline | identical |
| **Trained model dir** | `results/hvg_pearson_residuals_a_ood/` | `results/hvg_pearson_residuals_a_ood_uncapped/` |
| **Data file** | `hvg_pearson_residuals_a_v07.h5ad` | `hvg_pearson_residuals_a_uncapped_v07.h5ad` |
| **Only difference** | upstream 1000-per-type cap is applied | upstream cap is removed |

**Pre-cap pool size** (measured by `speciesOT/baseline/analysis/19_uncapped_cd8_ood_data_prep.py`, completed 2026-05-26 12:11):

| | Capped (current) | Uncapped (new) | Ratio |
|---|---|---|---|
| Mouse pool | 47,807 | **356,213** | **7.4×** |
| Human pool | 58,931 | **1,136,218** | **19.3×** |
| Matched pairs (after BioMart + 1:1 (cell_type, tissue) match, no assay filter) | 6,495 / 6,495 | **62,443 / 62,443** | **9.6×** |
| Held-out CD8 cells (stacked, available for OOD eval) | 390 | **2,996** | **7.7×** |

The 9.6× pair-count increase is the headline. The 7.7× CD8 expansion means the **OOD evaluation itself becomes much more statistically stable** — the existing eval was bottlenecked at ~195 mouse CD8 / 195 human CD8.

**Per-cell-type composition change** (selected rows; full table at `speciesOT/baseline/analysis/uncapped_outputs/per_celltype_counts.csv`, plot at `…/per_celltype_counts_comparison.png`):

| cell_type | capped | uncapped | delta |
|---|---:|---:|---:|
| B cell | 406 | 38,292 | +37,886 |
| hepatocyte | 0 | 8,182 | +8,182 (new type) |
| macrophage | 204 | 7,702 | +7,498 |
| endothelial cell | 406 | 7,300 | +6,894 |
| natural killer cell | 912 | 6,076 | +5,164 |
| luminal epithelial cell of mammary gland | 0 | 5,342 | new type |
| CD8+ T cell (the holdout) | 390 | 2,996 | +2,606 |
| CD4+ T cell | 192 | 2,812 | +2,620 |
| hematopoietic stem cell | 1,584 | 1,584 | 0 (was already at full atlas count — no gain here, expected) |
| thymocyte | 910 | 910 | 0 |
| erythrocyte | 2 | 54 | +52 |

Three observations to call out at the meeting:
1. **B cell exploded from 406 to 38,292** — the cap was extremely binding for B cells.
2. **Entirely new cell types appeared**: hepatocyte, luminal epithelial cell of mammary gland, basal cell, mature NK T cell, granulocyte, adventitial cell, mesenchymal stem cell of adipose tissue, etc. They didn't make the capped pool at all because their counts on one side were below the matcher's threshold of pairing, or one species had fewer than the cap. Removing the cap let several new shared identities clear the matcher.
3. **Some types didn't grow** (HSC = 1584 unchanged, thymocyte = 910 unchanged, alveolar type 2 = 584 unchanged) — these were *already at their full per-tissue count under the cap* (i.e., neither species had >1000 cells of that type). For BCG (LT-HSC), the HSC count is unchanged. This is honest framing.

**Baseline metric to beat** (CD8 OOD, data-space, n_cells=30, from `results/hvg_pearson_residuals_a_ood/impact_cellot/evals_ood_data_space/evals.csv`):

| Model | Pearson r (r2-means column) | **R²** (Pearson r squared) |
|---|---|---|
| IMPACT_CellOT | 0.9286 | **0.862** |
| scGen baseline | 0.9322 | **0.869** |

**Status of the experiment** (as of 12:13 today):
- Data file: `cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_a_uncapped_v07.h5ad` (124,886 × 1000) — built.
- Configs: `cellot/cellot_gpu/results/hvg_pearson_residuals_a_ood_uncapped/{scgen,impact_cellot}/config.yaml` — staged.
- Training submitted: **scgen JID 15996393** (`shared` partition, ~4h), **impact_cellot JID 15996397** (`gpu_requeue`, ~12h, dependency on scgen).
- Eval sbatches: `sbatch/eval_dataspace/eval_hvg_pearson_residuals_a_ood_uncapped_{scgen,impact_cellot}_dataspace.sbatch` — staged, will submit after training completes.
- **Expected results by**: end of day 2026-05-27 at the latest.

**Expected outcome**: cleaner-than-current R² and lower MMD on held-out CD8 cells, attributable purely to (a) 9.6× more training cells and (b) 7.7× more CD8 OOD eval cells. If R² *doesn't* improve, that's also an important finding — it would suggest the model was already in a saturated regime and the next lever should be model design or hyperparameters rather than more data.


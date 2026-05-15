# Mentor meeting talking points — April 21, 2026

Cross-species preprocessing audit and PTPRC investigation.

---

## 0. Opening

- Last week's question: why is PTPRC missing from the HVG list?
- Treated it as a reason to audit the whole preprocessing + HVG pipeline.
- Found 2 independent issues (HVG methodology + data scale mismatch), both fixed.
- PTPRC is still not an HVG — but now for an understood, correct reason.

---

## 1. Starting point

- PTPRC = CD45, pan-leukocyte marker; usually HVG in mixed datasets (bimodal: immune vs non-immune).
- In `01.1_hvg_investigation.ipynb`: PTPRC ranked 14,336 / 14,451 — near the bottom.
- Two hypotheses going in:
  - (a) HVG run on pooled species without `batch_key` → species shifts fake variance.
  - (b) In this matched dataset PTPRC is genuinely flat.

---

## 2. Fix 1 — `batch_key="species"` in HVG

- Without `batch_key`: species offset counted as variance → false HVGs.
- With `batch_key`: per-species dispersion, merged by `nbatches` then `dispersions_norm`.
- Top HVGs flipped from noise to real markers: NPPA, TNNT2, ALB, ACTA2, CD8A, CD14.
- PTPRC: rank 14,336 → 5,349. Better, but still not top 1000 → something else wrong.

| Gene | Role | Old rank | New rank | Top-1000? |
|------|------|---------:|---------:|:---------:|
| NPPA | cardiomyocyte | 4,236 | 1 | yes |
| TNNT2 | cardiomyocyte | 3,852 | 5 | yes |
| ALB | hepatocyte | 534 | 9 | yes |
| ACTA2 | smooth muscle | 10,441 | 14 | yes |
| CD14 | monocyte | 4,061 | 138 | yes |
| CD8A | T cell | 14,363 | 168 | yes |
| CD19 | B cell | 7,312 | 957 | yes |
| PTPRC | pan-leukocyte | 14,336 | 5,349 | no |

---

## 3. Surprise — scale mismatch between species

- Combined `.X` max = exactly 10.0 — suspicious for log-normalized data.
- Split by species:
  - Human max = 8.51 (normal `log1p`).
  - Mouse max = 10.0 (hard clip).
- Unique values in 10k subsample: human ~4%, mouse ~81%.
  - ~4% = `log1p(normalize_total)` collision pattern (expected).
  - ~81% = extra per-gene `/std` scaling (Tabula Muris export style).
- Conclusion: human `.X` and mouse `.X` were on **different transforms**. Every cross-species run so far was on mismatched scales.

---

## 4. Where clean data actually lives

- `AnnData.raw` is hidden from default repr — easy to miss.
- Both files have integer UMI/read counts in `.raw.X`. No re-download needed.
- `ad.concat` silently drops `.raw`, `.layers`, `.uns`, `.obsp` — that's why raw counts vanished downstream.

---

## 5. Fixed pipeline (order matters)

1. Load `.h5ad` for mouse + human.
2. `.raw.to_adata()` → work from integer counts.
3. `match_cells_by_celltype_tissue` → paired subset.
4. `align_adatas_biomart_one2one` → ~14k shared orthologs.
5. `normalize_total(1e4)` + `log1p` identically on both species.

- Normalize *after* ortholog alignment = per-cell depth correction uses the same genes in both species.
- Verification: mouse max ≈ 8.87, human max ≈ 8.80 — matched scales, no clip.

---

## 6. HVGs on fixed pipeline

- Call: `highly_variable_genes(flavor="seurat", n_top_genes=1000, batch_key="species")`.
- Top HVGs = real cell-type markers, mostly `nbatches=2` (variable in both species).
- Scanpy does NOT return HVGs in ranked order in `.var` — must explicitly sort by `[nbatches, dispersions_norm]` (this was Task 6).

---

## 7. PTPRC verdict

- On fixed pipeline: `nbatches = 0`, `dispersions_norm ≈ -0.21`.
- `frac_nonzero`: mouse 58.6%, human 69.1% → uniformly on.
- Matched dataset is immune-heavy → PTPRC is a compartment label, not a discriminator.
- Subtype markers (CD8A, CD19, CD14, etc.) are more bimodal in the same mean bin → they displace PTPRC.
- **Not a bug**: algorithm correctly picks subtype discriminators over compartment labels.
- If matched set is later broadened to include more non-immune cells → PTPRC may return to HVG list.

---

## 8. Where this leaves us

- Done:
  - Task 1: preprocessing audited + fixed.
  - Task 6: HVG ordering clarified.
- Next:
  - Rerun downstream analyses that used the old `.X` (data prep, eval, OT runs).
  - PCA / UMAP on new feature space.
  - UMAP in scGen latent (50-dim).
  - Broader ontology matching (Task 4) + immune-only subset check (Task 5).
  - Model queue: scGen, SWAPPED CellOT (IMPACT), standard CellOT, per-cell-type CellOT.
- Caveat: any metric / training run from before this fix = stale until rerun.

---

## 9. If asked for receipts

- Full detail: `research_log_2026-04-20.txt`.
- Side-by-side comparison + plots: `01.2_pipeline_comparison.ipynb`.
- Original HVG question: `01.1_hvg_investigation.ipynb`.
- Helpers: `speciesot_helpers.py` — `align_adatas_biomart_one2one`, `match_cells_by_celltype_tissue`.
- Deeper topics in log if Q&A goes there: `log1p` staircase math, 10x vs Smart-seq2 mix, AnnData concat semantics.

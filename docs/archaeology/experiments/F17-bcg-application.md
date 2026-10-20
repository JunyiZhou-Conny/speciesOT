# F17 · The BCG application: predicting the human BCG-vaccination response of blood stem cells from mouse

> The project's real target was to predict, from mouse data, how human bone-marrow stem cells respond to BCG vaccination: mouse untreated, mouse treated and human untreated cells are the inputs, and human treated cells are to be predicted. Between May and August 2026 Josh prepared mouse (PBS vs BCG) and human (day 0 vs day 90) stem-cell data and compared three batch-correction methods; the mouse cells went through Conny's atlas-trained species maps (the scGen-style shift and IMPACT_CellOT) four times, but no treatment map was ever built. The only quantitative test (tb4, 2026-08-26) found both models' predicted "human treated" profiles further from the real ones (R² 0.50 and 0.49) than the unchanged mouse-treated cells (0.63) or the human untreated cells (0.97); that comparison was not like-for-like, because only the predictions passed through the autoencoder and the model inputs were scaled differently from the training data. The planned check of the species map on untreated cells never ran, no conclusion was written, and the BCG work stopped after 2026-08-26, just before the package work began in September 2026.

| | |
|---|---|
| Period | 2026-05-05 (`josh@41d16ab`, "started BCG mouse and human dataset setup") → 2026-08-26 (`josh@5d00f44`) [G]. The mouse raw data were downloaded on 2026-05-04 (file times in fasrc:JOSH/tb/data/mouse_bcg/) [R]. |
| People | Josh Price: data download, QC, cell isolation, batch correction, gene-list check, first predictions and the evaluation (tb1–tb4, e20, e22, e23) [G]. Junyi (Conny) Zhou: BCG notebooks 16–17 and 16.1–16.4, the prediction and scoring scripts, the runbook, the 2026-08-18 predictions and the 2026-08-19 PI update [G][R][D]. Conny's notebooks and docs were written with AI agents [D] (project brief). e22 contains a note about "Cursor's notebook viewer" (e22#c5) [C], and tb3 calls Josh's own file "mentor `.X`", which is Conny's notebook-16 term (tb3#c2, c6) [C], so Josh's later notebooks were at least partly written with an AI agent in Cursor [I]. The PI is not named; the speaker card calls him "he" (PI/SPEAKER.md) [D]. |
| Status | abandoned unfinished |
| Main code | `josh@main:tb/tb1_mouse_setup.ipynb` · `josh@main:tb/tb2_human_setup.ipynb` · `josh@main:e22_batch_correction.ipynb` · `josh@main:tb/tb4_eval_first_predictions.ipynb` · `conny:scripts/predict_new_input.sh` · `conny:speciesOT/baseline/analysis/16.3_bcg_attempts_v08_iid_pearson.ipynb` |
| Results live in | Saved notebook outputs (tb1–tb4, e20, e22, e23, nb16–nb17). Batch-corrected BCG files in fasrc:JOSH/tb/data/mouse_bcg/ and fasrc:JOSH/tb/data/human_bcg/, and Josh's 2026-08-05 predictions in fasrc:JOSH/tb/data/mouse_bcg/predictions_080526/ (8 predictions, `hvg_coverage.csv`, 4 UMAP PNGs). These are **outside the BK backup** [R]. Conny's predictions and inputs: DS/bcg_* [R]. No scored BCG run exists in fasrc:BK/results/external_eval/ (only self-tests) [R]. The BCG figure folders in BK are empty [R]. |

Citation shorthands. tb1–tb4 = `josh@main:tb/tb{1..4}_*.ipynb` · tb1c = `conny:tb/tb1_mouse_setup.ipynb` (Conny's copy, which differs) · e20, e22, e23 = `josh@main:e20_lab_meeting_051226.ipynb`, `…/e22_batch_correction.ipynb`, `…/e23_investigating_gene_lists.ipynb` · nb16, nb16.1, nb16.2, nb16.3, nb16.4, nb17 = `conny:speciesOT/baseline/analysis/{16_bcg_mouse_data_prep, 16.1_…, 16.2_…, 16.3_…, 16.4_bcg_v08_predict_verify, 17_bcg_prediction}.ipynb` · RB = `conny:docs/mentor_runbook.md` · FC = `conny:docs/concepts/the four-corner goal.md` · PNI = `conny:scripts/predict_new_input.sh` · PI = `fasrc:BK/logs/research_logs/pi_5min_2026-08-19/` · DS = `fasrc:BK/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg` · RES = `fasrc:BK/cellot/cellot_gpu/results` · `fasrc:JOSH/` = `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/` on FASRC (Josh's folder; not part of BK; see [sources.md](../sources.md)), so Josh's BCG data are under `fasrc:JOSH/tb/data/`. "ls" means a file listing on FASRC on 2026-10-20; time stamps are file modification times. Date tags in file names are MMDDYY: `080526` = 2026-08-05.

## The question

**Terms.** BCG (Bacille Calmette–Guérin) is the tuberculosis vaccine. PBS (phosphate-buffered saline) is the mock injection given to control mice. An LT-HSC (long-term haematopoietic stem cell) is the most primitive blood stem cell in the bone marrow. HSPC means haematopoietic stem and progenitor cells. An MPP is a multipotent progenitor: MPP3 leans towards myeloid cells and MPP4 towards lymphoid cells (e22#c31) [D].

**The four corners.** The repo's goal picture is a square (FC; RB §1) [D]:

```
                    T_drug (learnable on mouse: PBS -> BCG)
   mouse untreated ─────────────────────────► mouse treated
          │                                          │
     T_species                                  T_species
          ▼                                          ▼
   human untreated ─────────────────────────► human treated
                    T_drug' (wanted)
```

- Mouse untreated = PBS LT-HSCs. Mouse treated = BCG LT-HSCs. Human untreated = day-0 LT-HSCs. Human treated = day-90 LT-HSCs (tb2#c3, e22#c14) [C][N]. In this study the fourth corner was also measured, so it can serve as ground truth [I].
- A "leg" is one arrow of the square. FC lists three routes to the fourth corner: apply the mouse treatment map to human, compose the maps, or one model conditioned on species and treatment [D].
- **Only the species leg (T_species) was ever implemented.** RB §1 says "no drug-effect transport exists in this repository" [D]. None of the 89 folders in RES is a BCG run; the only treatment-map runs there are the LPS replications on other data (`paper_crossspecies*`, unstimulated → LPS; [F11](F11-bunne-lps-replication.md)) (ls; RES/paper_crossspecies_mouse_ood/scgen/config.yaml) [R][C]. Three v08 specs name BCG as their intended use, but they train species maps (`conny:specs/atlas_full_pearson_v08_iid.yaml:54`, `atlas_uncapped_pearson_v08.yaml:51`) [C], and none of the 538 job scripts in fasrc:BK/sbatch/ mentions BCG (grep) [C]. FC says the drug leg "is the exploratory BCG line (notebooks 16/17)" [D], and `conny:docs/conceptual_framework.md:212` says the same [D], but those notebooks only push BCG mouse cells through the species map (nb17#c0) [C]. RB §1 also warns that feeding vaccinated mouse cells gives vaccinated human cells "*only if* the vaccination signal survives the transport, which is exactly the thing we have not established" (RB:22-24) [D].
- What was tested in tb4: the right-hand vertical arrow. The predictions are T_species(mouse treated), compared with real human treated (tb4#c8–c9) [C]. That route never uses the human-untreated corner [I]. The scGen paper's cross-species prediction uses both routes around its square, including the target species' control cells: ½(z_mouse,LPS + δ_species + z_rat,control + δ_LPS) [P] (scgen.txt, "scGen predicts single-cell perturbation across species", Fig. 5). The CellOT paper learned the treatment arrow (unstimulated → LPS) on other species and applied it to a held-out species [P] (cellot.txt, "CellOT reconstructs innate immune responses across species").
- What was planned first but never run: the left-hand arrow alone. Predict untreated human cells from untreated mouse cells and compare them with real untreated human cells. This was called "external validation of the species leg alone" (RB §1) and the "external exam" (PI/SLIDES.md, slide 1) [D].

## Setup

**Data.** Raw 10x matrices on FASRC (ls; tb2#c1; e22#c4) [R][C]:

| corner | source | cells after QC | LT-HSCs in the final files | earlier LT-HSC set |
|---|---|---|---|---|
| mouse untreated (PBS) | GEO GSE108067 (name of the downloaded tar file), fasrc:JOSH/tb/data/mouse_bcg/PBS | 6,768 | 387 (Leiden cluster 7; file `…_081826`) | 412 (May joint clustering, cluster 4) |
| mouse treated (BCG; labelled "day 28" in code) | fasrc:JOSH/tb/data/mouse_bcg/BCG | 2,248 | 251 (cluster 5) | 994 (clusters 8 and 12) |
| human untreated (day 0) | GEO GSE248728, capture 3 | 954 | 230 (clusters 7 and 0; file `…_082626`) | — |
| human treated (day 90) | GSE248728, capture 4 | 1,246 (of 6,681 barcodes) | 392 (clusters 9 and 7) | — |

Sources: e22#c10, c14; tb1#c26–c27, c61; tb2#c3, c5, c7, c10 [C][N]. QC as written: at least 500 genes per cell and at most 4.7% mitochondrial reads. The human threshold was copied from mouse ("same contract as e22 mouse", tb2#c7) [C]. **In mouse the mitochondrial filter removed nothing.** It tests the prefix `mt-` on `var['gene_ids']`, which holds Ensembl IDs (ENSMUSG…), not gene symbols (e22#c10; tb1#c9; the IDs are visible in nb16#c3) [C]. The arithmetic confirms it: the 500-gene filter alone removed 730,512 and 735,032 of the 737,280 barcodes, leaving 6,768 and 2,248, which are also the counts after the mitochondrial step (e22#c10; tb1c#c2, c4) [N]. In human the prefix `MT-` is tested on gene symbols, so that filter worked (tb2#c7) [C]. Each mouse matrix has 737,280 barcodes × 27,998 genes before QC (tb1c#c2, c4) [N]. The human GEO series has 14 captures, 115,698 barcodes in total (tb2#c1; ls) [N][R]. The matrices carry no day or donor labels; only `capture` is in `obs` (tb2#c2) [N]. Why capture 3 is day 0 and capture 4 is day 90: not found (looked in tb2, RB, fasrc:JOSH/tb/data/ and Josh's saved GEO page `index.html?acc=GSE248730`, which is a download page without sample details) [R].

**Cell isolation.** Leiden clustering (graph-based grouping of cells), then marker genes. Mouse clusters were picked by hand from UMAP marker plots (e22#c14, comment "Re-check against the marker UMAPs") [C]. Human clusters were picked by a rule: the module score of 7 markers (HLF, MECOM, PROCR, FGD5, MLLT3, SLAMF1, CRHBP), keeping clusters with z ≥ 1 (tb2#c8–c10) [C]. A module score is the mean expression of a gene set minus a random background set. Reference (atlas) anchors: 32 mouse LT-HSCs, i.e. one Leiden cluster out of 613 Tabula Muris marrow precursor cells (tb1#c53–c56; e22#c16, c20) [N]; 51 MPP3 and 104 MPP4 (e22#c36) [N]; 107 human LT-HSCs plus 506 other HSPCs from Tabula Sapiens bone marrow, 10x 3' v3 only (tb2#c12) [N]. The mouse scANVI reference for the final files is therefore 187 atlas cells (32 + 51 + 104; e22#c47) [C][N].

**Batch correction.** The final files were made with scANVI reference mapping. scVI is a variational autoencoder for counts; scANVI is its version that also uses cell-type labels. "Reference mapping" trains on the atlas, then fits only extra weights for the new dataset (the "query"). Each condition was mapped as its own query and decoded "as if" it came from the atlas batch. The decoded frequencies were then multiplied by each cell's original count total on the 1,000 axis genes (tb2#c14; e22#c46–c47) [C]. The repo calls the result "posed counts" (PNI:46-51) [C]. So all four corners in the evaluation are scANVI reconstructions, not measured counts [I]. Both tb4 and the prediction script re-normalise these posed counts to 10,000 per cell on the same genes, so the library size cancels: what reaches the metric and the models is log(1 + 10,000 × scANVI frequency) (tb4#c6; PNI:473) [I]. The files' `.X` is not this: it is the uncorrected log-normalised mouse data (e22#c38, c47) or the raw human counts (tb2#c13–c14) [C][I].

**Gene axis.** The models read 1,000 human Ensembl genes, chosen as highly variable genes (HVGs) on the whole multi-tissue atlas (F08, F10). The v08 Pearson axis starts with CAMP, S100A8, MGP, ALB, FABP4, CYTL1, PLA2G2A, SFTPC, DCN and LYZ (DS/gene_lists/hvg_pearson_residuals_a_uncapped_v08_genes.csv) [R]. ALB is a liver gene and SFTPC a lung gene [I]. Of tb2's 7 LT-HSC markers only MECOM, PROCR and CRHBP are on this axis (same file) [R]. Genes are matched across species with a table of one-to-one orthologs (genes with exactly one counterpart in the other species). In that table human TMSB4Y (a Y-chromosome gene) is paired with mouse Tmsb4x, and TMSB4X has no partner (DS/gene_lists/pre_hvg_one2one_orthologs.csv) [R]. Genes absent from the input are filled with zeros (PNI:466-470) [C]. Coverage, i.e. how many of the 1,000 genes were really measured:

| step | axis | genes present / 1,000 | source |
|---|---|---|---|
| nb16, 2026-05-08 (raw counts) | atlas_full_v07 seurat_v3 / pearson | 531 / 650 | `josh@157a180:baseline/analysis/16_bcg_mouse_data_prep.ipynb#c9` [N] |
| nb16, 2026-05-10 (Josh's `.X`) | same | 428 / 582 | nb16#c12 [N] |
| tb3, 2026-08-05, saved output from the 08-18 re-run (scANVI files with 685 genes) | same | 325 / 685 | tb3#c2, c11; fasrc:JOSH/tb/data/mouse_bcg/predictions_080526/hvg_coverage.csv [D][N][R] |
| nb16.2, nb16.3, 2026-08-18 | v08 Pearson | 507 (May object, `.X` or raw counts), 498 (Aug-05 scANVI) | nb16.2#c9; nb16.3#c12 [N] |
| e22 → final mouse files, 2026-08-18 | v08 Pearson | 996 (PLA2G2A, HLA-DRA, CEBPD, SMIM38 zero-filled before scANVI) | e22#c18, c45 [N] |
| tb2 → final human files, 2026-08-26 | v08 Pearson | 998 | tb2#c7, c13 [N] |

**Normalisation.** The atlas training files are log1p(CP10k) of all ortholog genes, cut to the 1,000 HVGs *afterwards* (`conny:speciesOT/hub/prep.py:585-616`) [C]. CP10k means counts scaled to 10,000 per cell; log1p is log(1 + x). The BCG inputs are cut to the 1,000 genes first and normalised *on those 1,000 only* (PNI:444-473; tb4#c6) [C]. So BCG values sit on a different scale from the training data [I].

**Models.** Two "model sets" were used (PNI:16-21) [C]; a third was trained but not used:
- `atlas_full_v07`: trained 2026-05-08 (Slurm jobs 11585147–51), then retrained 2026-05-10, which overwrote the checkpoints (ls RES/atlas_full_*) [R].
- `uncapped_v08_iid`: trained 2026-08-03 (ls RES/hvg_*_a_uncapped_v08_iid) [R].
- Not used for BCG: `uncapped_v08`, the ordinary train_test set that the specs call the BCG deployment model and that should replace the iid "interim" set "when model.pt exists" (`conny:specs/atlas_uncapped_pearson_v08.yaml:51-58`) [D]. Its checkpoints were written on 08-18 by 13:18 (ls RES/hvg_{pearson_residuals,mixhvg}_uncapped_v08/*/cache) [R], yet the 17:44 BCG predictions used `uncapped_v08_iid` (DS file names) [R]. No reason is recorded [I].

The two used sets are CellOT's plain autoencoder (2 × 256 units, latent 50, dropout 0.1, no KL term, 50,000 iterations) plus a mean shift in the latent space ("scgen"), and an ICNN transport (4 × 64) in that latent space ("impact_cellot") (RES/…/config.yaml) [C]. Both were trained on about 80% of the atlas cells: `train_test` with test_size 0.2, or `toggle_ood` in iid mode, which also puts half of the CD8 T cells into training (`conny:cellot/cellot_gpu/cellot/data/cell.py:330-386`) [C]. On their own atlas check (the held-back half of the CD8 T cells; the other half was in training), the v08 iid models reach r = 0.977 (scgen) and 0.981 (impact_cellot) at n = 80 (r is unsquared; r² ≈ 0.954 and 0.963) (RES/hvg_pearson_residuals_a_uncapped_v08_iid/*/evals_ood_data_space/evals.csv) [R]. Training details: [F16](F16-deployment-models-and-mixhvg.md). See `conny:docs/archaeology/models.md` for how these differ from the scGen paper.

**Evaluation.**
- e22 used kBET and kNN purity. kBET (k-nearest-neighbour batch-effect test) asks, per cell type, whether a cell's neighbours come from both studies in the expected proportion; 1 means well mixed. kNN purity is the share of a cell's 15 nearest neighbours with the same cell-type label. Both were computed on 30 cells per study × cell type (180 cells), one random draw (seed 0). Each method was scored in its own space: PCA for "before" and "ratio", Harmony PCA for Symphony, the scANVI latent for scANVI (e22#c40, c42) [C][N].
- tb4: per-gene mean expression of each group. Then the Pearson r² across genes against human treated, on all 1,000 genes and on the 100 genes with the largest human day-90 − day-0 change (tb4#c9, c11) [C]. Pathways: module scores for 14 Hallmark gene sets (curated pathway lists from MSigDB), with a two-sided Mann–Whitney U test (a rank test) per source and Benjamini–Hochberg false-discovery correction (tb4#c13–c14) [C]. Observed groups use posed counts → normalise → log1p; predictions use the model output as it is (tb4#c6) [C].
- Planned, never run: the decoded-frame MMD scores (`model_over_floor`, `r2_model_dec`; see [F10](F10-monocytes-floor-ceiling-and-v08.md)) of untreated-mouse predictions against real untreated human (RB §3-4; nb16.4#c13) [D]. The script for this, `conny:scripts/eval_external_target.py`, builds every reference in the decoded frame, i.e. after an autoencoder round trip, including a no-transport baseline (the mouse cells encoded and decoded) and a split-half ceiling, at 30/50/80 cells (`eval_external_target.py:12-27, 243-296, 324`) [C]. No BCG folder exists in fasrc:BK/results/external_eval/ (ls) [R].

## What was done and what came out

### 1. Mouse data and the May batch correction (tb1; 2026-05-04 → 05-13)

- Josh downloaded GSE108067 (PBS and BCG matrices; `GSE108067_RAW.tar`, 2026-05-04 14:58) on 2026-05-04. The human GSE248728 capture files are dated 2026-05-05 16:34–16:35; a 1.4 GB `human_tb.tar` in his `tb/` folder is dated 05-04 14:46 (ls fasrc:JOSH/tb/data/; ls `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/tb/`) [R].
- The first LT-HSC sets came from joint clustering of both mouse samples: PBS cluster 4 (412 cells) and BCG clusters 8 and 12 (994 cells) (tb1#c26–c27, c82) [C][N]. The comment in tb1#c25 names clusters 2, 7 and 9 instead [C], so it is stale after a re-run [I].
- scVI/scANVI was trained on 723 atlas marrow immune cells, with the BCG cells as the query (400, 10 and 100 epochs; tb1#c61, c63–c64) [N]. Josh's note: "Overlap looks good in latent space. Doesn't look good in decoded full dimensions." (tb1#c71) [D].
- He then used a per-gene ratio instead: mean of 32 atlas LT-HSCs divided by mean of 412 PBS LT-HSCs. The ratio was computed on log-normalised values and applied to all 1,406 BCG-study cells (tb1#c76–c78) [C].
  - The first version, committed 05-08 in `josh@c56d420`, had no limits; it wrote `bcg_mouse_aligned_050626.h5ad` (file time 05-06 17:12) [C][R]. Conny's first nb16 describes that file's `.X` as reaching "max ~105" (`josh@157a180:baseline/analysis/16_bcg_mouse_data_prep.ipynb#c0`) [D].
  - From 05-10, genes with a mean ≤ 0.01 kept ratio 1, and ratios were clipped to [0.25, 4] (`josh@6381578`; file `bcg_mouse_aligned_051026.h5ad`, 05-10 17:03; tb1#c90) [C][R].
  - The 05-11 commit message "changed bcg batch correction strategy to prevent extreme values" (`josh@3915c50`) describes this change, but the code change is already in `josh@6381578` [G][I].
- The HEAD notebook cannot run top to bottom: tb1#c76 uses variables that are defined only in tb1#c77, which is now a Markdown cell [C].
- Conny's copy tb1c was first committed on 2026-05-15 as `speciesOT/tb1_mouse_setup.ipynb` (`conny@c342331`) and only moved to `tb/` on 2026-09-01 (`conny@1530e2f`, a pure rename) [G]. It is Josh's 05-08 version plus three inserted cells and two small edits (the `scvi` import commented out; a Smart-seq2 subset added) (diff against `josh@c56d420`) [G]. Conny ran cells c0–c56 in Conny's own environment (`analysis` env paths in the outputs), and the run stops at a NameError (tb1c#c56) [N]. Two facts from it:
  - In that version the atlas was not limited to marrow (tb1c#c33) [C].
  - The 10x part of Josh's mouse atlas sample has 7 "hematopoietic stem cells", against 993 in Smart-seq2 (tb1c#c36–c37) [N]. The 10x-only v08 cuts (assay filter `chromium_v2`/`chromium_v3`, `conny:specs/atlas_full_pearson_v08_iid.yaml:8-12`) [C] therefore hold almost no mouse cells with that label; mouse stem cells sit inside the "hematopoietic precursor cell" label [I].

### 2. Conny's first predictions (nb16, nb16.1, nb17; 2026-05-08 → 05-10)

- **05-08.** nb16 projected raw counts onto the `atlas_full_v07` axes and then normalised them on those 1,000 genes (`josh@157a180:baseline/analysis/16_bcg_mouse_data_prep.ipynb#c0, c9`) [C]; coverage 531 and 650 (see the table above) [N]. nb17 ran all four forward passes with the 05-08 checkpoints (`josh@a3b81c4:baseline/analysis/17_bcg_prediction.ipynb#c3`) [N].
- **05-10.** nb16 switched to "keep mentor `.X`, no `log1p`" on the 051026 file (nb16#c0, c12) [D][N]. Its stated premise is that `.X` is scANVI's `get_normalized_expression` output (nb16#c0) [D]. That is false: tb1 exports log-normalised values times the clipped ratio (tb1#c76–c78) [C]. The input reached 19.85 (Plac8), while the training data never exceed 8.46 (nb16#c4, c6, c8) [N]. 19.85 is about 4 × 4.96, i.e. the ratio cap of 4 times a normal log value [I]. Only the single largest entry was capped (nb16#c6) [C]; the next four entries, all Plac8, were 18.8–19.3 (nb16#c6), and both exported files still reach 19.31 (nb16#c12) [N]. 572 of the 1,000 seurat_v3 genes were zero-filled (nb16#c14) [N].
- nb17 re-ran three of the four predictions; IMPACT/pearson was interrupted by hand (`KeyboardInterrupt`, nb17#c3) [N]. On disk the IMPACT/pearson file is from 05-08 09:47 and the other three from 05-10 18:41–18:42 (ls DS) [R]. So the four "May predictions" mix two input pipelines and two sets of checkpoints, and the 05-08 checkpoint no longer exists [R][I].
- nb17 has "NO evaluation against real human BCG", only UMAP overlays (nb17#c0) [D]. The overlay PNGs are gone: fasrc:BK/speciesOT/baseline/analysis/bcg_prediction_outputs/figures/ is empty (ls) [R].
- nb16.1 (05-10) keeps only the measured genes and normalises after subsetting (nb16.1#c9) [C]. Its cells c9–c11 never ran, and its output files do not exist (nb16.1; ls DS) [N][R]. The models need exactly 1,000 columns anyway (nb16.1#c0) [D].

### 3. Cell-type coverage for the lab meeting (e20; meeting 2026-05-12, committed 06-22)

- 4,027 matched mouse–human cell pairs from 12 tissues and 27 cell types; 723 are from bone marrow; 613 pairs are HSPCs (e20#c5–c8) [N]. A cell-type × tissue dot plot (e20#c9) [N]. No model and no BCG data are used (e20) [C].

### 4. Batch-correction comparison (e22; 2026-07-28 → 08-18)

- Question: "when a population is left out of correction, which batch correction method aligns those populations best?" Hypothesis: scANVI, after Zappia et al. 2025 (e22#c1) [D].
- Design: the ratio is fitted on LT-HSCs only, so MPP3/MPP4 are left out of it. For Symphony and scANVI the left-out part is only on the BCG side: the BCG MPP3/MPP4 enter as unlabelled query cells, while the atlas reference includes labelled MPP3/MPP4 (e22#c24–c26, c42) [C]. On the BCG side the MPPs are labelled from 6,768 PBS cells by marker-score thresholds after Pietras et al. 2015: 783 MPP3 and 831 MPP4. On the atlas side: 51 and 104 (e22#c31–c36) [D][N]. Atlas marker support is weak: mean Slamf1 is 0 in both atlas MPP groups, and the atlas Flt3 thresholds are 0 (e22#c36) [N]. Only untreated (PBS) cells are scored; the treated cells are never part of the comparison (e22#c40, c42) [C].

| run | PBS / BCG LT-HSCs | genes | kBET: before / ratio / Symphony / scANVI | kNN purity: same order |
|---|---|---|---|---|
| `josh@8f0a7d8` (07-29) | 412 / 994 | 10,866 shared | 0.000 / 0.256 / 0.452 / 0.289 | 0.722 / 0.706 / 0.666 / 0.736 |
| `josh@f563dee` (08-03) | 412 / 994 | 10,866 | 0.000 / 0.256 / 0.452 / 0.167 | 0.722 / 0.706 / 0.666 / 0.728 |
| `josh@6cbf17d` = HEAD (08-18) | 387 / 251 | 1,000 (v08 axis) | 0.000 / 0.344 / 0.478 / 0.028 | 0.681 / 0.691 / 0.656 / 0.706 |

Sources: `josh@<sha>:e22_batch_correction.ipynb` outputs of the comparison cell (#c35 in the first two, #c42 in HEAD) [N]. On the same inputs, only scANVI moved (0.289 → 0.167), so scANVI and ratio swapped places [N]; this points to training randomness [I]. No scvi-tools seed is set; only NumPy and the neighbour search are seeded (e22#c5, c42) [C]. `josh@8f8d528` (08-03) shows the same numbers and the same execution counts as `josh@f563dee`, and still prints "Shared genes: 10866", although its header says the gene axis changed to the v07 list (`josh@8f8d528:e22_batch_correction.ipynb#c1, c39`) [N]; so it was not re-run [I].

- Hyperparameter search (`josh@f563dee:e22_batch_correction.ipynb#c37`) [N]:
  - Symphony: 0.469 with default settings, 0.418 tuned.
  - scANVI: 0.167 default, 0.222 tuned. The best setting scored 0.306 during the search and 0.222 when refitted.
  - 54 Symphony and 16 scANVI settings were tried, each scored once on 180 cells (same cell #c37) [N].
  - Commit message: "no improvement" (`josh@fa8f99d`) [G]. In that commit the search cell has no output; the results first appear in `josh@f563dee` (`josh@fa8f99d:e22_batch_correction.ipynb#c37`) [N].
- The conclusion changed between versions:
  - 08-03: "Symphony best performs reference mapping on the BCG dataset" (`josh@f563dee:e22_batch_correction.ipynb#c1`) [D].
  - 08-18: "Only scANVI can map to the original reference space (transcript counts). In PCA space, Symphony mixes batches better, while scANVI generates purer populations." (e22#c1) [D].
  - scANVI was kept because it outputs counts, not because of its mixing score, where it ranked last of the three methods on 08-18 [I].
- Exports:
  - First Symphony files: `bcg_{control,treated}_symphony_080326.h5ad` (08-05 11:58) and `…_symphony_080526.h5ad` (08-05 12:16) (ls fasrc:JOSH/tb/data/mouse_bcg/) [R]. The save cell for the 080326 files is in `josh@8f8d528:e22_batch_correction.ipynb#c42–c43` but shows no output [N]. Symphony maps into an embedding, not into genes (e22#c42, `X_pca_harmony`) [C], which fits the later switch to scANVI [I].
  - `bcg_{control,treated}_scanvi_080526`: 412 / 994 cells × 685 genes, written 08-05 19:36 (nb16.3#c0, c3; ls) [N][R]. No committed e22 version writes them (`git log -S`) [G].
  - `…_081826`: 387 / 251 cells × 1,000 genes (e22#c47) [N]. Their count totals on the axis are 720,873 and 51,404 (e22#c47) [N]: 1,863 per PBS cell against 205 per BCG cell, a ninefold depth gap [I]. In the 080526 files it was the other way round, 1,900 vs 3,206 per cell (685 genes × the means in nb16.3#c3) [I].

### 5. Josh's first predictions (tb3; work 2026-08-05, committed 08-18)

- Inputs: the 080526 files, 412 and 994 cells × 685 genes (tb3#c7) [N]. Models: `atlas_full_v07` scgen and impact_cellot, both flavors (tb3#c4) [C]; for these models a baked scGen shift file exists, dated 08-03 17:37 (ls RES/atlas_full_*/scgen/cache) [R]. Coverage 685/1000 (pearson) and 325/1000 (seurat_v3) (tb3#c11; `hvg_coverage.csv`) [N][R]. In each file the single largest entry was capped, both in the TMSB4Y column, which holds mouse Tmsb4x: control 5.62 → 4.59, treated 5.18 → 4.55 (tb3#c9) [N].
- tb3 fed the models the files' `.X` and calls it "atlas-decoded scANVI expression" (tb3#c2, c7) [D][C]. nb16.3, written on 08-18 after inspecting the same files, calls that `.X` a "log-like leftover; ignore it" and locates the scANVI output in `layers['counts']` (nb16.3#c0, c3) [D]. The code that wrote the 080526 files is not committed, so which is right cannot be checked; in the later 081826 files `.X` is the uncorrected log-normalised data (e22#c38, c47) [C][I].
- The forward-pass and UMAP cells have no saved output (tb3#c13, c15) [N]. Eight prediction files and four UMAP PNGs are dated 08-05 13:01–13:02 (ls fasrc:JOSH/tb/data/mouse_bcg/predictions_080526/) [R]. The current 080526 input files are dated 08-05 19:36 [R]. The predictions may therefore come from an earlier version of the inputs [I]. The projection cell was re-run on 08-18: the four aligned files and `hvg_coverage.csv` are dated 08-18 14:10, and the notebook file 08-18 17:52 (ls fasrc:JOSH/tb/data/mouse_bcg/predictions_080526/; ls `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/tb/`) [R]. The printed output of tb3#c5 does not match its own code (it prints "DATA_DIR exists", which the code does not contain), so it is left over from an earlier version [N][I]. Josh ran Conny's models in his own environment with a `torch.load` patch (tb3#c2, c13) [D][C].
- No hypothesis or conclusion was written (tb3#c1) [D].

### 6. Conny's v08 path and the second predictions (2026-08-18)

- nb16.2 put the May object on the v08 axis: 507/1000 genes present. The v08 and v07 Pearson axes share 721 genes; v08 Pearson and v08 mixhvg share 674 (nb16.2#c7, c9) [N]. It is marked "Superseded" (nb16.2#c0) [D].
- nb16.3 documented the 080526 files and wrote two attempt files (507 and 498 genes present) (nb16.3#c0–c12) [N]. It also wrote the gene lists at 14:19; the cell that writes them shows no execution in the saved notebook (nb16.3#c14; ls DS/gene_lists) [N][R].
- Code (`conny@abf75d2`, `conny@39e37cc`) [G]:
  - `predict_new_input.sh` gained `--posed-ensg` (PNI:7-14, 46-51) [C]. `--model-set` is older: it arrived on 2026-08-03 in `conny@6dff64e` [G]. PNI has not changed since `conny@abf75d2`, so the current file is the one that ran on 08-18 [G].
  - Without a baked shift file, the scGen shift is recomputed from the training split (PNI:655-660) [C]; `uncapped_v08_iid` has no such file (ls RES) [R].
  - New scripts `score_bcg_and_plot.sh` and `plot_bcg_paper_figures.py`. The plotting script ranks its top-100 genes by a Wilcoxon test of human BCG vs mouse BCG cells (`conny:scripts/plot_bcg_paper_figures.py:157-172`) [C].
- nb16.4 is the planned end-to-end run. It would score *control* predictions against real untreated human and draw five figure boards (nb16.4#c0, c13) [D]. It was never executed: no outputs, and its paths are placeholders "/path/to/…" (nb16.4#c20) [N].
- What ran (ls DS; ls fasrc:JOSH/tb/data/mouse_bcg) [R]:
  - 17:39: Josh wrote the 081826 files.
  - 17:44–17:46: eight files `bcg_{ctrl,trt}_081826_predicted_human_via_{scgen,impact_cellot}_{pearson_residuals,mixhvg}_uncapped_v08_iid.h5ad` appeared, owned by Conny's account, together with eight aligned inputs (`bcg_{ctrl,trt}_081826_aligned_…`, plus their `_anndata07` copies). The names follow PNI's output pattern (PNI:477, 502, 678), so the run was most likely `predict_new_input.sh --model-set uncapped_v08_iid --posed-ensg` with tags `bcg_ctrl_081826` / `bcg_trt_081826`; no log of the command was found (grep of logs/ and docs/) [I].
  - The mixhvg inputs came from files on the Pearson axis, so at most 674 of their 1,000 genes can be real [I].
  - 17:56: an empty folder `paper_style_bcg_outputs/pre_eval_081826` was created (ls fasrc:BK/speciesOT/baseline/analysis/) [R].
- RB on that day still said that no human `.h5ad` was assembled and that there was "no per-capture vaccinated/unvaccinated assignment on disk" (RB:616-620, written 2026-07-30 in `conny@fe856aa`) [D][G]. It also still said that `--model-set uncapped_v08_iid` "has NOT been run end to end" (RB:608-615, written 08-03) [D][G], which the 08-18 run made out of date [I].

### 7. Update to the PI (2026-08-19)

- Slide 1 (PI/SLIDES.md) [D]: "We are building a mouse → human cell translator." The atlas holdout is the `internal exam`; BCG LT-HSCs are the `external exam`.
- Slide 3 [D]: "BCG scANVI files sit on the v08 axis at **1000 / 1000**. Predictions are written (387 unvax, 251 vax)." The next step named there: score untreated mouse → predicted human against real untreated human.
  - 387 and 251 are the mouse cell counts (e22#c14) [N].
  - "1000/1000" counts columns: 996 genes were measured, and scANVI filled in the other 4 (e22#c45) [N][I].
- Speaker card (PI/SPEAKER.md) [D]: "We do not have the human ground truth yet." Under "Do not say" it lists "Vaccinated mouse scored against unvaccinated human."
- The two PNGs opened, `pi_slide3_two_exams.png` and `slide1_task.png` (the one SLIDES.md shows on slide 1), are schematic drawings of dots with no data (own inspection) [I]. The other seven of the nine PNGs in PI/ were not opened.

### 8. Gene-list check and human data (e23, tb2; 2026-08-18 → 08-26)

- e23 has one executed check: 100.0% of the v08 HVGs are in the gene list of Josh's mouse atlas sample (e23#c7) [N]. This is expected, since both come from Tabula Muris [I]. The file was saved 08-18 14:30 (ls) [R] and committed 08-25 with the message "now have 99.8% overlap" (`josh@404f72e`) [G]. 99.8% matches the human coverage in tb2 (998/1000; tb2#c7, c13) [N][I], although that tb2 version was only committed a day later (`josh@74cf2f2`) [G].
- Earlier tb2 versions (05-05 to 05-10) only loaded the 14 captures and isolated Tabula Sapiens LT-HSCs (Leiden cluster 5, written to `atlas_human_lthsc_050826.h5ad`, 05-08 15:29) (`josh@c56d420:tb/tb2_human_setup.ipynb#c18–c19`; ls fasrc:JOSH/tb/data/) [C][R]. In the committed versions no human BCG cells were processed before 08-26 [G].
- tb2 (HEAD = `josh@74cf2f2`) built the human corners (230 and 392 LT-HSCs, see Setup). It trained scANVI on 613 atlas cells (latent 20; 100, 20 and 50 epochs) and mapped day 0 and day 90 as two separate queries, both labelled LT-HSC (tb2#c11, c14) [C][N]. The files `bcg_{control,treated}_scanvi_082626.h5ad` were written 08-26 15:49 (ls fasrc:JOSH/tb/data/human_bcg/) [R].
- The commit says "now have two donors for tb2 batch correction (but correction doesn't look good)" (`josh@74cf2f2`) [G]. The notebook has only a latent UMAP and no metric (tb2#c15) [N].
- On 08-25/26 Josh also saved SRA run tables (SRA = NCBI's Sequence Read Archive) for BioProject PRJNA511004: 122 runs from 29 samples, 15 donors at D0/D90, bone-marrow HSPCs, HiSeq 1500 single-end, created 2018-12-20. A second table holds donor D19 only (6 runs, 3 at D0 and 3 at D90) (fasrc:JOSH/tb/data/human_bcg/sra/) [R]. These look like a different, non-10x study, not the GSE248728 captures [I]. The folder `/n/netscratch/mooney_lab/Lab/jmprice/bcg_fastqs/` (08-25) is empty (ls) [R].

### 9. The evaluation (tb4; started 08-18 per its header, committed 08-25 → 08-26)

Question: "Does IMPACT-OR better predict human LT-HSC responses to BCG vaccination than scGen in terms of feature-wise r^2 and pathway-level trends seen in the human BCG publication?" (tb4#c1) [D]. IMPACT-OR is IMPACT_CellOT (`conny:docs/archaeology/models.md:54`) [D]. The publication is not named [D]. Inputs: the mouse 081826 files, the human 082626 files and Conny's `uncapped_v08_iid` Pearson predictions (tb4#c4–c5) [C][N].

The first tb4 version (`josh@404f72e`, 08-25) looked only at the predictions. It tried to plot two human lncRNAs, LINC01128 and AL157893.2, which are not on the 1,000-gene axis (NaN), and scored three Hallmark sets on predicted control vs predicted treated cells (`josh@404f72e:tb/tb4_eval_first_predictions.ipynb#c2, c6, c10`) [N]. Why these two genes were chosen is not recorded [I]. The version below (`josh@5d00f44`) added the observed corners.

Agreement of mean expression with human treated (tb4#c9, c11) [N]:

| compared with human treated | r², 1,000 genes | Spearman ρ, 1,000 genes | r², top-100 human BCG genes | Spearman ρ, top-100 |
|---|---|---|---|---|
| mouse treated, unchanged | 0.628 | 0.393 | 0.182 | 0.298 |
| scGen(mouse treated) | 0.501 | 0.534 | 0.069 | 0.220 |
| IMPACT_CellOT(mouse treated) | 0.486 | 0.553 | 0.049 | 0.164 |
| human untreated, unchanged | 0.970 | 0.990 | 0.978 | 0.987 |

- The top-100 genes change by 0.52–0.95 log units in human; the largest are CSF3R, MCTP1 and TAFA2 (tb4#c11; names from DS/gene_lists) [N][R]. All 25 rows that are printed (ranks 1–20 and 96–100) go up at day 90 (tb4#c11) [N]. Even on these 100 genes, day 0 matches day 90 with r² 0.978 [N]. A correlation of mean profiles barely sees a response of this size [I].
- The predictions are autoencoder outputs; the two "unchanged" rows are not passed through the autoencoder (tb4#c6; PNI:663, 676) [C]. The repo's own external-evaluation script compares against decoded references for exactly this reason (`eval_external_target.py:12-27`) [C]. A decoded no-transport row was not computed, so the table cannot say how much of the models' deficit comes from the autoencoder round trip alone [I].
- Gene examples (tb4#c9) [N]:

| gene | mouse treated | human treated | scGen | IMPACT |
|---|---|---|---|---|
| CAMP | 3.26 | 0.035 | 0.06 | −0.22 |
| MGP | 1.47 | 0.049 | 1.47 | 1.75 |
| ALB | 1.64 | 0.12 | 1.04 | 1.08 |
| FABP4 | 1.56 | 0.12 | 0.66 | 1.04 |

  The maps move CAMP to the human level, leave MGP at the mouse level (or raise it), and lower ALB and FABP4 only part of the way (0.66–1.08 against 0.12 in human) [I]. Decoded values can be negative [N]. Liver and fat genes in "LT-HSCs" of both species, rising in both treated samples (e.g. human ALB 0.018 → 0.12), point to decoding or contamination artefacts [I].
- Pathways: 14 Hallmark sets (tb4#c4, c13–c14) [C][N].
  - The sets have 1–87 genes on the axis; OXPHOS has 3, Myc V2 1, DNA repair 2, Myc V1 5 and ROS 8 (tb4#c13) [N].
  - The treated − untreated shift points the same way as in human in 6/14 sets for unchanged mouse, 8/14 for scGen and 8/14 for IMPACT. Among the 9 sets with ≥ 10 genes: 3/9, 5/9, 5/9 (computed from tb4#c14) [I]. Chance would give about half [I].
  - Almost every test is "significant" (e.g. q ≈ 1e-97). Each cell counts as an independent sample, so n is in the hundreds [N][I].
- Josh's verdict: "tb4 making predictions (also not looking good yet)" (`josh@74cf2f2`) [G]. The Conclusion field is empty (tb4#c1) [D].

### 10. Checks of earlier survey leads

- tb3 "(08-18)": the predictions and UMAPs are from 2026-08-05 (header and file times); on 08-18 the projection cell was re-run (aligned files and `hvg_coverage.csv` 14:10), the notebook was saved (17:52) and committed (tb3#c1; ls) [D][R][G].
- tb4 "conclusion left blank (c9, c11)": the empty Conclusion is in c1; c9 and c11 hold the numbers [N]. The numbers in the lead are correct [N].
- "ENSG00000164047: 2.81 vs 0.006 suggests a normalisation mismatch": in tb4 both species get the same normalisation (tb4#c6) [C]. The gene is CAMP [R], and the gap is between the two species' decoded LT-HSC profiles [I]. A real normalisation mismatch exists elsewhere: between the training data and every BCG input (Setup) [C].
- "BCG scANVI files at 1000/1000": 996 genes were measured (e22#c45) [N].
- "16.1 may intersect genes before normalising": true in the code, but those cells never ran (nb16.1#c9) [N].
- `sources.md` lists Josh's raw BCG reads on netscratch as at risk: the folder is empty (ls) [R].
- e22 kBET numbers: correct for the 08-18 run; earlier runs gave other values (table in §4) [N].

## Verdict

- **Do the models beat trivial baselines? No.** In the only scored test, both predictions match the human treated profile worse than leaving the mouse treated cells unchanged: r² 0.501 and 0.486 against 0.628 on all genes, and 0.069 and 0.049 against 0.182 on the top-100 genes (tb4#c9, c11) [N]. Human untreated cells alone score 0.970 and 0.978 [N]. On rank correlation over all genes, the models do beat unchanged mouse (0.53–0.55 vs 0.39), but stay far below human untreated (0.99) [N]. On pathway direction they are at chance level (8/14) [I]. The comparison is not like-for-like: only the predictions went through the autoencoder, and the model inputs were normalised differently from the training data (§9; Problems) [C]. Both differences probably work against the models [I]. So the record shows that these predictions were worse than doing nothing, but it cannot say whether the transport itself made them worse [I].
- **The vaccination effect is small next to the species difference** in these data: 0.97 vs 0.63 (tb4#c9) [N]. This is why the human-untreated corner is such a strong baseline [I].
- **scGen vs IMPACT_CellOT (Josh's question): no difference that the evidence can support.** 0.501 vs 0.486, one run, no repeats [N][I].
- **Batch correction: no method is shown to be better.** On the same inputs the scANVI kBET went from 0.29 to 0.17 between two runs, and it was 0.03 on the 08-18 inputs; each value comes from one draw of 180 untreated cells [N]. Josh's own judgement of the human (tb2) mapping was "correction doesn't look good" (`josh@74cf2f2`) [G].
- **The weakness is in the inputs as much as in the models.** The gene axis is chosen on the whole atlas and holds few stem-cell genes [R]. Inputs are normalised differently from training [C]. Each condition is mapped as its own batch [C]. Mouse cells were not filtered for mitochondrial reads, human cells were (Setup) [C][N]. The mouse treated cells have a ninefold lower count total on the axis [N][I]. So the negative result does not show that a species map cannot work for BCG. It shows that this pipeline gave no usable prediction [I].
- **Not tested at all:** the species map on untreated cells, a treatment map, and any prediction that uses the human untreated corner as input [N][R].
- **Why the status is "abandoned unfinished" and not "did not work":** the one scored test was negative, but it scored a route that no plan named as the method (RB §1; nb16.4#c13) [D], and the planned test and the treatment leg never ran [R][I].

## Why it stopped

No reason is stated. The record shows:
- Josh's last commits on main, 2026-08-26: "tb4 making predictions (also not looking good yet)" (`josh@74cf2f2`), then "added top 100 DEG analysis" (`josh@5d00f44`) [G].
- No conclusion was written in tb3 or tb4 (tb3#c1, tb4#c1) [D].
- The step announced on 08-19 (score against real untreated human; PI/SLIDES.md) [D] never ran: there is no BCG scoring folder (ls fasrc:BK/results/external_eval/) [R].
- From 2026-09-01 the notebooks were copied into Conny's repo (`conny@1530e2f`), and the package work began ([F18](F18-oop-package.md); `conny:docs/archaeology/timeline.md`) [G].
- The last speciesOT compute job ran on 2026-08-18 [R] (Slurm accounting, from the project brief).

The record suggests the team moved to the package before a working BCG pipeline existed, after negative first results and a human batch correction Josh himself judged poor [I]. The BCG files live on: the package's test configs use the mouse-treated and human-treated BCG files as their test pair (`josh@scgen-model-impl:src/speciesot/Tests/config.yaml:10-12`, `toy_config.yaml`) [C].

## Problems in how it was done

- **Model outputs are compared with raw baselines.** In tb4 the predictions are decoded autoencoder outputs, while "mouse treated, unchanged" and the human corners are not round-tripped through the autoencoder (tb4#c6; PNI:663, 676) [C]. The repo's planned external evaluation uses decoded references and a decoded no-transport baseline for this reason (`eval_external_target.py:12-27`; RB §4) [C][D]. Without that baseline, the gap between 0.50 and 0.63 cannot be assigned to the transport rather than to reconstruction loss [I].
- **The mouse mitochondrial filter did nothing.** It looks for `mt-` in Ensembl IDs, so no mouse cell was removed by it, while human cells were filtered at 4.7% on symbols (e22#c10; tb1#c9; tb2#c7) [C][N]. QC therefore differs between the species, and the mouse corners may include damaged cells [I].
- **Normalisation differs between training and use.** The atlas is normalised on all ortholog genes before the 1,000-gene cut; BCG inputs and the tb4 truth are normalised on the 1,000 genes (prep.py:585-616; PNI:473; tb4#c6) [C]. Every BCG input is therefore off-scale for the models, and the predictions sit on a different scale from the observed corners they are compared with. This probably tilts tb4 against the models [I].
- **A wrong premise in nb16.** It treats Josh's `.X` as scANVI output (nb16#c0) [D], but the values are log-normalised data times a ratio of up to 4 (tb1#c76–c78) [C], with entries up to 19.85 against a training maximum of 8.46 (nb16#c4, c8) [N]. The May predictions came from inputs outside the training range [I]. tb3 repeated the pattern in August: it fed `.X` as "atlas-decoded scANVI expression", while nb16.3 calls that `.X` a leftover to ignore (tb3#c2; nb16.3#c0) [D] (§5).
- **The ratio correction is applied to log values** (tb1#c76; e22#c25) [C]. A ratio on log1p values is not a fold change in expression [I].
- **The gene axis is not built for stem cells.** It starts with CAMP, S100A8, MGP, ALB and FABP4, holds only 3 of the 7 LT-HSC markers, and holds none of CD34, CD48 and FLT3, the extra markers tb2 plots (DS/gene_lists/hvg_pearson_residuals_a_uncapped_v08_genes.csv; tb2#c9) [R][C]. Coverage was 32.5–68.5% for every prediction before 2026-08-18 (coverage table) [N]. The axis also pairs human TMSB4Y with mouse Tmsb4x [R]. Most of what the models see is unrelated to the BCG response [I].
- **Hand-picked, changing cell sets.** Mouse treated LT-HSCs went from 994 to 251 cells between the 08-03 and 08-18 versions, when joint clustering was replaced by clustering each sample on its own (e22 table; e22#c11, c14) [N][C]. The 251-cell set has about 9× fewer counts per cell on the axis than the PBS set (e22#c47) [N][I]. Re-normalisation cancels the depth itself (Setup), but low-count cells give scANVI less to work with and may be lower-quality cells, so the mouse "BCG effect" may be mixed with quality differences [I].
- **The batch correction can erase the signal.** Each condition is a separate query batch decoded into the atlas batch (tb2#c14; e22#c47) [C]. A shift shared by all treated cells can be absorbed as "batch" [I]. And the "ground truth" in tb4 is itself a scANVI reconstruction [C].
- **Batch correction was checked only where it matters least.** kBET and kNN purity were computed on untreated (PBS) cells only (e22#c40, c42) [C]; the mapping of the treated cells, and the whole human mapping, have no metric (e22#c47; tb2#c15) [C][N].
- **Tiny references and one draw.** 32 mouse atlas LT-HSCs as the ratio anchor, 187 atlas cells for the final mouse scANVI reference, and 613 cells for the human one (e22#c20, c47; tb2#c14) [N][C]. kBET on 30 cells per group, one draw per method, each method scored in its own embedding (e22#c42) [C]. No scvi seed (e22#c5, c42; tb2#c9, c14) [C]. scANVI and ratio swap places between two runs on the same inputs (§4) [N].
- **Unclear human design.** The capture → day mapping is undocumented (tb2#c2–c3) [N][I]. The "two donors" note is unexplained (`josh@74cf2f2`) [G]. If day 0 and day 90 come from different people, donor and vaccine effects are mixed [I]. The human QC thresholds were copied from mouse, and 81% of the day-90 barcodes were removed (tb2#c5–c7) [C][N].
- **The two treated corners may sit at different times.** The code labels the mouse BCG sample "day 28" (tb1#c17) and the human sample is day 90 (tb2#c3) [C]; the mouse study's timing is not recorded (Open questions). A mouse-to-human map of treated cells then also has to absorb a time difference [I]. The repo listed this as an open question (`conny:docs/conceptual_framework.md:886`) [D].
- **The wrong arrow was scored, with a blunt metric.** tb4 scores only T_species(mouse treated); the human-untreated corner appears only as a comparator, never as an input (tb4#c8–c9) [C]. Mean-profile r² cannot see a response that leaves day 0 vs day 90 at r² 0.97 [N][I]. Apart from the pathway directions, the predicted *change* (treated − untreated) was never compared gene by gene with the human change [C][I].
- **Two different "top-100" gene sets.** tb4's top-100 are the genes with the largest human day-90 − day-0 change (tb4#c11) [C]; the planned BCG figures' top-100 are a Wilcoxon ranking of human BCG vs mouse BCG cells, i.e. species-difference genes (`plot_bcg_paper_figures.py:157-172`) [C]. Numbers labelled "top-100" are not comparable across the two [I].
- **Pathway statistics are weak.** 5 of 14 sets have ≤ 8 genes on the axis, and the p-values treat cells as independent replicates (tb4#c13–c14) [N][I].
- **Mixed provenance of prediction files.** The May files mix inputs and checkpoints, and one checkpoint was overwritten (§2) [R]. tb3's predictions are older than their current inputs (§5) [R]. Conny's mixhvg predictions are at most 67% covered (§6) [I].
- **Docs disagree with the record.** FC and `conceptual_framework.md:212` call the BCG notebooks the drug leg [D]. PI says 1000/1000 [D]. e23's commit says 99.8% where its output says 100.0% [G][N]. e22's conclusion changed from "Symphony best" to scANVI [D]. RB (still on 08-18) says no human file exists and that `uncapped_v08_iid` was never run end to end; tb2 later built the human file and the 08-18 run used that model set [D][N][R]. PNI calls `atlas_full_v07` "the May-8 deployment models" (PNI:17), but its checkpoints are from 05-10 (ls RES) [C][R].
- **Notebooks do not re-run.** tb1#c76 needs a Markdown cell [C]. tb3's prediction cells have no outputs, and tb3#c5 shows output from an older version of its code [N]. nb16.1 and nb16.4 never ran [N].
- **Artefacts lost or outside the backup.**
  - The ortholog and symbol caches (`scripts/.biomart_ortholog_cache.csv`, `scripts/.bcg_symbol_to_ensmusg.csv`) are git-ignored (`conny:.gitignore:17-18`) and are missing from fasrc:BK/scripts/ (ls) [C][R]. A copy of the 14,451-pair table survives as DS/gene_lists/pre_hvg_one2one_orthologs.csv [R].
  - All of Josh's BCG data and scANVI files live only in fasrc:JOSH/tb/data/, not in BK [R].
  - The figure and coverage outputs of nb16–nb17 are missing [R].

## Terms used here

- `tb1`–`tb4`: Josh's BCG notebooks (mouse setup, human setup, first predictions, evaluation).
- `mentor .X`: the expression matrix stored in Josh's files and fed to the models as is: in May by nb16 (in fact log values × ratio), in August by tb3 (the `.X` that nb16.3 calls a leftover).
- "LT-HSC treated": e22's and tb1's label for the BCG-sample LT-HSCs.
- ratio method: per-gene scaling by the atlas-LT-HSC mean over the BCG-control-LT-HSC mean.
- posed counts, `--posed-ensg`: scANVI expression decoded for the atlas batch and multiplied by each cell's original count total on the axis genes (stored in `layers['counts']`); the script flag that accepts such files.
- attempt 1 / attempt 2 (nb16.3): the May raw counts vs the Aug-05 scANVI posed counts, both projected onto the v08 axis.
- `080526`, `081826`, `082626`: date tags of Josh's scANVI files (mouse Aug 5, mouse Aug 18, human Aug 26).
- `atlas_full_v07`, `uncapped_v08_iid`: the two model sets used for BCG (PNI:16-21); details in [F16](F16-deployment-models-and-mixhvg.md).
- `_anndata07`: a file rewritten for anndata 0.7; not the v07 model set (RB §3).
- coverage: how many of the model's 1,000 genes are really measured in the input; the rest are zeros.
- `internal exam` / `external exam`: the PI slides' names for the atlas holdout and the BCG test.
- species leg / T_species, drug leg / T_drug: the vertical and horizontal arrows of the four-corner square.
- d0, d90 (human), "day 28" (mouse BCG sample label in code): sample names; PBS is a control group, not a time point.

## What the package needs from this

Nothing here is a good test of model *quality*: the results are negative and the inputs are fragile. Three narrow reference tests are possible:

1. **tb4's mean-profile R² (evaluation code).**
   - Inputs: fasrc:JOSH/tb/data/mouse_bcg/bcg_{control,treated}_scanvi_081826.h5ad, fasrc:JOSH/tb/data/human_bcg/bcg_{control,treated}_scanvi_082626.h5ad, and DS/bcg_{ctrl,trt}_081826_predicted_human_via_{scgen,impact_cellot}_pearson_residuals_uncapped_v08_iid.h5ad.
   - Recipe (tb4#c6, c9, c11):
     - observed groups: `layers['counts']` → normalize_total(1e4) → log1p; predictions: `.X` as is;
     - per-gene means over the 1,000 genes; squared Pearson r against human treated;
     - top-100 = largest |human treated − untreated| mean difference, ties broken by Mann–Whitney p.
   - Expected values (tb4#c9, c11) [N]:
     - all genes: 0.628441 / 0.500532 / 0.485743 / 0.970376;
     - top-100: 0.181901 / 0.069001 / 0.048776 / 0.977887.
   - Tolerance: the recipe has no sampling, so about 1e-6 is expected [I].
   - Copy Josh's files into a safe place first; they are not in BK [R]. The package's current `R2Evaluation` correlates paired rows gene by gene (`conny:src/speciesot/speciesot_core.py:115-126`) [C], so it will not reproduce these numbers and cannot even pair 251 mouse with 392 human cells [I] (see also `conny:docs/archaeology/metrics.md` §1) [D].
   - The package's test configs already use exactly this pair, mouse treated → human treated, with an `IdentityModel` (`josh@scgen-model-impl:src/speciesot/Tests/config.yaml:10-12`) [C]. With tb4's recipe, the identity model should give tb4's "mouse treated, unchanged" values, 0.628441 (all genes) and 0.181901 (top-100) [N][I].
   - Read `layers['counts']`, not `.X`: in these files `.X` is the uncorrected log-normalised mouse data or the raw human counts (e22#c38, c47; tb2#c13–c14) [C][I], and the package's `TestData` reads the files as they are (`josh@scgen-model-impl:src/speciesot/speciesot_core.py:27-33`) [C].
2. **Forward pass of the v08 models (model loading).**
   - Input: fasrc:JOSH/tb/data/mouse_bcg/bcg_control_scanvi_081826.h5ad.
   - Checkpoints: RES/hvg_pearson_residuals_a_uncapped_v08_iid/{scgen,impact_cellot}/cache/model.pt.
   - Recipe: PNI with `--model-set uncapped_v08_iid --posed-ensg` (inferred from the file names; no run log, §6) [I]: posed counts → 1,000 axis genes → normalize_total(1e4) → log1p; the scGen shift is recomputed from the training split of DS/hvg_pearson_residuals_a_uncapped_v08.h5ad (PNI:444-473, 655-660) [C]. Both models run in eval mode, so the pass should be deterministic (PNI:626, 672-673) [C][I].
   - Expected: DS/bcg_ctrl_081826_predicted_human_via_{scgen,impact_cellot}_pearson_residuals_uncapped_v08_iid.h5ad (387 × 1,000) [R].
   - Tolerance: RB reports agreement between two environments of 8.3e-07 (scGen) and 4.8e-06 (IMPACT) on other inputs [D]. This is not checked against these files.
   - Useful only if the package keeps CellOT checkpoints.
3. **Gene projection (ortholog mapping).**
   - Raw mouse matrices: QC (≥ 500 genes; the ≤ 4.7% mitochondrial step is a no-op in this code, Setup) gives 6,768 / 2,248 cells (e22#c10) [N]. A package that applies the mitochondrial filter correctly will get fewer cells, so this number tests the old behaviour [I]. Projection onto the v08 axis gives 996/1000 genes; the missing four are PLA2G2A, HLA-DRA, CEBPD and SMIM38 (e22#c45) [N].
   - Human captures 3/4: 954 / 1,246 cells and 998/1000 genes (tb2#c7, c13) [N].
   - Ortholog table: DS/gene_lists/pre_hvg_one2one_orthologs.csv (14,451 rows) [R]. nb16.3#c14 writes it from the same cache that e22 reads, filtered to one-to-one pairs (code; the cell shows no execution) [C], and e22 reports 14,451 one-to-one pairs (e22#c9) [N], so it is the same table in content [I].
   - Tolerance: exact.

Not worth reproducing: the kBET comparison (unstable), the hand-picked LT-HSC clusters, the scANVI files (unseeded), and the May predictions (mixed provenance). Any future BCG test in the package should report, on the same cells:
- the two trivial baselines (human untreated as is; mouse treated as is), and a simple "human untreated + mouse BCG change" baseline;
- the same baselines after an autoencoder round trip, so that model and baseline are in the same frame;
- a score on the predicted change (treated − untreated), not only on the treated profile [I].

## Open questions

- Which donor and which day do GSE248728 captures 3 and 4 come from? What does "two donors" in `josh@74cf2f2` mean? Not found in tb2, RB, Josh's data folder or his saved GEO download page.
- What do the four tb3 UMAP PNGs (fasrc:JOSH/tb/data/mouse_bcg/predictions_080526/figures/) show? No written reading exists.
- How do the 08-18 untreated-mouse predictions score against the 082626 untreated human cells? Both files exist; the comparison was never made.
- Does scANVI's per-condition mapping remove part of the BCG effect? This could be tested by comparing day 90 − day 0 differences in `counts_original` and in the posed counts.
- Why does the 251-cell mouse treated set have about 9× fewer counts per cell on the axis than the PBS set?
- What is the mouse study (GSE108067): days after vaccination and route? Is "day 28" a real time point or only a label? Which "human BCG publication" did tb4 take its pathway trends from, and is it the source of the two lncRNAs in the first tb4 version? Not named in the record.
- What is the `.X` of the 080526 files that tb3 fed to the models: scANVI output (tb3#c2) or the uncorrected input (nb16.3#c0)? The writing code is not committed; the files would have to be opened.
- How many mouse cells would a working mitochondrial filter remove, and does it change the LT-HSC clusters?
- Would a stem-cell-specific gene axis, or the full ortholog space, change the result?

## Sources

- Josh's repo: `josh@main:tb/tb1_mouse_setup.ipynb`, `…/tb/tb2_human_setup.ipynb`, `…/tb/tb3_first_predictions.ipynb`, `…/tb/tb4_eval_first_predictions.ipynb`, `…/e20_lab_meeting_051226.ipynb`, `…/e22_batch_correction.ipynb`, `…/e23_investigating_gene_lists.ipynb`.
  - Older versions: `josh@41d16ab`, `josh@c56d420`, `josh@6381578`, `josh@3915c50`, `josh@57cb8f4` (tb1); `josh@41d16ab`, `josh@c56d420`, `josh@6381578`, `josh@74cf2f2` (tb2); `josh@05d881d`, `josh@680ade1`, `josh@8f0a7d8`, `josh@fa8f99d`, `josh@f563dee`, `josh@8f8d528`, `josh@6cbf17d` (e22); `josh@404f72e`, `josh@74cf2f2`, `josh@5d00f44` (tb4).
  - `josh@cellot`: `josh@157a180`, `josh@a3b81c4`, `josh@f10f1cf` (nb16, nb17); `josh@0849d9f`, `josh@e42fc11`, `josh@5d9a567` (nb16.4, scripts). `git log origin/main`; `josh@f0585b4`; `git log --all -S'scanvi_080526'`, `-S'symphony_080'`.
  - Package line: `josh@scgen-model-impl:src/speciesot/Tests/config.yaml`, `…/Tests/toy_config.yaml`, `…/speciesot_core.py:27-33, 305-316`.
- Conny's repo: `conny:tb/tb1_mouse_setup.ipynb`; `conny:speciesOT/baseline/analysis/16_bcg_mouse_data_prep.ipynb`, `16.1_bcg_mouse_data_prep_atlas_hvg_intersection.ipynb`, `16.2_bcg_mouse_align_v08_iid_pearson.ipynb`, `16.3_bcg_attempts_v08_iid_pearson.ipynb`, `16.4_bcg_v08_predict_verify.ipynb`, `17_bcg_prediction.ipynb`.
  - Scripts and code: `conny:scripts/predict_new_input.sh`, `conny:scripts/plot_bcg_paper_figures.py`, `conny:scripts/score_bcg_and_plot.sh`, `conny:scripts/eval_external_target.py:1-60, 240-300, 324`, `conny:speciesOT/hub/prep.py:560-635`, `conny:cellot/cellot_gpu/cellot/data/cell.py:258-392`, `conny:speciesOT/baseline/analysis/15_data_prep_full_atlas_no_holdout.ipynb#c0, c11, c16`, `conny:src/speciesot/speciesot_core.py:115-126`, `conny:specs/atlas_full_pearson_v08_iid.yaml`, `conny:specs/atlas_uncapped_pearson_v08.yaml`, `conny:specs/atlas_uncapped_mixhvg_v08.yaml`.
  - Docs: `conny:docs/mentor_runbook.md` (with `git blame` of lines 600-621), `conny:docs/concepts/the four-corner goal.md`, `conny:docs/conceptual_framework.md:205-216, 880-890`, `conny:AGENTS.md:1-10`, `conny:logs/research_logs/research_log_2026-07-30_repo_plan.txt:1-20, 575-600, 676-700`, `conny:.gitignore`.
  - Archaeology pages: `conny:docs/archaeology/{timeline.md, models.md, metrics.md, sources.md, inventory.csv}`.
  - Commits: `conny@abf75d2`, `conny@39e37cc`, `conny@1530e2f`, `conny@c342331`, `conny@6dff64e`, `conny@a2f89cc`, `conny@fe856aa`, `conny@8a9a103`.
- Backup (fasrc:BK):
  - `PI/SLIDES.md`, `PI/SPEAKER.md`, `PI/pi_slide3_two_exams.png`, `PI/slide1_task.png` (PNG names listed).
  - DS (ls of bcg_*); `DS/gene_lists/hvg_pearson_residuals_a_uncapped_v08_genes.csv`, `DS/gene_lists/pre_hvg_one2one_orthologs.csv` (read on FASRC with the `analysis` python).
  - `RES/` (ls: 89 folders); `RES/atlas_full_{pearson_residuals,seurat_v3}/` and `RES/hvg_{pearson_residuals,mixhvg}_a_uncapped_v08_iid/` (ls of folders and `cache/`; config.yaml; eval_dataspace_*.out; evals_ood_data_space/evals.csv); `RES/hvg_{pearson_residuals,mixhvg}_uncapped_v08/` (ls of `cache/`); `RES/paper_crossspecies_mouse_ood/scgen/config.yaml`.
  - `fasrc:BK/results/external_eval/` (ls); `fasrc:BK/speciesOT/baseline/analysis/{bcg_mouse_outputs, bcg_prediction_outputs, paper_style_bcg_outputs}/` (ls); `fasrc:BK/scripts/` (ls); `fasrc:BK/sbatch/` (grep).
- FASRC outside BK:
  - `fasrc:JOSH/tb/data/` (ls of `.`, `mouse_bcg/`, `mouse_bcg/{PBS,BCG,predictions_080526,predictions_080526/figures}/`, `human_bcg/`, `human_bcg/GSE248728/`); `fasrc:JOSH/tb/data/mouse_bcg/predictions_080526/hvg_coverage.csv`; `fasrc:JOSH/tb/data/human_bcg/sra/SraRunTable_BCG.csv`, `SraRunTable_BCG_D19.csv`.
  - `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/` (ls; `index.html?acc=GSE248730`; `wget-log`); `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/tb/` (ls; `wget-log`); `/n/netscratch/mooney_lab/Lab/jmprice/bcg_fastqs/` (ls).
- Papers: /tmp/sot-arch/papers/scgen.txt ("scGen predicts single-cell perturbation across species", Fig. 5); /tmp/sot-arch/papers/cellot.txt ("CellOT reconstructs innate immune responses across species") [P].

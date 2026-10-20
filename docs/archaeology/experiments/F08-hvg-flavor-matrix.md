# F08 · The five-flavor highly-variable-gene (HVG) matrix

> The question was whether the recipe used to pick the 1,000 input genes (the HVG "flavor") changes how well IMPACT_CellOT (CellOT's optimal-transport map, used here to move mouse cells to human) beats an scGen-style baseline when one T-cell type is held out. In May 2026 Conny built 20 datasets (5 flavors × 4 holdout groups) from one matched mouse–human pool of 12,990 cells, trained 80 models (one baseline and one IMPACT model per flavor × group × IID/OOD), and evaluated them in the 50-dimensional latent space and, on the same day, in gene space. In latent space IMPACT was closer to the real human cells than the baseline in 19 of 20 IID cases but only 11 of 20 OOD cases, and Pearson residuals was the only flavor where it won all four OOD groups. The gene-space ("data_space") results cannot be used as a set: 29 of the 40 IMPACT "data_space" evaluations are latent-space numbers in a gene-space folder, and only the other 11 were ever re-run in true gene space. Status: partly worked. All 80 runs finished and the within-flavor latent comparison is usable, but the flavor question itself stays inconclusive (one unseeded run per cell, flavors confounded with encoder and gene set).

| | |
|---|---|
| Period | 2026-04-19 (PTPRC question, Cursor transcript) → 2026-04-24 (first notebook, josh@8a2d53a) → 2026-05-10 (last matrix evaluation file, mtime in RES); talk planned for 2026-05-12 (log0504:33) |
| People | Junyi (Conny) Zhou: all notebooks, scripts and runs [G]. Joshua Price: built the capped source files (josh@main:tabula_make_samples.ipynb, 2025-09-30 → 10-03; the `_shared` subsets in josh@main:intraspecies_vs_interspecies_dists.ipynb#c14, #c21, 2025-10-03) and the cell-matching helper (josh@7dcd6c1, 2026-02-10) [G][C]; mentor meetings are mentioned in log0504:16-26 [D]. All six commits on Josh's `cellot` branch that touch this family's notebooks and scripts carry a Cursor trailer: "Made-with: Cursor" (josh@8a2d53a, josh@232b65e) or "Co-authored-by: Cursor" (josh@3c42e96, josh@a15d14c, josh@44a995e, josh@f10f1cf) [G]. |
| Status | partly worked (all runs finished and the within-flavor latent comparison is usable; the flavor ranking is inconclusive, see Verdict) |
| Main code | nb01.5; conny:scripts/generate_hvg_flavor_configs.py; conny:scripts/generate_data_space_eval_sbatches.py; nb13; conny:cellot/cellot_gpu/scripts/evaluate.py and cellot/utils/evaluate.py; conny:speciesOT/speciesot_helpers.py |
| Results live in | RES/hvg_{flavor}_{a,b,c,d}_{iid,ood}/{scgen,impact_cellot}/evals_ood_{latent,data}_space/evals.csv (160 files). Datasets: fasrc:BK/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_{flavor}_{g}_v07.h5ad. The notebook output folders (hvg_flavor_outputs, hvg_flavor_results_outputs, hvg_flavor_nb14_outputs) exist in fasrc:BK/speciesOT/baseline/analysis/ but hold only an empty `figures/` subfolder (`ls` on FASRC); no copy was found on the Mac either (`find` under ~/Desktop). |

Citation shorthands: nb01.1 = conny:speciesOT/baseline/analysis/archive/01.1_hvg_investigation.ipynb · nb01.4 = conny:speciesOT/baseline/analysis/01.4_hvg_flavor_comparison.ipynb · nb01.5 = conny:speciesOT/baseline/analysis/01.5_data_prep_all_holdouts_hvg_flavors.ipynb · nb13 = conny:speciesOT/baseline/analysis/13_hvg_flavor_results.ipynb · nb14 = conny:speciesOT/baseline/analysis/14_hvg_flavor_notebook6_replica.ipynb · log0504 / log0420 = conny:logs/research_logs/research_log_2026-05-04.txt / _2026-04-20.txt · CF = conny:docs/conceptual_framework.md · RES = fasrc:BK/cellot/cellot_gpu/results · SB = fasrc:BK/sbatch. Only nb01.1 is in `archive/`; the other four notebooks sit one level up (the assignment's paths were wrong).

## The question

- Trigger: a mentor expected the gene PTPRC (CD45, a marker carried by all immune cells) to be among the selected genes, and it was not (conny:speciesOT/baseline/analysis/cursor_hvg_function_and_metadata_repres.md:19-21, exported 2026-04-19) [D]. The transcript calls the mentor "she"; who it was is not recorded.
- First answer (2026-04-20): PTPRC is left out because it is "uniformly on" in an immune-heavy pool; "a DATA COMPOSITION outcome, not a methodology bug"; decision "No action on the HVG selection" (log0420:330-381) [D].
- Second answer (2026-04-30): try other flavors on training cells only (nb01.4#c0) [D]. The meeting note of that day calls it urgent because "0 of 16 standard immune markers" were in the top-1000 HVGs of the older CD8 holdout dataset, and it leaves the flavor "decision rule" (marker recovery vs breadth of detection) as an open question (conny:speciesOT/baseline/analysis/meeting_notes_2026-04-30.md:25, 50) [D]. No answer to that question was found.
- The matrix question (2026-05-04): does the flavor change downstream mouse→human prediction, for scGen and IMPACT, in IID and OOD modes? The planned headline was "which flavor produces the smallest scGen distribution gap", with the hoped-for story "Pearson HVG → better OOD encoder → better IMPACT outcomes" (log0504:444-449) [D]. It was the core of the 2026-05-12 lab-meeting talk (log0504:33-41, 47-54) [D].

## Setup

**Data.** Source files are Josh's `sampled_mouse_shared.h5ad` (Tabula Muris, 47,807 cells) and `sampled_human_shared.h5ad` (Tabula Sapiens, 58,931 cells) (nb01.5#c3) [N]. Both were made in two steps. First, at most 1,000 cells per `cell_type` label per species were sampled (josh@main:tabula_make_samples.ipynb#c3 defines the sampler; #c10 mouse with random_state 42; human per compartment with 42 in #c13, then the concatenation re-sampled in #c20 with the default random_state 0; #c17 was never executed) [C]. Second, those `sampled_*_1000.h5ad` files were cut to cells whose label maps to one of the shared cell-type groups and saved as `sampled_*_shared.h5ad` (josh@main:intraspecies_vs_interspecies_dists.ipynb#c14 human, #c21 mouse; table in tabula_make_samples.ipynb#c22-24) [C]. This is the "1000-cap". It acts on the source files before matching, not on the matched pool (the lead's "pool capped at 1000 cells per type" is slightly off). The files are dated 2025-10-03 and still exist (`ls` on FASRC) [R]. Raw counts come from `.raw` (nb01.5#c3) [N]. One-to-one orthologs are queried live from Ensembl BioMart with no pinned release (conny:speciesOT/speciesot_helpers.py:872-875, 1096; the May version josh@a15d14c:speciesot_helpers.py does the same) [C]; this gave 14,451 genes (nb01.5#c5) [N]. Cells are matched per identity (cell-type ontology ID + tissue ontology ID): each identity keeps min(n_mouse, n_human) cells per species, seed 0 (speciesot_helpers.py:523-557) [C]. Result: 6,495 mouse + 6,495 human = 12,990 cells (nb01.5#c7, #c9) [N], 75 identities (nb01.1#c26) [N], 30 cell types (nb01.5#c17) [N]. Counts are library-size normalized to 10,000 and log1p-transformed; raw integer counts are kept in `layers['counts']` for the count-based flavors (nb01.5#c9) [N]. No assay filter: Smart-seq2 cells (a plate-based method with a different expression profile) stay in. They are 17,481 of the 47,807 mouse source cells and 3,405 (+37 Smart-seq3) of the 58,931 human ones (nb01.1#c25) [N]; CF:878 confirms the matrix files predate the assay filter [D]. For each (flavor, group), HVGs are computed once on all non-held-out cells with `batch_key='species'` and the top 1,000 are kept; the file keeps all 12,990 cells × 1,000 genes (nb01.5#c11, #c13) [C][N]. Files carry the suffix `_v07` because they were rewritten with anndata 0.7.6 for the CellOT environment (nb01.5#c14-15) [N].

**Holdout groups** (IDs from nb01.5#c1; counts from #c9 and #c13) [C][N]:

| group | name | held-out cell types | held-out cells (mouse+human) | non-held-out cells |
|---|---|---|---|---|
| a | cd8 | CD8-positive alpha-beta T cell, CL:0000625 | 390 (195+195) | 12,600 |
| b | cd8_thymo | CL:0000625 + thymocyte (developing T cell in the thymus), CL:0000893 | 1,300 | 11,690 |
| c | tcell_subtypes | CD4-positive alpha-beta T cell, CL:0000624 + CL:0000625 + CL:0000893 | 1,492 | 11,498 |
| d | cd4 | CL:0000624 | 192 (96+96) | 12,798 |

Thymocytes are 910 cells (455+455). The generic "T cell" label CL:0000084 (204 cells) is never held out (nb01.5#c9) [N], so related T cells stay in training in every group [I]. nb01.5#c1 also defines m1 = non-classical monocyte CL:0000875 and m2 = CL:0000875 + monocyte CL:0000576 [C]. m1 and m2 are not part of the 80-run matrix. An m2 extension with two flavors (8 runs, trained 2026-05-10) and an m1 run (2026-06-02) reused this pipeline (RES/hvg_*_m2_*, hvg_pearson_residuals_m1_ood, log mtimes) [R]; they are not analysed here. The a–d and m2 holdout lists match fasrc:BK/docs/model_cards/INDEX.md (all 88 a–d/m2 entries), so that lead is correct [D][C]; m1 is not in the index because its run postdates it. nb01.4#c2 defines group B as CL:0000625 only, identical to A; only group A was run there [C].

**What an HVG flavor is.** A highly variable gene is one whose expression varies across cells more than expected for its average level. Variable genes usually mark cell types. A flavor is scanpy's name for one recipe that scores this. Different recipes rank the 14,451 genes differently, so the 1,000 kept genes, which are the models' only input features, change with the flavor.

| flavor | input | score | how the two species are merged |
|---|---|---|---|
| seurat | log-normalized `.X` | undo log1p, dispersion = variance/mean, log; z-score within bins of mean expression | rank by number of species where the gene is HVG, then by normalized dispersion |
| cell_ranger | log-normalized `.X` | dispersion on the log data; bins by mean percentiles; normalized by bin median and MAD (median absolute deviation) | as seurat |
| seurat_v3 | raw counts | variance after standardizing with a loess fit (smooth curve) of variance vs mean | median rank across species first, ties by number of species |
| seurat_v3_paper | raw counts | same score as seurat_v3 | number of species first, ties by median rank |
| pearson_residuals | raw counts | variance of Pearson residuals of a negative-binomial count model (θ = 100, clipped at √n) | number of species where the gene is top-1000, then median rank |

Sources: scanpy 1.12 in the FASRC `analysis` env, `scanpy/preprocessing/_highly_variable_genes.py:221-234, 367-383, 421-443, 573-582, 651-652` and `scanpy/experimental/pp/_highly_variable_genes.py` (θ = 100, clip = √n, sort by nbatches then median rank) [C]; layer dispatch in nb01.5#c11 [C]. log0504:127-136 (and the dispatch table in nb01.5#c0) says seurat_v3 and seurat_v3_paper differ by "average rank" versus "median rank". That is wrong for scanpy 1.12: both use the median rank and differ only in sort order [C].

**Models** (configs written by conny:scripts/generate_hvg_flavor_configs.py:55-151; the 40 scGen configs in RES are identical except data file, holdout and mode, and so are the 40 IMPACT configs, except that hvg_seurat_d_ood/impact_cellot/config.yaml gained explanatory comments on 2026-05-26) [C]:

| | "scGen" baseline (`scgen/`) | IMPACT_CellOT (`impact_cellot/`) |
|---|---|---|
| what it is | CellOT-repo autoencoder (AE), 1000→256→256→50, dropout 0.1, beta 0 (no KL term, no sampling) | CellOT input-convex networks f and g, 4 hidden layers of 64, fnorm_penalty 1, on the 50-d codes of the sibling `scgen/` AE (`data.ae_emb`) |
| training | Adam, lr 1e-3, weight decay 1e-5, batch 256, 50,000 iterations | Adam, lr 1e-4 (β 0.5, 0.9), batch 128, 50,000 iterations, 10 inner iterations |
| prediction | encode mouse cell, add (mean human code − mean mouse code over training cells), decode | map mouse code with the learned transport, decode only if asked |

"IMPACT" is the repo's label for the species-transport use of CellOT; the repo's own doc calls it "a label, not a known acronym" and leaves a TODO to ask the mentor (CF:80, CF:884) [D]. The CellOT paper trains 250k iterations with batch 256 (cellot.txt, Methods, "Hyperparameters" and the scRNA paragraph above it) [P]; here both are lower [C]. The baseline is a plain AE with an unbalanced per-species mean shift, not the scGen VAE (`beta: 0.0` in RES/hvg_*/scgen/config.yaml; conny:cellot/cellot_gpu/cellot/models/ae.py:175-187) [C]. It is also smaller and shorter-trained than the CellOT repo's own scGen config ([512, 512], dropout 0, 250k iterations; conny:cellot/cellot_gpu/configs/models/scgen.yaml) [C]. One scGen per (flavor, group, mode) serves both as baseline and as IMPACT's encoder (log0504:65-104 [D]; `ae_emb.path: ./results/hvg_{flavor}_{gk}_{mode}/scgen/` in generate_hvg_flavor_configs.py:107-108 [C]). No training seed is set anywhere in the CellOT code (no `manual_seed`) [C]. There is one run per cell.

**Split (`toggle_ood`).** Non-held-out cells are split 80/20 into train/test per species (config `test_size: 0.2`, `groupby: condition`) [C]. The held-out pool is split 50/50 with random_state 0, not stratified by species: one half is always the evaluation set ("ood"); the other half is dropped ("ignore") in OOD mode or added to training in IID mode (conny:cellot/cellot_gpu/cellot/data/cell.py:330-384) [C]. So an IID model has seen half of the held-out type, human cells included. This mirrors the CellOT paper's i.i.d./o.o.d. design (cellot.txt, Methods) [P].

**Evaluation.** `evaluate.py --setting ood` pushes the mouse cells of the "ood" half through the model and compares them with the human cells of that half (conny:cellot/cellot_gpu/cellot/utils/evaluate.py:174-230) [C]. Each comparison draws n cells from each side, 10 times, without a seed (scripts/evaluate.py:196-204) [C]. Metrics: `r2-means` is the Pearson r between the two mean vectors across features (squared to R² by nb13#c5 and the hub); MMD is the biased RBF estimator averaged over 50 bandwidths (conny:cellot/cellot_gpu/cellot/losses/mmd.py:5-10; scripts/evaluate.py:43-46, 63-80) [C]. "latent_space" means the 50 codes of that run's own encoder; "data_space" means the 1,000 genes [C]. Headline = mean over the 10 draws at the largest n present: a 80, b and c 250 (latent) or 300 (data), d 40 (RES evals.csv) [R]. Non-standard points: the scGen paper's R² is also the squared Pearson correlation of mean expression across genes, but on all cells, with error bars from 100 resamples of 80% with replacement (scgen.txt, Methods, "Statistics"; Fig. 2c caption) [P]. Here it is computed on small unpaired subsamples (n cells from each side), with 10 unseeded draws, and in latent space across 50 coordinates instead of genes [C]; MMD shrinks as n grows (e.g. scGen, pearson_residuals c iid, gene space: 0.1381 at n=30, 0.0858 at n=300, RES/hvg_pearson_residuals_c_iid/scgen/evals_ood_data_space/evals.csv) [R], so numbers are comparable only within a group.

## What was done and what came out

### 1. 2026-04-19 → 04-24: why is PTPRC missing? (nb01.1)

- The mouse `.X` in the source files was scaled differently from the human one (max exactly 10) (nb01.1#c18, #c21-22; log0420:16-22) [N][D]. Conny re-normalized both species from raw counts (nb01.1#c23-26) [N].
- With `flavor='seurat'` and `batch_key='species'` on all 12,990 matched cells (no holdout; nb01.1#c28), PTPRC ranks 5,349 of 14,451 (nb01.1#c31) [N]. Adding `batch_key` changes 269 of the 1,000 genes (nb01.1#c29) [N].
- The silhouette comparison is not trustworthy: #c34 failed (NameError on `hvg_selected`), #c36 and #c38 have no execution count, and both silhouettes print the same −0.1674 [N].

### 2. 2026-04-30 → 05-10: four flavors on group A (nb01.4)

The notebook was written on 2026-04-30 without cluster access ("Cloud was down for the full session") and committed without outputs (josh@232b65e; meeting_notes_2026-04-30.md:64-66) [G][D]. It was run by 2026-05-04, since log0504:49-51 already quotes its PTPRC result [D][I]; the outputs were first committed on 2026-05-10 (josh@f10f1cf) [G]. cell_ranger was not included. Training cells 12,600, held out 390 (nb01.4#c12) [N].

| | seurat | seurat_v3 | seurat_v3_paper | pearson_residuals |
|---|---|---|---|---|
| Jaccard overlap with seurat | 1 | 0.230 | 0.237 | 0.186 |
| Jaccard with seurat_v3 | | 1 | 0.903 | 0.125 |
| PTPRC rank | 5,323 | 6,023 | 6,023 | 108 |
| panel markers ranked ≤ 1000 (of 16 found) | 10 | 11 | 11 | 8 |

Source: nb01.4#c16, #c18, #c22 [N]. The PTPRC "rank" here is nb01.4's own rank of the flavor's score (#c14), not scanpy's selection order, which is why a few genes ranked ≤ 1000 are not selected and vice versa [C]. log0504:50-51 says "rank 108 vs >7000 in seurat"; the >7000 matches an earlier all-cells run (log0420:342, 7,183 / 14,451) [D], not nb01.4 (5,323) [N]. The saved output of that same nb01.1 cell shows 5,349 (nb01.1#c31) [N], so log0420 describes a different run. log0504:311-315 says the larger cell pool "provided no measurable improvement in 01.4-stage smoke tests"; nb01.4 trains no models (#c0), and no such test was found [D].

### 3. 2026-05-04: the design (log0504)

80 trained models (5 flavors × 4 groups × 2 modes × 2 models), 160 sbatch scripts, 20 dataset files; every evaluation in latent space; data space only "for 1-2 cells of interest" (log0504:335-402) [D]. The run matrix is enumerated in conny:speciesOT/baseline/analysis/hvg_flavor_run_matrix.csv (80 rows) [C]. Whether group B should exist at all was left "OPEN WITH MENTOR" (log0504:232-242) [D]; no answer was found.

### 4. 2026-05-05: build, train, evaluate

- The first 01.5 run failed for the three count-based flavors ("cannot safely cast non-equivalent float32 to int64"; josh@a15d14c:baseline/analysis/01.5_data_prep_all_holdouts_hvg_flavors.ipynb#c13) [N]. seurat and cell_ranger runs finished training at 02:02–02:54; the other three flavors at 16:44–17:46 (train-log mtimes in RES) [R].
- One IMPACT training (pearson_residuals c iid) crashed with an HDF5 file-lock error on `cache/scalars` and was re-run; its latent and data-space evaluations were re-run after the retrain (RES/hvg_pearson_residuals_c_iid/impact_cellot/train_10290561.err, train_10320288.out, eval_10320290.out) [R].
- The first latent evaluations used the default n list (100, 250, …; SB/eval scripts pass no `--n_cells`) [C]. For all 40 group-a and group-d runs the pool is smaller than 100, so they wrote empty files (40 of 40 logs show no draws) [R]. They were re-run with small n: 16 `eval_smalln` scripts (n = 30,40,80; five IMPACT ones were run twice, 21 jobs) and 24 `eval_smalln_latent` scripts (30,50,80 or 20,30,40) (SB/eval_smalln, SB/eval_smalln_latent; logs in RES) [C][R].
- All 80 data-space evaluations ran 16:22–17:48 (log mtimes in RES) [R], from the 80 scripts that conny:scripts/generate_data_space_eval_sbatches.py wrote to SB/eval_dataspace (79 still dated 05-05 16:22) [C][R]. Its lines 36-41 set `extra = ""` for both models, so IMPACT never received `--embedding ae` [C].
- The 80 run folders hold logs of 297 Slurm jobs, job IDs 10067733–11586149 (RES) [R]. The archaeology timeline gives 349 jobs for this family between 05-05 and 06-02 (conny:docs/archaeology/timeline.md:66) [D]; the split "340 completed, 8 failed, 1 cancelled" [unverified: it comes from the task leads; no file source found]. In that window all hvg_* result folders hold 333 distinct job IDs: the 297 above plus 36 from the m1, m2 and uncapped follow-ups [R]. So the 349 includes later hvg_* runs [I].
- The dataset files on disk were rebuilt on 2026-05-10, after training: the plain `hvg_{flavor}_{g}.h5ad` files at 15:51–15:52 and the `_v07` copies at 15:53 (`ls` on FASRC) [R]. So the HVG selection itself was re-run, not just the anndata-0.7 rewrite. The saved outputs of nb01.5#c13-#c17 (groups a–d plus m2; 27 `_v07` files) fit that run [N][I], which preceded the m2 trainings at 16:16 (RES/hvg_*_m2_* logs) [R]. The configs and SB/eval scripts were also regenerated on 05-10 15:35 (mtimes in RES and SB) [R]; the generator's templates did not change between josh@3c42e96 and josh@44a995e [G]. The pipeline is seeded, so the files are probably identical to the trained-on versions [I]; this is not verified, and the live BioMart query is a possible source of change.

### 5. 2026-05-06: results (nb13, nb14)

nb13 found 80/80 trainings and evaluations (#c3) and squares r before averaging (#c5) [N]. My recomputation from the 80 latent evals.csv files reproduces its pivot (#c7) to four decimals [R][N].

Latent R² of means, OOD, scGen / IMPACT (n = 80, 250, 250, 40):

| flavor | a | b | c | d | IMPACT wins |
|---|---|---|---|---|---|
| seurat | 0.728 / 0.742 | 0.665 / 0.641 | 0.798 / 0.764 | 0.824 / 0.798 | 1/4 |
| cell_ranger | 0.717 / 0.763 | 0.573 / 0.504 | 0.721 / 0.616 | 0.806 / 0.838 | 2/4 |
| seurat_v3 | 0.755 / 0.787 | 0.668 / 0.561 | 0.653 / 0.519 | 0.841 / 0.918 | 2/4 |
| seurat_v3_paper | 0.702 / 0.773 | 0.548 / 0.397 | 0.704 / 0.678 | 0.757 / 0.776 | 2/4 |
| pearson_residuals | 0.678 / 0.783 | 0.728 / 0.797 | 0.757 / 0.826 | 0.734 / 0.789 | 4/4 |

Latent R², IID, scGen / IMPACT:

| flavor | a | b | c | d | IMPACT wins |
|---|---|---|---|---|---|
| seurat | 0.674 / 0.780 | 0.756 / 0.856 | 0.816 / 0.876 | 0.796 / 0.844 | 4/4 |
| cell_ranger | 0.678 / 0.737 | 0.695 / 0.838 | 0.719 / 0.857 | 0.689 / 0.794 | 4/4 |
| seurat_v3 | 0.718 / 0.773 | 0.747 / 0.816 | 0.737 / 0.840 | 0.821 / 0.803 | 3/4 |
| seurat_v3_paper | 0.649 / 0.790 | 0.659 / 0.793 | 0.712 / 0.858 | 0.780 / 0.787 | 4/4 |
| pearson_residuals | 0.612 / 0.761 | 0.702 / 0.844 | 0.779 / 0.859 | 0.687 / 0.752 | 4/4 |

Latent MMD, OOD, scGen / IMPACT (lower is better):

| flavor | a | b | c | d | IMPACT lower |
|---|---|---|---|---|---|
| seurat | 0.0737 / 0.0613 | 0.0848 / 0.0643 | 0.0614 / 0.0584 | 0.0662 / 0.0674 | 3/4 |
| cell_ranger | 0.0755 / 0.0615 | 0.0899 / 0.0808 | 0.0664 / 0.0696 | 0.0702 / 0.0644 | 3/4 |
| seurat_v3 | 0.0649 / 0.0596 | 0.0765 / 0.0739 | 0.0602 / 0.0694 | 0.0602 / 0.0504 | 3/4 |
| seurat_v3_paper | 0.0672 / 0.0562 | 0.0835 / 0.0826 | 0.0582 / 0.0517 | 0.0687 / 0.0621 | 4/4 |
| pearson_residuals | 0.0792 / 0.0643 | 0.0736 / 0.0559 | 0.0502 / 0.0410 | 0.0717 / 0.0645 | 4/4 |

All three tables come from RES/hvg_{flavor}_{g}_{mode}/{model}/evals_ood_latent_space/evals.csv, mean of squared r (or MMD) over 10 draws at the largest n [R]; they match nb13#c7 and #c18 [N]. Tallies: IMPACT has the higher R² in 19/20 IID and 11/20 OOD cases, and the lower MMD in 20/20 IID and 17/20 OOD cases [R]. Pearson is the only flavor where IMPACT wins all four OOD groups [R]. The lead's counts are correct. Where IMPACT loses in OOD, it is mostly the two holdouts that contain thymocytes (b, c): 8 of the 9 OOD losses [R].

- nb13#c13 names seurat_v3 / D / OOD (R² 0.9184) the best IMPACT cell [N]. That cell has the smallest sample (n = 40) [R]. Neither PTPRC nor CD3E is in seurat_v3's genes (#c15) [N], so the planned PTPRC/CD3E density plot could not show them [I]. The plot code also reads the `imputed.h5ad` of the latent folder (#c3 `cell_imputed_path`), whose 50 columns carry no gene names, so it could not have shown predictions for any gene [C].
- Biomarker panel in the 1,000 genes actually used (#c15) [N]: PTPRC is selected only by pearson_residuals, in all four groups. But Pearson keeps the fewest panel markers: 15/48 (31.2%), against 29–35/48 for the others. It never keeps MS4A1, CD19, CD14 or NCAM1, and keeps CCR7 only in group D.
- nb14 picked six cells by latent IMPACT R² (#c5; it squares the mean r, while nb13 averages squared r) [C] and crashed on the first (#c12, `ValueError: zero-size array`) [N]. Its summary shows IMPACT "data_space" R² 0.9186 / MMD 0.0505 next to latent 0.9184 / 0.0504: the "data_space" file was latent, and no IMPACT gene names matched [N][I]. Nothing else was rendered.
- The CSV and figure outputs of nb13 and nb14 are not in the backup; the folders hold only an empty `figures/` subfolder (`ls` on FASRC) [R].

### 6. 2026-05-08 → 05-10: gene-space re-runs and the space mix-up

- 10 hand-picked IMPACT runs were re-evaluated with `--embedding ae` on 2026-05-08 08:44–08:50 (SB/eval_dataspace_aeflag/, 10 scripts dated 08:43; logs in RES) [C][R]. seurat_v3 a ood was re-evaluated on 2026-05-10 14:32-14:34 (`imputed.h5ad` and evals.csv mtimes), but no job log for it exists in its run folder [R]. Its SB/eval_dataspace script now carries `--embedding ae`, but that file is dated 2026-05-15 13:53, after the re-run, so it does not show how the re-run was launched [R]. presentation_preparation.ipynb#c0 tells the user to do exactly this re-run for gene-space figures, and it uses only seurat_v3 and pearson_residuals, on CD8 OOD (group a) and M2 OOD (#c1 `FLAVOR_KEYS`, `EXPERIMENTS`; same in the 2026-05-10 version, josh@da0cbdc) [D][C].
- The other 29 IMPACT "data_space" files are latent. Three independent checks agree: (1) their `imputed.h5ad` has the latent file size (49,304 / 115,118 / 128,060 / 38,160 bytes for a/b/c/d), the same as the latent-space files, while the 11 re-runs have the scGen gene-space size (451,776 / 1,417,086 / 1,577,932 / 253,032 bytes) (`stat` on FASRC) [R]; (2) their metrics match the latent ones within re-draw noise (Verdict, last bullet) [R]; (3) the code makes decode the identity when `--embedding` is missing (cellot/utils/evaluate.py:99-109, 292-301, 361-362) [C]. CF:316-324 records the same widths (93×50 vs 93×1000) [D].
- The re-run evidence above corrects the lead "never re-run": 11 of 40 were re-run; 29 were not.

The 11 pairs where both models are really in gene space (RES/…/evals_ood_data_space/evals.csv; mean ± SD over the 10 draws) [R]:

| flavor, group, mode | n | scGen R² | IMPACT R² | scGen MMD | IMPACT MMD |
|---|---|---|---|---|---|
| seurat a ood | 80 | 0.831 ± 0.005 | 0.812 ± 0.009 | 0.1157 | 0.1008 |
| seurat b iid | 300 | 0.854 ± 0.003 | 0.889 ± 0.003 | 0.1023 | 0.0893 |
| seurat c iid | 300 | 0.876 ± 0.005 | 0.912 ± 0.003 | 0.0915 | 0.0906 |
| seurat c ood | 300 | 0.809 ± 0.004 | 0.736 ± 0.006 | 0.1190 | 0.0993 |
| seurat_v3 a ood | 80 | 0.828 ± 0.009 | 0.824 ± 0.017 | 0.1131 | 0.1062 |
| seurat_v3 d ood | 40 | 0.869 ± 0.004 | 0.884 ± 0.007 | 0.1026 | 0.1065 |
| pearson a ood | 80 | 0.858 ± 0.008 | 0.897 ± 0.006 | 0.1250 | 0.1046 |
| pearson b ood | 300 | 0.845 ± 0.003 | 0.861 ± 0.002 | 0.1166 | 0.0831 |
| pearson c iid | 300 | 0.947 ± 0.002 | 0.963 ± 0.003 | 0.0858 | 0.0594 |
| pearson c ood | 300 | 0.902 ± 0.005 | 0.896 ± 0.004 | 0.1054 | 0.0777 |
| pearson d ood | 40 | 0.902 ± 0.010 | 0.921 ± 0.006 | 0.1220 | 0.1046 |

IMPACT has the higher R² in 7/11 (IID 3/3, OOD 4/8) and the lower MMD in 10/11 [R]. Ten of the 11 were "hand-curated" (CF:342) [D], so they are not a random sample [I].

scGen in gene space, all 40 genuine: R² IID → OOD (RES/…/scgen/evals_ood_data_space/evals.csv) [R]:

| flavor | a | b | c | d | mean drop |
|---|---|---|---|---|---|
| seurat | 0.866 → 0.831 | 0.854 → 0.768 | 0.876 → 0.809 | 0.856 → 0.866 | 0.045 |
| cell_ranger | 0.827 → 0.835 | 0.882 → 0.654 | 0.868 → 0.708 | 0.801 → 0.851 | 0.083 |
| seurat_v3 | 0.834 → 0.828 | 0.835 → 0.643 | 0.875 → 0.668 | 0.854 → 0.869 | 0.098 |
| seurat_v3_paper | 0.838 → 0.840 | 0.816 → 0.642 | 0.848 → 0.688 | 0.837 → 0.851 | 0.080 |
| pearson_residuals | 0.827 → 0.858 | 0.943 → 0.845 | 0.947 → 0.902 | 0.878 → 0.902 | 0.022 |

On the planned headline metric, Pearson gives the smallest scGen IID→OOD drop, mainly because it holds up on b and c [R]. The held-out cells are identical across modes, but IID and OOD are separately trained, unseeded models [C].

- Mixed tally: if one reads the folders named data_space as they are, IMPACT has the lower MMD in 20/20 IID and 19/20 OOD pairs, and scGen the higher R² in 16/20 and 16/20 [R]. In 29 pairs this compares IMPACT latent numbers with scGen gene numbers, so it means nothing [I].
- presentation_preparation.ipynb#c12-#c13 would plot Pearson CD8 IID vs OOD from these folders, which puts a latent IMPACT IID bar next to a gene-space OOD bar [C][I]. This cell was added on 2026-06-09 (conny@8a9a103; the 2026-05-10 version, josh@da0cbdc, has no such cell) and has no execution count, so no such figure is recorded [G][N]. CF:330-337 shows the same mismatch from a separate spot-check at n = 30: IMPACT a_iid (latent) R² 0.77 below IMPACT a_ood (gene) 0.86, "the opposite of the in-sample-fit expectation" [D].

### 7. Afterlife (2026-05-26 → 06-09)

- 2026-05-27: the bug is documented, with "re-running is deferred for now" (CF:274-345, conny@a10fe24) [D][G].
- 2026-05-28: the model-card index lists the data_space headline for every run, including the 29 latent ones; e.g. hvg_pearson_residuals_a_iid/impact_cellot "R²=0.753, MMD=0.054" (fasrc:BK/docs/model_cards/INDEX.md:20) [D]. All 80 matrix entries in the index equal the data_space-folder evals.csv values (largest n, mean of squared r) [R]. The hub and vault take the space from the folder name (conny:speciesOT/hub/readers.py:62-80) and prefer data_space as the headline (conny:speciesOT/hub/cli.py:143-148) [C]; the vault page shows `eval_space: "data_space"`, `r2: 0.75266` (conny:docs/experiments/gpu__hvg_pearson_residuals_a_iid__impact_cellot.md:15-16) [D]. The lead was right here.
- The cards also mislabel metadata: `log1p_applied: No` for the count-based flavors and `hvg_batch_key: —` for every flavor (fasrc:BK/docs/model_cards/gpu__hvg_pearson_residuals_a_iid__impact_cellot.md:16, 19; gpu__hvg_seurat_a_ood__scgen.md:16, 19) [D], although every file is log1p data selected with `batch_key='species'` (nb01.5#c9, #c11) [C].
- A cross-family tally in the task leads (54 pairs; IID: scGen higher r in 16/24) [unverified: no source file found]. This family's folders-as-named tally is 16/20 IID (§6) [R].

## Verdict

- Solid: the data-preparation numbers (12,990 cells; holdout sizes; 30 cell types) come from seeded code that is deterministic once the BioMart ortholog table is fixed (nb01.5) [N][C]. The flavors pick very different genes: for group A and the four flavors nb01.4 compared, Jaccard is 0.13–0.24, except seurat_v3 vs seurat_v3_paper at 0.90 (nb01.4#c16) [N]. Only Pearson keeps PTPRC, and it loses many other panel markers (nb13#c15) [N].
- Moderately solid, within a flavor (same encoder, cells and genes): in latent space IMPACT is closer to the human cells than the mean-shift baseline in IID (19/20 R², 20/20 MMD); in OOD the picture is mixed (11/20 R², 17/20 MMD), with most losses in the thymocyte holdouts b and c [R].
- Suggestive only: Pearson residuals is the best flavor (all four OOD wins for IMPACT; smallest scGen gene-space OOD drop) [R]. It rests on one unseeded run per cell, and cross-flavor comparisons are confounded. Each flavor has its own latent space. Each flavor uses different genes, and Pearson's genes are about 2.5× more highly expressed (mean log-expression 0.39–0.40 vs 0.14–0.18; nb01.5#c17) [N]. A higher spread of gene means makes R² of means easier to reach [I].
- Cannot be concluded: anything from the IMPACT data_space folders except the 11 re-runs; any IID-vs-OOD "distribution gap" in latent space, because IID and OOD models have different encoders [I]; any cross-group ranking, because n differs (40 to 300) [R].
- Re-drawing the same model's evaluation is cheap noise: across 15 duplicate latent evaluations of the same IMPACT models, R² moved by at most 0.0093 (median 0.004) and MMD by at most 0.0016 (median 0.0006) [R]. Training noise was never measured.

## Why it stopped

No stated reason for ending the matrix. It was built for the 2026-05-12 talk (log0504:33-41) [D]. From 2026-05-08 on, only seurat_v3 and pearson_residuals were carried forward. nb15 keeps "Only two HVG flavors: `seurat_v3` and `pearson_residuals` (per the May 8 mentor meeting)" (conny:speciesOT/baseline/analysis/15_data_prep_full_atlas_no_holdout.ipynb#c0) [D]; the phrase is already in its first version, committed 2026-05-08 08:51 (josh@157a180) [G]; its atlas files are dated 2026-05-09 (`ls` on FASRC) [R]. The same two flavors appear in the m2 extension (trained 2026-05-10, RES mtimes) [R], in presentation_preparation.ipynb#c1 (`FLAVOR_KEYS`) [C], and in the uncapped CD8 study, which calls hvg_pearson_residuals_a_ood the "existing baseline" (conny:speciesOT/baseline/analysis/19_uncapped_cd8_ood_data_prep.ipynb#c0) [D]. So the choice was made at a 2026-05-08 mentor meeting, but why these two was not recorded: no notes of that meeting were found (searched research logs, docs, analysis markdown; there is no research log between 05-04 and 06-09). The gene-space re-run was deferred on 2026-05-27 (CF:345) [D]. The record suggests the matrix served as a one-off screen for the talk and the follow-up moved to monocytes, the uncapped pool and BCG [I].

## Problems in how it was done

- **Wrong eval space.** 29 of 40 IMPACT "data_space" results are latent (§6), because generate_data_space_eval_sbatches.py:36-41 never adds `--embedding ae` [C][R]. Every gene-space scGen-vs-IMPACT comparison built from these folders compares different spaces.
- **Labels follow folder names.** hub/vault/model cards report space from the directory name (readers.py:62-80) [C]. The wrong numbers spread to INDEX.md (file dated 2026-05-28) one day after the bug was documented (conny@a10fe24, 2026-05-27) [D][G].
- **Cross-flavor comparisons are not like-for-like.** Each flavor has its own encoder (latent metrics) and its own 1,000 genes with different expression levels (nb01.5#c17) [N]. So "which flavor is best" is not answered by these metrics [I].
- **Sample size differs by group.** The headline n ranges from 40 to 300 [R], and the biased MMD falls with n [R]. The "best IMPACT cell" (n = 40) is partly a sample-size effect [I].
- **One unseeded run per cell.** No training seed is set [C]. Evaluation draws are unseeded [C]. No replicate exists, so differences of a few hundredths cannot be called real [I].
- **Latent IID vs OOD compares different spaces.** The research log's "distribution gap" (log0504:414-424) subtracts R² from two different encoders [I]. In latent space scGen scores higher in OOD than in IID in 11 of 20 (flavor, group) pairs (e.g. seurat a 0.674 → 0.728) [R].
- **"scGen" is not scGen.** It is a plain AE (beta 0, hidden 256) with an unbalanced mean shift [C], smaller and shorter-trained than even the CellOT repo's scGen config ([512, 512], 250k iterations) [C]. IMPACT gets 50k iterations and batch 128, against 250k and 256 in the CellOT paper [C][P].
- **Holdouts are near-OOD and small.** Generic T cells (CL:0000084) and the non-held-out T-cell types stay in training [N]. Group d's evaluation half is about 48 cells per species (generate_data_space_eval_sbatches.py:24-27) [D].
- **Unbalanced OOD split.** The 50/50 holdout split is not stratified by species (cell.py:330-384) [C]. The a ood evaluation pushes 93 mouse cells (CF:318) [D].
- **Mixed assays.** Smart-seq2 cells are in every file (nb01.1#c25; CF:878) [N][D]. The v08 assay filter came later → F10.
- **Data files rewritten after training.** HVG selection was re-run and all dataset files rewritten on 2026-05-10 15:51–15:53, and the configs regenerated at 15:35 (`ls` on FASRC; RES mtimes) [R]; the trained-on data files cannot be checked, and the gene lists depend on a live BioMart query [C].
- **Patchy evaluation history.** The first a/d evaluations were empty, then re-run with different n lists (30,40,80 vs 30,50,80) [R][C].
- **Lost outputs and inconsistent notebooks.** nb13/nb14/01.4/01.5 CSV and figure outputs are gone [R]. nb01.5#c1's output (m1 only) contradicts #c13's (groups a–d and m2), so the cells come from different runs [N]. The nb01.5 committed on 2026-05-06 still shows the failed first run (josh@a15d14c:baseline/analysis/01.5_data_prep_all_holdouts_hvg_flavors.ipynb#c13) although the count-based flavors had trained the day before [N][R]. nb13 and nb14 square r at different points (#c5 in each) [C]. nb01.1#c36/#c38 have no execution count [N].
- **Docs that disagree with results.** ">7000" PTPRC rank (log0504:51) vs 5,323 in nb01.4 [D][N]; log0420:342 (rank 7,183) vs the saved output of the same nb01.1 cell (5,349, #c31) [D][N]; the v3/v3_paper description (log0504:131-136; nb01.5#c0) vs scanpy source [C]; unsupported "smoke tests" claim (log0504:311-315) [D]; nb01.4 group B equals group A (nb01.4#c2) [C].
- **Ortholog table not pinned.** It is fetched live from BioMart [C]. Later code reads a cache at `scripts/.biomart_ortholog_cache.csv` (conny:speciesOT/hub/prep.py:66, 391-392), but no such file, and no other ortholog table for this pool, is in the backup (`ls` of fasrc:BK/scripts; `find -maxdepth 4` over the whole backup) [C][R]. A rebuild today may not give 14,451 genes [I]. The scGen paper pinned BiomaRt v.84 for its orthologs (scgen.txt, Methods, data sets) [P].

## Terms used here

- **HVG flavor**: scanpy recipe for ranking genes by excess variability; here one of five (table above).
- **batch_key='species'**: HVGs scored per species, then merged; the merge rule differs by flavor.
- **groups a–d**: the four T-cell holdout sets in the Setup table; **m1/m2**: monocyte holdouts outside this matrix.
- **1000-cap**: at most 1,000 cells per `cell_type` label per species in the source files.
- **matched pool**: the 12,990 cells (6,495 per species) with equal counts per (cell type, tissue) identity.
- **toggle_ood**: the split; held-out pool split 50/50 into "ood" (always evaluated) and "ignore" (OOD mode) or "train" (IID mode).
- **IID / OOD mode**: the model saw half / none of the held-out cell type; both are evaluated with `--setting ood` on the same half.
- **IMPACT_CellOT**: CellOT's transport map trained mouse → human on the sibling scGen's latent codes.
- **latent_space / data_space**: evaluation on 50 codes / 1,000 genes; a folder name, not a guarantee.
- **aeflag**: the 10 re-evaluations that added `--embedding ae` (SB/eval_dataspace_aeflag).
- **eval_smalln, eval_smalln_latent**: latent re-evaluations with small n for groups a and d.
- **model-scgen**: symlink to `scgen/` that lets evaluate.py find the encoder.
- **v07**: dataset rewritten for anndata 0.7 (CellOT env).
- **r2-means**: Pearson r of mean vectors, squared to R² downstream.
- **method gap / distribution gap**: IMPACT − scGen in one mode / IID − OOD for one model (log0504:414-424).

## What the package needs from this

1. **Data-preparation reference (recommended; deterministic once the ortholog table is fixed).** Inputs: `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_muris/sampled_mouse_shared.h5ad` and `…/tabula_sapiens/sampled_human_shared.h5ad`, `.raw` counts. Config: BioMart one-to-one orthologs; match on (cell_type_ontology_term_id, tissue_ontology_term_id), seed 0; normalize_total 1e4 + log1p; HVG on non-held-out cells, `batch_key='species'`, top 1,000, count layer for seurat_v3/seurat_v3_paper/pearson_residuals; scanpy 1.12. Expected: 14,451 orthologs (nb01.5#c5); 6,495 + 6,495 cells (#c7); held-out / non-held-out counts per group as in the Setup table (#c13); gene lists equal to the `var_names` of the 20 `hvg_{flavor}_{g}_v07.h5ad` files; group-A Jaccard values 0.230 / 0.237 / 0.186 / 0.903 / 0.125 / 0.133 and PTPRC rank 108 under Pearson (nb01.4#c16, #c18) [N]. Tolerance: exact. Caveats: pin the ortholog table first, since the release used is unknown; the `_v07` files on disk come from the 2026-05-10 rebuild, not the trained-on run; nb01.4's PTPRC rank is its own rank of the flavor score (#c14), not scanpy's `highly_variable_rank`, so the package must reproduce that definition to match 108.
2. **Evaluation-layer reference (recommended; no training).** Inputs: RES/hvg_pearson_residuals_a_ood/{scgen,impact_cellot}/evals_ood_data_space/imputed.h5ad (both genuine gene space, 451,776 bytes) and the human "ood" half rebuilt from hvg_pearson_residuals_a_v07.h5ad with toggle_ood (holdout CL:0000625, mode ood, random_state 0, test_size 0.2, groupby condition). Metric: R² of mean vectors over 1,000 genes, unpaired draws of n = 80, 10 reps; biased MMD with gammas `np.logspace(1, -3, 50)`. Expected: scGen R² 0.858, MMD 0.1250; IMPACT R² 0.897, MMD 0.1046 [R]. Spread in the record: the SD over the 10 draws is 0.0079 (R²) and 0.0033 (MMD) for scGen, 0.0065 and 0.0021 for IMPACT (same evals.csv files) [R]. Two independent 10-draw means should then differ by less than about ±0.01 R² and ±0.005 MMD (three standard deviations of the difference) [I]. The 15 duplicate re-draws in the Verdict (max change 0.0093 R², 0.0016 MMD) are latent-space, so they understate the gene-space MMD spread [R][I]. The evaluations ran on 2026-05-05 (scGen) and 2026-05-08 (IMPACT, aeflag), before the dataset rebuild, so rebuilding the human half from today's file assumes the rebuild changed nothing [R][I]. The package's current `R2Evaluation` (conny:src/speciesot/speciesot_core.py:115-128) averages per-gene squared correlation over paired cells; that is a different metric and will not match.
3. **Model-level reference (weak).** Retrain both models for pearson_residuals × a × OOD with the configs in RES/hvg_pearson_residuals_a_ood/*/config.yaml and compare with the numbers in item 2 (latent: scGen 0.678 / 0.0792, IMPACT 0.783 / 0.0643) [R]. No tolerance is supported: training was never repeated. Run at least three seeds before using it as a test.

The full 80-run grid, the data_space-folder tallies and nb13's "best cell" are not worth reproducing.

## Open questions

- Were the 2026-05-05 dataset files identical to the 2026-05-10 rewrites?
- Who or what re-evaluated seurat_v3 a ood IMPACT on 2026-05-10 14:32, and why were those 10 runs picked for the aeflag re-runs?
- What was shown and decided at the 2026-05-12 lab meeting? Was the group B question answered?
- What was said at the 2026-05-08 mentor meeting that kept only seurat_v3 and pearson_residuals (nb15#c0), and why those two? The note is already in a commit made at 08:51 that day (josh@157a180), so when did the meeting take place?
- Did anyone pick an HVG "decision rule" (meeting_notes_2026-04-30.md:50)?
- How large is training noise (seed to seed) for these models?
- Which Ensembl release produced the 14,451 orthologs?
- Who was the mentor ("she") who expected PTPRC among the HVGs?

## Sources

- nb01.1 (conny:speciesOT/baseline/analysis/archive/01.1_hvg_investigation.ipynb), nb01.4 (conny:speciesOT/baseline/analysis/01.4_hvg_flavor_comparison.ipynb), nb01.5 (conny:speciesOT/baseline/analysis/01.5_data_prep_all_holdouts_hvg_flavors.ipynb), nb13 (conny:speciesOT/baseline/analysis/13_hvg_flavor_results.ipynb), nb14 (conny:speciesOT/baseline/analysis/14_hvg_flavor_notebook6_replica.ipynb)
- conny:speciesOT/baseline/analysis/presentation_preparation.ipynb, conny:speciesOT/baseline/analysis/19_uncapped_cd8_ood_data_prep.ipynb (#c0-#c4), conny:speciesOT/baseline/analysis/15_data_prep_full_atlas_no_holdout.ipynb (markdown), conny:speciesOT/baseline/analysis/18_paper_figure_F_G_replica.ipynb (grep only)
- conny:speciesOT/baseline/analysis/cursor_hvg_function_and_metadata_repres.md, conny:speciesOT/baseline/analysis/meeting_notes_2026-04-30.md, conny:speciesOT/baseline/analysis/hvg_flavor_run_matrix.md, conny:speciesOT/baseline/analysis/hvg_flavor_run_matrix.csv
- conny:speciesOT/hub/prep.py (ortholog cache path), conny:speciesOT/baseline/analysis/19_uncapped_cd8_ood_data_prep.py (grep only), conny:cellot/cellot_gpu/configs/models/scgen.yaml, conny:cellot/cellot_gpu/configs/models/cellot.yaml, conny:docs/archaeology/timeline.md
- conny:scripts/generate_hvg_flavor_configs.py, conny:scripts/regenerate_hvg_flavor_run_matrix.py, conny:scripts/submit_hvg_flavor_matrix.sh, conny:scripts/generate_data_space_eval_sbatches.py
- conny:cellot/cellot_gpu/scripts/evaluate.py, conny:cellot/cellot_gpu/cellot/utils/evaluate.py, conny:cellot/cellot_gpu/cellot/data/cell.py, conny:cellot/cellot_gpu/cellot/models/ae.py, conny:cellot/cellot_gpu/cellot/losses/mmd.py, conny:cellot/cellot_gpu/scripts/train.py (byte-identical to the copies under fasrc:BK/cellot/cellot_gpu by checksum; these are end-state copies, e.g. cell.py gained its default-off `stratify` option on 2026-06-09, conny@8a9a103)
- conny:speciesOT/speciesot_helpers.py, conny:speciesOT/hub/readers.py, conny:speciesOT/hub/cli.py, conny:speciesOT/hub/spec.py, conny:src/speciesot/speciesot_core.py
- conny:logs/research_logs/research_log_2026-05-04.txt, conny:logs/research_logs/research_log_2026-04-20.txt, conny:docs/conceptual_framework.md, conny:docs/hub_handoff.md, `conny:docs/maps/Hub Experiments MOC.md`, conny:docs/experiments/gpu__hvg_pearson_residuals_a_iid__impact_cellot.md, conny:docs/archaeology/inventory.csv
- conny@c342331, conny@8a9a103, conny@a10fe24 (git log/diff)
- josh@main:tabula_make_samples.ipynb, josh@main:intraspecies_vs_interspecies_dists.ipynb (#c10-#c21), josh@main:e20_lab_meeting_051226.ipynb (grep for hvg/flavor/IMPACT: no hits; not about this matrix), josh@a15d14c (incl. its 01.5 notebook and speciesot_helpers.py), josh@44a995e, josh@f10f1cf, josh@232b65e, josh@8a2d53a, josh@3c42e96, josh@157a180, josh@da0cbdc (incl. its presentation_preparation.ipynb), josh@7dcd6c1 (git show/log on origin/cellot and origin/main)
- RES/hvg_{seurat,cell_ranger,seurat_v3,seurat_v3_paper,pearson_residuals}_{a,b,c,d}_{iid,ood}/{scgen,impact_cellot}/: config.yaml, evals_ood_latent_space/evals.csv, evals_ood_data_space/evals.csv, train/eval logs (local mirror; all 160 evals.csv recomputed); `imputed.h5ad` sizes and mtimes of all 160 via `ls -la`/`stat` on FASRC (files not opened)
- RES/hvg_*_m2_*, RES/hvg_pearson_residuals_m1_ood, RES/hvg_pearson_residuals_a_ood_uncapped (listing and log mtimes only)
- SB/eval_dataspace, SB/eval_dataspace_aeflag, SB/eval_smalln, SB/eval_smalln_latent, SB/eval (scripts)
- fasrc:BK/docs/model_cards/INDEX.md, fasrc:BK/docs/model_cards/gpu__hvg_pearson_residuals_a_iid__impact_cellot.md, fasrc:BK/docs/model_cards/gpu__hvg_seurat_a_ood__scgen.md, fasrc:BK/docs/model_cards/gpu__hvg_cell_ranger_a_ood__scgen.md, fasrc:BK/docs/model_cards/gpu__hvg_seurat_v3_a_ood__scgen.md, fasrc:BK/docs/model_cards/gpu__hvg_pearson_residuals_a_ood__scgen.md
- fasrc:BK/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/, fasrc:BK/speciesOT/baseline/analysis/hvg_flavor_*outputs and presentation_figure_outputs, fasrc:BK/scripts (listing only); /n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_{muris,sapiens}/sampled_*_shared.h5ad (`ls` only)
- FASRC env `analysis`: scanpy/preprocessing/_highly_variable_genes.py (lines 215-240, 360-450, 560-600, 640-660 read) and scanpy/experimental/pp/_highly_variable_genes.py (grep, lines 205-260 read)
- /tmp/sot-arch/papers/cellot.txt (Methods: i.i.d./o.o.d. design, hyperparameters) [P]; /tmp/sot-arch/papers/scgen.txt (Methods: data sets, "Statistics") [P]

# F07 · Toggle IID vs OOD (T1–T4, M1–M4) and the renormalisation fix

> In April 2026 Conny measured how much a model gains when it has seen half of a held-out cell type ("IID") compared with never seeing it ("OOD"). Conny built 8 holdout groups (4 T-cell, 4 monocyte), trained scGen, IMPACT (CellOT transport from mouse to human in the scGen latent space) and a cell-type CellOT in both modes on the night of 2026-04-08/09, and scored all of them in the 50-dimensional latent space (the compressed code the scGen autoencoder gives each cell). IMPACT beat the notebook scGen baseline in all 16 group × mode cells, but the IID numbers are not clean: the IID encoder was trained on the evaluation cells, and IID and OOD were scored in two different latent spaces. On 2026-04-20 Conny found that the mouse input was clipped at exactly 10 and, judging from its value pattern, also divided per gene by its standard deviation. A re-normalised re-run of four T-cell holdouts (04-21) scored higher, but it was scored in latent space while the old runs were scored in gene space, so the gain is not demonstrated; compared in the same (latent) space, the change is mixed. Status: partly worked — the runs completed and the scale bug was found and fixed, but neither the IID–OOD gap nor the renorm gain was measured cleanly.

| | |
|---|---|
| Period | 2026-04-08 → 2026-04-21 for runs: first toggle job 04-08 23:49, last renorm evaluation 04-21 10:47 [R] (file times of fasrc:BK/cellot/cellot_gpu/results/toggle_*/scgen/train_44*.{out,err} and renorm_*/*/eval_*.out). Asked for at the 03-30 mentor meeting [D] (conny:logs/research_logs/research_log_2026-03-30.txt:201-210; research_log_2026-04-08.txt:9-27). Design notebook 11 committed 2026-04-30 [G] (josh@232b65e). |
| People | Conny: all code, runs, notebooks and logs [G] (josh@a1efc54, josh@8a2d53a, josh@232b65e; author "Junyi Zhou"). The mentor (the logs give no name; Josh [I]) asked for the IID comparison and a non-classical-monocyte holdout on 03-30 [D] (research_log_2026-03-30.txt:201-210; research_log_2026-04-08.txt:12). Mentor meeting 04-21 [D] (conny@c342331:logs/mentor_meetings/2026-04-21_mentor_meeting_slides.md). |
| Status | partly worked |
| Main code | conny:speciesOT/baseline/analysis/09_data_prep_toggle_experiments.ipynb · conny:speciesOT/baseline/analysis/10_iid_vs_ood_evaluation.ipynb · conny:cellot/cellot_gpu/cellot/data/cell.py:330-384 (a later vendored copy; the April library is lost, see Setup) · conny:cellot/cellot_gpu/scripts/evaluate.py · conny:speciesOT/baseline/analysis/01.3_data_prep_all_holdouts_renorm.ipynb · conny:speciesOT/baseline/analysis/08.1_renorm_vs_stale_comparison.ipynb |
| Results live in | fasrc:BK/cellot/cellot_gpu/results/toggle_{t1..t4,m1..m4}_{iid,ood}/{scgen,impact}/ · fasrc:BK/cellot/cellot_gpu/results/_archive/toggle_cellot_subdirs/toggle_*/cellot/ · conny:speciesOT/baseline/analysis/toggle_ood_all_results.csv and toggle_ood_iid_vs_ood_comparison.csv (notebook 10 exports, the only scGen numbers) · fasrc:BK/cellot/cellot_gpu/results/renorm_{cd8,cd8_thymo,tcell_subtypes,cd4}/{scgen,swapped_cellot,normal_cellot}/ · conny@c342331:autospeciesOT/results_renorm_vs_stale{,_delta}.tsv (deleted in conny@4200f8e) · conny:speciesOT/baseline/analysis/immune_ontology_outputs/ |

## The question

- The 03-30 log lists an IID baseline among next steps "carried forward from March 25th meeting", with the reason: "If IID performance is also poor, the issue is fundamental (model capacity, data quality) rather than OOD generalization" [D] (research_log_2026-03-30.txt:154, 173-178). The 03-30 mentor meeting then asked to "Perform in distribution comparison", to "Leave out the non-classical monocyte ... (important to include scGEN)", and for "CD8, nonclassical, and IID" presentation figures [D] (research_log_2026-03-30.txt:201-210; research_log_2026-04-08.txt:9-27). A holdout is a cell type removed from training; OOD (out of distribution) means the model never saw it; IID (in distribution) means it saw part of it.
- The design copies the CellOT paper: i.i.d. and o.o.d. models are scored "on the same subset of holdout cells", and "i.i.d. models have seen the remaining holdout cells during training" [P] (CellOT, Methods "Setup"; nb09#c0 names this source).
- The plan: 8 groups × 2 modes × 3 models = 48 trainings and 32 evaluations, with scGen "handled separately" [D] (research_log_2026-04-08.txt:476-478).
- After 04-20 a second question appeared: do the results change once both species are normalised the same way ("Rerun all previously-reported cross-species results on the re-normalized pipeline") [D] (research_log_2026-04-20.txt:517-521).
- Notebook 11 (04-30) asked how to design later immune holdouts along lineage distance [D] (markdown, conny:speciesOT/baseline/analysis/archive/11_immune_cell_ontology.ipynb#c0).

## Setup

**Data (toggle runs).** Cells came from Tabula Sapiens (human) and Tabula Muris (mouse) through the upstream `.X` matrix, i.e. on the "stale" scale (the mismatched mouse/human scaling found on 04-20): 58,852 human and 47,802 mouse cells [N] (09_data_prep_toggle_experiments.ipynb#c3). One donor per species was silently missing (human TSP13, 79 cells; mouse 3-M-8/9, 5 cells) because `top_n_organisms_from_species(..., -1)` sliced `[:-1]` [D] (research_log_2026-04-13.txt:338-372). Genes were BioMart one-to-one orthologs (genes that correspond one-to-one between species): 14,451 [N] (nb09#c5). 1,000 HVGs (highly variable genes) were picked with scanpy flavor `seurat` on all 106,654 cells pooled, without `batch_key` (the option that measures gene variability within each species separately), so the held-out cells took part in feature selection [C] (nb09#c6). Cells were then matched by (cell type, tissue): 6,418 mouse + 6,418 human = 12,836 [N] (nb09#c7). Each group got four files [C] (nb09#c11): `_ae_training_ood` (whole atlas minus every cell of the holdout types), `_ae_training_iid` (whole atlas, 106,654 cells, the same content for all 8 groups), `_holdout` (the 12,836 matched cells, condition = species) and `_holdout_swapped` (same cells, condition = "holdout type" vs "rest").

| Group | Holdout (CL = Cell Ontology ID) | Matched holdout cells | Evaluation half (both species) | Atlas cells removed from OOD encoder | Largest n per side evaluated (IMPACT / CellOT-ct) |
|---|---|---|---|---|---|
| T1 | CD8 (CL:0000625) | 390 | 195 | 1,998 | 80 / 100 |
| T2 | CD8 + thymocyte (+CL:0000893) | 1,300 | 650 | 3,453 | 250 / 250 |
| T3 | CD4 + CD8 + thymocyte (+CL:0000624) | 1,490 | 745 | 5,452 | 250 / 250 |
| T4 | CD4 (CL:0000624) | 190 | 95 | 1,999 | 30 / 30 |
| M1 | non-classical monocyte (CL:0000875) | 852 | 426 | 2,000 | 100 / 100 |
| M2 | non-classical + "monocyte" (+CL:0000576) | 1,012 | 506 | 3,997 | 100 / 100 |
| M3 | all four monocyte labels (+CL:0000860, CL:0002393) | 2,202 | 1,101 | 7,997 | 500 / 500 |
| M4 | classical monocyte (CL:0000860) | 182 | 91 | 2,000 | 30 / 30 |

Sources: group definitions and counts [N] (nb09#c9, #c11); evaluation half = half of the holdout cells [I]; largest n from the `ncells` column [R] (fasrc:BK/cellot/cellot_gpu/results/toggle_*/impact/evals_ood_latent_space/evals.csv and _archive/toggle_cellot_subdirs/*/cellot/...). "M" groups are monocyte labels only, not other myeloid cells [N] (nb09#c9). T3 is named "All T cell subtypes" but leaves the broad "T cell" label (CL:0000084, 204 matched cells) in training [N] (nb09#c7, #c9).

**Models.**
- scGen here is CellOT's `scgen` autoencoder (AE, a network that compresses each cell to a short code and decodes it back): hidden layers [256, 256], latent size 50, dropout 0.1, beta 0 (no KL term), lr 1e-3, 50,000 iterations, trained on the `_ae_training_{mode}` file with its own 80/20 train/test split [C] (fasrc:BK/cellot/cellot_gpu/results/toggle_t1_iid/scgen/config.yaml). Its prediction exists only in notebook 10: encode, add delta = mean human code − mean mouse code over training cells of the matched file, no decoding [C] (10_iid_vs_ood_evaluation.ipynb#c5). This is not the scGen paper's cell-type balancing [P] (scGen, delta definition), but the matched file already has equal (cell type, tissue) counts in both species [C] (conny:speciesOT/speciesot_helpers.py:465-488).
- IMPACT: CellOT's ICNN (input-convex neural network, the learned transport map), 4 × 64 units, lr 1e-4, batch 128, 50,000 iterations, 10 inner steps, run on the 50-d codes of the same run's scGen encoder; condition = species, mouse → human [C] (toggle_t1_iid/impact/config.yaml). The CellOT paper used batch 256 and 250k iterations [P] (CellOT, Methods "Hyperparameters" and "Setup").
- CellOT-ct (this page's label for the cell-type framing; on disk `cellot/`): the same ICNN with source = non-holdout cells, target = holdout cells (e.g. `non_cd8` → `cd8`), and the toggle applied to species with `holdout: human` [C] (fasrc:BK/cellot/cellot_gpu/results/_archive/toggle_cellot_subdirs/toggle_t1_iid/cellot/config.yaml).

**What "IID" and "OOD" meant.** `split_cell_data_toggle_ood` first splits every cell 80/20 into train/test within each condition, then splits the held-out cells 50/50 with `random_state=0` and no stratification; in `ood` mode the first half becomes `ignore` (unused), in `iid` mode it becomes `train`; the second half is always `ood` [C] (conny:cellot/cellot_gpu/cellot/data/cell.py:330-384; this copy's optional `stratify` argument was added later, in conny@8a9a103 on 2026-06-09, so the code as of April is closer to conny@c342331:cellot/cellot_gpu/cellot/data/cell.py:322-353). Every evaluation used `--setting ood`, i.e. the `ood` half [C] (fasrc:BK/sbatch/eval/eval_toggle_*.sbatch). So `mode` names the training data and `--setting` names the evaluated slice [D] (conny:docs/conceptual_framework.md:254-272). The exposure differed by component:

| Component | OOD mode saw | IID mode saw |
|---|---|---|
| scGen encoder (used by all three models) | atlas minus all cells of the holdout types | the whole atlas, including the evaluation half (about 80% of it fell in the AE's train split) |
| IMPACT transport | no holdout-type cells | half of the matched holdout cells, both species |
| CellOT-ct transport | mouse cells only | mouse cells plus half of the human cells |
| scGen delta (notebook 10) | non-holdout matched cells | all matched cells except the evaluation half |

Sources: [C] (nb09#c11; toggle_*/{scgen,impact}/config.yaml; _archive/.../cellot/config.yaml; nb10#c5); "about 80%" is [I] from `test_size: 0.2`.

**Evaluation.** IMPACT and CellOT-ct were scored with `scripts/evaluate.py --setting ood --where latent_space`, so predictions and targets are 50-d codes [C] (fasrc:BK/sbatch/eval/eval_toggle_t1_iid_impact.sbatch). For each n in `--n_cells` it draws 10 unseeded subsamples of n target and n predicted cells and stops at the first n larger than the smaller cloud [C] (evaluate.py:194-204). Metrics: `r2-means`, which is the unsquared Pearson r between the two mean vectors (here across 50 latent dimensions) [C] (evaluate.py:73); and MMD (maximum mean discrepancy, a kernel distance between two clouds; 0 = same distribution) averaged over 50 RBF bandwidths `np.logspace(1,-3,50)`, using the biased estimator whose floor shrinks with n [C] (evaluate.py:63, 78-80; conny:cellot/cellot_gpu/cellot/losses/mmd.py:5-10). Default n was 100,250,500,1000,1500 [C] (evaluate.py:19-21); T1-IMPACT was re-run with 25,50,80, and T4 and M4 (both IMPACT and CellOT-ct) with 10,20,30, because the default-n evaluations computed no draws (their eval_*.out logs contain no `ncells=` lines, so evals.csv held only a header) [C][R] (fasrc:BK/sbatch/eval/eval_toggle_{t1,t4,m4}_*.sbatch; toggle_*/impact/eval_*.out and eval_re_*.out; _archive/toggle_cellot_subdirs/toggle_{t4,m4}_*/cellot/eval_re_*.out). Notebook 10 keeps only the largest n, averages r over the 10 draws and squares it [C] (nb10#c3). scGen was scored inside notebook 10 on the full evaluation clouds, with no subsampling, using the same kernel and bandwidths [C] (nb10#c5). Seeds: all splits use `random_state=0`; training sets no seed [C] (no `seed` in conny:cellot/cellot_gpu/scripts/train.py or cellot/train/train.py); each mode has one run.

**Code that actually ran.** Training imported the CellOT library from an editable install at `/n/holylabs/.../speciesOT/cellot/cellot`, outside git and absent from the backup [R] (traceback in fasrc:BK/cellot/cellot_gpu/results/toggle_t1_iid/scgen/train_4408933.err; the CellOT env's `cellot.egg-link` on FASRC points there). The vendored copy above is the nearest record [I]. An upstream CellOT copy crashes on list holdouts (`value` undefined) [C] (mac:OptimalTransport/CellOT/cellot/cellot/data/cell.py:325-328). The April library had exactly this bug at first: the first IMPACT attempts of the four list-holdout groups (T2, T3, M2, M3; 8 runs) crashed at 00:35 on 04-09 with `UnboundLocalError: local variable 'value'` at cell.py line 328 [R] (e.g. fasrc:BK/cellot/cellot_gpu/results/toggle_t2_iid/impact/train_4423913.err). The second attempts trained, so the library was patched in between; the patch itself is not recorded [R][I].

**Renorm re-run (setup).** Notebook 01.3 read the raw counts from `.raw`, applied `normalize_total(1e4)` + `log1p` (scale each cell to 10,000 total counts, then take log(1 + x)) to each species on its full gene set, then aligned orthologs (14,451) [N] (01.3_data_prep_all_holdouts_renorm.ipynb#c3, #c5). HVGs: flavor `seurat`, `batch_key="species"`, on all 106,738 cells; 269 of the 1,000 were variable in both species [N] (01.3#c9). Matched cells: 6,495 + 6,495 = 12,990, all donors [N] (01.3#c11, #c15). Groups A–D re-ran the earlier T-cell holdouts of F06, not the toggle groups: A = CD8; B = CD8 with thymocytes removed from the AE only; C = CD4 + CD8 + thymocyte; D = CD4 [N] (01.3#c13). Hyperparameters equal the stale runs [C] (renorm_cd8/*/config.yaml vs speciesot_cd4/*/config.yaml). The split is `train_test` with every holdout cell in `ood`, so there is no IID arm [C] (renorm_cd8/swapped_cellot/config.yaml). Evaluation: latent space, largest n = 100 (A, B), 500 (C), 80 (D) [R] (renorm_*/*/evals_ood_latent_space/evals.csv). The stale counterparts (`speciesot_*` runs) were last evaluated in gene space on 2026-04-06, by one job that re-scored all 8 of them between 00:01 and 00:16 [R] (fasrc:BK/cellot/cellot_gpu/results/eval_all_3691082.out; file times of speciesot_*/*/evals_ood_data_space/evals.csv). Their imputed.h5ad sizes fit 1,000 features (866,233 bytes for 195 CD8 cells), the renorm ones fit 50 (75,190 bytes for 195 cells) [R][I] (FASRC `ls -l`; files not opened).

**Non-standard choices.** (1) Metrics on 50 latent dimensions; the paper computes r² and ℓ2 on the ~1,000 genes and MMD on the top 50 marker genes, and calls its MMD "an unbiased estimate" [P] (CellOT, Methods "Feature selection" and "maximum mean discrepancy"). (2) HVGs from all cells; the paper computes them "on the training set only" [P] (CellOT, Methods "Single-cell RNA sequencing data"). (3) Evaluation clouds of 30–500 cells per side; the paper's test sets hold 500–1,000 cells [P] (CellOT, Methods "Setup"). (4) Transport trained 5× shorter than in the paper [C][P].

## What was done and what came out

### 2026-04-08 · Decisions before the runs

- Notebooks now square `r2-means`, because evaluate.py stores Pearson r under that name [D] (research_log_2026-04-08.txt:182-197, 342-344).
- "All future experiments must use the original CellOT paper's evaluate.py ... We will NOT invent new metric functions in analysis notebooks" [D] (same file:336-341).
- CellOT-family models move to `--where latent_space` [D] (same file:244-276).
- The toggle design was written down, including: "IID mode: ae_training file INCLUDES all cells (no exclusion). This gives scGen a slight advantage in IID ... Acceptable since IID-vs-OOD comparisons are per-model" [D] (same file:464-470). The same log says both CellOT-family models "use scGen purely for dimension reduction" [D] (same file:260-261), but section 8 does not connect the two: the exposed encoder also serves IMPACT and CellOT-ct [I].

### 2026-04-08 23:49 → 04-09 09:49 · Data build and runs

- Notebook 09 wrote 32 files with a custom h5py writer, so that the old anndata 0.7 (the library that reads `.h5ad` files) in the CellOT environment could read them [N] (nb09#c9, #c11, #c13). The files on FASRC date from 00:31 on 04-09: they were rewritten after the third scGen attempt failed on file reading, and the fourth attempt (00:34) read them [R] (FASRC `ls -l`; train_*.err times).
- scGen trained on the CPU partition `shared`; both transports on `gpu_requeue` with one GPU [C] (fasrc:BK/sbatch/train/train_toggle_*.sbatch).
- Every one of the 16 scGen runs failed four times before a fifth attempt finished 50,000 iterations: three times on reading the file (`/layers`, then `/obs/condition` twice) and once on a missing `hidden_units` [R] (toggle_*/scgen/train_*.err; e.g. toggle_t1_iid/scgen/train_{4408933,4416570,4421280,4423895,4426365}.err). Every transport failed once: 8 IMPACT runs on the `value` bug (see Setup), the other 8 IMPACT and all 16 CellOT-ct runs on the same `hidden_units` assertion while loading the encoder [R] (first train_*.err of each toggle_*/impact and _archive/.../cellot directory). Of the first evaluation jobs, 30 were cancelled together at 00:36 and one crashed on the `value` bug [R] (first eval_*.err of each directory).
- The best-checkpoint files (cache/model.pt, rewritten whenever the test loss or test MMD improved) date 00:52–01:19 for the encoders and 01:30–02:18 for the transports; the training logs end at 01:12–01:25 and 01:56–02:26 [R] (FASRC file times) [C] (conny:cellot/cellot_gpu/cellot/train/train.py:152-158, 233-240). Each transport started after its encoder had finished (start = log end time minus the elapsed time shown by the progress bar), so each used its final encoder [R][I]. Evaluations ran 02:27–02:28, re-evaluations 09:48–09:49 on 04-09 [R] (evals.csv file times).
- Log files hold 217 job IDs: 144 training, 63 evaluation, 10 re-evaluation [R] (file names in toggle_* and _archive/toggle_cellot_subdirs). An earlier sacct survey (Slurm accounting) counted 234 toggle jobs: 90 completed, 113 failed, 31 cancelled [unverified: survey lead; sacct not re-queried]. If right, 90 = 48 trainings + 32 evaluations + 10 re-evaluations [I]. The 04-13 log says "all 80 jobs completed" [D] (research_log_2026-04-13.txt:324).

### 2026-04-09 · Results (notebook 10)

R² (squared Pearson r of mean latent vectors; higher is better):

| Group | IMPACT OOD | IMPACT IID | CellOT-ct OOD | CellOT-ct IID | scGen OOD | scGen IID |
|---|---|---|---|---|---|---|
| T1 CD8 | 0.841 | 0.867 | 0.712 | 0.909 | 0.645 | 0.710 |
| T2 CD8+thymo | 0.829 | 0.843 | 0.681 | 0.917 | 0.587 | 0.669 |
| T3 T subtypes | 0.797 | 0.872 | 0.728 | 0.883 | 0.582 | 0.562 |
| T4 CD4 | 0.772 | 0.759 | 0.414 | 0.795 | 0.336 | 0.391 |
| M1 non-classical | 0.731 | 0.790 | 0.595 | 0.949 | 0.427 | 0.445 |
| M2 non-class.+mono | 0.751 | 0.821 | 0.680 | 0.944 | 0.439 | 0.468 |
| M3 all monocytes | 0.641 | 0.824 | 0.458 | 0.972 | 0.352 | 0.640 |
| M4 classical | 0.714 | 0.679 | 0.494 | 0.775 | 0.410 | 0.452 |

MMD (lower is better):

| Group | IMPACT OOD | IMPACT IID | CellOT-ct OOD | CellOT-ct IID | scGen OOD | scGen IID |
|---|---|---|---|---|---|---|
| T1 | 0.0221 | 0.0219 | 0.0322 | 0.0159 | 0.0872 | 0.0883 |
| T2 | 0.0202 | 0.0183 | 0.0520 | 0.0123 | 0.1254 | 0.1247 |
| T3 | 0.0233 | 0.0146 | 0.0407 | 0.0130 | 0.1256 | 0.1134 |
| T4 | 0.0495 | 0.0490 | 0.0796 | 0.0453 | 0.1324 | 0.1541 |
| M1 | 0.0357 | 0.0317 | 0.0550 | 0.0192 | 0.0889 | 0.0807 |
| M2 | 0.0310 | 0.0274 | 0.0901 | 0.0192 | 0.0916 | 0.0749 |
| M3 | 0.0317 | 0.0243 | 0.0971 | 0.0077 | 0.0925 | 0.0823 |
| M4 | 0.0506 | 0.0563 | 0.1109 | 0.0579 | 0.1169 | 0.1135 |

Sources: IMPACT and CellOT-ct [R] — I re-derived every value from the evals.csv files listed in the header table, and they match nb10#c3. scGen [N] (nb10#c5; conny:speciesOT/baseline/analysis/toggle_ood_all_results.csv); no scGen result file from a run exists.

- IID − OOD in R²: IMPACT −0.035 (M4) to +0.183 (M3), positive in 6 of 8; CellOT-ct +0.156 to +0.513, positive in 8 of 8; scGen −0.020 (T3) to +0.288 (M3) [R][N] (conny:speciesOT/baseline/analysis/toggle_ood_iid_vs_ood_comparison.csv). Family means: monocyte CellOT-ct 0.3535, IMPACT 0.0690, scGen 0.0939; T cell CellOT-ct 0.2428, IMPACT 0.0256, scGen 0.0458 [N] (nb10#c16).
- IMPACT beat scGen on both R² and MMD in all 16 group × mode cells [R][N] (tables above).
- Spread of R² across the 10 subsamples (one standard deviation): 0.004 (M3, n=500) to 0.065 (T4, n=30) [R] (my computation from the evals.csv files). The IMPACT T4 and M4 differences (−0.013, −0.035) are within about two standard errors of that subsampling noise [I]. Training-run noise was never measured (one run per cell) [C].
- The largest IID gains for all three models are in M3, whose IID encoder saw the most extra holdout-type atlas cells (7,997) [N][I]. M3 is also where IID mode added the largest share of holdout-type cells to the transport's training cells (about 550 per species, 11% of them, against 1–8% in the other groups), and the two negative IMPACT gains (T4, M4) are where that share was smallest (about 1%) [I] (from the counts in nb09#c7, #c11 and `test_size: 0.2`). Encoder exposure and transport exposure rise together across the 8 groups, so these runs cannot tell which one drives the gain [I].
- The T4 and M4 rows (n = 30) have the highest IMPACT MMDs, as expected if the n-dependent floor of the biased MMD dominates [I].
- No conclusion was written. Notebook 10 has no conclusion cell (its last cells print numbers, draw bar charts and export CSVs), and the 04-13 and 04-20 logs still list "Run notebook 10 for IID/OOD results analysis" as open, although notebook 10 had run on 04-09 [N] (nb10#c11-c18) [D] (research_log_2026-04-13.txt:329; research_log_2026-04-20.txt:544) [G] (josh@a1efc54).

### 2026-04-13 · Donor bug found

The `n=-1` slicing bug was fixed in the helper [D] (research_log_2026-04-13.txt:374-386). The toggle files were not rebuilt: notebook 09 still shows 58,852 / 47,802 cells [N] (nb09#c3), and all 32 toggle files on FASRC are dated 2026-04-09 00:31 [R] (FASRC `ls -l` of fasrc:BK/cellot/cellot_gpu/datasets/speciesot-human-mouse/toggle_*).

### 2026-04-20 · Scale mismatch found

- While checking why PTPRC was not an HVG, Conny found, on the 6,495 matched cells per species, human `.X` max 8.5077 with 672,062 unique non-zero values out of 16.9 million, and mouse `.X` max exactly 10.0000 with 10.6 million unique out of 13.1 million [N] (conny:speciesOT/baseline/analysis/archive/01.1_hvg_investigation.ipynb#c18-#c21). Mouse cell 0 has several genes at exactly 10.0000 [N] (01.1#c22).
- On matched, aligned cells: mouse max 10.0000 with 9,961 unique values in a 10,000-value sample; human max 8.5077 with 139 unique [N] (01.2_pipeline_comparison.ipynb#c4). Few unique values is the pattern of `log1p(normalize_total(counts))`; many unique values plus a hard maximum of 10 fit `sc.pp.scale(zero_center=False, max_value=10)` on top of it [D] (research_log_2026-04-20.txt:42-104). The clip is visible directly; the per-gene `/std` step is inferred from these fingerprints [I].
- Both files carry raw integer counts in `.raw` [N] (01.1#c24), and `ad.concat` drops `.raw`, `.layers` and `.uns` [D] (research_log_2026-04-20.txt:107-198).
- After re-normalising from counts: mouse max 8.8695 (265 unique), human 8.8025 (147 unique) [N] (01.2#c7). The old and new HVG sets share 74 of 1,000 genes; CD8A moves from rank 14,363 to 168, CD14 from 4,061 to 138; PTPRC stays outside the top 1,000 (rank 5,349) [N] (01.2#c9, #c10). This comparison changes normalisation, `batch_key` and the HVG cell pool at once, and its "Pipeline A" computes HVGs on 12,990 matched cells, not on the 106,654 cells the runs used [C] (01.2#c3; nb09#c6). Its "Pipeline B" normalises after ortholog alignment on the matched cells, while 01.3 (used for the renorm runs) normalises before alignment on all cells, so these overlap and rank numbers describe neither the toggle nor the renorm HVG list exactly [C] (01.2#c6; 01.3#c3, #c5, #c9).
- Sequencing-protocol imbalance (mouse 36.6% Smart-seq2, human 5.8% [N] (01.1#c25); Smart-seq2 reports read counts, not molecule counts) was noted and deferred [D] (research_log_2026-04-20.txt:383-416).

### 2026-04-21 · Renorm re-run and comparison (01.3, 08.1)

- 16 training jobs (the 4 first scGen attempts failed on `/layers`; 12 completed) and 10 evaluation jobs (the first two CD4 evaluations wrote header-only files and were re-run with `--n_cells 50,80`) [R] (renorm_*/*/train_*.err, eval_*.out) [D] (research_log_2026-04-20.txt:602-607). All ran on the CPU partition `shared` [C] (fasrc:BK/sbatch/train/renorm/*.sbatch); the log says "GPU partition" [D] (research_log_2026-04-20.txt:557).
- Notebook 08.1 found renorm better on R² in 7/8, on the std-R² in 5/8, on MMD in 6/8 group × model cells, best = renorm / CD4 / IMPACT (R² 0.8157, MMD 0.0442) [N] (08.1_renorm_vs_stale_comparison.ipynb#c9, #c13). All 16 values re-derived from the evals.csv files match [R]. The combined-rank Spearman correlation between families is −0.118 [N] (08.1#c17). The "Summary and Takeaways" cell is an unfilled template [D] (markdown, 08.1#c16). The 04-21 slides show neither this comparison nor the toggle results; the log's "Slide deck update" item for the renorm comparison stayed unticked [D] (conny@c342331:logs/mentor_meetings/2026-04-21_mentor_meeting_slides.md; research_log_2026-04-20.txt:688-689).
- The log reads the rank change as evidence that "The stale pipeline's ranking was partly driven by species-specific scale confounds" [D] (research_log_2026-04-20.txt:651-664).

R² of IMPACT and CellOT-ct, three ways:

| Holdout | Model | Stale data, gene space (04-06) | Renorm data, latent (04-21) | Stale data, latent: toggle OOD run (04-09) |
|---|---|---|---|---|
| CD8 (A; T1) | IMPACT | 0.685 | 0.775 | 0.841 (n=80, half the cells) |
| CD8 (A; T1) | CellOT-ct | 0.624 | 0.730 | 0.712 |
| CD8, thymocytes out of AE (B) | IMPACT | 0.674 | 0.747 | — |
| CD8, thymocytes out of AE (B) | CellOT-ct | 0.558 | 0.691 | — |
| CD4+CD8+thymocyte (C; T3) | IMPACT | 0.641 | 0.666 | 0.797 (n=250) |
| CD4+CD8+thymocyte (C; T3) | CellOT-ct | 0.507 | 0.484 | 0.728 |
| CD4 (D; T4) | IMPACT | 0.597 | 0.816 | 0.772 (n=30) |
| CD4 (D; T4) | CellOT-ct | 0.572 | 0.769 | 0.414 |

Sources: stale and renorm [N] (08.1#c7), re-derived [R] (speciesot_*/*/evals_ood_data_space/evals.csv; renorm_*/*/evals_ood_latent_space/evals.csv); toggle column [R] (tables above).

- My cross-check [I]: the toggle OOD runs used the stale data, the same HVG call and the same transport design as the stale runs, and the same encoder cell pools: 104,656 cells as stale A, 101,202 as stale C, 104,655 as stale D [N] (archive/05_expanded_training_CD8_holdout.ipynb#c7, #c13; archive/07_data_prep_all_holdouts.ipynb#c5, #c10; nb09#c6, #c11). Stale A's encoder file has another name (`ae_training_expanded_v07.h5ad`, from notebook 05; see F06) but the same cells [C][N] (fasrc:BK/cellot/cellot_gpu/results/speciesot_cd8/speciesot_scgen/config.yaml; archive/05#c13). In latent space the toggle OOD runs already scored 0.16–0.18 higher for IMPACT than the stale gene-space runs. Holding the space fixed at latent, renorm IMPACT is lower for CD8 and T-cell subtypes and higher for CD4; renorm CellOT-ct is higher for CD8 and CD4 and lower for T-cell subtypes. The pairs still differ in evaluated cells (half vs all holdout cells), n, and encoder training run (same cells, separate unseeded runs), so this is weak evidence either way.
- Latent scales may also differ: IMPACT `l2_means` (the distance between predicted and true mean codes) is 0.85 in toggle T1-OOD but 3.2–4.4 in the renorm runs at similar R², which suggests larger latent coordinates in the renorm encoders; if so, MMD values with one fixed bandwidth grid are not comparable across these latent spaces [N][I] (toggle_ood_all_results.csv; conny@c342331:autospeciesOT/results_renorm_vs_stale.tsv).

### 2026-04-30 · Immune ontology design (notebook 11)

- A design-only notebook: 11 shared immune types with CL IDs, a simplified lineage tree, and A/B/C/D holdout templates (focal type; plus nearest sibling; plus all siblings; one distant type) for five focal candidates [N] (11_immune_cell_ontology.ipynb#c4, #c6, #c12). It does not count cells [D][C] (markdown #c0; scaffold-only code #c14).
- For dendritic cell, macrophage and neutrophil, templates B and C are identical; for plasma cell A = B = C [N] (#c12). The meeting note proposes NK cell as "cleanest" and leaves the choice open [D] (conny:speciesOT/baseline/analysis/meeting_notes_2026-04-30.md).
- Its "dendritic cell" ID CL:0000451 does not occur in the matched data, which has CL:0000782 and CL:0000784 [N] (nb11#c4; nb09#c7); an exact-ID holdout would select nothing [I]. Its "T cell" ID (CL:0000084) and "monocyte" ID (CL:0000576) are parent terms: in the matched data they label only 204 and 160 cells, while CD4, CD8 and thymocyte (1,490 cells) and the classical, non-classical and intermediate monocytes (2,042 cells) carry their own IDs [N] (nb09#c7). An exact-ID "T cell" holdout (NK-cell templates B and C, macrophage template D) would leave the T-cell subtypes in training [I]. The planned data audit `11.1` and `immune_ood_chosen.json` were not found (searched all tracked files in conny, josh history, the inventory and the FASRC mirror) [I].

### May 2026 · What happened next

- 05-04: the HVG-flavor matrix (F08) replaced the two-file toggle pipeline with one data file per group and `toggle_ood` for both scGen and IMPACT, with HVGs per group from training cells [D] (research_log_2026-05-04.txt:52-61, 168-198, 245-290). That log describes the April IID encoder file as holding half of the holdout cells [D] (same file:256-258); notebook 09 actually wrote all cells [C] (nb09#c11).
- 05-10: notebook 10's label for CellOT-ct changed from `CellOT` to `IMPACT_CellOT` in the code only; saved outputs still say `CellOT` [G] (diff josh@a1efc54..josh@f10f1cf).
- 05-27: the 16 CellOT-ct runs were moved to `_archive/toggle_cellot_subdirs/`; the framing is "dead" because of the source/target size imbalance and "No coherent biological question" [G] (conny@17562ba) [D] (conceptual_framework.md:41-64).
- 05-28: the unstratified split and the missing within-distribution anchor were documented [D] (conceptual_framework.md:378-513). v08 configs add `stratify: condition` [C] (fasrc:BK/cellot/cellot_gpu/results/hvg_pearson_residuals_m2_v08_ood/impact_cellot/config.yaml).
- The M1 and M2 holdout definitions live on in the v08 benchmark cuts [C] (hvg_pearson_residuals_m{1,2}_v08_ood/impact_cellot/config.yaml) [D] (conny:AGENTS.md).

## Verdict

- What is solid: the runs happened as configured, and every IMPACT, CellOT-ct, stale and renorm number in notebooks 10 and 08.1 matches a result file [R]. The CellOT library that ran is lost, so its exact code is known only from tracebacks and later copies [R][I]. The scale mismatch is real and directly visible (mouse values clipped at exactly 10) [N].
- IMPACT vs scGen: in latent space IMPACT won all 16 cells on R² and MMD [R][N]. The scoring protocol favoured scGen (full clouds give less noisy means and a smaller MMD floor), so this ranking is not an artefact of that difference [I]. It is still one run per cell, on stale data, in latent space only. A later gene-space spot check on other data found IMPACT 0.86 vs scGen 0.87 [D] (conceptual_framework.md:312-337); see F08.
- IID vs OOD: these runs cannot measure a generalisation gap. The IID encoder saw the evaluation cells, IID and OOD were scored in different latent spaces, there is no within-distribution anchor, and there is one run per cell [C]. For IMPACT the measured IID gain is small (≤ 0.075) outside M3 [R]; read literally, seeing half of a cell type barely helped, but the confounds stop any conclusion, and the groups where the gain is largest are also those where both the encoder and the transport saw the most extra holdout-type cells [I].
- IMPACT vs CellOT-ct: not a model comparison. The two models predict different cells from different sources, and CellOT-ct's IID mode adds human cells, not holdout-type cells [C].
- Renorm vs stale: the fix is sound in principle [I]. The claimed gain (7/8, 6/8) is not shown, because the evaluation space changed together with the data [C][R] (08.1#c1 `evals_sub`; evals_ood_data_space vs evals_ood_latent_space directories; imputed.h5ad sizes); the log admits this [D] (research_log_2026-04-20.txt:644-649). A Spearman ρ of −0.12 on 8 single-run points carries no information [I]. In the closest same-space comparison, the change is mixed [I].
- Checks of earlier survey leads: confirmed — the latent R² ranges (IMPACT 0.64–0.87, scGen 0.34–0.71), the 7/8 and 6/8 counts, ρ = −0.12, the unfilled takeaway, the scGen full-cloud versus subsampled MMD, and the IID encoder leakage. Corrected — (a) "iid adds back the ignore half" is true only for the IMPACT transport: the encoder saw all holdout cells, and CellOT-ct toggles species; (b) the `IMPACT_CellOT` label for the cell-type model exists only in code changed on 05-10, while the saved outputs say `CellOT`; (c) "M" groups are monocyte labels only. Not re-checked — the Slurm counts: 90 completed equals the number of successful runs in the log files, but 234 jobs exceed the 217 log files [I].

## Why it stopped

- Toggle line: no stated reason. The record shows [I]: the results were never written up (see above); on 04-21 "any metric / training run from before this fix = stale until rerun" [D] (conny@c342331:logs/mentor_meetings/2026-04-21_mentor_meeting_slides.md, §8); the toggle groups were never re-run on renormalised data under their own names [R] (no such directories in fasrc:BK/cellot/cellot_gpu/results/); the IID/OOD question moved to the HVG-flavor matrix (F08) [D] (research_log_2026-05-04.txt:1-10); and CellOT-ct was declared dead [D] (conceptual_framework.md:59-64).
- Renorm: no stated reason. Its follow-ups (re-score the stale runs in latent space; explain group C) were still open on 05-04 [D] (research_log_2026-05-04.txt:497-513) and no later file closes them [I]. The 04-30 meeting ranked "HVG on training set only" as "Foundational" because of OOD leakage [D] (meeting_notes_2026-04-30.md).
- Notebook 11: stayed a design; the cell-count audit was never written [I].

## Problems in how it was done

- **Encoder leakage in IID.** The IID encoder file holds every cell (106,654), so about 80% of the evaluation cells were encoder training cells and the other ~20% sat in the test split used to pick the encoder checkpoint, for all three models [C] (nb09#c11; toggle_*_iid/scgen/config.yaml). In the CellOT paper's design the i.i.d. model sees only "the remaining holdout cells" [P] (CellOT, Methods "Setup"). The 04-08 log calls this "a slight advantage" for scGen only [D] (research_log_2026-04-08.txt:468-470), and notebook 10 states that the "Only difference is whether the model saw the other half of holdout cells during training" [D] (nb10#c0). This makes every IID number optimistic by an unknown amount [I].
- **Different latent spaces per mode.** IID and OOD use different encoders, so R² and MMD are computed in different coordinates [C] (impact/config.yaml `ae_emb`). The IID − OOD difference mixes transport learning with encoder change [I].
- **Unequal scoring of scGen.** scGen was scored by a notebook function on full clouds; the transports by evaluate.py on 10 subsamples [C] (nb10#c5; evaluate.py:194-204). This breaks the 04-08 rule against notebook metrics [D] (research_log_2026-04-08.txt:336-341).
- **n differs across runs.** Largest n ranges from 30 to 500, and T1 uses 80 for IMPACT but 100 for CellOT-ct [R]. The biased MMD has a floor that falls with n, so MMD comparisons across groups (and within T1) are unfair [C][I] (the later floor/ceiling work is in F10). The 03-30 meeting had flagged MMD sample-size sensitivity; it stayed open [D] (research_log_2026-04-08.txt:394).
- **CellOT-ct mixes two axes.** Its transport toggles species while its encoder toggles cell type; notebook 10 still plots and averages it beside IMPACT [C] (nb10#c13, #c16).
- **No anchor, one seed.** `--setting iid` was never run; splits use seed 0; training and evaluation subsampling are unseeded [C] [D] (conceptual_framework.md:490-513).
- **Unstratified 50/50 split.** Species counts in the evaluation half can drift [C] (conny@c342331:cellot/cellot_gpu/cellot/data/cell.py:339-340; mac:OptimalTransport/CellOT/cellot/cellot/data/cell.py:328-329). Indirect sign: M2's 506-cell evaluation half never reached n = 250 per side, so one species had fewer than 250 cells there [R][I].
- **Plots and tables call latent numbers gene expression.** Notebook 10's bar charts label the latent-space R² "R² (mean gene expression)" and "R² of Mean Gene Expression" [C] (nb10#c13), and 08.1 prints "R² of mean gene expression" for both families although renorm is latent [C] (08.1#c7, #c11). A reader of the figures would take them as gene-space results [I].
- **HVGs from all cells**, including the held-out ones, in toggle and renorm data [C] (nb09#c6; 01.3#c9); the paper uses the training set only [P] (CellOT, Methods).
- **Stale inputs.** All toggle data carry the mouse scaling and clip, and miss two donors [D][N] (see above).
- **Short training.** 50k iterations and batch 128 instead of 250k and 256 [C][P].
- **Renorm vs stale is confounded.** Normalisation, HVG method, donors (12,836 vs 12,990 matched cells) and evaluation space all changed at once [N] (nb09#c7; 01.3#c11) [C] (08.1#c1).
- **Docs contradict code or results.** (a) The 04-20 log §5 and the 04-21 slides say normalise after ortholog alignment; 01.3 normalised before it [D] (research_log_2026-04-20.txt:240-259; conny@c342331:logs/mentor_meetings/2026-04-21_mentor_meeting_slides.md §5) [C] (01.3#c3). The same log's §11 says the opposite of its §5 ("normalize-before-ortholog-align ... Done via 01.3") [D] (research_log_2026-04-20.txt:670-671). (b) The 04-20 log calls the stale space "14,451-dim"; the stale predictions are 1,000-d [D] (same file:644-646) [N] (josh@cellot:e18_confirming_cellot_identities.ipynb#c3). (c) conceptual_framework §5.6 says stale was latent and renorm was gene space; it is the reverse [D] (conceptual_framework.md:376) [C][R] (08.1#c1; imputed.h5ad sizes, see Setup). (d) §5.3 says `batch_key` "performs the normalization separately per species"; it only computes dispersion per species [D] (conceptual_framework.md:250) [C] (01.3#c3, #c9). (e) 08.1 calls the stale HVGs "human-only", and the 04-20 and 05-04 logs repeat it; notebooks 05 and 07 pooled both species [D] (08.1#c0; research_log_2026-04-20.txt:684-687; research_log_2026-05-04.txt:506-510) [C] (archive/05_expanded_training_CD8_holdout.ipynb#c7; archive/07_data_prep_all_holdouts.ipynb#c5). (f) The 05-04 log misstates the IID encoder file (see above). (g) §5.7 places the 509 + 509 M2 cells in notebook 09; notebook 09's M2 has 1,012 [D] (conceptual_framework.md:384) [N] (nb09#c11). (h) The 04-08 log says the switch to `--where latent_space` "aligns with the original CellOT paper's evaluation pipeline" [D] (research_log_2026-04-08.txt:249-251); the paper computes r² and ℓ2 on about 1,000 genes and MMD on 50 marker genes [P] (CellOT, Methods "Feature selection").
- **Colliding labels.** `swapped` means the cell-type data file but the species model directory (`swapped_cellot`) [C] (renorm_cd8/{swapped_cellot,normal_cellot}/config.yaml) [D] (01.3#c0, which warns about it). `cd8_thymo` means "CD8 and thymocytes held out" in T2 but "CD8 held out, thymocytes out of the AE" in renorm B [N] (nb09#c9; 01.3#c13). `IMPACT_CellOT` names the cell-type model in notebook 10's code but the species model everywhere else [C] (nb10#c1) [D] (conceptual_framework.md:117-143).
- **Stale artefacts.** Notebook 10's saved outputs predate its current code (the 05-10 label change) [G] (josh@f10f1cf); the 08.1 TSV exports were deleted [G] (conny@4200f8e).

## Terms used here

- **T1–T4, M1–M4**: the 8 toggle holdout groups (T = T-cell labels, M = monocyte labels), defined in nb09#c9.
- **toggle_ood**: CellOT's split that halves the held-out cells into a hidden half (`ignore` or `train`) and an evaluated half (`ood`).
- **mode (`iid`/`ood`)**: what the model trained on; part of the run name (`toggle_t1_iid`).
- **`--setting`**: which slice evaluate.py scores; always `ood` here.
- **IMPACT**: CellOT transport from mouse to human in the scGen latent space; on disk `impact`, `impact_or`, `speciesot_cellot`, `swapped_cellot`; later `IMPACT_CellOT`.
- **CellOT-ct**: this page's name for the cell-type framing (non-holdout → holdout cells, species held out); on disk `cellot` (toggle), `normal_cellot` (renorm), `speciesot_cellot_swapped` (stale).
- **`_holdout_swapped` file**: the matched file with condition = holdout type vs rest.
- **stale / renorm**: data built from the upstream `.X` (mismatched scales) / rebuilt from raw counts in 01.3.
- **Groups A–D**: the renorm re-runs of the earlier T-cell holdouts (F06).
- **Option X / Option Y**: normalise before / after ortholog alignment (research_log_2026-04-20.txt:254-259).
- **latent_space / data_space**: evaluate.py `--where`: compare 50-d codes / decoded genes.
- **`_v07`**: in April, the suffix for copies written to be readable by anndata 0.7 in the CellOT environment, not a data version (archive/07_data_prep_all_holdouts.ipynb#c13); the later hub treats `v07`/`v08` as dataset versions.
- **eval_re**: re-evaluation jobs with smaller `--n_cells`.
- **model-scgen**: symlink to `scgen/` that evaluate.py needs to find the encoder (conny:cellot/cellot_gpu/cellot/utils/evaluate.py:305; FASRC listing of toggle_t1_iid).

## What the package needs from this

Nothing here is worth reproducing as a scientific result: the IID numbers are leaky, the data are stale, CellOT-ct is abandoned, and the renorm deltas compare two spaces. Four pieces are useful as software checks, because inputs, models and outputs are all on FASRC:

1. **Toggle split (exact).** Input: fasrc:BK/cellot/cellot_gpu/datasets/speciesot-human-mouse/toggle_t1_holdout_v07.h5ad (or toggle_m2_...). Config: the `datasplit` block of toggle_t1_iid/impact/config.yaml (`key`, `holdout`, `mode`, `random_state: 0`, `test_size: 0.2`, `groupby: condition`, no stratify). Expected: an `ood` half of 195 cells (T1) or 506 (M2), identical in both modes [C][I]; the exact mouse cell IDs are the `obs` of toggle_t1_{iid,ood}/impact/evals_ood_latent_space/imputed.h5ad, which exist on FASRC (42,256 bytes each) [R] (`ls -l`; not opened). Tolerance: exact match. The split depends on obs order and on sklearn's `train_test_split`.
2. **scGen latent arithmetic (deterministic).** Inputs: toggle_{g}_{mode}/scgen/cache/model.pt and toggle_{g}_holdout_v07.h5ad; recipe in nb10#c5 (encoder 1000→256→256→50, eval mode; delta from all matched cells outside the holdout types (OOD) or outside the evaluation half (IID); full-cloud metrics). Expected: the 16 scGen rows of toggle_ood_all_results.csv, e.g. T1-OOD R² 0.644644, MMD 0.087178, l2_means 1.796072; M3-OOD 0.351794, 0.092512, 3.170725 [N]. Tolerance: no re-run exists; the computation has no randomness, so agreement to about 1e-4 should be expected [I].
3. **evaluate.py protocol on saved transports.** Inputs: toggle_m3_{ood,iid}/impact/cache/model.pt plus the matching scGen encoder; `--setting ood --where latent_space`, default n. Expected: mean r 0.8004 / 0.9075 (R² 0.6406 / 0.8236), MMD 0.0317 / 0.0243 at n = 500 [R]. Tolerance: the per-draw spread (sample standard deviation over the 10 draws) of r is 0.0051 / 0.0024 and of MMD 0.0007, so a 10-draw mean should land within about ±0.003 (r) and ±0.0005 (MMD) [R][I]. Only worth doing if the package wraps CellOT's ICNN.
4. **Renorm preprocessing counts.** 01.3 gives exact counts: 47,807 + 58,931 cells; 14,451 orthologs; 1,000 HVGs with 269 in both species; 6,495 + 6,495 matched; holdouts CD8 390, CD4 192, T subtypes 1,492; encoder files 104,738 / 103,283 / 101,283 / 104,738; post-normalisation maxima mouse 8.9909, human 9.1015 [N] (01.3#c3, #c9, #c11, #c15). Tolerance: exact, provided the ortholog table is the April one. The helper queries the live Ensembl BioMart with no version pin [C] (speciesot_helpers.py:906-970), so start from the saved files or pin a table. A cheap guard test: the upstream mouse `.X` has maximum exactly 10.0 and must never be used as input [N] (01.2#c4).

The current package metrics would not reproduce any number above. `R2Evaluation` averages the squared per-gene correlations computed across paired cells, and `MMDEvaluation` uses one bandwidth (0.1) [C] (josh@scgen-model-impl:src/speciesot/speciesot_core.py:305-337). The package needs the mean-vector r, the 50-bandwidth grid, subsampled draws, and an explicit rule for squaring: (mean r)² and mean(r²) differ by up to 0.0014 here [R]. The repo already uses both rules: notebook 10 reports T1-IID IMPACT as 0.866992 = (mean r)², the hub card as 0.867071 = mean(r²) [N][D] (toggle_ood_all_results.csv; conny:docs/experiments/gpu__toggle_t1_iid__impact.md) [R] (both re-derived from the evals.csv).

## Open questions

- What exactly was in the April library at `.../speciesOT/cellot/cellot`, which patch made it accept list holdouts between 00:35 and 01:25 on 04-09, and does its toggle split equal the vendored one?
- Does notebook 10's re-implemented split choose the same evaluation cells as evaluate.py? (Compare its cell IDs with the `imputed.h5ad` obs.)
- How many mouse and human cells are in each evaluation half?
- How much of the IID gain is encoder leakage? This needs an IID encoder trained without the evaluation half.
- The 8 IID encoders were trained on identical data [C] (nb09#c11; the IID files of T1, M2 and M3 have the same size, 447,654,126 bytes [R] (FASRC `ls -l`)); their loss curves (`cache/scalars`, not read here) could measure encoder run-to-run spread.
- Were the toggle results ever shown to Josh? The 04-21 slides do not mention them.
- Do the toggle files share the HVG list in which "0 of 16 standard immune markers" appear [D] (meeting_notes_2026-04-30.md)? Probably yes: notebooks 05, 07 and 09 ran the same `highly_variable_genes(flavor='seurat', n_top_genes=1000)` call on the same 106,654 cells [C] (archive/05_expanded_training_CD8_holdout.ipynb#c7; archive/07_data_prep_all_holdouts.ipynb#c5; nb09#c6) [I]; F06 reports the 0-of-16 result for that list. Comparing the `var` names of the files would settle it.
- Was "08.2" (renorm with vs without HVG leakage), planned on 04-30, ever run? Not found in conny's tracked files, the inventory, analysis/ or the FASRC mirror of results/.

## Sources

- conny:speciesOT/baseline/analysis/09_data_prep_toggle_experiments.ipynb (#c3, #c5, #c6, #c7, #c9, #c11, #c13)
- conny:speciesOT/baseline/analysis/10_iid_vs_ood_evaluation.ipynb (#c0–#c18)
- conny:speciesOT/baseline/analysis/toggle_ood_all_results.csv · conny:speciesOT/baseline/analysis/toggle_ood_iid_vs_ood_comparison.csv
- conny:speciesOT/baseline/analysis/08.1_renorm_vs_stale_comparison.ipynb (#c0–#c17)
- conny:speciesOT/baseline/analysis/01.2_pipeline_comparison.ipynb (#c0–#c23)
- conny:speciesOT/baseline/analysis/01.3_data_prep_all_holdouts_renorm.ipynb (#c0–#c23)
- conny:speciesOT/baseline/analysis/archive/01.1_hvg_investigation.ipynb (#c18–#c26)
- conny:speciesOT/baseline/analysis/archive/05_expanded_training_CD8_holdout.ipynb (#c7, #c13)
- conny:speciesOT/baseline/analysis/archive/07_data_prep_all_holdouts.ipynb (#c0, #c3, #c5, #c6, #c8, #c10, #c12, #c13)
- conny:speciesOT/baseline/analysis/archive/11_immune_cell_ontology.ipynb (#c0–#c15) · conny:speciesOT/baseline/analysis/immune_ontology_outputs/
- conny:speciesOT/baseline/analysis/meeting_notes_2026-04-30.md
- conny:logs/research_logs/research_log_2026-03-30.txt · research_log_2026-04-08.txt · research_log_2026-04-13.txt · research_log_2026-04-20.txt · research_log_2026-05-04.txt
- conny@c342331:logs/mentor_meetings/2026-04-21_mentor_meeting_slides.md · conny@c342331:autospeciesOT/results_renorm_vs_stale.tsv · conny@c342331:autospeciesOT/results_renorm_vs_stale_delta.tsv
- conny:docs/conceptual_framework.md (§1.2, §1.3, §2.1, §5.3–§5.8) · `conny:docs/concepts/OOD vs IID evaluation.md` · conny:docs/experiments/gpu__toggle_*.md · conny:docs/experiments/gpu___archive__toggle_cellot_subdirs__toggle_*__cellot.md · conny:docs/experiments/gpu__renorm_*.md · conny:AGENTS.md
- conny:cellot/cellot_gpu/cellot/data/cell.py · conny@c342331:cellot/cellot_gpu/cellot/data/cell.py · conny:cellot/cellot_gpu/scripts/evaluate.py · conny:cellot/cellot_gpu/cellot/utils/evaluate.py · conny:cellot/cellot_gpu/cellot/losses/mmd.py · conny:cellot/cellot_gpu/cellot/models/ae.py · conny:cellot/cellot_gpu/cellot/train/train.py · conny:cellot/cellot_gpu/cellot/train/summary.py · conny:cellot/cellot_gpu/scripts/train.py · conny:speciesOT/speciesot_helpers.py
- conny@17562ba (archive commit and REFACTOR_WALKTHROUGH_2026-05-24.md diff) · conny@4200f8e · conny@8a9a103 (cell.py `stratify` option) · conny:docs/archaeology/inventory.csv · conny:docs/archaeology/experiments/F06-tcell-holdouts-speciesot-v1.md
- josh@a1efc54, josh@f10f1cf (notebook 10 diff), josh@8a2d53a, josh@232b65e, josh@b9eff70 · josh@cellot:e18_confirming_cellot_identities.ipynb (#c3) · josh@cellot:scripts/generate_toggle_configs.py · josh@cellot:baseline/analysis/presentation_preparation.ipynb · josh@cellot:baseline/analysis/20_m1_mmd_investigation.ipynb · josh@scgen-model-impl:src/speciesot/speciesot_core.py
- fasrc:BK/cellot/cellot_gpu/results/toggle_*/{scgen,impact}/ (config.yaml, train_*/eval_*/eval_re_* logs, evals_ood_latent_space/evals.csv) · fasrc:BK/cellot/cellot_gpu/results/_archive/toggle_cellot_subdirs/toggle_*/cellot/ (same files)
- fasrc:BK/cellot/cellot_gpu/results/renorm_*/{scgen,swapped_cellot,normal_cellot}/ (config.yaml, logs, evals.csv) · fasrc:BK/cellot/cellot_gpu/results/speciesot_{cd8,cd8_nothymo,tcell_subtypes,cd4}/*/ (config.yaml, eval_ds_* logs, evals_ood_data_space/evals.csv) · fasrc:BK/cellot/cellot_gpu/results/eval_all_3691082.{out,err} · fasrc:BK/cellot/cellot_gpu/results/hvg_pearson_residuals_{m1_v08_ood,m2_v08_ood,m2_iid}/impact_cellot/config.yaml · fasrc:BK/cellot/cellot_gpu/results/hvg_seurat_a_iid/*/config.yaml
- fasrc:BK/sbatch/train/train_toggle_*.sbatch · fasrc:BK/sbatch/eval/eval_toggle_*.sbatch · fasrc:BK/sbatch/eval/eval_tcell_subtypes_impact.sbatch · fasrc:BK/sbatch/train/renorm/*.sbatch, submit_all_renorm.sh · fasrc:BK/sbatch/eval/renorm/*.sbatch
- fasrc:BK/docs/model_cards/gpu__toggle_t1_iid__impact.md
- FASRC listings (ls only): BK results/toggle_t1_iid/ (model-scgen symlink, cache/), BK datasets/speciesot-human-mouse/ (32 toggle files, dated 04-09 00:31) and speciesot-human-mouse-renorm/, file times of toggle_*/*/cache/model.pt, sizes of imputed.h5ad in toggle_*, speciesot_* and renorm_* runs, BK cellot/ (only cellot_gpu/ and sbatch/); /n/home01/jzhou1125/.conda/envs/CellOT/lib/python3.9/site-packages/cellot.egg-link
- conny:docs/experiments/gpu__toggle_t1_iid__impact.md · conny:docs/experiments/gpu__toggle_t1_iid__scgen.md (hub cards)
- mac:OptimalTransport/CellOT/cellot/cellot/data/cell.py · mac:OptimalTransport/CellOT/cellot/cellot/losses/mmd.py
- [P] CellOT paper text (Fig. 4a and 4f legends; Methods "Single-cell RNA sequencing data", "Setup", "Hyperparameters", "maximum mean discrepancy", "Feature selection") · [P] scGen paper (delta definition, as summarised in the archaeology brief)

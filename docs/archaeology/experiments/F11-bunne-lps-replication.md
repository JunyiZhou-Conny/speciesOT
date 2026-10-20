# F11 · Replicating the CellOT paper's cross-species LPS result (Bunne Fig. 4)

> The CellOT paper (Bunne et al. 2023, Fig. 4d–f) reports that CellOT predicts the response to LPS (a bacterial molecule that triggers inflammation) of a species never seen in training, rat or mouse, better than scGen, mainly through a lower MMD (a distance between two clouds of cells) [P]. In June 2026 Conny retrained both models with the paper's training settings on scGen's LPS training file cut to 1,000 genes, scored them with the authors' evaluation script, and on 06-22 compared the scores with the authors' per-species results file, `species.csv` [R][G]. Rat came out reversed (MMD on 50 marker genes: CellOT 0.273, scGen 0.256; `species.csv`: 0.234 and 0.265), and mouse kept the paper's order with a much smaller gap (0.206 vs 0.212; `species.csv`: 0.149 vs 0.236) [R]. CellOT's distance from the do-nothing baseline is almost the same as in `species.csv`, but our scGen is much stronger than theirs [I]. Each model was trained once, and the scored checkpoints are the ones the code's best-batch rule kept (rat CellOT from about step 16,750 of 250,000; rat scGen from step 165,000 of a run cancelled at 229,762) [R; I], so the record cannot say why the result differs; a log of 07-20 closed the topic as "NOT reproduced" [D], and we rate it partly worked.

| | |
|---|---|
| Period | 2026-06-12 14:53 (first Slurm job) → 2026-06-22 06:59 (notebook 24, conny@3ccd3d5) [R][G]. Before: the species × condition counts come from a data-inspection notebook first committed on 2026-05-15 as `explore_dataset.ipynb` (conny@c342331) and renamed `explore_LPS_dataset.ipynb` on 06-09 (conny@8a9a103); `inventory.csv` lists only the rename date [G]. After: decoded-frame files written 2026-07-20 13:12–13:34 (file times in RAT/, MOUSE/) [R]; closing log 07-20, committed 07-30 (conny@fe856aa) [D][G]; plotting script started on 2026-08-16 (its empty output folder is dated 14:47) [R; I] and committed 2026-08-18 (conny@abf75d2) [G]. |
| People | Junyi (Conny) Zhou: all commits and all 72 Slurm jobs (account `jzhou1125`) [G][R]. No trace of Joshua Price (searched the commit messages of the josh clone) [G]. The 07-20 log is headed "Mentor-facing synthesis" [D, LOG0720:2]. It refers to Cursor canvases and a Cursor skill [D, LOG0720:3-4], so it was probably written with an AI agent [I]. |
| Status | partly worked |
| Main code | PC/scripts/setup.py (configs) · PC/scripts/prep_data.py · PC/scripts/run_train_gpu.sh, run_eval.sh · CODE/scripts/evaluate.py, extended_metrics.py · AN/paper_crossspecies_fig4_helpers.py (+ NB23x, NB24) · AN/compare_paper_replication.py |
| Results live in | RAT/ and MOUSE/: `{scgen,impact_cellot}/config.yaml`, `cache/{model.pt,last.pt,status}`, `evals_{ood,iid}_data_space_paper/{evals.csv,imputed.h5ad}`, and for ood also `extended_metrics.csv`, `decoded_frame_metrics.csv`, `recon_identity.json` (all present in fasrc:BK, listed 2026-10-20) [R]; logs in LOGS/ and `RES/paper_crossspecies_pipeline_*`; AN/paper_crossspecies_fig4_outputs/ (`headline_metrics.csv`, `fig4f_bar_data.csv`, `extended_metrics_nc1000.csv`, `figures/`); SPC. |

Shorthands: `RES/` = fasrc:BK/cellot/cellot_gpu/results/ · `RAT/`, `MOUSE/` = RES/paper_crossspecies_rat_ood/, RES/paper_crossspecies_mouse_ood/ · `LOGS/` = RES/paper_crossspecies/_logs/pipeline/ · `DATA/` = fasrc:BK/cellot/cellot_gpu/datasets/scrna-crossspecies/ · `PC/` = conny:cellot/cellot_gpu/paper_crossspecies/ · `CODE/` = conny:cellot/cellot_gpu/ · `UP/` = mac:scGen v.s. CellOT/cellot/ (a clone of the authors' GitHub repository bunnech/cellot, HEAD 522d2b9 of 2024-11-01; cited at HEAD) · `AN/` = conny:speciesOT/baseline/analysis/ · `NB23x` = AN/23_paper_crossspecies_fig4_executed.ipynb · `NB24` = AN/24_species_csv.ipynb · `SPC` = ablation:species.csv (byte-identical to mac:scGen v.s. CellOT/species.csv, sha256 8c0347a9…) · `LOG13`, `LOG14`, `LOG0720` = conny:logs/research_logs/research_log_2026-06-13.txt, research_log_2026-06-14_gpu.txt, research_log_2026-07-20.txt · `SACCT` = Slurm accounting for `jzhou1125`, 2026-06-12 → 06-15, queried 2026-10-20 with a state filter (see Sources).

Out of scope: the March LPS runs → F05; scGen Fig. 5 reproduction and the 2×2 split ablation → F12; the autoresearch loop → F13.

## The question

What the paper reports, exactly:
- Task: train on the other species and test on rat (or mouse), "o.o.d." (out-of-distribution: the test species is never seen in training) [P, cellot.txt:681-688, caption :1244-1246]. Rat and mouse were chosen because only they "show consistent responses" across species [P, :2306-2308].
- Claim 1: "CellOT accurately reconstructs the innate immune response in both mouse and rat in the i.i.d. and o.o.d. setting", shown by marker-gene means (Fig. 4e) and by "the average correlation coefficient r2 computed between o.o.d. predictions and holdout observations across all genes (Fig. 4f)" [P, :689-697].
- Claim 2: "CellOT outperforms the baselines when analyzing how well each method captures the heterogeneity … as demonstrated by low levels of MMD (Fig. 4f)", plus matching marginals of bimodal marker genes for the rat holdout (Fig. 4g) [P, :697-703, :1249-1251].
- Fig. 4f shows bars for CellOT, scGen and cAE (a conditional autoencoder) for the mouse and rat holdouts, "mean ± s.d. across n = 10 bootstraps of the test set" [P, :1247-1249]. In the extracted figure text, tick columns 0–0.7 and 0–0.6 sit next to the label "r2 feature means" and 0–0.35 next to "MMD" [P, :1063-1094]. The paper text gives no numbers for this panel [P, searched].
- Methods: r² and ℓ2 of means "on the entire gene set, i.e., ~1,000 genes"; MMD on "the top 50 marker genes" from scanpy `rank_genes_groups` against untreated cells, reported as "an unbiased estimate" with RBF kernels averaged over `np.logspace(1, -3)` [P, :2046-2058]. All models are trained for 250k iterations [P, :1976-1977]; the OT maps use batch 256, 4 hidden layers of width 64, lr 1e-4 [P, :2004-2010]; autoencoder settings come from a grid search in Supplementary Table 1 [P, :2012-2014], which is not in the text available here. 1,000 HVGs are computed "on the training set only" "for all datasets" [P, :1947-1950], while the cross-species preprocessing was "inherited" from scGen [P, :1950-1953]. i.i.d. models see half of the holdout cells in training and are scored on the same held-out cells as o.o.d. models [P, :1957-1966; Fig. 4a caption :1238].
- The paper's baselines include `identity` (return the untreated cells unchanged) and `observed` (a second sample of real treated cells) [P, :225-230]; Fig. 4f does not show them [P].

Conny's question: "Replicate Fig. 4d–f MMD + r² on Hagai/scGen LPS dataset; compute MMD floor/ceiling (50 marker genes + 1000-gene r²) for rat and mouse OOD holdouts" [D, LOG13:3-5]. On 07-20 it was restated as "OT beat linear AE-shift under species OOD?" [D, LOG0720:10].

## Setup

### Data
- Input: scGen's training file `train_species.h5ad`, 62,114 cells × 6,619 one-to-one orthologs (genes with exactly one copy in each species); mouse, pig, rabbit, rat; only `unst` (unstimulated) and `LPS6` (6 h of LPS) [N, CODE/explore_LPS_dataset.ipynb#c3, #c6, #c7]. At that time the file was already named `hvg-top1k-train-only.h5ad` but held all 6,619 genes [N, #c3]. Rat has 8,421 `unst` and 9,423 `LPS6` cells, mouse 7,625 and 7,428 [N, #c6]; full table in F05. The prep input (`hvg-top1k-train-only.6619-backup.h5ad`) has the same sha256 as `train_species.h5ad` (26e42d9f…) [R, conny:offline_data_manifest.txt:5, :7]. The scGen paper's dataset has 77,642 cells [P, scgen.txt:1235]; the other 15,528 are scGen's validation file [D, conny:offline_bundle/README.md:14-15].
- The authors' processed data (the "ETH bundle", doi 10.3929/ethz-b-000609681) was "not used (auth required)" [D, LOG13:17]. A plan written on 06-19 says "Email sent" for the authors' exact file [D, ablation:scgen_bunne_ablation_plan.md:390]; no reply is recorded (not found in the conny or ablation repos).
- The authors' own task config names the treated condition `LPS` [C, UP/configs/tasks/crossspecies-ood.yaml:4]; that file last changed in the authors' commit 060f4a6 of 2023-02-16 [G]. The vendored copy says `LPS6` [C, CODE/configs/tasks/crossspecies-ood.yaml:4]. So the authors' file labels its treated cells differently from scGen's file; whether it holds the same 6-hour cells is not recorded [I].
- Prep (PC/scripts/prep_data.py): 1,000 highly variable genes (HVGs: genes with the largest cell-to-cell variance; scanpy flavor `seurat`) chosen from all 62,114 cells, both holdout species included [C, prep_data.py:88-96], although its docstring says "training pool only" [C, :7]. Then a Wilcoxon test of `LPS6` vs `unst` (`rank_genes_groups`, reference `unst`) on all cells ranks the genes; the ranks go to `varm['marker_genes-condition-rank']` and define the "top 50 marker genes" [C, :37-52, :98-100]. One file serves both holdouts, so neither holdout's genes are "train-only" [I].
- Output: 62,114 × 1,000 [D, LOG13:14; conny:offline_bundle/README.md:17] (the 1,000 genes also appear as `n_genes: 1000` in recon_identity.json [R]), sha256 90330ec1… (256,084,932 bytes; hash recorded 06-14) [R, conny:offline_data_manifest.txt:6]. The file is still at DATA/hvg-top1k-train-only.h5ad with that byte size [R, listing 2026-10-20; hash not re-checked].

### Split
- CellOT's `toggle_ood` with `key: species`, `holdout: rat` (or `mouse`), `mode: ood`, `groupby: [species, condition]`, `test_size: 500`, `random_state: 0`, `stratify: condition` [C, RAT/scgen/config.yaml, MOUSE/scgen/config.yaml].
- The holdout species is split 50/50, balanced by condition: one half (`ood`) is scored, the other half (`ignore`) is not used [C, CODE/cellot/data/cell.py:330-384]. For the other species, 500 cells per species × condition go to `test` (used to pick checkpoints); the rest is `train` [C, cell.py:267-290].
- Derived sizes [I, counts + code]: rat `ood` ≈ 4,210 `unst` + 4,712 `LPS6`; mouse `ood` ≈ 3,812 + 3,714; `test` = 1,500 `unst` + 1,500 `LPS6` from the three training species.
- `stratify` is Conny's addition to the vendored code [C, cell.py:340-345]. The upstream task config has no `stratify` and uses batch 128 [C, CODE/configs/tasks/crossspecies-ood.yaml; same in UP/].

### Models
- "scGen" here is the vendored CellOT model `scgen`: a plain autoencoder (a network that compresses each cell into a 50-number code and reconstructs it), 1,000 → 512 → 512 → 50 and back, β = 0 (no KL term, so not a VAE), dropout 0, Adam lr 1e-3, weight decay 1e-5, lr halved every 100k steps, batch 256, 250k steps [C, RAT/scgen/config.yaml; PC/scripts/setup.py:52-96]. It predicts by adding mean(`LPS6` codes) − mean(`unst` codes) of the training cells, with no cell-type balancing, and decoding [C, CODE/cellot/models/ae.py:175-187; CODE/cellot/transport.py:61-69]. This is not Lotfollahi's scGen VAE; the 07-20 log says the same [D, LOG0720:13, :28-29]. It is the model the authors' code calls `scgen` (UP/configs/models/scgen.yaml equals the vendored file apart from a `device` line) [C], so the comparison with SPC's `scgen` rows is like for like [I].
- "CellOT" (`impact_cellot` in the repo): two ICNNs (input-convex neural networks; the transport map is the gradient of one of them), hidden layers [64, 64, 64, 64], trained on the 50-number codes of that same autoencoder; Adam lr 1e-4 (β1 0.5, β2 0.9), weight penalty 1, 10 inner updates, batch 256, 250k steps [C, RAT/impact_cellot/config.yaml; setup.py:99-151]. This matches the paper [P, cellot.txt:2004-2010]. Predictions are decoded back to 1,000 genes [C, CODE/cellot/utils/evaluate.py:361-362].
- Which state is scored: training keeps `last.pt` (newest state) and `model.pt` (best score so far on one 256-cell `test` batch: latent MMD with six bandwidths every 250 steps for CellOT, reconstruction loss every 2,500 steps for the autoencoder) [C, CODE/cellot/train/train.py:58-85, :152-158, :233-240; CODE/cellot/losses/mmd.py:114-125]. Evaluation, and CellOT's encoder, load `model.pt` [C, CODE/cellot/utils/evaluate.py:340; CODE/cellot/data/cell.py:161-163]. This is upstream CellOT behaviour. So "250k steps" says how long training ran, not which state was scored.
- Only o.o.d. models were trained (every config has `mode: ood`) [C, setup.py:68, :117]. One run per model; no seed was varied [C, configs].

### Evaluation
- `evaluate.py --where data_space --n_markers 50 --n_cells 500,1000 --n_reps 10` (CellOT also with `--embedding ae`), run with `--setting ood` and `--setting iid` [C, PC/scripts/run_eval.sh:12-29]. In each of 10 repetitions it draws 500 or 1,000 real treated and predicted cells, without a seed, keeps the top-50 marker genes and computes [C, CODE/scripts/evaluate.py:62-87, :173-191]:
  - `r2-means`: Pearson r between per-gene means. It is not squared, despite its name [C, evaluate.py:73].
  - `mmd`: the biased MMD estimator (it includes each cell's similarity with itself, so it is above 0 even for identical distributions), RBF kernel averaged over 50 bandwidths `np.logspace(1, -3, 50)` [C, evaluate.py:63; CODE/cellot/losses/mmd.py:5-10]. The authors' code has the same function [C, UP/cellot/losses/mmd.py:5-10], although the paper says "unbiased" [P, cellot.txt:2046].
  - `l2-means`, and kNN enrichment: the share of a predicted cell's nearest neighbours that are also predicted cells; 0.5 means well mixed, 1.0 fully separated [C, CODE/cellot/utils/evaluate.py:16-47].
- `--setting ood` scores the holdout's `ood` half. `--setting iid` scores the `test` cells of the three training species: in-distribution cells, not the paper's i.i.d. setting [C, CODE/cellot/utils/evaluate.py:182-186, :214-224].
- CODE/scripts/extended_metrics.py (Conny's addition) works on the same 50 genes with a seeded generator: MMD floor (MMD between two disjoint random samples of the real treated cells, each of the evaluation size), MMD ceiling (the control cells used as the prediction, i.e. the identity baseline), `frac_gap_closed` = (ceiling − model) / (ceiling − floor), and squared r of means on all cells for the model, the identity baseline and two halves of the treated cells [C, extended_metrics.py:4-10, :129-168; CODE/cellot/losses/mmd.py:13-91]. Definitions: ../metrics.md §1–3.
- Notebook 23 adds r of means on all 1,000 genes (10 seeded samples of 1,000 cells) [C, AN/paper_crossspecies_fig4_helpers.py:92-109].

### Bunne's per-species file (`species.csv`)
- 1,260 rows: `metric` (`r2-means`, `l2-means`, `mmd`), `value`, `holdout` (pig, rabbit, rat, mouse), `mode` (iid, ood), `model` (cellot, scgen, cae, identity, random, popalign for pig only), `experiment` (`species-ood`); 10 values per group [R, SPC, counted here]. In CellOT's code `random` is a second half of the real treated cells, i.e. the paper's "observed" [C, CODE/cellot/utils/evaluate.py:246-271]. There is no column for the number of cells or for the gene set [R].
- Origin not recorded. The commit that first uses it says "found final results of Bunne paper" [G, conny@3ccd3d5]; the ablation repo calls it "Published metrics" [D, ablation:README.md:75]; the paper says "Source data are provided with this paper" [P, cellot.txt:2074-2075]. It entered git on 06-19 (ablation@efba789) [G]; the Mac copy has file time 2026-06-15 14:16 [R].

### Differences from the paper at a glance

| item | paper / authors' code | this replication |
|---|---|---|
| data | preprocessing "inherited from" scGen [P, cellot.txt:1950-1953]; authors' processed file [P, :2073-2074]; treated label `LPS` [C, UP/configs/tasks/crossspecies-ood.yaml:4] | scGen's training file only (62,114 cells), re-prepared; label `LPS6`; ETH file not used [N][D, LOG13:17] |
| genes | 1,000 HVGs from the training set only [P, :1947-1950] | 1,000 HVGs and marker ranks from all cells, holdouts included [C, prep_data.py:88-100] |
| split | `toggle_ood`, not stratified [C, UP/configs/tasks/crossspecies-ood.yaml] | stratified by condition [C, RAT/scgen/config.yaml] |
| batch | 256 for the OT maps [P, :2005]; autoencoder from Supplementary Table 1 [P, :2012-2014]; upstream task config 128 [C, same yaml] | 256 for both models [C] |
| steps | 250k for all models [P, :1976-1977]; upstream CellOT default 100k [C, CODE/configs/models/cellot.yaml; UP/ same] | 250k set; rat autoencoder stopped at 229,762; scored states from `model.pt` (see §2) [C][R] |
| i.i.d. | separate models that see half of the holdout [P, :1238, :1957-1966] | not trained; `iid` means training-species test cells [C] |
| repeats | 10 bootstraps of the test set [P, :1249]; training seeds not stated | 10 unseeded evaluation subsamples; one training run per model [C] |

## What was done and what came out

### 1. Data preparation (06-12)
- File times in DATA/: the 6,619-gene file is dated 14:51:02, the export files `_crossspecies_export.*` 15:03:21, and the final 1,000-gene file 15:03:28 [R, listing 2026-10-20]. A rename keeps the file time, so the 6,619-gene input was written at 14:51, and HVG selection and marker ranking ran between then and 14:57, when the first jobs tried to read the output [I].
- The first two training jobs that started (06-12 14:57–14:59) failed within about a minute: the old `anndata` of the `CellOT` env (0.7.6 [D, PC/GPU_UPGRADE.md:53]) could not read the file written in the `analysis` env (`KeyError: 'dict'`) [R, RES/paper_crossspecies/_logs/failed_jobs/train_21991310.err; SACCT]. At 15:03 the file was exported and re-saved through the CellOT env [R, file times; C, PC/scripts/export_for_cellot.py, import_for_cellot.py; D, LOG13:16]. `prep_data.py` as committed calls a helper `_import_crossspecies_cellot.py` that is in neither git nor fasrc:BK [C, prep_data.py:129; searched], so it does not run end to end [I].

### 2. Training and scoring: 72 Slurm jobs (14 started) plus one login-node run, 06-12 14:53 → 06-14 11:19

| when | job(s) | what happened | evidence |
|---|---|---|---|
| 06-12 14:53–15:07 | 48 jobs: the per-model chain (`pc_rat_*`, `pc_mouse_*`: train autoencoder, train CellOT, four evaluations, two extended-metric jobs per holdout) submitted three times | 46 cancelled before they started; the two autoencoder jobs of the second round failed reading the h5ad | [R] SACCT; failed_jobs/ |
| 06-12 ~15:09–15:18 | not a Slurm job: rat autoencoder on the login node | 0 → 2,500 steps in 9 min 12 s, then crashed when saving `model.pt` (`FileNotFoundError`: the cache folder no longer existed) | [R] LOGS/paper_crossspecies_train.log; [D] RES/paper_crossspecies/_logs/README.md |
| 06-12 15:19 → 06-14 00:22 | 21994633 `paper_lps_full` (CPU) | rat autoencoder ran 229,762 of 250,000 steps (1.37 steps/s at the end), then was cancelled | [R] SACCT; RES/paper_crossspecies_pipeline_21994633.err, last line |
| 06-13 13:58–15:12 | 5 queued follow-up jobs (`paper_lps_cont` ×2, `paper_lps_gpu`, `paper_lps_gpu_c` ×2) | all cancelled before they started (the last one, 22427476, at 06-14 01:25) | [R] SACCT |
| 06-14 00:36 → 01:25 | 22427475 `paper_lps_gpu` (submitted 06-13 15:12) | rat CellOT steps 0 → 46,789 on a GPU (V100 per PC/GPU_UPGRADE.md:31 [D]), cancelled | [R] SACCT; RES/paper_crossspecies_pipeline_gpu_22427475.{out,err} |
| 06-14 01:25 → 01:54 | 14 jobs: smoke tests and restarts on H100/H200 GPUs with a new env `CellOT_gpu` (torch 2.3.1) | six were cancelled before they started; one smoke test passed (1,000 CellOT steps in 72 s on an H200), after which a monitor script submitted two production restarts by itself; both failed on optimizer state left on the CPU; a restart and a resume test failed on a circular import; the resume tests set the production config to `n_iters: 46250` (LOG14:36 blames the first one), and the second ran 46,000 → 46,249 in the production folder before failing in its final log write; so the next two restarts declared rat CellOT finished at 46,250 and trained the mouse autoencoder (0 → 78,348, then 70,001 → 74,270) before being cancelled | [R] SACCT; LOGS/*.out, *.err; RES/paper_crossspecies/_logs/gpu_benchmark.json, monitor_smoke.log; [D] LOG14:6-36 |
| 06-14 01:55 → 06:41 | 22625950 `paper_lps_gpu` (H200), plus its continuation 22625962, which never started | rat CellOT 46,249 → 250,000 (2 h 08 min); mouse autoencoder 70,001 → 250,000 (6 min); mouse CellOT 0 → 250,000 (2 h 27 min); rat scGen scored; then `extended_metrics.py` crashed on a Python 3.10 type hint under Python 3.9; Slurm state FAILED | [R] SACCT; LOGS/paper_crossspecies_pipeline_gpu_22625950.{out,err} |
| 06-14 10:32 → 11:19 | 22771742 `paper_lps_eval` (CPU) | all 8 evaluations and 4 extended-metric files | [R] SACCT; LOGS/paper_crossspecies_eval_22771742.out |

In total 72 jobs: 2 completed, 8 failed, 62 cancelled (58 of them before they started) [R, SACCT].

The rat autoencoder's `cache/status` says `done`, but that file was written at 00:22:03, the same second as Slurm's cancel message, and holds 5 bytes (`done` plus a newline); `train.py` writes the 4-byte `done` and only after training ends [R, listing and bytes of RAT/scgen/cache/status; C, CODE/scripts/train.py:62-73]. So it was written by a command run together with the cancel, not by `train.py`, so that the GPU jobs would skip this model [I]; the GPU plan says "Mark rat scGen still `done` (already set)" [D, PC/GPU_UPGRADE.md:160]. The GPU jobs did skip it ("skip scgen … (status=done)") [R, LOGS/*.out].

Scored states. Each log's progress counter was dated from the job's end (cancel time minus final elapsed time, or end of training minus the bar's final elapsed time), then read at the time `model.pt` was written [R, file times and progress lines; I]:

| model | training that actually ran [R] | `model.pt` written [R] | scored step [R; I] |
|---|---|---|---|
| rat scGen | 0 → 229,762 (cancelled), CPU | 06-13 11:56:58 | 165,000: the line `165000/250000 [20:36:29` falls exactly on the file time (counter start 06-12 15:20:29 = 00:22:03 minus 33:01:34) |
| rat CellOT | 0 → 46,789 (V100); 46,000 → 46,249; 46,249 → 250,000 (H200) | 06-14 00:54:36, during the V100 run | about 16,750 (counter start 00:36:58 = 01:25:54 minus 48:56; at 17:37–17:38 elapsed it reads 16,741–16,769; scoring every 250 steps) |
| mouse scGen | 0 → 78,348; 70,001 → 74,270; 70,001 → 250,000 | 06-14 04:08:21 | about 187,500 (counter start ≈ 04:04:25 = 04:10:26 minus 06:01; at 03:56–03:57 it reads 186,955–187,871; scoring every 2,500 steps) |
| mouse CellOT | 0 → 250,000 | 06-14 06:27:58 | about 232,750 (counter start ≈ 04:10:46 = 06:38:05 minus 2:27:19; at 2:17:12–2:17:13 it reads 232,723–232,777) |

- For rat CellOT none of the ~233k later steps beat the early best batch score, which `train.py` restores on restart under the right key (`minmmd`), so the resumes did not change the scored model [R, file time; C, train.py:95, :154-158].
- The autoencoder saves its best score under the key `eval_loss` but reads `best_eval_loss` on restart, so after a restart the next evaluation always overwrites `model.pt` [C, train.py:210-214, :238]; the upstream code has the same bug [C, UP/cellot/train/train.py:205-206, :233]. The warning appears for the mouse autoencoder [R, LOGS/paper_crossspecies_pipeline_gpu_22624912.err, …22625950.err]. Mouse scGen's `model.pt` is therefore the best state after step 70,001 only [I]; the rat autoencoder never restarted [R].
- LOG13 says "Training COMPLETE (GPU job 22625950, ~4h47m): all 4 models status=done, 250k iters" [D, LOG13:25]. The time is right (4 h 46 min [R, SACCT]); "250k iters" is wrong for the rat autoencoder, and LOG14 calls the 46,000-step CellOT checkpoint a "CPU checkpoint" [D, LOG14:15], but it came from GPU job 22427475 ("Training impact_cellot … on cuda") [R].

### 3. Scores (06-14)

O.o.d., 1,000 cells, top-50 marker genes, mean ± SD over the 10 subsamples [R, RAT/{scgen,impact_cellot}/evals_ood_data_space_paper/evals.csv and MOUSE/…; same values in AN/paper_crossspecies_fig4_outputs/headline_metrics.csv and NB23x#c3]:

| holdout | model | r (`r2-means`) | MMD | ℓ2 of means | kNN enrichment |
|---|---|---|---|---|---|
| rat | scGen | 0.666 ± 0.003 | 0.256 ± 0.002 | 6.32 | 1.000 |
| rat | CellOT | 0.636 ± 0.003 | 0.273 ± 0.003 | 7.18 | 1.000 |
| mouse | scGen | 0.761 ± 0.002 | 0.212 ± 0.002 | 5.27 | 1.000 |
| mouse | CellOT | 0.674 ± 0.002 | 0.206 ± 0.002 | 5.97 | 1.000 |

- Enrichment 1.000: every predicted cell's nearest neighbours are predicted cells, so in these 50 genes neither model makes cells that mix with real treated cells [R; I].
- With 500 instead of 1,000 cells every o.o.d. MMD is 0.0014–0.0022 higher, as expected from the biased estimator [R, same files].

Next to `species.csv` (o.o.d.; SPC values are mean ± SD of its 10 rows) [R, SPC and files above]:

| holdout | model | r ours | r SPC | MMD ours | MMD SPC |
|---|---|---|---|---|---|
| rat | CellOT | 0.636 | 0.677 ± 0.002 | 0.273 | 0.234 ± 0.006 |
| rat | scGen | 0.666 | 0.694 ± 0.003 | 0.256 | 0.265 ± 0.004 |
| rat | cAE | — | 0.638 ± 0.003 | — | 0.363 ± 0.004 |
| rat | identity | 0.763 † | 0.798 ± 0.005 | 0.291 ‡ | 0.253 ± 0.004 |
| rat | observed | 0.9999 † | 0.998 | 0.0014 ‡ | 0.0061 |
| mouse | CellOT | 0.674 | 0.576 ± 0.007 | 0.206 | 0.149 ± 0.002 |
| mouse | scGen | 0.761 | 0.550 ± 0.004 | 0.212 | 0.236 ± 0.003 |
| mouse | cAE | — | 0.476 ± 0.003 | — | 0.357 ± 0.006 |
| mouse | identity | 0.585 † | 0.723 ± 0.007 | 0.296 ‡ | 0.213 ± 0.004 |
| mouse | observed | 0.9996 † | 0.997 | 0.0015 ‡ | 0.0062 |

† square root of `r2_identity` / `r2_self` in extended_metrics.csv (50 genes, all cells, not subsampled). ‡ `mmd_ceiling` / `mmd_floor` at 1,000 cells [R].

- Rat: CellOT − scGen MMD is +0.017 in ours (CellOT 6.6% worse) and −0.031 in SPC (11.5% better). Mouse: −0.006 (2.7%) in ours and −0.087 (36.9%) in SPC [R, computed from the tables].
- r: scGen is ahead in both of our holdouts (50 genes); in SPC (gene set not recorded) scGen is ahead for rat and CellOT for mouse [R].
- In SPC, `identity` (doing nothing) has a higher r and a lower ℓ2 of means than every model in all four held-out species (rat ℓ2: identity 8.80, scGen 10.72, CellOT 10.99) [R, SPC]. Only on MMD do models beat it: CellOT in all four species, scGen only for pig (0.196 vs 0.234) [R, SPC]. CellOT has the lowest o.o.d. MMD in all four species [R, SPC].

Floor and ceiling on our side (extended_metrics.csv; MMD at 1,000 cells, r² on all cells; 50 genes) [R, RAT/*/evals_ood_data_space_paper/extended_metrics.csv, MOUSE/…]:

| holdout | model | model MMD | floor | ceiling | `frac_gap_closed` | r² model | r² identity |
|---|---|---|---|---|---|---|---|
| rat | scGen | 0.2554 | 0.0014 | 0.2915 | 0.124 | 0.442 | 0.582 |
| rat | CellOT | 0.2716 | 0.0014 | 0.2915 | 0.068 | 0.404 | 0.582 |
| mouse | scGen | 0.2132 | 0.0015 | 0.2962 | 0.282 | 0.580 | 0.343 |
| mouse | CellOT | 0.2054 | 0.0015 | 0.2962 | 0.308 | 0.455 | 0.343 |

- Both models beat doing nothing on MMD but close only 7–31% of the gap to the floor [R]. For rat, doing nothing has the higher mean correlation [R].
- The same fraction computed from SPC (identity as ceiling, observed as floor) [I, computed from R]: rat CellOT 0.075, scGen −0.049; mouse CellOT 0.309, scGen −0.113 (rabbit 0.054 and −0.510; pig 0.209 and 0.167). CellOT's fraction is almost the same in both sources (0.068 vs 0.075; 0.308 vs 0.309). The difference is scGen: in SPC it is worse than doing nothing for rat, mouse and rabbit; in ours it is better [I].

r of means on all 1,000 genes (NB23x#c3; 10 seeded samples of 1,000 cells; SD ≤ 0.0015) [N; R, headline_metrics.csv]: rat CellOT 0.793, scGen 0.714; mouse CellOT 0.898, scGen 0.700. On this metric, the one the paper names, CellOT leads in both holdouts, the opposite of the 50-gene r [N]. No identity baseline was computed on all genes (not found). The helper calls the loader with `embedding=None`, which gives gene-space output for CellOT only if the `model-cellot` link exists [C, CODE/cellot/utils/evaluate.py:292-295; helpers.py:101]. The `model-cellot` links date from 06-14 11:53:41 (rat) and 11:54:24 (mouse); the `model-scgen` links from setup on 06-12 15:09 [R, listing of RAT/, MOUSE/]. The `model-cellot` links are made by later cells of the same notebook [C, helpers.py:152-166]. The 06-22 re-run, with the links in place, printed identical numbers [G], so the saved values are gene space [I].

`--setting iid` (1,000 cells, 50 genes) [R, evals_iid_data_space_paper/evals.csv] next to SPC's i.i.d. rows [R]: rat scGen r 0.972, MMD 0.043 (SPC 0.916, 0.162); rat CellOT 0.992, 0.009 (SPC 0.995, 0.017); mouse scGen 0.979, 0.035 (SPC 0.909, 0.096); mouse CellOT 0.992, 0.008 (SPC 0.990, 0.026). These are not the same experiment: ours scores the o.o.d.-trained models on held-in cells of the training species; SPC's i.i.d. models saw half of the holdout species [C; P]. They only show that CellOT fits the training species more closely than scGen [R].

### 4. Notebook 23 figures (06-14; re-run 06-22)
- NB23x#c6: Fig. 4f replica, r on all genes on top and MMD on 50 genes below [N, figures/fig4f_ood_bars.png].
- NB23x#c8: Fig. 4e replica. Only 5 of the paper's 9 Fig. 4e genes are in our top 50 markers: Oasl1, Sdc4, Ch25h, Acsl1, Slc7a2; Nfkbia, Tnfaip6, Mmp12 and Cxcl5 are not [N, figures/fig4e_{rat,mouse}_ood.png; C, helpers.py:190-210; P, cellot.txt:1179-1187]. A code comment adds that Nfkbia and Mmp12 are not even among the 1,000 HVGs [D, PC/scripts/plot_fig4_replica.py:47]. Read from the PNGs (approximate): in rat, real treated means are about 2.1 (Oasl1), 2.7 (Sdc4) and 2.0 (Ch25h); CellOT predicts about 0.6, 0.9 and 0.3, scGen about 0.3, 0.3 and 0.05. In mouse, CellOT overshoots the same three genes (about 2.1–2.4 against 0.4–1.8 real), and both models miss Acsl1 and Slc7a2 (about 1.7 and 2.2 real, ≤ 0.45 predicted) [N, visual reading].
- NB23x#c10: Fig. 4g replica (Oasl1, Sdc4, Acsl1, Slc7a2). For rat, CellOT's Oasl1 and Sdc4 distributions sit near the control cells, far from the treated cells [N, figures/fig4g_rat_impact_cellot_marginals.png, visual reading].
- No i.i.d. rows: no i.i.d. models existed [C, setup.py:68, :117; D, PC/scripts/plot_fig4_replica.py:189-190].
- All seven figure outputs differ between conny@39232f8 (06-15) and conny@3ccd3d5 (06-22), the kernel name ("Python 3" → "cellot") and Python version (3.9.23 → 3.9.25) changed, and every printed number stayed the same [G]; the notebook was re-run [I].

### 5. `species.csv` and the comparison (06-15 → 06-22)
- NB24#c0 prints the mouse o.o.d. block of SPC, although its comment says "rat OOD block": CellOT MMD 0.149 ± 0.002, scGen 0.236 ± 0.003, cAE 0.357; r 0.576, 0.550, 0.476 [N, NB24#c0].
- AN/compare_paper_replication.py (06-22) lines up SPC with our numbers and lists differences: input data (ETH vs re-prep), HVGs on all cells, re-ranked marker genes, `stratify`, CellOT 250k steps vs the repo default 100k, batch 256 vs 128, unseeded evaluation [C, :88-141]. It assumes SPC's r is the 50-gene slice ("likely stores…") [C, :12-14] and compares SPC's i.i.d. rows with our `iid` rows [C, :186-191]. It also hard-codes an "eyeball" reading of the published figure for rat CellOT, "r²≈0.65, MMD≈0.22" [D, :228]. Its printout was not saved (not found). Its next steps (the ETH data, one rat run with the original config, re-scoring the authors' predictions, diffing cell barcodes) [C, :148-155] have no runs in RES/ [R, folder listing].
- The same commit adds to conny:docs/conceptual_framework.md an argument that the Bunne-style strict holdout is the right benchmark for a frozen model, and points to the scGen-vs-CellOT ablation [D, conny@3ccd3d5] → F12.

### 6. Decoded frame and the closing synthesis (07-20)
- On 07-20, `decoded_frame_metrics.csv` and `recon_identity.json` were written next to each o.o.d. evaluation [R, file times]; only interactive Jupyter jobs were running that day, so they were computed interactively [I, SACCT]. The decoded frame uses all 1,000 genes; its floor is MMD(decode(encode(treated)), treated) and its ceiling MMD(decode(encode(control)), treated) [C, CODE/scripts/decoded_frame_metrics.py:1-17, :110-138].

| holdout | model | MMD, all genes | AE floor | decoded ceiling | `frac_gap_closed_decoded` | r² vs decoded treated |
|---|---|---|---|---|---|---|
| rat | scGen | 0.225 | 0.142 | 0.257 | 0.277 | 0.814 |
| rat | CellOT | 0.247 | 0.142 | 0.257 | 0.091 | 0.740 |
| mouse | scGen | 0.212 | 0.153 | 0.250 | 0.394 | 0.942 |
| mouse | CellOT | 0.218 | 0.153 | 0.250 | 0.336 | 0.859 |

[R, RAT/*/evals_ood_data_space_paper/decoded_frame_metrics.csv, MOUSE/…, 1,000 cells]
- The autoencoder rebuilds held-out treated cells poorly: `recon_target_r2_pergene` is 0.061 (rat `LPS6`, 9,423 cells) and 0.093 (mouse `LPS6`, 7,428), against `recon_train_r2_pergene` 0.285 and 0.257 on 10,000 sampled training cells [R, recon_identity.json]. The script that wrote these JSON files is not in git (not found), so the exact definition is not checked. LOG0720 quotes "train≈0.26–0.28, target≈0.06–0.09" [D, LOG0720:26], which these files confirm.
- Here the decoded denominator (ceiling − AE floor) is 0.115 (rat) and 0.097 (mouse) [R]. The "~0.02–0.05" quoted for "the LPS cut" in conny:AGENTS.md matches the "Hagai LPS rat-LPS6 holdout" row (0.022) of conny:docs/conceptual_framework.md:634, i.e. the scGen-split runs of F12/F15, not these runs [D; I].
- LOG0720 concludes: "Paper rat OOD: CellOT MMD < scGen; ours: FLIPPED"; "Decoded north-star: AE-scGen ≥ CellOT on rat and mouse"; "Bunne OT-wins-MMD story: NOT reproduced" [D, LOG0720:31-34, :52]. All three agree with the files above [R]. The canvas it names, `bunne-fig4-crossspecies-metrics` [D, LOG0720:3], was not found (searched the conny and ablation repos, the fasrc mirror and the Mac's Cursor canvas folders).

### 7. Afterwards
- 07-21: plan D (unbalanced OT) took `paper_crossspecies_rat_ood` as its frozen starting point [D, conny:logs/research_logs/agent_plans_2026-07-21/DELIVERABLE_D_option_a.md:11-18] → F14.
- 08-16/08-18: PC/scripts/plot_fig4_replica.py was committed on 08-18 inside an unrelated BCG commit [G, conny@abf75d2]. It plots SPC next to our 50-gene r and MMD [C, :198-247]. Its output folder `figures_paperstyle/` exists in fasrc:BK/speciesOT/baseline/analysis/paper_crossspecies_fig4_outputs/, dated 2026-08-16 14:47, but is empty; `fig4f_paper_vs_ours.csv` was not found [R, listing].

## Verdict
- Status "partly worked": the runs and the scoring finished for both holdouts and the mouse MMD order matched the paper; the rat order and the size of the mouse gap did not [R].
- Reproduced: CellOT's own standing. On 50-gene MMD it closes about the same share of the identity-to-observed gap as in the authors' file (rat 0.068 vs 0.075, mouse 0.308 vs 0.309) [R; I]. In-distribution, CellOT fits more closely than scGen [R].
- Not reproduced: CellOT beating scGen on MMD for rat (reversed by 0.017), and the size of its lead for mouse (0.006 instead of 0.087) [R]. Most of the difference lies in the baseline: our scGen beats doing nothing, theirs does not [I].
- Not supported, in either source: the mean-correlation part of claim 1. Doing nothing has a higher mean correlation than both models for rat in our runs (50 genes), and than every model in all four species in SPC (gene set not recorded) [R; I]. Fig. 4f leaves the identity baseline out [P].
- Ranking depends on the metric: 50-gene r and ℓ2 favour scGen in both holdouts; all-gene r favours CellOT in both; 50-gene MMD splits by holdout; the decoded frame favours scGen in both [R; N].
- Strength: weak. The numbers are well recorded, but there is one training run per model; the scored checkpoints were chosen by a one-batch rule, and the rat CellOT one is very early (about step 16,750); the rat autoencoder stopped at 229,762; and data (even the treated label), gene selection and split differ from the authors'. None of these factors was varied, so this family cannot say whether the paper's result is fragile or whether the replication is off [I].

## Why it stopped
Stated reason: "Our Bunne replication is partial + ranking-unstable … Stop chasing ETH lockstep / global Fig.4 fidelity as infinite game", and in the "Stop (infinite games)" list: "Exact ETH Fig.4 lockstep (we don't even recover the trend)" [D, LOG0720:31-34, :40-45]. A plan of 07-21 repeats the decision and returns the work to the human–mouse atlas [D, conny:logs/research_logs/agent_plans_2026-07-21/PLAN_A_atlas_memory_pack.md:16]. The record suggests [I]: from 06-19 the effort moved to the scGen side, first the Fig. 5 reproduction and split ablation (F12), then the autoencoder studies of the autoresearch loop (F13, from 06-22) [D, ../timeline.md:99-108]; no runs of the follow-up steps listed on 06-22 were found.

## Problems in how it was done
- **Scored checkpoints are early ones, picked by a noisy rule.** `model.pt` keeps the best score on one 256-cell batch of training-species cells [C, train.py:152-158, :233-240]. The scored rat CellOT state is from about step 16,750 of 250,000, and the rat scGen state from step 165,000 of a run that was cancelled at 229,762 and marked `done` outside `train.py` [R; I]. This is upstream behaviour, so "trained for 250k iterations" never meant "scored at 250k" [C; I], but no record shows that anyone checked which step was scored [I]. LOG13's "250k iters" is wrong for the rat autoencoder [D, LOG13:25].
- **One run per model.** The ± values come only from re-sampling the evaluation cells, not from retraining [C]. A 0.017 or 0.006 MMD difference cannot be judged against training noise.
- **`iid` is mislabelled.** The `iid` numbers are o.o.d. models on held-in training-species cells, yet the headline table and the comparison script line them up with SPC's i.i.d. rows [C, compare_paper_replication.py:186-191; AN/…/headline_metrics.csv]. The `iid` rows of headline_metrics.csv also carry the o.o.d. floor, ceiling and `frac_gap_closed`, because the helper reads the extended metrics from the ood folder only [R; C, helpers.py:71-75, :127-146].
- **Inputs differ from the paper's.** scGen's training file instead of the authors' ETH data, whose config even labels the treated cells `LPS` rather than `LPS6`; HVGs and marker genes picked on all cells including the holdouts, while the paper picks HVGs on training cells only; split stratified by condition; batch 256 for the autoencoder too, where the upstream task config has 128 [C; D; P]. Any of these could move the result; none was tested. Picking genes with the held-out species' cells also makes the test slightly easier, for both models [I].
- **Which r matches the paper is inconsistent.** The paper says all genes; notebook 23 uses all genes; the comparison script, plot_fig4_replica.py and the ablation plan use the 50-gene r [C; D, ablation:scgen_bunne_ablation_plan.md:96]. SPC does not say. The CellOT-vs-scGen order flips between the two [R; N].
- **Hidden dependency in the all-gene r.** With `embedding=None`, CellOT's value silently comes out in the 50-number code space when the `model-cellot` link is missing [C, CODE/cellot/utils/evaluate.py:292-295, :205-212; D, conny:docs/conceptual_framework.md:368].
- **Unseeded evaluation.** `evaluate.py` subsamples without a seed [C, CODE/scripts/evaluate.py:189-190]. The first scoring of rat scGen (r 0.6636, MMD 0.2570 [D, LOG13:32]) was overwritten by a second (0.6658, 0.2561 [R]).
- **Resumes across hardware and versions.** The rat CellOT run spans a V100 job (presumably the old `CellOT` env with torch 1.11, the only one that ran on V100s then [D, PC/GPU_UPGRADE.md:6, :31; I]) and H200 jobs with torch 2.3.1, a 250-step test run in the production folder, and an overwritten `n_iters` [R; D, LOG14:36]. The scored rat CellOT state comes from the V100 job alone, so this does not touch the reported numbers [R; I], but the run cannot be repeated exactly.
- **Autoencoder best-loss key bug** (`eval_loss` saved, `best_eval_loss` read; also upstream): after a restart, `model.pt` means "best since the restart" [C, train.py:210-214, :238]. This affects mouse scGen (restarted at 70,001), not rat [R].
- **Docs contradict the record.** LOG13:25 says all models ran 250k [D]; LOG14:15 says "CPU checkpoint" [D]; LOG14:24 calls job 22623309 "PASSED" [D], while Slurm says FAILED (logger flush) [R, SACCT; LOGS/smoke_resume_22623309.err]; PC/scripts/run_train_gpu.sh:3 says "rat scGen finished on CPU" [C]; NB24#c0's comment says rat but the cell prints mouse [N]; prep_data.py's docstring says "training pool only" [C, :7]. See §2 for what the records show.
- **Files changed after the runs.** RAT/impact_cellot/config.yaml was rewritten on 06-22 06:01:58, the same second as RES/paper_crossspecies/_logs/README.md and several sbatch files [R, file times]; its content matches setup.py except `device: cuda` [C]. What rewrote it is not recorded.
- **Code and outputs missing.** `prep_data.py` calls a helper that does not exist [C, :129]; the comparison printout, the plot_fig4_replica.py outputs, the first `evals.csv` and the 07-20 canvas were not found.
- **MMD details.** The estimator is biased (the paper says unbiased), and absolute values depend on the number of cells (0.0014–0.0022 lower at 1,000 than at 500 cells) [C; R]. Both sides use the same function, so rankings are comparable [C, UP/cellot/losses/mmd.py:5-10]. The upstream `evaluate.py` computes MMD only below 1,000 features, the vendored one up to 1,000 [C, UP/scripts/evaluate.py:75; CODE/scripts/evaluate.py:78]; this does not affect the 50-gene numbers.
- **Paper reporting.** Fig. 4f omits `identity`, which in SPC has the best r and ℓ2 in all four o.o.d. species and beats scGen on MMD in three of them [R, SPC]. Shown without it, the bars overstate both models [I].

## Terms used here
- `impact_cellot` / IMPACT_CellOT: the repo's name for CellOT trained in the autoencoder's 50-number code; "CellOT" on this page.
- `scgen` (here): CellOT's plain autoencoder plus one mean shift in code space; not the scGen VAE.
- `toggle_ood`, `ood`, `ignore`: CellOT's split. The holdout species is halved; `ood` is the scored half, `ignore` the unused half.
- `--setting iid` (this family): scoring on the `test` cells of the training species, not the paper's i.i.d.
- `n_markers 50` / `nfeatures=50`: the top 50 genes by Wilcoxon rank for `LPS6` vs `unst`, all cells.
- `LPS6`, `LPS`: treated-condition labels; `LPS6` (6 h of LPS) in scGen's file, `LPS` in the authors' config.
- `r2-means`: unsquared Pearson r of gene means. The `r2_*` columns of the extended and decoded files are squared.
- `mmd_floor`, `mmd_ceiling`, `frac_gap_closed`, `frac_r2_closed`: see Evaluation and ../metrics.md §3.
- decoded frame, `frac_gap_closed_decoded`: scores against the autoencoder's reconstruction of the control and treated cells. The repo docs call it the `north-star`, meaning the one headline number they rank by.
- `model.pt`, `last.pt`, `cache/status`: best-batch checkpoint, newest checkpoint, and the text file the scripts check to skip finished trainings.
- `identity`, `random` (= observed), `cae`, `popalign`: baselines in SPC.
- ETH bundle: the authors' processed data, doi 10.3929/ethz-b-000609681 [P, cellot.txt:2074; D, LOG13:17].
- `paper_lps_*`, `pc_*`: Slurm job names of this family.
- "infinite game": LOG0720's phrase for work with no end condition.

## What the package needs from this
Retraining does not make a good reference test here (one run per model, early checkpoints chosen by a noisy rule, no recorded spread). Two evaluation-level tests do, plus an optional data check:

1. **Identity baseline on the fixed split (no model).**
   - Inputs: DATA/hvg-top1k-train-only.h5ad (62,114 × 1,000; 256,084,932 bytes, the size in the manifest; sha256 90330ec1… per conny:offline_data_manifest.txt:6) [R]. The `offline_bundle/` links in fasrc:BK point into the deleted working tree, and the Mac folder `~/speciesOT_offline_20260614` is empty [R, listings 2026-10-20].
   - Config: `toggle_ood`, holdout rat or mouse, `mode: ood`, `groupby: [species, condition]`, `test_size: 500`, `random_state: 0`, `stratify: condition`; control = holdout `ood` `unst`, treated = holdout `ood` `LPS6`; genes = the first 50 of `varm['marker_genes-condition-rank']['LPS6']` sorted ascending.
   - Expected [R, extended_metrics.csv]: squared r of means on the 50 genes, all cells: rat 0.58241, mouse 0.34262. MMD ceiling (biased, 50 bandwidths, 1,000 + 1,000 cells, 10 reps, `numpy.random.default_rng(0)`): rat 0.29146, mouse 0.29617; floor 0.00144 and 0.00153. At 500 cells: ceiling 0.29269 and 0.29912, floor 0.00280 and 0.00293.
   - Tolerance: the r² involves no randomness, so it should match to float precision. An exact MMD match also needs the loader's row order and the script's draw order (a fresh `default_rng(0)` per quantity, 500-cell draws before 1,000-cell draws) [C, CODE/cellot/losses/mmd.py:56-89; extended_metrics.py:133-138]. Otherwise there is no rerun record; the 10-rep SDs of the model MMD (≈0.002) suggest ±0.003 [I].
2. **Re-scoring the saved predictions.**
   - Inputs: test 1's inputs plus `imputed.h5ad` in RAT/{scgen,impact_cellot}/evals_ood_data_space_paper/ and MOUSE/… (written by job 22771742; present in fasrc:BK) [R].
   - Expected: squared r of means on the 50 genes, all cells (no randomness): rat scGen 0.44232, CellOT 0.40352; mouse scGen 0.58024, CellOT 0.45502 [R, extended_metrics.csv]. Subsampled r and MMD at 1,000 cells: the table in §3 [R]. All-gene r with pandas `sample(1000, random_state=0…9)`: rat CellOT 0.79290, scGen 0.71449; mouse CellOT 0.89810, scGen 0.70036 [N; R].
   - Tolerance: exact for the full-cloud r² and the seeded all-gene r. ±0.005 for subsampled r and MMD: the two scorings of the same rat scGen model differ by 0.0022 (r) and 0.0009 (MMD) [D, LOG13:32 vs R], and the 10-rep SDs are 0.0017–0.0027 [R].
3. **Data preparation (optional, cheap).**
   - Inputs: the 6,619-gene file, DATA/hvg-top1k-train-only.6619-backup.h5ad (sha256 26e42d9f…, the same bytes as `train_species.h5ad`) [R, conny:offline_data_manifest.txt:5, :7; listing].
   - Config: scanpy `highly_variable_genes(flavor="seurat", n_top_genes=1000)` on all cells, then `rank_genes_groups(groupby="condition", reference="unst", method="wilcoxon")` [C, PC/scripts/prep_data.py:37-52, :88-100].
   - Expected: the gene list and `LPS6` rank order of `hvg-top1k-train-only.h5ad` (not extracted here). Spot check: of the paper's nine Fig. 4e genes, exactly Oasl1, Sdc4, Ch25h, Acsl1 and Slc7a2 are in the top 50 [N, NB23x#c8; C, helpers.py:190-210].
   - Tolerance: exact with the same scanpy version; the prep was meant to run in the `analysis` env (scanpy 1.12) [D, PC/README.md "Quick start"; PC/scripts/prep_data.py:10]. Ties may change with other versions [I].
- To get these numbers the package must use the biased MMD with 50 bandwidths, not the single-bandwidth `MMDEvaluation` [D, ../metrics.md:99]; name r and r² separately; store the gene set and the number of cells; seed the subsampling; record which checkpoint step is scored; and report `identity` and `observed` next to every model.
- SPC is an external reference only: different data, split and gene selection, and no record of cell numbers or gene set.

## Open questions
- Where did SPC come from (Nature source data, the ETH bundle, or elsewhere), and which number of cells and which gene set does each metric use? Its `random` MMD (≈0.006) is what our floor would be at about 250 cells (it halves from 500 to 1,000 cells) [I]. Fewer cells would raise both models' MMD by a similar amount (roughly 0.004–0.007 here), so the cell number cannot reverse the rat order [I].
- Is Fig. 4f drawn from SPC? SPC's o.o.d. values are near the axis ranges (rat cAE MMD 0.363 is just above the top tick label 0.35), and the hard-coded eyeball reading for rat CellOT (r ≈ 0.65, MMD ≈ 0.22) is close to SPC (0.677, 0.234) [D; I]; nothing states it.
- Would scoring rat CellOT's `last.pt` (the final state, saved at the end of training [R, file time 04:04:01]) instead of the `model.pt` from about step 16,750 change the rat order? Not tried.
- Why is the authors' scGen worse than doing nothing on MMD in three of four species, while ours is better (batch size, data file, checkpoint)?
- Which cells does the authors' file hold under the label `LPS`: the same 6-hour cells as scGen's `LPS6`?
- How large is the run-to-run spread of these trainings?
- Did the authors answer the email, and does their exact file exist somewhere?

## Sources
Paper: /tmp/sot-arch/papers/cellot.txt (baselines :222-232; Fig. 4 text :673-703; Fig. 4 caption :1234-1251; figure labels :1027-1030, :1063-1094, :1179-1187; Methods :1942-2075; Extended Data Fig. 4 :2302-2310) [P]; /tmp/sot-arch/papers/scgen.txt:1230-1235 [P].
conny: PC/README.md · PC/GPU_UPGRADE.md · PC/env.sh · PC/specs/rat_ood.yaml, mouse_ood.yaml · PC/scripts/{setup.py, prep_data.py, export_for_cellot.py, import_for_cellot.py, run_train.sh, run_train_gpu.sh, run_eval.sh, submit_gpu_remainder.sh, monitor_smoke_and_submit.sh, collect_results.py, plot_fig4_replica.py} · conny:cellot/cellot_gpu/explore_LPS_dataset.ipynb#c0-c22 (and its 05-15 version via conny@c342331) · CODE/scripts/{evaluate.py, extended_metrics.py, decoded_frame_metrics.py, train.py, plot.py} · CODE/cellot/{utils/evaluate.py, utils/helpers.py, data/cell.py, losses/mmd.py, train/train.py, train/summary.py, models/ae.py, transport.py} · CODE/configs/tasks/{crossspecies-ood.yaml, crossspecies.yaml} · CODE/configs/models/{cellot.yaml, scgen.yaml} · AN/23_paper_crossspecies_fig4.ipynb#c0-c12 · NB23x#c0-c12 (versions conny@39232f8 and conny@3ccd3d5) · NB24#c0 · AN/paper_crossspecies_fig4_helpers.py · AN/compare_paper_replication.py · AN/paper_crossspecies_fig4_outputs/{headline_metrics.csv, fig4f_bar_data.csv, extended_metrics_nc1000.csv, figures/fig4f_ood_bars.png, fig4e_rat_ood.png, fig4e_mouse_ood.png, fig4g_rat_impact_cellot_marginals.png} · LOG13 · LOG14 · LOG0720 · conny:logs/research_logs/research_log_2026-06-09.txt · conny:logs/research_logs/agent_plans_2026-07-21/{DELIVERABLE_D_option_a.md, PLAN_A_atlas_memory_pack.md} · conny:docs/conceptual_framework.md (incl. :368, :634), docs/scgen_bunne_ablation_plan.md, docs/local_offline_handoff.md (via the conny@3ccd3d5 diff and git grep) · conny:offline_bundle/README.md · conny:offline_data_manifest.txt · conny:AGENTS.md · conny:.cursor/skills/metric-atlas-canvas/reference.md · conny:docs/archaeology/{inventory.csv, timeline.md, metrics.md, sources.md, experiments/F05-first-cellot-runs-on-lps.md}.
git: conny@c342331, conny@8a9a103, conny@af7a2c7, conny@39232f8, conny@3ccd3d5, conny@fe856aa, conny@abf75d2 · ablation@efba789 (blame of scgen_bunne_ablation_plan.md) · josh clone: commit messages searched; josh@junyi holds the same bundle (file list only).
ablation: species.csv · README.md · scgen_bunne_ablation_plan.md. mac: scGen v.s. CellOT/species.csv (identical to SPC), scGen v.s. CellOT/ (listing); UP/ (git HEAD 522d2b9): configs/tasks/{crossspecies-ood.yaml, crossspecies.yaml}, configs/models/{scgen,cellot,cae}.yaml, scripts/evaluate.py, scripts/submit/ (listing: no cross-species script), cellot/losses/mmd.py, cellot/train/train.py, git log; `~/speciesOT_offline_20260614` (empty); `~/.cursor/projects/*/canvases` (searched).
fasrc (mirror): RAT/ and MOUSE/ {scgen,impact_cellot}/config.yaml, evals_{ood,iid}_data_space_paper/evals.csv, extended_metrics.csv, decoded_frame_metrics.csv, recon_identity.json · RES/paper_crossspecies/_logs/{README.md, gpu_benchmark.json, monitor_smoke.log, monitor_nohup.out, failed_jobs/train_2199131{0,9}.err} · LOGS/*.out, *.err (all except 22625950.err), including LOGS/paper_crossspecies_train.log · RES/paper_crossspecies_pipeline_21994633.out, paper_crossspecies_pipeline_gpu_22427475.{out,err} · fasrc:BK/cellot/cellot_gpu/paper_crossspecies/sbatch/*.sbatch · fasrc:BK/offline_data_manifest.txt · fasrc:BK/logs/research_logs/ (searched).
fasrc (read directly on 2026-10-20, not in the mirror): listings with times of RAT/, MOUSE/ (incl. `cache/`, `evals_*`, the `model-*` links), DATA/, fasrc:BK/offline_bundle/tier1_crossspecies/, fasrc:BK/speciesOT/baseline/analysis/paper_crossspecies_fig4_outputs/; the bytes of both rat `status` files; the last bytes and the progress lines around 20:36 of RES/paper_crossspecies_pipeline_21994633.err; final-elapsed and progress lines of LOGS/paper_crossspecies_pipeline_gpu_22625950.err; SACCT. SACCT note: a plain time-window query returns only 20 of the 72 jobs, because it leaves out jobs that waited on a dependency and never became eligible; adding `-s CA,F,CD,TO,NF,OOM,PD,R` returns all 72 (`sacct -j 22625962` confirms one of the missing ones). Windows 06-21→06-23, 07-19→07-21 and 08-15→08-19 were also checked. Not opened: `.pt` and `.h5ad` files.
Leads checked: the MMD and r values [R, evals.csv], the 07-20 quotes [D, LOG0720] and the r-vs-r² note [C, evaluate.py:73] are correct. Corrections: the job count is 72 (2 completed, 8 failed, 62 cancelled), not 20; the authors' mouse values (0.149 vs 0.236) are in NB24#c0 and SPC, not in NB23x; "published" means SPC, since the paper prints no numbers; mouse CellOT r is 0.674 (not 0.673) and lives under MOUSE/, not RAT/; the "IID 0.972 vs 0.992" pair is not the paper's i.i.d. setting.

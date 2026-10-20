# F13 · The autoresearch loop: LPS autoencoder sweeps and the ICNN ladder

> The question was which single setting (data split, gene count or one autoencoder knob) changes how well CellOT's PyTorch "scGen" autoencoder (AE) predicts LPS-stimulated rat cells from unstimulated ones, and later whether the AE helps at all. From 2026-06-22 to 2026-07-18 Conny and a Cursor coding agent ran 338 logged experiments (318 finished), 144 linear-model rows and one neural optimal-transport (ICNN) run [R] through `scgen-cellot-autoresearch`, a cluster harness modelled on karpathy/autoresearch, scoring each by the fraction of the MMD gap between unstimulated and stimulated cells that it closes; its autonomous parts were barely used [R]. A plain mean shift in gene space with no AE (`raw_shift`) closed +0.17 to +0.38 of the gap, while the default AE (50-dimensional latent) never beat it and scored below zero (worse than doing nothing) everywhere except at 250 and 500 genes under the `scgen` split [R]. A much wider, slower-trained AE only matched `raw_shift` at 2,000 genes, and the one ICNN run did worse than a mean shift on the same latent space [R]. Status: partly worked; the result about the default AE is consistent across hundreds of runs, but there is one random draw of the out-of-distribution split, mostly unseeded training, and only 1 of 7 planned ICNN runs [R].

| | |
|---|---|
| Period | 2026-06-22 08:05 (first commit, autoresearch@096518f) → 2026-07-18 15:52 (last job, LOGS/monitor_g6619_r3.log:24) [G][R]. The last commit, autoresearch@5d1a7d9, was pushed to GitHub on 2026-07-29 (GitHub API `pushed_at` 2026-07-29 20:35 UTC) [G]. |
| People | Junyi (Conny) Zhou: all 7 commits, 6 with an emory.edu address and 1 made on a FASRC node (autoresearch@170e916) [G]. A Cursor coding agent wrote most of the journal and the meeting slides: INS:131 is an "AUTONOMOUS SESSION LOG (user away ~2h)", and MD/PLAN_A_results_analysis.md:3 begins "For the agent executing this plan" [D]. Conny chose the direction inside those sessions: RECON:123 titles the identity test "the one you asked for" [D]. David Alvarez-Melis (Harvard SEAS, optimal-transport expert) proposed the MMD floor/ceiling idea and was the audience of the 2026-06-25 slides (MD/PLAN_B_mmd_questions.md:3-8) [D]. Joshua Price has no commit in this repo and is not mentioned in any of its files (git log; text search of AR) [G][R]. |
| Status | partly worked |
| Main code | autoresearch:run_one_experiment.py · autoresearch:honest_metrics.py · autoresearch:proposer.py and director.py · autoresearch:gen_genecount_sweep.py · autoresearch:ae_study/ (controlled_latent_sweep.py, optimization_sweep.py, linear_baselines.py, icnn_ot_sweep.py) · ABL/scripts/02_prepare_data.py, 02b_prepare_hvg_arms.py, cellot_predict.py |
| Results live in | EXP (338 rows × 33 columns) · RUNS/ (337 folders: metrics.json in 309, error.txt in 19, cache/model.pt in 299) · INS · AES/*.csv · AR/results/icnn_ot/640eead2b9c2/metrics.json · MD/ · LOGS (the only copy of 9 deleted 6,619-gene runs, section 8) [R] |

Citation shorthands: AR = fasrc:BK/scgen-cellot-autoresearch · EXP = AR/results/experiments.csv, cited by file line (line 1 is the header) · INS = AR/results/insights.md · RUNS = AR/results/runs · LOGS = AR/results/logs · AES = AR/ae_study/results · PLAN = AR/ae_study/PLAN.md · RECON = AR/ae_study/PLAN_recon_diagnostics.md · MD = AR/meeting_david · ABL = fasrc:BK/scgen-cellot-ablation. The Python, YAML and Markdown code files on FASRC are byte-identical to autoresearch@5d1a7d9. The differences: README.md and .gitignore are the 06-22 versions, the result files differ, and BK's `slurm/` folder is empty, so the 18 tracked Slurm scripts exist only in git (`cmp` of every tracked file against the mirror; `ls -la` and `md5sum` on FASRC) [G][C]. `adaptations.yaml` is untracked and exists only on FASRC, so it is cited as AR/adaptations.yaml. Other code is cited as `autoresearch:<path>`. A bare file name such as `honest_metrics.py:66` means the file in `autoresearch:`; ablation files always carry `ABL/`.

## The question

- **Planned (06-22).** "Decompose the scGen↔CellOT cross-species gap into causal levers (split, gene space, model knobs), each conditioned on the split, with confidence." The deliverable was `results/intuitions.md` (autoresearch:program.md:5-9) [D]. The rules: change exactly one setting per experiment, never generalize across data splits, keep the lab's fairshare near 0.5 (cheap CPU partitions, capped concurrency), reflect after every tier, and tune infrastructure but never the science (program.md:21-30) [D]. The planned ranking metric was `r2_all` under the `scgen` split and `r_50` under `bunne_ood` (autoresearch:search_space.yaml:26-32; priorities.md:87-96) [C][D]; the MMD scores of Setup replaced it from the evening of 06-22 (section 2).
- **First targets.** Reproduce the four Mac "Stage 1" arms A–D (see F12) on the cluster within ε = 0.02 (autoresearch:search_space.yaml:23; baselines.yaml:5-78) [C]. Then run a fixed ladder of one-change tiers: latent size, width, VAE, the Fig. 5 recipe and split seed (search_space.yaml:5-13, 72-115) [C].
- **Shift on 06-23.** Once the metric issues were found (Findings 3 and 4 below), the question became whether the AE helps at all compared with no AE (INS:95-129; autoresearch:space.yaml:102-115) [D].
- **July (`ae_study/`).** Why does the AE reconstruct cells so badly? And does a better AE, or a nonlinear OT map, beat the mean shift (PLAN:8-17; RECON:12-17) [D]?
- **Background.** An earlier autoresearch-style orchestrator was discussed on 2026-03-30 for the atlas task. It was a different, now-deleted tool (conny:logs/research_logs/research_log_2026-03-30.txt:213-230; conny:docs/conceptual_framework.md:895) [D].

## Setup

**Data.** The input is the scGen LPS file `train_species.h5ad`: 62,114 cells × 6,619 one-to-one orthologs (asserted at ABL/scripts/02_prepare_data.py:135) [C]. The paper reports 77,642 cells (scgen.txt:1235) [P]; the rest are probably in the separate `valid_species.h5ad` (fasrc:BK/offline_data_manifest.txt:8) [I]. The cells are mononuclear phagocytes (immune cells, such as macrophages, that engulf microbes) from mouse, rat, rabbit and pig (scgen.txt:894-895) [P]. The task is always rat `unst` (unstimulated) → rat `LPS6` (6 h of LPS, a bacterial cell-wall molecule that triggers an immune response) (autoresearch:run_one_experiment.py:145-150) [C]. There are two splits (ABL/scripts/02_prepare_data.py:45-64) [C]:

| split | training cells | evaluation: source → target cells |
|---|---|---|
| `scgen` | everything except rat LPS6: 52,691 cells, rat unst included | all 8,421 rat unst → all 9,423 rat LPS6 |
| `bunne_ood` | no rat cells: 44,270 cells. The rat cells are split 50/50 within each condition (random_state 0); one half is the evaluation set, the other half is unused | 4,210 rat unst → 4,712 rat LPS6 |

Counts: ABL/data/manifests/split_summary.json and AES/pca_ceiling.csv [R]. Gene spaces: all 6,619 orthologs (arms A and C), or the top 250 / 500 / 1,000 / 2,000 / 4,000 highly variable genes (HVGs: genes whose expression varies most across cells). The HVGs use scanpy flavor `seurat` and are chosen on all cells except rat LPS6 (02_prepare_data.py:112-122; ABL/scripts/02b_prepare_hvg_arms.py:48-63) [C]. Arms: A = scgen/6619, B = scgen/1k, C = bunne_ood/6619, D = bunne_ood/1k, and `G{N}_{split}` for the other gene counts (run_one_experiment.py:34-64) [C]. Two non-standard details. First, under `bunne_ood` the HVG choice still sees rat unst cells, including the evaluation inputs. Second, the marker genes behind `r_50` are ranked using cells that include the held-out rat LPS6 targets (02_prepare_data.py:32-42, 146; run_one_experiment.py:274-282) [C].

**Prediction methods.**

| name | what it does | code |
|---|---|---|
| `transport_scgen` (called "scGen" in this repo) | CellOT's `AutoEncoder`: hidden layers [512, 512], latent 50, β = 0, Adam (lr 1e-3, weight decay 1e-5), batch 256. Predict decode(encode(source) + Δ), where Δ = mean code of LPS6 − mean code of unst over *all* training cells of all species, with no cell-type balancing | run_one_experiment.py:103-176; ABL/scripts/cellot_predict.py:36-66 |
| β > 0 | the same network with a VAE head: the code is sampled, and the loss is MSE + β·KL | ABL/cellot/cellot/models/ae.py:158-198 |
| `fig5_arithmetic` | the scGen paper's Fig. 5 latent blend on the same AE (4 runs) | cellot_predict.py:68-102 |
| `raw_shift` | no AE: source cells + (mean LPS6 − mean unst) over the training cells, in gene space | run_one_experiment.py:245-256 |
| `pca_arith` | PCA with L components fitted on the training pool, plus the same mean shift in PCA space (a linear AE) | autoresearch:ae_study/linear_baselines.py:51-82 |
| `gaussian_ot` | PCA(K), then the closed-form Gaussian (Bures) OT map, which matches the mean and covariance of the two clouds; covariance shrinkage 0.1 | autoresearch:ae_study/linear_baselines.py:43, 85-111 |
| ICNN-OT | CellOT's input-convex networks: 4 × 64 hidden, lr 1e-4, batch 256, 250k iterations, 10 inner iterations, seed 0, trained on frozen AE codes | autoresearch:ae_study/icnn_ot_sweep.py:420-466; conny:specs/lps_icnn_ae_study.yaml:14-21 |

None of these is the scGen paper's VAE [C]. The ICNN settings match the CellOT paper (cellot.txt:2004-2006) [P]. The AE runs mostly used 50k iterations, not the 250k of the CellOT paper ("All models are trained for 250k iterations", cellot.txt:1976-1977) [P] and of CellOT's `scgen` config (conny:cellot/cellot_gpu/configs/models/scgen.yaml:22) [C]. The switch to 50k came from AR/adaptations.yaml:17-34 [C].

**Evaluation.** All metrics are in gene space unless stated otherwise (autoresearch:honest_metrics.py):
- `r2_all` is the squared Pearson r between the mean predicted and mean true expression over all genes. `r_50` is the unsquared r over the top-50 markers (run_one_experiment.py:270-293) [C]. Both compare means only.
- MMD (maximum mean discrepancy, a distance between two clouds of cells) uses the biased RBF-kernel estimator, averaged over 50 bandwidths `logspace(1, -3)`. It draws 30, 50 and 80 cells per side, 10 times each, from a numpy generator seeded with `split_seed`. The headline uses n = 80 (honest_metrics.py:42-43, 66-128; run_one_experiment.py:323-330) [C].
- `frac_gap_closed` (the raw frame; "raw fgc" below) = (ceiling − model)/(ceiling − floor). Here model = MMD(prediction, target), ceiling = MMD(source, target), which is "do nothing", and floor = MMD between two disjoint random draws of n target cells (honest_metrics.py:94-112, 178-185, 252-263) [C]. A value of 1 is perfect, 0 is no better than doing nothing, and below 0 is worse.
- `frac_gap_closed_decoded` uses the same model MMD, but floor = MMD(decode(encode(target)), target) and ceiling = MMD(decode(encode(source)), target) (honest_metrics.py:291-305) [C]. The repo calls it the `north-star`: the one score the loop was told to maximize (space.yaml:18-27) [C]. It is undefined for `raw_shift`.
- `frac_r2_closed` = (r²_model − r²_identity)/(r²_self − r²_identity) on the means (honest_metrics.py:271-282) [C]. `mean_js` is the mean per-gene Jensen–Shannon divergence on 50-bin histograms; lower is better (honest_metrics.py:132-155) [C].

Fixed values on the evaluation cells (RUNS/6e099eb43516_scgen_1k, 19362ebf748a_bunne_ood_1k, 95c11f9e113d_scgen_6619, ec74ad5e8c4f_bunne_ood_6619 metrics.json) [R]:

| evaluation set | raw floor | raw ceiling | closable gap | r² of "do nothing" |
|---|---|---|---|---|
| scgen, 1k | 0.0206 | 0.1278 | 0.107 | 0.660 |
| bunne_ood, 1k | 0.0203 | 0.1256 | 0.105 | 0.658 |
| scgen, 6,619 | 0.0238 | 0.0453 | 0.021 | 0.867 |
| bunne_ood, 6,619 | 0.0237 | 0.0450 | 0.021 | 0.866 |

At 6,619 genes the closable gap is five times smaller. So the same excess MMD gives a raw score about five times more negative there than at 1k [I].

**Which score is compared.** The repo-wide rule tells agents to rank on the decoded score and to ignore raw `frac_gap_closed` (conny:AGENTS.md:26, 38) [D]. This family's own documents instead use the raw frame when comparing an AE with no AE. The decoded score does not exist for `raw_shift`, and the raw frame charges the AE for its reconstruction error (INS:97-100; PLAN:40-42) [D]. This page follows the family's choice.

**Seeds.** `split_seed` is 0 in all 338 rows (EXP) [R]. Seeding never changed the split, because the out-of-distribution split hard-codes random_state 0 (autoresearch:AUTONOMOUS_DESIGN.md:259-261; space.yaml:147-149) [D][C]. 277 of the 327 run folders that still hold a config set no training seed. The other 50 used `training_seed` 0, and no other training seed was ever used (RUNS/*/experiment.json) [R].

## What was done and what came out

### Overview by tier

A tier is the label in EXP's `tier` column for one batch of runs. "AE raw" is `frac_gap_closed` over the AE-based runs of the tier [R].

| tier label(s) | dates | rows ok / error | what varied | AE raw, best → worst | EXP lines |
|---|---|---|---|---|---|
| tier0_smoke | 06-22 | 4 / 0 | arms A–D, 5k iterations | −0.167 → −9.996 | 2-5 |
| full_baseline_250k | 06-22 → 06-23 | 4 / 2 | arms A–D, 250k iterations | −0.034 → −9.222 | 6-7, 33-34, 60, 64 |
| gpu_validation2, 3 | 06-23 | 1 / 1 | GPU check on B, 4k iterations | −0.127 | 10-11 |
| auto_explore | 06-23 | 23 / 0 | 21 one-change runs on arm A at 50k, plus `raw_shift` on A and C | −4.603 → −7.252 | 8-9, 12-32 |
| auto_explore_xbase | 06-23 | 60 / 0 | the A changes without the two `n_iters` runs, plus `raw_shift`: 20 runs on each of B, C and D | +0.121 → −17.192 | 35-96 (not 60, 64) |
| auto_genecount | 06-26 | 96 / 0 | 6 gene counts × 2 splits × 8 configs | +0.236 → −12.822 | 97-192 |
| latent_sweep | 07-08 | 70 / 14 | latent 1 → 4,096 with hidden = max(512, 2 × latent); G = 2,000 and 6,619; both splits | −0.836 → −36.561 | 193-276 |
| identity_ceiling, controlled_latent_sweep(_seed0), optimization_smoke, optimization_sweep_seed0, architecture_probe_seed0 | 07-10 | 46 / 3 | 2,000 genes, scgen split: lr, latent 50 → 2,000, 5 training recipes, one shallow net | +0.283 → −4.502 | 277-325 |
| *_g6619 (3 tiers) | 07-17 → 07-18 | 14 / 0 | the same at 6,619 genes, width 13,238 (a first attempt of 07-14 with width 4,000 was deleted from EXP; section 8) | −0.006 → −3.879 | 326-339 |

In total: 338 rows, 318 ok and 20 errors, under 17 tier labels; 317 `transport_scgen` rows, 17 `raw_shift` and 4 `fig5_arithmetic`; 79.3 h of summed wall time (EXP) [R]. The 2026-07-29 README says "338 experiments — 318 completed and 20 failed … across 12 tiers … 79.3 hours" (autoresearch:README.md:16-18) [D]. All of this matches EXP except "12 tiers" [R]. None of the planned ladder tiers (tier1_paired_*, tier2a–2d, tier4_paired_seed) appears in EXP [R]. The declared budget was 200 experiments in total (search_space.yaml:17; space.yaml:176) [C]; EXP holds 338 rows [R]. Job logs: 387 `.out` files in LOGS, the largest groups being ar-genecount 96, ar-latsweep 84, ar-overnight 62, ar-optgrid 30, ar-gpufront 21 and ar-lat-g6619 16 [R].

### 1. 2026-06-22: harness, smoke test, CPU baselines

- The design (autoresearch:AGENT_PLAN.md:38-49): a loop `autoresearch.py` runs WORK → WAIT → TRIAGE → REFLECT → DECIDE for each tier, then SYNTHESIZE writes `intuitions.md`. Jobs were to be CPU-only on `serial_requeue`, at most 8 at once, because "GPU eats fairshare 200-500x faster than CPU" (fairshare = FASRC's priority score, which drops as a lab uses more compute) (autoresearch:cluster.yaml:11-35) [D][C].
- `tier0_smoke` failed once on a directory-permission error (LOGS/ar-tier0_smoke_24154783_0.err) [R], then ran 4 arms at 5k iterations with `r2_all` 0.651–0.822 (EXP:2-5) [R].
- The 250k baselines on CPU: D finished after 10.8 h and B after 12.0 h (EXP:6-7, wall_sec) [R]. A and C were cancelled on 06-23 at 17:02 after 20 h, at 75,864 (A) and 77,184 (C) of 250,000 iterations, about 1 iteration per second (LOGS/ar-full250k_24168208_0.err, _2.err) [R]. Two earlier submissions failed on a shell syntax error and on a YAML float-parsing error (LOGS/ar-full250k_24167932_0.err, ar-full250k_24168050_0.err) [R].

### 2. 2026-06-23: `honest metrics`, `raw_shift`, one director episode, GPU

The repo calls its MMD gap-closed metric set the `honest metrics` (honest_metrics.py:1-33) [C]. They were added to the runner and back-filled for the four smoke runs on 06-22 at 20:22, before the 250k runs started (LOGS/backfill.log and its file date) [R]. The agent's findings that day (INS:33-208) [D], checked against the result files:

| finding | claim (INS lines) | check |
|---|---|---|
| 1 | the 1k AE "saturates fast": decoded score 0.302 at 5k vs 0.286 at 250k (35-42) | numbers match EXP:2, 7 [R]. On the raw frame, B went −0.167 (5k) → −0.083 (50k, EXP:128) → −0.034 (250k) [R]. The rule "use 50k everywhere" followed (AR/adaptations.yaml:17-34) [C] |
| 2 | B vs D are "not rankable": `r2_all` 0.818 vs 0.621, decoded 0.286 vs 0.412, `frac_r2_closed` +0.466 vs −0.108 (44-65) | matches EXP:6-7 [R]. On the raw frame B beats D on both MMD (−0.034 vs −0.827) and R², so the "disagreement" exists only in the decoded score [R] |
| 3 | the decoded score is confounded across splits: D's decoded floor is 0.151 vs B's 0.048, because D's AE never saw rat cells, so a worse AE is rewarded (67-93) | the table's MMDs give back EXP:6-7's scores to three decimals (e.g. B: (0.1647 − 0.1314)/(0.1647 − 0.0484) = 0.286), and its raw floors and ceilings equal those in the `raw_shift` metrics.json files [R][I]. The AE model and decoded MMDs themselves survive in no result file, because both folders' metrics.json were later overwritten (Problems) [R] |
| 4 | `raw_shift` beats the AE on the raw frame: +0.338 vs −0.034 (B), +0.377 vs −0.827 (D) (95-129) | matches EXP:48, 90, 6-7 [R]. space.yaml:111-114 had predicted that `raw_shift` would lose under the `scgen` split; INS:114-115 notes that this was refuted [C][D] |
| 5 | the 6,619 AE also saturates (best checkpoint at steps 22,501 / 47,501) (200-208) | not checked: needs .pt files [D] |
| 6 | the AE is "net-harmful" at 6,619 genes: A −4.67, C −8.91 vs `raw_shift` +0.208 / +0.206 (170-198) | C: −8.914 in RUNS/89f0485c14bb_bunne_ood_6619/metrics.json, a run not listed in EXP [R]. A: no surviving file, because the CPU run folder 2f93b8153df3 is not in BK although its config is (AR/configs/generated/2f93b8153df3.json) [R]. Both AE numbers come from the CPU runs' checkpoints while they were still training ("converged-70k not official-250k", INS:172, 195) [D]; the finished GPU 250k runs later gave −5.134 (A) and −9.222 (C) (EXP:60, 64) [R]. `raw_shift`: EXP:8-9 [R] |
| 7 | "no AE hyperparameter rescues 6619": raw −4.6 to −7.3 (153-162) | EXP:12-32 range −4.603 to −7.252 [R] |

- **The one director episode.** At 11:32, `director.py` (rule reasoner) wrote a 4-item agenda: latent 64, width [256, 256], β 5e-6, dropout 0.1, all on arm A (AR/results/research_agenda.json; INS:24-31) [R]. Its "best" run was D's decoded 0.412, the cross-split number that Finding 3 calls confounded [R]. The proposer always perturbs baseline A, whatever the best run is (proposer.py:37-47, 128-200) [C]. Later, `explore.py` logged 21 proposals (AR/results/proposals.jsonl, 21 lines) [R]. These are all the untried one-change values around arm A in space.yaml:33-115 [I]. They ran as `auto_explore` (EXP:12-32) [R].
- **GPU.** During the "user away" session the agent added GPU support to the ablation copy of CellOT. It also put anndata 0.8.0 into a private `.gpu_libs` folder, then moved the 21 runs from CPU to any free GPU (21 jobs, ar-gpufront) [D][R]. Of the 9 CPU jobs that had started, 8 were cancelled at 17:33 after 9 to 10 minutes and 1 was preempted after 7 seconds (LOGS/ar-explore_24351767_*.err) [R]. INS:147-148 claims a "~70×" speed-up [D]. The two A/C 250k reruns on GPU took 10 min 46 s and 10 min 12 s (LOGS/ar-base250k_24384009_{0,1}.err) [R]. From then on, the CPU-only rule was not followed [I].
- **Overnight (23:26 → 23:56).** Twenty one-change runs were made on each of B, C and D at 50k (the A changes without the two `n_iters` runs, plus `raw_shift`), giving 60 runs (EXP, auto_explore_xbase) [R]. No script for this batch is in the repo; its configs exist only in AR/configs/generated/ [R]. Two baseline jobs (A and C at 250k, EXP:33-34) first failed on a logger `KeyError 'step'` and were rerun (INS:164-168 [D]; the traceback is in LOGS/ar-overnight_24383839_{0,1}.err [R]).

The four arms at 250k iterations, next to the Mac targets and `raw_shift`:

| arm | Mac Stage 1 `r2_all` | cluster `r2_all` | raw fgc | decoded fgc | `frac_r2_closed` | `raw_shift` raw fgc (`r2_all`) |
|---|---|---|---|---|---|---|
| A scgen/6619 | 0.897 | 0.882 | −5.134 | NaN | +0.118 | +0.208 (0.896) |
| B scgen/1k | 0.846 | 0.818 | −0.034 | +0.286 | +0.466 | +0.338 (0.810) |
| C OOD/6619 | 0.654 | 0.662 | −9.222 | +0.865 | −1.529 | +0.206 (0.901) |
| D OOD/1k | 0.669 | 0.621 | −0.827 | +0.412 | −0.108 | +0.377 (0.828) |

Sources: autoresearch:baselines.yaml:17-78 [C], equal to ablation:results/stage1/{A,B,C,D}/metrics.json [R]; EXP:60, 7, 64, 6 (AE) and EXP:8, 48, 9, 90 (`raw_shift`) [R].

### 3. 2026-06-25: slides for David

MD/ holds three slide decks, two plans written "for the agent executing this plan", five plot scripts and seven figures dated 06-25 (MD/figs/) [R]. The meeting date and David's answers were not found: no file in MD/, INS, conny:logs/research_logs/ or conny:docs/ (outside archaeology/) mentions David or Alvarez, and there is no research log between 06-14 and 07-20 (text search; file list). The decks tell the story so far: R² and MMD disagree; the floor/ceiling metric; the `AE tax` (the extra MMD caused only by passing cells through encode → decode); `raw_shift` beats the AE; and a list of questions (MD/slides_part0_journey.md:16-107; slides_part2_mmd.md:110-123) [D]. Most of their numbers match EXP, but these statements do not hold up:
- "A no-AE linear shift beats the scGen AE … at every gene count" (slides_part1_results.md:49-50; slides_part2_mmd.md:119) [D]. Only 1k and 6,619 genes had been run. Later, one AE at 250 genes (β 5e-5: +0.203 vs +0.169, EXP:99 vs 97) and ten wide AEs at 2,000 genes beat `raw_shift` [R].
- "VAE helps (1k)": β = 5e-5 raises the decoded score from about 0.29 to 0.64 (slides_part1_results.md:66-74) [D]. That gain is only in the decoded frame. The raw-frame model MMD is unchanged (0.1363 vs 0.1366, raw fgc −0.080 vs −0.083) while the decoded floor rises from 0.057 to 0.101 (RUNS/433044f47a93_scgen_1k vs e44a41f3180e_scgen_1000 metrics.json; EXP:43, 128) [R]. A worse reconstruction inflated the score [I].
- The slide table puts the raw ceiling for A and C at "~0.11" (slides_part2_mmd.md:54-55) [D]. The measured value is 0.045 (table in Setup) [R].
- The "MMD vs R² disagree" slide (B vs D) compares across splits with the confounded decoded score (row 2 in the findings table) [I].
- The AE scores for A and C, −4.67 and −8.91 (slides_part1_results.md:56-57; slides_part2_mmd.md:54-55) [D], are Finding 6's provisional CPU numbers. The finished 250k runs had already given −5.134 and −9.222 on the night of 06-23 (EXP:60, 64; run-file dates) [R].
- "The 3 failures were one operational bug" (slides_part1_results.md:35-37) [D]. Only two of them (EXP:33-34) show the logger `KeyError` (LOGS/ar-overnight_24383839_{0,1}.err). For the third (EXP:10, `gpu_validation2`) only "non-zero exit status 1" survives (RUNS/7c131e5aac30_scgen_1k/error.txt), and no job log exists [R].

One meeting file holds a result found nowhere else. MD/figs/arm_metrics_top50.csv scores the four 250k AEs on the top-50 marker genes only, as the CellOT paper does (cellot.txt:223) [P]: raw fgc +0.069 (A), +0.484 (B), +0.014 (C), +0.285 (D) (made by MD/plot_arm_metrics.py) [R][C]. On marker genes the AEs close part of the gap. `raw_shift` was never scored this way [I].

### 4. 2026-06-26: gene-count sweep (96 runs)

The 250 to 4,000-gene arms were built by ABL/scripts/02b_prepare_hvg_arms.py (job ar-buildhvg) [R]. Each (gene count, split) got the same 8 configs: the AE baseline (L 50), β 5e-5, β 5e-4, L 32, L 100, dropout 0.1, width [800, 800], and `raw_shift`, all at 50k iterations (autoresearch:gen_genecount_sweep.py:8-21) [C]. Raw fgc values, next to linear baselines run on 07-07 (EXP:97-192; AES/ae_study.csv) [R]:

| genes | split | `raw_shift` | AE, L 50 | best of the 7 AE configs | PCA L 50 + shift | best Gaussian OT (K) |
|---|---|---|---|---|---|---|
| 250 | scgen | +0.169 | +0.071 | +0.203 (β 5e-5) | −0.176 | +0.137 (200) |
| 500 | scgen | +0.274 | +0.120 | +0.236 ([800, 800]) | −0.099 | +0.027 (400) |
| 1,000 | scgen | +0.338 | −0.083 | +0.073 (L 100) | −0.238 | −0.077 (400) |
| 2,000 | scgen | +0.229 | −0.924 | −0.800 (L 100) | −0.888 | −0.670 (400) |
| 4,000 | scgen | +0.205 | −2.409 | −2.230 (L 100) | −2.028 | −2.010 (400) |
| 6,619 | scgen | +0.208 | −4.770 | −4.770 (L 50) | −3.837 | −4.099 (400) |
| 250 | OOD | +0.216 | −0.040 | +0.085 (β 5e-5) | −0.829 | **+0.457 (200)** |
| 500 | OOD | +0.318 | −0.496 | −0.272 (L 100) | −0.577 | +0.198 (400) |
| 1,000 | OOD | +0.377 | −0.925 | −0.653 (L 100) | −0.936 | +0.069 (400) |
| 2,000 | OOD | +0.280 | −2.251 | −2.109 (dropout 0.1) | −2.095 | −0.442 (400) |
| 4,000 | OOD | +0.233 | −5.187 | −5.119 (L 32) | −4.649 | −1.676 (400) |
| 6,619 | OOD | +0.206 | −9.129 | −8.999 (L 32) | −8.048 | −3.707 (400) |

At 1,000 and 2,000 genes the AE with a 50-dimensional latent scores within 0.16 of a linear 50-component PCA; it does better than the PCA at 250–500 genes and worse at 4,000–6,619 genes [R]. So much of the loss comes from compressing to 50 dimensions, not from the AE being nonlinear [I]. The +0.457 Gaussian OT result is the highest all-gene raw fgc anywhere in this family; the highest in EXP is `raw_shift` on D, +0.377 [R]. (On the top-50 marker genes, MD/figs/arm_metrics_top50.csv has +0.484 for B, a different metric; section 3.)

### 5. 2026-07-07 → 07-08: PCA ceiling, linear baselines, latent sweep

- **PCA ceiling.** With 50 components, the share of variance PCA leaves out is 0.22 at 250 genes, 0.36 at 1k, 0.47 at 2,000 and 0.62 at 6,619. Keeping 95% of the variance needs 130, 514, 1,152 and 3,826 components (AES/pca_ceiling.csv, scgen rows) [R]. This is where the later latent sizes 1,152 and 3,826 come from; PLAN:143-144 asks for extra grid points "bracketing PCA L@90/95%" [D][I].
- **Linear baselines.** 72 `pca_arith` and 70 `gaussian_ot` rows, plus 2 linear-AE rows (AES/ae_study.csv; AES/linear_baselines.log) [R]. At full rank, `pca_arith` reproduces `raw_shift` exactly; the code asserts this (autoresearch:ae_study/linear_baselines.py:118-126) [C].
- **Latent sweep** (PLAN §6 and §7): latent 1, 2, 4, …, 4,096; hidden = max(512, 2 × latent); lr 1e-3; early stopping with patience 8 on a 15% validation split; 2,000 and 6,619 genes; both splits (EXP:193-276; RUNS/633adf9695f8_scgen_6619/train_config.yaml) [R]. 14 runs failed: 12 on the logger `KeyError 'step'` and 2 on CUDA out-of-memory (LOGS/ar-latsweep_29275251_*.err) [R]. Every raw fgc was negative: the best was −0.836 (2,000 genes, scgen, L 192), the worst −36.56 (6,619, scgen, L 1) [R]. Reconstruction did not improve with latent size: train MSE stayed at 0.075–0.101 and per-gene R² at 0.10–0.20 across all 84 runs (AES/recon_sidecar.csv) [R]. At 6,619 genes, 7 runs with L ≥ 2,048 were flagged unstable, one ending at train MSE 548 (AES/train_dynamics.csv) [R]. RECON:27-43, 64-73 read this as a training failure ("optimization breakdown" at the largest latents), not as evidence about the bottleneck [D].

### 6. 2026-07-10: reconstruction diagnostics at 2,000 genes (scgen split)

- **Identity checks** (AES/identity_ceiling.csv) [R]. An identity check asks whether a model with latent size equal to the gene count can copy its input. Full-rank PCA: MSE about 1e-30, R² 1.0. Linear AE with L = 2,000: train MSE 3.3e-6, per-gene R² 0.997 (0.987 on the target cells). The plan's pass bar was MSE < 1e-4 and R² > 0.99 (RECON:156-160) [D]; the linear AE passes it here [I].
- **Deep AE with L = G = 2,000** ([4000, 4000], 100k iterations, EXP:277-279) [R]: raw fgc −1.129 (lr 1e-3, wd 0), +0.257 (lr 1e-4, wd 0), −1.882 (lr 1e-3, wd 1e-5). In these three runs the learning rate decided the outcome [I].
- **Controlled latent sweep** (lr 1e-4, wd 0, [4000, 4000], 100k, no early stopping; first unseeded, then with training seed 0) (EXP:278, 280-290; AES/controlled_latent_sweep*.csv) [R]:

| latent | 50 | 200 | 400 | 800 | 1,152 | 2,000 |
|---|---|---|---|---|---|---|
| target MSE (seed 0) | 0.0601 | 0.0446 | 0.0263 | 0.0098 | 0.0046 | 0.0018 |
| target per-gene R² (seed 0) | 0.041 | 0.082 | 0.162 | 0.358 | 0.534 | 0.722 |
| raw fgc, seed 0 | −2.064 | −0.546 | −0.025 | +0.216 | +0.221 | +0.259 |
| raw fgc, unseeded | −1.749 | −0.493 | −0.014 | +0.266 | +0.256 | +0.257 |
| decoded fgc, seed 0 | −1.306 | −0.211 | +0.149 | +0.276 | +0.264 | +0.268 |

`raw_shift` on the same cells scores +0.229 (EXP:145) [R].
- **Optimizer grid.** 6 latent sizes × 5 recipes, all with seed 0 (EXP:292-324; AES/optimization_sweep_seed0.csv) [R]. The best AE raw fgc in the whole family, +0.283, came from `bestval` (and `adamw`) at L 1,152 (EXP:300, 313) [R]. Plain seeded Adam was kept as the "frozen winner" (RECON:202-218) [D]. The `adamw` rows are bit-identical to the `bestval` rows in 5 of 6 latent sizes and at 6,619 genes (EXP:301/304, 293/305, 294/309, 300/313, 297/312, 336/337) [R]. A likely reason: AdamW multiplies each weight by 1 − lr × wd = 1 − 1e-8 per step, which rounds to exactly 1.0 in float32, so it equals Adam without weight decay [I]. The L 800 pair differs. Its `bestval` run crashed once on the logger `KeyError` at step 80,000 and was resumed from that step (EXP:295, 303; LOGS/ar-optgrid_30057330_3.err, ar-optretry_30058048_1.err) [R]. But `bestval` at L 50 also crashed (at step 30,000) and was resumed, and still matches `adamw` (EXP:292, 301, 304; ar-optgrid_30057330_0.err, ar-optretry_30058048_0.err) [R]. So the resume is a possible reason for the L 800 difference, not a proven one [I].
- **Shallow probe.** One hidden layer [4000] with L = 2,000 improved reconstruction (target per-gene R² 0.879, AES/recon_sidecar.csv) but not prediction (raw +0.236, EXP:325) [R].
- **Representation ladder** (AES/representation_ladder_g2000_scgen.csv) [R]. Raw fgc: `raw_shift` 0.2291, full-rank PCA 0.2291, linear AE 0.2290, deep AE L 50 −0.924, deep AE L 2,000 +0.259.

### 7. 2026-07-13: the frozen-representation ICNN ladder ("Round 1′")

- **Plan.** Seven "rungs": representations that are each kept fixed while only CellOT's ICNN map is trained on them. They were raw genes, full-rank PCA, linear AE, shallow AE, and deep AEs at L 50, 800 and 2,000 (conny:specs/lps_icnn_ae_study.yaml:23-64, committed conny@4244985 on 07-30; AR/configs/generated/icnn_ot_round1_seed0/, 7 configs) [C][R]. The hub prints the submit command but never submits (conny:docs/hub_usage.md:294-310) [D].
- **What ran.** Only the deep L 800 rung (array index 6 in all four job logs). The first three attempts crashed before the first training step: an unexpected `device` argument in the ICNN constructor, a missing validation iterator, and a CPU/GPU device mismatch (LOGS/icnn_ot_30656950_6.err, icnn_ot_30659815_6.err, icnn_ot_30665669_6.err) [R]. The fourth reached 250,000 iterations and wrote metrics on 07-13 at 20:27. Its surviving log starts at step 44,000, so the run was resumed from a checkpoint, most likely after a requeue that overwrote the first part of the log; the last 206,000 steps took 2 h 14 min (LOGS/icnn_ot_30666137_6.err, .out) [R][I]. No logs exist for the other six rungs [R]. AES/ot_ladder_g2000_scgen.csv still lists all seven as `pending` [R]. The code also defines ICNN rounds 2 and 3 (one ICNN per controlled-sweep latent and per optimizer recipe; autoresearch:ae_study/icnn_ot_sweep.py:182-230) [C], but only round-1 configs were ever generated (AR/configs/generated/icnn_ot_round1_seed0/, 7 files) [R].

| on the frozen L 800 deep AE (2,000 genes, scgen) | ICNN-OT | latent mean shift |
|---|---|---|
| raw fgc | −0.203 | +0.216 |
| decoded fgc | −0.134 | +0.276 |
| latent fgc | −0.556 | +0.170 (via encode of the prediction) |
| `frac_r2_closed` | −0.323 | +0.344 |
| `mean_js` (lower is better) | 0.414 | 0.384 |

Sources: AR/results/icnn_ot/640eead2b9c2/metrics.json and EXP:288 [R].

### 8. 2026-07-14 → 07-18: the same study at 6,619 genes

- **The redo.** The first attempt (07-14) used width [4000, 4000], which is narrower than the latent at L = 4,096 and 6,619. It was "obliterated" on 07-17 (AR/ae_study/PLAN_three_round_g6619.md:17-19) [D]. Its 9 runs (8 latent sizes in job 30793630 and a shallow [4000] probe in job 30793641) had all finished with status `ok`; one task (index 7) was preempted and requeued on the way, but none was cancelled for good [R]. Their rows and folders are gone from EXP and RUNS, and the numbers survive only in the job logs. Raw fgc: L 50 −6.34, 200 −2.54, 400 −1.25, 800 −0.67, 1,152 −0.42, 2,000 −0.16, 4,096 −0.41, 6,619 −0.37; shallow [4000] with L 6,619 +0.018 (LOGS/ar-lat-g6619_30793630_{0-7}.out, ar-shallow-g6619_30793641_0.out) [R]. The redo used width [13238, 13238], 8 latent sizes, a shallow probe, and 5 recipes at L 2,000 (EXP:326-339) [R]:

| latent | 50 | 200 | 400 | 800 | 1,152 | 2,000 | 4,096 | 6,619 |
|---|---|---|---|---|---|---|---|---|
| target per-gene R² | 0.026 | 0.029 | 0.040 | 0.065 | 0.082 | 0.080 | 0.091 | 0.065 |
| raw fgc | −0.918 | −0.360 | −0.184 | −0.024 | −0.025 | −0.016 | −0.006 | −0.044 |
| decoded fgc | +0.141 | +0.118 | +0.212 | +0.208 | +0.176 | +0.219 | +0.224 | +0.288 |

Sources: EXP:327-334; AES/controlled_latent_sweep_seed0_g6619.csv [R]. `raw_shift` scores +0.208 [R].
- **Other models at 6,619 genes.** The shallow [13238] net: target R² 0.194, raw −0.238 (EXP:326) [R]. The linear AE with L = 6,619: target R² 0.701, raw +0.206 (AES/identity_ceiling.csv; AES/representation_ladder_g6619_scgen.csv) [R]. The 5 recipes at L 2,000: −1.083 to −3.879; `combined` gave a decoded score of 22.8 (EXP:335-339) [R]. The last job finished at 07-18 15:52 (LOGS/monitor_g6619_r3.log:24) [R].

### 9. How big is run-to-run noise?

No seed sweep was run, but 23 pairs of runs share a byte-identical training config (unseeded, 50k iterations, latent ≤ 100). Most are the same config logged under two tiers (my comparison of RUNS/*/train_config.yaml over EXP) [R]:

| split / genes | pairs | median (max) abs. difference: `r2_all` | raw fgc | decoded fgc |
|---|---|---|---|---|
| scgen / 1k | 6 | 0.015 (0.027) | 0.042 (0.106) | 0.068 (0.141) |
| OOD / 1k | 6 | 0.015 (0.022) | 0.049 (0.136) | 0.044 (0.093) |
| scgen / 6,619 | 7 | 0.011 (0.035) | 0.250 (0.761) | mostly NaN |
| OOD / 6,619 | 4 | 0.009 (0.011) | 0.356 (1.100) | 0.126 (0.451) |

Seed 0 versus unseeded at 2,000 genes differs by 0.001–0.315 raw fgc: 0.315 at L 50, 0.053 at L 200, and 0.001–0.050 for L ≥ 400 (the table in section 6) [R]. Repeated `raw_shift` runs are bit-identical (EXP:48/132, 90/139, 9/73/185, 8/178) [R].

### 10. Corrections to earlier survey notes

Most survey leads checked out. These did not, or only in part:
- **"The FASRC copy has uncommitted director.py, policy.py, … ae_study/, meeting_david/".** This is true relative to the FASRC clone's own HEAD, 170e916 (conny:docs/archaeology/sources.md:106-107) [D]. But all of these except `meeting_david/` were committed to GitHub in autoresearch@5d1a7d9 with identical content [G][R]. `meeting_david/`, `adaptations.yaml`, `configs/generated/` and `.gpu_libs/` are in no repository; the last two are git-ignored (autoresearch:.gitignore) [G].
- **"The director ran one rule-based episode … 21 proposals".** The director's agenda has 4 items. The 21 proposals were logged separately by `explore.py` (section 2) [R].
- **"Reconstruction improves with latent size up to L = genes; a linear AE passes the identity test".** This holds only for the 07-10 recipe at 2,000 genes. It does not hold for the 07-08 latent sweep or at 6,619 genes, where the linear AE reaches train R² 0.93, below the 0.99 bar (sections 5, 6 and 8) [R].
- **"ar-latsweep: 12 of the 14 failures are a logger KeyError".** Correct; the other 2 are CUDA out-of-memory [R].
- **Sizes not re-measured.** RUNS is 188 GB according to conny:docs/archaeology/sources.md:56 and "196 GB" according to the 07-29 commit message (autoresearch@5d1a7d9) [D][G]. The survey's Slurm count of 390 jobs is consistent with the 387 job logs; Slurm accounting was not re-queried [R][I].

## Verdict

- **Supported, moderately strong.** On this task, scored by all-gene MMD in gene space, CellOT's default AE plus a latent mean shift predicts worse than the same mean shift done directly on genes. This holds at all six gene counts and in both splits [R]. Only 11 of 301 AE runs beat `raw_shift`: one at 250 genes and ten wide AEs with lr 1e-4 at 2,000 genes, of which two `adamw` runs repeat `bestval` runs exactly (EXP) [R]. The very negative values at 6,619 genes are partly a small-denominator effect [R][I].
- **Supported at 2,000 genes, `scgen` split, one seed.** The loss is mainly the 50-dimensional bottleneck. A 50-component PCA loses about as much at 1,000–2,000 genes (section 4 table), and widening the latent with a good training recipe removes the loss at 2,000 genes [R]. But even the best AE only ties `raw_shift`. It is at most 0.054 above it (+0.283 vs +0.229), about the size of the difference between a seeded and an unseeded run of one config (0.001–0.050 for L ≥ 400, section 6) [R][I]. That best value is also the maximum over 45 finished wide-AE runs at 2,000 genes (EXP:277-325 without the smoke run), so it is biased upward [R][I]. Nothing here shows the AE adding predictive value. None of the July work used the `bunne_ood` split [R].
- **Supported.** At 6,619 genes no deep AE recipe tried reconstructed the target cells well (per-gene R² ≤ 0.091 in the latent sweep and ≤ 0.134 across the five recipes), and none reached `raw_shift` (AES/controlled_latent_sweep_seed0_g6619.csv; AES/recon_sidecar.csv) [R]. So a recipe tuned at 2,000 genes does not carry over to 6,619 genes [I].
- **Supported.** Mean-only metrics rank differently from MMD. Under the scgen split the AE has a slightly higher `r2_all` than `raw_shift` (0.834 vs 0.810 at 1k; 0.910 vs 0.896 at 6,619; EXP:128/132, 176/178) while being much worse on MMD [R]. Doing nothing already scores r² 0.66–0.87 (Setup table) [R].
- **OT, weak evidence.** A linear Gaussian OT map gave the best single number (+0.457, OOD, 250 genes) but lost to `raw_shift` everywhere else [R]. The only neural OT run was worse than a mean shift on the same latent space [R]. This gives no support for "OT beats a mean shift" on the LPS data, but one run cannot rule it out [I].
- **The `north-star` failed as a model-selection metric.** Among 301 AE runs it is NaN in 42, above 1 in 16 and below 0 in 46 (EXP) [R], and it rises when reconstruction gets worse (the β example in section 3) [R].
- **Cannot be concluded.** Anything about the scGen paper's VAE (not used here); knob effects smaller than about 0.1 at 1k genes (inside the noise, section 9) [R]; other split seeds (never varied); and an AE-vs-no-AE comparison on marker genes (never run).

## Why it stopped

- **Stated reasons.** The 2026-07-20 log lists "Global-best G=6619 optimizer search" under "Stop (infinite games)" and notes "G=2000 deep recipe fails at G=6619 recon under same knobs" (conny:logs/research_logs/research_log_2026-07-20.txt:36-45) [D]. The 07-21 plans say "LPS paper-replication threads are parked as infinite games" (conny:logs/research_logs/agent_plans_2026-07-21/DELIVERABLE_A_atlas_memory.md:131) and that chasing global AE hyperparameter tuning "is an infinite game", with the atlas as the next target (conny:logs/research_logs/agent_plans_2026-07-21/PLAN_B_atlas_return_scoreboard.md:24) [D]. A slide image from 07-21 is titled "Recipe transfer failed" (fasrc:BK/.cursor-assets/failure-4-recipe-transfer.png) [D].
- **What the record suggests** [I]:
  - The next steps planned in RECON never ran: seed repeats at L ∈ {800, 1,152, 2,000} (RECON:321-322; no training seed other than 0 exists) [D][R], and the six remaining ICNN rungs (RECON:237-252; section 7) [D][R].
  - The AE question moved to the ablation repository (F15; "Round 3 launched (identity-first)" on 07-27, conny:logs/research_logs/research_log_2026-07-27.txt:182-185) [D], and the project returned to the atlas (F14).
  - The loop had stopped steering the work after 06-23: there are no driver or director job logs [R], and the journal INS ends on 06-23 [D].

## Problems in how it was done

- **"Autonomous" overstates what ran.** The README says "The loop has run" (autoresearch:README.md:16) [D]. Yet `findings.json`, `intuitions.md` and `results/logs/llm_usage.jsonl` do not exist; there are no ar-driver or ar-director logs; and the director planned once [R]. The design doc reports that a compute-node job reached the LLM provider's API on 06-23 (AUTONOMOUS_DESIGN.md:384-385) [D], but no LLM reasoner episode left any trace [R]. The work was chosen in agent sessions, so coverage is uneven: for example, everything after 07-08 is on the scgen split only [R].
- **The proposer and the "best" run.** The proposer says it centers on the running best but always perturbs arm A (proposer.py:37-47, 128-200) [C]. The "best" it cited, D's decoded 0.412 (AR/results/research_agenda.json) [R], is the cross-split score that Finding 3 calls confounded (INS:84-93) [D]. This matters because the stated search method was not the method actually used.
- **The decoded `north-star` is unstable.** It is NaN or above 1 at 6,619 genes, and it rewards worse AEs within a split, not only across splits (section 3) [R]. Any "win" ranked on it, including the slide's "VAE helps", is unreliable.
- **Raw fgc denominators differ fivefold by gene count** (0.107 vs 0.021) [R]. So raw fgc values are comparable within one gene count, not across gene counts [I].
- **One split seed and mostly unseeded training.** Most one-change differences at 1k genes (about ±0.1) are within the measured rerun spread (section 9) [R]. Single-knob claims at that size cannot be trusted. The planned 250k confirmations of 50k "wins" and the seed sweeps (slides_part1_results.md:42-43, 107-108) [D] never ran: no AE run after 06-23 has 250k iterations (EXP) [R].
- **A missed replication check.** The declared check compares the primary metric (`r2_all` under `scgen`, `r_50` under `bunne_ood`) with the Mac value, with tolerance ε = 0.02 (search_space.yaml:23, 26-32; reflect.py:43-45, 127-137) [C]. By that rule the cluster baselines missed for B (`r2_all` −0.028) and C (`r_50` +0.031); A (−0.015) and D (`r_50` −0.017) passed. On `r2_all` alone D also missed (−0.048) (EXP:6-7, 60, 64 vs baselines.yaml) [R]. No file records the comparison. The 250k runs were logged as `full_baseline_250k`, not as a tier1 replication tier, and `reflect.py` never wrote output [R].
- **Silent overrides.** AR/adaptations.yaml turned the "n_iters = 100,000" run into 50,000 (EXP:18) [R]. The `adamw` recipe was numerically the same as `bestval` (section 6) [R][I]. Neither result says anything about its knob.
- **The ledger and the folders disagree.** On 06-23 at 16:13, the B and D 250k folders' metrics.json files were overwritten with `raw_shift` results; RUNS/6826b38e062d_scgen_1k/metrics.json says `"prediction": "raw_shift"`, while EXP:6-7 keep the AE numbers [R]. The CPU run behind Finding 6's A number is missing [R]. Ten folders (f930…–ffc0…) hold only an empty `cache/` folder in BK, so only EXP keeps their numbers [R]; they are the alphabetically last ten, which suggests the backup copy stopped early [I]. The 9 finished runs of the first 6,619-gene attempt were deleted from both RUNS and EXP; only their job logs remain (section 8) [D][R]. CLUSTER.md:23 calls EXP an "append-only run log" [D], but it is neither complete nor append-only [R][I].
- **Secondary metrics see the target.** Marker genes, used for `r_50` and for the top-50 marker MMD, are ranked with the held-out rat LPS6 cells, and the `bunne_ood` HVGs use rat cells [C]. This makes marker scores optimistic [I].
- **`fig5_arithmetic` (4 runs)** uses all rat unst cells whatever the split, and draws mouse-control indices from the mouse-LPS6 index range (ABL/scripts/cellot_predict.py:81-98) [C].
- **The ICNN comparison is one run.** One rung, one seed, a run resumed part-way, and an un-summarized CSV [R]. It cannot carry an "OT vs mean shift" conclusion.
- **Agent-written docs overstate or contradict the data.** See section 3. Also, INS entries are out of time order (the 23:25 entry precedes the 16:38 and 16:50 ones; INS:153-208), and the journal stops on 06-23 [D].

## Terms used here

- **arm A / B / C / D**: split × gene space: scgen/6619, scgen/1k, bunne_ood/6619, bunne_ood/1k. **G{N}_{split}**: an extra HVG arm with N genes.
- **`scgen` split**: only rat LPS6 is held out. **`bunne_ood` split**: all rat cells are held out, and half of them are evaluated.
- **`transport_scgen`**: the CellOT AE plus a pooled latent mean shift ("scGen" in this repo). **`raw_shift`**: the same shift in gene space, with no AE. **`pca_arith`**, **`gaussian_ot`**: the PCA versions of a mean shift and of a Gaussian OT map.
- **`honest metrics`**: the repo's name for its gap-closed metric set. **floor**: the target compared with itself. **ceiling**: the source compared with the target ("do nothing").
- **`frac_gap_closed`** (raw fgc): computed in gene space. **`frac_gap_closed_decoded`** = the **`north-star`**: the metric the loop was told to maximize, computed with AE-reconstructed floor and ceiling. **`frac_gap_closed_latent`**: the same in AE code space.
- **`guardrails`**: secondary metrics that a "win" must not worsen: `frac_r2_closed_decoded` and `mean_js` in space.yaml:20-24; the slides name `frac_r2_closed` instead (slides_part1_results.md:28).
- **`AE tax`**: the extra MMD that comes only from passing cells through encode → decode.
- **tier**: the batch label in EXP. **one-delta**: exactly one setting changed from a baseline (`baseline_id`, `delta_field`, `delta_value`).
- **`adaptations.yaml`** (AR/adaptations.yaml, on FASRC only, not in git): rules that override "infrastructure" settings such as `n_iters`.
- **L1 / L2 / L3**, also called "substrate / proposer / director" or "brain": the fixed tier loop, the one-delta proposer, and the director with a `RuleReasoner` or `LLMReasoner`. **`research_agenda.json`**: the director's saved plan.
- **recipes** `baseline` / `bestval` / `dropout` / `adamw` / `cosine_clip` / `combined`: the training variants of section 6. `bestval` = early stopping on a full validation pass.
- **identity ceiling**: whether a model with latent size equal to the gene count can copy its input. **recon sidecar**: reconstruction scores of a trained AE (AES/recon_sidecar.csv).
- **rung / ladder / Round 1′**: one fixed representation in the July comparisons, the set of rungs, and the ICNN version of the ladder.
- **seeded / unseeded**: whether `training_seed` 0 was set (from 07-10 on) [R].

## What the package needs from this

1. **`raw_shift` plus the MMD gap metric on arms A–D.** This is the best reference test here: there is no training, and reruns are bit-identical [R].
   - Inputs: ABL/data/processed/arms/{A_6619_scgen_split, B_1k_scgen_split, C_6619_bunne_ood, D_1k_bunne_ood}.h5ad and ABL/data/manifests/*.csv (the manifests are also in ablation git). The four arm files and the G250–G4000 arms exist in BK (`ls` on FASRC on 2026-10-20: A–D dated 06-22, G arms 06-26), but their hashes were not checked against split_summary.json; the Mac copies are empty (mac:scGen v.s. CellOT/data/processed/arms/) [R]. They can be rebuilt with ABL/scripts/02_prepare_data.py from ABL/data/raw/train_species.h5ad, which is in BK with the size listed in fasrc:BK/offline_data_manifest.txt:7 (209,165,300 bytes) [C][R].
   - Config: the shift over the training cells; n = 30, 50, 80; 10 repetitions; 50 bandwidths; `np.random.default_rng(0)`; headline at n = 80 (run_one_experiment.py:245-256, 323-330; honest_metrics.py:42-43) [C].
   - Expected (raw fgc / `r2_all` / `frac_r2_closed` / `mean_js`): B 0.33769 / 0.80961 / 0.44084 / 0.25765; D 0.37668 / 0.82773 / 0.49665 / 0.28431; A 0.20807 / 0.89607 / 0.22036 / 0.18222; C 0.20594 / 0.90101 / 0.26105 / 0.18818 (RUNS/6e099eb43516…, 19362ebf748a…, 95c11f9e113d…, ec74ad5e8c4f… metrics.json) [R].
   - Tolerance: about 1e-6 if the sampling order is the same, since reruns are bit-identical [R][I]. Otherwise about 0.01, the spread between n = 30, 50 and 80 within one run (`per_ncells` in the same files: 0.008–0.012) [R][I]. The harness's own parity test allowed 0.05 (autoresearch:ae_study/harness.py:205-230) [C].
2. **MMD unit test.** The floor and ceiling values in the Setup table, e.g. 0.02063 / 0.12776 for scgen/1k, are fixed properties of the data and the estimator [R]. They test the package's biased MMD, its bandwidth average and its subsampling. Note: the package's `MMDEvaluation` uses a single γ = 0.1 on the whole clouds, with no subsampling (josh@scgen-model-impl:src/speciesot/speciesot_core.py:320-335; conny:docs/archaeology/metrics.md:99) [C]. It will not match until that is changed.
3. **Identity test.** A full-rank PCA mean shift must equal `raw_shift`: 0.2291176 vs 0.2291181 at 2,000 genes (AES/representation_ladder_g2000_scgen.csv), with the assertion rtol 1e-7 at autoresearch:ae_study/linear_baselines.py:118-126 [R][C].
4. **CellOT-AE baseline on B** ([512, 512], L 50, lr 1e-3, wd 1e-5, batch 256, 50k iterations): `r2_all` 0.834, raw fgc −0.083, decoded 0.281 (EXP:128); at 250k, 0.818 / −0.034 / 0.286 (EXP:7) [R]. Tolerance from the duplicate pairs (section 9): `r2_all` ±0.03, raw fgc ±0.11, decoded ±0.14 [R].
5. **Optional, deterministic.** Gaussian OT on OOD/250 genes with K 200 and shrinkage 0.1: +0.457 (AES/ae_study.csv) [R]. No rerun exists, so the tolerance is unknown; 0.02 is a guess [I]. A GPU-sized option is the seeded wide AE at 2,000 genes with L 800: raw +0.216, unseeded +0.266, so ±0.05 (EXP:288, 283) [R].
6. **Not worth reproducing as numbers.** The ICNN run (a single GPU run of more than 2 hours, resumed part-way; section 7) [R], the 6,619-gene sweeps (up to about 1 h of GPU per run, and poor reconstruction; EXP:327-334, wall_sec) [R], and any decoded-score ranking.

## Open questions

- Do the arm h5ad files in ABL/data/processed/arms/ match the hashes in split_summary.json? They exist (verification pass of 2026-10-20, when FASRC SSH worked again; the first pass had failed with "Permission denied (keyboard-interactive)"), but hashing 0.6 GB files was out of scope for a read-only pass.
- Why was the first 6,619-gene attempt (width 4,000) deleted rather than kept as a labelled variant? Its shallow [4000] probe (+0.018) is the best nonlinear-AE raw fgc recorded at 6,619 genes (section 8) [R].
- Why does the deep AE recipe that works at 2,000 genes fail to reconstruct at 6,619 genes even at width 13,238, while a linear AE reaches per-gene R² 0.70 (section 8) [R]?
- Is the ICNN's −0.203 (section 7) [R] a training problem (validation split, schedule) or a real loss? Only one run exists.
- Does the Gaussian OT win at 250 genes (OOD) survive other split seeds, and does it hold at K > 400 for more genes?
- On the top-50 markers (CellOT's own metric), does `raw_shift` still beat the AE?
- What did David say at the meeting? There are no notes.

## Sources

- autoresearch (git): README.md, program.md, priorities.md, AGENT_PLAN.md, AUTONOMOUS_DESIGN.md, CLUSTER.md, cluster.yaml, schema.py, search_space.yaml, space.yaml, baselines.yaml, honest_metrics.py, run_one_experiment.py, autoresearch.py (grep), director.py, proposer.py, policy.py, explore.py, reflect.py, synthesize.py, llm_client.py, backfill_honest.py, gen_genecount_sweep.py, ae_study/{harness.py, linear_baselines.py, icnn_ot_sweep.py, optimization_sweep.py, pca_ceiling.py}, .gitignore at every commit, git log of all 7 commits; GitHub API metadata of JunyiZhou-Conny/scgen-cellot-autoresearch (`created_at`, `pushed_at`).
- AR (fasrc:BK/scgen-cellot-autoresearch, via the local mirror): results/experiments.csv, results/insights.md, results/research_agenda.json, results/proposals.jsonl, results/icnn_ot/640eead2b9c2/{experiment.json, ot_config.yaml, config.yaml, metrics.json}, results/runs/*/{experiment.json, train_config.yaml, metrics.json, error.txt} (all, by script), results/logs (file list; ar-tier0_smoke, ar-full250k, ar-base250k, ar-explore, ar-overnight_24383839_{0,1}, ar-latsweep, ar-optgrid_30057330_{0,3,6}, ar-optretry_30058048_{0,1,2}, ar-lat-g6619_30793630_* and _32284686_*, ar-shallow-g6619_*, icnn_ot, backfill.log, monitor_g6619_r3.log), adaptations.yaml, configs/generated/ (list and 2f93b8153df3.json), ae_study/PLAN.md, PLAN_recon_diagnostics.md, PLAN_three_round_g6619.md, ae_study/results/{ae_study, pca_ceiling, identity_ceiling, controlled_latent_sweep, controlled_latent_sweep_seed0, controlled_latent_sweep_seed0_g6619, optimization_sweep_seed0_g6619, ot_ladder_g2000_scgen, representation_ladder_g2000_scgen, representation_ladder_g6619_scgen, recon_sidecar, train_dynamics}.csv, linear_baselines.log, recon_sidecar.log; meeting_david/{slides_part0_journey, slides_part1_results, slides_part2_mmd, PLAN_A_results_analysis, PLAN_B_mmd_questions}.md, plot_arm_metrics.py, figs/arm_metrics_top50.csv.
- FASRC directly (first pass, before its auth failure; and the verification pass of 2026-10-20): `ls`/`find` of fasrc:BK/scgen-cellot-autoresearch/results/runs (337 folders; counts of model.pt, last.pt, metrics.json, error.txt, experiment.json; contents of the 10 folders missing from the mirror), `ls -la` of fasrc:BK/scgen-cellot-autoresearch/ and its empty `slurm/`, `md5sum` of its .gitignore, and `ls -la` of fasrc:BK/scgen-cellot-ablation/data/{processed, processed/arms, raw}.
- ABL (fasrc:BK/scgen-cellot-ablation): scripts/02_prepare_data.py, 02b_prepare_hvg_arms.py, cellot_predict.py, cellot/cellot/models/ae.py, data/manifests/split_summary.json; ablation:results/stage1/{A,B,C,D}/metrics.json and train_config.yaml.
- conny: AGENTS.md; docs/conceptual_framework.md (grep); specs/lps_icnn_ae_study.yaml; cellot/cellot_gpu/configs/models/scgen.yaml; docs/archaeology/timeline.md; text search of logs/ and docs/ for "David"/"Alvarez"; logs/research_logs/research_log_2026-07-20.txt, research_log_2026-03-30.txt, research_log_2026-07-27.txt, research_log_2026-07-30_repo_plan.txt; logs/research_logs/agent_plans_2026-07-21/{DELIVERABLE_A_atlas_memory.md, PLAN_B_atlas_return_scoreboard.md}; docs/hub_usage.md; docs/archaeology/{sources.md, metrics.md, inventory.csv}.
- fasrc:BK/.cursor-assets/failure-4-recipe-transfer.png, failure-5-unexplored.png; fasrc:BK/offline_data_manifest.txt.
- mac: scGen v.s. CellOT/data/processed/arms/ (empty).
- josh@scgen-model-impl:src/speciesot/speciesot_core.py:320-335 (`MMDEvaluation`).
- Papers: /tmp/sot-arch/papers/scgen.txt, cellot.txt [P].

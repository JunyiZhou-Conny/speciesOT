# F05 · First CellOT runs on the cross-species LPS data

> In March 2026 Conny ran the published CellOT code on its own cross-species task. The data are bone-marrow-derived immune cells (mononuclear phagocytes) from mouse, pig, rabbit and rat, either unstimulated (`unst`) or stimulated with LPS, a bacterial molecule that triggers inflammation (`LPS6`). A map from `unst` to `LPS6` was learned on three species and applied to held-out rat cells: once directly on all 6,619 genes (100k steps, 21 h), and once in the 50-number code space of an autoencoder (10k steps, 8.5 min; the `race_*` runs, set up mainly as a CPU-vs-GPU speed test, although the "GPU" jobs most likely ran on CPUs). Only the code-space model was scored on rat, and only in code space: MMD 0.216, Pearson r 0.846 between mean codes (squared 0.715), and nearest-neighbour enrichment ≈1.0, which means predicted and real rat cells do not mix; no baseline was run. The gene-space scoring hit its 1-hour limit, no score of the raw-gene model survives, and from 2026-03-18 the work moved to the mouse/human atlas (F06), so the status is abandoned unfinished; later docs describe these runs wrongly ("1000-dim", "mouse→human", "no scGen").

| | |
|---|---|
| Period | 2026-03-04 → 2026-03-16. First look at the data: josh@e86c1df. Last job with surviving output ended 2026-03-15 18:14 (ARCH/race_cpu/eval_ds_66195100.err). Last March file time: 2026-03-16 10:55:22 on both eval scripts in fasrc:BK/sbatch/eval/ (the same second for both, and after the 03-15 job that used one of them, so probably a copy or move, not an edit [R, file times; I]). Notebooks committed 2026-03-24 (josh@ddc56ad). |
| People | Junyi (Conny) Zhou ran every job (files owned by `jzhou1125`) and wrote the notebooks and the 03-15 log. No direct trace of Joshua Price; the 03-04 commit is titled "Pair coding" without naming the partner. NB00 was re-run between 03-24 and 03-25 with a Python env under `Lab/joshprice/` (its c2 output shows the `CellOT` env at josh@ddc56ad and that env at josh@1db1592) [N, NB00#c2; G]: shared infrastructure, not evidence that Josh worked on these runs. |
| Status | abandoned unfinished |
| Main code | mac:OptimalTransport/CellOT/cellot/configs/tasks/crossspecies-ood.yaml (task config, unmodified CellOT repo) · conny:cellot/cellot_gpu/cellot/data/cell.py · conny:cellot/cellot_gpu/cellot/train/train.py · conny:cellot/cellot_gpu/scripts/evaluate.py · fasrc:BK/sbatch/train/racing_cellot/cellot_cpu_shared.sbatch · fasrc:BK/sbatch/eval/eval_cellot_50dim_ood.sbatch. The conny: files are later versions; March copies survive only as Jupyter checkpoint files under fasrc:BK/cellot/cellot_gpu/**/.ipynb_checkpoints/ (dated 2026-03-10). These predate the GPU edits (the train.py checkpoint has no device handling), so they are not exactly the code that ran on 03-13 to 03-15 either [C, diff of cellot/train/.ipynb_checkpoints/train-checkpoint.py with CODE/cellot/train/train.py]. |
| Results live in | ARCH/{cross_species_ood, cross_species_ood_scgen_gpu, race_cpu, race_gpu_requeue}/ (configs, logs, cache/); the only evals.csv is ARCH/race_cpu/evals_ood_latent_space/evals.csv; unscored decoded predictions in ARCH/race_cpu/evals_ood_data_space/imputed.h5ad; an empty folder fasrc:BK/cellot/cellot_gpu/results/cross_species_ood_cellot_gpu/ (output path of the cancelled dependent job); saved outputs of NB02 and NB03; figures conny:speciesOT/baseline/analysis/{scgen_eval_loss, cellot_previous_run, cellot_race_mmd, cellot_embedding_comparison, ood_distributional_metrics}.png. The CPU tree `cellot/cellot/results/` is not in the backup. |

Shorthands on this page: `ARCH/` = `fasrc:BK/cellot/cellot_gpu/results/_archive/scrna_crossspecies_pre_paper/` · `NB00` = `josh@cellot:baseline/analysis/00_data_exploration.ipynb` · `NB02` = `josh@cellot:baseline/analysis/02_scgen_training_analysis.ipynb` (identical copy at conny:speciesOT/baseline/analysis/) · `NB03` = `josh@cellot:baseline/analysis/03_cellot_evaluation_analysis.ipynb` (identical copy at conny:speciesOT/baseline/analysis/archive/) · `LOG15` = `conny:logs/research_logs/research_log_2026-03-15.txt` · `CODE/` = `conny:cellot/cellot_gpu/`.

## The question

Can CellOT, trained on how mouse, pig and rabbit cells respond to LPS, predict how rat cells respond? This is the out-of-distribution task (o.o.d.: the test species is never seen in training) of Bunne et al. Fig. 4d–f, which holds out rat or mouse [P, CellOT Fig. 4 caption]. LOG15 adds two practical questions: is CellOT faster in an autoencoder's code space than on raw genes, and does a GPU help [D, LOG15 sections 4–5]. In the paper, CellOT on scRNA-seq data is trained in the 50-d latent space of "the same encoder that is used for SCGEN", for 250k iterations [P, CellOT Online Methods "Training and technical details"]. So the code-space (`race_*`) runs follow the paper's design; the raw-gene run does not [I].

The plan is a to-do list at the top of the first data notebook: "Run CellOT using their own codes and their dataset / Apply on our cross-species dataset using cellot / Recreate using Pytorch" [D, NB00#c0; first written in josh@e86c1df:prediction/data_examination.ipynb#c0, which spells "Pytorhc"]. These runs are step 1. "Our cross-species dataset" is the mouse/human atlas of F06 [I].

## Setup

### Data
- File: `datasets/scrna-crossspecies/hvg-top1k-train-only.h5ad`, the name CellOT's own task config expects [C, mac:OptimalTransport/CellOT/cellot/configs/tasks/crossspecies-ood.yaml].
- Content: 62,114 cells × 6,619 genes; log-normalized values 0–7.383 (mean 0.179, SD 0.478); 81.3% zeros [N, NB00#c3, #c5, #c8]. Genes carry mouse symbols (Gnai3, Narf, …) [N, conny:cellot/cellot_gpu/explore_LPS_dataset.ipynb#c9]. The cells are mononuclear phagocytes (monocyte/macrophage-type cells) [P, CellOT "CellOT reconstructs innate immune responses across species"].
- Counts, from a notebook first committed on 2026-06-09 [G, conny:docs/archaeology/inventory.csv] that read the file at that path before the June re-processing (it shows 6,619 genes; its run date is not recorded); its shape and value statistics match the March outputs [N, explore_LPS_dataset.ipynb#c3, #c6, #c10]:

| species | unst | LPS6 | total |
|---|---:|---:|---:|
| mouse | 7,625 | 7,428 | 15,053 |
| pig | 8,448 | 4,806 | 13,254 |
| rabbit | 8,856 | 7,107 | 15,963 |
| rat | 8,421 | 9,423 | 17,844 |
| all | 33,350 | 28,764 | 62,114 |

- Origin: scGen's training file `train_species.h5ad` under CellOT's file name. The CellOT paper says its cross-species preprocessing was inherited from the scGen paper [P, CellOT Online Methods "Single-cell RNA sequencing data"]. On 03-04 Conny loaded `train_species.h5ad`; the version of the same notebook committed on 03-16 loads the CellOT-path file; both show the same shape and the same value statistics [N, josh@e86c1df:prediction/data_examination.ipynb#c3, #c8; josh@953e669:prediction/data_examination.ipynb#c3, #c8]. The June backup of the pre-June file at the CellOT path (`hvg-top1k-train-only.6619-backup.h5ad`) is byte-identical to `train_species.h5ad` (sha256 26e42d9f…, 209,165,300 bytes) [R, conny:offline_data_manifest.txt:5, :7]; by then the CellOT path itself held the new 1,000-gene file (line 6). That backup was written on 2026-06-12 14:51 [R, file time of fasrc:BK/cellot/cellot_gpu/datasets/scrna-crossspecies/hvg-top1k-train-only.6619-backup.h5ad], so byte identity with the March file is not proven; shape and statistics match [N]. With scGen's validation file (15,528 cells) the total is 77,642 [D, conny:offline_bundle/README.md:14-15], the scGen paper's cell count [P, scGen]. The CellOT authors' own processed file was never used ("ETH bundle … not used (auth required)") [D, conny:logs/research_logs/research_log_2026-06-13.txt].
- Not 1,000 genes. Despite the name, the file holds all 6,619 one-to-one orthologs (genes with exactly one matching copy in each species). Conny noted it on 03-04: "Not highly variable gene, because columns size should be restruicted to belwo 2000, we ahve 6000" [D, josh@e86c1df:prediction/data_examination.ipynb#c8]. The loader drops genes only if `data.features` is set; no config here sets it [C, CODE/cellot/data/cell.py:55-63; ARCH/*/config.yaml]. The June prep script calls this file the "6619-gene ortholog pool" and only then cut it to 1,000 genes [C, conny:cellot/cellot_gpu/paper_crossspecies/scripts/prep_data.py:1-4]. Checkpoint sizes confirm 6,619 inputs (section 6) [I].
- The paper used 1,000 highly variable genes (HVG: genes with the largest cell-to-cell variance), chosen on training cells [P, CellOT Online Methods "Single-cell RNA sequencing data"].

### Split (same for all runs)
- Source `unst`, target `LPS6`. The original config says `target: LPS`, a label this file lacks, so every March training sbatch adds `--config.data.target LPS6` [C, `mac:scGen v.s. CellOT/cellot/configs/tasks/crossspecies-ood.yaml` (the upstream CellOT copy); fasrc:BK/sbatch/train/racing_cellot/cellot_cpu_shared.sbatch].
- `toggle_ood`, `mode: ood`, `holdout: rat`, `key: species`: all rat cells are split 50/50 at random, not stratified by condition, into `ignore` (thrown away) and `ood` (scored) [C, ARCH/race_cpu/config.yaml; CODE/cellot/data/cell.py:330-375].
- Other cells: `groupby: [species, condition]`, `test_size: 500` puts 500 cells of each species×condition group into `test` (used to pick checkpoints); the rest is `train` [C, CODE/cellot/data/cell.py:267-283].
- Derived counts [I, table + code]: train 41,270; test 3,000; ignore 8,922; ood 8,922 (≈4,200 rat `unst` and ≈4,700 rat `LPS6` if the random half is proportional). LOG15 says "train: 80% … test: 20%" and lists "human, mouse, pig" [D, LOG15:6, :50-51]; both are wrong.
- The autoencoder used the same split, so it never saw rat; the code-space CellOT runs encode rat cells with that encoder [C, CODE/cellot/train/train.py:173-252; CODE/cellot/data/cell.py:149-175].
- One map for three species: CellOT learns one transport from all training `unst` cells to all training `LPS6` cells; species is not an input [C]. The pools are mixed differently: pig is 34% of training `unst` but 24% of training `LPS6` [I, from the table], so the map must move some pig cells toward other species.

### Models

| run | model | inputs | parameters [I] | steps | sbatch |
|---|---|---:|---:|---:|---|
| `cross_species_ood` | CellOT on genes | 6,619 | 3,427,384 | 100,000 | not found |
| `cross_species_ood_scgen` (CPU) / `_scgen_gpu` | autoencoder | 6,619 | 7,362,061 | 250,000 configured | fasrc:BK/sbatch/train/train_scgen_ood.sbatch, train_scgen_ood_gpu.sbatch |
| `race_cpu`, `race_gpu_requeue` | CellOT on codes | 50 | 50,918 | 10,000 | fasrc:BK/sbatch/train/racing_cellot/*.sbatch |

- CellOT: two ICNNs (input-convex neural networks: the output is convex in the input; the transport map is the gradient of one network), hidden layers [64, 64, 64, 64], Adam lr 1e-4 (β 0.5, 0.9), 10 updates of g per update of f, batch 128 [C, ARCH/race_cpu/config.yaml, ARCH/cross_species_ood/config.yaml].
- Autoencoder: the vendored CellOT model `scgen`, a plain autoencoder (β = 0: no KL term, no sampling), 6,619 → 512 → 512 → 50 → 512 → 512 → 6,619, MSE loss, Adam lr 1e-3, weight decay 1e-5, learning rate halved every 100k steps, batch 128 [C, ARCH/cross_species_ood_scgen_gpu/config.yaml; CODE/cellot/models/ae.py:51-87, :161-166]. On this page "scGen" means this autoencoder, not scvi-tools SCGEN.
- Parameter counts are computed from layer sizes [I, CODE/cellot/networks/icnns.py:48-69]. LOG15 gives "~1.6M" and "~31k" [D, LOG15:47, :86]; 1.6M is the count for 1,000 inputs.
- Paper: batch 256, 250k iterations [P, verified facts; CellOT Online Methods "Training and technical details"]. The repo's own task config already uses batch 128 and its model config 100k steps [C, mac:OptimalTransport/CellOT/cellot/configs/tasks/crossspecies-ood.yaml; mac:OptimalTransport/CellOT/cellot/configs/models/cellot.yaml].
- All four archived configs say `device: cuda`, including `race_cpu`, which ran on the CPU-only `shared` partition [C, ARCH/*/config.yaml; fasrc:BK/sbatch/train/racing_cellot/cellot_cpu_shared.sbatch:8]. The key comes from the edited model configs, which already had it on 03-10 [C, fasrc:BK/cellot/cellot_gpu/configs/models/.ipynb_checkpoints/cellot-checkpoint.yaml, scgen-checkpoint.yaml]. It does not show where a job ran.

### Evaluation
- During training: every 250 steps (CellOT) or 2,500 steps (AE), the code scores one random test batch of 128 cells and saves the lowest-scoring step as `model.pt`. CellOT uses a biased MMD (maximum mean discrepancy: a kernel distance between two point sets; 0 = same distribution) averaged over six RBF bandwidths γ = 2, 1, 0.5, 0.1, 0.01, 0.005; the AE uses MSE [C, CODE/cellot/train/train.py:58-80, :152-158, :233-240; CODE/cellot/losses/mmd.py:5-10, :114-125].
- After training, `scripts/evaluate.py --setting ood` pushes the rat `unst` cells of the `ood` half through the map and compares them with the rat `LPS6` cells of that half, on n = 100, 250, 500, 1000, 1500 cells, 10 draws each, with no fixed seed [C, CODE/scripts/evaluate.py:19-23, :193-204; CODE/cellot/utils/evaluate.py:174-219]. Metrics: MMD over 50 bandwidths (np.logspace(1, −3, 50)), l2 distance and correlation of per-feature means and SDs, correlation of feature–feature correlations, kNN enrichment [C, CODE/scripts/evaluate.py:62-86]. The March code computed MMD and enrichment only for fewer than 1,000 features [C, fasrc:BK/cellot/cellot_gpu/scripts/.ipynb_checkpoints/evaluate-checkpoint.py:75], as the original CellOT code does [C, mac:OptimalTransport/CellOT/cellot/scripts/evaluate.py:75]; today's code says ≤ 1000 [C, CODE/scripts/evaluate.py:78]. The evaluation MMD uses the same biased estimator as training (`mmd_distance`, diagonal included) [C, CODE/cellot/losses/mmd.py:5-10], not the "unbiased estimate" the paper describes [P, CellOT Online Methods "Metrics"]. It is positive even for two samples of one distribution, and that offset shrinks as n grows.
- `--where latent_space` compares 50-d codes; `--where data_space --embedding ae` decodes predictions to genes first. `evaluate.py` finds the autoencoder through `results/model-scgen` [C, CODE/scripts/evaluate.py:131], which pointed to `cross_species_ood_scgen_gpu` [R, symlink fasrc:BK/cellot/cellot_gpu/results/model-scgen].
- `r2-means` is an unsquared Pearson r [C, CODE/scripts/evaluate.py:73]. The hub cards square each value and average at the largest n [C, conny:speciesOT/hub/readers.py:56-58, :83-106].
- Not the paper's protocol: the paper reports MMD on the top-50 marker genes and r2 on all ~1,000 genes, both in gene space [P, CellOT Online Methods "Metrics", "Feature selection"]. The only finished March score is in the 50-d code space, so no number here can sit next to Fig. 4f [I].

## What was done and what came out

### 1. 2026-03-04: first look at the data
- A notebook committed as "Mar4 Pair coding Anndata UMAP examination" loads scGen's `train_species.h5ad` on the Mac, prints its shape, value range and UMAPs by species, condition and individual [G, josh@e86c1df; N, prediction/data_examination.ipynb#c3, #c8, #c9]. The CellOT repo was cloned to the Mac on 2026-03-03/04 [I, file times of mac:OptimalTransport/CellOT/cellot/].

### 2. Up to 2026-03-10: CellOT on all 6,619 genes (`cross_species_ood`, job 64733534)
- 100,000 steps in 21 h 10 min 16 s at 1.31 steps/s; status `done` [R, ARCH/cross_species_ood/train_64733534.err (tail), cache/status].
- Every file in the archived folder has the same time, 2026-03-10 22:16:49, so the folder is a copy made then [R, file times]. The run itself lived in the CPU tree `cellot/cellot/results/cross_species_ood`: NB02 parses a log there and gets the same 21:10:16 [N, NB02#c18]. So the hub inventory's "GPU re-run" [D, conny:scripts/build_experiments_inventory.py:295] is this same run [I].
- Training MMD: best 0.015835 at step 2,000 out of 400 evaluations [N, NB02#c13]. The saved curve starts at ≈0.016 at step 0, jumps to ≈0.041 and ≈0.024 at steps 250 and 500, and then stays between ≈0.0158 and ≈0.017 (slightly higher after step ~85,000) up to step 100,000 [N, conny:speciesOT/baseline/analysis/cellot_previous_run.png].
- Reading [I]: in 6,619 dimensions two different cells are so far apart that every kernel value between them is ≈0. The biased estimator then returns ≈1/128 + 1/128 = 0.0156 for any prediction that stays spread out (only predictions squeezed close together, as at steps 250 and 500, raise it). The untrained map at step 0 already scored there, so the curve cannot show learning, and the saved "best" step was picked by noise.
- No rat score survives. An eval script exists (fasrc:BK/sbatch/eval/eval_cellot_1000dim_ood.sbatch, file time 03-16); NB03 lists its output as "NOT READY YET" [N, NB03#c1]; the archived folder has no `evals_*` folder [R]. Not found elsewhere; its output path was in the CPU tree, which is not in the backup.
- The launching sbatch was not found. None of the five `train_*_ood*.sbatch` scripts (four with file time 03-10, `train_cellot_ood_gpu_requeue.sbatch` 03-15) writes to `cross_species_ood/`: the three `train_cellot_ood*` scripts set `ae_emb` (code space), and the two `train_scgen_ood*` scripts train the autoencoder [C, fasrc:BK/sbatch/train/train_cellot_ood.sbatch, train_cellot_ood_gpu.sbatch, train_cellot_ood_gpu_requeue.sbatch, train_scgen_ood.sbatch, train_scgen_ood_gpu.sbatch]. The only script that names `results/cross_species_ood` is the eval script above [C, search of fasrc:BK/sbatch/].

### 3. 2026-03-13 → 03-15: the autoencoder
- Two copies with one config: CPU (job 65338032, CPU tree) and GPU (job 65338587) [D, LOG15:15-16; C, train_scgen_ood.sbatch, train_scgen_ood_gpu.sbatch].
- CPU: stopped at the 48-h limit ("~38%" [D, LOG15:15]); last saved checkpoint at step 90,001; best test MSE 0.08427 at step 37,501 [N, NB02#c9; C, `-t 48:00:00`]. Its folder is not in the backup.
- GPU: started 2026-03-13 19:17; about 11.3–11.8 steps/s up to step ~1,100, 1.45 steps/s at step 1,600, then 1.15–1.5 s per step from step 2,500 on; step 101,104 after 40 h 09 min; cancelled ("CANCELLED ... DUE to SIGNAL Terminated", not the time limit) on 2026-03-15 at 11:26:55 [R, ARCH/cross_species_ood_scgen_gpu/train_65338587.err; file time of config.yaml]. The slowdown was never explained; LOG15 lists untested guesses [D, LOG15:19-27]. It ran in the `CellOT` env on node holygpu8a22403 [R, same log]; see "Problems" for why it most likely computed on the CPU.
- Test MSE (GPU): 0.2607 at step 0, 0.0908 at step 2,500, then between 0.0820 and 0.0937 up to step 100,000; minimum 0.0820 at step 32,500, saved as `model.pt` on 2026-03-14 07:12 [N, NB02#c11, #c9; R, file time]. The CPU copy stays within 0.008 of it at every step (largest gap 0.0078 at step 87,500) [N, NB02#c11]. LOG15's "model already converged" and "model.pt at step 32,500 ... is ready" [D, LOG15:27, :31, :162] are better read as "flat after 2,500 steps; the minimum at 32,500 is single-batch noise" [I].
- The dependent CellOT job 65338591 was cancelled too [D, LOG15:36]. Its output folder `results/cross_species_ood_cellot_gpu/` exists, is empty, and was last changed at 11:29:43 on 03-15, three minutes after the cancellation [R, listing of fasrc:BK/cellot/cellot_gpu/results/cross_species_ood_cellot_gpu/]. The scGen prediction (shift of mean codes) was never scored: the shift is computed only after the last step [C, CODE/cellot/train/train.py:250-252], and the autoencoder's folder has no `evals_*` [R]. Its card still says `running` [D, fasrc:BK/docs/model_cards/gpu__cross_species_ood_scgen_gpu.md].

### 4. 2026-03-15 afternoon: the `race`
Three identical code-space CellOT jobs (10,000 steps) went to three Slurm partitions to compare speed [C, fasrc:BK/sbatch/train/racing_cellot/*.sbatch; D, LOG15:117-131].

| run | partition | job | what happened | speed | best training MMD (step) |
|---|---|---|---|---|---|
| `race_cpu` | `shared` (CPU) | 66178858 | 14:13 → 14:24, finished | 19.63 steps/s; 8 min 29 s | 0.018975 (8,750) |
| `race_gpu_requeue` | `gpu_requeue` (A100 requested) | 66178859 | started ≈17:18–17:20; preempted at step 3,754 (17:22:48) and again at 17:26:02, before training resumed; restarted ≈18:05; resumed from step 3,000; finished 18:11:56 | 23.56 steps/s; 2 min 37 s + 4 min 57 s of training | 0.017632 (6,250) |
| `race_gpu` | `gpu` (A100) | 66178861 | no output found | — | — |

Sources: [R, ARCH/race_cpu/train_66178858.err, ARCH/race_gpu_requeue/train_66178859.err, file times of the run folders, cache/ and config.yaml]; `--constraint=a100` [C, fasrc:BK/sbatch/train/racing_cellot/cellot_gpu_requeue.sbatch:9]; best MMD and "not yet available" for `race_gpu` [N, NB02#c16, #c18]; no `race_gpu` folder in the backup [R].
- Training MMD fell from ≈0.074–0.076 at step 0 to ≈0.02 after ~4,000 steps in both runs [N, cellot_race_mmd.png]. For two samples of one distribution this estimator gives at most ≈2/128 = 0.0156 at n = 128, and less in a 50-d code space, where nearby cells have non-zero kernel values. So both runs end somewhat above the same-distribution level on in-distribution test cells; by how much is not known [I].
- Same config and code, and training sets no seed [C, CODE/cellot/train/train.py]. The best values differ by 0.0013 and occur at different steps: a rough size for run-to-run noise in this number [I].
- The `gpu_requeue` job was 1.2× faster per step but started ≈3 h after the CPU job (consecutive job IDs, so submitted together) and was preempted twice [I, job IDs and file times]. It most likely never used its GPU (see "Problems"), so the 1.2× is a difference between nodes, not a GPU speed-up [I]. LOG15's "use shared (CPU)" and its explanation (GPU transfer overhead) were written while both GPU jobs were pending [D, LOG15:103-107, :128-131]; the later numbers do not test that explanation.
- LOG15's "15x speedup from dimensionality reduction" (19.6 vs 1.3 steps/s) is right as arithmetic, but it compares 6,619 inputs with 50, not 1,000 with 50 [D, LOG15:133-134; I].

### 5. 2026-03-15 evening: scoring on held-out rat (only `race_cpu`)
- Code space (job 66195099, 17:14–17:24): finished; `evals.csv` has 450 rows [R, ARCH/race_cpu/eval_66195099.out; ARCH/race_cpu/evals_ood_latent_space/evals.csv].
- Gene space (job 66195100): wrote a 113,208,715-byte `imputed.h5ad` of decoded predictions at 17:18 (size fits ≈4,200 cells × 6,619 genes as 32-bit floats), reached draw 13 of 50, and was killed at its 1-hour limit at 18:14:16 [R, ARCH/race_cpu/eval_ds_66195100.out, .err, file sizes; C, `-t 1:00:00` in the saved script; I for the cell count]. No `evals.csv`. A likely cause is the 6,619 × 6,619 gene-correlation matrix computed for every draw [I]. It was not retried [I, no later file].
- The script for this job, as saved now, runs `--where latent_space`, while its header describes `--where data_space --embedding ae` [C, fasrc:BK/sbatch/eval/eval_cellot_50dim_ood_dataspace.sbatch:5, :29; file time 2026-05-15]. The March job wrote into `evals_ood_data_space`, so the March version differed [I].

Code-space results, rat `ood` half, mean ± SD over 10 draws [R, ARCH/race_cpu/evals_ood_latent_space/evals.csv; the same values are printed in N, NB03#c3, #c12]:

| n cells | MMD | r2-means (Pearson r) | r² (squared) | enrichment-k50 | enrichment-k100 |
|---:|---:|---:|---:|---:|---:|
| 100 | 0.2320 ± 0.0051 | 0.8431 ± 0.0052 | 0.711 | 0.9966 ± 0.0035 | 0.9571 ± 0.0133 |
| 250 | 0.2212 ± 0.0040 | 0.8461 ± 0.0021 | 0.716 | 0.9995 ± 0.0005 | 0.9982 ± 0.0011 |
| 500 | 0.2164 ± 0.0026 | 0.8456 ± 0.0017 | 0.715 | 0.9998 ± 0.0003 | 0.9996 ± 0.0004 |
| 1000 | 0.2154 ± 0.0018 | 0.8457 ± 0.0009 | 0.715 | 0.9996 ± 0.0003 | 0.9995 ± 0.0004 |
| 1500 | 0.2159 ± 0.0013 | 0.8457 ± 0.0010 | 0.715 | 0.9997 ± 0.0002 | 0.9996 ± 0.0002 |

At n = 1500 also: r2-stds 0.815 ± 0.008, r2-pairwise_feat_corrs 0.740 ± 0.005, l2-means 19.42 ± 0.05, l2-stds 2.06 ± 0.03 [R, same file]. The run card's "R² 0.7152, MMD 0.2159" are the n = 1500 values with r squared [D, conny:docs/experiments/gpu__race_cpu.md; C, readers.py].

Reading the numbers [I]:
- Enrichment is the share of a predicted cell's 50 or 100 nearest neighbours (among predicted plus real cells) that are also predicted. Mixed clouds give ≈0.5, separate clouds ≈1.0. Here it is ≥ 0.998 for n ≥ 250: in code space the predicted rat `LPS6` cells form their own cloud [C, CODE/cellot/utils/evaluate.py:16-46 for the definition]. NB03's own guide reads ~1.0 as "poor mixing", but its first sentence says the opposite ("Values near 1.0 mean predicted and treated cells are well-mixed") [D, NB03#c6, markdown].
- r = 0.846 is a correlation over only 50 code coordinates; a few coordinates with large means can drive it. It is not the gene-level r² of the scGen or CellOT papers.
- MMD 0.216 has no reference: no no-transport (identity) score, no scGen-shift score, no i.i.d.-trained model, no self-MMD floor. It is also not comparable with the training value 0.019 (other bandwidths, other cells, other n). Its fall from 0.232 (n = 100) to 0.216 (n = 1,500) is consistent with the shrinking offset of the biased estimator, which is at most 2/n (0.020 at n = 100, 0.0013 at n = 1,500).
- NB03's "Key Takeaways" cell is still the empty template [D, NB03#c13, markdown]. No written conclusion about prediction quality was found from March (looked in LOG15, the 03-22 log, NB02, NB03).

### 6. How the input size is known (6,619 genes, not 1,000)
`model.pt` stores the weights and Adam's two running averages per weight, i.e. 12 bytes per parameter [C, CODE/cellot/train/train.py:47-53, :176-180].

| checkpoint | observed bytes [R] | expected with 6,619 genes [I] | expected with 1,000 genes [I] |
|---|---:|---:|---:|
| ARCH/cross_species_ood/cache/model.pt (CellOT on genes) | 41,151,983 | 41,128,608 + overhead | 6,470,616 + overhead |
| ARCH/cross_species_ood_scgen_gpu/cache/model.pt (AE) | 88,355,126 | 88,344,732 + overhead | 19,231,032 + overhead |
| ARCH/race_cpu/cache/model.pt (CellOT on 50 codes) | 634,543 | 611,016 + overhead (50 inputs) | — |

The two CellOT files carry nearly the same overhead (23,375 and 23,527 bytes), as they should for the same layer structure [I]. So both models called "1000-dim" had 6,619 inputs [I].

### 7. After 2026-03-15
- 03-16: `eval_cellot_1000dim_ood.sbatch` and `eval_cellot_50dim_ood.sbatch` were last written at the same second, 10:55:22, after the 03-15 job that used the 50-dim one [R, file times], which suggests a copy or move rather than an edit [I]; no new outputs found. NB02's outputs were saved after 18:11 on 03-15 (they show the finished GPU race), NB03's after 17:24; both were committed to Josh's repo on 03-24 [N; G, josh@ddc56ad].
- 03-18: the earliest mouse/human atlas run found (`speciesot_cpu`): human → mouse, broad T-cell holdout, its own autoencoder (5,000 steps) and CellOT (10,000 steps) [C, fasrc:BK/cellot/cellot_gpu/results/speciesot_cpu/*/config.yaml, file times 03-18 09:36 and 09:48; C, fasrc:BK/sbatch/train/train_scgen_speciesot_cpu.sbatch]. The CellOT budget is within LOG15's advice (10,000–25,000); the autoencoder budget is below it (LOG15 advised 25,000–50,000) [D, LOG15:162-169]. → F06.
- 03-22: the meeting notes never mention LPS. "Reversed training, we should use mouse to predict human" is about the 03-18 atlas run [D, conny:logs/research_logs/research_log_2026-03-22.txt:34; research_log_2026-03-30.txt:21]. CD8 and monocyte holdouts are atlas topics too [D, 03-22 log:19-24].
- 2026-06-13: the runs were moved to `_archive/`; the LPS task came back as the paper-faithful replication (1,000 HVG, 250k steps) → F11 [D, ARCH/README.md; research_log_2026-06-13.txt].

## Verdict
The record supports:
- The CellOT code ran on this data end to end in code space: train the autoencoder, train CellOT, encode rat, score [R].
- The autoencoder's test MSE is flat after ~2,500 steps [N].
- For CellOT on 50 codes a CPU job is fast enough: 10,000 steps in 8.5 min [R]. The `gpu_requeue` job was 1.2× faster per step, waited ≈3 h and was preempted twice [R]; but it most likely ran on its node's CPU, so this is not a GPU result [I].
- One CellOT model (10k steps, one run) gave rat `LPS6` predictions whose mean code correlates with the real one (r 0.846) but whose cells do not mix with real rat `LPS6` cells (enrichment ≈1.0) [R].

It does not support:
- Any claim that CellOT predicts the rat response well, or better than scGen: no baseline was scored and no gene-space number exists.
- Any raw-genes vs code-space comparison: no rat score of the raw model survives, and its training MMD is stuck at the estimator's floor.
- Any comparison with Bunne Fig. 4f: 6,619 vs 1,000 genes, 10k vs 250k steps, code-space vs gene-space metrics.
- Any CPU-vs-GPU conclusion (LOG15's "GPU is unnecessary for these model sizes" [D, LOG15:171-172]): no log shows a GPU in use, and the env could not run CUDA kernels on A100s (see "Problems").

Strength: weak. This was a pipeline shake-down and a partition-speed benchmark (which most likely never used a GPU), not a comparison.

Leads from earlier surveys, checked:
- "unst → LPS6, rat held out; raw 1000-d vs scGen latent for `race_*`": true, except the raw inputs had 6,619 genes.
- "scGen converged by step 32.5k": the best checkpoint is at 32,500, but the curve is flat from 2,500.
- "race_cpu latent R2 0.715, MMD 0.216 (research_log_2026-03-15)": partly false. The numbers are right, but they are not in that log; they come from the run card, which squares a Pearson r over 50 codes.
- "The concept note describes these runs as raw mouse → human": confirmed; it is wrong on direction, space and gene count.
- "03-15 log: CellOT on LPS works": the log says training is fast; it reports no prediction quality.
- "03-22 log: flip to mouse → human": true, but the flip is from the 03-18 human → mouse atlas run, not from LPS.
- "'the three model variants' says paper-original CellOT was never run": confirmed, and contradicted by these runs (and F11).
- "No Slurm accounting for March": consistent; all job facts here come from file names, logs and file times.

## Why it stopped
- Stated reason: none. LOG15 ends with "Next: evaluate the trained CellOT model on the held-out rat" and an open question about training the autoencoder with rat [D, LOG15:174-181]. The next log (03-22) is only about the atlas [D].
- What the record suggests [I]:
  - LPS was step 1 of a plan whose step 2 was the project's own data (to-do list of 03-04).
  - The goal was always mouse → human: the proposal (start 2026-02-23) names mouse and human atlases and Mooney-lab data [D, mac:OptimalTransport/Junyi_HDS_Independent_Study_Project_Proposal_2025-26.docx]; the 03-30 log says "Goal: Transport gene expression across species (mouse → human)" [D, research_log_2026-03-30.txt:5].
  - Atlas data work ran in parallel (josh@953e669, 03-16, `Human_Mouse_Data.ipynb`), and the earliest atlas run found started 03-18 [G, C].
  - The one failed job (gene-space scoring) hit a 1-hour limit and was not retried.
  - The May semester report mentions only atlas work [D, mac:OptimalTransport/Junyi_HDS_Independent_Study_End_of_Semester_Report.docx].

## Problems in how it was done
- Wrong feature space in every March write-up and in the later concept notes. LOG15, NB02, NB03, the eval scripts, the concept note and `conceptual_framework.md` call the raw run "1000-dim" or "1000 HVG"; the input had 6,619 genes. The runs therefore do not match the paper's setup, and the "15x" and "1.6M" figures are mislabelled. [D, LOG15:6, :45, :90; NB02#c22; NB03#c0; eval_cellot_1000dim_ood.sbatch:2; `conny:docs/concepts/CellOT legacy crossspecies.md`:13, :21; conny:docs/conceptual_framework.md:127, :132 vs N, I above]
- Docs contradict the configs. The concept note says "mouse→human … with no scGen autoencoder in the loop" and that these runs avoid the `AE round-trip tax` (repo term: error added by encoding and decoding) [D, CellOT legacy crossspecies.md:13-25]; the configs say `unst → LPS6`, and both `race_*` configs set `ae_emb` [C, ARCH/race_*/config.yaml]. `conceptual_framework.md` says "We have never used CellOT in this paper-original framing" and `the three model variants.md` "never run here" [D, conceptual_framework.md:39; the three model variants.md:17]; these runs are that framing (control → stimulated) [C].
- The "GPU" runs most likely never used a GPU. Every March job ran in the `CellOT` env [R, env paths in all March .err logs; C, `mamba activate CellOT` in every sbatch]. Its torch is 1.11.0+cu102, installed 2026-03-05 [R, FASRC file /n/home01/jzhou1125/.conda/envs/CellOT/lib/python3.9/site-packages/torch/version.py and its dist-info file time]. The repo later recorded that this build supports GPUs only up to compute capability sm_70, and that jobs landing on A100 or newer cards die with "no kernel image is available for execution on the device" [D, conny:speciesOT/hub/spec.py:484-488; conny:docs/hub_handoff.md:229]. `race_gpu_requeue` requested an A100 (`--constraint=a100`) [C], and the autoencoder job ran on node holygpu8a22403 of the `gpu` partition (A100 per LOG15:111 [D]). Yet the race job ran to completion and the autoencoder job ran 101,104 steps, with no CUDA warning or error in either log [R]. So they most likely computed on the node's CPU [I]. This undermines the race's purpose and LOG15's GPU explanation and advice [D, LOG15:100-107, :171-172]. It also fits LOG15's observation that the CPU and "GPU" autoencoders ended at the same ~1.5 s per step [D, LOG15:22-23].
- LOG15 misdescribes the setup: "human" instead of rabbit, an 80/20 split instead of 500 per group, "~1.6M"/"~31k" parameters instead of 7.36M/50.9k [D vs C, N, I].
- Checkpoints chosen on one batch. Both models keep the step with the lowest score on one random 128-cell test batch [C]. For the autoencoder the minimum is noise in a flat band; for the raw CellOT model the score sits at the floor, so the saved model is effectively arbitrary [I].
- The training MMD is uninformative in 6,619 dimensions: ≈0.016 at step 0 and at step 100,000 [N, I]. LOG15 noticed the two training MMDs are not comparable [D, LOG15:138], not that the raw one is meaningless.
- No baselines or reference values: no identity, scGen-shift, i.i.d.-mode or floor scores [R: one evals.csv in the whole family]. MMD 0.216 and r 0.846 cannot be judged.
- Biased MMD in the evaluation too. The evaluation MMD includes each set's self-similarity terms, so it is positive for identical distributions and shrinks with n; the paper describes an unbiased estimate [C, CODE/cellot/losses/mmd.py:5-10; P, CellOT Online Methods "Metrics"]. Without a same-distribution (floor) score, 0.216 cannot be split into real difference and estimator offset [I].
- Scored only in code space, with an encoder that never saw rat; agreement there says nothing about genes, and the gene-space job timed out [R].
- The planned raw-vs-code comparison never happened: no score of the raw model was found, and NB03 lists it as "NOT READY YET" [N, NB03#c1].
- One training run, no seed, and unseeded evaluation draws [C]. The two race trainings show the training metric moving by ~0.001 between identical runs [N].
- Short training: the only scored model ran 10k steps vs 250k in the paper [C, P]; the 10k budget was picked for a speed race and then became the only result.
- One map for pooled species with different species mixes in source and target (pig 34% vs 24%) [I]; inherited from CellOT's task config, but it lets the map move cells across species.
- Lost and drifted artifacts: the CPU tree `cellot/cellot/` (CPU autoencoder, original raw-run folder, any raw-run scoring) is not in the backup [R]; the gene-space eval script was edited after use and now contradicts its header [C]; `results/model-scgen` still points to the moved autoencoder folder, so `evaluate.py` will not find it from the archive [I].
- The hub inventory is wrong four times: it calls the archived raw run a "GPU re-run" (same run), attributes the raw run to `train_cellot_ood*.sbatch` (those train on codes), says `speciesot_cpu` "borrowed this checkpoint" (its `model-scgen` points to its own `speciesot_scgen`), and lists Josh's 2025 `perturbOT_tutorial.ipynb`, which uses random toy data, as the raw run's notebook [D, conny:scripts/build_experiments_inventory.py:273-304; R, symlink fasrc:BK/cellot/cellot_gpu/results/speciesot_cpu/model-scgen; C, josh@main:perturbOT_tutorial.ipynb#c2].

## Terms used here
- `unst` / `LPS6`: unstimulated cells / LPS-stimulated cells (the 6 presumably means 6 h [I]); source and target of the map.
- `toggle_ood`, `mode: ood`: CellOT's split; the holdout species goes 50/50 into `ignore` (discarded) and `ood` (scored); other cells go to `train` / `test`.
- `test_size: 500`: 500 cells per species×condition group go to `test`.
- `ae_emb`: config key naming a trained autoencoder; CellOT then trains on its 50-d codes.
- `model-scgen`: symlink `evaluate.py` uses to find the autoencoder (`results/model-scgen → cross_species_ood_scgen_gpu`).
- `scgen` (model name): in the vendored CellOT code, a plain autoencoder with β = 0.
- `cross_species_ood`: the CellOT run on all 6,619 genes ("1000-dim" in March write-ups).
- `race_*`: the 2026-03-15 "racing experiment": one 10k-step code-space CellOT job per partition (`shared`, `gpu_requeue`, `gpu`).
- `gpu_requeue`: FASRC partition whose jobs can be preempted (stopped) and restarted.
- `evals_ood_latent_space` / `evals_ood_data_space`: output folders of `evaluate.py --setting ood --where latent_space / data_space`.
- `r2-means`: unsquared Pearson r of mean vectors; the hub cards square it and call it R².
- `enrichment-k50` / `-k100`: share of a predicted cell's 50 / 100 nearest neighbours that are predicted; 0.5 = mixed, 1.0 = separate.
- `cellot_legacy`, `legacy_crossspecies`, framing `legacy`: hub labels given to these runs in May–June [C, conny:speciesOT/hub/resolve.py:33, :39-56, :91, :97-106; G, file first committed 2026-05-28].
- `device: cuda`: a key in every archived config; it was copied from the model configs and does not show that a GPU was used.
- `IMPACT`: later project name for CellOT on autoencoder codes with species as the condition; the archive README applies it to `race_cpu` anyway [D, ARCH/README.md].

## What the package needs from this
No run here is a scientific reference; for LPS use the June replication (F11). Four small checks are possible:
1. Split counts (exact).
   - Input: fasrc:BK/cellot/cellot_gpu/datasets/scrna-crossspecies/hvg-top1k-train-only.6619-backup.h5ad (209,165,300 bytes [R]; sha256 26e42d9fc06f3fde2321a7859cb9b58e16cb17d60d4cb6a53db07f4ae964727c [R, conny:offline_data_manifest.txt:5]).
   - Config: `datasplit` block of ARCH/race_cpu/config.yaml; source `unst`, target `LPS6`.
   - Expected: group sizes as in the Data table [N]; train 41,270, test 3,000, ignore 8,922, ood 8,922 [I].
   - Tolerance: exact. Caveat: these are derived; the March split was never saved, so confirm once with the vendored CellOT split function before freezing them.
2. Autoencoder convergence band.
   - Input: same file and split; config ARCH/cross_species_ood_scgen_gpu/config.yaml (5k–10k steps are enough).
   - Expected: single-batch test MSE ≈0.26 at step 0, 0.088–0.091 at step 2,500, then within 0.082–0.094 [N, NB02#c11, two runs].
   - Tolerance: about ±0.008, the largest gap between the two copies ("CPU" and "GPU", most likely both computed on CPUs) at the same step [N]. Each value is the MSE of one random 128-cell batch, so compare bands, not single steps.
3. MMD-floor guard.
   - Input: two disjoint random sets of 128 cells from one group (e.g. mouse `LPS6`) in the 6,619-gene matrix; biased MMD with γ = 2, 1, 0.5, 0.1, 0.01, 0.005 (CODE/cellot/losses/mmd.py:114-125).
   - Expected: ≈0.0156 (= 2/128) [I]; the raw run's training scores sat between ≈0.0158 and ≈0.017, apart from two early spikes at steps 250 and 500 [N, NB02#c13 and cellot_previous_run.png].
   - Use: the package should warn about, or avoid, an MMD that cannot tell distributions apart.
4. Re-score the saved checkpoints (evaluation path only).
   - Inputs: ARCH/race_cpu/config.yaml, ARCH/race_cpu/cache/model.pt, ARCH/cross_species_ood_scgen_gpu/{config.yaml, cache/model.pt}, the file above.
   - Expected, code space, n = 1500, 10 draws: MMD 0.2159 ± 0.0013, r2-means 0.8457 ± 0.0010, enrichment-k50 0.9997 ± 0.0002 [R].
   - Tolerance: ±0.003 for MMD and ±0.002 for r (about two SDs of single draws; generous for a 10-draw mean, whose standard error is ≈0.0004 for MMD) [I]. Valid only for this checkpoint; training is unseeded and only one model was ever scored, so there is no retraining tolerance.
   - To match, the package must use the vendored estimators: biased MMD over 50 bandwidths np.logspace(1, −3, 50), unsquared Pearson r for `r2-means`, and kNN enrichment as in CODE/cellot/utils/evaluate.py:16-46 [C].

## Open questions
- Was the raw-gene model ever scored on rat? Not found (looked in ARCH/cross_species_ood/, NB03 outputs, all sbatch scripts; its output path was in the deleted CPU tree).
- Which script launched the raw run? Not found (none of the surviving train sbatch scripts writes to `cross_species_ood/`).
- What do the saved decoded predictions (ARCH/race_cpu/evals_ood_data_space/imputed.h5ad, 113 MB) score in gene space? Never computed.
- Did `race_gpu` (job 66178861) ever run? No output found.
- Which device did the "GPU" jobs actually use? No log names it; most likely the CPU (see "Problems").
- Why did the "GPU" autoencoder slow from ~11.5 to ~0.7 steps/s between steps ~1,200 and ~2,500? Never tested. If both copies ran on CPUs, it is a CPU effect.
- `ARCH/race_cpu/evals_ood_data_space/` was created at 16:57:49 on 03-15, about 17 min before both eval jobs started. Was there an earlier data-space attempt? No log of one survives [R, folder time].
- Was the i.i.d. within-mouse task (`crossspecies.yaml`, `subset: species: mouse`) ever run? Its config had already been edited by 03-10 (`target: LPS6`, `device: cuda`, a CPU-tree data path), so a run was at least prepared [C, fasrc:BK/cellot/cellot_gpu/configs/tasks/.ipynb_checkpoints/crossspecies-checkpoint.yaml]. The June notebook points to `results/cross_species/evals_iid_data_space/imputed.h5ad` [C, explore_LPS_dataset.ipynb#c19]; no such folder in the backup.
- Does the CellOT authors' processed file differ from scGen's `train_species.h5ad` beyond the 1,000-gene cut? Unknown; never downloaded.
- LOG15's design question (train the autoencoder with rat) was not tested in March; check whether F11 answered it.

## Sources
- conny:logs/research_logs/research_log_2026-03-15.txt · research_log_2026-03-22.txt · research_log_2026-03-30.txt (lines 1-60) · research_log_2026-06-13.txt
- conny:docs/experiments/gpu__cross_species_ood.md · gpu__cross_species_ood_scgen_gpu.md · gpu__race_cpu.md · gpu__race_gpu_requeue.md · _experiments_index.md
- `conny:docs/concepts/CellOT legacy crossspecies.md` · the three model variants.md · IMPACT_CellOT.md · scGen.md · OOD vs IID evaluation.md
- conny:docs/conceptual_framework.md (§1.1, §2.1, §3) · conny:docs/hub_usage.md:46 · conny:docs/local_offline_handoff.md:58-61 · conny:offline_bundle/README.md · conny:offline_data_manifest.txt · conny:docs/archaeology/inventory.csv
- conny:cellot/cellot_gpu/configs/tasks/{crossspecies-ood, crossspecies, sciplex3-ood, lupuspatients-ood}.yaml · configs/models/{scgen, cellot}.yaml
- conny:cellot/cellot_gpu/cellot/data/cell.py · cellot/train/train.py · cellot/models/ae.py · cellot/networks/icnns.py · cellot/losses/mmd.py · cellot/utils/evaluate.py · cellot/utils/loaders.py · scripts/evaluate.py · configs/models/{cellot, scgen}.yaml
- conny:cellot/cellot_gpu/explore_LPS_dataset.ipynb · conny:cellot/cellot_gpu/paper_crossspecies/scripts/prep_data.py
- conny:speciesOT/hub/resolve.py · conny:speciesOT/hub/readers.py · conny:scripts/build_experiments_inventory.py · conny:speciesOT/hub/spec.py:484-488 · conny:docs/hub_handoff.md:229 · conny:logs/research_logs/research_log_2026-07-30_env_modernization.txt:21 · conny:AGENTS.md:22
- conny:speciesOT/baseline/analysis/archive/00_data_exploration.ipynb · conny:speciesOT/baseline/analysis/{cellot_previous_run, cellot_race_mmd, cellot_embedding_comparison, scgen_eval_loss, ood_distributional_metrics}.png · conny@c342331:archive/old_notes/cellot_cell_py_cpu_vs_gpu.diff
- josh@cellot:baseline/analysis/00_data_exploration.ipynb · 02_scgen_training_analysis.ipynb · 03_cellot_evaluation_analysis.ipynb · josh@main:perturbOT_tutorial.ipynb
- josh@e86c1df:prediction/data_examination.ipynb · josh@953e669:prediction/data_examination.ipynb · josh@953e669 · josh@6f964c6 · josh@ddc56ad · josh@1db1592 (commit file lists)
- fasrc:BK/cellot/cellot_gpu/results/_archive/scrna_crossspecies_pre_paper/README.md · {cross_species_ood, cross_species_ood_scgen_gpu, race_cpu, race_gpu_requeue}/config.yaml · train_*.out · train_*.err (the two >5 MB logs read on FASRC: head, tail, sampled lines) · race_cpu/eval_66195099.{out,err} · race_cpu/eval_ds_66195100.{out,err} · race_cpu/evals_ood_latent_space/evals.csv · listings with sizes and times of */cache/ and race_cpu/evals_*/
- fasrc:BK/cellot/cellot_gpu/results/model-scgen (symlink) · fasrc:BK/cellot/cellot_gpu/results/cross_species_ood_cellot_gpu/ (listing) · fasrc:BK/cellot/cellot_gpu/results/speciesot_cpu/ (configs, model-scgen symlink) · fasrc:BK/cellot/cellot_gpu/results/ and _archive/ (listings) · fasrc:BK/cellot/cellot_gpu/datasets/scrna-crossspecies/ (listing) · fasrc:BK/offline_bundle/ (listing) · fasrc:BK/cellot/ (listing)
- fasrc:BK/cellot/cellot_gpu/configs/tasks/.ipynb_checkpoints/{crossspecies-ood, crossspecies}-checkpoint.yaml · configs/models/.ipynb_checkpoints/{cellot, scgen}-checkpoint.yaml · cellot/train/.ipynb_checkpoints/train-checkpoint.py · scripts/.ipynb_checkpoints/evaluate-checkpoint.py · scripts/submit/.ipynb_checkpoints/iid-checkpoint.sh
- FASRC outside BK: /n/home01/jzhou1125/.conda/envs/CellOT/lib/python3.9/site-packages/torch/version.py and torch-1.11.0.dist-info (file time)
- fasrc:BK/docs/model_cards/gpu__cross_species_ood.md · gpu__cross_species_ood_scgen_gpu.md · gpu__race_cpu.md · gpu__race_gpu_requeue.md · INDEX.md
- fasrc:BK/sbatch/train/racing_cellot/{cellot_cpu_shared, cellot_gpu_requeue, cellot_gpu}.sbatch · fasrc:BK/sbatch/train/{train_cellot_ood, train_cellot_ood_gpu, train_cellot_ood_gpu_requeue, train_scgen_ood, train_scgen_ood_gpu, train_scgen_speciesot_cpu, train_cellot_speciesot_cpu}.sbatch · fasrc:BK/sbatch/eval/{eval_cellot_50dim_ood, eval_cellot_50dim_ood_dataspace, eval_cellot_1000dim_ood}.sbatch (all with file times) · search of fasrc:BK/sbatch/ for `results/cross_species_ood`
- mac:OptimalTransport/CellOT/cellot/ (clone of bunnech/cellot at 522d2b9; only requirements.txt is modified: configs/tasks/crossspecies-ood.yaml, crossspecies.yaml, configs/models/cellot.yaml, scgen.yaml; cellot/data/cell.py:252-341 (original split); scripts/evaluate.py:75) · mac:OptimalTransport/CellOT/datasets/ (listing) · mac:OptimalTransport/Junyi_HDS_Independent_Study_Project_Proposal_2025-26.docx · mac:OptimalTransport/Junyi_HDS_Independent_Study_End_of_Semester_Report.docx
- [P] CellOT (Bunne et al. 2023): section "CellOT reconstructs innate immune responses across species"; Fig. 4 caption; Extended Data Fig. 4; Online Methods "Single-cell RNA sequencing data", "Training and technical details" (incl. "Hyperparameters"), "Metrics", "Feature selection". [P] scGen (Lotfollahi et al. 2019), via the verified facts.

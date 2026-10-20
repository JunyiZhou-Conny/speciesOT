# Reference experiments: what the package should reproduce

The package (`src/speciesot`) is judged by whether it can reproduce earlier
experiments. This page turns that into concrete tests: inputs, recipe,
expected numbers and a tolerance that the record supports. Every number is
taken from a family page, where its source file is cited. The tests are
ordered from "no model needed" to "retrain".

Most old results cannot serve as tests: they are single unseeded runs, on data
that was later fixed, scored with metrics that varied
([critique.md](critique.md)). The tests below are the ones that can.

## Before any test: what the package must be able to compute

Most of the numbers below cannot be matched with the package's current
metrics. The exceptions are R0.1, R4.4 and the R3 counts. `R2Evaluation`
correlates paired cells, and `MMDEvaluation` uses one bandwidth on full
clouds ([metrics.md](metrics.md) §1–2,
[F18](experiments/F18-oop-package.md)). The tests need:

- **R² of mean expression**: Pearson r between the mean vectors of two cell
  sets, squared. Keep r available too, because `evals.csv` stores r. Say
  whether squaring happens before or after averaging over draws:
  notebook 10 and the hub cards differ by up to 0.0014 on this
  ([F07](experiments/F07-toggle-iid-ood-and-renorm.md)).
- **Biased RBF MMD** averaged over `np.logspace(1, -3, 50)`, on subsamples of
  n cells (usually 30, 50, 80), 10 draws, `numpy.random.default_rng(0)`.
  Exact matches also need the old draw order
  (`conny:cellot/cellot_gpu/cellot/losses/mmd.py:13-91`).
- **Floor and ceiling** in the same frame and at the same n
  ([metrics.md](metrics.md) §3).
- **A record per result** of the frame, gene set, n, number of draws and
  seeds.
- **The pinned ortholog table**:
  `conny@c342331:scripts/.biomart_ortholog_cache.csv`, 14,451 one-to-one
  pairs. It was removed from git on 2026-05-25. A four-column copy with the
  same rows is
  `fasrc:BK/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/gene_lists/pre_hvg_one2one_orthologs.csv`
  ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md),
  [F17](experiments/F17-bcg-application.md)).

Copy these inputs to a safe place first. They exist in only one location
([sources.md](sources.md)):

- Josh's BCG files under `fasrc:JOSH/tb/data/` (not in the backup);
- the Stage 1 prediction files, on the Mac only
  (`mac:scGen v.s. CellOT/results/stage1/`);
- the late-July ablation scripts, uncommitted on FASRC.

## Recommended first five

| # | test | why first |
|---|---|---|
| 1 | [R1.1](#r11-bcg-do-nothing-baseline-e24-files) BCG do-nothing baseline | It uses exactly the files and the `IdentityModel` already in the package's test config. No model or training is needed. |
| 2 | [R0.2](#tier-0-unit-tests-synthetic-or-small-data) biased-MMD floor | Pins the MMD estimator before anything depends on it. |
| 3 | [R1.2](#r12-lps-do-nothing-baselines) LPS do-nothing baselines | Pure arithmetic on one public file; it pins the R² definition. |
| 4 | [R3.4](#tier-3-data-preparation-and-splits-exact-counts) split counts | Pins `TrainingData`'s split against the hub's `toggle_ood`. |
| 5 | [R2.1](#r21-decoded-frame-scorer-m1-v08-impact) decoded-frame scorer | Reproduces the project's headline metric from saved files. |

## Tier 0: unit tests (synthetic or small data)

| id | test | expected | source |
|---|---|---|---|
| R0.1 | MMD of a cloud with itself | exactly 0 | existing test `josh@0ba4158:src/speciesot/Tests/test_evaluation.py:14-22` |
| R0.2 | MMD between two disjoint halves of one cloud | positive, ≈ (2/n)(1 − mean kernel). Real reference, M2 v07 human cells, seed 0: 0.063726 / 0.038505 / 0.023722 at n = 30 / 50 / 80 | [F10](experiments/F10-monocytes-floor-ceiling-and-v08.md) test 2 (`fasrc:BK/cellot/cellot_gpu/results/hvg_pearson_residuals_m2_ood/impact_cellot/evals_ood_data_space/mmd_floor.csv`) |
| R0.3 | a full-rank PCA mean shift equals the gene-space mean shift | the two prediction matrices agree within rtol 1e-7 / atol 1e-8 (`autoresearch:ae_study/linear_baselines.py:118-126`). Their raw fgc values then agree to about 5e-7: 0.2291176 vs 0.2291181 at 2,000 genes | [F13](experiments/F13-autoresearch-loop.md) test 3 |
| R0.4 | if a paired-cell metric is kept, it refuses unequal cell counts, swapped axes and sparse input | raises an error | [F18](experiments/F18-oop-package.md) test 2 (`ai_package@src:tests/test_r2_fail_closed.py`) |

## Tier 1: do-nothing baselines (real data, no model)

### R1.1 BCG do-nothing baseline (e24 files)

- Inputs: mouse treated `fasrc:JOSH/tb/data/mouse_bcg/bcg_treated_scanvi_081826.h5ad`
  (251 cells) as the "prediction"; human treated
  `fasrc:JOSH/tb/data/human_bcg/bcg_treated_scanvi_082626.h5ad` (392) as the
  truth; human untreated `…/bcg_control_scanvi_082626.h5ad` (230).
- Recipe (tb4):
  - strip Ensembl version suffixes;
  - from `layers['counts']`: normalize to 10,000 per cell, then log1p;
  - keep the 1,000 shared genes;
  - squared Pearson r of the mean profiles;
  - top-100 = the genes with the largest |human treated − untreated| difference.
- Expected:

  | comparison | all 1,000 genes | top 100 |
  |---|---|---|
  | mouse treated, unchanged (identity) | 0.628441 | 0.181901 |
  | human untreated vs human treated | 0.970376 | 0.977887 |

- Tolerance: about 1e-6 (no sampling).
- Details: [F17](experiments/F17-bcg-application.md) test 1,
  [F18](experiments/F18-oop-package.md) test 1. The package's test config
  already pairs these files with `IdentityModel`
  (`josh@scgen-model-impl:src/speciesot/Tests/config.yaml:10-12`). Read
  `layers['counts']`, not `.X`.

### R1.2 LPS do-nothing baselines

- Input: `fasrc:BK/scgen-cellot-ablation/data/raw/train_species.h5ad` and the
  split and gene manifests in `ablation:data/manifests/`.
- Expected r² of mean source vs mean target profiles:

  | split | 6,619 genes | 1,000 genes |
  |---|---|---|
  | scGen split | 0.8667375 | 0.6596110 |
  | Bunne OOD half | 0.8661401 | 0.6579674 |

- Tolerance: 1e-6.
- Details: [F12](experiments/F12-scgen-fig5-stage0-and-stage1.md) test 1.

### R1.3 CellOT-paper LPS task, identity on the 50 marker genes

- Input: `fasrc:BK/cellot/cellot_gpu/datasets/scrna-crossspecies/hvg-top1k-train-only.h5ad`.
- Recipe: split `toggle_ood`, holdout rat or mouse, `test_size: 500`, seed 0.
- Expected squared r of means: rat 0.58241, mouse 0.34262.
- Tolerance: float precision. The MMD ceiling and floor values are on the page.
- Details: [F11](experiments/F11-bunne-lps-replication.md) test 1.

### R1.4 v08 floor, ceiling and identity

- Input: `fasrc:BK/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_m{1,2}_v08.h5ad`,
  OOD cells.
- Expected at n = 80:

  | cut | floor | ceiling | `r2_identity` | `r2_self` |
  |---|---|---|---|---|
  | M1 | 0.0236093 | 0.1087470 | 0.5541515 | 0.9917168 |
  | M2 | 0.0232675 | 0.1061868 | 0.5589876 | 0.9924411 |

- Tolerance: 1e-6 with the same draws; otherwise about ±0.003.
- Details: [F14](experiments/F14-july-plans-a-to-d.md) test 1.

## Tier 2: re-score saved predictions (no training)

### R2.1 Decoded-frame scorer, M1 v08 IMPACT

- Inputs:
  - `fasrc:BK/cellot/cellot_gpu/results/hvg_pearson_residuals_m1_v08_ood/impact_cellot/evals_ood_data_space/eval_clouds.npz`
    (183 human, 182 predicted, 182 mouse cells × 1,000 genes);
  - the autoencoder `…/hvg_pearson_residuals_m1_v08_ood/scgen/cache/model.pt`.
- Expected at n = 80:

  | quantity | value |
  |---|---|
  | MMD (model) | 0.103570 |
  | autoencoder floor | 0.080459 |
  | decoded ceiling | 0.305666 |
  | `frac_gap_closed_decoded` | 0.897378 |
  | `r2_model_dec` | 0.92245 |
  | raw floor / raw ceiling | 0.023609 / 0.108747 |
  | `frac_gap_closed` (raw) | 0.0608 |

- Tolerance: 1e-8 with the same random stream; otherwise ±0.0035 MMD and
  ±0.02 on the fraction.
- Two null inputs must also be added:
  - decoded mouse cells must give exactly 0;
  - raw mouse cells give 0.874. This is a known weakness of the metric.
- Details: [F10](experiments/F10-monocytes-floor-ceiling-and-v08.md) test 1,
  [F09](experiments/F09-hub-and-metrics-infrastructure.md) test 1,
  [F16](experiments/F16-deployment-models-and-mixhvg.md) test 1.

### R2.2–R2.7 Other re-scoring tests

| id | what | expected | tolerance | details |
|---|---|---|---|---|
| R2.2 | HVG matrix, pearson_residuals group a OOD, gene space, n = 80 | scGen R² 0.858, MMD 0.1250; IMPACT R² 0.897, MMD 0.1046 | ±0.01 R², ±0.005 MMD | [F08](experiments/F08-hvg-flavor-matrix.md) test 2 |
| R2.3 | CD8 holdout predictions of March 2026. The inputs are in this repo via git LFS (`conny:speciesOT/baseline/results/speciesot_cd8/`), so a fresh clone can run this test without FASRC | r² of means 0.7178 (IMPACT-OR), 0.6488 (cell-type CellOT); MMD (logspace(1,−3,50)) 0.0725 / 0.1013 | ±1e-3 | [F06](experiments/F06-tcell-holdouts-speciesot-v1.md) candidate 1 |
| R2.4 | LPS `raw_shift` with the MMD gap metric, arms A–D | raw fgc / r2_all: A 0.20807 / 0.89607; B 0.33769 / 0.80961; C 0.20594 / 0.90101; D 0.37668 / 0.82773 | 1e-6 with the same draws, else ~0.01 | [F13](experiments/F13-autoresearch-loop.md) test 1 |
| R2.5 | CellOT-paper replication predictions, squared r of means on 50 markers | rat scGen 0.44232, CellOT 0.40352; mouse scGen 0.58024, CellOT 0.45502 | exact | [F11](experiments/F11-bunne-lps-replication.md) test 2 |
| R2.6 | Stage 1 saved predictions (on the Mac only) | B r2_all 0.846455, r_50 0.873902; D r2_all 0.669015, r_50 0.784123 | ~1e-6 | [F12](experiments/F12-scgen-fig5-stage0-and-stage1.md) test 3 |
| R2.7 | Paper-VAE atlas predictions (Plan C), raw frame, n = 80 | M1 MMD 0.129217, R² 0.804537; M2 0.124112, 0.803171 | R² exact, MMD ±0.003 | [F14](experiments/F14-july-plans-a-to-d.md) test 2 |

## Tier 3: data preparation and splits (exact counts)

| id | what | expected | details |
|---|---|---|---|
| R3.1 | Josh's ontology matcher, donors in count order, seed 0 | 312 matched pairs (mouse [0] × human [0]); 381 (donors [1]) | [F03](experiments/F03-labels-ontology-and-distances.md) test 1 |
| R3.2 | Capped atlas prep from raw counts | 14,451 orthologs; 6,495 + 6,495 matched cells; 1,000 HVGs | [F07](experiments/F07-toggle-iid-ood-and-renorm.md) test 4, [F08](experiments/F08-hvg-flavor-matrix.md) test 1 |
| R3.3 | `toggle_ood` on the April toggle files | scored `ood` half: 195 cells (T1), 506 (M2) | [F07](experiments/F07-toggle-iid-ood-and-renorm.md) test 1 |
| R3.4 | `toggle_ood` on v08 files (`test_size` 0.2, seed 0, stratified by condition) | uncapped CD8: train 35,210, test 8,800, ignore 435, ood 435 per species. M1 v08: train 2,927 / 2,927, test 735 / 735, ignore 183 mouse / 182 human, ood 182 / 183 | [F16](experiments/F16-deployment-models-and-mixhvg.md) test 2, [F10](experiments/F10-monocytes-floor-ceiling-and-v08.md) test 3 |
| R3.5 | Backed prep of the uncapped CD8 v08 cut (needs the 51 GB atlases) | after the assay filter 245,389 mouse / 1,025,717 human cells; 44,880 pairs; 89,760 × 1,000 | [F09](experiments/F09-hub-and-metrics-infrastructure.md) test 4 |
| R3.6 | LPS split rebuild, seed 0 | 52,691 / 44,270 training cells and 4,210 / 4,712 scored OOD cells; manifests byte-identical | [F12](experiments/F12-scgen-fig5-stage0-and-stage1.md) test 2 |
| R3.7 | Gene-axis guard: the `atlas_full` gene list vs the uncapped v08 axis | 721 shared genes, so the package must refuse to mix them | [F16](experiments/F16-deployment-models-and-mixhvg.md) test 3 |
| R3.8 | Spec → config for m1 v08 | the hyperparameters and split block of the saved configs, compared as parsed values | [F09](experiments/F09-hub-and-metrics-infrastructure.md) test 2 |

## Tier 4: load saved models and predict (needs model code)

| id | what | expected | details |
|---|---|---|---|
| R4.1 | Paper scGen frozen checkpoint (TensorFlow 1, env `scgen_tf1`) on LPS rat | two-path r2_all 0.906739 ± 3e-6, top-100 R² 0.742302 ± 1e-6; average-delta r2_all 0.85633 | [F12](experiments/F12-scgen-fig5-stage0-and-stage1.md) test 4a |
| R4.2 | CellOT-autoencoder checkpoints of the autoresearch reruns, arms A–D | r2_all 0.8824042, 0.8183062, 0.6618999, 0.6210565 (±1e-5) | [F12](experiments/F12-scgen-fig5-stage0-and-stage1.md) test 3 |
| R4.3 | Forward pass of the `uncapped_v08_iid` deployment models on BCG control cells | reproduces the saved `bcg_ctrl_081826_predicted_human_via_{scgen,impact_cellot}_…h5ad` (387 × 1,000) | [F17](experiments/F17-bcg-application.md) test 2 |
| R4.4 | `R2Evaluation` as a reconstruction metric on the frozen LPS checkpoint | paired Pearson² 0.08618 over 4,673 genes; shuffled rows 0.0001 | [F15](experiments/F15-ae-repair-rounds-and-calibration.md) test 1 |
| R4.5 | First LPS CellOT checkpoint, code space, n = 1,500, 10 draws | MMD 0.2159 ± 0.003, r 0.8457 ± 0.002 | [F05](experiments/F05-first-cellot-runs-on-lps.md) test 4 |

## Tier 5: retrain (stochastic)

Retraining tolerances come only from the few reruns on record. Run several
seeds and test their mean.

| id | what | pass rule | details |
|---|---|---|---|
| R5.1 | Paper scGen at the paper settings (100-d latent, 2 × 800, dropout 0.2, KL 5e-5, 300 epochs, batch 32), rat LPS6 held out | r2_all in [0.88, 0.93] and above identity 0.8667; top-100 R² within ±0.06 of 0.742 | [F12](experiments/F12-scgen-fig5-stage0-and-stage1.md) test 4b |
| R5.2 | CellOT-autoencoder scGen, arms A–D | r2_all A 0.897 / 0.882, B 0.846 / 0.818, C 0.654 / 0.662, D 0.669 / 0.621, ±0.05. Structural: A − C ≥ 0.15, B − D ≥ 0.15, C below its identity 0.866 | [F12](experiments/F12-scgen-fig5-stage0-and-stage1.md) test 5 |
| R5.3 | The same autoencoder on arm B, 50k iterations | r2_all 0.834 ± 0.03 | [F13](experiments/F13-autoresearch-loop.md) test 4 |
| R5.4 | v08 benchmark retrain, scGen-style and IMPACT | fgc_dec IMPACT 0.897 (M1) / 0.776 (M2), scGen-style 0.588 / 0.575. No noise estimate exists; establish one with ≥ 3 seeds first | [F14](experiments/F14-july-plans-a-to-d.md) test 3, [F10](experiments/F10-monocytes-floor-ceiling-and-v08.md) |

## Not worth reproducing

- Josh's OT pairing experiments as numbers. They are single unseeded runs,
  some with failed solvers. If the package adds a pairing module, keep the
  synthetic GW swap test, the convergence guard, and the e14 ortholog-OT
  result (0.9014, which reproduced exactly across two sessions)
  ([F01](experiments/F01-gw-feasibility-and-simulations.md)–[F04](experiments/F04-gene-priors-and-standard-ot.md)).
- The speciesot_v1 and toggle retrains, which ran on stale data with leakage
  ([F06](experiments/F06-tcell-holdouts-speciesot-v1.md),
  [F07](experiments/F07-toggle-iid-ood-and-renorm.md)).
- The full HVG matrix and the mixhvg ablation
  ([F08](experiments/F08-hvg-flavor-matrix.md),
  [F16](experiments/F16-deployment-models-and-mixhvg.md)).
- Any scorecard ranking ([F09](experiments/F09-hub-and-metrics-infrastructure.md)).
- The autoencoder-repair variants, the 6,619-gene sweeps and the single ICNN
  run ([F13](experiments/F13-autoresearch-loop.md),
  [F15](experiments/F15-ae-repair-rounds-and-calibration.md)).
- Unbalanced OT, whose outputs are lost
  ([F14](experiments/F14-july-plans-a-to-d.md)).
- BCG model quality ([F17](experiments/F17-bcg-application.md)). A future BCG
  test should report both trivial baselines on the same cells and in the same
  frame, and score the predicted *change*, not only the treated profile.

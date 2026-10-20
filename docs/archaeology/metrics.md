# Metrics: what each number means, as the code computes it

The project used the same few names (R², MMD, `frac_gap_closed`) for several
different computations. Two numbers with the same name can differ because one
is squared and the other is not, or because they were computed on different
sample sizes, in a different space, or against a different reference. This page
lists every variant found in the code, so that:

- old numbers can be read correctly, and
- the package can choose one definition per metric and say which historical
  numbers it is meant to reproduce.

Evidence labels: [C] code, [P] paper, [R] result file, [D] doc or log (see
[README](README.md)). Citation prefixes are defined in [sources.md](sources.md).

## Notation

- **control**: the cells a model starts from (mouse cells, or unstimulated
  cells in the LPS task). In code this is also called *source*.
- **treated**: the real cells the model should reproduce (human cells, or
  LPS-stimulated cells). Also called *target*.
- **imputed**: the model's prediction for the treated cells.
- **μ(X)**: the mean expression vector of a group of cells, one number per gene.
- **Frame** (or space): where a comparison happens.
  - *raw*: gene expression as stored in the `.h5ad` file.
  - *latent*: the autoencoder's internal code, usually 50 numbers per cell.
  - *decoded*: the autoencoder's reconstruction of gene expression,
    `decode(encode(x))`.

## 1. Agreement of mean expression ("R²")

All of these compare one number per gene, not per cell, except the two
reconstruction-style rows, which are marked.

| name in code or paper | where | what is computed | squared? |
|---|---|---|---|
| R² (scGen paper) | Lotfollahi 2019, Methods [P] | Pearson r between μ(imputed) and μ(treated) over all genes, and over the top-100 differentially expressed genes (DEGs), then squared. Error bars come from 100 resamples of 80% of cells. | yes |
| r² feature means (CellOT paper) | Bunne 2023, Methods [P] | "correlation of the means of the observed and predicted distributions" over all ~1000 genes | the paper says r²; the code below is not squared |
| `r2-means` in `evals.csv` | `conny:cellot/cellot_gpu/scripts/evaluate.py:73` [C] | `pd.Series.corr(μ(treated), μ(imputed))` | **no: it is r, despite the name** |
| hub R² | `conny:speciesOT/hub/readers.py:45`, `:86-88` [C] | squares the `r2-*` rows of `evals.csv`; the headline is taken at the largest `ncells` with `nfeatures = all`, averaged over reps | yes |
| `r2_all` (autoresearch) | `autoresearch:run_one_experiment.py:271-272` [C] | Pearson r of μ over all genes, squared | yes |
| `r_50` (autoresearch) | `autoresearch:run_one_experiment.py:274-292` [C] | Pearson r of μ over the top-50 DEGs. DEGs come from ranks stored in the data file, computed on all pooled cells (`ablation:scripts/02_prepare_data.py:32-42`). A rat-only Wilcoxon test (LPS6 vs unstimulated) is the fallback, used for the 6,619-gene arms. | **no** |
| `r2_model_dec` | `conny:cellot/cellot_gpu/scripts/decoded_frame_metrics.py:136` [C] | corr²(μ(imputed), μ(decode(encode(treated)))) | yes. Note: the reference is the autoencoder's *reconstruction* of the target, not the target itself. |
| `r2_identity_dec`, `r2_self_dec` | same file `:134-135` [C] | the same quantity for decoded control vs decoded treated, and for two random halves of decoded treated | yes |
| per-gene paired Pearson², COD (reconstruction) | `fasrc:BK/scgen-cellot-ablation/scripts/stage0_metric_helpers.py:42-66` [C] | per gene, across **paired** cells (a cell and its own reconstruction); COD = 1 − SS_res/SS_tot | per cell pair, not per gene mean |
| `R2Evaluation` (the new package) | `conny:src/speciesot/speciesot_core.py:115-126`; `josh@scgen-model-impl:src/speciesot/speciesot_core.py:305-316` [C] | mean over genes of the per-gene Pearson² between `predicted.X` and `truth.X`, **across cells taken in row order** | per cell pair |

Things to know when reading these numbers:

- **r vs r².** Values in raw `evals.csv` files are r. Everything the hub,
  autoresearch, the Stage 0 code and the scGen paper call R² is r². An
  r-vs-r² mix-up once made a model look better than it was (research log
  2026-04-08 [D]; see [F06](experiments/F06-tcell-holdouts-speciesot-v1.md)).
- **Correlation of means is high even for "do nothing".** On the LPS task,
  leaving control cells unchanged already scores about 0.87 on all 6,619
  genes (0.66 on 1,000 HVGs); on BCG, human
  untreated vs human treated scores 0.97 (see
  [F12](experiments/F12-scgen-fig5-stage0-and-stage1.md) and
  [F17](experiments/F17-bcg-application.md)). An R² is only meaningful next to
  the identity baseline computed on the same cells.
- **The package's `R2Evaluation` measures something else.** It pairs
  predicted cell *i* with real cell *i*. Mouse-to-human predictions have no
  such pairing, and the two clouds usually have different numbers of cells. So
  it does not reproduce any historical R², and on unequal cell counts it fails.
  It is a reconstruction-style metric, closest to the Stage 0 identity checks
  (see [F18](experiments/F18-oop-package.md)).

## 2. MMD

MMD (maximum mean discrepancy) measures how different two clouds of cells are
as whole distributions. It looks at more than their means. With a Gaussian
(RBF) kernel k(x, y) = exp(−γ‖x − y‖²):

MMD²(P, Q) = E[k(x, x′)] + E[k(y, y′)] − 2 E[k(x, y)], with x, x′ ~ P and
y, y′ ~ Q.

### The estimator is biased

Every implementation in this project computes
`xx.mean() + yy.mean() − 2·xy.mean()` on the full kernel matrices
(`conny:cellot/cellot_gpu/cellot/losses/mmd.py:5-10`;
`autoresearch:honest_metrics.py:66`; the package's `MMDEvaluation`) [C].

The `xx` and `yy` averages include each cell compared with itself, where
k = 1. This "V-statistic" is therefore positive even when both samples come
from the same distribution. The excess shrinks roughly like 1/n as the sample
size n grows. The CellOT paper says it reports an "unbiased estimate" [P]; the
code does not.

Consequences:

- An MMD value means nothing without its n. Comparing MMDs computed at
  different n compares sample sizes as much as models.
- A perfect model cannot reach 0. This is why the project built a "floor" (§3).

### Settings that change the number

| setting | variants found |
|---|---|
| bandwidth γ | average over 50 values `np.logspace(1, -3, 50)`, i.e. γ from 10 down to 0.001 (`evaluate.py:63`, all floor/ceiling scripts) · 50 values `np.logspace(-3, 3, 50)` in notebook 06, which produced the F06 MMDs (`conny:speciesOT/baseline/analysis/06_cd8_holdout_evaluation.ipynb#c9`) · six values `[2, 1, 0.5, 0.1, 0.01, 0.005]` (`compute_scalar_mmd`, `mmd.py:114-116`) · a single γ = 0.1 (the package's `MMDEvaluation`, `josh@scgen-model-impl:src/speciesot/speciesot_core.py:320-335`) [C] |
| sample size | `evaluate.py` default n_cells 100, 250, 500, 1000, 1500 with 10 reps (`evaluate.py:20-23`) [C]. Job scripts (some written before the hub existed) passed different lists to different runs, even inside one experiment matrix: `30,50,80` (66 job scripts), `30,80,200,300` (46), `20,30,40` (34), `30,40,80` (16), `10,20,30` (8), `50,80` (4), `25,50,80` (2) (counted over `fasrc:BK/sbatch/`) [C]. Some notebooks used the full cloud with no subsampling ([F07](experiments/F07-toggle-iid-ood-and-renorm.md)). The `evals.csv` draws are not seeded. |
| genes | the CellOT paper uses the top-50 marker genes [P]. `evaluate.py` uses all features, but only when there are at most 1000 (`:78`). `--n_markers` instead sets the list of gene sets to score: marker counts, optionally with `all` [C] |
| frame | raw genes, latent (50-d), or decoded |

Example of why this matters: in the five-flavor HVG matrix of May 2026, the
largest n depends on the holdout group: 80 for group a, 300 for b and c, 40
for d. All five flavors share it within a group. The hub reports MMD "at the
largest ncells" (`readers.py:86-88`), so its headline MMDs are not comparable
across groups. Comparisons between models or flavors *within* one group used
the same n ([F08](experiments/F08-hvg-flavor-matrix.md)).

## 3. Floor, ceiling and `frac_gap_closed`

These were added in this repo on 2026-06-09 to make MMD interpretable: the
floor/ceiling helpers and `extended_metrics.py` in `conny@8a9a103`, and
`decoded_frame_metrics.py` in `conny@7c178c5`. The idea: compare a model's MMD to the best value it could
possibly get (the *floor*) and to what doing nothing gets (the *ceiling*).

```
frac_gap_closed = (ceiling − model) / (ceiling − floor)
```

A score of 1 means the model is as close to the real target as the target is
to itself. A score of 0 means no better than doing nothing. A negative score
means worse than doing nothing.

| variant | model | floor | ceiling | code |
|---|---|---|---|---|
| raw (`frac_gap_closed`) | MMD(imputed, treated) | MMD between two disjoint random draws of n treated cells | MMD(control, treated) | `conny:cellot/cellot_gpu/scripts/extended_metrics.py:4-10, 136, 175` [C] |
| decoded (`frac_gap_closed_decoded`) | MMD(imputed, treated) | MMD(decode(encode(treated)), treated) | MMD(decode(encode(control)), treated) | `conny:cellot/cellot_gpu/scripts/decoded_frame_metrics.py:8-17, 129-145` [C] |
| latent (`frac_gap_closed_latent`) | the same, in the 50-d code | | | `autoresearch:honest_metrics.py:340` [C] |
| R² analogue (`frac_r2_closed_decoded`) | r2_model_dec | r2_self_dec | r2_identity_dec | `decoded_frame_metrics.py:137-138` [C] |

All of these use `compute_mmd_two_sample` with the same 50 bandwidths, n
usually 30, 50 and 80, and 10 reps (`mmd.py:13-91`) [C]. The latent variant and
the sidecar scripts set n themselves; it is not always the eval's n.

Why there are two main variants:

- An autoencoder-based model outputs *decoded* cells, and decoding is never
  perfect. In the raw variant the floor is the target compared with itself,
  with no decoding. A model that passes its output through the decoder
  therefore cannot get near that floor, and the raw score often comes out
  negative even for a reasonable model. The repo calls this the
  "AE round-trip tax" (`conny:docs/concepts/AE round-trip tax.md` [D]).
- The decoded variant puts the floor at "what a perfect transport would score
  through this autoencoder".

Known problems with these scores (details and evidence in
[F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)):

- The decoded score is relative to *this autoencoder*. Two models with
  different autoencoders have different floors, so their decoded scores are not
  directly comparable. The repo's own `conceptual_framework.md` §5.9 says so
  [D], while `AGENTS.md` tells agents to rank models on it.
- It can exceed 1: the model's output can sit closer to the target than the
  autoencoder's reconstruction of the target does. The top scorecard entry is
  1.032 ([F16](experiments/F16-deployment-models-and-mixhvg.md)).
- When ceiling − floor is small, the ratio is unstable. On the LPS task the
  denominator was about 0.02, against about 0.22 on the atlas [D].
- `r2_model_dec` rewards matching the autoencoder's reconstruction of the
  target, including its errors, not the target itself.
- Always report model, floor and ceiling next to the fraction. From late July
  the repo's own rule is to also quote model/floor (`model_over_floor`).
  `conceptual_framework.md` added it on 2026-07-27, committed in
  `conny@fe856aa` [D].

## 4. Other metrics that appear

| metric | what it is | code |
|---|---|---|
| `mean_js` | per-gene Jensen–Shannon divergence between the treated and imputed marginal distributions (histograms, 50 bins), averaged over genes | `conny:cellot/cellot_gpu/cellot/losses/divergence.py:29` [C] |
| `l2-means`, `l2-stds` | Euclidean distance between mean vectors, or between per-gene standard-deviation vectors | `evaluate.py` [C] |
| `r2-stds`, `r2-pairwise_feat_corrs` | correlation of per-gene standard deviations; correlation of gene–gene correlation matrices (both unsquared) | `evaluate.py` [C] |
| `enrichment-k50`, `-k100` | share of a predicted cell's 50 or 100 nearest neighbours that are also predicted cells. 0.5 means well mixed with the real cells; 1.0 means fully separate, so higher is worse | `evaluate.py` [C] |
| AE identity panel | MSE, paired-cell Pearson² per gene, COD per gene, mean-vector Pearson², per-cell Pearson r | `conny:cellot/cellot_gpu/scripts/ae_identity_metrics.py`; `stage0_metric_helpers.py` [C] |
| cell-pairing accuracy | share of cells whose OT partner (argmax of the transport plan) has the same cell-type label | Josh's notebooks ([F01](experiments/F01-gw-feasibility-and-simulations.md)–[F04](experiments/F04-gene-priors-and-standard-ot.md)) |
| kBET, kNN purity | kBET scores batch mixing; kNN purity scores how well cell labels are kept. Both were used to judge batch correction | `josh@main:e22_batch_correction.ipynb` ([F17](experiments/F17-bcg-application.md)) |

## 5. What this means for the package

These are decisions for Conny and Josh, not things this archaeology changed.

1. **R².** To reproduce historical numbers, the package needs the squared
   Pearson r of mean vectors, on all genes and on a stated top-K DEG set (with
   the DEG method stated). The identity baseline must be computed on the same
   cells. The current `R2Evaluation` is a different, paired-cell metric. If it
   is kept, it should get a different name and be used only where cells really
   are paired, e.g. autoencoder reconstruction.
2. **MMD.** Fix and record the estimator, the bandwidth grid, n, the number of
   reps, the gene set and the frame. To compare with old hub numbers that means
   the biased estimator, `np.logspace(1, -3, 50)`, n in {30, 50, 80}, 10 reps,
   all genes. A single-γ full-cloud MMD reproduces none of the old numbers.
3. **`frac_gap_closed`.** Compute floor and ceiling in the same frame and at
   the same n as the model, and store all three numbers, not only the ratio.
4. **Never compare across code paths** without converting first (r vs r²;
   subsampled vs full-cloud MMD; raw vs latent vs decoded).

[`reference_experiments.md`](reference_experiments.md) lists which concrete
numbers the package should be able to reproduce, and with which of these
definitions.

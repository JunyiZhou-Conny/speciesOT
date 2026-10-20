# Models: what each name means, and which version was used where

The project's model names are overloaded. "scGen" alone refers to at least four
different programs, and "CellOT" to one architecture used in four different
framings. This page pins each name to code, hyperparameters, and the experiment
families that used it. It also lists which existing library could provide each
model for the new package.

Evidence labels: [C] code or config, [P] paper, [R] result file, [D] doc or
log. Citation prefixes are in [sources.md](sources.md).

## Short answers

- **Is CellOT's "scGen" the scGen of the scGen paper?** No.
  - **Paper scGen** is a variational autoencoder (VAE). The authors trained it
    with a very small KL weight (α = 5e-5), a 100-d latent, two layers of 800
    units with batch normalization and dropout 0.2, for 300 epochs [C]. The paper
    computes δ after balancing cell types [P]. In the cross-species Fig. 5 run,
    each δ is a single-species mean over equal-size subsets, with no
    cell-type balancing [C].
  - **CellOT's "scgen"** is a plain (deterministic) autoencoder with no KL term.
    It has a 50-d latent and two layers of 512 units (256 in most hub runs), and
    its δ is a plain difference of means [C].
  - The CellOT authors say the VAE part barely matters because the KL weight is
    tiny in practice [P]. The authors' own α = 5e-5 supports that. But width,
    latent size, normalization, dropout and training length all differ as
    well.
- **Does the difference matter here?** On the scGen-paper split with 6,619
  genes, the two reach similar mean-expression R²:
  - paper scGen (TensorFlow): r2_all 0.907, against 0.910 reported in the
    paper (`fasrc:BK/scgen-cellot-ablation/results/stage0/metrics.json`) [R];
  - CellOT's autoencoder scGen (arm A): 0.897
    (`fasrc:BK/scgen-cellot-ablation/results/stage1/ablation_grid.csv`) [R].

  On the genes that respond to LPS, the autoencoder is weaker: top-100 DEG R²
  0.642 vs 0.694–0.742 for two VAE trainings. On CellOT's out-of-distribution
  split (arm C), CellOT's scGen falls to 0.654, because rat cells are then
  fully absent from training. Paper scGen was never run on that split, so
  whether the model choice matters there is unknown. This is the missing cell
  of the comparison ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md)).
- **R² hides a distribution problem.** Paper scGen's prediction gets the mean
  right: 0.907, against 0.867 for doing nothing. But its MMD to the real LPS
  rat cells is 0.201, while the unstimulated rat cells themselves are only
  0.045 away. So as a *distribution*, the prediction is further from the
  truth than the input was (same `metrics.json`, `fig5_two_path`) [R].

## The model zoo

| name used in the repo | what it actually is | implementation | used in |
|---|---|---|---|
| identity, "do nothing", `r2_identity`, ceiling | predict that the target looks like the source | — | used as a baseline from June on ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)–[F17](experiments/F17-bcg-application.md)), and in Stage 0. Missing in F05–F08 and in the Stage 1 grid ([critique.md](critique.md) §1) |
| scGen (paper) | VAE + latent mean shift, TensorFlow 1 `VAEArith` | theislab code at `fasrc:BK/scgen-cellot-ablation/scgen-reproducibility/code/scgen/models/_vae.py`; env `scgen_tf1` | Stage 0 and the late-July repair study ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md), [F15](experiments/F15-ae-repair-rounds-and-calibration.md)) |
| atlas paper-VAE, "Plan C" | the same `VAEArith` with paper settings, trained on the atlas cuts | `conny:atlas-paper-vae/` | [F14](experiments/F14-july-plans-a-to-d.md) |
| `scgen` 2.x, `SCGEN` | the maintained scvi-tools (PyTorch) rewrite of scGen | pip `scgen` (2.1.1 in env `analysis`) | the AI-built package ([F18](experiments/F18-oop-package.md)); pinned in `requirements.txt` on branch `scgen-model-impl` (added in `josh@3eb6555`); no experiment used it |
| hub "scgen", Stage 1 arms, autoresearch base | CellOT's deterministic `AutoEncoder` + latent mean shift | `conny:cellot/cellot_gpu/cellot/models/ae.py:90-188`, `transport.py:61-70` | [F05](experiments/F05-first-cellot-runs-on-lps.md)–[F16](experiments/F16-deployment-models-and-mixhvg.md), [F17](experiments/F17-bcg-application.md) |
| `scGenModel` (package) | a stub that calls the TensorFlow 1 `VAEArith` API, while the pinned library has only `SCGEN` | `josh@scgen-model-impl:src/speciesot/speciesot_core.py` | [F18](experiments/F18-oop-package.md) |
| CellOT | input-convex neural network (ICNN) optimal transport map | `conny:cellot/cellot_gpu/cellot/models/cellot.py`, `transport.py:54` | see the framings below |
| IMPACT_CellOT, IMPACT-OR, `impact_cellot`, `impact_or`, `swapped_cellot` (renorm runs) | CellOT trained mouse → human inside a frozen scGen autoencoder's latent space; predictions are decoded. What "IMPACT" stands for is not recorded. | hub configs with `data.ae_emb` | [F06](experiments/F06-tcell-holdouts-speciesot-v1.md)–[F17](experiments/F17-bcg-application.md) |
| cell-type CellOT; folders `cellot/` and `speciesot_cellot_swapped/` (speciesot_v1), `cellot/` (toggle), `normal_cellot/` (renorm) | CellOT from non-held-out to held-out cell types (T cells; monocytes in the toggle runs) | — | [F06](experiments/F06-tcell-holdouts-speciesot-v1.md), [F07](experiments/F07-toggle-iid-ood-and-renorm.md); abandoned |
| `raw_shift` | add the mean difference in gene space; no autoencoder | autoresearch | [F13](experiments/F13-autoresearch-loop.md) |
| Gaussian / Bures OT | linear OT map between Gaussians fitted to each cloud | autoresearch | [F13](experiments/F13-autoresearch-loop.md) |
| unbalanced OT "Option A" | reweight cells, then a balanced ICNN | `conny:scgen-cellot-unbalanced/` | [F14](experiments/F14-july-plans-a-to-d.md); real run lost |
| GW, entropic GW, FGW, OTDD, AGW, EMD, Sinkhorn, PerturbOT | OT methods for *matching* cells across species. They are not translators: they pair cells, they do not predict new expression. | POT, ott-jax, `otdd`, Josh's `speciesot_helpers.py` | [F01](experiments/F01-gw-feasibility-and-simulations.md)–[F04](experiments/F04-gene-priors-and-standard-ot.md) |
| scVI, scANVI, Symphony, ratio | batch correction / reference mapping of the BCG data onto the atlas | scvi-tools etc. | [F17](experiments/F17-bcg-application.md) |

## scGen, side by side

| | paper scGen (authors' cross-species run) | `scgen` 2.1.1 defaults | CellOT "scgen" (upstream config) | hub "scgen" (example: `hvg_pearson_residuals_m1_v08_ood`) |
|---|---|---|---|---|
| model type | VAE | VAE | deterministic autoencoder | deterministic autoencoder |
| loss | reconstruction + α·KL | 0.5·reconstruction + 0.5·kl_weight·KL | MSE + β·‖z‖² | same |
| KL / regularizer weight | α = 5e-5 | kl_weight = 5e-5 | β = 0 (no regularizer) | β = 0 |
| hidden layers | 2 × 800, batch norm, leaky ReLU | 2 × 800 | 2 × 512 | 2 × 256 |
| latent size | 100 | 100 | 50 | 50 |
| dropout | 0.2 | 0.2 | 0 | 0.1 |
| training | 300 epochs, batch 32, Adam lr 1e-3 | — | 250k iterations; batch from the task config (256 for `crossspecies`) | 50k iterations, batch 256, Adam lr 1e-3 |
| δ (the shift) | in the paper's method, mean latent difference after up-sampling cell types and down-sampling the larger condition [P]. In the cross-species Fig. 5 run, single-species means over equal-size subsets, with no cell-type balancing (`fasrc:BK/scgen-cellot-ablation/scripts/04_stage0_fig5_eval.py:174-185`) [C] | balanced as in the paper (`predict()` calls `balancer`) | plain mean of codes per label (`compute_scgen_shift`, `ae.py:175-188`) | same |
| cross-species prediction | ½(z_mouse,LPS + δ_species + z_rat,ctrl + δ_LPS), the Fig. 5 "two paths" | — | decode(encode(x) + δ) | decode(encode(x) + δ) |
| source | `fasrc:BK/scgen-cellot-ablation/scripts/run_stage0.sh:27-31`; `…/scgen-reproducibility/code/scgen/models/_vae.py:45-170`; Lotfollahi 2019 [P][C] | `fasrc:/n/home01/jzhou1125/miniforge3/envs/analysis/lib/python3.12/site-packages/scgen/_scgen.py:49-55`, `_scgenvae.py:36-130` [C] | `conny:cellot/cellot_gpu/configs/models/scgen.yaml` [C] | `fasrc:BK/cellot/cellot_gpu/results/hvg_pearson_residuals_m1_v08_ood/scgen/config.yaml` [C] |

Notes:

- Most hub families used the same settings: autoencoder 2 × 256, dropout 0.1,
  50k iterations; CellOT 4 × 64, 50k iterations, batch 128. The exceptions
  are `speciesot_cpu`, the March LPS runs ([F05](experiments/F05-first-cellot-runs-on-lps.md))
  and the paper replication ([F11](experiments/F11-bunne-lps-replication.md)).
  Each family page records its configs.
- The hub computes the shift δ after the last training step with the model
  still in training mode, so dropout is active when δ is computed
  ([F18](experiments/F18-oop-package.md)).
- In the original TensorFlow code, the decoder's second batch-normalization
  call computes a value that is never used (`_vae.py:114`) [C]. This only
  matters if someone re-implements scGen line by line.
- The `scgen` 2.x API is `SCGEN(adata).train()` / `.predict()`. The
  `VAEArith(...)` plus TensorFlow-session style in `scgen-model-impl` belongs
  to the old TensorFlow package and does not exist in the version pinned in
  `requirements.txt` ([F18](experiments/F18-oop-package.md)).

## CellOT, side by side

| | CellOT paper | upstream config (`configs/models/cellot.yaml`) | hub runs (example: m1 v08) | paper replication bundle |
|---|---|---|---|---|
| network | ICNN, 4 hidden layers × 64 | 4 × 64 | 4 × 64 | as the paper |
| optimizer | Adam, lr 1e-4, β₁ = 0.5, β₂ = 0.9 | same | same | same |
| inner loop | f fixed, 10 g-updates per step; λ = 1 | `n_inner_iters: 10`, `fnorm_penalty: 1` | same | same as upstream |
| iterations | 250k ("all models") | **100k** | **50k** | 250k planned; the rat autoencoder was cancelled at step 229,762 ([F11](experiments/F11-bunne-lps-replication.md)) |
| batch | 256 | set by the task config: 256 (`crossspecies.yaml`), 128 (`crossspecies-ood.yaml`) | 128 | 256 |
| space | 50-d latent of the scGen encoder | — | 50-d latent of the hub scGen | 50-d latent of its own autoencoder |
| source | Bunne 2023 Methods [P] | `conny:cellot/cellot_gpu/configs/models/cellot.yaml:4-23` [C] | `fasrc:BK/cellot/cellot_gpu/results/hvg_pearson_residuals_m1_v08_ood/impact_cellot/config.yaml` [C] | `conny:cellot/cellot_gpu/paper_crossspecies/specs/rat_ood.yaml:12-13`, `scripts/setup.py:62-111` [C] |

Across the hub results tree, 58 of 60 `impact_cellot` configs and 78 of 80
`scgen` configs use 50k iterations. That is a fifth of the paper's 250k
(`fasrc:BK/cellot/cellot_gpu/results/*/{impact_cellot,scgen}/config.yaml`,
counted on 2026-10-20) [C]. The remaining two of each are the replication of
the paper's own cross-species task, which used the paper settings
([F11](experiments/F11-bunne-lps-replication.md)).

### What gets transported where ("framings"; three of the four were run)

| framing | source → target | used in |
|---|---|---|
| paper, drug response | control → drug-treated cells, within one dataset | not run: the benchmark datasets were downloaded (`fasrc:BK/cellot/cellot_gpu/datasets/`), but the results tree has no runs on them |
| paper, cross-species LPS | unstimulated → LPS-stimulated (6 h), with rat (or mouse) held out | [F05](experiments/F05-first-cellot-runs-on-lps.md), [F11](experiments/F11-bunne-lps-replication.md) |
| cell-type | non-CD8 → CD8 T cells | [F06](experiments/F06-tcell-holdouts-speciesot-v1.md), [F07](experiments/F07-toggle-iid-ood-and-renorm.md); abandoned |
| IMPACT (species) | mouse → human cells of the same cell types, with some cell types held out | [F06](experiments/F06-tcell-holdouts-speciesot-v1.md) onward; the main line |

The project's end goal combines a species map with a treatment map, for
example mouse untreated → mouse treated → human treated. The four-corner note
lists other routes too. Only the species leg was ever built ([F17](experiments/F17-bcg-application.md);
`conny:docs/concepts/the four-corner goal.md` [D]).

## Reuse map for the package

Options, not decisions:

| model | ready-made source | caveats |
|---|---|---|
| identity | none needed | — |
| paper scGen (VAE) | pip `scgen` 2.x (`SCGEN`) | Not byte-for-byte the TensorFlow model. Paper numbers were reproduced only with the TensorFlow code, in a separate Python 3.7 / TensorFlow 1.15 env. |
| CellOT "scgen" (AE) and CellOT / IMPACT | the vendored `conny:cellot/cellot_gpu/cellot/` | It has a `setup.py`, but the CellOT env's editable install points to a stale path, so it is used via `PYTHONPATH`. It needs torch and the `ml_collections`-style configs. Every hub result was made with it. |
| raw mean shift, Gaussian OT | a few lines of numpy, or POT (`ot`) | — |
| GW-family matching | POT, ott-jax (PerturbOT) | PerturbOT needed jax < 0.6 ([F02](experiments/F02-perturbot.md)) |

[`reference_experiments.md`](reference_experiments.md) says which model and
which settings each reference experiment needs.

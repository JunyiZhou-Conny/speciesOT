# Metric atlas — field reference

Source of truth for formulas: `scgen-cellot-autoresearch/honest_metrics.py`
and `docs/conceptual_framework.md` §5.9.

## Identity (no transport)

| Field | Meaning |
|---|---|
| `recon_train_mse` | Mean squared error `X` vs `decode(encode(X))` on train (or train-like) cells |
| `recon_train_r2_pergene` | Legacy field: mean over genes of paired-cell Pearson²(true, recon) on train; not COD |
| `recon_train_cod_pergene` | Mean over genes of standard `1 − SSE/SST` across paired cells |
| `recon_train_r2_mean_vector` | Pearson² across raw vs reconstructed gene-mean vectors |
| `recon_train_pearson_r_percell` | Mean over cells of Pearson r across each cell's gene profile |
| `recon_target_*` | The same five identity metrics on the evaluation target cloud (e.g. held-out treated) |
| `recon_target_mmd_self` | MMD(decode(encode(target)), target) — AE tax; equals decoded floor when computed the same way |

### Required identity presentation

For every AE/VAE metric atlas, display MSE, paired-cell Pearson²/gene,
COD/gene, mean-vector Pearson², and per-cell Pearson r together for each
available slice. These metrics are complementary:

- MSE/COD evaluate numerical fidelity.
- Paired-cell Pearson²/gene evaluates cell-to-cell tracking within each gene.
- Mean-vector Pearson² evaluates preservation of average programs.
- Per-cell Pearson r evaluates preservation of broad within-cell gene profiles.

Do not describe `recon_*_r2_pergene` as “variance explained”; only COD has the
standard `1 − SSE/SST` interpretation.

### DEG / marker identity fields

When a predefined biological feature set exists, add:

| Field | Meaning |
|---|---|
| `recon_target_deg_r2_pergene` | Mean paired-cell Pearson² across the DEG set |
| `recon_target_deg_cod_pergene` | Mean paired-cell COD across the DEG set |
| `recon_target_deg_r2_mean_vector` | Pearson² across true vs reconstructed DEG mean vectors |
| `r2_top100_degs` | Post-transport predicted-vs-target DEG mean-vector Pearson²; not an identity metric |

Always show the all-other-gene paired-cell Pearson² comparator and label the
feature-set size and selection method.

## Mean / paper-style

| Field | Meaning |
|---|---|
| `r_all` | Pearson r between predicted gene-mean vector and true gene-mean vector |
| `r2_all` / `r2_model` | `r_all²` (or equivalent mean-vector R²) |
| `r2_identity` | Mean-vector R² of source vs target (do nothing) |
| `r2_self` | Split-half reproducibility ceiling of target means |
| `frac_r2_closed` | `(r2_model - r2_identity) / (r2_self - r2_identity)` |
| `frac_r2_closed_decoded` | Same using decoded source/target mean references |

## MMD frames

All use subsampled multi-γ MMD; headline usually `ncells=80`.

| Field | Meaning |
|---|---|
| `mmd_model` | MMD(prediction, target) in gene space |
| `mmd_floor` | Split-half MMD within target (raw irreducible) |
| `mmd_ceiling` | MMD(source, target) (raw do-nothing) |
| `frac_gap_closed` | `(ceiling - model) / (ceiling - floor)` — **diagnostic only** |
| `mmd_ae_recon_floor` | MMD(decode(encode(target)), target) |
| `mmd_decoded_ceiling` | MMD(decode(encode(source)), target) |
| `frac_gap_closed_decoded` | Same frac with decoded floor/ceiling — **north-star** |
| `decoded_denominator` | `mmd_decoded_ceiling - mmd_ae_recon_floor`; report always. Fraction is ill-conditioned when this is below `gap_above_ae_recon` |
| `model_over_floor` | `mmd_model / mmd_ae_recon_floor`; scale-free companion, and the statistic to rank on when the fraction is ill-conditioned |
| `mmd_*_latent` / `frac_gap_closed_latent` | Same idea in encoder latent space |

## Guardrail

| Field | Meaning |
|---|---|
| `mean_js` | Mean over genes of Jensen–Shannon divergence between pred and target marginals (lower better) |

## Common artifact paths

- Paper Stage 0: `scgen-cellot-ablation/results/stage0/metrics.json`
- Autoresearch runs: `scgen-cellot-autoresearch/results/runs/<exp_id>_*/metrics.json`
- Recon sidecar: `scgen-cellot-autoresearch/ae_study/results/recon_sidecar.csv`
- Hub: `./hub show <run_id>`, `./hub metrics <run_id>`, scorecard columns

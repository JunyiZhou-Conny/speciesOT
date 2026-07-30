---
name: metric-atlas-canvas
description: >-
  Builds a Stage-0-style metric atlas Cursor canvas for a scored model or
  prediction variant. Use when the user asks for a metric atlas, metrics canvas,
  Stage-0-style metric table, or after eval/metrics land and they want a
  comparable baseline view of the five-axis AE identity panel + mean-R² +
  raw/decoded/latent MMD + JS.
---

# Metric atlas canvas

Standard presentation for **all scored models** in speciesOT: one canvas that
lists every reported metric with **value · definition · intuition**, matching
the Stage 0 paper-scGen atlas.

## When to run

- User says “metric atlas”, “metrics canvas”, or “Stage 0 style metrics”
- A new `metrics.json`, hub sidecar, or `./hub metrics` result should be reviewed
- Comparing prediction variants (e.g. two-path vs average-δ, baseline vs recipe)

Also read the Cursor canvas skill before writing any `.canvas.tsx`.

## Gold template

Clone structure from:

`~/.cursor/projects/n-holylabs-mooney-lab-Lab-junyizhou-speciesOT/canvases/scgen-fig5-stage0-metrics.canvas.tsx`

Do **not** invent numbers. Pull from artifacts on disk (`metrics.json`,
`experiments.csv`, recon sidecars, `./hub show`, honest_metrics outputs).

## Output location

Write exactly one file:

`~/.cursor/projects/<workspace>/canvases/<slug>-metrics.canvas.tsx`

Slug examples: `scgen-fig5-stage0`, `impact-m1-v08`, `ae-g2000-L800-baseline`.

## Required canvas structure (fixed order)

1. **Title + subtitle** — model family, arch, gene space, holdout/split, seed, headline `ncells`
2. **Callout: paper-native vs project-add-on** — which metrics the external paper (if any) reports vs our harness
3. **Stat strip (4)** — pick the four most decision-relevant scalars (always include north-star if present)
4. **§ Autoencoder identity** — encode→decode only (no transport): the five-metric identity panel below + recon MMD; note missing slices explicitly
5. **§ Mean / paper-style R²** — `r_all`, `r2_all`/`r2_model`, `r2_identity`, `r2_self`, `frac_r2_closed` (+ decoded if available)
6. **§ Raw-frame MMD** — diagnostic only: `mmd_model`, `mmd_floor`, `mmd_ceiling`, `frac_gap_closed`
7. **§ Decoded-frame MMD** — north-star: `mmd_ae_recon_floor`, `mmd_decoded_ceiling`, `frac_gap_closed_decoded`, `frac_r2_closed_decoded`
8. **§ Latent-frame MMD** — if available: `mmd_*_latent`, `frac_gap_closed_latent`
9. **§ Marginal guardrail** — `mean_js`
10. **§ How to read** — 4–6 Q→evidence→answer rows (reproduce paper? identity OK? means improved? cloud improved?)
11. **Source footer** — artifact paths + `honest_metrics.py` / hub script names

Omit a section only if that frame was never computed; never invent placeholders.

## AE identity panel (required when encode→decode exists)

Never present `recon_*_r2_pergene` alone. For each relevant slice (at minimum
train/train-like and evaluation target), jointly show:

1. **MSE** — exact coordinate error over cells × genes
2. **Paired-cell Pearson²/gene** — for each gene, correlation across paired
   input/reconstructed cells, squared; then mean genes
3. **COD/gene** — for each gene, `1 − SSE/SST`; then mean genes
4. **Mean-vector Pearson²** — correlate raw vs reconstructed gene means across genes
5. **Per-cell Pearson r** — within each cell, correlate raw vs reconstructed
   profiles across genes; then mean cells

Also show reconstruction MMD when available. Label the comparison axis in the
table/chart; do not call all five values “R².” A perfect reconstruction gives
MSE=0 and all four correlation/COD metrics=1. Disagreement is diagnostic:
high mean-vector/per-cell values with low per-gene Pearson²/COD means the AE
preserves broad programs while losing cell-specific variation.

### Biologically focused identity extension

If a predefined DEG or marker set exists, the same identity section must also
show, for that feature set:

- mean paired-cell Pearson²/gene (plus the all-other-gene comparator)
- mean-vector Pearson² of raw vs reconstructed expression
- COD/gene when available

Keep these separate from post-transport DEG metrics. For example,
`recon_target_deg_r2_mean_vector` asks whether AE identity preserves DEG means;
`r2_top100_degs` asks whether transport predicts target DEG means. DEG/marker
sets are evaluation slices only and must not leak held-out target information
into training or model selection.

If the artifact lacks one of the five metrics but the checkpoint and paired
round-trip clouds exist, compute a sidecar. If computation is impossible, use
one explicit callout naming the missing metric and reason; never silently omit
it or infer it from another axis.

## Table column contract

Every metric table uses:

| Metric | Value(s) | Definition | Intuition |

When comparing variants, use side-by-side value columns (e.g. Two-path | Average-δ).

Round for display (≈3 decimals for fractions; keep enough digits that rankings don’t tie wrongly).

## Metric semantics (do not reverse)

Gap-closed formula (all MMD frames):

```text
frac = (ceiling - model) / (ceiling - floor)
```

- **1** ≈ as good as floor; **0** ≈ identity/do-nothing; **&lt;0** ≈ worse than identity
- **North-star:** `frac_gap_closed_decoded` (rank / headline)
- **Conditioning check (required):** always report
  `decoded_denominator = mmd_decoded_ceiling - mmd_ae_recon_floor` and
  `model_over_floor = mmd_model / mmd_ae_recon_floor` next to the fraction.
  Two separate failure modes:
  1. *Sensitivity* — a δ change in `mmd_model` moves the fraction by
     `δ / denominator`. With subsampled MMD (δ ≈ 0.005 is ordinary noise), a
     denominator of 0.02 gives ±0.23 of slop; 0.22 gives ±0.02.
  2. *Non-comparability* — the denominator contains the scored model's own AE
     floor, so models with different floors are graded on different-length
     rulers and their fractions must not be ranked against each other.
  When either applies, rank on absolute `mmd_model`, `gap_above_ae_recon`, and
  `model_over_floor`, and say so explicitly.
  Verified 2026-07-27: atlas v08 denominators ~0.16–0.23 (sound); Hagai LPS
  ~0.02–0.05 with floors varying 2× across variants (rank on absolutes there).
  Note `denominator < gap_above_ae_recon` is just `model > ceiling` (worse than
  decoded identity) — an interpretation flag, not a conditioning flag.
- **Guardrails:** `frac_r2_closed_decoded`, `mean_js` (lower JS better)
- **Raw `frac_gap_closed`:** diagnostic only (AE round-trip tax); never rank on it alone
- **`r2_all` / `r2_model`:** R² of **gene-mean vectors** (paper-style) — not per-gene recon r²
- **`recon_*_r2_pergene`:** legacy name for paired-cell Pearson²/gene — not COD and not the paper Fig. 5 score
- **`recon_*_cod_pergene`:** standard coefficient of determination across cells, averaged over genes
- **`recon_*_r2_mean_vector`:** raw-vs-reconstructed gene-mean Pearson²
- **`recon_*_pearson_r_percell`:** raw-vs-reconstructed profile Pearson r, averaged over cells

Definitions detail: [reference.md](reference.md)

## Agent checklist

- [ ] Numbers copied from artifacts (cite paths in footer)
- [ ] Paper vs project metrics labeled
- [ ] AE models show all five identity axes together (or an explicit missing-metric reason)
- [ ] Available DEG/marker sets show focused identity metrics, distinct from transport metrics
- [ ] Decoded north-star called out in Stats + §4
- [ ] Missing metrics stated, not fabricated
- [ ] Imports only from `cursor/canvas`; default-export one component
- [ ] No empty sections / TODO placeholders

## Related repo rules

- North-star policy: repo root `AGENTS.md`
- Science definitions: `docs/conceptual_framework.md` §5.9
- Harness: `scgen-cellot-autoresearch/honest_metrics.py`

---
title: AE round-trip tax
type: concept
tags:
  - concept
  - metric
  - gotcha
source_doc: "conceptual_framework.md §5.9 (AE round-trip)"
---

# AE round-trip tax

The single subtlest gotcha in the metric framework, and the cause of confusing negative
[[frac_gap_closed]] values on [[IMPACT_CellOT]] runs.

## What happens

IMPACT's data-space prediction goes `mouse ──encode──► latent ──transport──► latent'
──decode──► imputed`. So `imputed` lives in **AE-decoded gene space**. But the real human
`treated` cloud is **raw**. The autoencoder ([[scGen]]'s AE) cannot perfectly rebuild
1000-d expression from a 50-d bottleneck, and that distortion is itself an MMD:

```
mmd_ae_recon = MMD(decode(encode(human)), human)  ≈ 0.083   (m1 v08)
```

This "tax" is paid by `mmd_model` but **not** by the raw `mmd_floor`/`mmd_ceiling` — an
apples-to-oranges comparison. Because the raw ceiling (~0.109) sits *below* the model
(~0.11+), [[frac_gap_closed]] goes negative even when transport is doing real work.

## The honest frame (decoded space)

Measure all three clouds in the *same* space:

| reference                | formula                                                     | m1 v08     |
| ------------------------ | ----------------------------------------------------------- | ---------- |
| AE-recon floor           | MMD(decode(encode(treated)), treated)                       | ~0.083     |
| model                    | MMD(imputed = decode(encode(treated) + transport), treated) | ~0.11–0.14 |
| decoded-identity ceiling | MMD(decode(encode(control)), treated)                       | ~0.31      |

With these, m1 v08 IMPACT `frac_gap_closed ≈ 0.91`.

## Consequences

1. Don't panic at negative `frac_gap_closed` on IMPACT until decoded refs land — check
   `frac_r2_closed` (means commute through the AE, so it's trustworthy).
2. The AE is a real ceiling on distributional metrics; even a perfect latent transport
   can't beat `mmd_ae_recon`.
3. **TODO (code):** add `mmd_ae_recon_floor` + `mmd_decoded_ceiling` to
   `extended_metrics.py` so the sidecar is honest by default.

## Related

- The metric it distorts: [[frac_gap_closed]] · [[MMD floor and ceiling]]
- Why R² is immune: means commute through encode/decode.
- The AE itself: [[scGen]]

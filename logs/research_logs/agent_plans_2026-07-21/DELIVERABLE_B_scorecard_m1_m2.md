# Deliverable B — Atlas v08 scoreboard (M2 primary, M1)

**Date:** 2026-07-21  
**Question:** On v08 OOD, does IMPACT_CellOT beat hub scGen AE+shift on `frac_gap_closed_decoded` (ncells=80)?  
**Canvases:** `atlas-m2-v08-metrics.canvas.tsx`, `atlas-m1-v08-metrics.canvas.tsx`  
**Fence → C:** B owns these run_ids; do **not** write under `hvg_pearson_residuals_*_v08_ood/scgen/` or `.../impact_cellot/`.

---

## Decision (one sentence)

**IMPACT wins cleanly** on the decoded north-star for both M2 (0.776 vs 0.575) and M1 (0.897 vs 0.588); hub scGen keeps a slight mean-R² / `frac_r2_closed_decoded` edge; IMPACT has better `mean_js` — **do not reopen AE HPO**.

---

## Inventory (2026-07-21)

| run_id | status | checkpoint | decoded sidecar |
|--------|--------|------------|-----------------|
| `gpu/hvg_pearson_residuals_m2_v08_ood/impact_cellot` | done | `cache/model.pt` | present |
| `gpu/hvg_pearson_residuals_m2_v08_ood/scgen` | done | `cache/model.pt` | present |
| `gpu/hvg_pearson_residuals_m1_v08_ood/impact_cellot` | done | `cache/model.pt` | present |
| `gpu/hvg_pearson_residuals_m1_v08_ood/scgen` | done | `cache/model.pt` | present |

Datasets: `cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_m{1,2}_v08.h5ad`  
Specs: `specs/m2_baseline.yaml`, `specs/m1_modern.yaml`  
Metrics refresh: **not needed** — `extended_metrics.csv` + `decoded_frame_metrics.csv` already on disk (eval dates 2026-06-05); `./hub scorecard` reads them.

Optional recon identity (train/holdout r²/gene): **not on disk** for these runs; §1 of atlases uses shared `mmd_ae_recon_floor` only.

---

## Scorecard snapshot (ncells=80)

From `evals_ood_data_space/{extended,decoded}_metrics.csv` and `./hub scorecard` / `./hub show`.

| Cut | Model | fgc_decoded ★ | fr2_decoded | mean_js ↓ | fgc_raw (diag) | r2_model | hub R² (evals) |
|-----|-------|---------------|-------------|-----------|----------------|----------|----------------|
| **M2** | IMPACT | **0.776** | 0.861 | **0.451** | −0.128 | 0.929 | 0.923 |
| **M2** | scGen AE+shift | 0.575 | **0.906** | 0.485 | −0.675 | **0.949** | 0.944 |
| **M1** | IMPACT | **0.897** | 0.821 | **0.449** | +0.061 | 0.918 | 0.919 |
| **M1** | scGen AE+shift | 0.588 | **0.857** | 0.502 | −0.759 | **0.929** | 0.927 |

Decoded floors/ceilings (shared AE per cut, n=80):

| Cut | mmd_ae_recon_floor | mmd_decoded_ceiling |
|-----|--------------------|---------------------|
| M2 | 0.066 | 0.292 |
| M1 | 0.080 | 0.306 |

Δ north-star (IMPACT − scGen): M2 **+0.201**, M1 **+0.310**.

---

## Guardrail reading

- **Means:** scGen slightly ahead on `frac_r2_closed_decoded` and raw `r2_model` — classic mean≠cloud; does **not** overturn the OT cloud win.
- **JS:** IMPACT lower (better) on both cuts.
- **Raw fgc:** IMPACT still near-zero / negative on M2; ignore for ranking (AE tax).

---

## Handoff

- **→ Mentor:** atlases + decision sentence above; no new training required.
- **→ Plan C:** do not overwrite the four run dirs above; new VAE lives elsewhere.
- **→ Plan D:** if moving unbalanced OT to atlas, freeze the M2 v08 AE at  
  `cellot/cellot_gpu/results/hvg_pearson_residuals_m2_v08_ood/scgen/` (`ae_emb_path` already wired for IMPACT).

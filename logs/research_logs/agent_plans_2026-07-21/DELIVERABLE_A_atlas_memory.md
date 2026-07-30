# Deliverable A — Atlas memory pack (v08 freeze)

**Date:** 2026-07-21  
**Scope:** read-only reconstitution of human–mouse atlas institutional memory  
**Presentation spine:** [`speciesot-journeys-so-far.canvas.tsx`](/n/home01/jzhou1125/.cursor/projects/n-holylabs-mooney-lab-Lab-junyizhou-speciesOT/canvases/speciesot-journeys-so-far.canvas.tsx)  
**Stop 1 appendix canvas:** [`atlas-v08-memory-pack.canvas.tsx`](/n/home01/jzhou1125/.cursor/projects/n-holylabs-mooney-lab-Lab-junyizhou-speciesOT/canvases/atlas-v08-memory-pack.canvas.tsx)  
**Why we left LPS (one line):** mentor synthesis 2026-07-20 — stop ETH Fig.4 lockstep / global G=6619 HPO infinite games; keep metric lessons; return judgment to atlas (`logs/research_logs/research_log_2026-07-20.txt`).

---

## 1. M1 vs M2 (and why M1 ≠ “better” automatically)

| Tag | Holdout CL | Meaning | Spec |
|-----|------------|---------|------|
| **M1** | `CL:0000875` | Non-classical monocyte **alone** | `specs/m1_modern.yaml` → `hvg_pearson_residuals_m1_v08_ood` |
| **M2** | `CL:0000875` + `CL:0000576` | Non-classical + **generic** monocyte | `specs/m2_baseline.yaml` → `hvg_pearson_residuals_m2_v08_ood` |
| **atlas-CD8** | `CL:0000625` | Uncapped full-atlas CD8 (saturated ladder) | `specs/atlas_cd8_uncapped.yaml` → `hvg_pearson_residuals_a_uncapped_v08_ood` |

**IMPACT** = species effect mouse→human with cell-type OOD (train without holdout type; eval on it).  
**Hub scGen (atlas)** = shared PyTorch AE (`beta=0`) + latent mean-shift — **not** Lotfollahi’s TF VAE.

**Why M1 is not automatically “better”:**  
Switching M2→M1 raised gene-mean R² but made **raw** MMD look worse / paradoxical (`20_m1_mmd_investigation.ipynb`). That was not proof that the harder single-type holdout is a cleaner science win — it mixed (i) a small raw mouse–human MMD ceiling on matched lung monocytes, (ii) **AE round-trip tax** charged to imputed but not to raw floor/ceiling, and (iii) **Smart-seq2 / 10x mixing** that created within-species scatter mistaken for biology (`21_data_imbalanced.ipynb`, `conceptual_framework.md` §5.9–5.10). After v08 cleanup, M1 IMPACT is the **clearest OT-vs-mean-shift win on the north-star**; M2 remains the harder **two-population** distributional test (means can look solved while clouds stay muddy).

---

## 2. Prep decisions frozen in v08

Enforced in specs + `hub/prep.py` (`conceptual_framework.md` §5.7, §5.10):

1. **Assay filter:** mouse `chromium_v2`, human `chromium_v3` — **drop Smart-seq2**  
2. **OOD split stratified** by `condition` (species): `datasplit_stratify: condition`  
3. **HVG:** Pearson residuals, top 1000, `hvg_batch_key: species`, log1p  
4. **Seed / eval:** `random_state=0`; headline `ncells=80` (also 30/50 on disk)  
5. **Benchmark tags:** `hvg_pearson_residuals_{m1,m2,a_uncapped}_v08_ood`

**Datasets on disk:**

- `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_m1_v08.h5ad` (32M)  
- `.../hvg_pearson_residuals_m2_v08.h5ad` (32M)  
- `.../hvg_pearson_residuals_a_uncapped_v08.h5ad` (350M)

**Result roots:**

- `.../cellot/cellot_gpu/results/hvg_pearson_residuals_m1_v08_ood/{impact_cellot,scgen}/`  
- `.../hvg_pearson_residuals_m2_v08_ood/{impact_cellot,scgen}/`  
- `.../hvg_pearson_residuals_a_uncapped_v08_ood/{impact_cellot,scgen}/`

---

## 3. What we already believe: IMPACT vs hub AE-scGen on v08

**North-star:** `frac_gap_closed_decoded` (`AGENTS.md`). Guardrails: `frac_r2_closed_decoded`, `mean_js`. Raw `frac_gap_closed` is diagnostic only.

All numbers below: **ncells=80**, from each run’s `evals_ood_data_space/{extended_metrics,decoded_frame_metrics}.csv` (matches `speciesOT/baseline/analysis/v08_scorecard_dual.csv` and `./hub scorecard`).

| Cut | Model | fgc_decoded ★ | fr2_decoded | fgc_raw (diag) | R² (raw means) | mean_js |
|-----|-------|---------------|-------------|----------------|----------------|---------|
| M1 | IMPACT | **0.897** | 0.821 | +0.061 | 0.918 | 0.449 |
| M1 | scGen | 0.588 | 0.857 | −0.759 | 0.929 | 0.502 |
| M2 | IMPACT | **0.776** | 0.861 | −0.128 | 0.929 | 0.451 |
| M2 | scGen | 0.575 | 0.906 | −0.675 | 0.949 | 0.485 |
| CD8 uncapped | IMPACT | **0.935** | 0.846 | −0.247 | 0.926 | 0.451 |
| CD8 uncapped | scGen | 0.596 | 0.853 | (no extended_metrics.csv) | 0.924† | — |

† R² from dual scorecard / hub for CD8 scGen; decoded sidecars present.

**Belief (no new runs):** On the frozen v08 OOD cuts, **IMPACT beats hub AE-scGen on decoded MMD gap-closed** for M1, M2, and CD8. Hub scGen often wins or ties **mean** R² / `frac_r2_closed_decoded` (classic mean≠cloud). M1 IMPACT’s v07→v08 cleanup moved raw `frac_gap_closed` from **−0.71 → +0.06** and decoded north-star to **~0.90** (`v08_scorecard_dual.csv`, notebook 22).

---

## 4. Why raw MMD lied on M1 (plain language)

Two stacked artifacts made “M1 IMPACT looks worse than identity on MMD” a bad headline:

1. **AE round-trip tax.** Imputed cells are `decode(transport(encode(mouse)))`. Raw floor/ceiling compare against **raw** human. The AE alone costs ~0.08 MMD on M1 v08 (`mmd_ae_recon_floor≈0.080` at n=80). That tax is charged to the model but not to raw references → raw `frac_gap_closed` can go **negative** while decoded `frac_gap_closed_decoded≈0.90` (`conceptual_framework.md` §5.9; `research_log_2026-06-09.txt`).

2. **Assay mixing.** Pre-v08 M1 OOD mixed Chromium with Smart-seq2 (~7% of cells); ~77% of “scattered” cells were Smart-seq2 (`21_data_imbalanced.ipynb` / §5.10). That inflated within-species heterogeneity and muddied distributional metrics. v08 drops Smart-seq2 and stratifies the split.

**Rule:** never rank IMPACT on raw `frac_gap_closed`; use `frac_gap_closed_decoded`.

---

## 5. Objectives ranked clear → muddy

1. **IMPACT species OOD (M1/M2/CD8)** — current main task; clear biological claim (`conceptual_framework.md` §1.3).  
2. **M1 v08** — single non-classical holdout; after assay cleanup, strongest OT-vs-shift north-star delta.  
3. **M2 v08** — two monocyte populations; harder cloud-matching stress test; IMPACT still wins decoded MMD but by less.  
4. **Atlas CD8 uncapped v08** — high decoded IMPACT score, but CD4/CD8 ladders were judged **saturated** as a research frontier.  
5. **Cell-type OT (non-CD8→CD8, species holdout)** — **abandoned** (`§1.2`; fossils under `results/toggle_*/cellot/`).

---

## 6. Top 10 reopen list for Plan B

Absolute paths. First commands after reading this: `./hub scorecard` then `./hub show` / open the CSVs below.

1. `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/speciesOT/baseline/analysis/v08_scorecard_dual.csv` — dual-frame table  
2. `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/speciesOT/baseline/analysis/22_v08_results.ipynb` — scorecard narrative + figures  
3. `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/hvg_pearson_residuals_m1_v08_ood/impact_cellot/evals_ood_data_space/decoded_frame_metrics.csv` — **headline M1 IMPACT**  
4. `.../hvg_pearson_residuals_m1_v08_ood/scgen/evals_ood_data_space/decoded_frame_metrics.csv` — M1 AE-scGen baseline  
5. `.../hvg_pearson_residuals_m2_v08_ood/impact_cellot/evals_ood_data_space/decoded_frame_metrics.csv`  
6. `.../hvg_pearson_residuals_m2_v08_ood/scgen/evals_ood_data_space/decoded_frame_metrics.csv`  
7. `.../hvg_pearson_residuals_a_uncapped_v08_ood/impact_cellot/evals_ood_data_space/decoded_frame_metrics.csv`  
8. `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/specs/m1_modern.yaml` + `specs/m2_baseline.yaml` — intent SoT (do not re-dump)  
9. `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/speciesOT/baseline/analysis/v08_figure_outputs/` — fig1–5 raw-vs-decoded / v07→v08 cleanup  
10. Repo root: `./hub scorecard` then `./hub show gpu/hvg_pearson_residuals_m1_v08_ood/impact_cellot` (and M2 twin)

Supporting narrative (optional reopen): `20_m1_mmd_investigation.ipynb`, `21_data_imbalanced.ipynb`, `docs/conceptual_framework.md` §5.9–5.10.

---

## 7. Confusion table (Plan C fence)

| Name | What it is | Where | Plan C must… |
|------|------------|-------|----------------|
| **Hub AE-scGen (atlas)** | PyTorch AE `beta=0` + mean δ in latent; shared encoder for IMPACT | `.../results/hvg_pearson_residuals_*_v08_ood/scgen/` | **Not overwrite / not retrain here** |
| **Paper / Lotfollahi scGen** | TensorFlow VAE + latent arithmetic (Fig. 5 LPS track) | LPS / Stage 0 artifacts; **not** v08 atlas dirs | Scaffold **new** dirs/tags only |
| **IMPACT_CellOT** | ICNN OT in the **shared hub AE** latent space | `.../impact_cellot/` under same v08 tags | Leave alone unless Plan B/D |

**Fence sentence:** Plan C must not write `hvg_pearson_residuals_*_v08_ood/scgen/`. Hub “scGen” ≠ Lotfollahi VAE.

---

## 8. Standing claims (tell the mentor without new runs)

1. Frozen atlas benchmark = v08 OOD cuts (Chromium-only + stratified split), seed 0, headline ncells=80; rank by **`frac_gap_closed_decoded`**.  
2. On that freeze, **IMPACT > hub AE-scGen** on decoded MMD gap-closed for M1 (0.90 vs 0.59), M2 (0.78 vs 0.57), and CD8 uncapped (0.94 vs 0.60).  
3. Hub scGen can still win **means**; that does not overturn the cloud north-star.  
4. Raw negative `frac_gap_closed` on IMPACT was largely **AE tax + assay mix**, not proof OT failed — decoded frame fixed the ranking story.  
5. LPS paper-replication threads are parked as infinite games; atlas judgment resumes from these v08 artifacts, not from ETH Fig.4 lockstep.

---

## Handoff

- **→ B:** reopen list §6 + best decoded numbers §3 (start M1 IMPACT vs scGen).  
- **→ C:** §7 fence — new VAE scaffolds only; never touch v08 `scgen/`.  
- **→ D:** atlas already has balanced ICNN IMPACT on v08; LPS is parked — pick target explicitly before unbalanced OT.

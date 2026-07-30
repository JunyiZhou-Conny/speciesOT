# Deliverable C — Paper-like VAE on atlas (scaffold + feasibility)

**Date:** 2026-07-21  
**Status:** Phase 2 train+eval submitted (see §8); fence held  
**Fence:** never write `cellot/cellot_gpu/results/hvg_pearson_residuals_*_v08_ood/scgen/`  
**Code root:** `atlas-paper-vae/` (new, isolated)  
**Result root:** `atlas-paper-vae/results/atlas_paper_vae_m2_v08_ood/`  
**Spec:** `specs/atlas_paper_vae_m2_v08.yaml` (new tag only)

---

## 0. What this is / is not

| | Paper Lotfollahi scGen (Stage 0) | Hub “scGen” (Plan B) | This scaffold (Plan C) |
|---|---|---|---|
| Model | TF1 `VAEArith` | PyTorch AE `beta=0` | Same TF1 `VAEArith` |
| Arch | 800–800, z=100, α=5e-5 | [512,512] or hub [256,256], z=50 | Stage-0 knobs on atlas |
| Data | Hagai LPS, 6619 genes | Tabula v08 HVG, 1000 genes | **Same v08 h5ad as Plan B** |
| Result dir | `scgen-cellot-ablation/results/stage0/` | `.../hvg_*_v08_ood/scgen/` | `atlas-paper-vae/results/atlas_paper_vae_*` |

This sprint does **not** claim a scoreboard number. Phase 2 trains + writes a metric atlas canvas.

---

## 1. Design answers

### 1.1 Data — use existing v08 h5ad (recommended)

**Decision:** train/eval on  
`cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_m2_v08.h5ad`  
**as-is** (1000 genes, Chromium-filtered, log1p, balanced 4027 mouse / 4027 human).

| Option | Pros | Cons |
|--------|------|------|
| **Same v08 h5ad (chosen)** | Apples-to-apples vs Plan B AE+IMPACT; no re-prep; fingerprint stable | Not 6619-gene paper space |
| Rebuild 6619-style ortholog space | Closer to Fig.5 gene count | New tag + prep; breaks B comparison; atlas biology ≠ LPS |

Do **not** re-prep v08. If a wider gene space is ever wanted, new tag e.g. `atlas_paper_vae_m2_g6619_*`.

Dry-run confirmed: shape `(8054, 1000)`, X ∈ [0, ~8.46], mean ≈ 0.46, sparsity ≈ 78%.

### 1.2 Split — mirror hub `toggle_ood` (M2)

Mirror `specs/m2_baseline.yaml` / `split_cell_data_toggle_ood`:

- Holdout types: `CL:0000875` (non-classical monocyte), `CL:0000576` (monocyte)
- `test_size=0.2`, `random_state=0`, `stratify=condition`, `mode=ood`
- Labels: `train` / `test` / `ood` / `ignore`

**Dry-run split table (printed 2026-07-21):**

| split | n | human | mouse | holdout types? |
|-------|---|-------|-------|----------------|
| train | 5802 | 2901 | 2901 | no |
| test | 1450 | 725 | 725 | no |
| ood | 401 | 201 | 200 | yes (half of holdout pool) |
| ignore | 401 | 200 | 201 | yes (other half; unused) |

**VAE training mask (analogue of “rat LPS held out”):**  
train on `split == "train"` only (non-holdout cell types; ~5802 cells).  
Holdout types never appear in train under ood mode — stricter than Fig.5 soft OOD (rat unst stayed in train).

**Transport eval:** OOD mouse → predict human; compare to OOD human (same cells Plan B scores).

Optional validation: `split == "test"` for early stopping (Stage 0 used a valid h5ad; we can carve 10% of train or use hub `test`).

### 1.3 Prediction rule — single species δ

Atlas task is **species** (mouse→human), not stim×species.

| Rule | When |
|------|------|
| **Primary: single δ** | `δ = mean(z_human_train) − mean(z_mouse_train)`; `ẑ = z_mouse_ood + δ`; decode. Honest analogue of hub `transport_scgen`. |
| Fig.5 two-path | Not primary — needs two orthogonal effects (species + stim). Document only. |

Always report **identity** baseline (`r2_identity`: decode(encode(mouse)) vs human means) so mean-R² cannot fool.

### 1.4 Env — `scgen_tf1` on cluster (CPU today; GPU preferred)

| Fact | Detail |
|------|--------|
| Conda env | `scgen_tf1` exists; **TF 1.15.0** imports |
| `scgen` package | Not pip-installed; add `PYTHONPATH=.../scgen-cellot-ablation/scgen-reproducibility/code` |
| Login node | No GPU (`nvidia-smi` absent) — full train → SLURM `gpu_requeue` or CPU partition |
| Stage 0 recipe | 300 epochs, batch 32, α=5e-5, dropout=0.2, lr=1e-3, z=100, width 800 |

Prefer GPU job if `tensorflow-gpu==1.15` (or TF1 GPU build) is available in the env; else CPU is fine for ~6k×1000 (smaller than Stage 0 6619-gene LPS).

Do **not** train inside `CellOT` / `CellOT_gpu` — those are PyTorch AE/ICNN.

### 1.5 Metrics — Stage-0 / Plan-B honest atlas

Eval script should call `scgen-cellot-autoresearch/honest_metrics.py` (same as `04_stage0_fig5_eval.py`) and write:

`atlas-paper-vae/results/atlas_paper_vae_m2_v08_ood/metrics.json`

Required slices (canvas skill §1–9):

1. Recon (encode→decode, no transport): MSE, r²/gene, recon MMD  
2. Mean R²: `r2_all`, `r2_identity`, `r2_self`, `frac_r2_closed` (+ decoded)  
3. Raw MMD (diagnostic)  
4. **Decoded MMD north-star** `frac_gap_closed_decoded`  
5. Latent MMD if cheap  
6. `mean_js`  
Headline `ncells=80`, also 30/50.

Phase 2 canvas: `atlas-paper-vae-m2-v08-metrics.canvas.tsx` (beside Plan B AE atlas).

### 1.6 IMPACT on VAE latents — Phase 2 only

Out of scope this sprint. Mention only: after VAE proves stable recon + scored δ, optional ICNN in VAE-z with a **new** tag (never overwrite hub `impact_cellot/`).

---

## 2. Directory layout

```text
atlas-paper-vae/
  README.md
  configs/
    m2_v08.yaml                 # arch + data + split knobs
  scripts/
    00_dry_run_split.py         # shapes + split table (no train)
    01_train_vae.py             # stub → TF VAEArith
    02_eval_metrics.py          # stub → metrics.json via honest_metrics
    submit_train.sh             # SLURM sketch (not auto-submitted)
  results/
    atlas_paper_vae_m2_v08_ood/
      .gitkeep
      dry_run_split.txt         # from this sprint
      # Phase 2: model/, metrics.json, pred_*.h5ad
  logs/

specs/atlas_paper_vae_m2_v08.yaml   # intent mirror of m2_baseline; new tag
```

**Naming:** tag / run root always `atlas_paper_vae_*` — never `scgen` under v08 hub trees.

---

## 3. Cost estimate

| Item | Estimate |
|------|----------|
| Cells × genes | 5802 train × 1000 (vs Stage 0 ~tens of k × 6619) |
| Epochs | 300 (paper recipe); early-stop optional |
| Walltime CPU | ~2–8 h (order-of-magnitude; Stage 0 LPS was longer) |
| Walltime GPU (TF1 GPU) | ~30–90 min if available |
| GPU mem | Comfortable on 16–24 GB for batch 32–128; H100 overkill but fine |
| Disk | model checkpoint ≪ 1 GB; preds/metrics small |

300-epoch recipe **transfers as a starting point**; do not HPO α/width in Phase 2 before a first scored run.

---

## 4. Risks

1. **Env fragility** — TF1 + old scanpy; `scgen` only via PYTHONPATH; GPU TF1 may be missing → CPU fallback.  
2. **Split mismatch** — if eval uses a different OOD half than hub, Plan B comparison is invalid. Scripts must call the same `toggle_ood` logic (`random_state=0`, stratify `condition`).  
3. **Mean-R² fooling** — always report `r2_identity`; Stage 0 showed ~0.87 identity vs ~0.91 model.  
4. **Decoded gap can be negative** — Stage 0 VAE had `frac_gap_closed_decoded≈−3`; VAE-on-atlas is not assumed to beat AE.  
5. **Recon ≠ transport** — training optimizes recon (+KL), not post-δ MMD.  
6. **Fence breach** — accidental `./hub generate` into v08 `scgen/`; mitigate by never pointing hub family at this stack.

---

## 5. Dry-run (this sprint)

```bash
conda run -n analysis python atlas-paper-vae/scripts/00_dry_run_split.py
# → atlas-paper-vae/results/atlas_paper_vae_m2_v08_ood/dry_run_split.txt
```

Confirmed: shapes, split counts (§1.2), holdout exclusion from train, OOD mouse/human ≈ 200/201.

Optional smoke (not done): 1k-cell / 2-epoch overfit in `scgen_tf1` — mark clearly as smoke, not result.

---

## 6. Success criteria checklist

- [x] Design doc answers data / split / δ / env / metrics  
- [x] Fence respected (no writes under v08 hub `scgen/` or `impact_cellot/`)  
- [x] Stub paths exist and are documented  
- [x] Dry-run split table printed  
- [x] Clear Phase 2 handoff  

---

## 7. Phase 2 handoff

1. Submit `atlas-paper-vae/scripts/run_train_eval.sbatch`.  
2. `02_eval_metrics.py` → `metrics.json`.  
3. Metric atlas canvas via `.cursor/skills/metric-atlas-canvas/` → `atlas-paper-vae-m2-v08-metrics`.  
4. Compare to Plan B AE-scGen **on the same v08 OOD cells** (north-star `frac_gap_closed_decoded`).  
5. Only then discuss VAE-latent IMPACT (new tag).

**→ B:** C will not touch your run_ids; compare later on matched v08 cells.  
**→ Mentor:** third model is scaffolded, not yet a scoreboard claim.

---

## 8. Experiment actually running (2026-07-21)

**One experiment — not a grid.**

| Knob | Choice | Why |
|------|--------|-----|
| Cut | M2 v08 OOD only | Apples-to-apples vs Plan B M2 AE-scGen; holdout monocytes |
| Data | Same 8054×1000 cells/genes | Via `atlas-paper-vae/data/m2_v08_legacy/` (TF1 anndata 0.6 cannot read modern h5ad) |
| Model | TF `VAEArith` 800–800, z=100, α=5e-5, dropout 0.2 | Stage 0 / paper recipe |
| Train | `split==train` (~5802), 300 epochs, batch 32, lr 1e-3 | Mirror Stage 0; early-stop inside upstream trainer |
| Predict | **single species δ** only | Honest hub-scGen analogue; no Fig.5 two-path |
| Eval | `honest_metrics` → `metrics.json` | recon + mean R² + raw/decoded/latent MMD + JS; headline ncells=80 |
| Compute | CPU `shared`, 8 cores, 32G, 24h | TF 1.15 is CPU-only here; H100 TF1 not worth the fight |
| Out of scope | M1, CD8, HPO, two-path, VAE-latent IMPACT | After first scored run |

**Not claimed until metrics land:** any north-star ranking vs Plan B.

**sbatch:** `atlas-paper-vae/scripts/run_train_eval.sbatch`

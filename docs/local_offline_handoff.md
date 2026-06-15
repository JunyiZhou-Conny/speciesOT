# Local offline handoff (Mac Cursor context)

**Purpose:** Read this when helping on the **Mac laptop** during Harvard RC cluster downtime.
The cluster (`login.rc.fas.harvard.edu`) may be unavailable for compute; **local data + notebooks still work**.

---

## Machine layout

| | Mac (local) | Cluster (holylabs) |
|---|-------------|-------------------|
| **Repo root** | `/Users/conny/Desktop/speciesOT/speciesOT` | `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT` |
| **Git remote** | `mine` → `github.com/JunyiZhou-Conny/speciesOT` | same |
| **SSH** | `jzhou1125@login.rc.fas.harvard.edu` (VPN required off-campus) | interactive shell |
| **User** | Mac login `conny`; cluster account `jzhou1125` | |

Open **the inner** `speciesOT` folder in Cursor (repo root). Parent `Desktop/speciesOT/` is just a wrapper.

**Do not use** `speciesOT_hub/` at repo root — that was a mistaken duplicate of `docs/`; delete if it reappears.

---

## What is offline vs on cluster

### Works on Mac (no cluster)

- Read/explore `.h5ad` in `offline_bundle/` (scanpy, plots, split logic)
- Notebooks: `21_data_imbalanced.ipynb`, cross-species exploration, figure replots from CSVs
- Git: pull/push code (not data)

### Cluster only

- GPU training, sbatch, `./hub prep` on full Tabula atlases
- `CellOT` / `CellOT_gpu` training and eval
- Files under `cellot/cellot_gpu/datasets/` and `results/` (not on Mac unless rsynced)
- Josh's assay source files: `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_*` (notebook 21 §4 assay plots need these unless rsynced)

---

## Offline data bundle (`offline_bundle/`)

**Gitignored** (`.gitignore` lists `offline_bundle/tier1_crossspecies/` and `tier2_hub_v08/`).
Data is copied via `rsync -avL`, not git.

Verify after copy:

```bash
cd /Users/conny/Desktop/speciesOT/speciesOT
./scripts/verify_offline_bundle.sh offline_bundle
```

Checksums: `offline_data_manifest.txt` at repo root.

### Tier 1 — cross-species / scGen / Bunne LPS (~729 MB)

| File | Shape | Notes |
|------|--------|--------|
| `tier1_crossspecies/train_species.h5ad` | 62,114 × 6,619 | scGen canonical train split |
| `tier1_crossspecies/valid_species.h5ad` | 15,528 × 6,619 | scGen valid (77,642 total) |
| `tier1_crossspecies/hvg-top1k-train-only.h5ad` | 62,114 × 1,000 | CellOT/Bunne matrix |
| `tier1_crossspecies/hvg-top1k-train-only.6619-backup.h5ad` | same bytes as `train_species` | optional duplicate |

### Tier 2 — notebook 21 v07/v08 (~86 MB)

| File | Shape |
|------|--------|
| `tier2_hub_v08/hvg_pearson_residuals_m1_v08.h5ad` | 8,054 × 1,000 |
| `tier2_hub_v08/hvg_pearson_residuals_m1_v07.h5ad` | (v07 m1 cut) |

### Re-sync from cluster (VPN on)

```bash
cd /Users/conny/Desktop/speciesOT/speciesOT
mkdir -p offline_bundle/tier1_crossspecies offline_bundle/tier2_hub_v08

rsync -avL --progress \
  jzhou1125@login.rc.fas.harvard.edu:/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/offline_bundle/tier1_crossspecies/ \
  offline_bundle/tier1_crossspecies/

rsync -avL --progress \
  jzhou1125@login.rc.fas.harvard.edu:/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/offline_bundle/tier2_hub_v08/ \
  offline_bundle/tier2_hub_v08/
```

---

## Python environment on Mac

Cluster `analysis` env: **scanpy 1.12**, **anndata 0.12.10**.

Mac may not have `analysis` yet. Base miniconda already loads offline h5ad. To match cluster:

```bash
conda create -n analysis python=3.12 -y
conda activate analysis
pip install "scanpy==1.12.*" "anndata==0.12.*" pandas numpy matplotlib seaborn scikit-learn jupyter ipykernel
python -m ipykernel install --user --name analysis --display-name "Python (analysis)"
```

Use kernel **Python (analysis)** or **base** in Jupyter/Cursor. Do **not** need `CellOT` on Mac for offline notebooks.

---

## Notebook path pattern (use on Mac)

Cluster notebooks hardcode `/n/holylabs/...`. For offline, use repo-relative paths — **do not commit Mac-only absolute paths** unless using a portable helper.

```python
from pathlib import Path

# Repo root (Mac)
REPO = Path("/Users/conny/Desktop/speciesOT/speciesOT")
# Or discover repo:
for p in [Path.cwd(), *Path.cwd().parents]:
    if (p / "offline_data_manifest.txt").exists():
        REPO = p
        break

B = REPO / "offline_bundle"
H5_V08 = B / "tier2_hub_v08/hvg_pearson_residuals_m1_v08.h5ad"
H5_V07 = B / "tier2_hub_v08/hvg_pearson_residuals_m1_v07.h5ad"
H5_CROSS = B / "tier1_crossspecies/hvg-top1k-train-only.h5ad"
OUT = REPO / "speciesOT/baseline/analysis/nb21_outputs"
```

Cluster equivalent for `CELL_GPU`:

```python
CELL_GPU = REPO / "cellot/cellot_gpu"
H5 = B / "tier2_hub_v08/hvg_pearson_residuals_m1_v08.h5ad"  # offline
# H5 = CELL_GPU / "datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_m1_v08.h5ad"  # cluster
```

---

## Git rules (important)

- **Never commit** `.h5ad` under `offline_bundle/tier*/` (gitignored).
- **Never commit** mass deletions of `docs/` — if `git status` shows hundreds of deleted `docs/*`, run `git restore docs/`; do not commit.
- **Do not** add `speciesOT_hub/` (stray copy of docs).
- **Do not** commit `scgen-reproducibility/` nested clone into this repo.
- Push/pull via **`mine`**, not `josh` (mentor's diverged remote).
- Cluster may have unpushed work; run `git pull mine main` on Mac after cluster pushes.

---

## Project context (short)

- **speciesOT:** mouse→human species transport via **IMPACT_CellOT** (CellOT OT in scGen AE latent space); **scGen** is baseline.
- **North-star metric:** `frac_gap_closed_decoded` on v08 OOD cuts (hub scorecard) — **not** raw `frac_gap_closed` (AE round-trip tax; see `docs/concepts/AE round-trip tax.md`).
- **Cross-species LPS (Bunne Fig 4):** Hagai/scGen data; bundle in `offline_bundle/tier1_crossspecies/`. scGen paper holdout ≠ CellOT `toggle_ood`.
- Canonical rules: `AGENTS.md`, science in `docs/conceptual_framework.md`, CLI in `docs/hub_usage.md`.

---

## Active research thread (June 2026 — read this first)

**Problem:** M1 monocyte holdout metrics look confusing — some `frac_gap_closed` values negative or near zero even when R² improves. User is pivoting to **foundational UMAP / holdout-quality analysis** before concluding the autoencoder is useless.

### Experiments (monocyte holdouts)

| Line | Holdout | v07 OOD human n | v08 OOD human n |
|------|---------|-----------------|-----------------|
| **M1** | non-classical monocyte `CL:0000875` only | 207 | 183 |
| **M2** | `CL:0000875` + generic monocyte `CL:0000576` | larger, heterogeneous | assay-filtered |

**M2 → M1 rationale:** M2 UMAP tail was largely bone-marrow generic monocytes; M1 drops them. M1 still does not look like one perfect blob.

### Key findings already established (do not re-derive from scratch)

1. **v07 scatter is partly Smart-seq2 contamination** (notebook 21 §6): ~77% of “scattered” cells are Smart-seq2; detached Leiden cluster is 100% Smart-seq2. Donor signal (TSP1, TSP14) was a proxy for assay mix.
2. **v08 assay filter helps but does not fix everything** (notebook 21 §7, `22_v08_results.ipynb`):
   - Smart-seq2 gone; Chromium-only UMAP shows **two species blobs** (mouse v2, human v3) — expected.
   - Human Chromium: mostly one blob + small satellite (Leiden cl2, ~22 cells); ~15% still “scattered” on pure 10x.
   - **Raw `frac_gap_closed` still negative** for several v08 scGen runs; **decoded** `frac_gap_closed_decoded` is much better for M1 IMPACT (~0.90) but scGen still ~0.57–0.59.
3. **Atlas-reference UMAP edge cells** (`m1_atlas_ood_investigation/`, script `scripts/m1_atlas_ood_outlier_analysis.py`): on v07, 31/207 human OOD are UMAP-edge — 16 Smart-seq2, 15 real 10x (mostly TSP2). Same donor can be core **and** edge. kNN projection creates some vertical-tail artifact (joint UMAP removes it).
4. **Assay lookup in notebook 21 §6** needs Josh's Tabula source files on cluster — **not in offline bundle**. Offline §7 can run without assay re-lookup (v08 is already filtered); skip or stub assay plots if sources missing.

### Primary notebooks & outputs (mostly in git)

| Artifact | Path | Offline? |
|----------|------|----------|
| M1 blob investigation | `speciesOT/baseline/analysis/21_data_imbalanced.ipynb` | ✅ edit + rerun §7 |
| v08 scorecard reader | `speciesOT/baseline/analysis/22_v08_results.ipynb` | ✅ read CSVs; no GPU re-eval |
| Atlas outlier script | `speciesOT/baseline/analysis/scripts/m1_atlas_ood_outlier_analysis.py` | ⚠️ needs cluster paths or adapt to `offline_bundle` |
| v07/v08 UMAP figures | `nb21_outputs/nb21_v08_*.png`, `nb21_assay.png` | ✅ in git |
| Atlas outlier tables/figs | `m1_atlas_ood_investigation/` | ✅ in git (~1 MB) |
| MMD comparison | `m1_pearson_outputs/r2_mmd_comparison_m1_m2.csv` | ✅ in git |
| Scorecards | `v08_scorecard_dual.csv` | ✅ in git |

### Sensible offline next steps

- Continue notebook 21: human-only Chromium embedding, per-donor edge breakdown (TSP2), compare v07 vs v08 scatter counts.
- Replot / annotate existing CSVs (`edge_cells_ranked_v07.csv`, `human_ood_cell_table_m1_v08.csv`) — regenerate by adapting script paths to `offline_bundle`.
- Read `docs/concepts/frac_gap_closed.md` and `docs/concepts/AE round-trip tax.md` when interpreting metrics.
- **Do not** submit sbatch, run `./hub prep`, or train IMPACT/scGen on Mac.

### Open questions (user may ask you to pursue)

- Is residual v08 scatter biological (monocyte sub-state) or still visualization?
- Should MMD be recomputed on “core blob only” vs full holdout?
- Bunne paper MMD floor/ceiling on `tier1_crossspecies/` (separate from hub M1 work).

---

## Paste-this prompt for local Cursor

Copy everything in the block below into a **new Cursor chat** on the Mac (adjust repo path if needed):

```
I'm working OFFLINE on my Mac during a 2-day Harvard RC cluster outage. No GPU, no sbatch, no ./hub prep, no /n/holylabs paths.

## Setup
- Repo root: /Users/conny/Desktop/speciesOT/speciesOT  (inner speciesOT folder — not the Desktop wrapper)
- Read first: @docs/local_offline_handoff.md, @AGENTS.md
- Offline h5ad: @offline_data_manifest.txt → files under offline_bundle/ (gitignored; rsynced with -L)
- Conda: `analysis` env (scanpy ≥1.12) or base

## Path rule
Never commit Mac absolute paths. Use repo-relative discovery:
  REPO = first parent of cwd containing offline_data_manifest.txt
  B = REPO / "offline_bundle"
  H5_V08 = B / "tier2_hub_v08/hvg_pearson_residuals_m1_v08.h5ad"

## What I'm working on
M1 non-classical monocyte holdout quality — why the 207 (v07) / 183 (v08) human OOD cells don't form one clean blob, and how that relates to confusing frac_gap_closed metrics.

Key notebooks: @speciesOT/baseline/analysis/21_data_imbalanced.ipynb (§7 = v08 Chromium UMAP), @speciesOT/baseline/analysis/22_v08_results.ipynb

Already known (don't redo blindly):
- v07 scatter ≈ Smart-seq2 assay contamination (nb21 §6)
- v08 removes Smart-seq2; ~15% edge cells remain on pure 10x; species split is expected
- raw frac_gap_closed can be negative; north-star is frac_gap_closed_decoded (v08 M1 IMPACT ~0.90)
- Atlas outlier analysis in m1_atlas_ood_investigation/ and scripts/m1_atlas_ood_outlier_analysis.py

## Constraints
- Git remote: `mine` only (not `josh`). Don't commit .h5ad or offline_bundle/tier*/
- Josh Tabula assay source files NOT on Mac — skip assay lookup or note missing
- Help me adapt notebook paths, run scanpy analysis, and interpret plots — not cluster jobs

What should we do next for [YOUR SPECIFIC TASK HERE]?
```

---

*Last updated: 2026-06-14 (cluster prep for 2-day outage; includes M1 UMAP / frac_gap research context).*

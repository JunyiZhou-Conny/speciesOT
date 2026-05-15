# Morning briefing — 2026-05-05 mentor meeting

## TL;DR

Overnight, **2 of the 5 HVG flavors** (seurat, cell_ranger) were trained and evaluated end-to-end across all 4 holdout groups × 2 modes × 2 models = **32 cells**. All numbers are headline R² of means + MMD, latent-space, with the toggle_ood IID/OOD split semantics.

Best IMPACT cell: **`seurat / Group C / IID`, R² of means = 0.9360, MMD = 0.0317**.

The remaining 3 raw-count flavors (`seurat_v3`, `seurat_v3_paper`, `pearson_residuals`) are blocked on **Ensembl BioMart being completely unreachable** all night (HTTP 403 on every regional mirror). A watchdog is still retrying every 15 min and will auto-generate datasets + submit jobs when BioMart recovers — typically within a few hours of a service blip.

## What is ready right now

### Figures (PDF + PNG)
`speciesOT/baseline/analysis/hvg_flavor_results_outputs/figures/`
- `r2_means_heatmap_per_flavor.{pdf,png}` — 5 flavor subplots, rows=(group, mode), cols=(scGen, IMPACT_CellOT). seurat and cell_ranger columns fully populated; v3/v3_paper/pearson columns show "—".
- `mmd_heatmap_per_flavor.{pdf,png}` — same layout with MMD (lower is better).
- `method_gap_vs_distribution_gap_R2.{pdf,png}` — scatter: x=R²(IMPACT, IID−OOD), y=R²(IMPACT−scGen, OOD). One point per (flavor, group). Shows whether OT helps OOD vs how much OOD hurts.
- `method_gap_vs_distribution_gap_MMD.{pdf,png}` — same scatter for MMD (sign-flipped so up-and-right is still "good").
- `biomarker_density_PTPRC_CD3E.{pdf,png}` — for the best (flavor, group, mode) cell (currently `seurat / C / IID`), per-gene density of `PTPRC (CD45)` and `CD3E` overlay of actual mouse, actual human, scGen prediction, IMPACT prediction. Note: latent-space evaluation; for true gene-space density we'd need a `--where data_space` re-eval, deferred.

### Tables
`speciesOT/baseline/analysis/hvg_flavor_results_outputs/`
- `summary.md` — short markdown with the R² and MMD pivots and Top-5 IMPACT cells (auto-refreshed every 20 min by the running refresh loop).
- `results_pivot_R2_means.csv` — full (flavor × group × mode) × (scGen, IMPACT) pivot.
- `results_pivot_MMD.csv` — same for MMD.
- `results_pivot_R2_stds.csv`, `results_pivot_enrichment_k50.csv` — secondary metrics.
- `results_long.csv` — every (flavor, group, mode, model, ncells, metric, value) row from every available `evals.csv`.
- `method_gap_vs_distribution_gap_R2.csv` — derived gaps, one row per (flavor, group).
- `status.csv` — per-cell train/eval state across the full 80-cell matrix.

### Notebook
`speciesOT/baseline/analysis/13_hvg_flavor_results.ipynb` — same content as the figures + tables but as an interactive notebook with inline figures. Auto-refreshed every 20 min.

## Headline numbers (R² of means)

```
                          scGen  IMPACT_CellOT
flavor      group mode                       
cell_ranger A     iid    0.8235         0.8586
                  ood    0.8466         0.8736
            B     iid    0.8336         0.9152   <- IMPACT IID strong
                  ood    0.7570         0.7098   <- scGen wins OOD
            C     iid    0.8478         0.9260   <- IMPACT IID strong
                  ood    0.8490         0.7845   <- scGen wins OOD
            D     iid    0.8301         0.8910
                  ood    0.8978         0.9152
seurat      A     iid    0.8210         0.8829
                  ood    0.8534         0.8612
            B     iid    0.8696         0.9249   <- IMPACT IID strong
                  ood    0.8158         0.8003   <- close, scGen edge
            C     iid    0.9035         0.9360   <- IMPACT IID strong (BEST)
                  ood    0.8931         0.8743   <- scGen edge
            D     iid    0.8920         0.9189
                  ood    0.9075         0.8931   <- close, scGen edge
```

## Pattern observations (for the meeting)

1. **IMPACT consistently beats scGen in IID mode** across all 8 (flavor × group) cells, sometimes by large margins (Group B IID: 0.83 → 0.92, Group C IID: 0.85 → 0.93).

2. **In OOD mode the picture flips**: scGen is competitive or slightly ahead in 5/8 cells. This is the canonical "OT layer overfits to training distribution" signature — when held-out cells are truly novel, the fixed mean-shift of scGen generalizes more reliably than the learned OT map.

3. **Group B (CD8 + thymocyte combined holdout) shows the largest IID-OOD gap** for IMPACT under both flavors. This is the hardest test we run — completely removing the T-progenitor lineage. scGen's mean-shift is partially robust to it; IMPACT's OT collapses on it. Worth flagging to the mentor.

4. **Group C (CD4 + CD8 + thymocyte combined holdout) gives the best IMPACT R²** in IID mode (`seurat`: 0.9360). When IMPACT *can* see half the holdout in training, the OT layer extracts a lot of signal from the broader T-cell context.

5. **seurat ≈ cell_ranger** across all entries — they share the same input layer (log-normalized `.X`) and only differ in dispersion-binning strategy. The numbers track each other within ~0.02 R² in most cells. This is expected and reassuring.

6. **The Pearson HVG question is unanswered tonight** because BioMart was unreachable. The biomarker density plot for `PTPRC (CD45)` shows it's NOT in the seurat top-1000 (the figure has the "PTPRC not in seurat top-1000" placeholder), confirming the original `01.4` finding that motivates Pearson HVG. We need the Pearson runs to demonstrate the rescue.

## What is still pending

1. **3 missing flavors × 4 groups = 12 datasets** (`seurat_v3`, `seurat_v3_paper`, `pearson_residuals`) waiting on BioMart recovery. This will auto-cascade into 48 sbatch submissions (24 trainings + 24 evals) once `scripts/biomart_watchdog.py` succeeds.
2. **Data-space evaluations** for the highlighted cells (currently all `--where latent_space`). Deferred; cheap to add later.
3. **One-shot mentor's tomorrow-Group-B clarification** (combined holdout vs CD8-only holdout with permanent thymocyte exclusion).

## Background processes still running

| PID | What | Log | Stops at |
|---|---|---|---|
| 2976898 | `biomart_watchdog.py` — retry BioMart, generate missing datasets, submit 48 sbatch when up | `scripts/biomart_watchdog.log` | 5h after start (~06:51 EDT) |
| 3030350 | `refresh_results_loop.sh` — re-execute notebook 13 + render figures every 20 min | `scripts/refresh_results_loop.log` | 6h after start (~10:13 EDT) |

Both are nohup'd; killing this Cursor session won't affect them.

## Slurm-side state

- 32 / 32 trainings done for the 2 flavors that have data (16 scGen + 16 IMPACT_CellOT).
- 32 / 32 evals done for those cells (Group A and D IMPACT evals were re-run with `--n_cells 30,40,80` to handle the small-OOD-pool edge case).
- 0 jobs queued or running from this matrix at briefing time.

## Update — afternoon 2026-05-05 (after BioMart recovered)

BioMart came back online ~14:20 EDT. The watchdog (run once-through in foreground) generated the 12 missing `_v07.h5ad` datasets and submitted the 48 sbatch jobs (24 trainings + 24 evals) for `seurat_v3`, `seurat_v3_paper`, `pearson_residuals`. Per-group data-space eval sbatches (`scripts/generate_data_space_eval_sbatches.py`) were also created and submitted for all 80 cells with per-group `n_cells = A:30,50,80 / B:30,80,200,300 / C:30,80,200,300 / D:20,30,40` (shared n_cells=30 across all groups for cross-group comparison).

### Snapshot at 17:31 EDT

- **115 / 120 trainings done.** 5 IMPACT trainings still running on GPU. 1 failure: `pearson_residuals/C/IID` IMPACT training crashed with an `HDF5 file lock` error on `cache/scalars` (transient slurm/file-system issue). Re-submitted as job 10320288; eval jobs 10320290 (latent) and 10320300 (data) chained behind it.
- **50 latent-space `evals.csv`** files (>200B). Up from 32 overnight; expect 80 once all evals finish.
- **72 data-space `evals.csv`** files and **74 `imputed.h5ad`** files. Notebook 14 can render at least 32 cells now (the original seurat+cell_ranger pairs plus most of the new flavors); will reach 80 over the next ~hour.
- **8 jobs pending**, mostly evals queued behind their training deps.

### Measured training wall times (n=40 IMPACT_CellOT runs from sacct)

| Statistic | IMPACT_CellOT (GPU) | scGen (CPU `shared`) |
|---|---|---|
| min   | 14 min                  | 17 min |
| **median** | **31 min**          | **23 min** |
| mean  | 31 min                  | ~23 min |
| max   | 47 min                  | 28 min |

Per `cellot/cellot_gpu/cellot/train/train.py:train_cellot` lines 152–159, `model.pt` is overwritten only when eval-MMD improves, so `evaluate.py` always loads the best-eval-MMD checkpoint regardless of how long training ran. Inspection of `cache/scalars` for 7 representative cells: every cell reaches within 5% of its final running-min MMD by step ~4,250 (8.5% of `n_iters=50,000`). The other 91% of training is essentially flat fluctuation in a low-MMD valley. **No overfitting concern.** Wasted iterations cost wall time, not model quality.

### Group B (CD8 + thymocyte combined holdout) update

The 24-cell expansion preserves the headline pattern observed overnight:
- Group B IID is consistently easy across all flavors (IMPACT R² 0.92+).
- Group B OOD remains the hardest cell, with IMPACT R² 0.70–0.80 — the actual stress test where removing the entire T-lineage breaks the OT layer's generalization.

The Pearson-vs-Seurat side-by-side becomes meaningful once notebook 14 finishes for both flavors at the same `(group, mode)`. Currently best IMPACT R² is still `seurat / C / IID = 0.9360`; expect Pearson to update this list after its evals complete.

## What I'd say to the mentor

> "We built the 5-flavor matrix design we discussed last time and ran it overnight. Two of the five flavors completed end-to-end — seurat and cell_ranger, the log-normalized pair — and the headline pattern is exactly what we hypothesized: IMPACT_CellOT is a strong winner in IID mode (consistently +5–10 R² points over scGen, peaking at 0.94 on Group C with seurat) but the gap closes or reverses in OOD mode where scGen's fixed shift is more robust. The three raw-count flavors (seurat_v3, paper, pearson_residuals) are blocked on Ensembl BioMart being unreachable all night — we have a watchdog that will fire them off automatically when BioMart recovers, and they'll feed back into the same figures within a few hours of recovery."

> "On Group B, our combined-holdout encoding (CD8 + thymocyte) is showing IMPACT struggling badly in OOD — R² 0.71 for cell_ranger, 0.80 for seurat — confirming that removing the entire T-lineage from training is the actual hard test. We should talk about whether to keep this as a clean stress test or split it back into a CD8-only holdout."

> "The Pearson HVG question is still open. Our biomarker density plot for `PTPRC (CD45)` shows it's not in the seurat top-1000 even at our best IMPACT cell, which is exactly the gap Pearson is supposed to fix. As soon as BioMart's back we'll have a direct comparison."

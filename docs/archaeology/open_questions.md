# Open questions and suggested next steps

This page lists what the record could not settle, grouped by who or what can
settle it. Each family page has a longer list under "Open questions". Nothing
here was run or changed by this archaeology. Computations on FASRC need
Conny's approval first.

## 1. Questions for Conny and Josh

- **What does "IMPACT" (IMPACT-OR, IMPACT_CellOT) stand for?** It is not
  recorded anywhere; `docs/conceptual_framework.md` has a TODO for it
  ([F06](experiments/F06-tcell-holdouts-speciesot-v1.md)).
- **Which uncommitted copy of `speciesot_core.py` is current?** The Mac copy
  is from 2026-10-15 18:54, the FASRC copy from 18:29
  ([sources.md](sources.md), [F18](experiments/F18-oop-package.md)).
- **What did the 2026-05-08 mentor meeting decide, and why?** Only
  seurat_v3 and pearson_residuals were kept afterwards, and no notes survive
  ([F08](experiments/F08-hvg-flavor-matrix.md)). The same goes for the
  2026-05-12 lab meeting.
- **What did Josh conclude from e18?** e18 was his check of Conny's IMPACT-OR
  outputs ([F06](experiments/F06-tcell-holdouts-speciesot-v1.md)).
- **Were these results ever shown to Josh?** No record shows that any of these
  reached him:
  - the April toggle results ([F07](experiments/F07-toggle-iid-ood-and-renorm.md));
  - the July Plan A and B deliverables ([F14](experiments/F14-july-plans-a-to-d.md));
  - the late-July autoencoder study ([F15](experiments/F15-ae-repair-rounds-and-calibration.md)).
- **What was said at the 2026-06-25 meeting with David?** There are slides
  but no notes ([F13](experiments/F13-autoresearch-loop.md)).
- **Did the CellOT authors answer the e-mail about their data and
  `species.csv`?** ([F11](experiments/F11-bunne-lps-replication.md)).
- **Which human BCG capture is day 0 and which is day 90, and what does "two
  donors" mean?** ([F17](experiments/F17-bcg-application.md)).
- **The package decisions:** which scGen, which R² and MMD, which frame, how
  splits work, where genes are aligned, the config schema and data loading.
  The twelve decisions are listed in
  [F18](experiments/F18-oop-package.md#decisions-the-package-needs-next).

## 2. Cheap checks on saved files (CPU only, no training)

All inputs exist in the FASRC backup or in this repo. Each check would close a
gap named on a family page.

1. **Identity baseline for the March CD8 holdout.** Unchanged mouse CD8 cells
   vs human CD8 cells, with the same metrics as IMPACT-OR's 0.72. The inputs
   are in this repo via git LFS
   ([F06](experiments/F06-tcell-holdouts-speciesot-v1.md),
   [reference_experiments.md](reference_experiments.md) R2.3).
2. **The species map on untreated BCG cells.** The 2026-08-18 untreated-mouse
   predictions vs the 2026-08-26 untreated human cells. This is the check
   announced on 2026-08-19 that never ran
   ([F17](experiments/F17-bcg-application.md)).
3. **`raw_shift` on the top-50 markers** (CellOT's own metric) on the LPS
   arms. Does the gene-space mean shift still beat the autoencoder?
   ([F13](experiments/F13-autoresearch-loop.md)).
4. **M1 v07 without its 60 Smart-seq2 cells.** Does the v07 models' MMD drop?
   ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)).
5. **Rat CellOT's final checkpoint (`last.pt`)** instead of the early
   best-batch one. Does the rat MMD order flip back?
   ([F11](experiments/F11-bunne-lps-replication.md)).
6. **Gene-space scores for the first LPS model.** Its decoded predictions are
   saved but were never scored in gene space
   ([F05](experiments/F05-first-cellot-runs-on-lps.md)).
7. **Hash checks.** Compare the sha256 of the Stage 1 arm files and
   checkpoints with their manifests before they are used as references
   ([F13](experiments/F13-autoresearch-loop.md),
   [F15](experiments/F15-ae-repair-rounds-and-calibration.md)).
8. **Encoder run-to-run spread.** The eight April IID encoders were trained on
   identical data. Their saved loss curves would give a first noise estimate
   ([F07](experiments/F07-toggle-iid-ood-and-renorm.md)).

## 3. Experiments that would settle the main scientific questions (need GPU time)

1. **Paper scGen on the hard split.** The TensorFlow VAE with the two-path
   rule on the Bunne OOD LPS split was never run. It is the missing cell of
   the "is CellOT's scGen a fair baseline?" comparison
   ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md)).
2. **Training-seed noise on the v08 benchmark.** Retrain scGen-style and
   IMPACT with at least three seeds, so that "IMPACT beats scGen" gets an
   error bar ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md),
   [F14](experiments/F14-july-plans-a-to-d.md)).
3. **IID without leakage.** Train the IID encoder without the evaluation half
   to measure how much of the IID gain was leakage
   ([F07](experiments/F07-toggle-iid-ood-and-renorm.md)).
4. **OT without the bottleneck.** Gene-space or wide-latent transport, and
   the six unrun rungs of the ICNN ladder. Is the one ICNN loss (−0.203) a
   training problem or real? ([F13](experiments/F13-autoresearch-loop.md)).
5. **A BCG test that scores the change.** Predict (treated − untreated), with
   both trivial baselines in the same frame
   ([F17](experiments/F17-bcg-application.md)).

## 4. Repository housekeeping (decisions; none done here)

- **Commit the code that exists in one place only.** The late-July ablation
  scripts and the uncommitted autoresearch files on FASRC
  ([sources.md](sources.md#at-risk)).
- **Back up inputs that are outside the backup.** Josh's
  `fasrc:JOSH/tb/data/`, the Stage 1 predictions on the Mac, and the Cursor
  canvases in the FASRC home ([F15](experiments/F15-ae-repair-rounds-and-calibration.md)).
- **Mark or fix stale documents** where this archaeology found them wrong
  ([critique.md](critique.md) §9):
  - `AGENTS.md` "Current focus" (the E3 claim);
  - `docs/concepts/scGen.md` ("a VAE");
  - the concept notes on the legacy LPS runs and "the three model variants";
  - the mixhvg spec comment;
  - the runbook's default-model-set label.

  A one-line banner pointing to `docs/archaeology/` would be the smallest
  change.
- **Decide what to do with the vault and the model cards** (regenerate,
  freeze with a warning, or delete). They froze in May and June
  ([F09](experiments/F09-hub-and-metrics-infrastructure.md)).
- **Clean up the PRs.** Josh's PR #2 does not import. This repo's stack PRs
  #8–#10 are still open against branches that were undone
  ([F18](experiments/F18-oop-package.md)).
- **Retire `scripts/build_experiments_inventory.py`.** It points into the
  deleted FASRC working tree; `docs/archaeology/inventory.csv` and `./hub
  export` replace it ([F09](experiments/F09-hub-and-metrics-infrastructure.md)).
- **Pin the ortholog table.**
  `conny@c342331:scripts/.biomart_ortholog_cache.csv` is the only copy
  ([data.md](data.md)).

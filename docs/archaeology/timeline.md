# Timeline, 2024-06 → 2026-10

The project in date order, so you can find "what were we doing in May?" quickly.
Each entry links to the family page that has the evidence. Labels: [G] git,
[D] research log or doc, [R] Slurm or result file, [N] saved notebook output.
Citation prefixes are in [sources.md](sources.md).

Slurm accounting starts on 2026-03-30. Jobs submitted by Conny's account per
month, deduplicated (almost all speciesOT until September): April 321, May
354, June 279, July 244, August 20 [R]. These counts come from plain
time-window queries, which leave out jobs cancelled while waiting on a
dependency, so the true numbers are higher. In the June replication, for
example, the plain query shows 20 of 72 jobs
([F11](experiments/F11-bunne-lps-replication.md)). After 2026-08-18 there are
no more speciesOT compute jobs.

## Before Conny: Josh's cross-species matching work (2024-06 → 2026-02)

The early question: can optimal transport (OT) *match* mouse cells to the
corresponding human cells?

- **2024-06-15** Josh's repo starts: exploration of Tabula Muris and Tabula
  Sapiens bone marrow [G]. → [F01](experiments/F01-gw-feasibility-and-simulations.md)
- **2025-07** Gromov-Wasserstein (GW) alignment of blood cells across pig,
  mouse and human. The commit messages call pig→human "successful", but that
  rests on 7 hand-checked cells. Measured type-matching was at chance: 43.2% vs
  45.6% with shuffled labels. Mouse→human pairs were "not correct"
  (`josh@c861dce`, `josh@393065f`) [G][D][N]. → F01
- **2025-10** Atlas sampling. Within- vs between-species distances:
  "between-species OT not better than random yet" (`josh@7f16bb7`) [G].
  PerturbOT (label-constrained OT) experiments E1–E4. E1's apparent gain at
  ε ≈ 1e-8 came from failed (NaN) solver runs, out-of-sample cell types failed,
  and T cells were not aligned [N][D].
  → F01, [F02](experiments/F02-perturbot.md)
- **2026-01** Simulations E5–E8 to diagnose why GW fails. The main failure is
  "symmetry mismatch": whole populations get swapped. Seeded anchors removed
  the swaps in a handful of toy runs [N]. → F01
- **2026-02** Real immune data again (E9–E14): informative dimensions,
  ontology matching, OTDD, CellTypist labels, and fused GW with one-to-one
  orthologs: best at α = 0, i.e. with the GW part switched off, and with genes
  chosen using the scored labels [N].
  → [F03](experiments/F03-labels-ontology-and-distances.md),
  [F04](experiments/F04-gene-priors-and-standard-ot.md)
- **2026-02-25** Josh's last `main` commit before the `cellot` branch splits
  off (`josh@a7f7301`) [G].

## Conny's scGen / CellOT work inside Josh's repo (2026-03 → 2026-05)

The question changes from *matching* cells to *translating* them: predict
human expression from mouse cells with scGen and CellOT.

- **2026-03-04** Conny's first commits on branch `cellot`: pair-coding an
  AnnData/UMAP examination (`josh@9124d02`, `josh@e86c1df`) [G].
- **2026-03-10 → 03-15** First CellOT runs on the cross-species LPS data
  (the CellOT paper's task) (`conny:logs/research_logs/research_log_2026-03-15.txt`)
  [D]. → [F05](experiments/F05-first-cellot-runs-on-lps.md)
- **2026-03-18** First atlas run on Tabula Muris/Sapiens, in the human → mouse
  direction [R]. **2026-03-22**: the direction flips to mouse → human, with
  narrow cell-type holdouts (CD8 T cells, monocytes) (log 03-22) [D].
  → [F06](experiments/F06-tcell-holdouts-speciesot-v1.md)
- **2026-03-24 → 03-25** Analysis notebooks 00–06: scGen autoencoder,
  CellOT OOD evaluation, held-out T cells, and the first CD8-holdout
  comparison of IMPACT-OR vs CellOT vs scGen (`josh@1db1592`) [G].
  → [F06](experiments/F06-tcell-holdouts-speciesot-v1.md)
- **2026-03-30** Iteration 2 (106k cells, BioMart orthologs) (log 03-30) [D].
- **2026-04-05 → 04-06** `speciesot_cd4/cd8/tcell` runs [R]. → F06
- **2026-04-08 → 04-09** An r-vs-r² mix-up is fixed and evaluation moves to
  CellOT's `evaluate.py` (log 04-08) [D]. The toggle IID/OOD runs T1–T4 /
  M1–M4 follow: 234 jobs, 113 of them failed [R].
  → [F07](experiments/F07-toggle-iid-ood-and-renorm.md)
- **2026-04-10** Josh's E17: plain OT pairs only about 25% of cells correctly
  in gene space, so "redo with the scGen autoencoder latent" [N]. → F04
- **2026-04-20** Josh's E18 checks Conny's IMPACT-OR outputs (`josh@b9eff70`)
  [G]. A preprocessing scale mismatch between mouse and human is found and the
  data are renormalised (log 04-20) [D]. → F06, F07
- **2026-04-24 → 05-12** Highly-variable-gene (HVG) investigation and the
  five-flavor HVG matrix: 80 runs, 349 jobs between 05-05 and 06-02 [R].
  → [F08](experiments/F08-hvg-flavor-matrix.md)
- **2026-05-05 → 05-13** Josh starts the BCG application: mouse and human
  BCG stem-cell data (tb1, tb2) [G].
  → [F17](experiments/F17-bcg-application.md)
- **2026-05-08 → 05-10** First deployment models (full atlas, no holdout),
  first BCG mouse→human prediction, paper-style figure F/G replicas, and a
  presentation (2026-05-10) [G].
  → [F16](experiments/F16-deployment-models-and-mixhvg.md), F17, F06

## Conny's own repo: infrastructure and the atlas benchmark (2026-05-15 → 06-22)

- **2026-05-15** This repo starts from a fresh `git init` ("Tier 1 repository
  reorganization", `conny@c342331`) [G].
- **2026-05-25 → 05-29** Ten "walkthrough cleanup" commits, then the `hub`
  CLI from v0 to v1.1: run discovery, scorecard, specs and job generation
  [G]. → [F09](experiments/F09-hub-and-metrics-infrastructure.md)
- **2026-05-26 → 06-02** Uncapped CD8 data. The M1 monocyte puzzle (R² up,
  MMD not), which leads to the MMD floor/ceiling framework [N].
  → [F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)
- **2026-05-28** 175 model cards and an index generated by `./hub card --all`
  (`fasrc:BK/docs/model_cards/`) [R].
- **2026-06-05** The v08 data cut (assay filter, species-stratified split) and
  the "frozen benchmark" runs [R]. → F10
- **2026-06-09** Obsidian vault generated; decoded-frame metric adopted as the
  headline (log 06-09, `conny@8a9a103`) [G][D]. → F09, F10
- **2026-06-12 → 06-22** Replication of the CellOT paper's cross-species LPS
  result. Of 72 jobs, 2 completed, 8 failed and 62 were cancelled [R]. On
  06-22, "found final results of Bunne paper" (`conny@3ccd3d5`) [G].
  → [F11](experiments/F11-bunne-lps-replication.md)

## Summer: scGen reproduction, autoresearch, and the autoencoder problem (2026-06-15 → 07-30)

- **2026-06-19 → 06-22** The `scgen-cellot-ablation` repo. Stage 0
  reproduces scGen's Fig. 5 with the original TensorFlow code; Stage 1 is the
  2×2 grid of split × gene set using CellOT's autoencoder scGen [G][R].
  → [F12](experiments/F12-scgen-fig5-stage0-and-stage1.md)
- **2026-06-22 → 07-18** The autoresearch loop: 338 logged LPS experiments in 337 run
  folders (390 jobs) [R]. On 06-23 there is an "autonomous session" while Conny was
  away; on 06-25 a meeting with David. The last run finished on 07-18
  ("DONE") [R][D]. Its journal concludes that the autoencoder hurts, and the
  one CellOT-on-frozen-autoencoder run loses to a plain mean shift [R].
  → [F13](experiments/F13-autoresearch-loop.md)
- **2026-07-20** "Stop the infinite games": OT beating scGen on MMD was not
  reproduced; return to the atlas (log 07-20) [D]. → F11, F13
- **2026-07-21** Four agent plans run in parallel:
  - A: atlas memory brief;
  - B: atlas scoreboard;
  - C: paper-style VAE on the atlas;
  - D: unbalanced OT. Its five jobs completed, but their outputs are missing
    from the backup [R].

  → [F14](experiments/F14-july-plans-a-to-d.md)
- **2026-07-23 → 07-29** Bounded repair of the paper-scGen autoencoder:
  - Rounds 1 and 3 have no winner [R];
  - Round 2 is skipped;
  - composition and variance checks;
  - a post-hoc variance correction ("devar") that fails its permuted-control
    check (07-29) [R].

  → [F15](experiments/F15-ae-repair-rounds-and-calibration.md)
- **2026-07-30** Environment modernisation and a hand-over plan: "mentor will
  be RUNNING predictions" (log 07-30) [D]. `AGENTS.md` gets its "current
  focus" text [G]. `mixhvg-py` split out [G]. → F15, F16

## Deployment and BCG (2026-08)

- **2026-08-03** Specs for the uncapped v08 deployment models and the mixhvg
  ablation; models made self-contained (baked shift and gene axis)
  (`conny@0b9c66e`, `conny@a2f89cc`) [G]. → F16
- **2026-08-18** BCG prediction path on the v08 gene axis (notebooks
  16.2–16.4). The last speciesOT compute jobs run: the uncapped v08 models.
  There is no atlas evaluation (`evals.csv`) for them [G][R]. Josh's tb3 makes the first predictions
  through Conny's models [G]. → F16, F17
- **2026-08-19** Five-minute update to the PI: BCG predictions written, no
  human ground truth to score them against yet
  (`fasrc:BK/logs/research_logs/pi_5min_2026-08-19/`) [D]. → F17
- **2026-08-25 → 08-26** Josh's tb4: against human BCG-treated cells, both
  scGen and IMPACT-CellOT predictions fit worse than leaving the mouse-treated
  cells unchanged [N]. Josh's last research commit is 08-26 (`josh@5d00f44`)
  [G]. → F17

## The package (2026-09 → 2026-10)

- **2026-09-01** Josh's notebooks copied into this repo (`conny@1530e2f`) [G].
- **2026-09-03** Josh's package skeleton and usage example e24 (`josh@e1fe1b0`)
  [G]. → [F18](experiments/F18-oop-package.md)
- **2026-09-07 → 09-08** OOP files in this repo, `pyproject.toml`, and
  `R2Evaluation` (`conny@cebd146`, `conny@7bb193e`, `conny@109bf12`) [G].
  The same day an AI agent opens and partly merges the PR stack #1–#10 on
  this repo [G], and writes a 237-item package plan that was never executed
  [D]. → F18
- **2026-09-08 → 09-09** `R2Evaluation` reaches Josh's `src` (PR #1, merged
  09-09) [G]. → F18
- **2026-09-17** An AI-built package repo, `speciesost-package`: ten PRs
  opened and merged in one day [G]. → F18
- **2026-09-29 → 10-01** `MMDEvaluation` and tests (`josh@0ba4158`), then the
  scGen planning commit (`josh@6d4925e`) [G]. → F18
- **2026-10-01** The FASRC working tree is copied to
  `speciesOT-backup-2026-10-01` and fresh clones are made. This is inferred
  from folder timestamps [I].
  → [sources.md](sources.md)
- **2026-10-14** `scGenModel` (`josh@3eb6555`); Josh's PR #2 opened, still
  open; PR #11 (an earlier archaeology) opened and closed the next day [G].
  → F18
- **2026-10-15** `TrainingData` train/validation split work, left uncommitted
  in two different copies (Mac and FASRC). → [sources.md](sources.md)
- **2026-10-20** This archaeology.

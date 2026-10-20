# Where everything lives

speciesOT work is spread over six GitHub repositories, three FASRC directories,
and several Mac folders. This page lists each one, what it holds, and whether it
is in sync. It was checked on 2026-10-20; the method is at the bottom.

The short version:

- **Code** is in git, mainly in `JunyiZhou-Conny/speciesOT` (this repo) and
  `JoshuaPrice/speciesOT`.
- **Results** are only on FASRC, in
  `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT-backup-2026-10-01/speciesOT/`
  (called **BK** below). The original working tree
  `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT` no longer exists. Every
  absolute path inside configs, symlinks and older docs that starts with it is
  now broken; the same relative path under BK is the surviving copy.
- **Some code is in no git repo at all**: the late-July ablation scripts and
  part of the autoresearch harness exist only as uncommitted files on FASRC
  (see [At risk](#at-risk)).

Citation prefixes used across `docs/archaeology/`:

| prefix | means |
|---|---|
| `conny:<path>` | this repo at `main` 109bf12 |
| `conny@<sha>` | a commit in this repo |
| `josh@<branch>:<path>`, `josh@<sha>` | `JoshuaPrice/speciesOT` |
| `autoresearch:`, `ablation:`, `ai_package@src:` | the other repos below |
| `fasrc:BK/<path>` | `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT-backup-2026-10-01/speciesOT/<path>` |
| `fasrc:JOSH/<path>` | `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/<path>`, Josh's own FASRC folder (raw atlases, BCG data) |
| `fasrc:/n/<path>` | any other absolute FASRC path |
| `mac:<path>` | a file under `~/Desktop/` on Conny's Mac that is not in git |

## GitHub repositories

| repo | visibility | dates | what it is | state on 2026-10-20 |
|---|---|---|---|---|
| `JunyiZhou-Conny/speciesOT` (this repo) | public | history starts 2026-05-15 (`conny@c342331`, a fresh `git init`); created on GitHub 2026-06-09; last push 2026-10-15 | Conny's research repo: the `hub` CLI, the vendored CellOT code (`cellot/cellot_gpu/`), notebooks, specs, docs, research logs, and the package skeleton in `src/speciesot/` | `main` 109bf12. Branches `pr-0-install-public-package` … `pr-6-reference-bundle` are a stack of AI-written PRs (#1–#10, 2026-09-08). GitHub shows #1, #4 and #6 as merged, but `main` was rewritten afterwards, so none of the stack is on `main` now. PR #11 (an earlier archaeology) was closed unmerged on 2026-10-15. |
| `JoshuaPrice/speciesOT` | private | created 2024-06-16; last push 2026-10-14 | Josh's repository | `main` 5d00f44: Josh's research notebooks, last commit 2026-08-26. `cellot` 5d9a567: Conny's February–August CellOT work inside Josh's repo; it split from `main` at a7f7301 (2026-02-25). `junyi` 1530e2f: a copy of this repo's history (no common ancestor with `main`). Package line, stacked on `main`: `src` 9816d59 → `junyi-r2-evaluation` a823f96 → `MMDEv_Test` 6d4925e → `scgen-model-impl` 3eb6555. PR #1 merged; PR #2 (`MMDEv_Test` → `main`) open. |
| `JunyiZhou-Conny/scgen-cellot-autoresearch` | public | 2026-06-22 → 2026-07-29 | The autoresearch harness for the LPS autoencoder sweeps ([F13](experiments/F13-autoresearch-loop.md)) | 7 commits. Results are only on FASRC. |
| `JunyiZhou-Conny/scgen-cellot-ablation` | private | 2026-06-19 → 2026-06-22 | scGen Fig. 5 reproduction and the 2×2 ablation ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md)) | 2 commits, 65c13a4. The late-July follow-up code was never committed (see [At risk](#at-risk)). |
| `JunyiZhou-Conny/mixhvg-py` | public | 2026-07-30 | Python port of the mixhvg HVG selector. It is GPL-3, which is why it is kept out of this repo (`conny@9b30aa5`). | e332495 |
| `JunyiZhou-Conny/speciesost-package` | private | 2026-09-17 | A package built by AI agents from Josh's skeleton: ten PRs (A–J) opened and merged on the same day | `src` 60d54ab. Not the hand-built package Josh asked for; see [F18](experiments/F18-oop-package.md). |

## FASRC

All under `/n/holylabs/mooney_lab/Lab/junyizhou/` unless noted.

### BK: `speciesOT-backup-2026-10-01/speciesOT/` (225 GB)

A copy of the old working tree made on 2026-10-01. Its `.git` matches this
repo's `main` 109bf12, but 272 tracked files are missing from its working tree.
They are all in git, so nothing is lost there. What BK adds is everything git
ignored:

| path under BK | size | holds |
|---|---|---|
| `scgen-cellot-autoresearch/` | 189 GB | Its own git clone. `results/runs/` has 337 run folders (188 GB, mostly checkpoints), `results/experiments.csv` (338 rows), `results/insights.md`, `ae_study/`, `meeting_david/`. |
| `cellot/cellot_gpu/results/` | 2.6 GB | Every hub-trained scGen / IMPACT-CellOT run (97 folders, 273 `evals.csv`, metric sidecars). |
| `cellot/cellot_gpu/datasets/` | 23 GB | Derived `.h5ad` inputs: atlas holdout cuts, toggle cuts, v07/v08 cuts, uncapped cuts, BCG files, LPS files, CellOT benchmark datasets. |
| `scgen-cellot-ablation/` | 12 GB | Its own git clone with untracked `data/`, `results/` (Stage 0/1, AE follow-up, calibrations, devar) and uncommitted scripts. Its `scgen-reproducibility/` is the theislab scGen code used for Stage 0. |
| `atlas-paper-vae/` | 93 MB | TensorFlow VAEArith on the atlas ("Plan C"), with results. |
| `docs/model_cards/` | — | 176 run cards generated on 2026-05-28 (gitignored in this repo). |
| `logs/`, `sbatch/` | 5.2 MB, 571 KB | Run logs, 538 job scripts, and two untracked research logs: the 2026-08-19 PI slides and the unexecuted 2026-09-08 package plan. |
| `results/external_eval/` | 3.1 MB | Self-tests of the external-target evaluator (2026-07-30). |
| `.cursor-assets/` | 5.7 MB | Five figures from 2026-07-21. |
| `scgen-reproducibility/`, `scgen-cellot-unbalanced/`, `speciesOT/` | 0 | Empty folder skeletons. The real `scgen-reproducibility` is inside `scgen-cellot-ablation/`. The unbalanced-OT result folders are empty, although Slurm shows its jobs completed on 2026-07-21 (five, see [F14](experiments/F14-july-plans-a-to-d.md)), so those outputs are lost. |

### Other FASRC locations

| location | holds | state |
|---|---|---|
| `Conny_speciesOT/` (343 MB) | Clone of this repo | `main` 109bf12, clean, no ignored files |
| `Josh_speciesOT/` (266 MB) | Clone of Josh's repo | `scgen-model-impl` 3eb6555 with three uncommitted files: `src/speciesot/speciesot_core.py`, `e24_src_example.ipynb`, `src/speciesot/Tests/e24_replica.ipynb` |
| `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/` | Josh's raw inputs, e.g. `tabula_sapiens/tabula_sapiens_all.h5ad` (about 45 GB) and `tabula_muris/tabula_muris_all.h5ad` (about 6 GB) | — |
| `/n/netscratch/mooney_lab/Lab/jmprice/bcg_fastqs/` | Josh's raw BCG reads (2026-08-25) | netscratch is scratch space; FASRC purges old files there |
| Conda envs under `/n/home01/jzhou1125/` | `analysis` (py3.12, scanpy 1.12, scgen 2.1.1, POT 0.9.6), `scgen_tf1` (py3.7, TensorFlow 1.15), `CellOT` (py3.9, torch 1.11, editable `cellot`), `CellOT_gpu` (torch 2.3.1), `CellOT_v3` (py3.11) | — |

Slurm accounting goes back only to 2026-03-30. From then to 2026-10-20 a plain
time-window query finds 1,265 jobs. That undercounts: jobs cancelled while
waiting on a dependency are left out unless their states are requested
([F11](experiments/F11-bunne-lps-replication.md) found 72 jobs where the plain
query shows 20). The last speciesOT compute job ran on 2026-08-18.

## Conny's Mac

| folder | what it is | state |
|---|---|---|
| `~/Desktop/speciesOT/Conny_speciesOT` | Clone of this repo | `main` 109bf12, clean |
| `~/Desktop/speciesOT/Josh_speciesOT` | Clone of Josh's repo | `scgen-model-impl` 3eb6555 with two uncommitted files: `src/speciesot/speciesot_core.py` and `e24_src_example.ipynb` |
| `~/Desktop/speciesOT/Conny_speciesOT-archaeology` | Clone used to write `docs/archaeology/` | branch `docs/experiment-archaeology` |
| `~/Desktop/scGen v.s. CellOT` | Clone of `scgen-cellot-ablation` plus 2.1 GB of untracked data, Stage 0/1 results and logs | 65c13a4 |
| `~/Desktop/OptimalTransport/speciesOT` | Old clone of Josh's repo, branch `cellot` at 232b65e | Last fetched 2026-05-02; 19 commits behind on `main` and 13 on `cellot`. Do not work here. |
| `~/Desktop/src/speciesot` | Loose copy of the package core (2026-10-14) | Same code as `scgen-model-impl` 3eb6555 |
| `~/Documents/Codex/2026-09-21/…/outputs/speciesot-workspace` | Codex teaching workspace (`mentor-pr-01`, a copy of `speciesost-package`) | The `mentor-pr-01` worktree is broken: its git directory no longer exists |
| `~/speciesOT_offline_20260614` | — | empty |

## Sync problems

1. **Two different unsaved versions of the package core.**
   `src/speciesot/speciesot_core.py` on branch `scgen-model-impl` has
   uncommitted edits on the Mac (saved 2026-10-15 18:54) and different
   uncommitted edits on FASRC (saved 18:29 the same day). Both are
   hand-written `TrainingData.train_valid_split` work from pair programming. The
   FASRC copy also has an edited `src/speciesot/Tests/e24_replica.ipynb`.
   Neither copy is on GitHub.
2. **This repo's `main` does not contain the merged stack PRs.** See
   [F18](experiments/F18-oop-package.md).
3. **Josh's PR #2 is open and cannot be imported** (a syntax error in
   `speciesot_core.py`); see [F18](experiments/F18-oop-package.md).
4. **The FASRC autoresearch clone is one commit behind GitHub** (170e916 vs
   5d1a7d9) and has 32 uncommitted entries.

## At risk

These exist in exactly one place:

- **Late-July ablation code, uncommitted on FASRC** in
  `fasrc:BK/scgen-cellot-ablation/`: scripts `02b_prepare_hvg_arms.py`,
  `05_stage0_identity_audit.py` … `13_devar_confirmation.py`,
  `stage0_ae_variants.py`, `stage0_metric_helpers.py`,
  `test_stage0_metric_helpers.py`, plus `configs/` and modified
  `04_stage0_fig5_eval.py` and `run_stage0.sh`. This is the code behind
  [F15](experiments/F15-ae-repair-rounds-and-calibration.md).
- **All trained models and metrics**, only in BK.
- **Josh's raw BCG reads** on netscratch.

Suggested actions, for Conny and Josh to decide. Nothing here was done by
this archaeology.

- Commit the uncommitted ablation and autoresearch code (code only, not
  results) to their own repos.
- Choose one of the two `speciesot_core.py` versions and commit it.
- Keep BK in place until the package has reproduced the reference experiments
  in [`reference_experiments.md`](reference_experiments.md).

## Chat histories (leads, not evidence)

These record intent and reasoning. They are not measurements, and they were
used only to find things to check.

- Codex: four speciesOT sessions from September to October 2026
  (`~/.codex/sessions/`), and summaries in `~/.codex/memories/rollout_summaries/`.
- Cursor: agent transcripts under `~/.cursor/projects/*speciesOT*/` and the
  cloud agent that opened PR #11.

## How this was checked

On 2026-10-20 the following were done:

- GitHub: `gh repo view`, `gh api …/branches`, and `gh pr list` for every repo.
- FASRC: `ls`, `du -sh`, read-only `git log` and `git status`, and `sacct` in
  7-day windows.
- Mac: `git status`, `git log`, and `shasum` on every checkout.
- The two `speciesot_core.py` versions were compared with `diff`.

No file was changed anywhere except under `docs/archaeology/`. One side effect:
an early plain `git status` in some checkouts refreshed git's index cache. That
writes only metadata, not file contents. Later checks used
`--no-optional-locks`.

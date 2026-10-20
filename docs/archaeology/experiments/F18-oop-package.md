# F18 · The object-oriented package `src/speciesot`: every version, what works, what is broken

> The aim is a Python package in which one experiment is one YAML file plus four calls (`setup`, `train`, `predict`, `evaluate`), built by hand by Conny with Josh, and judged by whether it reproduces the earlier experiments. Josh wrote a 102-line skeleton on 2026-09-03; Conny then added an R² metric (approved by Josh on 2026-09-08), an MMD metric, a first scGen model class, and on 2026-10-15 uncommitted train/validation-split code. Alongside, AI agents produced two larger versions, a ten-PR stack on Conny's repo (2026-09-08, undone the same evening by a force-push) and a private repo with ten PRs opened and merged in 62 minutes (2026-09-16/17), plus a Codex teaching workspace; none of these is the hand-built package that, by Conny's account, Josh wants, and none was proposed to him. No version can run a real experiment end to end, and none has produced a scientific number: the newest committed scGen model calls a TensorFlow-1 class that the installed library does not have, the open PR #2 does not import, the package's R² equals only a reconstruction check from Stage 0 (not any earlier prediction score), and its one-bandwidth MMD matches no earlier setting. Status: infrastructure, in progress.

| | |
|---|---|
| Period | 2026-09-03 23:02 (Josh's skeleton, `josh@e1fe1b0`) → 2026-10-15 18:54 (last uncommitted edit, Mac file time) [G][C] |
| People | Joshua Price: the skeleton, the merge of PR #1 and the only review (PR #1, "Looks good!") [G]. Junyi (Conny) Zhou: every other package commit in both repos [G]. AI agents wrote the 2026-09-08 stack and its plan, the `speciesost-package` PRs, the Codex teaching workspace and PR #11. The stack and package commits carry Conny's name; PR #11's commit and two unmerged fix branches are by "Cursor Agent" [G][D]. |
| Status | infrastructure |
| Main code | `josh@3eb6555:src/speciesot/speciesot_core.py` (newest commit, branch `scgen-model-impl`); `josh@6d4925e:src/speciesot/speciesot_core.py` (head of open PR #2); `conny:src/speciesot/speciesot_core.py` (Conny's `main`); `mac:speciesOT/Josh_speciesOT/src/speciesot/speciesot_core.py` (uncommitted); S and `ai_package@src:src/speciesot/engines.py` (AI-built) |
| Results live in | no saved results found. No package run wrote a result file. The only executed outputs are notebook cells that print a config dict, an AnnData summary or an import error (`josh@3eb6555:src/speciesot/Tests/e24_replica.ipynb#c3`, `#c6`; `mac:speciesOT/Josh_speciesOT/e24_src_example.ipynb#c0`), the AI stack's plumbing receipts (S `logs/research_logs/media/pr-1-review-atlas-obs.txt`, `pr-3-review-reuse.txt`, `pr-6-review-bcg-predict.txt`), and test logs and probes with fake back ends (`mac-codex:package/docs/learning/evidence/core-tests.txt`, `…/baseline-probes.json`) [N][R]. None holds a metric. |

Citation shorthands:
- **S** = the top of the AI stack in Conny's repo, branch `origin/pr-6-reference-bundle` at `conny@12f7eee`. It contains every stack file. "S `ae.py:105`" means `src/speciesot/ae.py` line 105 at that commit.
- **UM**, **UF** = the uncommitted `src/speciesot/speciesot_core.py` on the Mac (`mac:speciesOT/Josh_speciesOT/src/speciesot/speciesot_core.py`, saved 2026-10-15 18:54) and on FASRC (`fasrc:/n/holylabs/mooney_lab/Lab/junyizhou/Josh_speciesOT/src/speciesot/speciesot_core.py`, saved 18:29). Both sit on branch `scgen-model-impl` at 3eb6555.
- **PLAN** = `fasrc:BK/logs/research_logs/2026-09-08-speciesot-core-populate-plan.md`.
- **mac-codex:** = `~/Documents/Codex/2026-09-21/https-github-com-junyizhou-conny-speciesost/outputs/speciesot-workspace/`.
- **GH** = facts read on 2026-10-20 with `gh pr view`, `gh api …/pulls/<n>/comments` and `gh api repos/JunyiZhou-Conny/speciesOT/activity` (the push log of `main`).
- Times are US Eastern (UTC−4) unless marked Z (UTC).
- "Traced" means I followed the code by reading it. I ran no project code; I only ran `ast.parse` (a syntax check) and a five-line numpy check of matrix behaviour [I].

## The question

There was no scientific question; this is software work.

- **Aim.** An installable package where an experiment is one YAML file and four calls on an `Experiment` object, as in Josh's example notebook "e24" (`josh@e1fe1b0:e24_src_example.ipynb#c1`) [C]. The package will be judged by whether it reproduces earlier experiments. Those are described on [F09](F09-hub-and-metrics-infrastructure.md), [F10](F10-monocytes-floor-ceiling-and-v08.md), [F12](F12-scgen-fig5-stage0-and-stage1.md), [F13](F13-autoresearch-loop.md) and [F16](F16-deployment-models-and-mixhvg.md).
- **How.** By hand. Conny told this archaeology (2026-10-20) that Josh wants Conny to build the package step by step, one function, module and abstraction at a time, rather than have an AI write it. No written statement of this by Josh was found in PR reviews, commit messages or notebooks (searched; not found) [I]. Conny's private AI chat sessions from September record the same intention; they were read as leads only and are not quoted here.

What Josh designed, as far as the record shows:
- Two abstract roles. `AbstractModel` has `setup`, `train` and `predict`; `AbstractEvaluation` has `evaluate` (`josh@e1fe1b0:src/speciesot/speciesot_core.py:9-25`) [C].
- Two data holders, `TrainingData` and `TestData`. Each holds a source (mouse) and a target (human) AnnData read from two `.h5ad` files; `TestData` also has a `batch_corrected = False` flag (`josh@e1fe1b0:src/speciesot/speciesot_core.py:28-42`) [C]. (AnnData = the standard Python container for single-cell data: a cells × genes matrix `.X` plus tables that describe cells and genes.)
- One orchestrator, `Experiment`. It reads the YAML and runs every model and every evaluation on the same test data (`josh@e1fe1b0:src/speciesot/speciesot_core.py:45-83`) [C].
- One baseline, `IdentityModel`: it "predicts" that the human cells look exactly like the mouse test cells (`:86-94`). One placeholder metric, `DummyEvaluation`, which returns 1 (`:97-99`) [C].
- His instructions to Conny, later pasted into the code: "I added the initial classes to the src branch on GitHub … You'll want to run 'pip install -e .' after activating your virtual environment … Example usage with dummy model and evaluation methods are the e24 notebook I made" (`josh@6d4925e:src/speciesot/speciesot_core.py:202-207`) [D].
- His reviews: one in total, "Looks good!" on PR #1 (2026-09-09 01:55Z, GH) [G]. PR #2 has no review [G].
- Read together [I]: a thin, readable layer; models and metrics are swappable subclasses; comparisons are fair because every model is scored on the same test cells; Identity is the do-nothing baseline every model must beat, which is how earlier R² values had to be read too ([metrics.md](../metrics.md) §1).

## Setup

### Data named in the configs

| config | training source → target | test source → target |
|---|---|---|
| Josh's `experiment_config_example_090326.yaml` (not in git; FASRC file time 2026-09-21; keys `training_data`, `test_data`, `models: [IdentityModel]`; **no `evaluations` key**) | Tabula Muris sample `sampled_mouse_shared.h5ad` (1.6 GB) → Tabula Sapiens sample `sampled_human_shared.h5ad` (6.1 GB) | BCG-treated mouse `bcg_treated_scanvi_081826.h5ad` → BCG-treated human `bcg_treated_scanvi_082626.h5ad` |
| `conny:example_debugging.yaml` (adds `evaluations: [R2Evaluation]`) | same | same |
| `josh@3eb6555:src/speciesot/Tests/config.yaml` | same | same |
| `josh@3eb6555:src/speciesot/Tests/toy_config.yaml` | the BCG files | the BCG files |
| S `specs/e24_tiny_identity.yaml` (`conny@7aad392`) | the BCG files | the BCG files |

Sources: `fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/experiment_config_example_090326.yaml` and the files named [C]; sizes PLAN:504 [D], confirmed with `ls` on 2026-10-20.

- The BCG test files hold 251 mouse and 392 human cells on the same 1,000 genes (`josh@main:tb/tb4_eval_first_predictions.ipynb#c5`, `#c6`) [N]. They are two clouds of different size with no cell-to-cell pairing [I]. (BCG = the tuberculosis vaccine; the cells are blood stem cells; see [F17](F17-bcg-application.md).)
- The human training sample has 58,931 cells × 61,759 genes (`josh@3eb6555:src/speciesot/Tests/e24_replica.ipynb#c6`); the mouse sample has 18,024 genes (`#c3`, the `x_dimensions` value) [N]. No version of the package maps orthologs [C]. The only gene-alignment code is the AI stack's `project_genes`, which copies an input onto a saved gene list by name (S `bundle.py:22-45`); Josh's line and the AI package never compare gene names [C]. (Orthologs = the same gene in two species.)
- No committed version splits cells into training and validation sets; the only split code is the uncommitted work in §11 [C].

### Environments (FASRC, checked 2026-10-20)

| env | Python | `scgen` installed | `import speciesot` resolves to |
|---|---|---|---|
| Josh's venv `speciesOT_env` | 3.12.5 | no | `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/src`; its core file is byte-identical to the skeleton `josh@e1fe1b0` |
| `analysis` | 3.12 | 2.1.1, built from theislab GitHub commit d79e1f04 | FASRC `Josh_speciesOT/src` (install record written 2026-10-15 18:34; PLAN:478 says `analysis` had no install on 09-08) |
| `CellOT` | 3.9.5 | no | `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/src`, a folder that no longer exists (set 2026-09-08 13:15) |
| `CellOT_v3` | 3.11 | no | the same missing folder (set 2026-09-08 17:40) |
| `CellOT_gpu` | 3.9.23 | no | not installed |
| `scgen_tf1` | 3.7 | pip `scgen` 2.0.0 (the scvi-tools version) in site-packages; the original TensorFlow-1 `VAEArith` only when the reproducibility code is put first on the path (`conny:atlas-paper-vae/scripts/01_train_vae.py:107-108`) | not installed |

Evidence: the install records in each env [C], e.g. `fasrc:/n/home01/jzhou1125/miniforge3/envs/analysis/lib/python3.12/site-packages/__editable__.speciesot-0.0.1.pth`, `fasrc:/n/home01/jzhou1125/miniforge3/envs/analysis/lib/python3.12/site-packages/scgen-2.1.1.dist-info/direct_url.json`, `fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/speciesOT_env/lib/python3.12/site-packages/__editable__.speciesot-0.0.1.pth`, `fasrc:/n/home01/jzhou1125/.conda/envs/CellOT/lib/python3.9/site-packages/__editable__.speciesot-0.0.1.pth`, the `site-packages` listing of `fasrc:/n/home01/jzhou1125/miniforge3/envs/scgen_tf1` (`scgen-2.0.0.dist-info`; its `scgen/__init__.py` imports `SCGEN` from scvi-tools); Josh's core file hashed with `git hash-object` [C]. On the Mac, `analysis` has no `speciesot` install, and the Mac `cellot` env's editable install (2026-09-29 18:03) points to `/Users/conny/Desktop/speciesOT src/speciesOT/src`, a folder that no longer exists (`/Users/conny/miniconda3/envs/cellot/lib/python3.9/site-packages/__editable__.speciesot-0.0.1.pth`, outside the `mac:` Desktop root) [C].

- Josh's line declares `requires-python = ">= 3.9.25"` (`josh@0ba4158:pyproject.toml:9`). That excludes `CellOT` (3.9.5), `CellOT_gpu` (3.9.23) and `scgen_tf1` (3.7) [C][I]. Conny's `main` says `>=3.9` (`conny:pyproject.toml:13`) [C]. Neither file lists any dependency [C]. Josh's `requirements.txt` (added in `josh@47feafa`, 2026-08-03; 180 lines, 178 of them `==` pins) describes his venv [C][G].

### Metrics in the package, against the research

- `R2Evaluation`: for each gene, the Pearson correlation between predicted cell *i* and true cell *i*, taken across cells in row order; then squared and averaged over genes, skipping genes whose denominator is ≤ 1e-12 (`conny:src/speciesot/speciesot_core.py:115-126`) [C]. Every R² that scored a mouse-to-human or control-to-treated prediction in the earlier work is instead a correlation of **mean** expression profiles across genes, usually squared (scGen paper, hub, autoresearch `r2_all`, tb4) [P][C]; see [metrics.md](../metrics.md) §1. The one earlier metric with the package's formula is Stage 0's reconstruction check `pearson_r2_pergene_mean`, which compares each cell with its own autoencoder reconstruction (same centring, same 1e-12 cut, mean over genes; `fasrc:BK/scgen-cellot-ablation/scripts/stage0_metric_helpers.py:20`, `:42-52`, `:127`) [C].
- `MMDEvaluation`: biased RBF-kernel MMD with one bandwidth, γ = 0.1, on all cells (`josh@0ba4158:src/speciesot/speciesot_core.py:132-147`) [C]. (MMD = maximum mean discrepancy, a distance between two clouds of cells. "Biased" = each cell's similarity to itself is included, so two samples of one distribution score above 0.) The research used the same biased estimator but averaged 50 bandwidths and subsampled n cells with 10 draws; the n lists differed between runs, from 10 up to 1,500 cells (30, 50, 80 was the most common), and some notebooks used full clouds ([metrics.md](../metrics.md) §2) [C].
- Space: the package scores whatever `.X` holds, i.e. raw gene space. There is no latent or decoded frame (decoded = after the autoencoder's reconstruction; [F10](F10-monocytes-floor-ceiling-and-v08.md)) [C].
- No package code ran as a batch (sbatch) job: the last speciesOT compute jobs were on 2026-08-18, before the package existed ([timeline.md](../timeline.md)) [R]. Package code ran only interactively: the e24 notebooks, and agent checks on compute nodes (the stack commits come from host `holy7c06103`, `josh@3eb6555` from `holy8a26602`) [N][G][I].

## What was done and what came out

### Version map

| # | date | where | by | what changed |
|---|---|---|---|---|
| 1 | 09-03 23:02 | `josh@e1fe1b0`; copied unchanged as `conny@cebd146` (09-07 22:00) | Josh | skeleton, `__init__.py`, e24 notebook |
| 2 | 09-08 14:39 / 17:44 | `conny@7bb193e`, `conny@109bf12` (Conny's `main` today) | Conny | `pyproject.toml`; `R2Evaluation`; `example_debugging.{py,yaml}` |
| 3 | 09-08 15:05–16:05 | S: branches `pr-0` … `pr-6`, PRs #1–#10 | AI agent, in Conny's account | seven feature commits: wiring, a data handle, job plans and wrappers around hub and CellOT code |
| 4 | 09-08 (file time 16:30) | PLAN | AI agent | 590-line plan for that stack |
| 5 | 09-08 18:12 | GH push log | Conny's account | `main` force-pushed back to `cebd146`, then version 2 pushed |
| 6 | 09-08 18:34 → 21:56 | `josh@a823f96` → `josh@9816d59` (branch `src`; PR #1) | Conny; merged by Josh | same core file as `conny@109bf12` |
| 7 | 09-16 23:47 → 09-17 00:49 | branch `src` of `speciesost-package` (60d54ab; `ai_package@src:src/speciesot/`), PRs A–J | AI agent, commits as Junyi Zhou | registries, injected "engines", 38 tests |
| 8 | 09-21 → 09-29 | mac-codex: `mentor-pr-01` | Codex and Conny | results list; MMD draft |
| 9 | 09-29 18:16 | `josh@0ba4158` (branch `MMDEv_Test`) | Conny | `MMDEvaluation`, first test, `pyproject.toml` |
| 10 | 10-01 16:29 | `josh@6d4925e` (head of PR #2) | Conny | `scGenModel` stub with a syntax error |
| 11 | 10-14 14:58 | `josh@3eb6555` (branch `scgen-model-impl`) = `mac:src/speciesot` | Conny | config-driven setup; `scGenModel` on `scgen.VAEArith` |
| 12 | 10-14 18:03 → 22:29 | PR #11 on Conny's repo, closed | Cursor cloud agent | an earlier archaeology |
| 13 | 10-15 18:29 / 18:54 | UF / UM, uncommitted | Conny | `TrainingData.train_valid_split` |

Sources: `git log` of both repos and GH [G]. Byte identity [G]: `josh@e1fe1b0` and `conny@cebd146` have the same blobs for all three files; `conny@109bf12`, `josh@a823f96` and `josh@9816d59` have the same core file; `josh@3eb6555` and `mac:src/speciesot` have the same seven files.

### 1. Josh's skeleton (2026-09-03)

- Commit `josh@e1fe1b0` by Joshua Price from a FASRC node: `e24_src_example.ipynb`, `src/speciesot/__init__.py` (exports `Experiment`) and a 102-line `speciesot_core.py` [G]. No `pyproject.toml` was committed, although Josh's message tells Conny to `pip install -e .` [G][D]. His FASRC checkout has a `pyproject.toml` that is in none of his commits (file time 2026-09-21 15:11:49, the same second as his example YAML); it is byte-identical to the one Conny committed in `conny@7bb193e` [C][G]. His venv's editable install dates from 2026-09-03 23:00:33 (`.pth` file time), and an editable install needs a build file, so some build file existed in his checkout that evening; the 09-21 time is probably a later copy or touch [C][I].
- Implemented [C]: `Experiment.setup` builds both data holders and an `IdentityModel` when the YAML lists it (`josh@e1fe1b0:src/speciesot/speciesot_core.py:58-70`); `train`, `predict` and `evaluate` loop over models (`:72-83`).
- Stubs: `DummyEvaluation` (`:97-99`) [C].
- Gaps, traced [C][I]:
  - `self.evaluations` is created empty (`:52`) and never filled, so `evaluate()` does nothing.
  - `predict()` throws away what the models return (`:76-78`).
  - `evaluate()` calls `evaluation.evaluate(model, self.test_data)` (`:83`), but `DummyEvaluation.evaluate` takes only `self` (`:98`). It would raise `TypeError` if it ever ran.
  - The abstract `predict(self)` has no data argument, while `IdentityModel.predict(self, test_data)` has one (`:19`, `:93`).
  - The data holders inherit `abc.ABC` but have no abstract methods (`:28`, `:36`).
  - Both holders read whole files when they are created. With Josh's example YAML that is 7.7 GB of files on disk (1,562,533,262 + 6,098,345,094 bytes for the two Tabula samples, `ls -l` on FASRC; PLAN:504 gives 1.6 and 6.1 GB) [C][D]; the memory needed was not measured [I].
- Config format: `training_data.source_training_data_path`, `.target_training_data_path`, `test_data.source_test_data_path`, `.target_test_data_path`, and `models` as a list of class names [C].
- Tests: none [C]. Saved outputs: e24 cell 0 (the import) has execution count 1 and no error; cell 1 (the four calls) has no saved execution (empty execution count, no output), which shows it was not run in the saved session but does not prove it never ran (`josh@e1fe1b0:e24_src_example.ipynb#c0`, `#c1`) [N][I].

### 2. R2Evaluation, by hand, on both repos (2026-09-07 → 09-09)

- 2026-09-07 22:00: Conny copies the skeleton into Conny's repo (`conny@cebd146`, "Added files for OOP architecture") [G].
- 2026-09-08 14:39: `conny@7bb193e` adds `pyproject.toml`, the same bytes as the uncommitted file in Josh's checkout, which names "Joshua Price" as author [G][C].
- 2026-09-08 17:44: `conny@109bf12` "Implemented R2Evaluation" [G]:
  - `R2Evaluation` (`conny:src/speciesot/speciesot_core.py:115-126`) [C];
  - `AbstractEvaluation.evaluate(predicted, truth)` no longer abstract (`:23-25`) [C];
  - `predict()` keeps the predictions (`:85-88`); `evaluate()` passes each prediction and the human test cells to each evaluation (`:91-95`) [C];
  - `setup()` adds `R2Evaluation` when the YAML lists it (`:76-78`) [C];
  - `conny:example_debugging.py` and `conny:example_debugging.yaml` are written to run Identity + R² on Josh's files (no saved run found); the script's YAML path points into the deleted working tree (`conny:example_debugging.py:6`) [C].
- 18:34: the same core file goes to Josh's `src` branch as `josh@a823f96` (PR #1). Josh approves "Looks good!" at 21:55 and merges as `josh@9816d59` [G]. The PR text ("## Summary … ## Test plan" with tick boxes) is in the style of an AI agent and says "Copy Junyi's current src/speciesot/speciesot_core.py onto Josh's src history" [D]. Who typed which line is not recorded [I].
- What it cannot do, traced:
  - It pairs predicted cell *i* with true cell *i*. Mouse-to-human predictions have no such pairing, so it reproduces no earlier prediction R² ([metrics.md](../metrics.md) §1) [C][I]. Its formula is that of Stage 0's reconstruction check (Setup), so it could reproduce `pearson_r2_pergene_mean` if given a cell matrix and its own reconstruction in the same row order [C][I].
  - `setup()` reads `experiment_spec['evaluations']` unconditionally (`conny:src/speciesot/speciesot_core.py:77`). Josh's example YAML has no such key, so `setup()` raises `KeyError` on it [C][I].
  - `evaluate()` drops the scores and returns `None` (`:91-95`) [C].
  - Unequal cell numbers (251 vs 392 on the e24 test files) raise "operands could not be broadcast" at `:123` [C][I].
  - Sparse `.X`: `.mean(0)` returns a numpy *matrix*, and for matrices `*` and `**` are matrix products, so `:121-124` raise shape errors [I] (checked on a 4 × 3 random sparse matrix). Whether the BCG files' `.X` is sparse was not checked.
  - Genes with zero variance are dropped silently (`:125`); if all genes are constant the result is `nan` (Codex probe `all_constant_genes`, `mac-codex:package/docs/learning/evidence/baseline-probes.json`) [C][R]. Gene names are never compared [C]. Squaring makes a perfectly anti-correlated gene score 1 [I].
- Tests: none [C].

### 3. The AI stack on Conny's repo: PR-0 … PR-6 = GitHub #1–#10 (2026-09-08, 15:05–16:05)

- Seven branches, all starting at `cebd146` [G]. Seven feature commits by "Junyi Zhou" from a FASRC node between 15:05 and 16:05; ten PRs opened between 19:05Z and 20:05Z [G]. In `src/`, `tests/`, `specs/` and `pyproject.toml` they add 1,134 lines and remove 32 in 15 files; the whole diff, with the e24 notebook, `docs/mentor_runbook.md` and the review receipts and videos, is 23 files, +1,250/−91 (`git diff --shortstat cebd146 origin/pr-6-reference-bundle`, with and without a path filter) [G].
- Signs of an agent run [D]: PR bodies with Cursor-generated summaries; Cursor Bugbot (an automatic reviewer) posted "Bugbot couldn't run - usage limit reached" on all ten PRs; verification described as "ten live lanes" with receipts in `/tmp/swarm-pr-N/`; PR bodies that wait for "the operator" to click merge (#2, #5, #10); comments posted in Conny's account at 20:30Z that say which PR to click next (#8, #9, #10) (GH). Seven of the PRs were merged 37 seconds to 11 minutes after they were opened (GH) [G]. Rule of the program: "wrap existing functions. Do not copy CellOT or scGen math" (PLAN:3) [D].

| PR | GitHub | adds (at S) | what it really does, traced [C] |
|---|---|---|---|
| PR-0 `conny@7aad392` | #1, merged to `main` 19:17Z | wires `DummyEvaluation`; `predict`/`evaluate` return values; `specs/e24_tiny_identity.yaml`; 2 tests | Always appends `DummyEvaluation` (S `speciesot_core.py:166`). Keeps Josh's call shape `evaluate(model, test_data)` (S `:86-89`), unlike Conny's `(predicted, truth)`. Returns only the **last** prediction and score (S `:183-194`). Trains and tests on the same BCG files. |
| PR-1 `conny@0646a8b` | #2 into PR-0; #4 to `main` 19:33Z | `DatasetHandle` | Counts cells with h5py instead of loading the file. `load_X` refuses atlas file names and any file with more than 2,000 cells (S `speciesot_core.py:62-69`), so no real training set can be loaded. `source_adata` re-reads the file on every access (S `:99-105`). |
| PR-2 `conny@fb6591f` | #3 into PR-1; on `main` via #6 19:39Z | `JobPlan`, `AutoEncoderModel` | `train()` returns the text of the hub's Slurm job chain unless `local=True` (S `ae.py:105-108`). Local training refuses Python ≥ 3.12 (S `:113-117`). `predict` raises `NotImplementedError` (S `:150-151`). Imports the hub by putting the repository root on `sys.path` (S `:11-38`), so it works only inside a checkout of Conny's research repo [I]. |
| PR-3 `conny@d36b761` | #5 into PR-1; on `main` via #6 | `FrozenAE` | Loads a trained CellOT autoencoder folder and refuses a stale `scgen_shift.pt` by comparing SHA-256 hashes of `model.pt` and of the gene list (S `ae.py:166-203`). `encode`/`decode` reload the model on every call (S `:256-272`). |
| PR-4 `conny@2f2db44` | #7 into PR-1; #9 to `main`, open | `CellOTModel` | `train()` returns a job plan (S `cellot_model.py:53-64`). `fit` builds a new, **untrained** ICNN with two layers of 32 units and returns its output; nothing is trained (S `:66-94`). `predict(inputs)` expects a tensor, but `Experiment.predict` passes a `TestData` (S `:96-110`; S `speciesot_core.py:183-187`) [I]. (ICNN = input-convex neural network, CellOT's transport map.) |
| PR-5 `conny@83cff23` | #8, open | `DecodedFrameEvaluation` | Reads the sidecar CSVs that the hub already wrote and computes nothing (S `evaluation.py:51-114`); headline row `ncells` = 80 (S `:51`). Title calls this metric the `north-star`, i.e. the one headline number ([F10](F10-monocytes-floor-ceiling-and-v08.md)). |
| PR-6 `conny@12f7eee` | #10, open | `ReferenceBundle`, `project_genes` | Prediction = match genes by name (first duplicate wins; missing genes filled with 0; S `bundle.py:22-45`) → encode → CellOT transport → decode (S `:162-186`). Imports `cellot.transport` before adding CellOT to `sys.path` (S `:169`, `:171`), so it works only where CellOT is installed [I]. `decoded_score` always raises (S `:188-193`). |

- Numbers quoted in the PRs, checked where possible:
  - PR #8 quotes fgc_dec 0.897 and mean_js 0.449 for the M1 v08 IMPACT run [D]. The sidecars hold `frac_gap_closed_decoded` 0.8973777541337926 at n = 80 and `mean_js` 0.449233156915886 (`fasrc:BK/cellot/cellot_gpu/results/hvg_pearson_residuals_m1_v08_ood/impact_cellot/evals_ood_data_space/decoded_frame_metrics.csv:4`, `…/extended_metrics.csv:4`) [R]. The wrapper reads them correctly.
  - PR #2: the human atlas has 1,136,218 cells (and 61,759 genes); the old eager loader failed with "Unable to allocate 13.2 GiB" under `ulimit -v 4GB` (receipt `logs/research_logs/media/pr-1-review-atlas-obs.txt:3-13` in `conny@0646a8b`) [R].
  - Real-library runs on FASRC, plumbing only [R]: `FrozenAE` loaded the trained autoencoder `…/results/atlas_full_pearson_residuals/scgen`, found the same gene-axis hash as the bake script (`afab9f6f…`), took `code_means` from `last.pt` and left `model.pt` unchanged (S `logs/research_logs/media/pr-3-review-reuse.txt`); `ReferenceBundle.predict` pushed the BCG mouse cells through that autoencoder and its CellOT model and returned 251 × 1,000 without opening the atlas (S `logs/research_logs/media/pr-6-review-bcg-predict.txt:1-3`; PR #10 body). No metric was computed on that prediction [R][I].
  - PR #1: "four verbs on the tiny yaml return `1` and 251 cells" [D]. The `/tmp/swarm-pr-*` receipts were not found: they were written to `/tmp` of a compute node, which is not kept, and the FASRC backup (BK) has no `swarm-pr` folder (`find`, four levels) [I].
- Tests: 15 functions in 7 files [C]. `tests/test_frozen_ae.py:8-10` points into the deleted working tree, so it now fails [C][I]. `tests/test_dataset_handle.py:7-9` and `tests/test_speciesot_import.py` (through `specs/e24_tiny_identity.yaml`) read Josh's BCG and atlas files, which still exist; `test_ae_jobplan.py` and `test_cellot_requires_grad.py` need the research repo's `specs/` and `cellot/cellot_gpu/`; `test_decoded_eval.py` and `test_gene_project.py` are synthetic [C]. The tests check plumbing (types, file names, refusals), not model output [C].

### 4. The populate plan (2026-09-08)

- PLAN is a 590-line checklist for PR-0 … PR-6. It has 237 boxes, none ticked (counted with `grep`) [D].
- **A lead turned out false.** The survey lead said the plan was "never executed". Its own last section, "Landing status 2026-09-08" (PLAN:574-590), lists the same seven commits (`7aad392` … `12f7eee`), with #1, #4 and #6 merged into `main` and #9 "landing"; git and GH confirm this [D][G]. The boxes were simply never ticked. The plan is also stale in places: Appendix A, written before the work, says "No prototype ran this turn. The operator forbade implementation, commit, push, and sbatch" (PLAN:466), while the last appendix records the landed commits; the file was last saved at 16:30, after all seven commits [D][I].
- Useful content [D]: rejected alternatives (PLAN:488-494), e.g. "Treat Josh's 5-key yaml as the long-term spec. Rejected" and "One env that installs everything … Rejected because CellOT (torch 1.11, scanpy 1.8.1), analysis (scanpy 1.12), CellOT_gpu (Python 3.9.23), and Josh's venv (Python 3.12, scanpy 1.11.5, torch 2.11) already disagree"; risks such as two gene-matching rules (first-wins vs last-wins, PLAN:512) and the scGen shift being computed without `eval()` (PLAN:518). "Operator" in the plan means Conny, the human who clicks merge [I].

### 5. `main` is force-pushed back (2026-09-08 18:12)

- GH push log of `main` [G]: 19:17:00Z merge #1 → `fb8507e`; 19:33:08Z merge #4 → `f703fac`; 19:39:54Z merge #6 → `ac18274`; **22:12:38Z force-push `ac18274` → `cebd146`**; 22:16:57Z push `cebd146` → `109bf12` (version 2).
- So `main` today is `cebd146` + `7bb193e` + `109bf12`. GitHub's compare of `ac18274` with `main` says "diverged, 2 ahead, 10 behind" [G]. The three merge commits are not in the local clone [G].
- Effect: GitHub shows #1, #4 and #6 as merged, but their code is not on `main`; #8, #9 and #10 are still open [G].
- No stated reason was found in commit messages, PR comments or research logs (searched `fasrc:BK/logs/research_logs/` for "force" and `cebd146`) [I]. Twenty-one minutes after the force-push (22:34Z) Conny opened PR #1 on Josh's repo with their own R² [G]. The record suggests Conny chose the hand-made line over the agent's stack [I]. In the backup, 258 files within three folder levels carry file times of 2026-09-08 18:40–18:55, among them `fasrc:BK/AGENTS.md` and `fasrc:BK/example_debugging.py` (18:47, although committed at 17:44), which fits a reset or fresh checkout of the FASRC working tree half an hour after the force-push (`find -newermt` on the mirror; `ls -l` on FASRC) [R][I].

### 6. The AI-built private repo `speciesost-package` (2026-09-16 23:47 → 09-17 00:49)

- Repository created 2026-09-17 03:42Z, starting from Josh's `src` (`9816d59`). Ten PRs (A–J) were opened and merged between 03:47Z and 04:49Z, i.e. within 62 minutes; each was merged 2–8 minutes after it was opened [G]. They add 1,823 lines and remove 130 in `src/`, `tests/` and `pytest.ini` [G]. Commits are by "Junyi Zhou" (Emory e-mail, so probably from the Mac [I]); PR J's test log ran `.venv/bin/python` with warnings from `/Users/conny/miniconda3/envs/analysis` (PR J body); eight of the ten PR bodies (all but F and G) state "No push to `JoshuaPrice/speciesOT`" [G][D].
- Why it exists: its purpose is recorded only in Conny's private AI chat sessions, which are not quoted here. What the public record shows: ten PRs with tests, merged without review by Josh, and never proposed to his repository (eight of the ten PR bodies say "No push to `JoshuaPrice/speciesOT`") [G][D].
- Final layout at `ai_package@src:src/speciesot/` [C]: `experiment.py` (77 lines), `models.py` (163), `engines.py` (424), `evaluations.py` (55), `pairing.py` (54), a 72-line re-export shim `speciesot_core.py`, and `__init__.py`.
- What is real [C]:
  - `Experiment` looks model and evaluation names up in registries (`ai_package@src:src/speciesot/experiment.py:49-58`), passes the training data to `train` (`:61-63`), and stores and returns the scores (`:71-77`). Files are still read eagerly (`:10-24`).
  - `R2Evaluation` keeps the paired formula but first refuses sparse `.X`, unequal cell or gene numbers, and different gene names (`ai_package@src:src/speciesot/pairing.py:10-54`). On the e24 BCG files it would raise `R2PairingError` (251 ≠ 392) [I].
- What is not real [C]:
  - `CellOTModel` and `ScGenModel` built from the YAML get "identity engines" that copy their input (`ai_package@src:src/speciesot/models.py:94`, `:143`). The YAML can only list names (`experiment.py:50-51`), so there is no way to request a real model or set a hyperparameter.
  - `BunneCellOTEngine.fit` ignores the arrays it is given and trains from its config's own data path (`ai_package@src:src/speciesot/engines.py:156-167`). Without a checkpoint it stores `object()` as the model (`:175-176`). `transport` passes numpy arrays (`:178-179`), but CellOT's transport needs a torch tensor: the Codex probe got "'numpy.ndarray' object has no attribute 'requires_grad_'" [R] (`mac-codex:package/docs/learning/evidence/baseline-probes.json`). That probe ran CellOT's small transport function extracted from the source, with a stand-in model, because CellOT was not installed (`mac-codex:package/docs/learning/09-verification.md`, method list) [D].
  - `TheislabScGenEngine` wraps the scvi-tools `SCGEN` with default settings and labels every cell with one cell type, `"cell"`, so scGen's cell-type balancing does nothing (`engines.py:273-302`, `:313-359`). Prediction builds a bare AnnData without the fields registered in training (`:372`) [C].
- Cursor Bugbot found three bugs, all posted **after** the merges: two on PR G at 04:34:24Z (merged 04:28:24Z) and one "High Severity" on PR I at 04:43:55Z (merged 04:42:14Z) (GH) [G]. Fix branches by "Cursor Agent" (`ai_package@c625dd9`, `ai_package@a445910`) were never merged into `src` [G].
- Tests: 38 functions in 9 files [C]. "38 passed, 3 warnings" in an isolated venv on 2026-09-21 in which `cellot`, `scgen` and `torch` were **not installed** (`mac-codex:package/docs/learning/evidence/core-tests.txt`, `…/verification.json`) [R]. The scGen tests use a fake `SCGEN` class (`ai_package@src:tests/test_scgen_model.py:117-137`) [C].
- It cannot be installed: there is no `pyproject.toml`; tests find the code through `pytest.ini` (`pythonpath = src`) [C]. It has no MMD, because it branched before `josh@0ba4158` [G]. No `docs/` folder exists on branch `src` (not found; `git ls-tree`) [C].

### 7. The Codex teaching workspace (2026-09-21 → 09-29)

- A Codex session built `mac-codex:` with three parts: `package/` (a git worktree of `speciesost-package` at `60d54ab`, with its own venv and nine numbered tutorials in Chinese in `docs/learning/`), `research-reference/` (a clone of Conny's repo at `109bf12`) and `mentor-pr-01` (a git worktree of Josh's `9816d59`, branch `learn/01-evaluation-results`) (`mac-codex:START-HERE.md`; `…/evidence/verification.json`; `mac-codex:package/.git`; `mac-codex:research-reference/.git/config`) [D][R][C].
- `mentor-pr-01/.git` points to `/Users/conny/Desktop/speciesost-package-work/…`, which no longer exists, so its git history cannot be read [C].
- The first candidate change, "PR-01": store and return the scores (`mac-codex:PR-01-body.md`) [D]. Three tests with hand-computed scores 0.625 and 0.25 passed (`mac-codex:mentor-pr-01/tests/test_experiment_results.py:21-37`; `…/evidence/mentor-pr-tests.txt`) [C][R]. It was never committed or sent to Josh: as of 2026-09-21 the workspace's own verification note records no new commit, push or PR (`mac-codex:package/docs/learning/09-verification.md`) [D], and no later commit in Josh's repo stores the scores [C]. Josh's line still drops the scores (`josh@3eb6555:src/speciesot/speciesot_core.py:141-145`) [C].
- The working copy saved 2026-09-29 17:38 [C]:
  - `self.experiment_spec['modesals']` (`mac-codex:mentor-pr-01/src/speciesot/speciesot_core.py:74`): a typo, so `setup()` raises `KeyError`.
  - `MMDEvaluation.evaluate` calls `self.mmd_distance(self, …)` on a static method (`:153`): four arguments for three, so `TypeError`. The committed version 38 minutes later is correct (`josh@0ba4158:src/speciesot/speciesot_core.py:147`).
  - Its `tests/test_evaluations.py` is byte-identical to `josh@0ba4158:src/speciesot/Tests/test_evaluation.py` (same blob `f490c5c`) [C].
- The MMD class was probably written here by hand [I]: the workspace holds a small practice file on Python's `self` saved on 2026-09-24 (`mac-codex:mentor-pr-01/test.py`) [C].
- The Codex audit's 13 probes on the AI package [R] (`baseline-probes.json`): the identity prediction is the same object as the test input; named models default to copies; running the notebook cells twice doubles models and evaluations (2, 2, 4 predictions, 8 scores); CellOT training arrays are not forwarded; a missing checkpoint still "transports"; the scGen prediction has no `obs` columns.

### 8. MMDEvaluation, the scGen stub and PR #2 (2026-09-29 → 10-14)

- `josh@0ba4158` (2026-09-29 18:16, GitHub no-reply e-mail, so probably from the Mac [I]) [G]:
  - `MMDEvaluation` (`josh@0ba4158:src/speciesot/speciesot_core.py:132-147`): scikit-learn `rbf_kernel`, biased estimate, one γ (default 0.1). Not added to `Experiment.setup` [C].
  - `src/speciesot/Tests/test_evaluation.py`: one test, identical 3 × 2 inputs → 0, plus a module-level `print` (`josh@0ba4158:src/speciesot/Tests/test_evaluation.py:11-22`) [C]. Any estimator of the form xx + yy − 2xy gives exactly 0 when x equals y, so the test cannot catch bias or bandwidth errors [I].
  - `pyproject.toml` with `requires-python = ">= 3.9.25"` and no dependencies [C].
- 2026-10-01: the work moved from evaluation classes to the scGen model; PR #2, opened on 2026-10-14, says it was opened "so that we can move forward to scGenModel building" (PR #2 body) [D]. `josh@3eb6555:src/speciesot/speciesot_core.py:16` imports `dataclass` and never uses it [C].
- `josh@6d4925e` (16:29) [G][C]:
  - `class scGenModel` with `self.config = ` and nothing after it (`josh@6d4925e:src/speciesot/speciesot_core.py:147`). `ast.parse` reports `SyntaxError` at line 147, so **`import speciesot` fails on this commit** [C][I].
  - An empty `src/speciesot/Tests/config.yaml`; a placeholder "# setup MMD" (`:87`).
  - The intended scGen settings, pasted as comments (`:118-143`), are lines 31-55 of the hub spec `conny:specs/m1_modern.yaml`: CellOT-autoencoder scGen, 256 × 256, latent 50, lr 0.001, batch 256, 50,000 iterations.
  - Josh's instructions (`:202-207`) and three note lines "vpn setup / unit testing / system testing" (`:199-201`).
- PR #2 (opened 2026-10-14 14:56; `MMDEv_Test` → Josh's `main`; 5 commits, 6 files, +305 lines; open; no review) (GH) [G]. Body: "R2 and MMD Evaluation framework added from a month ago. R2 needs some attention from future when actually running these metrics" and "This pull request is set up so that we can move forward to scGenModel building without keep editing stuff on MMDEv_test" [D]. Its head is the commit that does not import [C].

### 9. scGenModel on the TensorFlow-1 API (`scgen-model-impl`, 2026-10-14)

- `josh@3eb6555`, 14:58, from a FASRC node, two minutes after PR #2 opened. It is in no PR [G]. The same seven files exist on the Mac as `mac:src/speciesot` and inside `mac:src.zip` (17:33) [G][C].
- What changed [C]:
  - `models` in the YAML becomes a mapping from class name to hyperparameters (`josh@3eb6555:src/speciesot/Tests/config.yaml:30-40`); a new `experiment.experiment_export_path` (`josh@3eb6555:src/speciesot/speciesot_core.py:86`).
  - `use_all_genes` overwrites the input size with the mouse gene count (`:97-104`).
  - `MMDEvaluation` is now wired in (`:126-128`); `AbstractEvaluation.evaluate` is abstract again (`:54-57`); `AbstractModel.train(training_data)` and `predict(test_data)` gain arguments (`:42-48`).
  - `scGenModel` (`:212-294`): `__init__` copies nine config keys (`:214-225`); `setup` builds `scgen.VAEArith(...)` (`:247-258`); `train` defines helpers, encodes with the **untrained** network, computes `delta` into a local variable, and never trains (`:261-285`); `predict` uses names that do not exist (`_dense`, `mouse_ood`, `human_ood`) and would then return the mouse cells (`:287-294`).
  - Next to it, a commented-out sketch of the scvi-tools API (`scgen.SCGEN.setup_anndata(...)`, `:232-244`). The comment at `:10-14` still says setup/train/predict "are still stubs".
- `requirements.txt` pins `scgen` to theislab GitHub commit d79e1f04 (`josh@3eb6555:requirements.txt:140-143`) [C]. That exact commit is the one installed in `analysis`. It exports only `SCGEN` and `SCGENVAE`, and the string `VAEArith` appears nowhere in it (`fasrc:/n/home01/jzhou1125/miniforge3/envs/analysis/lib/python3.12/site-packages/scgen/__init__.py`; `grep -r` of the package folder) [C]. `VAEArith` is the TensorFlow-1 class of the original scGen code. In this project it was used by Stage 0 and its follow-ups ([F12](F12-scgen-fig5-stage0-and-stage1.md), [F15](F15-ae-repair-rounds-and-calibration.md); `fasrc:BK/scgen-cellot-ablation/scripts/run_stage0.sh:24-32`) and by Plan C (`conny:atlas-paper-vae/scripts/01_train_vae.py:107-160`; [F14](F14-july-plans-a-to-d.md)), always under env `scgen_tf1` [C]. So `setup()` fails in every env that can install this package: `AttributeError` where scgen 2.x is installed (`analysis`), `ModuleNotFoundError` where it is missing (Josh's venv, `CellOT_v3`) [I].
- **One class, three scGens** [C]: the pasted config is the CellOT-autoencoder scGen of the hub (§8); the code calls the TensorFlow-1 `VAEArith` of the paper; the pinned library is the scvi-tools `SCGEN`. See [models.md](../models.md).
- Settings in `Tests/config.yaml:33-40` [C]: hidden units [256, 256], `z_dimension` 50, `alpha` 0.5, `dropout_rate` 0.2, `lr` 0.001. `VAEArith` hard-codes two hidden layers of 800 units in encoder and decoder (`fasrc:BK/scgen-cellot-ablation/scgen-reproducibility/code/scgen/models/_vae.py:82`, `:86`, `:109`, `:113`) and the call never passes `hidden_units` (`josh@3eb6555:src/speciesot/speciesot_core.py:252-258`) [C]. The paper text only calls α a hyperparameter (its values are in Supplementary Table 1, not in the text we have) [P]. The original code trains the species model with `alpha=0.00005` (`fasrc:BK/scgen-cellot-ablation/scripts/run_stage0.sh:30`; `mac:scGen v.s. CellOT/scgen-reproducibility/code/train_scGen.py:195`), which Plan C copies (`conny:atlas-paper-vae/configs/m2_v08.yaml:28`); `VAEArith`'s own default is 0.001 (`_vae.py:52`) [C]. So `alpha` 0.5 is 10,000 times the value used for the species model [I].
- Bugs, file:line, traced [C][I]:
  - `:104` writes `x_dimensions`, `:220` reads `x_dimension`, `:253` uses `self.x_dimensions`, which is never set → `AttributeError`. The two YAMLs disagree too: `Tests/config.yaml:37` has `x_dimension`, `Tests/toy_config.yaml:19` has `x_dimensions`.
  - `:86` needs an `experiment` section, which `toy_config.yaml` and Josh's example YAML lack → `KeyError`.
  - `:97-98` index `models` by name; a list-format `models` (Josh's YAML) would give `TypeError`, though on Josh's YAML the `KeyError` at `:86` comes first.
  - `:101` reads `use_all_genes` from every dict config → `KeyError` if absent.
  - `config.yaml:31` and `toy_config.yaml:13` write `IdentityModel: None`; YAML reads that as the string "None", not as empty. It is harmless here only because strings are skipped at `:101`.
  - `:133` calls `model.train()` without data; `scGenModel.train` requires it (`:261`) → `TypeError`.
  - `:141-145` still drop the scores; `R2Evaluation` (`:305-316`) is unchanged.
  - Gene axes: `x_dimensions` was 18,024 (mouse) while the human file has 61,759 genes (`josh@3eb6555:src/speciesot/Tests/e24_replica.ipynb#c3`, `#c6`) [N]. Even a working network would be fed two different gene lists [I].
  - `Tests/config.yaml:2` and `Tests/test_model.py:5` point into `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT`, which no longer exists.
- Tests: `Tests/test_model.py` has no test function. It calls `setup()` at import (`josh@3eb6555:src/speciesot/Tests/test_model.py:5-8`), so `pytest` would run it while collecting [C][I]. The notebook `Tests/e24_replica.ipynb` cell 3 printed a five-key config without `z_dimension`, `alpha` or `model_path`, so it ran against an older config and older code than the commit holds [N][I]. It is still the only saved sign that some version's `setup()` finished on the real files: it returned with two models, after reading both Tabula samples and the BCG test files named in `Tests/config.yaml` (`#c3`) [N][I]. The commit also keeps, commented out, the `VAEArith` training block of `conny:atlas-paper-vae/scripts/01_train_vae.py:142-159` (`josh@3eb6555:src/speciesot/speciesot_core.py:190-207`) [C].

### 10. PR #11, an earlier archaeology (2026-10-14)

- Opened 18:03 by a Cursor cloud agent (branch `cursor/experiment-archaeology-briefs-3575`), closed unmerged at 22:29 (2026-10-15 02:29Z) [G]. Files: `docs/learning/experiment-archaeology.md` (148 lines, one row per notebook for 83 notebooks), five "episode briefs", a citation checker (GH, commit 63af136, read through the GitHub API) [G].
- Its claims [D]: "Zero notebooks are yes", i.e. no notebook is the only copy of a scGen train, test or evaluate procedure; "Three programs share the word scgen": `src/speciesot` (imports neither library), the hub's CellOT autoencoder path, and the Lotfollahi package (shown through the `atlas-paper-vae` scripts); and the 2026-10-14 upload `src_aa1d.zip` (not in git) "stubs `scgen.VAEArith`" (PR #11 body; `docs/learning/experiment-archaeology.md`, last section, at 63af136). These agree with the code, except that PR #11 says the stub "imports the TensorFlow package": in every env that can install the package, `import scgen` loads the scvi-tools version or fails (§9) [C]. It misses a fourth program, the scvi-tools `SCGEN` that `requirements.txt` pins and the AI package wraps [C]. The zip it read was probably `mac:src.zip` (same core file) [I].

### 11. Uncommitted train/validation split (2026-10-15)

- Two copies, not on GitHub [G]: UF (FASRC clone `Josh_speciesOT`; core saved 18:29; `e24_src_example.ipynb` 18:29; `src/speciesot/Tests/e24_replica.ipynb` 18:32) and UM (Mac; core 18:54; e24 18:28) (file times) [C].
- Both add to `TrainingData` [C]:
  - `train_valid_split(self, adata, random_state, valid_size)` (UM:30-43; UF:30-48);
  - `toggle_ood_split(adata, holdout, key, test_size, random_state, stratify, mode)`, copied verbatim from `conny:atlas-paper-vae/scripts/01_train_vae.py:45-61` (UM:54-70; UF:58-74);
  - in `scGenModel.train`, the training block of `conny:atlas-paper-vae/scripts/01_train_vae.py:151-160` (UM:327-336; UF:327-336).
- The copies differ [C]: UF builds an unused `split` Series and has a dead `pass` (UF:35-40, :48); UM comments the Series out and adds two expression lines that do nothing (UM:322-324).
- Bugs, the same in both, traced [C][I]:
  - UM/UF:27-28 call `self.source_adata.train_valid_split(self.source_adata)`. AnnData has no such method, and the call omits `random_state` and `valid_size`. `setup()` would fail with `AttributeError` right after reading 7.7 GB.
  - `toggle_ood_split` has no `self` (UM:54; UF:58).
  - `train`, `valid`, `n_epochs`, `vae` and `network` are undefined (UM/UF:327-336); they were local variables of the script.
  - `self.network.train()` without data (UM/UF:347).
  - Both files parse [I].
- Design: the reference split runs once on one joint mouse + human AnnData and stratifies the held-out cells by species ([F07](F07-toggle-iid-ood-and-renorm.md), [F16](F16-deployment-models-and-mixhvg.md)). Splitting each species file separately is a different design. The current code has both problems: AnnData has no `train_valid_split` method, and a single-species file cannot be stratified by species (UM and UF, §11) [C][I].
- Saved outputs: the three edited notebooks show `ModuleNotFoundError: No module named 'speciesot'` in a kernel named `analysis` (`mac:speciesOT/Josh_speciesOT/e24_src_example.ipynb#c0`; `fasrc:/n/holylabs/mooney_lab/Lab/junyizhou/Josh_speciesOT/e24_src_example.ipynb#c0`; `fasrc:/n/holylabs/mooney_lab/Lab/junyizhou/Josh_speciesOT/src/speciesot/Tests/e24_replica.ipynb#c2`) [N]. The FASRC notebooks were saved at 18:29 and 18:32; the editable install in FASRC `analysis` was (re)written at 18:34 to point at `Josh_speciesOT/src` (file time of the `.pth`), so the errors were probably fixed right after they were saved [C][I]. On the Mac, `analysis` has no `speciesot` install at all (Setup) [C].

### 12. What each version does today

| version | imports? | `setup()` on its own example | train → predict → evaluate | real model? | tests |
|---|---|---|---|---|---|
| skeleton `josh@e1fe1b0` (Josh's checkout and venv) | yes, e24 cell 0 ran [N] | should work with Josh's YAML after reading 7.7 GB; no saved run [I] | no-op → Identity, result dropped → nothing to evaluate [C] | no | none |
| Conny's `main` = Josh's `src` (`9816d59`) | yes [I] | `KeyError: 'evaluations'` on Josh's YAML; works with `example_debugging.yaml` [I] | Identity → R² crashes on 251 vs 392 cells; score dropped [I] | no | none |
| `josh@0ba4158` | yes [I] | as above | as above; MMD not wired [C] | no | 1 trivial [C] |
| `josh@6d4925e` (PR #2) | **no**, `SyntaxError` line 147 [C] | — | — | — | 1 trivial |
| `josh@3eb6555` | yes [I] | `AttributeError` (`VAEArith`) with `Tests/config.yaml` in `analysis`, `ModuleNotFoundError` where `scgen` is missing; `KeyError: 'experiment'` with the others [I]; an older version's `setup()` finished on real files (`e24_replica.ipynb#c3`) [N] | `TypeError`, then `NameError` [C] | no | 1 trivial + 1 script |
| UM / UF | yes, both parse [I] | `AttributeError` in `TrainingData` after loading [I] | `NameError` [C] | no | as above |
| AI stack S | yes [D] | tiny BCG spec: Dummy score 1 and 251 cells (PR #1 body) [D] | AE and CellOT return job texts; CellOT `fit` is untrained; decoded metric reads old CSVs [C] | wraps hub code; trains nothing; `ReferenceBundle` ran a saved AE + CellOT on 251 BCG cells, shape only [R] | 15; one needs a deleted path [C] |
| AI package, branch `src` (60d54ab) | only through `PYTHONPATH` [C] | tiny synthetic files [R] | YAML models copy their input; real engines have open bugs [C][R] | no | 38 pass with fakes [R] |
| Codex `mentor-pr-01` (copy of 09-29) | yes, it parses [I] | `KeyError: 'modesals'` [C] | scores stored; MMD raises `TypeError` [C] | no | 3 passed on 09-21, before the later edits [R]; 1 MMD test [C] |

## Verdict

- No version of the package has produced a number about biology, and none can train a model on real data [C][N]. The executed outputs are a printed config dict, an AnnData summary, import errors, the stack's plumbing receipts and synthetic test logs [N][R].
- Solid [C]: Josh's skeleton gives a shared vocabulary (source and target, four calls, the Identity baseline). The R² formula computes per-gene paired Pearson² for dense, same-shape inputs (it is Stage 0's reconstruction metric), and the MMD formula computes the biased one-bandwidth estimate. The YAML-per-experiment idea is used by every line.
- Useful only as design input, not as the hand-built package [C][I]: gene-axis hashing and refusing a stale shift (stack PR-3, PR-6); refusing illegal metric inputs and keeping a results list (AI package, Codex); counting cells without loading big files (stack PR-1).
- Cannot be concluded: whether the AI package's engines work with the real CellOT or scGen libraries (its tests ran with neither installed [R]); whether the stack's wrappers give correct numbers (they ran against a saved autoencoder and CellOT model on FASRC, but the receipts check only hashes and output shape [R]); what Josh thinks of the scGen direction (no review of PR #2 or of `scgen-model-impl`) [G].
- Evidence strength: strong for what the code says (read at exact commits, with syntax checks); medium for what it would do at run time (traced, not run) [I].

## Why it stopped

- It has not stopped: the newest edits are from 2026-10-15 and PR #2 is open [G][C].
- Stated reasons for turns:
  - PR #2 was opened "so that we can move forward to scGenModel building" (PR #2 body) [D].
- No stated reason for dropping the AI stack. The force-push, and Conny's own R² PR to Josh 21 minutes later, suggest Conny chose the hand-made line [G][I].
- The AI package: it was never offered to Josh ("No push to `JoshuaPrice/speciesOT`" in eight of the ten PR bodies) [D], and the work moved to a teaching workspace (§7) [C]. Why the agent's loop stopped is recorded only in private chat sessions, which are not quoted here.
- The teaching workspace ended on 2026-09-29 [I]: its last saves are 17:38 (core) and 17:47 (`pyproject.toml`); at 18:03 the Mac `cellot` env's editable install was pointed at a new folder `/Users/conny/Desktop/speciesOT src/speciesOT/src`, and `josh@0ba4158` was committed at 18:16 [C][G].

## Problems in how it was done

- **Nothing runs end to end, and no full run was saved.** No version has a saved run of all four calls on real data; the furthest any saved output gets is an older `setup()` (§9, §12) [N][C]. Without one, "the package reproduces X" cannot even be attempted.
- **Two different unsaved copies of the newest code.** UM and UF differ (§11) and neither is on GitHub [G][C]. Losing one machine loses work; choosing between them is undocumented.
- **History that says "merged" but isn't.** #1, #4 and #6 show as merged on GitHub, while `main` was force-pushed past them (§5) [G]. Readers of GitHub alone will be misled.
- **An open PR whose head does not import.** Merging PR #2 as it is puts a `SyntaxError` into Josh's `main` (`josh@6d4925e:src/speciesot/speciesot_core.py:147`) [C].
- **Three scGens in one class.** Config from the CellOT autoencoder, code from TensorFlow-1 `VAEArith`, library pinned to scvi-tools `SCGEN` (§9) [C]. Whatever the class eventually computes, it cannot match all three sources of reference numbers.
- **Metrics do not match the research.** Paired-cell R² and one-bandwidth full-cloud MMD reproduce no earlier prediction score (metrics.md §1, §2) [C]. The paired R² does equal Stage 0's reconstruction metric (Setup), so the name "R2" now means two different things in the project: a mean-profile r² for predictions and a paired r² for reconstructions [C][I]. Josh approved R² without comment on this [G]; PR #2 flags it only as "needs some attention" [D].
- **Authorship is not visible in git.** The stack and AI-package commits carry Conny's name (§3, §6), and the hand-made `R2Evaluation` reached Josh through an AI-written PR text (§2) [G][D]. From git alone, Josh cannot tell which lines Conny wrote, which is exactly what the hand-built rule is about [I].
- **Tests that cannot fail for the right reasons.** The MMD test uses identical inputs (§8); `Tests/test_model.py` is a script that runs at import (§9); the 38 AI tests pass with fake back ends and none of the real libraries installed (§6) [C][R].
- **Merging before review.** All ten AI-package PRs were merged 2–8 minutes after opening; Bugbot's three findings arrived after the merges and stayed unfixed (§6) [G]. On the stack, seven PRs were merged 37 seconds to 11 minutes after opening while Bugbot could not run (§3) [G].
- **Dead absolute paths.** `Tests/config.yaml:2`, `Tests/test_model.py:5`, `conny:example_debugging.py:6` and the stack's `tests/test_frozen_ae.py:8-10` point into the deleted working tree; three editable installs do too (FASRC `CellOT` and `CellOT_v3`, Mac `cellot`; Setup) [C].
- **Config drift.** Three schemas (list of names, mapping with hyperparameters, hub spec with `scgen_*` keys) and inconsistent key names (`x_dimension` vs `x_dimensions`; `scgen_lr` vs `lr`) [C]. A YAML `None` is a string [C].
- **No shared gene axis.** Training uses 18,024 mouse and 61,759 human genes with no ortholog step (§9) [N]. The hub and atlas pipelines aligned genes to orthologs before any model saw them ([F08](F08-hvg-flavor-matrix.md), [F09](F09-hub-and-metrics-infrastructure.md), [F16](F16-deployment-models-and-mixhvg.md)) [D].
- **Environment drift.** The package resolves to different code in each env, to a deleted folder in three of them (two on FASRC, one on the Mac), and is not installable in the TensorFlow-1 env that `VAEArith` needs (Setup) [C].
- **Wrappers that look like models.** The stack's `CellOTModel.fit` trains nothing, `AutoEncoderModel.train` returns text, and both depend on the research repo's folder layout (§3) [C].
- **Docs that contradict the record.** PLAN says no prototype ran but lists landed commits (§4) [D]; the 3eb6555 comment says the scGen methods are stubs while the code calls `VAEArith` (§9) [C]; the survey lead "never executed" was wrong (§4) [D][G], and [timeline.md](../timeline.md) still repeats it.

## Terms used here

- **source / target**: the mouse and the human AnnData inside `TrainingData` and `TestData`.
- **the four calls (verbs)**: `setup`, `train`, `predict`, `evaluate` on `Experiment`.
- **e24**: Josh's example notebook `e24_src_example.ipynb`; also used for its YAML.
- **`IdentityModel`**: returns the mouse test cells unchanged as the "prediction" of the human cells.
- **`DummyEvaluation`**: a metric that always returns 1.
- **`R2Evaluation` (package)**: mean over genes of the squared per-gene Pearson correlation between paired cells.
- **`MMDEvaluation` (package)**: biased RBF MMD with one bandwidth, γ = 0.1.
- **`use_all_genes`, `x_dimension(s)`**: 3eb6555 config keys for the network's input size.
- **PR-0 … PR-6**: the agent's stack, GitHub #1–#10 on Conny's repo.
- **operator**: PLAN's name for the human who merges (Conny).
- **lanes, swarm, receipts**: PLAN's parallel agent checks and their log files in `/tmp/swarm-pr-N/`.
- **`JobPlan`**: the text of Slurm commands that the stack returns instead of training.
- **`FrozenAE`**: the stack's handle to a trained CellOT autoencoder folder.
- **`ReferenceBundle`**: the stack's handle to a "baked" results folder (gene list, autoencoder, shift, CellOT weights).
- **engine**: in the AI package, an object passed into a model that does the real work; the default copies the input.
- **fail closed**: raise an error instead of guessing.
- **`mentor-pr-01`, PR-01**: the Codex worktree and its unsent first change.
- **toggle_ood split**: the hub's split that holds out cell types ([F07](F07-toggle-iid-ood-and-renorm.md)).

## What the package needs from this

This family contains no scientific experiment, so nothing here is worth reproducing as a result about biology. It gives the package one end-to-end test tied to the e24 example, some unit tests, and a list of decisions.

### Reference tests

1. **e24 Identity with a mean-profile R² (recommended first end-to-end test; no training).**
   - Inputs: the e24 test files, `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/tb/data/mouse_bcg/bcg_treated_scanvi_081826.h5ad` (251 × 1,000; file time 2026-08-18 17:39) as the prediction and `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/tb/data/human_bcg/bcg_treated_scanvi_082626.h5ad` (392 × 1,000; 2026-08-26 15:49) as the truth; for the last two numbers below also the human control file `…/tb/data/human_bcg/bcg_control_scanvi_082626.h5ad` (230 cells; 2026-08-26 15:49) (`ls -l` on FASRC; cell counts from tb4 `#c5`) [C][N].
   - Config: `IdentityModel`. Both clouds go through tb4's preprocessing: strip ENSG version suffixes from gene names and make them unique (`#c5`); if a `counts` layer exists, normalize each cell to 10,000 counts and take log1p, otherwise use `.X` (`josh@main:tb/tb4_eval_first_predictions.ipynb#c6`). Genes: the 1,000 genes shared by all tb4 inputs (`#c6` prints 1000). Metric: Pearson r between the two mean profiles across genes, then squared (`#c9`) [C][N]. The top-100 set ranks genes by |mean treated − mean untreated| in the human files (`#c10`, `#c11`) [C].
   - Expected: r 0.792743, r² 0.628441; on the top 100 human BCG genes r² 0.181901; human untreated vs human treated r² 0.970376 (`josh@main:tb/tb4_eval_first_predictions.ipynb#c9`, `#c11`) [N].
   - Tolerance: about 1e-6, since nothing is sampled [I]. Did tb4 read these exact files? Probably: the outputs first appear in `josh@5d00f44` (16:46); the tb4 notebook in `josh@74cf2f2` (16:33) has no outputs; both data files were last written before 16:33 [G][C][I]. Caveat: the package's `IdentityModel` returns `.X` unchanged; whether `.X` already equals log-normalized counts was not checked (no `.h5ad` was opened) [I]. The paired-cell `R2Evaluation` cannot produce this number; on these files it crashes or refuses [C][I].
2. **Unit tests already written (synthetic).** Keep: MMD of identical inputs is exactly 0 (`josh@0ba4158:src/speciesot/Tests/test_evaluation.py:14-22`), and add the positive floor for two disjoint halves of one cloud ([F10](F10-monocytes-floor-ceiling-and-v08.md), test 2). If a paired-cell metric is kept under its own name: hand-computed 0.625 and 0.25 (`mac-codex:mentor-pr-01/tests/test_experiment_results.py:21-37`). Refusals for unequal cells, a transposed (swapped-axis) matrix and sparse input (`ai_package@src:tests/test_r2_fail_closed.py:27-58`). If the paired metric is kept for reconstructions, check it against Stage 0's helper on the same arrays (`fasrc:BK/scgen-cellot-ablation/scripts/stage0_metric_helpers.py:42-52`; its own tests are in `…/test_stage0_metric_helpers.py`). If gene matching by name is chosen: first-wins with zero fill (S `tests/test_gene_project.py`) [C].
3. **Larger references from other families.** The decoded-frame scorer on M1 v08, `frac_gap_closed_decoded` 0.897378 at n = 80 ([F09](F09-hub-and-metrics-infrastructure.md) test 1, [F10](F10-monocytes-floor-ceiling-and-v08.md) test 1, [F16](F16-deployment-models-and-mixhvg.md) test 1) [R]; split counts ([F07](F07-toggle-iid-ood-and-renorm.md) test 1, [F16](F16-deployment-models-and-mixhvg.md) test 2); do-nothing and scGen R² on the LPS data ([F12](F12-scgen-fig5-stage0-and-stage1.md)); the mean shift with the MMD gap ([F13](F13-autoresearch-loop.md) test 1).

### Decisions the package needs next

Options found in the record, not recommendations.

| # | decision | options seen | evidence |
|---|---|---|---|
| 1 | Which "scGen" | (a) CellOT's deterministic autoencoder + mean latent shift: every hub and atlas result ([F05](F05-first-cellot-runs-on-lps.md)–[F16](F16-deployment-models-and-mixhvg.md)); its settings are what §8 pasted. (b) The paper's TensorFlow-1 `VAEArith`: Stage 0 ([F12](F12-scgen-fig5-stage0-and-stage1.md)) and Plan C ([F14](F14-july-plans-a-to-d.md)); needs Python 3.7 and TF 1.15; what 3eb6555 calls. (c) scvi-tools `SCGEN` 2.x: installed and pinned, wrapped by the AI package, used by **no** experiment, so no reference number exists. | On the scGen split, paper scGen r2_all 0.906741 vs CellOT autoencoder 0.897159; on the OOD split the autoencoder falls to 0.653528 (`fasrc:BK/scgen-cellot-ablation/results/stage0/metrics.json`; `fasrc:BK/scgen-cellot-ablation/results/stage1/ablation_grid.csv:2`, `:4`) [R]. So the split matters more than which scGen [I]. Stage 1 has one run per arm; the one rerun (in F13) gave 0.882 (A) and 0.662 (C), as listed in [F12](F12-scgen-fig5-stage0-and-stage1.md), "What the package needs", test 5 [R]. To match hub numbers with (a), note that the hub computes the shift after the last training step with the model still in training mode, i.e. with dropout 0.1 active (`conny:cellot/cellot_gpu/cellot/train/train.py:217-252`; `fasrc:BK/cellot/cellot_gpu/results/hvg_pearson_residuals_m1_v08_ood/scgen/config.yaml:22`, `:37`, `:39`) [C][I]; PLAN:518 says the same [D]. |
| 2 | Which R² | paired per-gene r² (now; equal to Stage 0's reconstruction metric `pearson_r2_pergene_mean`); r² of mean profiles (scGen paper, hub, autoresearch `r2_all`, tb4); unsquared r (`r2-means` in `evals.csv`); all genes vs top-k marker genes | [metrics.md](../metrics.md) §1; `fasrc:BK/scgen-cellot-ablation/scripts/stage0_metric_helpers.py:42-52` [C]; the r-vs-r² mix-up of April ([F06](F06-tcell-holdouts-speciesot-v1.md)) [D]; always report the Identity score beside it (0.628441 on e24, above) [N] |
| 3 | Which MMD | one γ on full clouds (now); the average over 50 γ on subsamples of n cells with 10 draws (CellOT `evaluate.py`, hub, autoresearch); biased vs unbiased | [metrics.md](../metrics.md) §2; floor values in [F10](F10-monocytes-floor-ceiling-and-v08.md) and [F13](F13-autoresearch-loop.md). On the 58,931-cell human sample one full kernel matrix would need about 27.8 GB [I]. |
| 4 | Which space to score in | raw genes (now), latent, decoded | [F10](F10-monocytes-floor-ceiling-and-v08.md) on why the decoded frame was adopted |
| 5 | How splits work | one joint mouse + human AnnData with a toggle_ood split (held-out cell types, test fraction 0.2, seed 0, stratified by species) vs splitting each species file (the uncommitted code) | exact counts in [F07](F07-toggle-iid-ood-and-renorm.md) and [F16](F16-deployment-models-and-mixhvg.md); §11 |
| 6 | Where genes are aligned | a prep step before the package (the hub's `prep`) or inside `TrainingData`; which ortholog table; first-wins or last-wins for duplicate genes | §9 (18,024 vs 61,759 genes) [N]; PLAN:512 [D]; [F09](F09-hub-and-metrics-infrastructure.md) (prep), [F16](F16-deployment-models-and-mixhvg.md) test 3 (721 shared genes) |
| 7 | Config schema | list of names (skeleton), mapping with hyperparameters (3eb6555), hub spec keys; a dataclass was discussed on 2026-10-01 | §1, §9; [F09](F09-hub-and-metrics-infrastructure.md) test 2 (spec → config) |
| 8 | Data loading | read whole files (all of Josh's line) vs count first and load lazily (stack PR-1) | 7.7 GB of files for e24 (PLAN:504 [D]; `ls -l`, §1 [C]); atlas `MemoryError` receipt (§3) [R] |
| 9 | What `evaluate()` returns | nothing (Josh's line), the last score (stack), a list (AI package, Codex), a table with model, metric, space, n, seed | [F09](F09-hub-and-metrics-infrastructure.md) recommends one table per run with those columns |
| 10 | Where training runs | inside `train()` on a GPU node vs returning job text (stack) vs staying in the hub | no package code has run as a batch job; the last speciesOT compute jobs were on 2026-08-18 ([timeline.md](../timeline.md)) [R] |
| 11 | Which environment | one env vs several; `requires-python` | Setup table; PLAN:494 [D] |
| 12 | Which copy and which repo | UM or UF; Josh's `src`/`MMDEv_Test` line or Conny's `main` | §11; [sources.md](../sources.md), "Sync problems" |

## Open questions

- Which uncommitted copy (UM or UF) does Conny consider current? The file times differ by 25 minutes and neither is committed.
- Did Josh see the move from the CellOT-autoencoder settings to `VAEArith` (§9)? No review or comment was found.
- Did the skeleton's e24 example ever run all four calls? Its saved notebook shows only the import (§1).
- Is `.X` of the two BCG test files log-normalized, and is it sparse? This decides whether reference test 1 works without extra preprocessing and how the current R² fails. Not checked: no `.h5ad` was opened.
- Who ran the force-push of 2026-09-08 18:12, Conny by hand or an agent with Conny's token? GitHub records only the account.
- Where was `josh@3eb6555` committed? The FASRC clone `Josh_speciesOT` holds files with times from 2026-10-01 (`Tests/test_evaluation.py`), 2026-10-13 (`Tests/__pycache__`) and 2026-10-15 16:47 (the files added by 3eb6555, so they probably arrived by a pull), while the committed configs point into the deleted folder `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT`. That folder's backup has a `josh` remote for `JoshuaPrice/speciesOT` (`fasrc:BK/.git/config`), so the commit may have been made there [C][I].
- When did Josh write his `pyproject.toml`? His checkout's copy has a 2026-09-21 file time but his editable install dates from 2026-09-03 (§1).
- Are the stack's verification receipts (`/tmp/swarm-pr-0/` … `/tmp/swarm-pr-6/`) saved anywhere? Not found.

## Sources

Conny's repo: `conny:src/speciesot/speciesot_core.py`, `conny:src/speciesot/__init__.py`, `conny:pyproject.toml`, `conny:e24_src_example.ipynb`, `conny:example_debugging.py`, `conny:example_debugging.yaml`, `conny:specs/m1_modern.yaml`, `conny:atlas-paper-vae/scripts/01_train_vae.py`, `conny:atlas-paper-vae/configs/m2_v08.yaml`, `conny:cellot/cellot_gpu/cellot/train/train.py`, `conny:cellot/cellot_gpu/cellot/models/ae.py`; commits `conny@cebd146`, `conny@7bb193e`, `conny@109bf12`; stack commits `conny@7aad392`, `conny@0646a8b`, `conny@fb6591f`, `conny@d36b761`, `conny@2f2db44`, `conny@83cff23`, `conny@12f7eee` (all `src/speciesot/*.py`, all seven `tests/*.py`, `specs/e24_tiny_identity.yaml`, `e24_src_example.ipynb`, the receipts `logs/research_logs/media/pr-1-review-atlas-obs.txt`, `pr-3-review-reuse.txt`, `pr-6-review-bcg-predict.txt`, the `docs/mentor_runbook.md` diff; `git diff --shortstat` with and without a path filter); `conny:docs/archaeology/models.md`, `conny:docs/archaeology/metrics.md`, `conny:docs/archaeology/sources.md`, `conny:docs/archaeology/timeline.md`, `conny:docs/archaeology/tools/check_refs.py`; the "What the package needs" sections of F07, F09, F10, F12, F13, F16.

Josh's repo: `josh@e1fe1b0:src/speciesot/speciesot_core.py`, `josh@e1fe1b0:src/speciesot/__init__.py`, `josh@e1fe1b0:e24_src_example.ipynb`; `josh@a823f96`, `josh@9816d59`; `josh@0ba4158:src/speciesot/speciesot_core.py`, `josh@0ba4158:pyproject.toml`, `josh@0ba4158:src/speciesot/Tests/test_evaluation.py`; `josh@6d4925e:src/speciesot/speciesot_core.py`, `josh@6d4925e:src/speciesot/Tests/config.yaml`; `josh@3eb6555:src/speciesot/speciesot_core.py`, `josh@3eb6555:requirements.txt`, `josh@3eb6555:pyproject.toml`, `josh@3eb6555:src/speciesot/Tests/config.yaml`, `josh@3eb6555:src/speciesot/Tests/toy_config.yaml`, `josh@3eb6555:src/speciesot/Tests/test_model.py`, `josh@3eb6555:src/speciesot/Tests/e24_replica.ipynb`, `josh@3eb6555:e24_src_example.ipynb`; `josh@main:tb/tb4_eval_first_predictions.ipynb` (`#c1`, `#c5`, `#c6`, `#c9`, `#c10`, `#c11`), `josh@74cf2f2:tb/tb4_eval_first_predictions.ipynb` (no outputs), `josh@5d00f44`, `josh@main:tb/tb2_human_setup.ipynb`, `josh@main:e22_batch_correction.ipynb`; `josh@47feafa:requirements.txt`; `git grep` of `origin/main`, `origin/cellot`, `origin/junyi` for `import scgen`.

AI package: `ai_package@src:src/speciesot/experiment.py`, `ai_package@src:src/speciesot/models.py`, `ai_package@src:src/speciesot/engines.py`, `ai_package@src:src/speciesot/evaluations.py`, `ai_package@src:src/speciesot/pairing.py`, `ai_package@src:src/speciesot/speciesot_core.py`, `ai_package@src:src/speciesot/__init__.py`, `ai_package@src:tests/test_scgen_model.py`, `ai_package@src:tests/test_identity_experiment.py`, `ai_package@src:tests/test_r2_fail_closed.py` (and the other six test files, counted), `ai_package@src:pytest.ini`, `ai_package@src:README.md`; `ai_package@c625dd9`, `ai_package@a445910`.

FASRC: PLAN; `fasrc:BK/scgen-cellot-ablation/scripts/stage0_metric_helpers.py`, `fasrc:BK/scgen-cellot-ablation/scripts/test_stage0_metric_helpers.py` (listed), `fasrc:BK/scgen-cellot-ablation/scripts/run_stage0.sh`, `fasrc:BK/scgen-cellot-ablation/scgen-reproducibility/code/scgen/models/_vae.py`; `fasrc:BK/.git/config`; file times of `fasrc:BK/AGENTS.md`, `fasrc:BK/example_debugging.py`, `fasrc:BK/logs/research_logs/` (listing and `grep`); `fasrc:BK/cellot/cellot_gpu/results/hvg_pearson_residuals_m1_v08_ood/impact_cellot/evals_ood_data_space/decoded_frame_metrics.csv`, `fasrc:BK/cellot/cellot_gpu/results/hvg_pearson_residuals_m1_v08_ood/impact_cellot/evals_ood_data_space/extended_metrics.csv`, `fasrc:BK/cellot/cellot_gpu/results/hvg_pearson_residuals_m1_v08_ood/scgen/config.yaml`, `fasrc:BK/cellot/cellot_gpu/results/atlas_full_pearson_residuals` (listing), `fasrc:BK/scgen-cellot-ablation/results/stage0/metrics.json`, `fasrc:BK/scgen-cellot-ablation/results/stage1/ablation_grid.csv`; `fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/experiment_config_example_090326.yaml`, `fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/pyproject.toml`, `fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/src/speciesot/speciesot_core.py`; the FASRC clone `fasrc:/n/holylabs/mooney_lab/Lab/junyizhou/Josh_speciesOT` (`git status`, `git diff`, UF, `fasrc:/n/holylabs/mooney_lab/Lab/junyizhou/Josh_speciesOT/e24_src_example.ipynb`, `fasrc:/n/holylabs/mooney_lab/Lab/junyizhou/Josh_speciesOT/src/speciesot/Tests/e24_replica.ipynb`); env records `fasrc:/n/home01/jzhou1125/miniforge3/envs/analysis/lib/python3.12/site-packages/__editable__.speciesot-0.0.1.pth`, `fasrc:/n/home01/jzhou1125/miniforge3/envs/analysis/lib/python3.12/site-packages/scgen/__init__.py`, `fasrc:/n/home01/jzhou1125/miniforge3/envs/analysis/lib/python3.12/site-packages/scgen-2.1.1.dist-info/direct_url.json`, `fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/speciesOT_env/lib/python3.12/site-packages/__editable__.speciesot-0.0.1.pth`, `fasrc:/n/home01/jzhou1125/.conda/envs/CellOT/lib/python3.9/site-packages/__editable__.speciesot-0.0.1.pth`, `fasrc:/n/home01/jzhou1125/.conda/envs/CellOT_v3/lib/python3.11/site-packages/__editable__.speciesot-0.0.1.pth`, `fasrc:/n/home01/jzhou1125/miniforge3/envs/scgen_tf1/lib/python3.7/site-packages/scgen/__init__.py` and `scgen-2.0.0.dist-info`, `conda-meta` Python records of all six envs, `fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/speciesOT_env/pyvenv.cfg`; `ls` of `/n/holylabs/mooney_lab/Lab/junyizhou/` (the old `speciesOT` folder is missing); file listings of the BCG (treated and control) and Tabula files.

Mac: `mac:speciesOT/Josh_speciesOT` (`git status`, `git diff`, UM, `mac:speciesOT/Josh_speciesOT/e24_src_example.ipynb`); `mac:src/speciesot` (all seven files, hashed); `mac:src.zip` (listing, core file hashed); `mac:scGen v.s. CellOT/scgen-reproducibility/code/train_scGen.py`, `mac:scGen v.s. CellOT/scgen-reproducibility/code/scgen/models/_vae.py`; `/Users/conny/miniconda3/envs/` (listing) and `/Users/conny/miniconda3/envs/cellot/lib/python3.9/site-packages/__editable__.speciesot-0.0.1.pth`.

Codex workspace: `mac-codex:START-HERE.md`, `mac-codex:package/.git`, `mac-codex:research-reference/.git/config`, `mac-codex:mentor-pr-01/pyproject.toml`, `mac-codex:PR-01-body.md`, `mac-codex:PR-01-evaluation-results.md`, `mac-codex:current-development.env`, `mac-codex:mentor-pr-01/.git`, `mac-codex:mentor-pr-01/src/speciesot/speciesot_core.py`, `mac-codex:mentor-pr-01/tests/test_evaluations.py`, `mac-codex:mentor-pr-01/tests/test_experiment_results.py`, `mac-codex:mentor-pr-01/test.py`, `mac-codex:package/docs/learning/09-verification.md`, `mac-codex:package/docs/learning/evidence/core-tests.txt`, `mac-codex:package/docs/learning/evidence/mentor-pr-tests.txt`, `mac-codex:package/docs/learning/evidence/lesson-tests.txt`, `mac-codex:package/docs/learning/evidence/baseline-probes.json`, `mac-codex:package/docs/learning/evidence/verification.json`.

GitHub (GH): PRs #1–#11 on JunyiZhou-Conny/speciesOT (bodies, comments, creation and merge times; PR #11's `docs/learning/experiment-archaeology.md` at 63af136); PRs #1–#2 on JoshuaPrice/speciesOT (bodies, reviews, comments, `gh api …/pulls/<n>/reviews` and `/comments`); PRs #1–#10 on JunyiZhou-Conny/speciesost-package (bodies, review and issue comments, Bugbot comments with times); the push log of `main`; the merge commits fb8507e, f703fac, ac18274 and the compare `ac18274...main`; repository metadata of `speciesost-package`.

Leads: Conny's private AI chat sessions (Codex and Cursor) and Codex memory notes on the Mac were read to find things to check. They are not cited or quoted on this page.

Paper: `/tmp/sot-arch/papers/scgen.txt`, Methods (equation (6) and the δ-vector paragraph; the architecture and α values sit in Supplementary Table 1, which the text does not contain) [P].

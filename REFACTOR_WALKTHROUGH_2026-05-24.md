# Repo walkthrough — running notes (2026-05-24)

Working doc for the conversational walkthrough of the workspace root. One row per item that's been discussed. Decisions are not yet executed — they're queued until a folder-group is fully reviewed, then batched into one commit.

**Buckets**: `alive` (leave in place, you can pinpoint what it does), `document` (alive but needs a one-line note), `archive` (move out of the way, keep on disk), `delete` (true junk).

---

## Workspace root

| Path | Bucket | Pending action | Notes |
|---|---|---|---|
| `docs/cursor-connect-compute-node.md` | alive | — | Personal reference, kept for the recurring SSH config flow on OOD. Folder is the intended landing pad for more how-to notes (conda envs, end-to-end notebook run, BioMart workarounds). |
| `reference/` (the folder) | alive | rename → `reference_papers/` | Two methods PDFs (Bunne 2023, scGen). Folder name should advertise that it's papers. |
| `autospeciesOT/` (entire folder) | delete | `rm -r autospeciesOT/` | User: full delete (option B). Concept stays alive as a summer-2026 task — see Pending Future Tasks below. |
| `logs/NOTEBOOK_INDEX.md` | delete | `git rm logs/NOTEBOOK_INDEX.md` | Documents the wrong layer (notebooks instead of models). The right artifact is a model-card hub — see Pending Future Tasks. |
| `logs/research_logs/` | alive | — | Personal journey record; re-read later. Logging cadence has lapsed since 2026-05-04 because user has to initiate it manually. See Pending Future Tasks for auto-logging hook. |
| `logs/mentor_meetings/` | alive | — | Same content type as research_logs but separated when there's a presentation/ceremony attached. Naming is inconsistent (`*_slides.md` vs `MORNING_BRIEFING_*.md`) but user prefers to leave as-is. |
| `archive/` (entire folder, including `git_backups/`, `autoresearch_nested_placeholder/`, `old_notes/`) | deleted | already done by user 2026-05-25 | Permanently gone for gitignored content (~417 MB freed). The 3 `old_notes/*` files show as tracked deletions in git and are recoverable from history. |
| `scripts/` runtime artifacts (`.pid`, `.log`, `__pycache__/`) and tracked caches (`.bcg_*.csv`, `.biomart_*.csv`) | done | committed in batch 2 (`bcce463`) | -24,904 lines. Caches now gitignored. |
| `scripts/generate_data_space_eval_sbatches.py` | alive (provisional) | — | Generates 80 eval sbatches over flavor × group × mode × model. `--setting ood` is intentional (always eval on held-out cells; see `docs/conceptual_framework.md` §5.4). Identifies model only by path (no upfront check that training exists). Strong candidate for cookbook consolidation. |
| `scripts/generate_atlas_full_configs.py` | alive (provisional) | — | Generates configs + sbatches for "full atlas, no holdout" training (notebook 15's territory). 2 flavors × 2 models = 4 trainings. Uses `datasplit.name: train_test` (no toggle). Has a small bit of helpful abstraction (`_sbatch_header` helper, `PREAMBLE` constant) — seeds for the cookbook. Candidate for cookbook consolidation. |
| `scripts/generate_toggle_configs.py` | deleted (batch 3) | committed `17562ba` | Tracked in git → recoverable. Generator's outputs (data files, scgen + impact models) remain useful for monocyte-axis groups (m1, m3, m4) that the hvg_flavor matrix doesn't cover. |
| `cellot/cellot_gpu/results/toggle_*/cellot/` (16 abandoned cell-type-framing model dirs, 53 MB) | moved to archive (batch 3) | now at `cellot/cellot_gpu/results/_archive/toggle_cellot_subdirs/toggle_*/cellot/` | Disk-only move (path is gitignored). Kept for retrospective comparison. |
| `cellot/cellot_gpu/results/toggle_*/{scgen,impact}/` | alive, keep | (queued) rename `impact/ → impact_cellot/` in a later batch when we're ready for live-dir renames | Models for the monocyte groups (m1, m3, m4) are unique to the toggle line and worth preserving. |
| `scripts/generate_hvg_flavor_configs.py` | alive (active) | — | Source of truth for the active matrix (88 trainings, 176+ sbatches). Most-evolved generator: has `_sbatch_header`, `PREAMBLE`, three sbatch-body generators (`_train_sbatch`, `_eval_sbatch`, `_eval_dataspace_sbatch`). Config YAMLs still inline f-strings (copy-paste-prone — same template appears here AND in `generate_atlas_full_configs.py`). Notable overlap with script 1 on eval_dataspace generation: this script's `_eval_dataspace_sbatch` hard-codes `--n_cells 30,50,80` while script 1 uses a per-group dict (more careful). When cookbook consolidates, keep per-group n_cells logic. |
| `scripts/regenerate_hvg_flavor_run_matrix.py` | alive (active, slated for retirement) | — | Generates `hvg_flavor_run_matrix.{csv,md}` — an 80-row manifest of the active matrix with per-flavor input-layer + raw-counts-required metadata. Prototype-grade model-card hub for the hvg_flavor matrix only. **Will be subsumed by the model-card hub when built; delete then.** Has a parallel source-of-truth issue with `generate_hvg_flavor_configs.py` (both encode FLAVORS/GROUPS/MODES); not worth pre-refactoring since hub will absorb both. |
| `scripts/build_experiments_inventory.py` | alive (active, slated for retirement) | — | Generates `experiments_inventory.{csv,md}` at workspace root — a hand-curated forensic catalog of every CellOT/IMPACT/scGen run across every project phase (legacy_crossspecies, speciesot_v1, toggle, renorm, hvg matrix). Contains the only canonical `ALIAS_TABLE` mapping every old name to current canonical. **Will be subsumed by the model-card hub; deletion BLOCKED until `ALIAS_TABLE` and per-phase context overrides (lines 193–198) are ported into the hub design.** See hub project requirements. |
| `scripts/render_results_figures.py` | alive (active, slated for retirement) | — | Standalone Agg-backend renderer for the matrix headline figures (5 PDFs/PNGs under `hvg_flavor_results_outputs/figures/`). Mirrors notebook 13 logic but headless — was called by `refresh_results_loop.sh`. Properly squares Pearson-r to R² (bug fix documented in script docstring and in `docs/conceptual_framework.md` §5.5). **Deletion BLOCKED**: the bottom half of the file (lines 268+, "Reusable presentation functions" — `plot_metric_bars`, `plot_marginals_paper_style`, etc.) is *imported by notebook 18*. Port those functions into the hub's plotting library (or `speciesOT/lib/plotting.py`) before deleting. Third copy of FLAVORS/GROUPS/MODES source-of-truth — same matrix-definition duplication the hub will absorb. |
| `scripts/biomart_watchdog.py`, `scripts/refresh_results_loop.sh`, `scripts/run_full_pipeline.sh`, `scripts/submit_hvg_flavor_matrix.sh`, `scripts/predict_new_input.sh` | walkthrough deferred (architectural call) | — | Not walked individually. All five belong to the hub-absorption bucket (Group D watchers → hub v2 lifecycle; Group E drivers → hub v2 submission CLI; `predict_new_input.sh` may stay as a thin shim). When we build the hub, address each in v2's design. Out-of-scope for the rest of this walkthrough. |
| `sbatch/` (entire folder, ~439 files across 6 subdirs + 3 small files) | alive, no git action | gitignored; nothing to commit | Generated sbatches are regenerable from the 4 active generator scripts. Keep on disk for active submission. `.ipynb_checkpoints/` deleted as junk. `submit_m2_twoflavors_pipeline.sh` (32 lines) is the reference implementation hub v2's submission DAG should mimic — keep until hub v2. `monitor_m2_joblog.sh` + `m2_pipeline_joblog.txt` are paired with it. `eval_dataspace_aeflag/` (10 files) is a one-off May-8 batch using `--embedding ae`; leave for now. |
| **Root-file walk** (during 2026-05-27 unattended work) | (see below) | | |
| `README.md` (workspace root, 2.8 KB) | alive | — | Reflects T1 reorg state. Will need a small update post-walkthrough to mention the conceptual_framework + hub design + walkthrough scratchpad. |
| `REFACTOR_PLAN_2026-05-05.md` (29 KB) | **archive (recommended: move to `docs/`)** | (proposed) `git mv REFACTOR_PLAN_2026-05-05.md docs/refactor_plan_2026-05-05.md` | The original plan that kicked off this walkthrough. Done its job. Worth preserving as historical context (it explains why we did T1, what Tier 2/3 would look like, etc.) but doesn't belong at workspace root anymore. Action queued for user confirmation. |
| `HOW_TO_RUN_NEW_INPUT.md` (19 KB) | alive | — | The canonical human-readable how-to for the pipeline. Referenced by `speciesOT/scripts/README.md` and probably by mentor-facing materials. |
| `HOW_TO_RUN_NEW_INPUT.txt` (13 KB) | **likely delete or merge** | (proposed) keep `.md`, delete `.txt` | Plain-text variant of the same doc, ~30% smaller. The `.md` is more recent and richer. If mentor prefers plain text, can be regenerated from the `.md` with `pandoc`. Action queued for user confirmation. |
| `experiments_inventory.csv` (68 KB), `experiments_inventory.md` (12 KB) | alive (slated for hub retirement) | — | Auto-generated by `scripts/build_experiments_inventory.py`. Will be subsumed by hub v0. |
| `.gitignore` (2.2 KB) | alive | — | Already updated through batch 2. |

---

## Pending future tasks (not blocking the walkthrough)

- Gather scattered "how-to" notes (conda envs, end-to-end notebook run, BioMart timeout recovery) and consolidate them into `docs/`.
- **Summer 2026**: clone https://github.com/karpathy/autoresearch.git fresh into the workspace root as `autoresearch/` (no `species` prefix). Write fresh `program.md` and `run_experiment.py` against the *then-current* naming convention. The deleted `autospeciesOT/run_experiment.py` contained the prior orchestration ideas (cell ontology IDs, scGen + IMPACT_CellOT chain, T-cell family map). If needed for reference, recover from git history (commit prior to the autospeciesOT deletion).
- ~~Permanent design-decisions doc~~ → first pass landed at `docs/conceptual_framework.md` (2026-05-25). Covers the three model variants, the naming rationale, the eventual drug+species composition goal, and current state. Open questions captured at the bottom of that doc.

### Separate project: Model-card hub (proposed by user 2026-05-25)

**Motivation**: notebooks are scaffolding; trained models are the actual deliverable. The repo has no first-class way to compare, browse, or document them. The existing `experiments_inventory.{csv,md}` (auto-generated by `scripts/build_experiments_inventory.py`) is the seed but is missing most of the fields below.

**Requirements (user's list)**:
| Category | Fields |
|---|---|
| Identity | run ID, name, timestamp, who trained it, conda env, git commit hash |
| Architecture | model variant (`impact_cellot` / `scgen`), layer count, neurons per layer, activation, ICNN-specific hyperparameters |
| Data — preprocessing | HVG flavor, normalization scheme, batch_key, gene-count after HVG, ortholog matching policy |
| Data — splits | source/target species, training cell types, held-out cell type, IID vs OOD framing, train/valid sizes |
| Training | iterations, batch size, learning rate, optimizer, wall time, GPU vs CPU, best-checkpoint metric |
| Evaluation | R (Pearson, on what), R² (squared), MMD, latent-space vs data-space, eval `n_cells`, `n_features` |
| Provenance | data-prep notebook, sbatch script, config YAML, location of `imputed.h5ad` |
| Status | active / archived / failed / superseded |

**Inspired by**: HuggingFace model cards. Form factor TBD: a richer CSV, one markdown card per model, SQLite + viewer, or a static mkdocs site.

**One-model-to-many-sbatches relationship** (added 2026-05-27 per user): each trained model owns *N* sbatch files — one for training, plus several for evaluation across (data_space vs. latent_space) × (small-n schedules) × (with vs. without `--embedding ae` flag) × (potentially BCG/uncapped extensions later). Today these are scattered across `sbatch/{train,eval,eval_dataspace,eval_dataspace_aeflag,eval_smalln,eval_smalln_latent}/`. The hub should reify the 1:N relationship — a model's detail page lists *all* the sbatches that have ever run against it, their job IDs, exit codes, output paths, and resulting metrics. The hub spec language should accept an `evaluations: [...]` list per model where each evaluation is its own structured object (space, n_cells, embedding, evalprefix, etc.).

**Per-model-variation deltas as first-class metadata** (added 2026-05-27 per user): a lot of the value of the hub is making *small differences* between trained models legible at a glance. Examples we've already encountered:
- Eval `n_cells` schedule per group (`30,50,80` vs `20,30,40` for group `d` because of pool size).
- HVG flavor (`seurat_v3` vs `pearson_residuals` vs `cell_ranger` ...).
- Whether the holdout cells' "ignored" half got folded into training (`mode: iid`) or stayed out (`mode: ood`).
- ICNN hyperparameters (`hidden_units`, `n_inner_iters`, `kernel_init_fxn.b`).
- Optimizer betas tuned for min-max stability (`beta1: 0.5` instead of Adam-default `0.9`).
- Data preprocessing version tag (`v07`, etc.).
- Whether an experiment was run from `generate_hvg_flavor_configs.py` (active) or the older fossil `generate_toggle_configs.py`.

The cookbook spec should *write* these as structured fields, and the hub should *display* them as columns/rows so two near-identical experiments can be compared without opening their configs.

**Critical pre-deletion dependency** (added 2026-05-27): the `ALIAS_TABLE` in `scripts/build_experiments_inventory.py` (lines 120–139) plus the per-phase `cellot` disambiguation overrides (lines 193–198) encode the only canonical mapping from old alias names to current canonical names. They are also reproduced in `docs/conceptual_framework.md` §2.1, but the *script*-form is what auto-discovery needs. **Port this table into the hub's discovery code before deleting `build_experiments_inventory.py`.**

### Hub absorption roadmap — phased plan to retire `scripts/`

Added 2026-05-27 after user confirmed the end-state intent ("once the hub is built, can we get rid of everything in scripts/?"). Yes. Phased plan:

**End state (north star)**: `scripts/` is mostly empty — maybe 1–3 thin entry-point shims (e.g. a `bash predict_new_input.sh ...` wrapper that calls `hub` under the hood). All domain logic lives in `speciesOT/hub/` (or similar). `sbatch/` is no longer a hand-maintained source-of-truth — it's a hub-internal materialization. Data-prep notebooks, docs, mentor meetings, research logs all stay outside the hub.

**Phasing**:

| Milestone | Replaces | Effort | What it does |
|---|---|---|---|
| **v0 — read-only catalog** | `build_experiments_inventory.py`, `regenerate_hvg_flavor_run_matrix.py` | 1–2 days | Auto-discovers every `results/<exp>/<model>/` dir, reads configs + evals.csv + cache/status, presents as a single browsable index. Includes the ported `ALIAS_TABLE` + per-phase disambiguation. Doesn't change anything — just sees what's there. Biggest immediate win: one place to compare models. |
| **v1 — spec-driven generator** | `generate_atlas_full_configs.py`, `generate_data_space_eval_sbatches.py`, `generate_hvg_flavor_configs.py` | 3–5 days | A `Spec` dataclass + an `experiment_factory(spec)` that materializes configs and sbatches. Behind the scenes still writes the same files; from the user side, you write a 10-line YAML instead of forking a 355-line generator. Per-group `n_cells` becomes a first-class spec field (not hard-coded in two different places). |
| **v2 — submission & lifecycle** | `submit_hvg_flavor_matrix.sh`, `run_full_pipeline.sh`, `biomart_watchdog.py`, `refresh_results_loop.sh` | ~1 week | Submit jobs with afterok deps, track status, retry failed, run periodic refresh. Hub becomes the experiment runtime. |
| **v3 — viewer + figures** | `render_results_figures.py` | TBD | Static site or simple dashboard rendering hub catalog + experiment-detail pages with figures on demand. |

Each milestone is independently useful. v0 alone retires two scripts and the inventory CSV pain — recommended as the first concrete hub work after this walkthrough finishes.

**Scripts that stay outside the hub** (or become thin shims):
- `predict_new_input.sh` — new-user CLI entry point; might keep as a 5-line wrapper around a hub subcommand.
- Anything that's specifically about cluster/conda environment activation (module loads, mamba activate) is sysadmin-y — could live in `bin/` rather than the hub.

**Implication for the current walkthrough**: when we reach `cellot/cellot_gpu/results/` and `experiments_inventory.{csv,md}`, every keep/archive decision should be made with the hub in mind — anything kept should be representable as a model-card row.

### Separate project: Auto-written end-of-session research logs (proposed by user 2026-05-25)

**Motivation**: `logs/research_logs/` has lapsed since 2026-05-04 because the user must manually ask the agent to write the daily log. Would be much more reliable if it were automatic.

**Sketch**: use a Cursor session-end hook to invoke a small agent that summarizes the session and appends to `logs/research_logs/research_log_YYYY-MM-DD.txt` (creating the file if it doesn't exist).

### Smaller task: Config glossary doc

Add `docs/config_glossary.md` listing every config knob that appears in our auto-generated `config.yaml` files (e.g. `datasplit.name`, `model.name`, `data.ae_emb.path`, `data.type`, `training.n_inner_iters`), with for each: one-line description, set of valid values (if discrete), and a link to the consumer function in the library (e.g. `cellot/cellot_gpu/cellot/data/cell.py:split_cell_data`). Saves having to do a from-scratch grep every time someone asks "what does `toggle_ood` mean?"

Existing minor naming gotcha worth fixing alongside: in `split_cell_data_toggle_ood`, variables `trainobs`/`testobs` (line 340) are mislabeled — they're really "first half" / "second half" of the holdout cells, not train/test.

### Separate project: Declarative experiment-spec system ("the cookbook"; proposed by user 2026-05-25)

**Motivation**: today every new experiment shape requires a new `generate_*.py` that is essentially a fork of an existing one with config templates copy-pasted and a few values changed. There is no shared abstraction layer. Each generator hard-codes its sbatch template inline and hard-codes its flavor/group/mode/model lists as module constants. `generate_atlas_full_configs.py` explicitly documents itself as a diff against `generate_hvg_flavor_configs.py`. This means the user cannot describe a new experiment without writing (or having an agent write) a new generator.

**Target workflow**:
1. User describes the experiment in a declarative spec — either a YAML file or a short conversation: "OOD setting, holdout = CD8, HVG flavor = pearson_residuals, model = impact_cellot, n_iters = 50000".
2. A single experiment-factory consumes the spec and produces: data-prep step pointer (which notebook), training configs (one per model variant), training sbatches, eval sbatches (data-space + latent-space as requested), expected output paths, an entry in the model-card hub (see separate project).
3. The factory composes from a "cookbook" of small reusable building blocks: `make_sbatch_header(name, time, mem, gpu)`, `materialize_config(template, overrides)`, `chain_with_afterok(jobs)`, `expected_results_path(spec)`, etc.

**Spec vocabulary (initial)**:
- `model_variant ∈ {impact_cellot, scgen}`
- `condition ∈ {species, cell_type}`  (cell_type is the abandoned framing; kept for backwards compat)
- `holdout`: cell-ontology ID or list
- `also_exclude`: optional second cell-ontology ID
- `hvg_flavor ∈ {pearson_residuals, seurat_v3, seurat_v3_paper, cell_ranger, seurat}`
- `framing ∈ {iid, ood}`
- `n_iters`, `batch_size`, `lr`, …
- Output-space evaluation: `data_space` and/or `latent_space`, plus `n_cells` schedule.

**Implication for the current walkthrough**: when we walk `scripts/`, we should *not* try to refactor the generators into shared components yet. Inventory and understand first; the cookbook is a separate project after this walkthrough completes.

## Deferred for now

- **Tier 2 subfolder reorg of `scripts/`** (`generate/`, `submit/`, `render/`, `watch/`, `inventory/`): blocked on completing the script-by-script walk. User likes the idea but wants to know what each file does before moving things.

## Research-correctness findings (do not lose)

### `--embedding ae` / `--where` mis-coupling — symmetric bug pair (discovered 2026-05-27)

Two mirror bugs sharing the same root cause:

- **IMPACT_CellOT + `--where data_space` without `--embedding ae`** → silently produces 50-d latent output into a directory named `evals_ood_data_space/`. The 80 standard `eval_dataspace/` sbatches hit this. The 10 `eval_dataspace_aeflag/` + 8 m2 sbatches (with the flag) produce correct 1000-d gene-space output.
- **scGen + `--where latent_space` without `--embedding ae`** → silently produces 1000-d gene-space output into a directory named `evals_ood_latent_space/`. Symmetric mirror.

**Root cause**: `load_projectors` (lib evaluate.py lines 100–108) returns identity functions for both `encode` and `decode` when `embedding=None`, regardless of `--where`. The cellot model's natural space is latent (because `ae_emb` in config makes the loader pre-encode), scGen's natural space is data (no `ae_emb`); `--embedding ae` is what "switches" away from each model's natural space, and without it, `--where` is silently ignored.

**Why the bug is visible in our project**: the upstream Bunne code had an auto-detect at lib evaluate.py:275 that reads `model-cellot/` sibling's config to infer `embedding`. Our project renamed `model-cellot/` to `impact_cellot/` (deliberately, for IMPACT framing clarity), which disabled the auto-detect and surfaced the latent bugs. The bug was latent in the upstream design; our naming change *exposed* it.

**Universal rule going forward**: every sbatch should pass `--embedding ae` except IMPACT_CellOT + `--where latent_space` (which triggers a column-count assertion crash, and we don't run that combination anyway in practice).

**Implications**: standard-matrix R² heatmaps compare scGen-in-gene-space against IMPACT_CellOT-in-latent-space. Not directly comparable. The IMPACT side of every standard data-space eval needs re-running with `--embedding ae` to fix.

**Status**: documented in `docs/conceptual_framework.md` §5.5 (symmetric framing + upstream auto-detect explanation + spot-check data + universal rule). User confirmed re-runs deferred for now. The hub's eval spec must encode this dependency.

## Resolved (during 2026-05-27 unattended work): scripts/ vs speciesOT/scripts/ duplication

**Finding**: the inner `speciesOT/scripts/` is a *stale, redundant* copy of the outer `scripts/`. All 11 common scripts are **byte-identical** between the two (verified by `diff -q`). The inner has:
- A `README.md` (the only file the outer doesn't have) explaining the intended convention: *"the inner is canonical, the outer is runtime, sync by hand."*
- The fossil `generate_toggle_configs.py` we deleted from the outer in batch 3.

The inner is **missing** the recent additions to the outer:
- `check_uncapped_chain.sh`, `monitor_uncapped_chain.sh` (the new uncapped pipeline scripts).

**Reality**: the documented convention is dead. The outer `scripts/` is where you, Joshua, and agents have all been editing. Inner was last touched at `c342331` (Tier 1 reorg, 6 weeks ago); outer was touched in walkthrough batches 2 and 3 this week.

**Recommendation** (NOT executed during unattended work — policy decision left for the user): delete `speciesOT/scripts/` entirely (13 files including the README) and update workspace-root `README.md` to clarify the outer `scripts/` is the single source of truth. This formalizes the de facto state, prevents future confusion, and aligns with the cleaner pre-hub layout.

**Action queued (awaiting user confirmation)**:
```
git rm -r speciesOT/scripts/
# + update README.md note about scripts/ canonical location
```

---

## Hub v0 design — open questions resolution log

| # | Question | Decision (date) |
|---|---|---|
| 1 | Where does the hub package live? | `speciesOT/hub/` (inner Python package). 2026-05-27. |
| 2 | How much detail in EvalRecord? | (Z) hybrid: full schema preserved + headline summary fields extracted for fast filtering. 2026-05-27. |
| 3 | `project_phase` naming? | **Restructured**: drop `project_phase` as single string; replace with orthogonal structured fields (data_source, normalization, log1p_applied, hvg_method, hvg_input_layer, hvg_batch_key, framing, holdout_cell_types, holdout_species, train_includes_holdout, datasplit_strategy, plus lineage `generated_by`/`created_at`/`last_modified`). Auto-inferred from config + dataset filename. 2026-05-27. |
| 3a | Model family naming? | 4 families, all visible in hub: `scgen`, `impact_cellot`, `cellot_celltype` (abandoned cell-type framing), `cellot_legacy` (legacy crossspecies). 2026-05-27. |
| 4 | EvalRecord granularity? | One record per `evals_*/` subdir (not per ncells row). Compound key `(run_id, eval_id)` where `eval_id` is the subdir name. Full schema preserved per (Z). 2026-05-27. |
| 5 | Include `speciesOT/baseline/results/` in scope? | Yes — frozen historical discovery root alongside `cellot/cellot_gpu/results/`. No new writes go there. **Also**: revised hub design to NOT skip `_archive/` subtrees, so the batch-3 archived toggle cellot subdirs remain discoverable per "include everything" preference. 2026-05-27. |

---

## Cross-cutting workstream: model-framing naming convention

Settled convention (from `presentation_preparation.ipynb`, most up-to-date notebook):

| Use site | Convention | Examples |
|---|---|---|
| Code identifiers (path components, dict keys, CLI flags, variables) | lowercase + underscore | `impact_cellot`, `scgen` |
| Display labels (figure legends, tables, prose) | preserved capitalization | `IMPACT_CellOT`, `scGen` |

**Scope of rename**: only *application-level* labels for the model variant. Out of scope: the library directory `cellot/cellot_gpu/cellot/` (keeps its name); upstream config files; frozen historical results directory names like `cellot/cellot_gpu/results/speciesot_*`, `cross_species_*`, `race_*` (historical artifacts, do not rename — but `_archive/` them as a group is open for discussion).

**What "IMPACT_CellOT" means semantically** (per user, 2026-05-25): same CellOT architecture (Bunne 2023), but the condition variable is *species* (mouse vs human) rather than *perturbation* (control vs treated). Conceptual write-up: pending — see Pending Future Tasks (option i/ii/iii TBD by user).

As we walk each folder, every occurrence of stale labels gets flagged here for batch-rename later (not in-place during the walkthrough).

### Stale terms (alias-resolution from `build_experiments_inventory.py:ALIAS_TABLE`; full table also lives in `docs/conceptual_framework.md` §2.1)
- `impact`, `impact_or`, `swapped_cellot`, `speciesot_cellot` → all = `impact_cellot`
- `cellot` (context-dependent — see §2.1 of conceptual doc): in `toggle` or `speciesot_v1_iter2_*` phase = abandoned cell-type framing; in `legacy_crossspecies` phase = raw-HVG 1000-dim CellOT.
- `speciesot_cellot_swapped`, `normal_cellot` → abandoned cell-type-framing CellOT
- `speciesot_scgen` → `scgen`

### Flagged occurrences (populate as we walk)
- `speciesOT/baseline/results/speciesot_cd8/impact_or/evals_ood_data_space/imputed.h5ad` → `impact_or` = `IMPACT_CellOT`. Resolved.
- `speciesOT/baseline/results/speciesot_cd8/cellot/evals_ood_data_space/imputed.h5ad` → bare `cellot` in speciesot_v1 path = abandoned cell-type framing. Bucket TBD when we walk `speciesOT/` (likely archive next to the toggle_cellot_subdirs).
- `cellot/cellot_gpu/results/toggle_*/impact/` (16 dirs) — `impact` = `impact_cellot`. **Queued rename** for a future batch.
- `cellot/cellot_gpu/results/toggle_*/cellot/` (16 dirs) — archived in batch 3 to `_archive/toggle_cellot_subdirs/`.
- *Continue populating as we visit each folder.*

---

## Per-notebook flags to revisit when we open the `analysis/` folder

| Notebook | Flag |
|---|---|
| `08.1_renorm_vs_stale_comparison.ipynb` | **Important.** Contains stale `cellot = impact` / `cellot = paper_style` overloaded naming. Latent-space-evaluation rationale (stale vs renorm) needs to be documented in design-decisions doc. The "Pearson r not r²" finding originated here. |

---

## Commit history

- `4200f8e` — **Batch 1** (workspace-root cleanup): rename `reference/` → `reference_papers/`, delete `autospeciesOT/`, delete `logs/NOTEBOOK_INDEX.md`, delete `archive/old_notes/*` (3 files), add `docs/conceptual_framework.md`, add `REFACTOR_WALKTHROUGH_2026-05-24.md`. (~1,700 lines removed, ~290 added.)
- `bcce463` — **Batch 2** (scripts/ runtime junk): drop scripts/ .pid/.log/__pycache__ artifacts; untrack 1.2 MB of BioMart caches (`.bcg_*.csv`, `.biomart_*.csv`) and add gitignore rules so they stay untracked.
- `17562ba` — **Batch 3** (toggle fossil archive): delete `scripts/generate_toggle_configs.py` (fossil); move 16 abandoned `cellot/` subdirs into `cellot/cellot_gpu/results/_archive/toggle_cellot_subdirs/` (53 MB, disk-only); update `docs/conceptual_framework.md` §1.2 to clarify the cell-type framing's species-holdout structure.
- `455cf8e` — **Batch 4** (scripts/ walk complete, alias history landed): add `docs/conceptual_framework.md` §2.1 (full alias-history translation table); add hub absorption roadmap v0→v3 with effort estimates and end-state plan; bucket all 6 scripts in groups A/B/C as alive-slated-for-retirement; defer Group D/E walk to hub v2 design.
- (pending commit) — **Batch 5** (sbatch + root files + duplication diff + hub v0 design): sbatch/ walk; scripts/ vs speciesOT/scripts/ duplication resolved (recommendation captured); root files walked and bucketed; new `docs/hub_v0_design.md` written as first-pass hub v0 architecture.

## Queue of moves/renames to apply in next batch

User-confirmation required before executing any of these:
- [ ] `git rm -r speciesOT/scripts/` (delete the stale inner copy; 12 files + 1 README).
- [ ] `git mv REFACTOR_PLAN_2026-05-05.md docs/refactor_plan_2026-05-05.md` (archive original plan under docs/).
- [ ] `git rm HOW_TO_RUN_NEW_INPUT.txt` (keep the `.md`; regenerable via pandoc if mentor needs text).
- [ ] Update workspace-root `README.md` to mention `docs/conceptual_framework.md`, `docs/hub_v0_design.md`, `REFACTOR_WALKTHROUGH_2026-05-24.md`, and clarify "scripts/ at workspace root is the single source of truth."

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
| `scripts/generate_toggle_configs.py` | **delete** (fossil) | `git rm scripts/generate_toggle_configs.py` | Tracked in git → recoverable. Generator's outputs (data files, scgen + impact models) remain useful for monocyte-axis groups (m1, m3, m4) that the hvg_flavor matrix doesn't cover. |
| `cellot/cellot_gpu/results/toggle_*/cellot/` (16 abandoned cell-type-framing model dirs, ~400 MB total, gitignored) | **archive — pending a/b** | (a) move to `cellot/cellot_gpu/results/_archive/toggle_cellot_subdirs/`; (b) delete outright | User confirmed framing is abandoned; choice of move vs. delete depends on whether the GPU-hours are worth preserving for retrospective comparison. |
| `cellot/cellot_gpu/results/toggle_*/{scgen,impact}/` | alive, keep | (queued) rename `impact/ → impact_cellot/` in a later batch when we're ready for live-dir renames | Models for the monocyte groups (m1, m3, m4) are unique to the toggle line and worth preserving. |

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
- **Resolution of the `scripts/` vs `speciesOT/scripts/` duplication**: blocked on walking into the inner package. Will diff the two directories when we get to `speciesOT/`.

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

### Stale terms to watch for (extend this list as we walk)
- `cellot` (when used as a path component or dict key meaning "the IMPACT framing model variant") → `impact_cellot`
- `paper_style`, `cellot_paper`, similar tags meaning "the original-CellOT framing" → decision pending (likely `paper_cellot` if it ever needs a code identifier; may not exist anywhere in current code)
- `impact_or` (e.g. `interactive_impact_or.html`, `interactive_umap_impact_or.html` under `speciesOT/baseline/analysis/`) → `impact_cellot` if same thing
- `--model-framing impact` (CLI flag, was in `autospeciesOT/run_experiment.py`, now deleted) → N/A after deletion

### Flagged occurrences (populate as we walk)
- `speciesOT/baseline/results/speciesot_cd8/cellot/evals_ood_data_space/imputed.h5ad` — old `cellot/` subdir (likely the abandoned cell-type-framing variant, or the pre-rename IMPACT variant — confirm when we reach `speciesOT/`).
- `speciesOT/baseline/results/speciesot_cd8/impact_or/evals_ood_data_space/imputed.h5ad` — old `impact_or/` subdir (semantics unclear; possibly "IMPACT, OOD reverse"? confirm with user).
- `cellot/cellot_gpu/results/toggle_*/{impact,cellot}/` — 16 experiments × 2 stale subdir names. The `impact/` subdir should become `impact_cellot/` (alive, just renamed). The `cellot/` subdir is the abandoned cell-type-framing variant — archive or delete after user confirms no recent references.
- `scripts/generate_toggle_configs.py` writes the stale subdir names — the f-string templates use `impact` and `cellot` bare (lines 260, 271–272, 278). If we keep the script alive, those names should be updated alongside the directory rename.
- *Continue populating as we visit each folder.*

---

## Per-notebook flags to revisit when we open the `analysis/` folder

| Notebook | Flag |
|---|---|
| `08.1_renorm_vs_stale_comparison.ipynb` | **Important.** Contains stale `cellot = impact` / `cellot = paper_style` overloaded naming. Latent-space-evaluation rationale (stale vs renorm) needs to be documented in design-decisions doc. The "Pearson r not r²" finding originated here. |

---

## Commit history

- `4200f8e` — **Batch 1** (workspace-root cleanup): rename `reference/` → `reference_papers/`, delete `autospeciesOT/`, delete `logs/NOTEBOOK_INDEX.md`, delete `archive/old_notes/*` (3 files), add `docs/conceptual_framework.md`, add `REFACTOR_WALKTHROUGH_2026-05-24.md`. (~1,700 lines removed, ~290 added.)

## Queue of moves/renames to apply in next batch

- *empty — will fill as we walk `scripts/` and subsequent folders.*

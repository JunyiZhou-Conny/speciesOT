# Hub handoff doc — for a fresh agent

Last updated: 2026-05-29. Status: **v1.1 shipped, v2 (hub prep) is the highest-priority next milestone.**

Read this in order:

1. This doc, top to bottom (you're here)
2. `docs/hub_design.md` (the architecture + extensibility recipe)
3. `docs/hub_usage.md` (user-facing command reference)
4. `docs/conceptual_framework.md` (model variants, naming history, eval bug etc.)
5. `REFACTOR_WALKTHROUGH_2026-05-24.md` (history of repo decisions — only if you need archaeological context)

Then look at:

- `speciesOT/hub/__init__.py` → `cli.py` → `spec.py` → `discover.py` → `catalog.py` → `resolve.py` → `readers.py` → `render.py` → `figures.py`. That order roughly matches abstraction depth (CLI on top, data loaders at the bottom).
- The latest hub-related commits: `git log --oneline --grep="^Hub"` shows the eight version commits from `181306e` (v0) through `2055129` (v1.1).

---

## 1. What this project is

`/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT` — a cross-species single-cell transport project. Junyi adapts Bunne et al. 2023's CellOT framework to predict human cells from mouse cells (species transport, not the paper's original drug-perturbation framing). The renamed model variant is called `IMPACT_CellOT`. The scGen VAE serves as both a baseline and as the autoencoder embedding that IMPACT_CellOT operates in.

Conceptual depth: `docs/conceptual_framework.md`. Two sections to read first for context: §1 (the three model variants) and §5.5 (the `--embedding ae` evaluation bug we discovered).

## 2. What the hub is

A Python package at `speciesOT/hub/` that catalogs every trained model in the project (currently 177), generates markdown model cards with diagnostic figures, supports declarative experiment specs (clone an existing model's setup, modify a field, generate configs + sbatches), and exports the catalog to CSV/MD. Replaces a constellation of older one-off scripts (`build_experiments_inventory.py`, `regenerate_hvg_flavor_run_matrix.py`, `generate_hvg_flavor_configs.py`, and others).

Architecture: `docs/hub_design.md`. User commands: `docs/hub_usage.md`.

The `./hub` wrapper at workspace root auto-activates the `CellOT` conda env and invokes `python -m speciesOT.hub.cli`. Users type `./hub list`, `./hub show <run_id>`, etc.

## 3. What's been built so far

| Commit | Version | What it ships |
|---|---|---|
| `181306e` | v0 | Read-only catalog: discover, parse, alias-resolve, expose `./hub list` and `./hub show`. |
| `9f0711a` | v0 polish | `./hub` shell wrapper (auto-activates `CellOT` env), `docs/hub_usage.md`. |
| `1df2118` | v0.1 | Markdown model cards (`./hub card <run_id>`, `./hub card --all` → `docs/model_cards/INDEX.md`). |
| `321b910` | v0.1.1 | Run_id disambiguation: `gpu/...` vs `baseline/...` prefix; suffix-matching when unambiguous. |
| `3c24dfc` | v0.5 | Figure attachment matcher (`./hub attach-figures`). |
| `653b63b` | v0.7 | `./hub compare A B` for spec deltas + metric deltas. |
| `e0c53af` | v0.8 | CSV/MD export (`./hub export csv|md`). |
| `774f626` | v1 | Spec system: `./hub spec dump`, `./hub generate`. |
| `2055129` | v1.1 | Extended spec with preprocessing-intent fields; sibling-aware dump; corrected `log1p_applied`; extensibility recipe doc. |

The full hub today is ~1700 LOC across 8 modules in `speciesOT/hub/`. None of those modules import from the other `speciesOT/baseline/` or `scripts/` code — clean separation.

## 4. THE NEXT MILESTONE — v2 hub prep

**This is what to build next.** Junyi explicitly asked for it 2026-05-29.

### The use case

Data prep is currently a notebook task (`speciesOT/baseline/analysis/01.5_data_prep_all_holdouts_hvg_flavors.ipynb`). To add a new experiment cell (e.g. m1 with modern preprocessing), Junyi has to:
1. Open 01.5 in the `analysis` conda env (different env from `CellOT`)
2. Edit the `GROUPS` dict to add the new entry
3. Set `RUN_GROUP_KEYS` and `RUN_FLAVORS` to restrict scope
4. Run-all the notebook
5. Wait — even the first chunk takes "forever"

The end product is a single `.h5ad` file at `cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_<flavor>_<group>_v07.h5ad`. The hub then takes over.

What the user wants: **`./hub prep specs/m1_modern.yaml`** consumes the same spec the v1 generator uses and materializes the .h5ad file. Same one-spec-one-command flow as the rest of the hub.

### What it has to do

Reading the spec's preprocessing-intent fields (already there, recorded by v1.1):

```yaml
source_datasets:
  mouse: /n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_muris/sampled_mouse_shared.h5ad
  human: /n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_sapiens/sampled_human_shared.h5ad
assay_filter:
  mouse: [chromium_v2]
  human: [chromium_v3]
cap_cells_per_type:
  mouse: 1000
  human: 1000
ortholog_source: biomart
hvg_method: pearson_residuals
hvg_n_top: 1000
hvg_input_layer: layers['counts']
hvg_batch_key: species
log1p_applied: true
holdout_cell_types: [CL:0000875]
```

Plus the canonical procedure from 01.5 §2–§6:

1. Load `source_datasets.mouse` and `source_datasets.human` AnnData objects.
2. **Promote `.raw` to `.X`** so integer UMI counts are accessible.
3. Apply ortholog matching: map mouse symbols → human symbols using BioMart (or pre-cached mapping at `scripts/.biomart_ortholog_cache.csv`, regeneratable).
4. **Match cells by (cell_type_ontology_term_id, tissue_ontology_term_id)** — pairs each mouse cell with a human cell sharing the same cell type + tissue. Result: ~12,990 paired cells (6,495 per species).
5. Filter out the holdout cell types' cells (or in `mode: iid`, keep them — see 01.5 §6).
6. Run `sc.pp.highly_variable_genes(..., flavor=hvg_method, batch_key=hvg_batch_key, layer=hvg_input_layer)` on the appropriate layer. Get the top `hvg_n_top` HVG.
7. Subset to those HVG.
8. `sc.pp.normalize_total(target_sum=1e4)` + `sc.pp.log1p()` — `.X` becomes log-normalized.
9. **Drop `.layers['counts']`** (per 01.5 convention; downstream training reads `.X` only).
10. Save to `cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_<flavor>_<group>_v07.h5ad`.

### Implementation gotchas

- **Conda env**: the prep code needs `scanpy >= 1.12` (which lives in the `analysis` env). The hub currently runs in the `CellOT` env (scanpy 1.8.1). Two options:
  - **Option A**: `./hub prep` shells out to a python invocation in the `analysis` env (similar to how `./hub` wrapper activates CellOT). Less clean but works immediately.
  - **Option B**: put `prep.py` in a separate module that doesn't get imported by the catalog/cli code, and let users invoke it manually with `python -m speciesOT.hub.prep <spec.yaml>` after activating analysis. Even cleaner.
- **Time**: 01.5's first chunk is slow because of BioMart lookups for ortholog mapping (probably 100k+ symbols). Use the cached version at `scripts/.biomart_ortholog_cache.csv` if it exists. Fall back to live BioMart query.
- **Source files require attention**: `sampled_mouse_shared.h5ad` and `sampled_human_shared.h5ad` are NOT in this repo — they live in Josh's `data/` tree. The hub's `prep` step depends on them being readable; if they ever move or are renamed, fail loudly with a clear error pointing at where they should be.
- **Reproducibility**: the spec should capture a `random_state` for the matching step. Already in `ExperimentSpec.random_state` (default 0).
- **Existing files**: like `./hub generate`, `./hub prep` should refuse to overwrite an existing `.h5ad` unless `--force` is passed. Big files = big mistakes to avoid.

### Suggested approach

1. Look at notebook 01.5 carefully — `§1` (GROUPS + RUN_KEYS), `§2` (promote .raw), `§3` (ortholog match), `§5` (HVG dispatcher), `§7` (round-trip + write). Identify which cells you'd need to port to Python.
2. Implement `speciesOT/hub/prep.py` with a single entry point `prep_from_spec(spec, force=False)`.
3. Wire `./hub prep <spec.yaml>` in `cli.py`.
4. Test by running `./hub prep specs/m1_modern.yaml` and verifying the output matches what 01.5 would have produced (file size, shape, .X distribution).
5. Update `docs/hub_usage.md` with a v2 section showing the full one-command workflow.

Estimated effort: **1–2 days of focused work**. Most of the logic is straightforward port from 01.5; the env handling and ortholog caching are the main risk areas.

## 5. Key design principles to preserve

These came up across many conversations; please honor them.

### 5a. Extensibility over completeness

> The hub doesn't need to be perfect — it needs to be **extensible**. When a new preprocessing knob, model variant, or evaluation flag appears, the hub should be able to absorb it without major surgery. Add a field, update the renderer that consumes it, ship.

Concrete recipe: `docs/hub_design.md` §13. Three classes of feature (pure metadata, affects training, new data-prep step), with examples.

### 5b. Always pass `--embedding ae` for `--where data_space` IMPACT_CellOT evals

There's a real evaluation bug (`docs/conceptual_framework.md` §5.5): without `--embedding ae`, IMPACT_CellOT data-space evals silently produce latent-space results. The hub's v1 `render_eval_dataspace_sbatch` ALWAYS emits the flag for impact_cellot, fixing this. Don't regress.

### 5c. True R² (square the Pearson r)

The upstream `evaluate.py` labels Pearson r as `r2-means`. The hub's `readers.read_evals_csv()` squares all `r2-*` rows on read so every downstream consumer sees true R². This is foundational — don't unwind it.

### 5d. Conservative deletes; archive over rm

Junyi has been comfortable with permanent deletions for gitignored junk, but conservative for tracked files (the workflow has been "queue → confirm → execute"). When in doubt: archive (`git mv` to `_archive/` subfolder) rather than `rm`.

### 5e. The hub doesn't auto-submit sbatches

`./hub generate` writes files and *prints* the sbatch submission chain. The user copies and pastes. This is deliberate — the safety boundary is at submission, not at file-writing. Future `./hub submit <spec>` could be added (v2.5?), but it must be opt-in.

## 6. Codebase orientation

```
speciesOT/hub/
├── __init__.py       — version marker
├── cli.py            — argparse + subcommand dispatch (entry point)
├── catalog.py        — ModelRecord, EvalRecord, Catalog dataclasses
├── discover.py       — walk results trees, build records (TWO ROOTS, see §7)
├── readers.py        — config.yaml, evals.csv, cache/status parsers
├── resolve.py        — alias resolution (4 families) + per-phase overrides
├── render.py         — markdown card rendering + CSV/MD export + compare
├── figures.py        — figure attachment matcher
└── spec.py           — ExperimentSpec + spec_from_record + generate_artifacts

hub                   — shell wrapper at workspace root (auto-activates CellOT env)
docs/
├── hub_handoff.md    — this doc
├── hub_design.md     — architecture
├── hub_usage.md      — user reference
└── conceptual_framework.md — model variants, naming, eval bug

specs/                — declarative experiment specs (one per cell)
├── m2_baseline.yaml  — example: dumped from the existing m2 model
└── m1_modern.yaml    — example: cloned from m2 for the planned m1 experiment

experiments_inventory.csv  — auto-generated by ./hub export csv
experiments_inventory.md   — auto-generated by ./hub export md
docs/model_cards/          — auto-generated by ./hub card --all (gitignored)
```

## 7. Quirks and gotchas

### 7a. Two discovery roots; run_ids are prefixed

The catalog walks **two** roots:
1. `cellot/cellot_gpu/results/` → run_ids like `gpu/hvg_seurat_d_ood/impact_cellot`
2. `speciesOT/baseline/results/` → run_ids like `baseline/speciesot_cd8/cellot`

Both are kept per Junyi's "include everything" preference (see hub design Q5 resolution). When users type a short form (`hvg_seurat_d_ood/impact_cellot`), `Catalog.by_run_id()` suffix-matches it to a unique full id — or errors with the candidate list if ambiguous.

### 7b. The 4 model families

`scgen`, `impact_cellot`, `cellot_celltype` (abandoned cell-type framing), `cellot_legacy` (the raw-HVG legacy_crossspecies experiments). Aliases are resolved in `resolve.py:_ALIAS_TO_FAMILY` — adding a new alias is a one-line patch there. Adding a new family is a bigger change (affects card rendering, comparison logic).

### 7c. Parallel work areas — don't touch

The user has active work in:
- `speciesOT/baseline/analysis/presentation_preparation.ipynb` (another agent edits this)
- `speciesOT/baseline/analysis/19_uncapped_cd8_ood_data_prep.{ipynb,py}` (the uncapped sampling experiments)
- `speciesOT/baseline/analysis/umap_learn_and_investigate.ipynb` (where m1-vs-m2 investigation started)
- `speciesOT/baseline/analysis/20_m1_pearson.ipynb` (current m1 data prep run)
- `docs/conceptual_framework.md` (user takes notes in markdown comments)
- `cellot/cellot_gpu/cellot/utils/evaluate.py` (user takes notes in code comments)
- `cellot/cellot_gpu/scripts/evaluate.py` (same)

Treat these as read-only unless the user explicitly asks.

### 7d. Remote git status

There's a `josh` remote at `https://github.com/JoshuaPrice/speciesOT.git` with ~10 commits diverged from local main. The user knows. No `git push` should be run by any agent unless explicitly asked.

### 7e. Two conda envs

- `CellOT`: scanpy 1.8.1, has yaml, has pandas. The `./hub` wrapper auto-activates this.
- `analysis`: scanpy 1.12, has the modern HVG functions (Pearson residuals, seurat_v3_paper). Used for notebook 01.5 / 19 / 20.

`./hub prep` (the next milestone) likely needs to invoke `analysis` env. See §4 implementation gotchas.

## 8. Open follow-ups (sorted by priority)

1. **v2 — `./hub prep <spec.yaml>`** (highest priority; details in §4)
2. Re-run the 80 standard `eval_dataspace` sbatches with `--embedding ae` to fix the §5.5 bug for the existing matrix. The hub generates correct ones for new cells, but the existing matrix still has the buggy outputs on disk. Mechanical: regenerate via `./hub spec dump` + `./hub generate --force` for each cell, then resubmit the data-space eval sbatch.
3. Retire `scripts/build_experiments_inventory.py` and `scripts/regenerate_hvg_flavor_run_matrix.py` (replaced by `./hub export`). Pending the user diffing the new CSV against the old to confirm no rows lost.
4. The walkthrough left some pending sign-offs from earlier batches:
   - `git mv REFACTOR_PLAN_2026-05-05.md docs/refactor_plan_2026-05-05.md` (archive the original plan under docs/)
   - `git rm HOW_TO_RUN_NEW_INPUT.txt` (workspace-root; keep the .md; the .txt is regenerable via pandoc)
   - Update root `README.md` to point at the new `docs/` structure
5. **v3 (eventually) — `./hub submit <spec.yaml>`**: actually launch the sbatch chain after confirming dependencies. Currently the chain is printed and user pastes. v3 would automate but should require a `--confirm` flag.
6. **v2.5 (eventually) — `./hub figure-pack <run_id>`**: regenerate diagnostic UMAPs / biomarker plots from scratch for newly-trained models (the matcher in v0.5 only links existing figures; can't generate new ones).

## 9. Acceptance criteria for v2

When `./hub prep specs/m1_modern.yaml` works:

- Produces `cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_m1_v07.h5ad`
- File has shape ~(12990, 1000) — same scale as the existing m2 file
- `.X` is float, min=0, max ≈ 8.8 (log1p signature)
- `.layers` is empty (raw counts dropped before write)
- `.obs` has the standard columns (condition, species, cell_type_ontology_term_id, etc.)
- Output matches what notebook 01.5 would have produced (modulo determinism quirks from BioMart ordering)
- The hub's existing `./hub generate specs/m1_modern.yaml` + sbatch chain still works end-to-end with the file produced by `./hub prep`

After that ships, the full one-command flow for "add a new experiment cell" becomes:

```bash
# Edit specs/m1_modern.yaml to taste, then:
./hub prep specs/m1_modern.yaml      # NEW in v2
./hub generate specs/m1_modern.yaml  # v1
# copy-paste the sbatch chain
# wait
./hub list / show / compare
```

That's the goal. Good luck.

# Model-card hub — v0 design

A first-pass design for the read-only catalog phase of the planned model-card hub. Written 2026-05-27 by the walkthrough agent for Junyi to review.

**Scope of v0**: walk the results tree, read what's there, present a browsable index. No mutations, no submission, no figure rendering. The goal is to retire `scripts/build_experiments_inventory.py` + `scripts/regenerate_hvg_flavor_run_matrix.py` (~600 LOC combined) and replace the flat `experiments_inventory.{csv,md}` files with something queryable.

**Effort estimate**: 1–2 focused days of coding. The biggest risks are (a) auto-discovery edge cases (legacy_crossspecies dirs, top-level non-sub-dir experiments) and (b) faithfully porting the `ALIAS_TABLE` and per-phase disambiguation logic.

---

## 1. Goals (v0 ships)

- **Walk the results tree once**: `cellot/cellot_gpu/results/` + `speciesOT/baseline/results/` → list of model directories.
- **Read each model dir**: parse `config.yaml`, read `cache/status`, check what evals exist (`evals_ood_data_space/evals.csv`, `evals_ood_latent_space/evals.csv`, others).
- **Resolve identity via aliases**: every model gets a canonical `(model_family, framing, condition)` triple, even if the directory name is `impact`, `impact_or`, `swapped_cellot`, `speciesot_cellot`, etc.
- **Compute headline metrics**: for each evals.csv that exists, pull out R² of means (Pearson r squared per §5.5 of `conceptual_framework.md`) and MMD at the default `nfeatures=all, ncells=80` (or whatever's available).
- **Render the catalog in three formats**:
  - **`hub.list`** — terse CLI table (one model per row, key columns: tag, family, framing, holdout, status, R², MMD).
  - **`hub.show <run_id>`** — full detail for a single model: every config field, every eval, all sbatches that targeted it, output paths.
  - **`hub.export csv`** / **`hub.export md`** — replacements for `experiments_inventory.{csv,md}`.
- **Stable run-ID scheme**: a one-line `run_id` per model directory, e.g. `hvg_seurat_d_ood/impact_cellot`. This becomes the primary key throughout the hub.

## 2. Non-goals (deferred to v1+)

- No spec → config generation (that's v1).
- No sbatch submission, no afterok chains, no watchdogs (v2).
- No figure rendering (v3).
- No HTML viewer or web UI in v0 — terminal output + exported markdown only. The user can `cat hub_export.md` in their browser-rendered IDE pane if they want a richer view.
- No editing of existing files (read-only).
- No interactive mode, no fancy filtering (just `hub.list --filter family=impact_cellot` style flags).

## 3. Where the hub lives

```
speciesOT/                               ← workspace root
└── speciesOT/                           ← inner Python package (rename TBD post-walkthrough)
    └── hub/                             ← NEW: the hub package
        ├── __init__.py
        ├── discover.py                  ← walk results dirs, find model directories
        ├── resolve.py                   ← apply ALIAS_TABLE + per-phase overrides
        ├── catalog.py                   ← dataclasses: ModelRecord, EvalRecord, Catalog
        ├── readers.py                   ← parse config.yaml, evals.csv, status
        ├── render.py                    ← list, show, export-csv, export-md
        └── cli.py                       ← entry point: `hub list`, `hub show <run_id>`, …
```

After the hub is functional, the workspace-root `scripts/` becomes thin shims that wrap into the hub package — or disappears entirely. See the `REFACTOR_WALKTHROUGH` scratchpad's hub absorption roadmap.

## 4. Data model

```python
@dataclass(frozen=True)
class EvalRecord:
    space: Literal["data_space", "latent_space"]      # from evalprefix or subdir name
    n_cells: int                                       # 30, 50, 80, …
    n_features: int | Literal["all"]                   # the nfeatures column in evals.csv
    r2_means: float                                    # PEARSON r squared (already squared from raw)
    mmd: float
    other_metrics: dict[str, float]                    # r2-stds, r2-pairwise_feat_corrs, etc.
    eval_csv_path: Path
    mtime: datetime

@dataclass(frozen=True)
class ModelRecord:
    run_id: str                                        # e.g. "hvg_seurat_d_ood/impact_cellot"
    model_dir: Path                                    # absolute path
    family: Literal["scgen", "impact_cellot", "cellot_celltype_framing", "cellot_legacy_crossspecies"]
    family_alias_seen: str                             # the on-disk subdir name (impact, impact_or, ...)
    framing: Literal["species", "cell_type", "drug", "legacy"]
    condition: str                                     # the literal value of config.data.condition
    source: str                                        # config.data.source
    target: str                                        # config.data.target
    holdout: list[str] | None                          # e.g. ["CL:0000625"]
    holdout_human: list[str] | None                    # e.g. ["CL:0000625 (CD8+ alpha-beta T cell)"]
    mode: Literal["iid", "ood", None]                  # None when datasplit.name != toggle_ood
    datasplit_name: str                                # "toggle_ood" or "train_test"
    datasplit_key: str | None                          # "cell_type_ontology_term_id" or "species"
    data_file: str                                     # config.data.path (relative)
    ae_emb_path: str | None                            # config.data.ae_emb.path if any
    n_iters: int
    batch_size: int
    hidden_units: list[int]
    latent_dim: int
    lr: float
    optimizer: str
    status: Literal["done", "running", "aborted", "never_started"]
    evals: list[EvalRecord]
    project_phase: str                                 # legacy_crossspecies, speciesot_v1, toggle, renorm, hvg_flavor, atlas_full, ...
    notes: str                                         # free-form, ported from build_experiments_inventory.py
    created_mtime: datetime                            # earliest mtime of files in model_dir
    last_modified: datetime                            # most-recent mtime

@dataclass
class Catalog:
    records: list[ModelRecord]
    walk_root: list[Path]                              # the two roots: cellot_gpu/results, baseline/results
    discovered_at: datetime

    def filter(self, **kw) -> "Catalog": ...           # simple equality filter
    def by_run_id(self, run_id: str) -> ModelRecord: ...
    def export_csv(self, path: Path) -> None: ...
    def export_md(self, path: Path) -> None: ...
```

`ModelRecord` is the unit of identity. Two models that differ in any of `(family, holdout, mode, hidden_units, lr, batch_size, n_iters, data_file)` are distinct records. The user-facing display can group/aggregate however the user wants.

## 5. Discovery algorithm

The hub discovers across **two roots**:
1. `cellot/cellot_gpu/results/` — the main results tree (active + historical + archived).
2. `speciesOT/baseline/results/` — the older speciesot_v1 holdings (locked-in 2026-05-27 per Junyi: "include everything in the Hubscope"). No new model writes happen here; the dir is essentially frozen historical.

```python
def discover(roots: list[Path]) -> Iterator[Path]:
    """Find every model directory under the given roots."""
    for root in roots:
        for config_yaml in root.rglob("config.yaml"):
            model_dir = config_yaml.parent
            # Skip the upstream library's own task templates
            if "configs" in model_dir.parts and "cellot" in model_dir.parts:
                continue
            yield model_dir
```

A model dir is defined by "contains a `config.yaml`". The walker is intentionally **inclusive** — `_archive/` subtrees are discovered too. The reason: per Junyi's "include everything" preference (2026-05-27), the hub should surface every model that has been trained, even abandoned-framing models we moved to `_archive/` for disk-tidiness reasons. The archive directories signal "moved out of the way," not "hidden."

What does get excluded:
- The upstream library's `configs/tasks/*.yaml` (those are config templates for the upstream paper's experiments — not our trained models).
- Stray legacy paths that have a `config.yaml` but no `cache/` — those get an `aborted` / `never_started` status from `readers.py` and still appear in the catalog with that status.

**Records from archived dirs** carry the standard `family` field (e.g. `cellot_celltype` for the abandoned cell-type framing), so they're visible-but-distinguishable. The user can filter them out with `hub list --filter family!=cellot_celltype` if desired, but the default `hub list` shows them.

## 6. Alias resolution

Direct port of `ALIAS_TABLE` and per-phase overrides from `scripts/build_experiments_inventory.py` (lines 120–139 + 193–198), reshaped as:

```python
# resolve.py

CANONICAL = {
    "scgen": ("scgen", "scgen / speciesot_scgen / autoencoder"),
    "speciesot_scgen": ("scgen", ...),
    "impact": ("impact_cellot", ...),
    "impact_or": ("impact_cellot", ...),
    "swapped_cellot": ("impact_cellot", ...),
    "speciesot_cellot": ("impact_cellot", ...),
    "speciesot_cellot_swapped": ("cellot_celltype_framing", ...),
    "normal_cellot": ("cellot_celltype_framing", ...),
}

CELLOT_PHASE_OVERRIDES = {
    "legacy_crossspecies": "cellot_legacy_crossspecies",
    "speciesot_v1_iter2_groupA": "cellot_celltype_framing",
    "toggle": "cellot_celltype_framing",
}

def resolve_family(subdir_name: str, project_phase: str) -> str:
    if subdir_name == "cellot":
        return CELLOT_PHASE_OVERRIDES.get(project_phase, "cellot_unresolved")
    return CANONICAL[subdir_name][0]
```

The `project_phase` is inferred from the experiment tag (the parent dir name): `cross_species_*` → `legacy_crossspecies`; `toggle_*` → `toggle`; `hvg_*` → `hvg_flavor`; `atlas_full_*` → `atlas_full`; `renorm_*` → `renorm`; `speciesot_*` (legacy) → `speciesot_v1`; etc. This logic lives in `resolve.py`.

**The bare `cellot` family `cellot_unresolved`** is intentional. It signals "this experiment dir has a `cellot` subdir but we don't recognize the phase" — the catalog should show it but flag it for human review. Better than silently picking the wrong meaning.

## 7. Reading existing artifacts

`readers.py` parses three sources:

- **`config.yaml`**: PyYAML safe_load. Already-known schema (we walked it in conversation; see `docs/conceptual_framework.md` and config-walkthrough discussion).
- **`cache/status`**: 4-byte file with a string ("done", "running", "aborted"). If absent → `never_started`.
- **`evals_*/evals.csv`**: pandas DataFrame with columns like `metric, nfeatures, ncells, value`. Pivot to wide form. **Critically**: square every `r2-*` row immediately after reading (Pearson r → R²), matching what `scripts/render_results_figures.py` does.

```python
R2_METRICS = {"r2-means", "r2-stds", "r2-pairwise_feat_corrs"}

def read_evals_csv(p: Path) -> pd.DataFrame:
    df = pd.read_csv(p)
    df.loc[df["metric"].isin(R2_METRICS), "value"] **= 2
    return df
```

This is the one-line bug-fix from §5.5 of the conceptual doc, moved to a library function so every consumer gets it for free.

## 8. Renderers

```
hub list                                    → terse table to stdout
hub list --filter family=impact_cellot      → filter on any ModelRecord field
hub list --filter project_phase=hvg_flavor --sort r2_means
hub show hvg_seurat_d_ood/impact_cellot     → full detail for one model
hub export csv -o /tmp/inventory.csv        → replaces experiments_inventory.csv
hub export md -o /tmp/inventory.md          → replaces experiments_inventory.md
hub diff <run_id_a> <run_id_b>              → bonus: show what differs between two models
```

The `diff` command is a stretch goal but cheap to write once `ModelRecord` exists, and directly addresses the user's "make tiny differences legible" request from 2026-05-27.

## 9. CLI shape (entry point)

```python
# pyproject.toml or setup.py
[project.scripts]
hub = "speciesOT.hub.cli:main"
```

Then on the shell:

```bash
$ hub list --filter project_phase=hvg_flavor --sort r2_means
RUN_ID                                          FAMILY         HOLDOUT             MODE  STATUS  R²_means  MMD
hvg_pearson_residuals_a_ood/impact_cellot       impact_cellot  CD8+ T cell         ood   done    0.812     0.034
hvg_pearson_residuals_a_iid/impact_cellot       impact_cellot  CD8+ T cell         iid   done    0.897     0.018
hvg_pearson_residuals_a_ood/scgen               scgen          CD8+ T cell         ood   done    0.745     0.052
…

$ hub show hvg_seurat_d_ood/impact_cellot
run_id              : hvg_seurat_d_ood/impact_cellot
family              : impact_cellot  (alias seen on disk: impact_cellot)
framing             : species
project_phase       : hvg_flavor
condition           : condition  (= "mouse" → "human")
holdout             : CL:0000624  (CD4+ alpha-beta T cell)
mode                : ood
data_file           : datasets/speciesot-human-mouse-hvg/hvg_seurat_d_v07.h5ad
ae_emb              : ./results/hvg_seurat_d_ood/scgen/
architecture        : ICNN, hidden_units=[64,64,64,64], latent_dim=50
optimizer           : Adam lr=0.0001 beta1=0.5 beta2=0.9
training            : n_iters=50000, n_inner_iters=10, batch_size=128
status              : done
evals (2):
  data_space   ncells=30  r2_means=0.612  mmd=0.041
  latent_space ncells=80  r2_means=0.834  mmd=0.027
```

That's enough output to (a) confirm what a model is, (b) compare two of them, (c) decide whether to re-run an eval.

## 10. Acceptance criteria for v0

- [ ] `hub list` runs in < 5 seconds across all of `cellot/cellot_gpu/results/` + `speciesOT/baseline/results/`.
- [ ] Every model that appears in the current `experiments_inventory.csv` appears in `hub export csv` output (one row).
- [ ] No models are *missing* from `hub list` that the current inventory would have caught (i.e. discovery is at least as thorough as the hand-coded tuples in `build_experiments_inventory.py`).
- [ ] R² values match what `render_results_figures.py` prints (i.e. the Pearson → square correction is applied consistently).
- [ ] Every alias in `ALIAS_TABLE` is resolved correctly: a model dir named `impact_or` and a model dir named `impact_cellot` produce records with the same `family` field.
- [ ] `hub show <run_id>` for any model emits a single clean panel with no errors.
- [ ] One smoke test per renderer: list, show, export-csv, export-md.

## 11. Open questions for Junyi

These are things I'd want to know before starting v0 implementation:

1. **Where should the hub package live?** I sketched `speciesOT/hub/` (inner Python package). Alternatives: `hub/` at workspace root (separate package), or `scripts/hub/` (keep CLI-adjacent). My weak preference is `speciesOT/hub/` because the hub *is* part of the speciesOT project, but if you want to publish/install it independently, top-level might be cleaner.
2. **Should `EvalRecord` include the upstream `evaluate.py` output columns verbatim** (so the hub captures the full evals.csv schema), or only the user-facing pivoted summary? My read: capture everything but display only key metrics by default. Storage is cheap.
3. **Is there a particular naming convention you want for `project_phase`?** I used `legacy_crossspecies`, `speciesot_v1`, `toggle`, `renorm`, `hvg_flavor`, `atlas_full`, `bcg`. Will appear as a column / filter value, so worth getting right.
4. **What about evaluation_id?** Two evals at different `n_cells` are different records. Should they share a `model.run_id` parent and have their own `eval_id`? I think yes — the 1:N relationship you flagged on 2026-05-27 fits this exactly.
5. ~~Do you want to include `speciesOT/baseline/results/` in scope?~~ **Resolved 2026-05-27**: yes, include everything; `speciesOT/baseline/results/` is a discovery root alongside `cellot/cellot_gpu/results/`. The dir is essentially frozen historical — no new writes go there; all future results land in `cellot/cellot_gpu/results/`.

## 12. How the cookbook (v1) collapses CellOT's three-layer YAML system

(Captured 2026-05-27 — relevant for v1's design, scoped out of v0.)

The upstream CellOT codebase has three YAML layers:

1. **Task templates** in `cellot/cellot_gpu/configs/tasks/*.yaml` — `data:`, `dataloader:`, `datasplit:` blocks.
2. **Model templates** in `cellot/cellot_gpu/configs/models/*.yaml` — `model:`, `optim:`, `scheduler:`, `training:` blocks.
3. **Merged config** at `cellot/cellot_gpu/results/<exp>/<model>/config.yaml` — union of Layer 1 + Layer 2 + CLI overrides.

Upstream's train.py composes Layer 1 + Layer 2 at train time:
```bash
python ./scripts/train.py --outdir ./results/X/Y \
    --config ./configs/tasks/A.yaml \
    --config ./configs/models/B.yaml \
    --config.data.target Z
```

Our current workflow already bypasses this: `scripts/generate_hvg_flavor_configs.py` writes Layer 3 directly as inline f-strings, skipping the composition. The 13 stale `speciesot-*.yaml` files were archived to `cellot/cellot_gpu/configs/tasks/_archive/speciesot_v1/` during the walkthrough (2026-05-27) for this reason.

**The cookbook spec collapses all three layers into one declarative input.** The user authors one spec; the factory materializes Layer 3 internally and (optionally) records the spec alongside as provenance. The user-facing `configs/tasks/` and `configs/models/` directories disappear from the workflow — they become *internal* templates the factory composes against, never edited by hand.

This means:
- A new experiment = one spec, not "edit task template + edit model template + figure out composition + write generator."
- The hub catalog (v0) discovers the Layer 3 files that already exist on disk. The hub generator (v1) writes new Layer 3 files from specs. Both pieces share the same understanding of the merged-config shape (the `ModelRecord` dataclass).
- The upstream Layer 1 task templates (`4i.yaml`, `sciplex3-*.yaml`, etc.) and the `crossspecies*.yaml` ones can stay in `configs/tasks/` as inert reference material; they're not part of the cookbook's path.

## 13. What this doc is NOT

- Not a green-light for implementation. It's a design proposal. The user reviews, picks apart, and either approves or rewrites before any code lands.
- Not a commitment to the exact CLI / data model. These are *first proposals* — iterate freely.
- Not the full hub. v0 is a sliver. The cookbook (v1), submission/lifecycle (v2), and viewer (v3) are downstream of this.

---

## Cross-references

- `docs/conceptual_framework.md` — model variants, naming conventions, alias history (§2.1), R²-vs-r footgun (§5.5).
- `REFACTOR_WALKTHROUGH_2026-05-24.md` — the running scratchpad. See "Hub absorption roadmap" for the v0→v3 plan and "Per-model-variation deltas" + "One-model-to-many-sbatches" insights captured during the walkthrough.
- `scripts/build_experiments_inventory.py` — the script v0 replaces. The `ALIAS_TABLE` (lines 120–139) and per-phase overrides (lines 193–198) are the irreplaceable parts that must port over.
- `scripts/regenerate_hvg_flavor_run_matrix.py` — also replaced by v0's `export csv` / `export md`.

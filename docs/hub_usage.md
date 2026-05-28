# Using the hub (v0)

A model-card catalog for every CellOT/IMPACT_CellOT/scGen run in this project. v0 is **read-only** — it discovers what's already on disk, parses it, and presents it in a queryable form.

Design doc: [`hub_v0_design.md`](hub_v0_design.md).
Conceptual context: [`conceptual_framework.md`](conceptual_framework.md).

---

## Quick start

From the workspace root:

```bash
./hub list                              # all models
./hub show <run_id>                     # full detail for one model
```

The `hub` wrapper auto-activates the `CellOT` conda env (which has `yaml` and `pandas`). If your conda is at a non-standard path, edit `CONDA_INIT` near the top of the `hub` script.

If you'd rather invoke directly, the equivalent commands are:

```bash
conda activate CellOT
python -m speciesOT.hub.cli list
python -m speciesOT.hub.cli show <run_id>
```

---

## What's in the catalog

The hub walks two roots:
- `cellot/cellot_gpu/results/` (main active tree)
- `speciesOT/baseline/results/` (frozen historical from speciesot_v1 era)

It catalogs every directory that contains a `config.yaml`. As of 2026-05-28 that's **175 models** across four families.

### The 4 model families

| Family | What it means |
|---|---|
| `scgen` | The scGen VAE baseline |
| `impact_cellot` | IMPACT_CellOT (species framing). Current main model. |
| `cellot_celltype` | The abandoned cell-type-framing CellOT (non-X → X, holdout=human) |
| `cellot_legacy` | The earliest direct-CellOT-on-raw-HVG runs (cross_species_ood, race_*) |

Alias resolution is automatic: dirs named `impact`, `impact_or`, `swapped_cellot`, `speciesot_cellot` all map to family `impact_cellot`. See `docs/conceptual_framework.md` §2.1 for the full alias table.

### The R² values are real R² (not Pearson r)

The upstream `evaluate.py` labels its Pearson-r column as `r2-means` (see `docs/conceptual_framework.md` §5.5). The hub squares these on read so every reported R² downstream is true R². You can trust the numbers.

---

## Common commands

### List + filter

```bash
./hub list                                                # all models
./hub list --filter family=impact_cellot                  # only IMPACT_CellOT
./hub list --filter hvg_method=pearson_residuals          # only this flavor
./hub list --filter status=done --filter family=scgen     # combine filters
./hub list --filter holdout_species=human                 # the abandoned framing
./hub list --sort hvg_method                              # sort
./hub list --sort run_id --desc                           # sort descending
```

Filterable fields include: `family`, `hvg_method`, `status`, `framing`, `normalization`, `data_source`, `train_includes_holdout`, `datasplit_strategy`, `model_name`, `latent_dim`, `n_iters`, `batch_size`, and any other top-level `ModelRecord` field. See `speciesOT/hub/catalog.py` for the full schema.

### Show full detail

```bash
./hub show hvg_seurat_d_ood/impact_cellot
./hub show hvg_pearson_residuals_m2_iid/impact_cellot
./hub show _archive/toggle_cellot_subdirs/toggle_m2_ood/cellot       # archived models work too
```

Output sections: identity, data provenance, framing, holdout, architecture, lineage, evaluations.

### Inspecting filters quickly

```bash
./hub list | wc -l                                        # quick total count
./hub list --filter family=impact_cellot | wc -l          # count one family
./hub list --filter hvg_method=pearson_residuals \
           --filter framing=species \
           --filter status=done | wc -l                   # active matrix cells
```

---

## Markdown model cards (v0.1)

```bash
./hub card <run_id>             # writes one card to docs/model_cards/
./hub card --all                # writes 175 cards + an INDEX.md grouped by family
```

Open `docs/model_cards/INDEX.md` in Cursor's preview pane (Cmd-Shift-V) for a clickable browseable view. Each model card has full tables for data provenance, framing, holdout, architecture, lineage, plus inline diagnostic figures (see below) and per-eval R²/MMD with true (squared) values.

## Diagnostic figure attachment (v0.5)

```bash
./hub attach-figures --dry-run  # preview what would be linked (no changes)
./hub attach-figures            # create the symlinks (idempotent)
./hub attach-figures --overwrite # replace existing symlinks
```

Scans `speciesOT/baseline/analysis/{presentation_figure_outputs,umap_learn_outputs,hvg_flavor_nb14_outputs/figures}/` for image files (PNG/PDF/SVG), matches each one to compatible models by `(group, hvg_method, mode)` extraction, and creates symlinks at `<model_dir>/figures/<figname>` so the cards pick them up.

The matcher is conservative — only per-experiment-cell figures are attached. Matrix-wide figures (`method_gap_*`, `figure_F_*_OOD.png`, paper-figure replicas, BCG-domain figures) are not auto-attached.

After running `attach-figures`, regenerate cards (`./hub card --all`) to see the figures inline in each card.

## Comparison (v0.7)

```bash
./hub compare A B               # prints markdown to stdout
./hub compare A B --out FILE    # writes to file
```

Side-by-side comparison of two models. Shows:
- **Spec differences** (the "cause"): which preprocessing / architecture / training fields differ.
- **Metric differences** (the "effect"): R²/MMD deltas per matched eval_id, with sign (`+` / `−`) showing whether B beat A.
- **Identical fields**: collapsed at the bottom so the deltas are the focus.

Example: `./hub compare hvg_pearson_residuals_m2_ood/impact_cellot hvg_seurat_v3_m2_ood/impact_cellot` immediately surfaces "only hvg_method differs; pearson is better in data_space (R² 0.93 vs 0.90) but seurat_v3 is better in latent_space (0.78 vs 0.71)".

## Export to CSV/MD

```bash
./hub export csv                # writes experiments_inventory.csv at workspace root
./hub export md                 # writes experiments_inventory.md at workspace root
./hub export csv --out FILE     # custom path
```

Replaces the old `scripts/build_experiments_inventory.py` workflow. The exports include every ModelRecord field plus a one-line per-eval summary.

## What's still planned

- **Spec system / cookbook (v1)**: `hub spec from <run_id>` to clone an existing model's spec, then `hub generate <spec>` to write configs + sbatches, then `hub submit <spec>` to launch with proper afterok deps. This is the m2 → m1 workflow.
- **Figure pack (v1.5)**: regenerate diagnostic UMAPs and biomarker scatters from scratch for newly-trained models, so v1-generated experiments get figures alongside their evals.

---

## Notes on quirks you might see

- Some legacy models show `status=never_started` because they have a `config.yaml` but no `cache/status` file. This is the hub correctly saying "I can't verify this finished" rather than misclassifying. The model checkpoints may still exist at `<model_dir>/cache/model.pt` — `hub show` will show whether evaluations succeeded.
- `lr` is rendered in scientific notation for very small magnitudes (e.g. `1.00e-04`) to avoid losing precision.
- The `R²` and `MMD` columns in `hub list` show the data-space metric if available, else latent-space, else "—". Use `hub show <run_id>` to see all evaluations.

---

## When things go wrong

- **Import errors on yaml or pandas**: you're probably not in the `CellOT` conda env. The `./hub` wrapper should activate it automatically; if it doesn't, run `conda activate CellOT` manually.
- **No models found**: check that `cellot/cellot_gpu/results/` exists and contains experiment subdirs with `config.yaml` files.
- **Wrong family for an unknown subdir**: alias resolution is in `speciesOT/hub/resolve.py`; the `_ALIAS_TO_FAMILY` dict + `_CELLOT_PHASE_OVERRIDES` dict are the source of truth. New aliases get added there.

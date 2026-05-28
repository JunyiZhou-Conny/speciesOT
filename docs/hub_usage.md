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

## What v0 does NOT do (yet)

- **Markdown model cards** (planned v0.1): a `hub card <run_id>` command that writes a self-contained `.md` file you can open in Cursor's preview pane, with images inlined.
- **Diagnostic figure attachment** (planned v0.5): a convention that `<model_dir>/figures/*.png` are auto-attached to the model card, plus a one-time matcher that links existing figures from `baseline/analysis/*_outputs/` into their model dirs.
- **Comparison** (planned v0.7): `hub compare <run_id_a> <run_id_b>` showing side-by-side spec deltas and metric deltas.
- **Spec system / cookbook** (planned v1): `hub spec from <run_id>` to clone an existing model's spec, then `hub generate <spec>` to write configs + sbatches, then `hub submit <spec>` to launch with proper afterok deps.
- **Export to CSV/MD** (small follow-up to v0): `hub export csv -o experiments_inventory.csv` would replace the existing inventory script.

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

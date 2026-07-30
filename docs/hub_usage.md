# Using the hub (v0)

A model-card catalog for every CellOT/IMPACT_CellOT/scGen run in this project. v0 is **read-only** — it discovers what's already on disk, parses it, and presents it in a queryable form.

Design doc: [`hub_design.md`](hub_design.md).
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

It catalogs every directory that contains a `config.yaml` (180+ models across four families; run `./hub list | tail -1` for the live count).

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
./hub card --all                # writes one card per model + an INDEX.md grouped by family
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

## Spec system (v1) — the cookbook

The hub can clone an existing model's setup, modify a few fields, and emit all the configs + sbatches needed to train + evaluate a new experiment cell.

### The m2 → m1 workflow (worked example)

```bash
# 1. Dump the existing m2 setup as a YAML spec
./hub spec dump hvg_pearson_residuals_m2_ood/impact_cellot --out specs/m2_baseline.yaml

# 2. Copy + edit for m1: change experiment_tag, data_file, holdout_cell_types
cp specs/m2_baseline.yaml specs/m1_modern.yaml
# (manually edit: experiment_tag=hvg_pearson_residuals_m1_ood,
#                 data_file=...hvg_pearson_residuals_m1_v07.h5ad,
#                 holdout_cell_types=[CL:0000875])

# 3. Dry-run preview before writing anything
./hub generate specs/m1_modern.yaml --dry-run

# 4. Materialize — writes 8 files (2 configs + 4 train/eval sbatches + 2 data-space eval sbatches)
#    plus the model-scgen symlink. Prints the recommended sbatch chain.
./hub generate specs/m1_modern.yaml

# 5. Copy-paste the emitted sbatch chain to submit (with afterok deps automatically wired).
#    The hub doesn't run sbatch itself — that's left manual on purpose.
```

### Spec file structure

```yaml
experiment_tag: hvg_pearson_residuals_m1_v08_ood
derived_from: gpu/hvg_pearson_residuals_m2_ood/impact_cellot  # lineage; informational
data_source: speciesot-human-mouse-hvg
data_file: datasets/speciesot-human-mouse-hvg/hvg_pearson_residuals_m1_v08.h5ad
assay_filter:                       # ENFORCED by ./hub prep (single platform/species)
  mouse: [chromium_v2]              # = 10x 3' v2 (drops Smart-seq2 etc.)
  human: [chromium_v3]              # = 10x 3' v3
hvg_method: pearson_residuals
hvg_input_layer: layers['counts']
log1p_applied: true                 # .X is always log-normalized (01.5 contract)
hvg_batch_key: species
condition_column: condition
source: mouse
target: human
holdout_cell_types: [CL:0000875]
datasplit_strategy: toggle_ood
mode: ood
datasplit_stratify: condition       # balance the OOD split by species (else it drifts)
scgen_hidden_units: [256, 256]
scgen_latent_dim: 50
scgen_lr: 0.001
impact_train_device: gpu            # "gpu" (V100-pinned) or "cpu"
# ... (full list in speciesOT/hub/spec.py:ExperimentSpec)
```

All fields except `experiment_tag` and `data_file` have defaults matching the existing matrix conventions. Override only what's different. Note the two treatments differ in their defaults: **`assay_filter` defaults to the values shown** (mouse `chromium_v2` / human `chromium_v3`), so even a minimal spec gets single-platform filtering; **`datasplit_stratify` defaults to `null`** (the original unstratified split, kept for backward-compatibility with the existing matrix) — set it to `condition` to balance the OOD split by species.

### What `./hub generate` writes

For a spec with tag `<tag>`:

| Path | Purpose |
|---|---|
| `cellot/cellot_gpu/results/<tag>/scgen/config.yaml` | scGen training config |
| `cellot/cellot_gpu/results/<tag>/impact_cellot/config.yaml` | IMPACT_CellOT training config |
| `cellot/cellot_gpu/results/<tag>/model-scgen` (symlink → `scgen`) | The contract that lets IMPACT_CellOT find its AE sibling |
| `sbatch/train/train_<tag>_scgen.sbatch` | scGen training job |
| `sbatch/train/train_<tag>_impact_cellot.sbatch` | IMPACT_CellOT training (requires scGen done first) |
| `sbatch/eval/eval_<tag>_scgen.sbatch` | scGen latent-space eval (with `--embedding ae`) |
| `sbatch/eval/eval_<tag>_impact_cellot.sbatch` | IMPACT_CellOT latent-space eval (no `--embedding ae` per §5.5) |
| `sbatch/eval_dataspace/eval_<tag>_scgen_dataspace.sbatch` | scGen data-space eval |
| `sbatch/eval_dataspace/eval_<tag>_impact_cellot_dataspace.sbatch` | IMPACT_CellOT data-space eval — **always passes `--embedding ae`** to avoid the latent-space silent bug |

Existing files are skipped by default. Pass `--force` to overwrite.

### Why the hub doesn't auto-submit

The hub deliberately stops at file-writing. Actually running `sbatch` is left manual. The `generate` command prints the recommended chain so you can copy-paste, but you decide when to launch.

## Data preparation (v2) — `./hub prep`

`./hub prep <spec.yaml>` materializes the training `.h5ad` named by the spec's `data_file`, using the same spec the v1 generator consumes. It is a faithful port of `speciesOT/baseline/analysis/01.5_data_prep_all_holdouts_hvg_flavors.ipynb` (§1–§7), so you no longer have to open the notebook, edit the `GROUPS` dict, and run-all.

```bash
./hub prep specs/m1_modern.yaml             # build the .h5ad named in the spec
./hub prep specs/m1_modern.yaml --force     # overwrite if it already exists
./hub prep specs/m1_modern.yaml --keep-intermediate   # keep the pre-round-trip temp file
```

### What it does, step by step

Reading the spec's preprocessing-intent fields (`source_datasets`, `assay_filter`, `ortholog_source`, `hvg_method`, `hvg_n_top`, `hvg_batch_key`, `holdout_cell_types`, `random_state`, `data_file`):

1. Loads `source_datasets.{mouse,human}` and **promotes `.raw` to `.X`** to recover integer UMI counts.
2. **Enforces the assay filter** (`assay_filter`, added 2026-06-05): keeps only the allowed sequencing platform per species — default mouse `10x 3' v2`, human `10x 3' v3` — and drops everything else, **critically Smart-seq2**. The atlas sources mix platforms, and the Smart-seq2 minority has a very different expression distribution that otherwise shows up as OOD "scatter" and inflates MMD (see `docs/conceptual_framework.md` §5.10 and notebook 21). This is an **enforced treatment**, not optional metadata; an empty `assay_filter` skips it with a loud warning. Tokens accept the `chromium_v{2,3}` aliases, the literal `10x 3' v{2,3}` strings, or the EFO ids (`EFO:0009899` / `EFO:0009922`). Implemented in `speciesOT/hub/prep.py:_apply_assay_filter`.
3. **Ortholog-aligns** mouse↔human onto a shared one-to-one axis. Uses the cached BioMart table at `scripts/.biomart_ortholog_cache.csv` if present (the slow path queries Ensembl live and writes the cache for next time).
4. **Matches cells by `(cell_type_ontology_term_id, tissue_ontology_term_id)`** with the spec's `random_state`. With the assay filter on, the atlas yields ~8,054 paired cells (4,027 per species); the pre-filter v07 cut was ~12,990 (6,495 per species).
5. Snapshots raw counts to `.layers['counts']`, then sets `.X = log1p(normalize_total(counts, 1e4))`.
6. Selects the top `hvg_n_top` HVG with `hvg_method` on the **train-eligible (non-holdout) cells**, dispatching the input layer per flavor (raw counts for `seurat_v3`/`seurat_v3_paper`/`pearson_residuals`/`mixhvg`/`mixhvg_default`, log-norm `.X` for `seurat`/`cell_ranger`).
7. Subsets to those HVG (**keeping** the holdout cells — `toggle_ood` splits them at train time), strips everything but `.X`/`.obs`, writes the file, and round-trips it through the CellOT env's anndata 0.7 for downstream compatibility.
8. Reads the result back and prints a verification panel (shape, `.X` range, obs columns, `condition` balance).

### Two conda envs

The prep needs `scanpy >= 1.12` (Pearson residuals, `seurat_v3_paper`), which lives in the **`analysis`** env — not the `CellOT` env the rest of the hub runs in. So `./hub prep` shells out: the CLI (CellOT env) invokes `python -m speciesOT.hub.prep` under the analysis interpreter, which in turn shells back to the CellOT interpreter for the final anndata-0.7 round-trip. Both interpreters are auto-detected; override them with `SPECIESOT_ANALYSIS_PY` and `SPECIESOT_CELLOT_PY` if your paths differ. You can also run it directly:

```bash
conda activate analysis
python -m speciesOT.hub.prep specs/m1_modern.yaml
```

### Notes

- **Refuses to overwrite** an existing `.h5ad` unless `--force` is passed (big files = big mistakes).
- **Fails loudly** if the `source_datasets` files are missing — they live in Josh's `data/` tree, not this repo.
- **Assay filter is enforced** (`assay_filter`): only the listed platform(s) per species survive (default mouse `10x 3' v2` / human `10x 3' v3`); Smart-seq2 and other platforms are dropped *before* ortholog matching and HVG. This was previously recorded-but-never-applied; it is now applied in prep, so any dataset built by `./hub prep` is single-platform per species. If the filter would remove all cells (e.g. a typo'd token), prep aborts with the source's actual assay values listed. See `conceptual_framework.md` §5.10.
- `.X` is **always** log-normalized regardless of `hvg_method`; this is the fixed 01.5 contract that scGen/IMPACT depend on. A spec that sets `log1p_applied: false` contradicts that contract — prep warns and log-normalizes anyway so the output matches what 01.5 would have produced.

### Ensemble HVG: `hvg_method: mixhvg`

Two extra flavors select genes by **combining several single-flavor scores** instead of trusting one, following Zhao et al. 2024 ([doi:10.1101/2024.08.25.608519](https://doi.org/10.1101/2024.08.25.608519)):

| flavor | member methods |
|---|---|
| `mixhvg` | `scran`, `seuratv1`, `mv_PFlogPF`, `scran_pos` (the paper's recommendation) |
| `mixhvg_default` | `scran`, `scran_pos`, `seuratv1` (the R package default) |

Each member scores every gene; scores become ascending ranks; each gene keeps the **best rank any member gave it**. It is a union, not an average — a gene one method loves and three hate is still selected.

Requires the `mixhvg` package in the **analysis** env — a Python port of the R original, kept in a **separate repository** and deliberately not vendored here. The port is GPL-3 (a translation is a derivative work, and its `scran` reimplementations independently set that floor), so vendoring it would make this repo GPL-3 too. Install it from wherever you have it checked out:

```bash
conda activate analysis
pip install -e /path/to/mixhvg-py
```

Read that package's `docs/fidelity.md` before quoting results. Measured against R (scran 1.30.0, Seurat 5.3.0): the Seurat-derived members reproduce R exactly, `scran`/`scran_pos`/`mv_PFlogPF` agree at Spearman 0.965–0.9998, and the recommended mixture matches R at Jaccard 0.98. The `mv_ct` and `mv_nc` members do **not** match and are excluded from both flavors. Cite the method as Zhao et al. 2024, [doi:10.1101/2024.08.25.608519](https://doi.org/10.1101/2024.08.25.608519).

**Batch handling is deliberately borrowed, not invented.** mixhvg has no notion of batches, but `hvg_batch_key` defaults to `species` on every existing run, so prep computes the ensemble independently within each batch and combines batches by scanpy's `seurat_v3` rule (keep a gene's rank only in batches where it made that batch's top-`n_top`, then take the nanmedian, then break ties by batch count). Without this the comparison would confound "ensemble vs single flavor" with "batch-aware vs batch-blind". On a synthetic two-species check this recovers 19/20 planted species-specific genes, matching `pearson_residuals`; a naive median over full ranks recovers only 7/20 because it averages a good rank against a bad one and throws away single-species genes.

### The full one-command experiment flow

```bash
# Edit a spec to taste, then:
./hub prep specs/m1_modern.yaml       # v2 — build the dataset
./hub generate specs/m1_modern.yaml   # v1 — write configs + sbatches
# copy-paste the printed sbatch chain to submit
# wait for training + evals
./hub list / show / compare           # inspect results
```

### Cross-species LPS frozen-AE ICNN study

The controlled `G2000_scgen` transport-swap study has a dedicated hub route:

```bash
./hub lps icnn-generate --round 1
# review and copy-paste the printed seven-job Slurm array command
# after all jobs finish:
./hub lps icnn-summarize --round 1
```

Round 1 uses the seven frozen rungs declared in
`specs/lps_icnn_ae_study.yaml` and writes
`scgen-cellot-autoresearch/ae_study/results/ot_ladder_g2000_scgen.csv`.
The generated jobs train only CellOT's ICNN map; AE/PCA/linear projectors stay
frozen. The pending CSV includes existing mean-shift metrics for comparison.
As elsewhere, `generate` validates and prints but never calls `sbatch`.

The separate TensorFlow paper anchor is inspected with:

```bash
./hub lps scgen-paper-generate
```

It prints one evaluation sbatch for the already-trained 6,619-gene Fig. 5
checkpoint and does not merge that result into the G=2000 OT ladder.

The no-retraining identity audit is generated separately:

```bash
./hub lps scgen-paper-audit-generate
# review and copy-paste the printed CPU sbatch
```

That job first preserves the pre-audit `metrics.json`, rechecks the frozen
all-gene Figure-5 gate, adds the paper's top-100 Wilcoxon-DEG R², then compares
train, seen rat-unstimulated, and held-out rat-LPS6 encode→decode behavior
against shuffled, gene-mean, zero, and exact-identity baselines. It writes
small JSON/CSV/NPZ sidecars and exportable figures under
`scgen-cellot-ablation/results/stage0/`; it does not retrain the VAE and does
not start unbalanced OT.

The bounded AE follow-up is a separate gated study:

```bash
./hub lps scgen-ae-followup-generate --round 1
# review and submit the printed four-task CPU array
# after all tasks complete:
./hub lps scgen-ae-followup-summarize --round 1
```

Round 1 is the preregistered `VAE/DAE × dropout 0.2/0.0` comparison at fixed
`z=100`, architecture, optimizer, epoch budget, data, split and seed. Each task
writes Figure-5 all-gene/top-100-DEG metrics plus the required five-axis AE
identity sidecars. Rounds 2–3 are not generated until the prior round's
decision JSON passes identity and transport non-inferiority gates declared in
`specs/lps_scgen_ae_followup.yaml`. The hub only prints submission commands.

## What's still planned

- **Figure pack (v1.5)**: regenerate diagnostic UMAPs and biomarker scatters from scratch for newly-trained models, so v1-generated experiments get figures alongside their evals.
- **`hub spec from --set field=value`**: in-place spec creation without needing to manually edit YAML.
- **Multi-cell spec batches**: generate an entire matrix dimension (e.g. all 4 m1–m4 monocyte cells × 2 modes) from one parent spec + a sweep field.

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

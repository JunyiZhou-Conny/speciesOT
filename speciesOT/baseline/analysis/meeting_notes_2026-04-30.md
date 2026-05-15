# Meeting note — 2026-04-30

## What we covered today

Read the April 20 research log, mapped the new task list against the existing notebook ecosystem, and produced concrete artifacts despite cloud-data being unavailable from my laptop.

## Research log recap (April 20)

The log is a postmortem of a preprocessing scale bug: human `.X` was `normalize_total + log1p`, mouse `.X` was log1p-then-per-gene-scaled-and-clipped-at-10. That contaminated HVGs, PCA/UMAP, OT/scGen training, and OOD evaluation. The fix was rebuilding from `.raw` counts and applying identical normalization (`01.3_data_prep_all_holdouts_renorm.ipynb`). `08.1` compared stale vs renorm and found renorm wins broadly, with one exception: Group C (T-cell subtypes) where renorm underperformed for CellOT and MMD.

## Updated task list and priority

| # | Task | Priority | Why this order |
|---|---|---|---|
| 5 | HVG on training set only | Foundational | OOD leakage; everything else is contaminated until this is fixed |
| 1 | Try Seurat v3 (and other flavors) | High | Fixes the marker-absence problem |
| 7 | Switch focal task to immune cells | High | Mentor priority; CD4/CD8 saturated |
| 2 | CD4 → CD8 model design | Medium | Closer to deployment narrative; needs data |
| 4 | Feature importance | Low | Post-result analysis |
| 3 | Figure G replication | Was lowest, but: feasible **today** | We have the data |
| 6 | External dataset | Lowest | Confounds with everything |

## Major finding from today's work

**0 of 16 standard immune markers (PTPRC/CD45, CD3D/E/G, CD4, CD8A/B, CD5, CD7, CCR7, TBX21, GATA3, NCAM1, GZMB, PRF1, IFNG) are in the top-1000 HVG list of the existing CD8 holdout dataset.**

This makes Task 5 (training-only HVG) and Task 1 (try seurat_v3 / pearson_residuals) urgent rather than nice-to-have: the model trained on this data has no marker-interpretable axis at all. This is a much stronger version of the PTPRC-missing observation in `01.1`. Source: `baseline/analysis/figure_g_outputs/` (the 16-panel figure had to fall back to data-driven gene selection because the curated panel was empty).

## Concrete artifacts produced today

All under `baseline/analysis/`.

| File | Status | Purpose |
|---|---|---|
| `01.4_hvg_flavor_comparison.ipynb` | Cloud-runnable | Compares `seurat`, `seurat_v3`, `seurat_v3_paper`, `pearson_residuals` HVG flavors on the renorm pipeline; runs HVG on training cells only (Task 5 fix); reports rank of immune marker panel; saves per-flavor lists for `01.3` to consume |
| `11_immune_cell_ontology.ipynb` | Locally executed | Defines the 11 shared immune types with CL IDs; builds a 4-level lineage tree (HSPC → lymphoid/myeloid → effectors/progenitors → terminal types); pre-builds A/B/C/D OOD group templates for 5 candidate focal types (NK cell looks cleanest by tree structure) |
| `12_figure_g_replication.ipynb` | Locally executed | Replicates Bunne et al. 2023 Fig. 3g per-gene KDE plot using local CD8 holdout evals (CellOT + IMPACT + treated + source) |
| `immune_ontology_outputs/immune_lineage_tree.pdf` | Output | Publication-quality lineage figure |
| `immune_ontology_outputs/immune_ood_templates.json` | Output | Pre-built A/B/C/D groups for dendritic cell, NK cell, macrophage, plasma cell, neutrophil |
| `figure_g_outputs/figure_g_cd8_holdout.pdf` | Output | The 4-color KDE figure on local CD8 evals |

## Method note: figure G, where it lives, what we changed

- **Original code**: `CellOT/cellot/cellot/utils/viz.py:plot_marginals` — `seaborn.kdeplot(common_norm=False)` per gene with 1st–99th percentile clipping, palette `cellot=#F2545B, treated=#114083, control=#A7BED3, scgen=#C3BABA, cae=#9A8F97`.
- **Our adaptation**: substituted IMPACT-OR (orange) for scGen because we don't have local scGen evals (only the trained `model.pt`); kept the published palette for treated/cellot/source.
- **What this requires when scGen evals exist**: just run `scripts/evaluate.py --outdir results/speciesot_cd8/speciesot_scgen --setting ood --where data_space` on cloud and re-execute notebook 12.

## Open questions for the meeting

1. **HVG flavor decision rule**: should the criterion be marker recovery (how many of `{PTPRC, CD3, CD4, CD8, CCR7, GATA3}` land in top-1000), or breadth-of-detection (median fraction-cells-detected among top-1000), or a hybrid? This determines which flavor the cloud rerun picks.
2. **Immune focal type**: NK cell is cleanest by tree structure (T cell + B cell as siblings, macrophage as distant control). Dendritic cell and macrophage have a degenerate Group B vs C (each other's only sibling). Shall we lock NK cell, or wait for the data audit (`11.1`) before committing?
3. **CD4 → CD8 setup**: pure cross-species (mouse-only training, human OOD) vs mixed-species (human CD4 included as source). I recommend running both arms; the delta quantifies how much human source-side info the model needs. Confirm OK?
4. **Group C (T-cell subtypes) renorm regression**: do you want me to dig into why renorm underperformed stale here, or defer until after the 01.4 flavor decision is in?

## What's blocked on cloud, ready to go when access returns

1. Run `01.4` on the real renormalized data → pick a flavor.
2. Update `01.3` (or fork to `01.5`) to apply the chosen flavor and move HVG inside the per-group holdout split.
3. Regenerate the four group holdout files; re-run CellOT, IMPACT, scGen.
4. Build `08.2` (renorm-with-leakage vs renorm-training-only): quantifies how much accuracy was leakage.
5. Run `11.1` (cell counts per `(species, tissue, cell_type)`) to lock the immune focal type.
6. Generate scGen evals for `12_figure_g_replication.ipynb` so the figure has the full 4-model panel.

## Time honesty

Cloud was down for the full session. Everything above was produced locally with the data that came down via git-lfs (the `cd8_holdout_v07.h5ad` and the `imputed.h5ad` files for both CellOT and IMPACT-OR).

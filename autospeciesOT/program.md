# autospeciesOT

This is an experiment to have an LLM agent autonomously iterate on cross-species
cell transport models (CellOT / IMPACT) and their data preprocessing.

## Background

We are building models that transport gene expression across species. The
downstream goal is: given a mouse cell that has been perturbed by a drug,
predict what the corresponding human cell would look like. Currently we are
modeling the species effect and cell-type effect (no drug perturbation yet).

The pipeline has two stages:
1. **scGen** — a variational autoencoder that learns a shared latent space
   for human and mouse cells. All cells are embedded through this encoder.
2. **CellOT / IMPACT** — an optimal transport model that learns to map
   source → target in the scGen latent space. CellOT and IMPACT use the
   exact same model architecture; the only difference is the condition variable:
   - **IMPACT**: condition = species (mouse/human). Task: mouse CD8 → human CD8.
   - **CellOT**: condition = cell_type_status (cd8/non_cd8). Task: human nonCD8 → human CD8.

The evaluation metric is computed on held-out cells that neither scGen nor
CellOT/IMPACT saw during training (strict OOD).

## What you are optimizing

**Two metrics, both must improve:**
- **r2_means** — R² between predicted and actual mean gene expression per gene. Higher is better. 1.0 = perfect.
- **mmd** — Maximum Mean Discrepancy between predicted and actual distributions. Lower is better. 0.0 = perfect.

**Keep/discard rule:** An experiment is a "keep" if r2_means improves AND mmd
improves (or stays within 10% of best). If only one improves and the other
degrades significantly, it is a "discard" unless the net improvement is clearly
worth the tradeoff. When in doubt, prefer the experiment with lower mmd.

## Constraints

**DO NOT change:**
- Gene alignment method (biomart one-to-one orthologs — already implemented)
- Number of HVGs (fixed at 1000)
- CellOT/IMPACT model architecture (hidden_units=[64,64,64,64], latent_dim=50)
- scGen architecture (hidden_units=[256,256], latent_dim=50, dropout=0.1)
- Optimizer settings (must match original CellOT paper for fair comparison)
- Species pairing (mouse → human)

**What you CAN change (the search space):**
- Which cell type(s) to hold out for OOD evaluation
- Which related cell types to also exclude from training (e.g., thymocytes)
- Model framing: IMPACT (condition=species) vs CellOT (condition=cell_type_status)
- Number of training iterations for scGen and CellOT (to find the sweet spot)

## Cell type reference

The matched dataset contains ~12,836 cells across 30 cell types. The T cell
family is the primary focus:

```
CL:0000084  T cell                              102 mouse, 102 human (204 total)
CL:0000893  thymocyte                           455 mouse, 455 human (910 total)
CL:0000624  CD4-positive, alpha-beta T cell      95 mouse,  95 human (190 total)
CL:0000625  CD8-positive, alpha-beta T cell     195 mouse, 195 human (390 total)
```

Key biology: thymocytes are precursors to both CD4+ and CD8+ T cells. A cell
labeled "thymocyte" may differentiate into either. In our data, holding out
CD8+ without also excluding thymocytes risks data leakage (thymocytes that
are effectively pre-CD8 remain in training).

Other cell types of interest for holdout experiments:
- Monocyte subtypes: conventional, unconventional, intermediate
- Macrophage subtypes: M1 (inflammatory), M2 (regenerative)

## Setup

To set up a new experiment run, work with the user to:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `mar30`).
2. **Read the in-scope files**: This document, `run_experiment.py`, and the
   current `results.tsv`.
3. **Verify the CellOT environment**: the CellOT conda env must be active and
   the cellot package importable. The cellot codebase lives at:
   `../cellot/cellot_gpu/`
4. **Verify data exists**: the full atlas h5ad files should be at:
   `../cellot/cellot_gpu/datasets/speciesot-human-mouse/`
5. **Initialize results.tsv** if it doesn't exist (header row only).
6. **Confirm and go**: confirm setup looks good, then start the experiment loop.

## Running an experiment

Each experiment is a full pipeline run:

```bash
python run_experiment.py \
    --tag <experiment_tag> \
    --holdout "CL:0000625" \
    --also-exclude "CL:0000893" \
    --model-framing impact \
    --scgen-iters 50000 \
    --cellot-iters 50000
```

The script does:
1. Prepare datasets — load full atlas, exclude holdout + also-excluded cell types,
   save scGen training h5ad and CellOT training h5ad
2. Train scGen on the prepared dataset (skip if a matching scGen checkpoint exists)
3. Train CellOT/IMPACT using frozen scGen encoder
4. Evaluate on held-out cells in data space
5. Print summary metrics

The output looks like:
```
---
r2_means:     0.717761
r2_stds:      0.322732
mmd:          0.052424
peak_mem_mb:  2048.0
train_seconds: 2580.0
holdout:      CL:0000625
also_excluded: CL:0000893
model_framing: impact
```

You extract the key metrics with: `grep "^r2_means:\|^mmd:" run.log`

## Logging results

When an experiment is done, log it to `results.tsv` (tab-separated).

The TSV has a header row and these columns:

```
tag	r2_means	mmd	status	holdout	also_excluded	model_framing	scgen_iters	cellot_iters	description
```

- **tag**: short identifier for this experiment
- **r2_means**: R² of mean gene expression (6 decimal places). Use 0.000000 for crashes.
- **mmd**: maximum mean discrepancy. Use 0.000000 for crashes.
- **status**: `keep`, `discard`, or `crash`
- **holdout**: ontology term ID(s) of held-out cell type
- **also_excluded**: additional excluded cell types (or "none")
- **model_framing**: `impact` or `cellot`
- **scgen_iters**: number of scGen training iterations
- **cellot_iters**: number of CellOT training iterations
- **description**: short text of what this experiment tried

Example:
```
tag	r2_means	mmd	status	holdout	also_excluded	model_framing	scgen_iters	cellot_iters	description
baseline_cd8	0.717761	0.052424	keep	CL:0000625	none	impact	50000	50000	baseline: CD8 holdout IMPACT framing
cd8_no_thymo	0.750000	0.045000	keep	CL:0000625	CL:0000893	impact	50000	50000	exclude thymocytes from training
cd4_holdout	0.680000	0.060000	discard	CL:0000624	none	impact	50000	50000	hold out CD4 instead of CD8
```

## The experiment loop

LOOP FOREVER:

1. Read `results.tsv` to see what has been tried and what the current best is.
2. Decide what to try next based on the planned experiment list and results so far.
3. Run the experiment: `python run_experiment.py [args] > run.log 2>&1`
   (redirect everything — do NOT flood your context with training output)
4. Read out the results: `grep "^r2_means:\|^mmd:" run.log`
5. If grep output is empty, the run crashed. Read `tail -n 50 run.log` for the
   stack trace. Attempt a fix if it's simple. If not, log as "crash" and move on.
6. Record results in results.tsv.
7. Determine keep/discard based on the rule above.
8. Move on to the next experiment.

**Experiment priority order** (do these first):

1. **Baseline CD8 holdout, IMPACT framing** — reproduce current best result
2. **Baseline CD8 holdout, CellOT framing** — compare framings
3. **CD8 + thymocyte exclusion, IMPACT framing** — cleaner holdout
4. **CD8 + thymocyte exclusion, CellOT framing** — compare framings
5. **CD4+CD8+thymocyte exclusion, IMPACT framing** — hold out all T cell subtypes,
   model only sees generic "T cell" labeled cells
6. **CD4+CD8+thymocyte exclusion, CellOT framing** — compare framings
7. **CD4 holdout, IMPACT framing** — different cell type
8. **Monocyte/macrophage holdout experiments** — different cell lineage entirely

For each holdout configuration, run IMPACT first (it's the primary model of
interest), then CellOT to compare.

**Timeout**: scGen trains in ~37 min (50K iters), CellOT in ~43 min (50K iters).
A full experiment with scGen retrain should complete in ~90 min. If it exceeds
120 min, kill it and treat as a failure.

**Crashes**: If a run crashes due to a bug, use judgment. Fix obvious issues
(typo, missing import, path error) and re-run. If the data configuration is
fundamentally broken (not enough cells, mismatched genes), log as crash and
move on.

**scGen caching**: If the holdout configuration hasn't changed from the previous
experiment, the scGen checkpoint can be reused. Only retrain scGen when the set
of excluded cell types changes. The script handles this via the `--tag` system.

**NEVER STOP**: Once the experiment loop has begun, do NOT pause to ask the
human if you should continue. The human may be asleep. You are autonomous.
If you finish the priority list, revisit experiments that were close to
improving and try variations. The loop runs until manually interrupted.

# Conceptual framework — what the speciesOT project is doing

A living reference doc. Written 2026-05-25 as part of a repo walkthrough; based on a conversation with Junyi about how the three model variants relate, why the naming changed, and where the project is going. Edit freely as understanding deepens.

---

## TL;DR

- **One model architecture**: CellOT (Bunne et al., 2023), an optimal-transport map parameterized by Input Convex Neural Networks (ICNNs).
- **Three things we've used it for**, distinguished only by **what plays the role of source vs. target distribution**:
  1. **CellOT (paper-original)** — source = control cells, target = drug-treated cells. Models a **drug perturbation effect**.
  2. **CellOT (cell-type framing)** — source = non-CD8 cells, target = CD8 cells. Models a **cell-type effect**. *Tried briefly, abandoned.*
  3. **IMPACT_CellOT (current)** — source = mouse cells, target = human cells. Models a **species effect**.
- **One baseline we compare against**: **scGen** (Lotfollahi et al.). A VAE with an additive perturbation vector. Simpler, often surprisingly competitive, but rests on a linear/additive assumption.
- **What our pipeline currently models**: only the **species effect** (IMPACT_CellOT). We have not yet done the **drug-effect** half of the eventual project. The BCG line (notebook `16_`* and onward) is the first toe in that water; nothing thorough yet.
- **The eventual goal**: given mouse untreated, mouse treated, and human untreated, predict human treated. This requires both a drug-effect transport and a species-effect transport, composed somehow.

---

## 1. The three model variants

All three use the same neural-network machinery (CellOT's ICNN-parameterized OT, or scGen's VAE + latent shift). They differ only in what the *condition* variable is — i.e. what defines the "two clouds" the model learns to transport between.

### 1.1 CellOT (paper-original) — drug effect


|                                     |                                                                                                                      |
| ----------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| **Source cloud**                    | Untreated cells                                                                                                      |
| **Target cloud**                    | Drug-treated cells                                                                                                   |
| **Condition**                       | Treatment status (control vs. drug X)                                                                                |
| **Cells in both clouds**            | Same cell line / type, just exposed to drug or not                                                                   |
| **OOD generalization tested along** | Unseen single cells (held-out cells of the same type)                                                                |
| **Reference**                       | [Bunne et al., 2023 — `reference_papers/Bunne et al - 2023.pdf](../reference_papers/Bunne%20et%20al%20-%202023.pdf)` |


This is what CellOT was published to do. The biological claim is: *given a control cell, what would it look like if exposed to drug X?* One CellOT model is trained per drug.

**We have never used CellOT in this paper-original framing**, because our datasets (human + mouse atlas, no chemical perturbation) don't contain drug-treated cells. The paper-original framing is included here only as the conceptual anchor — it's what the architecture was designed to model.

### 1.2 CellOT (cell-type framing) — abandoned


|                                     |                                                                    |
| ----------------------------------- | ------------------------------------------------------------------ |
| **Source cloud**                    | Non-CD8 cells (a large pool of many other cell types)              |
| **Target cloud**                    | CD8 T cells                                                        |
| **Condition**                       | Cell type (everything else vs. CD8)                                |
| **OOD generalization tested along** | A held-out **species** (train on mouse, test on human) — see below |


We tried this framing in early experiments. The on-disk fossil evidence lives at `cellot/cellot_gpu/results/toggle_*/cellot/`. Notably, the OOD test for these experiments held out *species*, not *cell type*: the model was trained to learn non-CD8 → CD8 on **mouse cells only** (where both clouds are available), then evaluated by transporting human non-CD8 cells and comparing to actual human CD8 cells. So two axes of generalization were being conflated:

1. The cell-type-transformation hypothesis (non-CD8 → CD8 is a learnable map at all).
2. The cross-species transferability hypothesis (a map learned on mouse cell types applies to human cell types).

In the corresponding YAML configs this showed up as `datasplit.key: species` and `datasplit.holdout: 'human'`, paired with `data.source: non_{label}` / `data.target: {label}`.

It was abandoned for two reasons:

1. **Huge size imbalance.** Non-CD8 vastly outnumbers CD8 in any atlas dataset. OT can still solve this mathematically, but with ICNN-based *deterministic* maps it forces a many-to-one squash from the large source cloud to the small target cloud, which is not a meaningful biological statement (it isn't saying "this monocyte becomes that CD8 cell" — that's not how cell identity works).
2. **No coherent biological question.** Treating "the other cell types" as if they were the "control" version of CD8 cells doesn't correspond to any real intervention. Cell types are not perturbations of each other. The conflation of the two generalization axes also made it hard to interpret what a positive result would mean.

**Status:** dead. Any code or notebook references to this framing (subdirs named `cellot/` next to `impact/` and `scgen/` under `cellot/cellot_gpu/results/toggle_*/`, configs with `datasplit.key: species`, paths containing `_holdout_swapped_v07.h5ad`) are stale.

### 1.3 IMPACT_CellOT — species effect (current main task)


|                                     |                                                                                                                              |
| ----------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| **Source cloud**                    | Mouse cells                                                                                                                  |
| **Target cloud**                    | Human cells                                                                                                                  |
| **Condition**                       | Species (mouse vs. human)                                                                                                    |
| **OOD generalization tested along** | Held-out cell type — train on most cell types, test on (e.g.) mouse CD8 → human CD8                                          |
| **What we're testing**              | Does the OT map learn a generalizable "mouse-to-human" transformation that works on cell types it never saw during training? |


This is essentially every numbered experiment from late April onward — the HVG-flavor matrix, IID vs. OOD evaluations, renorm vs. stale comparisons.

**Why the name has the `IMPACT_` prefix**: to signal explicitly that this is *not* CellOT's original drug-perturbation task. The architecture is identical to paper-original CellOT, but the biological claim is different, so the name needs to be different. (`IMPACT` here is a label, not a known acronym — TODO: confirm with mentor whether it stands for something.)

### 1.4 scGen — the baseline


|                                    |                                                                                                                                    |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **Architecture**                   | Variational autoencoder                                                                                                            |
| **How it predicts a perturbation** | Compute δ = mean(latent_target) − mean(latent_source) on training cells. For a new source cell, return `decode(encode(cell) + δ)`. |
| **Reference**                      | [Lotfollahi et al. — `reference_papers/scGen.pdf](../reference_papers/scGen.pdf)`                                                  |


scGen is older and simpler. It assumes the source-to-target effect is a **single fixed shift vector in latent space**, applied identically to every cell.

**The criticism your mentor raises**: scGen is fundamentally *linear and additive*. If the species effect (or drug effect) actually behaves differently for different cell types — and biologically it almost certainly does — scGen can't capture that. It will predict the same shift for monocytes and T cells, which is wrong.

**Why we still run it**: it's a fair baseline. If our nonlinear OT-based IMPACT_CellOT can't outperform scGen's simple additive shift, that's evidence the extra machinery isn't earning its keep on our data. Currently IMPACT_CellOT does beat scGen on most cells, but the gap varies by flavor and holdout.

---

## 2. Why the naming matters even though the architecture is identical

In code, `impact_cellot` and what would be `paper_cellot` (the original drug framing) would compile to the same ICNN training loop. So why bother distinguishing them by name?

1. **Different biological claim.** A "drug effect" is something a chemist intervenes on. A "species effect" is a billion years of evolution baked into the genome. They are not the same kind of thing, even when the math is the same.
2. **Different generalization axis.** Paper-original CellOT generalizes across *cells* within a fixed perturbation. IMPACT_CellOT generalizes across *cell types* within a fixed mouse→human direction. When we say "OOD" in a talk or a paper, the audience needs to know along which axis.
3. **Credit and clarity.** Saying "we used CellOT" leads readers to assume drug perturbation. Saying "we used IMPACT_CellOT" signals: "we adapted Bunne 2023's machinery to a species-transport task." That's the honest framing.

This is why the renaming workstream exists: any older variable named `cellot` (or dict key `"cellot"`, path component `cellot/`) that actually refers to the IMPACT (species) framing should become `impact_cellot`. The library directory itself (`cellot/cellot_gpu/cellot/`) and upstream config files keep their original names — only our *application-level* labels change.


| Use site                                                                 | Convention               | Examples                 |
| ------------------------------------------------------------------------ | ------------------------ | ------------------------ |
| Code identifiers (path components, dict keys, CLI flags, variable names) | lowercase + underscore   | `impact_cellot`, `scgen` |
| Display labels (figure legends, tables, prose)                           | preserved capitalization | `IMPACT_CellOT`, `scGen` |


### 2.1 Alias history — translation table for old names

The repo has accumulated several alias names for the same three model families across different project phases. This table maps **every alias** to the current canonical name. Source of truth: the `ALIAS_TABLE` in `scripts/build_experiments_inventory.py`.


| Canonical family                                                         | Aliases seen in old paths, configs, and filenames                                                    |
| ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------- |
| **scGen** (current name: `scgen`)                                        | `scgen`, `speciesot_scgen`, "autoencoder" (informal)                                                 |
| **IMPACT_CellOT** (current name: `impact_cellot`)                        | `impact`, `impact_or`, `swapped_cellot`, `speciesot_cellot`                                          |
| **CellOT (abandoned cell-type framing)**                                 | `cellot` (in `speciesot_v1_iter2_`* or `toggle` phases), `speciesot_cellot_swapped`, `normal_cellot` |
| **CellOT (legacy crossspecies)** — raw 1000-dim ortholog space, no scGen | `cellot` (only in `legacy_crossspecies` phase, top-level `cross_species_ood/` and `race_*/` dirs)    |


**Context-dependent disambiguation**: the directory or dict-key name `cellot` alone is ambiguous because it has meant three different things at different project phases. To resolve it, check:

- Phase = `legacy_crossspecies` (e.g. `cellot/cellot_gpu/results/cross_species_ood/`) → raw-HVG CellOT, no scGen sibling.
- Phase = `speciesot_v1_iter2_groupA` or `toggle` → abandoned cell-type framing (`datasplit.key: species`, `holdout: 'human'`, paths containing `_holdout_swapped_v07.h5ad`).
- Otherwise (current pipelines) → if next to an `impact_cellot/` sibling, the bare `cellot/` is the abandoned cell-type framing; if it's the only model subdir, check the config's `condition` field to disambiguate.

**Where you'll see these old aliases on disk today**:

- `speciesOT/baseline/results/speciesot_cd8/impact_or/evals_ood_data_space/imputed.h5ad` — `impact_or` = `IMPACT_CellOT`.
- `speciesOT/baseline/results/speciesot_cd8/cellot/evals_ood_data_space/imputed.h5ad` — bare `cellot` in this speciesot_v1 path = abandoned cell-type framing.
- `cellot/cellot_gpu/results/_archive/toggle_cellot_subdirs/toggle_*/cellot/` — already archived (batch 3); abandoned cell-type framing.
- `cellot/cellot_gpu/results/toggle_*/impact/` — `impact` = `IMPACT_CellOT`; queued for rename in a future batch.

---

## 3. The ultimate goal — and where we are today

### What we want eventually

A model that takes a **human untreated** cell and predicts a **human treated** cell, by leveraging the fact that we have observed the drug effect in *mouse* (where both untreated and treated cells are available).

Schematically:

```
                   T_drug (learnable on mouse)
   mouse_untreated ─────────────────────────► mouse_treated

   T_species ↓                                ↓ T_species
                                              
   human_untreated ─────────────────────────► human_treated
                   T_drug' (desired, unobserved directly)
```

We have three corners of this diagram observable in real datasets. We want to predict the fourth corner. There are at least three ways to attempt it:

- **(a) Assume the drug effect is species-invariant** — apply `T_drug` (learned on mouse) directly to a human cell. Strong but testable assumption.
- **(b) Compose the two transports** — `T_drug' ≈ T_species ∘ T_drug ∘ T_species^{-1}`. Requires invertibility (problematic for ICNN-OT maps as-published) and that composition is meaningful.
- **(c) Learn a joint conditional model** — train a single model conditioned on (species, treatment), with the unobserved corner imputed during training somehow.

None of these are implemented yet. The current matrix work (HVG flavor × holdout × IID/OOD) is laying the groundwork: making sure each species transport is reliable in isolation, before we try to compose anything.

### Where we actually are today

- **Species effect (IMPACT_CellOT)**: this is what the entire current pipeline measures. HVG-flavor matrix, IID/OOD evaluations, renorm vs. stale comparisons — all of it.
- **Drug effect**: not yet modeled. The first attempt is the **BCG line** (notebook `16_bcg_mouse_data_prep.ipynb`, `16.1_`*, `17_bcg_prediction.ipynb`). BCG is the tuberculosis vaccine, which has been administered to both mouse and human cohorts and has scRNA-seq data available — so it's a natural choice for a perturbation that exists in both species. So far the work in those notebooks is exploratory: data prep and initial inspection, no thorough modeling yet.
- **Composition of the two effects**: future work, downstream of the BCG line maturing.

---

## 4. Where each model lives in the pipeline output

When you look at `cellot/cellot_gpu/results/<experiment>/`, each experiment directory will typically contain subdirectories for the model variants that were run:

```
cellot/cellot_gpu/results/<experiment>/
├── impact_cellot/            ← the OT-based species transport
│   └── evals_ood_data_space/
│       ├── imputed.h5ad      ← predicted human cells (in data space)
│       └── evals.csv         ← R²-of-means, MMD, etc.
└── scgen/                    ← the VAE baseline
    └── evals_ood_data_space/
        ├── imputed.h5ad
        └── evals.csv
```

This is the layout assumed by `presentation_preparation.ipynb` and is the convention going forward. Older runs may use other labels — those are stale and being renamed.

---

## 5. Side notes worth remembering

### 5.1 Optimal transport doesn't require equal sample sizes

You can map a source cloud of n cells to a target cloud of m cells with n ≠ m. The math distributes mass according to the cost matrix (and, with entropy regularization à la Sinkhorn, the marginals). What gets weird at extreme imbalance is the **interpretation**: ICNN-CellOT learns a deterministic map T(x), so if n ≫ m many source cells get squashed onto the same target cells. The math is fine; the biology rarely is.

### 5.2 `r2-means` vs `r²`

The column `r2-means` in `evals.csv` is the **Pearson correlation r of mean expression vectors**, not r². To report R² you must square it. This was an easy point of confusion early on and is the reason `presentation_preparation.ipynb` squares the value before plotting.

### 5.3 "Renorm" vs. "stale" data preprocessing

- **Stale**: input cells were normalized on different scales between species (legacy preprocessing).
- **Renorm**: we re-normalized starting from raw single-cell RNA molecule counts, then ran HVG selection with `batch_key='species'` (which performs the normalization separately per species).

See `08.1_renorm_vs_stale_comparison.ipynb` for the head-to-head. The current pipeline uses the **renorm** preparation.

### 5.4 `mode` (training) vs `--setting` (evaluation) — the OOD-word overload

The word "OOD" is used in two different places in the pipeline and they mean different things:


| Term                             | Lives in                                                                               | Refers to                                                                                                                                                                                         |
| -------------------------------- | -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `**mode`** (`iid` or `ood`)      | `generate_*_configs.py`, sbatch tags, results directory names like `hvg_seurat_d_iid/` | **What data was used to train** the model. `ood`: the held-out cell type was completely excluded from training. `iid`: the "ignored" half of the held-out cell type was added back into training. |
| `**--setting`** (`iid` or `ood`) | `evaluate.py` CLI flag                                                                 | **Which slice of the dataset to evaluate on**. `iid`: the standard test split (random cells from in-training cell types). `ood`: the held-out cell type, test half.                               |


**In current practice, we always evaluate with `--setting ood`** — that is, we always measure performance on the held-out cell type, regardless of training mode. This means:

- IID-trained + `--setting ood` evaluation: the model has seen similar cells (the "ignored" half of the holdout) during training, so this is closer to in-sample fit. Useful as an upper bound.
- OOD-trained + `--setting ood` evaluation: the model has never seen any cells of the held-out type. This is true generalization.

The difference between the two is roughly **the generalization gap**.

This overload is confusing on first read (an "IID-mode" sbatch that calls `--setting ood` looks like a bug; it isn't). The cookbook should normalize the vocabulary so users describe what they want without having to remember the overload — e.g. `train_includes_holdout: bool` and `eval_on: held_out_celltype | in_training_celltype`.

### 5.5 The `--embedding ae` flag is mis-coupled to `--where data_space` (real-correctness bug)

 This is a subtle but consequential evaluation bug, discovered during the 2026-05-27 walkthrough. Captured here so neither future-Junyi nor a future agent has to re-derive it.

#### What `evaluate.py --where data_space` is supposed to mean

The output dimensionality of an evaluation: `data_space` ⇒ compare predictions to ground truth in 1000-dim gene-expression space; `latent_space` ⇒ compare in 50-dim AE-latent space. The output directory inherits the flag name (`evals_ood_data_space/`, `evals_ood_latent_space/`).

#### What it actually does for IMPACT_CellOT (the bug)

Without `--embedding ae`, the call to `load_projectors(aedir, embedding=None, where=...)` returns **identity** functions for both `encode` and `decode` (`evaluate.py` lines 100–108). So:

- The data loader sees `ae_emb` in IMPACT_CellOT's config and silently replaces `data.X` with 50-dim AE-encoded latents (`cellot/data/cell.py` lines 149–178). Every split — train, test, ood — gets the AE encoding applied. Ground truth (`dataset.ood.target.adata.to_df()`) ends up **50-d**.
- The model transports `to_pushfwd` (50-d) → `imputed` (50-d).
- Line 342: `if config.model.name == "cellot" and where == "data_space": imputed = decode(imputed)` — but `decode` is the identity, so `imputed` stays **50-d**.
- Comparison happens in **50-dim latent space**, despite the output path being named `evals_ood_data_space/`.

Only when `--embedding ae` is *also* passed does the elif at line 204 trigger: deep-copy the config, `del config.data.ae_emb`, reload the dataset → ground truth becomes raw 1000-d; `decode` becomes the real AE decoder; `imputed` gets decoded to 1000-d. Then the comparison is genuinely in gene space.

#### What this means for scGen — the mirror bug

scGen's config has no `ae_emb`. The data loader skips the AE-encoding block entirely. Ground truth stays 1000-d gene-space throughout. So scGen + `--where data_space` evaluates correctly in gene space, with or without `--embedding ae`.

**But there's a symmetric mirror bug for scGen + `--where latent_space`**: without `--embedding ae`, the comparison silently stays in 1000-d gene space even though `latent_space` was requested. Trace: `encode`/`decode` are identity (line 282), control/treated stay 1000-d (no encoding triggered at lines 290–293 because `embedding != "ae"`), scGen transport produces 1000-d, no projection branch fires. Output is gene-space comparison written to a directory called `evals_ood_latent_space/`. Wrong space, correct-looking path.

#### The symmetry

The same root cause produces both bugs, with sides swapped:


| Model                              | Natural space (loader's default) | To switch to other space, you must pass `--embedding ae` |
| ---------------------------------- | -------------------------------- | -------------------------------------------------------- |
| IMPACT_CellOT (`ae_emb` in config) | latent (50-d)                    | yes, to get **data_space**                               |
| scGen (no `ae_emb` in config)      | data (1000-d)                    | yes, to get **latent_space**                             |


In both cases, `--embedding ae` is what "switches the space" away from the model's natural default. And in both cases, the silent-bug version is: without the flag, `--where` is *ignored* and you get the natural space regardless. The cookbook spec language must require `--embedding ae` whenever the requested space differs from the model's natural default — or, more simply, always.

#### Spot-check evidence (2026-05-27)

Concrete file shapes confirm:

```
hvg_pearson_residuals_a_ood/impact_cellot/evals_ood_data_space/imputed.h5ad
  /X Dataset {93, 1000}   ← aeflag run (May 8), gene space, CORRECT for data_space

hvg_pearson_residuals_a_iid/impact_cellot/evals_ood_data_space/imputed.h5ad
  /X Dataset {93, 50}     ← standard run only (May 5), LATENT space despite path name

hvg_pearson_residuals_a_ood/scgen/evals_ood_data_space/imputed.h5ad
  /X Dataset {93, 1000}   ← scGen, gene space (always)
```

Numerical Pearson-r at ncells=30, nfeatures=all (square these for R²):


| Model / setup           | Eval space (verified by /X shape) | r     | R²   |
| ----------------------- | --------------------------------- | ----- | ---- |
| IMPACT a_ood (aeflag)   | gene (1000-d)                     | 0.929 | 0.86 |
| IMPACT a_iid (standard) | **latent (50-d)**                 | 0.880 | 0.77 |
| scGen a_ood (standard)  | gene (1000-d)                     | 0.932 | 0.87 |


The IID model evaluated in latent space (0.77) is **lower** than the OOD model evaluated in gene space (0.86), which is the *opposite* of the in-sample-fit expectation — a clear sign the comparison is apples-to-oranges.

#### Implications for the matrix

- The 80 standard `eval_dataspace/` sbatches (from `scripts/generate_data_space_eval_sbatches.py`) **do not pass `--embedding ae`**, so their IMPACT_CellOT outputs are silently latent-space.
- The 10 hand-curated `eval_dataspace_aeflag/` sbatches and the 8 m2 sbatches (from `generate_hvg_flavor_configs.py --m2-two-flavors`) **do pass it** — those IMPACT_CellOT outputs are genuine gene-space.
- Standard-matrix R² heatmaps therefore compare **scGen-in-gene-space** against **IMPACT_CellOT-in-latent-space** — not directly comparable.

The IMPACT side of every standard `eval_dataspace/` IMPACT cell would need re-running with `--embedding ae` to produce a clean comparison. (Junyi 2026-05-27 confirmed re-running is deferred for now; the finding is documented so it isn't lost.)

#### The universal rule we adopt going forward

The four (model × where) combinations behave differently with respect to `--embedding ae`. Per the table above, the loader has two natural-space defaults (IMPACT defaults to latent, scGen defaults to data). The flag's job is to *switch* the eval to the non-default space. So:


| Model         | `--where`      | What `--embedding ae` does                                                                                                         | Recommended?                  |
| ------------- | -------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| IMPACT_CellOT | `data_space`   | required (decodes 50-d → 1000-d)                                                                                                   | **yes — must pass**           |
| IMPACT_CellOT | `latent_space` | invalid (would trigger column-count assertion at `evaluate.py:130` because GT gets reloaded to 1000-d while predictions stay 50-d) | **no — must NOT pass**        |
| scGen         | `data_space`   | no-op (scGen's natural is already 1000-d data)                                                                                     | optional; pass for uniformity |
| scGen         | `latent_space` | required (encodes 1000-d → 50-d; this is the §5.5 mirror bug)                                                                      | **yes — must pass**           |


So the practical rule is: **pass `--embedding ae` for every eval *except* IMPACT_CellOT + `--where latent_space`**. The scGen + data-space case is the only one where the flag is a no-op rather than required, but passing it is harmless and keeps the eval-spec uniform. The current `generate_hvg_flavor_configs.py` happens to omit the flag for scGen + data-space (lines 222–242), which is correct in output but inconsistent with this rule — worth normalizing in a future cleanup so the four (model × where) cells follow one pattern instead of three.

The cookbook spec should encode this rule: an eval spec implies `--embedding ae` by default, and any invalid combination is rejected at spec-validation time rather than producing a wrong-space silent output.

#### Why this design is unfortunate — and why we happened to find it

`--where` and `--embedding` look like independent flags. They aren't — for AE-based models, `--where data_space` is silently a no-op unless `--embedding ae` is also passed. A correctly-designed CLI would either auto-detect (decode whenever an AE is in the config) or error loudly.

The upstream Bunne paper code *did* have an auto-detect mechanism at `evaluate.py` lines 274–278: if `embedding` is `None`, look for a sibling directory named `model-cellot` and infer the embedding from its config. In the upstream paper's directory layout, the canonical cellot model was named `model-cellot/`, so when the user evaluated a sibling baseline (scgen/, identity/, random/, average/), the auto-detect propagated cellot's embedding choice to the baseline eval — *masking* this bug in practice.

**Our project disabled that auto-detect by accident**: we named the cellot model `impact_cellot/` (deliberately, to signal IMPACT framing per §1.3 / §2 of this doc) instead of `model-cellot/`. With no `model-cellot/` sibling to read, the auto-detect at line 275 never fires, `embedding` stays `None`, and both bugs become visible.

So the bug isn't a defect we introduced — it was latent in the upstream design, *masked* by the upstream naming convention. Our naming improvement (which has its own good reasons) is what surfaced it. The proper fix is to make the dependency explicit in the sbatch and in the spec, not to revert the naming. Or, as a one-line-per-experiment workaround, we could add `ln -s impact_cellot model-cellot` in each experiment dir to re-enable the auto-detect; this is a quick fix for the existing 80 sbatches but not the right long-term answer.

### 5.6 The latent-space-vs-data-space evaluation choice

CellOT's natural output space is the **latent** space defined by an autoencoder it's trained against. Evaluations can be done in latent space (cheaper, smoother) or by decoding back to **data space** (gene expression — harder, but biologically interpretable). Older runs evaluated in latent space for stale data and data space for renorm data, possibly for historical reasons. *Junyi flagged this as a choice he can no longer fully reconstruct — worth re-examining when revisiting `08.1`.*

### 5.7 Toggle-OOD split is unstratified — species counts in OOD vs IGNORE drift apart

Discovered during the 2026-05-28 conversation about the M2 monocyte UMAP. Subtle but worth knowing about; doesn't break current metrics, would matter for any future paired analysis.

#### The symptom

In M2 (non-classical + generic monocyte holdout, Pearson HVG), the OOD subset has **261 mouse cells but only 248 human cells**, even though the cell-matching step in `09_data_prep_toggle_experiments.ipynb` (`match_cells_by_celltype_tissue`) guarantees exactly 509 mouse and 509 human cells in the holdout pool. The IGNORE subset has the mirror imbalance: 248 mouse and 261 human. The two halves are perfectly complementary, which by itself is the tell that this is sampling drift, not a data problem.


|              | CL:0000875 | CL:0000576 | row total |
| ------------ | ---------- | ---------- | --------- |
| OOD mouse    | 218        | 43         | **261**   |
| OOD human    | 203        | 45         | **248**   |
| IGNORE mouse | 208        | 40         | 248       |
| IGNORE human | 223        | 38         | 261       |


#### Where the imbalance is introduced

Two layers do splitting, and only one of them stratifies on species:


| Layer                                 | What it does                                                                   | Stratified by `condition` (= species)?                        |
| ------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------- |
| 80/20 train/test on non-holdout cells | `split_cell_data_train_test` (`cellot/cellot_gpu/cellot/data/cell.py:261-281`) | **Yes** — loops over `groupby` groups                         |
| 50/50 ignore/ood on holdout cells     | `split_cell_data_toggle_ood` (`cell.py:322-353`)                               | **No** — single `train_test_split` on the pooled holdout pool |


The relevant line in the second function:

```python
ood = data.obs_names[data.obs[key].isin(value)]
trainobs, testobs = train_test_split(ood, random_state=random_state, test_size=0.5)
```

`train_test_split` is `sklearn.model_selection.train_test_split` — not custom code. Without `stratify=`, it shuffles the 1018 row labels uniformly and slices the first 509 / last 509. It has no concept of `condition`. Expected mouse count in OOD is 254.5; observed 261 is ~0.6 SD above the mean for a hypergeometric draw (σ ≈ 11.3). Normal sampling variance.

#### Toy example — why the drift happens

Eight cells, 4 mouse + 4 human:

```python
from sklearn.model_selection import train_test_split

holdout = ["m1","m2","m3","m4","h1","h2","h3","h4"]
ignore, ood = train_test_split(holdout, test_size=0.5, random_state=0)
# ignore might be ["m2","h3","h1","m4"]  → 3 mouse + 1 human
# ood    might be ["m1","m3","h4","h2"]  → 1 mouse + 3 human
```

The seed makes the shuffle reproducible; it doesn't make it balanced. With `stratify=["mouse"]*4 + ["human"]*4`, sklearn would guarantee 2+2 on each side.

#### Why this is original CellOT behavior, not a bug we introduced

Tracing back to the paper-original framing (`§1.1` of this doc):

- In CellOT-original, `condition` ∈ {control, drug-treated}. The holdout was a *cell type* within a single experiment, and cell types were paired across conditions by design (same dish, same culture, then split into ± drug exposure). So even if the unstratified 50/50 split drifted the holdout's control:treated ratio, the downstream evaluation (control → treated mean shift, R² of means) didn't suffer — both sides of the comparison were computed independently from their own clouds.
- In speciesOT (`§1.3`), `condition` was reused to mean {mouse, human}. The 80/20 train/test layer kept doing the right thing because it explicitly groups by `condition`. The 50/50 ignore/ood layer was never updated for the new meaning of `condition`, so the species ratio in the OOD subset drifts even though the upstream matching step bent over backwards to ensure 509 = 509.

Same input under the two interpretations:


| Interpretation of `condition` | Holdout pool          | After unstratified 50/50 | Does the drift matter?                                                                                                                                                                                            |
| ----------------------------- | --------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| {ctrl, drug} (paper-original) | 509 ctrl + 509 drug   | 261 ctrl / 248 drug      | No — the metric is a **two-sample comparison** (cloud of 261 predictions vs cloud of 248 ground truths); cells are not paired, and the sample sizes only affect noise floor, not bias                             |
| {mouse, human} (speciesOT)    | 509 mouse + 509 human | 261 mouse / 248 human    | Same metric → still no, *for our current metrics*. But the species axis is now the axis we care about for biology, so the imbalance is worth naming explicitly in figure captions and any future paired analysis. |


**Important conceptual note**: the 50/50 ignore/ood split is on a *different axis* from the source/target distinction. It splits "which half of the holdout cells get evaluated on" vs "which half gets discarded" — not "which is source" vs "which is target." After the split, the OOD subset itself contains *both* species, and they play different roles inside it: the 261 mouse cells are model **input**, the 248 human cells are **ground truth**. The imbalance is between "how many predictions we make" and "how many ground truths we compare to" — two clouds of different sizes, which is fine for both OT and for the two-sample metrics we use.

#### Why it doesn't bite our current metrics — a second toy

The two columns in `evals.csv` (`r2-means` squared, and `mmd`) are both **two-sample distributional comparisons** that estimate population quantities from each side independently. Per-cell pairing is not required.

Toy model. Population of M2 monocyte cells. True species-mean expression vectors are μ_mouse and μ_human (each 1000-d). The model predicts μ̂_human from any mouse sample.

- **Predicted-mean estimator**: feed 261 mouse cells through the model, average. As n_mouse grows, μ̂_human converges to the model's population predicted-mean.
- **Actual-mean estimator**: average the 248 actual human cells. As n_human grows, converges to μ_human.
- **R²-of-means**: Pearson_r(μ̂_human, μ_human)². As both n's grow, both estimators converge, R² converges to its true value.

The *bias* of R²-of-means does not depend on the n_mouse : n_human ratio — only on whether each sample is drawn i.i.d. from the population it claims to represent (it is, since OOD and IGNORE are complementary halves of the same matched pool). The *variance* of R²-of-means scales roughly with 1/min(n_mouse, n_human). At 248 vs balanced 254, that's a ≈ 1.2% increase in noise floor — undetectable in practice. Same logic for MMD: it's a kernel two-sample statistic, consistent under any (n, m) with both → ∞.

A useful sanity check: if you re-ran the whole pipeline with a different seed and got 248/261 instead of 261/248, the `evals.csv` numbers would shift by less than the inter-seed variability already present in the model training. The imbalance is in the noise floor.

When the imbalance *would* bite:


| Analysis                                   | Why it cares                                                                                                    |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------- |
| Per-cell paired prediction error           | Can't pair 261 mouse predictions with 248 human ground truths                                                   |
| Donor-level matched mouse↔human comparison | The drift can drop a donor entirely on one side                                                                 |
| Cell-by-cell transport-cost diagnostics    | Some implementations assume equal sample sizes                                                                  |
| UMAP overlay counts in figures             | Caption says "n=248 actual human OOD"; that 248 vs the 261 mouse you might overlay is honest but worth labeling |


None of these are in the current pipeline. The UMAP one is what surfaced the discrepancy in the first place (`umap_atlas_ref_m2_ood_pearson_scgen_impact.pdf` legend reads "Monocyte holdout — mouse (n=261)" vs "Actual human OOD (n=248)").

#### One-line fix, deferred

```python
trainobs, testobs = train_test_split(
    ood,
    random_state=random_state,
    test_size=0.5,
    stratify=data.obs.loc[ood, "condition"].astype(str),   # add this
)
```

We don't apply this mid-experiment because every existing `evals.csv` was produced under the unstratified seed; flipping it would re-shuffle which specific cells land in OOD vs IGNORE and invalidate direct comparison against the current matrix. File for a v08 dataset cut, alongside the other batch of `_v07.h5ad` → `_v08.h5ad` regenerations.

The cookbook spec language should also call this out: any toggle-OOD recipe should declare whether the holdout's 50/50 split is stratified, and on what.

### 5.8 What the current M2 evaluation matrix doesn't tell us

A 2026-05-28 audit of the M2 setup against this doc surfaced two methodological gaps that are worth being explicit about. Both are *gaps*, not bugs — current numbers are correct, just incomplete.

#### No within-distribution baseline R²

`scripts/evaluate.py` accepts both `--setting ood` (held-out cell type) and `--setting iid` (test split: random cells from cell types that *were* in training). Our pipeline only ever invokes the OOD setting, so every reported number — Figure F's R²-of-means, the IID-vs-OOD bars, the `r2_scatter_`* panels — is on the same OOD slice.

The 20%-test split (2,418 cells per M2 cell, per-species stratified at split time) is *used* during training as an overfitting monitor (`eval_freq: 250` in IMPACT, `1000` in scGen — the cached `scalars` files in each `*/cache/` directory are the train-vs-test loss curves). It is *never* surfaced into a final `evals.csv`. So we have no in-distribution R² anchor against which to interpret the OOD R²:

- "M2 OOD R² of means is 0.86" is the headline.
- "M2 in-distribution test R² is X" is unmeasured. If X = 0.99, OOD penalty is meaningful. If X = 0.87, the model isn't really doing OOD-specific work — it's near its ceiling everywhere.

A reviewer asking "how much of the 14% gap to perfect prediction is OOD-specific vs intrinsic model error?" has no answer in the current numbers.

**Cheap fix, no retraining needed.** Add `--setting iid` evaluations to existing M2 models (4 cells × 2 models = 8 sbatch jobs, ~30 min each, ~4 hours total wall-clock with parallelism). Output: a parallel set of `evals_iid_data_space/` directories alongside the current `evals_ood_data_space/`, giving a within-distribution baseline for every cell of the matrix. This is a one-liner change to the existing eval sbatch template (swap `--setting ood` for `--setting iid` and the eval prefix). File for the same v08 cut as the §5.7 stratification fix.

#### All four M2 result cells share `random_state=0`

Every M2 config has `datasplit.random_state: 0`, so the *exact same* set of cells ends up in train / test / ignore / ood across (Pearson × seurat_v3) × (iid × ood). This is a deliberate design choice — it makes cross-flavor and cross-mode comparisons clean (the only thing that varies is the gene set, the model, or the training mode, never the cells). The §5.7 species drift (261 / 248) is the *deterministic* output of seed 0; under seed 42 it could be 245 / 264.

What we *don't* have: an estimate of split-induced variance. If we re-ran one cell (say Pearson OOD) with 3–5 different seeds, would R² stay at 0.86 ± 0.005 or drift to 0.86 ± 0.04? Currently unknown, so every reported R² is a point estimate, not a mean ± SE. This bounds how strongly we can claim cross-flavor or cross-mode differences are meaningful: a 0.86 vs 0.84 contrast might be real or might be within seed noise.

**Expensive fix, deferred.** Multi-seed retraining is ~150–200 GPU-hours for the M2 matrix alone. Not worth doing until the headline pipeline is otherwise stable. Worth flagging here so future-Junyi or a reviewer doesn't assume the reported values are mean-of-replicates when they're single-seed point estimates.

### 5.9 How to read the MMD metric — floor, ceiling, gamma, and the AE round-trip

Captured 2026-06-02 (MMD floor / gamma) and extended 2026-06-05 (MMD ceiling, gap-closure metrics, R² analog, AE round-trip resolution). MMD is the second column in every `evals.csv` (alongside R²-of-means), and it is easy to misread — raw MMD alone is not a sufficient headline number. This section pins down what MMD measures, the floor/ceiling reference frame, and a subtle but important space-mismatch that affects AE-based models.

#### What MMD is and how the code computes it

MMD (Maximum Mean Discrepancy) is a **distance between two distributions** — here the cloud of real target cells (`treated`) vs the model's predictions (`imputed`), in 1000-d gene space. It is a *two-sample* statistic: cells are not paired, only the two clouds are compared. The implementation (`cellot/cellot_gpu/cellot/losses/mmd.py`):

```python
def mmd_distance(x, y, gamma):
    xx = rbf_kernel(x, x, gamma)   # within real
    xy = rbf_kernel(x, y, gamma)   # cross
    yy = rbf_kernel(y, y, gamma)   # within imputed
    return xx.mean() + yy.mean() - 2 * xy.mean()
```

with the RBF (Gaussian) kernel `k(a,b) = exp(-gamma·‖a-b‖²)`. Read the formula as *"within-cloud similarity minus cross-cloud similarity."* If the two clouds overlap, the cross term `xy` is as large as the within terms → MMD ≈ 0. If they are separated, `xy` shrinks while `xx`,`yy` stay large → MMD > 0.

Two things the eval does that matter for interpretation (`scripts/evaluate.py`):

1. **It averages over 50 bandwidths**: `gammas = np.logspace(1, -3, num=50)` (10 → 0.001), via `compute_mmd_loss = np.mean([mmd_distance(·,·,g) for g in gammas])`. The reported scalar is this multi-kernel average — robust to not knowing the "right" bandwidth a priori.
2. **It subsamples**: for each `ncells` in `--n_cells` (data-space OOD uses `30,50,80`) it draws `ncells` cells from each cloud and repeats `n_reps` times (default 10), averaging. MMD is O(n²), and subsampling also produces error bars. **Consequence: MMD values are only comparable at equal `ncells`.**

#### What gamma does — "stricter" = the distance penalty

`gamma` multiplies the squared distance inside the exponential, so it sets how fast similarity decays with distance. The distance at which similarity falls to ≈ e⁻¹ is `d* = 1/√gamma`:

- **High gamma** → small `d`* → only cells within a tiny radius count as similar (strict / narrow kernel).
- **Low gamma** → large `d*` → even far-apart cells count as similar (loose / wide kernel).

Numerically, for two cells at squared distance 1: `exp(-0.01·1)=0.99` (γ=0.01, "alike") vs `exp(-10·1)=0.00005` (γ=10, "not alike").

#### Why both gamma extremes lose the signal — and why they are *asymmetric*

The crux is that `xx` and `yy` contain the **diagonal** (each cell vs itself, distance 0, `k=1` for *any* gamma), whereas `xy` does not (real vs imputed cells are never identical).

- **gamma → large:** off-diagonal terms → 0 everywhere, but the diagonals of `xx`,`yy` stay at 1. So `xx.mean → 1/n`, `yy.mean → 1/n`, `xy.mean → 0`, and **MMD → 2/n** — a positive constant set purely by sample size, blind to cloud shape.
- **gamma → small:** every pair (including off-diagonal and cross) → 1, so `xx ≈ yy ≈ xy ≈ 1` and **MMD → 0**.

So the two ends are *not* symmetric: low-gamma → 0, high-gamma → 2/n (not 0), and the discriminative signal lives in the **middle** where the bandwidth ≈ the real separation between the clouds. In the M2 OOD data the per-gamma curve peaks around **gamma ≈ 0.005–0.007** (`gamma_curve_m2_ood.png`). This is the whole reason the eval averages 50 gammas instead of picking one.

#### The "MMD floor" — an irreducible baseline for interpreting the number

A raw MMD of 0.108 is meaningless without a reference, because even a *perfect* model that resampled real cells gets MMD > 0 (the finite-sample bias above). We estimate that floor empirically with `compute_mmd_floor` (`cellot/cellot_gpu/cellot/losses/mmd.py`, added 2026-06-02): split the **real** target cells into half A / half B and run the *identical* MMD (same 50 gammas, same `ncells`, same estimator), averaged over reps. Because it is computed the same way as the model's MMD, the meaningful quantity is

> **gap above floor = model_mmd − mmd_floor**

which is the part of the discrepancy that is *not* sampling noise. Computed on the existing M2 OOD models (treated pool = 248 real human cells):


| ncells | model MMD (IMPACT) | model MMD (scGen) | `mmd_floor` | `2/n` |
| ------ | ------------------ | ----------------- | ----------- | ----- |
| 30     | 0.145              | 0.182             | 0.064       | 0.067 |
| 50     | 0.122              | 0.158             | 0.038       | 0.040 |
| 80     | 0.106              | 0.144             | 0.024       | 0.025 |


Two readings:

- The **floor collapses with `ncells`** (0.064 → 0.024) purely from the 1/n bias, but the **gap above floor is flat**: ≈ 0.082 for IMPACT, ≈ 0.120 for scGen, at every sample size. The gap — not the raw MMD — is the sample-size-robust error, and it confirms IMPACT_CellOT beats scGen by the same margin regardless of `ncells`.
- The model curve **coincides with the floor at high gamma** (both → 2/n). This is *not* the model performing as well as the oracle — it is the metric going blind, since at a strict-enough kernel neither comparison can see any off-diagonal structure.

#### `mmd_floor` vs `2/n` — empirical vs theoretical

These are two views of the same baseline and are easy to conflate:


|                  | `mmd_floor`                                | `2/n`                                      |
| ---------------- | ------------------------------------------ | ------------------------------------------ |
| Source           | **measured** from the real cells           | **closed-form** (`2.0 / ncells`)           |
| Gammas           | average of the self-MMD over all 50        | none — it is the `gamma → ∞` asymptote     |
| Depends on data? | yes (real cloud geometry)                  | no (only `n`)                              |
| Role             | the baseline you subtract from `model_mmd` | sanity check / intuition for the magnitude |


They are close (0.024 vs 0.025 at n=80) only because many of the 50 log-spaced gammas live in the high-gamma plateau where the floor ≈ 2/n; the average lands just under it. Use `mmd_floor` for the actual gap-above-floor comparison (it matches the model's recipe); treat `2/n` as the explanation for *why* the floor is that size and why it scales ~1/n.

#### The MMD ceiling — the no-transport baseline

The floor answers *"how low could MMD go even with a perfect resample of the real target?"* The **ceiling** answers the complementary question: *"how far apart are the two clouds if we do **no** species transport at all?"*

For IMPACT_CellOT (mouse → human), the ceiling is

> `**mmd_ceiling` = MMD(mouse control, real human target)**

computed with the same 50-gamma ensemble, `ncells` subsampling, and `n_reps` averaging as the model's MMD. Biologically: take the OOD mouse cells (model **input**) and compare their distribution directly to the real human cells (model **ground truth**), without running the transport map. This is the **identity / no-transport** reference — the distributional gap the model is trying to close.

On the MMD axis (lower = better):

```
floor  ◄──── model should move this way ────►  ceiling
(best   achievable                         no transport;
 resample of real human)                    just compare mouse vs human)
```

A model that genuinely helps should land **below** the ceiling (closer to human than raw mouse was) and ideally as close to the floor as the biology allows.

#### `gap_above_floor` and `frac_gap_closed` — the headline comparison metrics

Raw MMD conflates irreducible sampling noise with model error, and it is not comparable across different `ncells`. The two derived quantities in `extended_metrics.csv` fix both problems:


| Metric                | Formula                                                 | How to read it                                                                                                                                                                                                                                                                         |
| --------------------- | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `**gap_above_floor`** | `mmd_model − mmd_floor`                                 | Sample-size-robust **error above the oracle**. Flat across `ncells` when the estimator is working (M2 v08 IMPACT: ≈ 0.092 at n=30/50/80). This is the number to compare across models and preprocessing cuts.                                                                          |
| `**frac_gap_closed`** | `(mmd_ceiling − mmd_model) / (mmd_ceiling − mmd_floor)` | **Fraction of the identity→floor gap closed by the model.** 1.0 = reached the floor (best possible at this `ncells`). 0.0 = no better than identity (mouse-as-is). **Negative = worse than identity** — the transport overshot and landed farther from human than untransported mouse. |


**Use `gap_above_floor` and `frac_gap_closed` as the headline MMD comparison**, not raw MMD. This is the rule in `AGENTS.md` and the v08 scorecard notebook (`22_v08_results.ipynb`).

Example (M2 v08 OOD IMPACT, `ncells=80`): `mmd_model=0.117`, `mmd_floor=0.023`, `mmd_ceiling=0.106` → `gap_above_floor=0.093`, `frac_gap_closed≈−0.13`. R²-of-means is 0.93 — the model nails the mean while the full-distribution metric says it overshoots relative to identity. That tension between R² and MMD is real and is exactly why both metrics are kept (see below).

The v08 preprocessing cut (assay filter + stratified split, §5.10) showed why these metrics matter: m1 IMPACT's `frac_gap_closed` went from **−0.71 (v07) to +0.06 (v08)** — a win that raw R²/MMD alone obscured — while `gap_above_floor` tightened 0.113 → 0.080. The ceiling also **rose** (0.090 → 0.109) because dropping Smart-seq2 removed a platform-mismatch artifact and exposed the true cross-species gap.

#### R² floor and ceiling — the mean-based analog

R²-of-means (`r2-means` in `evals.csv`, squared to true R²) compares only per-gene **mean vectors**. The same floor/ceiling framing applies, with signs flipped (higher R² = better):


| Metric               | Definition                                           | Role                                                                                                    |
| -------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| `**r2_self`**        | Split-half correlation² of real human target means   | **Best achievable** — how well two independent halves of the same population agree (~0.99 for M2 v08).  |
| `**r2_identity`**    | corr²(mean(mouse control), mean(human target))       | **No-transport baseline** — how similar mouse and human means are without any model (~0.56 for M2 v08). |
| `**r2_model`**       | corr²(mean(imputed), mean(human))                    | What the model actually achieves (~0.93 for M2 v08 IMPACT).                                             |
| `**frac_r2_closed**` | `(r2_model − r2_identity) / (r2_self − r2_identity)` | Fraction of the identity→self gap closed on the mean. M2 v08 IMPACT ≈ **0.85**.                         |


R² and MMD floor/ceiling are **complementary views of the same experiment**: R² asks whether the model got the average expression right; MMD asks whether the full cloud shape matches. A model can score high `frac_r2_closed` while `frac_gap_closed` is negative — it captured the mean but got the spread wrong (or overshot in distribution space).

**Important:** R²'s floor/ceiling references are computed on **raw gene-space means** and are **not distorted by the autoencoder** (means commute through encode/decode approximately). So `frac_r2_closed` is trustworthy as written. MMD's floor/ceiling have an AE caveat — next subsection.

#### The AE round-trip — why raw `mmd_ceiling` can sit below model MMD (and look like "overshoot")

This was the central confusion in the 2026-06-05 M1/M2 analysis and is documented in `20_m1_mmd_investigation.ipynb` §6.

##### What the pipeline actually compares

IMPACT_CellOT's data-space evaluation path (with `--embedding ae`, §5.5) is:

```
mouse control  ──encode──►  latent  ──transport──►  latent'  ──decode──►  imputed (1000-d)
                                                                                  │
real human target (1000-d, raw)  ◄──────────── MMD(imputed, treated) ────────────┘
```

The model's `imputed` cloud lives in **AE-decoded gene space** — it passed through encode → transport → decode. The real human `treated` cloud does **not** — it is the raw normalized expression matrix.

But `extended_metrics.py` (as of 2026-06-05) computes:


| Reference     | Clouds compared            | Space                                         |
| ------------- | -------------------------- | --------------------------------------------- |
| `mmd_model`   | imputed vs treated         | **decoded vs raw** ← mismatch on imputed side |
| `mmd_floor`   | split-half of treated      | **raw vs raw**                                |
| `mmd_ceiling` | control (mouse) vs treated | **raw vs raw**                                |


So the model MMD pays an **AE reconstruction tax** that the floor and ceiling do not.

##### Measuring the tax

Run the AE round-trip on the real human target alone:

> `**mmd_ae_recon` = MMD(decode(encode(human)), human)**

For m1 v08 this is **≈ 0.083** — a large irreducible discrepancy introduced purely by the autoencoder bottleneck, before any transport happens. The AE cannot perfectly reconstruct 1000-d gene expression from 50-d latent; that distortion shows up as MMD.

Numerically (m1 v08 OOD, `ncells=80`, illustrative):


| Quantity                | Value                            | Clouds                         | Space          |
| ----------------------- | -------------------------------- | ------------------------------ | -------------- |
| Raw identity gap        | `mmd_ceiling` ≈ **0.109**        | raw mouse vs raw human         | raw            |
| AE reconstruction floor | `mmd_ae_recon` ≈ **0.083**       | decode(encode(human)) vs human | decoded vs raw |
| Model MMD               | `mmd_model` ≈ **0.11–0.14**      | imputed vs human               | decoded vs raw |
| Decoded identity gap    | `mmd_decoded_ceiling` ≈ **0.31** | decode(encode(mouse)) vs human | decoded vs raw |


Because `mmd_ceiling` (0.109) < `mmd_model` (0.11+) **and** `mmd_ae_recon` (0.083) is already a large fraction of the model score, `**frac_gap_closed` goes negative** even when the transport map is doing useful work. This is an **apples-to-oranges comparison**, not necessarily evidence that OT "overshot."

##### The honest reference frame (decoded space)

All three clouds should be measured in the **same space** — either all raw or all AE-decoded. For IMPACT_CellOT the natural choice is decoded space, because that is where `imputed` lives:


| Honest reference             | Formula                               | m1 v08 (≈) |
| ---------------------------- | ------------------------------------- | ---------- |
| **AE-recon floor**           | MMD(decode(encode(treated)), treated) | ~0.083     |
| **Model MMD**                | MMD(imputed, treated)                 | ~0.11–0.14 |
| **Decoded-identity ceiling** | MMD(decode(encode(control)), treated) | ~0.31      |


With these references, m1 v08 IMPACT `**frac_gap_closed` ≈ 0.91** — the transport closed ~91% of the gap between "decoded mouse with no transport" and "AE-limited best achievable." That is the performance statement that matches what the pipeline actually computes.

Schematic of the two reference frames side by side:

```
RAW-SPACE refs (current extended_metrics.py — misleading for IMPACT):
  floor ≈ 0.02    ceiling ≈ 0.11    model ≈ 0.12
  |-------|-------------X--|          ← model sits above ceiling → negative frac_gap_closed

DECODED-SPACE refs (honest for IMPACT):
  ae_floor ≈ 0.08    model ≈ 0.12    decoded_ceiling ≈ 0.31
  |----------X-------------------|    ← model well inside ceiling → frac_gap_closed ≈ 0.91
```

##### What this means for interpretation — and for improving the model

1. **Do not panic at negative `frac_gap_closed` on IMPACT runs** until the AE-space references are in the sidecar. Check `frac_r2_closed` (mean-based, AE-robust) and `gap_above_floor` alongside it. M2 v08 IMPACT: `frac_r2_closed≈0.85` while raw `frac_gap_closed≈−0.13` — the model is good on means, and the negative MMD fraction is largely a reference-frame artifact, not proof of catastrophic overshoot.
2. **The AE is a real bottleneck for distributional metrics.** Even with a perfect transport map in latent space, decoded output cannot beat `mmd_ae_recon` (~0.083). Improvements to MMD require either a better AE (lower reconstruction MMD) or evaluating in latent space (where transport happens natively — but that is less biologically interpretable, §5.6).
3. **Removing the AE would not automatically yield lower MMD in gene space.** The transport map is *trained against* the AE's latent geometry. The ~~0.109 raw mouse-vs-human gap is measured in a space the model never operates in. The relevant identity gap in the model's working space is the decoded ceiling (~~0.31), not the raw one (~0.11).
4. **Genuine OT overshoot is still possible** — if, after fixing the reference frame, `mmd_model` still exceeds the decoded ceiling. That would mean transport pushed cells farther from human than decoded-mouse-as-is. Distinguish this from the AE artifact by always comparing in decoded space.

**TODO (code):** add `mmd_ae_recon_floor` and `mmd_decoded_ceiling` to `extended_metrics.py` (load the AE via `cellot.utils.evaluate.load_projectors(model-scgen, "ae", "data_space")`, round-trip control/treated, recompute floor/ceiling) so `frac_gap_closed` in the sidecar is honest by default. Until then, treat raw `frac_gap_closed` on IMPACT as **unreliable** and use `frac_r2_closed` + `gap_above_floor` as the safe headlines.

#### Why we keep both MMD and R²

R² (`r2-means`) compares only the per-gene **mean** vectors of the two clouds — a first-moment check, blind to spread/shape. MMD compares the **full distribution**. A model can score high R² (right average) while MMD-above-floor stays high (wrong spread or a missed subpopulation — exactly the failure mode of the M2 two-population holdout). The two are complementary; see also §5.8 on what the matrix still doesn't measure.

#### Implementation pointers and a scope decision

**Core MMD code**

- `compute_mmd_two_sample(A, B=None, split_half=False, ...)` — general two-cloud MMD; `split_half=True` on one cloud gives the floor (`cellot/cellot_gpu/cellot/losses/mmd.py`).
- `compute_mmd_floor(target, ...)` — thin wrapper around `split_half=True`.
- `compute_marginal_divergence(treated, imputed)` — per-gene KL/JS; sidecar column `mean_js` (`cellot/cellot_gpu/cellot/losses/divergence.py`).

**Sidecar pipeline (preferred over editing `evaluate.py`)**

- `scripts/dump_eval_clouds.py` — dumps `treated` / `imputed` / `control` / `genes` to `eval_clouds.npz` (fast recompute, no torch reload).
- `scripts/extended_metrics.py` — writes `extended_metrics.csv` beside `evals.csv` with floor, ceiling, `gap_above_floor`, `frac_gap_closed`, `mean_js`, and the R² analogs (`r2_self`, `r2_identity`, `frac_r2_closed`). Run via `./hub metrics <run_id>` or directly in the CellOT env.
- `./hub show` / `compare` / `handoff` — read the sidecar and surface the headline fields.

**Analysis notebooks**

- `speciesOT/baseline/analysis/20_m1_mmd_investigation.ipynb` — gamma-sensitivity curves, floor-vs-`ncells` table, M1/M2 comparison with ceiling + `frac_gap_closed`, Figure-G marginals with JS.
- `speciesOT/baseline/analysis/22_v08_results.ipynb` — v07 vs v08 scorecard using `evals.csv` + `extended_metrics.csv`.

**Decisions**

- **2026-06-02:** do not write per-gamma breakdown or the floor into `evals.csv`; keep as sidecar / notebook artifacts.
- **2026-06-05:** judge models by `gap_above_floor` / `frac_gap_closed` (and `frac_r2_closed` for means), not raw MMD/R² — but treat raw `frac_gap_closed` on IMPACT as unreliable until AE-space references land (see AE round-trip subsection above).
- **2026-06-09:** the AE-honest references now exist in `scripts/decoded_frame_metrics.py` (`mmd_ae_recon_floor`, `mmd_decoded_ceiling`, `frac_gap_closed_decoded`, `frac_r2_closed_decoded`). `./hub metrics` runs it alongside `extended_metrics.py`, and the hub catalog/`scorecard`/`list`/`show`/`card`/vault surface `**frac_gap_closed_decoded` as the headline**. The raw `frac_gap_closed` is kept only as a diagnostic. See the next subsection for the frozen benchmark.

#### The north-star metric and the frozen benchmark (how we answer "are we improving?")

The recurring pain in this project was an unstable ruler: raw `frac_gap_closed` flips
sign for measurement reasons, so the same model looked "good" on one cut and "broken"
on another. The fix is one fixed, documented ruler applied to one fixed set of cells.

**North-star (one number):** `frac_gap_closed_decoded` — the fraction of the
identity→floor MMD gap closed, measured in the AE-decoded frame where the model's
`imputed` cloud actually lives (so it is apples-to-apples). Range: 1.0 = best
achievable at this `ncells`; 0.0 = no better than untransported mouse; negative =
genuine overshoot (now meaningful, because the reference frame is honest).

**Two guardrails (read alongside, never instead):**

- `frac_r2_closed_decoded` — did the model get the per-gene **mean** right? Mean-based,
so it cross-checks the distributional north-star.
- `mean_js` — mean per-gene Jensen-Shannon divergence (a symmetric, bounded version of
**KL divergence**). This is the per-gene distributional check; it is the metric to
show when the question is phrased in KL terms.

**Why these and not something else:** no single scalar is "objectively correct" for
distribution matching — the point is a *fixed, documented* choice so comparisons are
consistent over time. `frac_gap_closed_decoded` answers "does the whole cloud match,
in the space the model operates in"; `frac_r2_closed_decoded` answers "is the average
expression right"; `mean_js`/KL answers "is each gene's marginal right." If we ever
change the ruler, we change it here and re-run the frozen benchmark below — we do not
silently switch metrics per experiment.

**The frozen benchmark (the fixed set of cells):** model-version comparisons are made
on the **v08 OOD cuts** — `hvg_pearson_residuals_{m1,m2,a_uncapped}_v08_ood` — with a
**fixed eval seed (`random_state=0`)** and **fixed `ncells` (30/50/80, headline at 80)**.
Because the held-out cell types, seed, and subsample sizes are pinned, any change to the
model or preprocessing is judged by whether `frac_gap_closed_decoded` moves on these
same cells. New experiments may add their own cuts, but "did this help?" is always
answered against this frozen benchmark via `./hub scorecard`. (Current standing values
are in `./hub scorecard` and `22_v08_results.ipynb`; do not hardcode them here — they
move as runs are recomputed.)

### 5.10 Sequencing-assay mixing is an ENFORCED filter, not optional metadata

Discovered 2026-06-05 while investigating the M1 held-out monocytes (`speciesOT/baseline/analysis/21_data_imbalanced.ipynb`).

#### The finding

The atlas `_v07.h5ad` datasets **mix sequencing platforms within each species**. For the 426 OOD non-classical monocytes (M1):


| assay                          | human  | mouse  |
| ------------------------------ | ------ | ------ |
| 10x 3' v3 (`EFO:0009922`)      | 179    | 0      |
| 10x 3' v2 (`EFO:0009899`)      | 0      | 187    |
| **Smart-seq2 (`EFO:0008931`)** | **28** | **32** |


Smart-seq2 is plate-based, full-length, no UMIs — a fundamentally different expression distribution from 10x droplet 3'. The Smart-seq2 minority is exactly the within-species "scatter": **~77% of the cells flagged as scattered are Smart-seq2 (vs ~3% of the central blob), and the one fully detached UMAP sub-cluster is 100% Smart-seq2.** The apparent "donor effect" (TSP1/TSP14 scattered, TSP2 clean) is a proxy — those donors simply have more Smart-seq2 cells. So the heterogeneity that kept M1's MMD from tightening is a **preprocessing artifact, not biology**.

#### The rule (full-scope enforcement)

For **all** atlas preprocessing we keep exactly one droplet platform per species and drop everything else:

- mouse → `10x 3' v2` (`EFO:0009899`)
- human → `10x 3' v3` (`EFO:0009922`)

This is recorded in `ExperimentSpec.assay_filter` (default = the above) and **enforced** in `speciesOT/hub/prep.py:_apply_assay_filter`, applied right after the source files are loaded (before ortholog matching / HVG). It was previously recorded as "intent" only and never applied; that gap is now closed. Tokens accept the `chromium_v{2,3}` aliases, the literal `10x 3' v{2,3}` strings, or the EFO ids.

#### Caveat for existing datasets

The current `_v07.h5ad` files (m1, m2, the whole hvg-flavor matrix) were built **before** enforcement, so they still contain the Smart-seq2 cells. Applying the treatment to them requires a `./hub prep` rebuild (a `_v08` cut) + retrain — file alongside the §5.7 stratification fix. The expectation: dropping Smart-seq2 removes the scatter, leaves single-platform populations, and should tighten MMD without cherry-picking.

---

## 6. Open questions / things this doc should eventually answer

- Does `IMPACT` stand for something specific, or is it just a label?
- What is the formal definition of `T_drug'` that we are trying to predict? (Pointwise? Distributional? On the population mean?)
- For BCG: are the mouse-BCG and human-BCG datasets at comparable cell-type resolution and timepoint? (Critical for whether `T_drug` learned on mouse can plausibly apply to human.)
- For the renorm-vs-stale evaluation-space asymmetry: was there a methodological reason or just a historical accident? `08.1` revisit needed.

---

## References

- Bunne et al., *Learning single-cell perturbation responses using neural optimal transport*, Nature Methods, 2023. (`[reference_papers/Bunne et al - 2023.pdf](../reference_papers/Bunne%20et%20al%20-%202023.pdf)`)
- Lotfollahi et al., *scGen predicts single-cell perturbation responses*, Nature Methods, 2019. (`[reference_papers/scGen.pdf](../reference_papers/scGen.pdf)`)
- Karpathy, [autoresearch](https://github.com/karpathy/autoresearch) — the conceptual inspiration for the (now-deleted) `autospeciesOT/` experiment-orchestrator and a candidate framework for future overnight architecture-search work.


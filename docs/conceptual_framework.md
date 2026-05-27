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
- **What our pipeline currently models**: only the **species effect** (IMPACT_CellOT). We have not yet done the **drug-effect** half of the eventual project. The BCG line (notebook `16_*` and onward) is the first toe in that water; nothing thorough yet.
- **The eventual goal**: given mouse untreated, mouse treated, and human untreated, predict human treated. This requires both a drug-effect transport and a species-effect transport, composed somehow.

---

## 1. The three model variants

All three use the same neural-network machinery (CellOT's ICNN-parameterized OT, or scGen's VAE + latent shift). They differ only in what the *condition* variable is — i.e. what defines the "two clouds" the model learns to transport between.

### 1.1 CellOT (paper-original) — drug effect

| | |
|---|---|
| **Source cloud** | Untreated cells |
| **Target cloud** | Drug-treated cells |
| **Condition** | Treatment status (control vs. drug X) |
| **Cells in both clouds** | Same cell line / type, just exposed to drug or not |
| **OOD generalization tested along** | Unseen single cells (held-out cells of the same type) |
| **Reference** | [Bunne et al., 2023 — `reference_papers/Bunne et al - 2023.pdf`](../reference_papers/Bunne%20et%20al%20-%202023.pdf) |

This is what CellOT was published to do. The biological claim is: *given a control cell, what would it look like if exposed to drug X?* One CellOT model is trained per drug.

**We have never used CellOT in this paper-original framing**, because our datasets (human + mouse atlas, no chemical perturbation) don't contain drug-treated cells. The paper-original framing is included here only as the conceptual anchor — it's what the architecture was designed to model.

### 1.2 CellOT (cell-type framing) — abandoned

| | |
|---|---|
| **Source cloud** | Non-CD8 cells (a large pool of many other cell types) |
| **Target cloud** | CD8 T cells |
| **Condition** | Cell type (everything else vs. CD8) |
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

| | |
|---|---|
| **Source cloud** | Mouse cells |
| **Target cloud** | Human cells |
| **Condition** | Species (mouse vs. human) |
| **OOD generalization tested along** | Held-out cell type — train on most cell types, test on (e.g.) mouse CD8 → human CD8 |
| **What we're testing** | Does the OT map learn a generalizable "mouse-to-human" transformation that works on cell types it never saw during training? |

This is essentially every numbered experiment from late April onward — the HVG-flavor matrix, IID vs. OOD evaluations, renorm vs. stale comparisons.

**Why the name has the `IMPACT_` prefix**: to signal explicitly that this is *not* CellOT's original drug-perturbation task. The architecture is identical to paper-original CellOT, but the biological claim is different, so the name needs to be different. (`IMPACT` here is a label, not a known acronym — TODO: confirm with mentor whether it stands for something.)

### 1.4 scGen — the baseline

| | |
|---|---|
| **Architecture** | Variational autoencoder |
| **How it predicts a perturbation** | Compute δ = mean(latent_target) − mean(latent_source) on training cells. For a new source cell, return `decode(encode(cell) + δ)`. |
| **Reference** | [Lotfollahi et al. — `reference_papers/scGen.pdf`](../reference_papers/scGen.pdf) |

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

| Use site | Convention | Examples |
|---|---|---|
| Code identifiers (path components, dict keys, CLI flags, variable names) | lowercase + underscore | `impact_cellot`, `scgen` |
| Display labels (figure legends, tables, prose) | preserved capitalization | `IMPACT_CellOT`, `scGen` |

### 2.1 Alias history — translation table for old names

The repo has accumulated several alias names for the same three model families across different project phases. This table maps **every alias** to the current canonical name. Source of truth: the `ALIAS_TABLE` in `scripts/build_experiments_inventory.py`.

| Canonical family | Aliases seen in old paths, configs, and filenames |
|---|---|
| **scGen** (current name: `scgen`) | `scgen`, `speciesot_scgen`, "autoencoder" (informal) |
| **IMPACT_CellOT** (current name: `impact_cellot`) | `impact`, `impact_or`, `swapped_cellot`, `speciesot_cellot` |
| **CellOT (abandoned cell-type framing)** | `cellot` (in `speciesot_v1_iter2_*` or `toggle` phases), `speciesot_cellot_swapped`, `normal_cellot` |
| **CellOT (legacy crossspecies)** — raw 1000-dim ortholog space, no scGen | `cellot` (only in `legacy_crossspecies` phase, top-level `cross_species_ood/` and `race_*/` dirs) |

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
- **Drug effect**: not yet modeled. The first attempt is the **BCG line** (notebook `16_bcg_mouse_data_prep.ipynb`, `16.1_*`, `17_bcg_prediction.ipynb`). BCG is the tuberculosis vaccine, which has been administered to both mouse and human cohorts and has scRNA-seq data available — so it's a natural choice for a perturbation that exists in both species. So far the work in those notebooks is exploratory: data prep and initial inspection, no thorough modeling yet.
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

| Term | Lives in | Refers to |
|---|---|---|
| **`mode`** (`iid` or `ood`) | `generate_*_configs.py`, sbatch tags, results directory names like `hvg_seurat_d_iid/` | **What data was used to train** the model. `ood`: the held-out cell type was completely excluded from training. `iid`: the "ignored" half of the held-out cell type was added back into training. |
| **`--setting`** (`iid` or `ood`) | `evaluate.py` CLI flag | **Which slice of the dataset to evaluate on**. `iid`: the standard test split (random cells from in-training cell types). `ood`: the held-out cell type, test half. |

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

| Model | Natural space (loader's default) | To switch to other space, you must pass `--embedding ae` |
|---|---|---|
| IMPACT_CellOT (`ae_emb` in config) | latent (50-d) | yes, to get **data_space** |
| scGen (no `ae_emb` in config) | data (1000-d) | yes, to get **latent_space** |

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

| Model / setup | Eval space (verified by /X shape) | r | R² |
|---|---|---|---|
| IMPACT a_ood (aeflag) | gene (1000-d) | 0.929 | 0.86 |
| IMPACT a_iid (standard) | **latent (50-d)** | 0.880 | 0.77 |
| scGen a_ood (standard) | gene (1000-d) | 0.932 | 0.87 |

The IID model evaluated in latent space (0.77) is **lower** than the OOD model evaluated in gene space (0.86), which is the *opposite* of the in-sample-fit expectation — a clear sign the comparison is apples-to-oranges.

#### Implications for the matrix

- The 80 standard `eval_dataspace/` sbatches (from `scripts/generate_data_space_eval_sbatches.py`) **do not pass `--embedding ae`**, so their IMPACT_CellOT outputs are silently latent-space.
- The 10 hand-curated `eval_dataspace_aeflag/` sbatches and the 8 m2 sbatches (from `generate_hvg_flavor_configs.py --m2-two-flavors`) **do pass it** — those IMPACT_CellOT outputs are genuine gene-space.
- Standard-matrix R² heatmaps therefore compare **scGen-in-gene-space** against **IMPACT_CellOT-in-latent-space** — not directly comparable.

The IMPACT side of every standard `eval_dataspace/` IMPACT cell would need re-running with `--embedding ae` to produce a clean comparison. (Junyi 2026-05-27 confirmed re-running is deferred for now; the finding is documented so it isn't lost.)

#### The universal rule we adopt going forward

**Always pass `--embedding ae` for every eval**, with one exception: do NOT pass it for IMPACT_CellOT + `--where latent_space` (that combination triggers the column-count assertion at `evaluate.py:130` because predictions stay 50-d while ground truth gets reloaded to 1000-d). Since we generally don't run IMPACT_CellOT latent-space evals anyway, this caveat doesn't bite in practice.

The cookbook spec should encode this rule: an eval spec implies `--embedding ae` by default, and any invalid combination is rejected at spec-validation time rather than producing a wrong-space silent output.

#### Why this design is unfortunate — and why we happened to find it

`--where` and `--embedding` look like independent flags. They aren't — for AE-based models, `--where data_space` is silently a no-op unless `--embedding ae` is also passed. A correctly-designed CLI would either auto-detect (decode whenever an AE is in the config) or error loudly.

The upstream Bunne paper code *did* have an auto-detect mechanism at `evaluate.py` lines 274–278: if `embedding` is `None`, look for a sibling directory named `model-cellot` and infer the embedding from its config. In the upstream paper's directory layout, the canonical cellot model was named `model-cellot/`, so when the user evaluated a sibling baseline (scgen/, identity/, random/, average/), the auto-detect propagated cellot's embedding choice to the baseline eval — *masking* this bug in practice.

**Our project disabled that auto-detect by accident**: we named the cellot model `impact_cellot/` (deliberately, to signal IMPACT framing per §1.3 / §2 of this doc) instead of `model-cellot/`. With no `model-cellot/` sibling to read, the auto-detect at line 275 never fires, `embedding` stays `None`, and both bugs become visible.

So the bug isn't a defect we introduced — it was latent in the upstream design, *masked* by the upstream naming convention. Our naming improvement (which has its own good reasons) is what surfaced it. The proper fix is to make the dependency explicit in the sbatch and in the spec, not to revert the naming. Or, as a one-line-per-experiment workaround, we could add `ln -s impact_cellot model-cellot` in each experiment dir to re-enable the auto-detect; this is a quick fix for the existing 80 sbatches but not the right long-term answer.

### 5.6 The latent-space-vs-data-space evaluation choice

CellOT's natural output space is the **latent** space defined by an autoencoder it's trained against. Evaluations can be done in latent space (cheaper, smoother) or by decoding back to **data space** (gene expression — harder, but biologically interpretable). Older runs evaluated in latent space for stale data and data space for renorm data, possibly for historical reasons. *Junyi flagged this as a choice he can no longer fully reconstruct — worth re-examining when revisiting `08.1`.*

---

## 6. Open questions / things this doc should eventually answer

- Does `IMPACT` stand for something specific, or is it just a label?
- What is the formal definition of `T_drug'` that we are trying to predict? (Pointwise? Distributional? On the population mean?)
- For BCG: are the mouse-BCG and human-BCG datasets at comparable cell-type resolution and timepoint? (Critical for whether `T_drug` learned on mouse can plausibly apply to human.)
- For the renorm-vs-stale evaluation-space asymmetry: was there a methodological reason or just a historical accident? `08.1` revisit needed.

---

## References

- Bunne et al., *Learning single-cell perturbation responses using neural optimal transport*, Nature Methods, 2023. ([`reference_papers/Bunne et al - 2023.pdf`](../reference_papers/Bunne%20et%20al%20-%202023.pdf))
- Lotfollahi et al., *scGen predicts single-cell perturbation responses*, Nature Methods, 2019. ([`reference_papers/scGen.pdf`](../reference_papers/scGen.pdf))
- Karpathy, [autoresearch](https://github.com/karpathy/autoresearch) — the conceptual inspiration for the (now-deleted) `autospeciesOT/` experiment-orchestrator and a candidate framework for future overnight architecture-search work.

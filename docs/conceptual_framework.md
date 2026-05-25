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
| **OOD generalization tested along** | Predict CD8 from a never-before-seen non-CD8 cell |

We tried this framing in early experiments. It was abandoned for two reasons:

1. **Huge size imbalance.** Non-CD8 vastly outnumbers CD8 in any atlas dataset. OT can still solve this mathematically, but with ICNN-based *deterministic* maps it forces a many-to-one squash from the large source cloud to the small target cloud, which is not a meaningful biological statement (it isn't saying "this monocyte becomes that CD8 cell" — that's not how cell identity works).
2. **No coherent biological question.** Treating "the other cell types" as if they were the "control" version of CD8 cells doesn't correspond to any real intervention. Cell types are not perturbations of each other.

**Status:** dead. Any code or notebook references to this framing (likely tagged `cellot` in dict keys, or `paper_style` / `condition=cell_type` in old configs) are stale.

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

### 5.4 The latent-space-vs-data-space evaluation choice

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

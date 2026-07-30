# Mentor runbook — running the mouse→human species transport on your own data

Written for someone who has never opened this repository. You do not need the `./hub`
CLI, the spec system, or any of the training machinery. Everything below is CPU-only
and runs in minutes on a Cannon login node.

Repository root used throughout: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT`
(call it `$REPO`). **Every path in the scripts is hardcoded to the student's account —
see [§7](#7-paths-you-must-change) before you run anything.**

---

## 1. What the model does, and what it does not do

The trained model is a **species transport**. It takes a mouse cell and returns the
human cell it "would be". That is the only thing it does.

- Feed it **unvaccinated mouse** cells → you get **predicted unvaccinated human** cells.
- Feed it **vaccinated mouse** cells → you get **predicted vaccinated human** cells
  *only if* the vaccination signal survives the transport, which is exactly the thing
  we have not established. The model was never shown a treatment label.
- It **cannot** turn unvaccinated mouse into vaccinated human. That diagonal needs a
  drug-effect transport composed with the species transport, and **no drug-effect
  transport exists in this repository.**

### The four corners

```
                    T_drug  (learnable on mouse: PBS -> BCG)
   mouse_untreated ─────────────────────────────► mouse_treated
         │                                              │
    T_species  ◄── THIS IS THE ONLY LEG            T_species
         │          THAT IS IMPLEMENTED                 │
         ▼                                              ▼
   human_untreated ────────────────────────────► human_treated
                    T_drug' (not implemented)
```

Implemented and trained: the two vertical `T_species` arrows — the same map, applied
to whichever mouse cells you hand it. Not implemented: either horizontal arrow, and
therefore no route to `human_treated` from `mouse_untreated`.

The first experiment this runbook supports is deliberately the simple one, and it uses
**no new training**:

> Take BCG-study **unvaccinated mouse** cells → run them through the existing atlas
> model → compare the predicted human cells against the **real unvaccinated human**
> cells from the same study.

That is an external validation of the species leg alone. The vaccination axis plays no
part in it: the same condition (unvaccinated) sits on both sides.

### The two model families

Both are trained on the same Tabula human–mouse atlas, both operate inside a shared
autoencoder (AE) latent space, and predictions come out of the AE decoder:

| family | what it is |
|---|---|
| `scgen` | baseline: a constant mouse→human shift applied to the latent code |
| `impact_cellot` | the main model: a neural optimal-transport map on the latent code |

Each exists in two gene-selection flavors (`seurat_v3`, `pearson_residuals`), so a run
produces **four** predictions. `impact_cellot` + `pearson_residuals` is the usual
headline pairing.

---

## 2. Before you start

**Two conda environments.** They are not interchangeable.

| env | used for | why |
|---|---|---|
| `analysis` | gene mapping / preprocessing (step 2 below) | needs `scanpy >= 1.12` |
| `CellOT` | everything that touches a trained model (steps 2–4) | has the `torch` build the checkpoints were saved with |

`scripts/predict_new_input.sh` switches between them for you by calling each
interpreter by absolute path. The evaluation script in step 4 you run yourself in
`CellOT`.

**Trained models.** All four deployment checkpoints are already on disk and are the
ones to use for external prediction, because they were trained on *all* atlas cells
with no holdout:

```
$REPO/cellot/cellot_gpu/results/atlas_full_{seurat_v3,pearson_residuals}/{scgen,impact_cellot}/cache/model.pt
```

(The `*_v08_ood` models elsewhere in the tree deliberately withhold a cell type — they
are benchmark models, not deployment models. Do not use them here.)

### Input file requirements (mouse)

Carried over from the header of `scripts/predict_new_input.sh`:

- An **AnnData `.h5ad`** containing mouse cells.
- **Raw integer counts.** Preferred location is `.layers['counts']`; if that layer is
  absent, `.X` is used and **must itself be raw integer counts**. The script asserts
  integrality on the first 50 cells and aborts otherwise. Do not hand it
  log-normalized or scaled data — normalization happens inside the script.
- **Gene names in `.var_names`**, either mouse Ensembl IDs (`ENSMUSG…`) or gene
  symbols. Symbols are resolved through the cached table
  `scripts/.bcg_symbol_to_ensmusg.csv`; if a symbol is not in that cache it is silently
  dropped, so prefer `ENSMUSG…` IDs when you have them.
- Anything else in `.obs` is optional; the script keeps `condition`, `species`,
  `cell_type`, `study`, `_scvi_batch` if present and discards the rest.

**One file per condition.** The script does not split by metadata. If your BCG mouse
object contains both PBS and BCG cells, subset it to the unvaccinated cells first and
write that subset out as its own `.h5ad`.

### Input file requirements (human ground truth)

The human target must end up on the **same 1,000-gene axis** as the prediction:
human Ensembl IDs (`ENSG…`), in the atlas order, log1p(CP10k)-normalized. See
[§3, step 3](#step-3-put-the-human-ground-truth-on-the-same-gene-axis-analysis-env--cellot-env-1-min)
— this is the one piece of the path that is not yet wrapped in a script.

---

## 3. The external validation, step by step

### Step 1 — prepare two input files (your own tooling, minutes)

Write out, as separate `.h5ad` files with raw counts:

- `bcg_mouse_unvax.h5ad` — the unvaccinated (PBS) mouse cells
- the unvaccinated human cells from the same study (used in step 3)

### Step 2 — predict human cells from the mouse cells (`CellOT` + `analysis`, ~3 min, CPU)

```bash
cd /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT
bash scripts/predict_new_input.sh /path/to/bcg_mouse_unvax.h5ad bcg_unvax
```

The second argument is a tag used to name the outputs. This script activates both
environments itself; you do not need to `conda activate` anything.

What it does: maps mouse genes → human orthologs via the cached BioMart table,
projects onto each atlas HVG list (genes with no ortholog are filled with zeros — the
printed **coverage** line tells you how many of the 1,000 genes were actually found),
log1p(CP10k)-normalizes, then runs all four trained models.

It writes, into
`$REPO/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/`:

```
bcg_unvax_aligned_{seurat_v3,pearson_residuals}_v07.h5ad          # the mouse input, atlas-aligned
bcg_unvax_predicted_human_via_{scgen,impact_cellot}_{seurat_v3,pearson_residuals}.h5ad
```

**Check the coverage line before going further.** If coverage is far below ~80% of
1,000 genes, the remaining genes are zeros and every downstream number is degraded.

### Step 3 — put the human ground truth on the same gene axis (`analysis` env → `CellOT` env, ~1 min)

`predict_new_input.sh` is mouse-only: it does the ortholog hop. A human file needs the
same treatment **minus** the ortholog step, because the shared axis already *is* human
Ensembl. There is no script for this yet; this is the snippet, and it is the one step
of this path that has never been run end to end.

```bash
conda activate analysis
python - <<'PY'
import anndata as ad, numpy as np, pandas as pd, scanpy as sc, scipy.sparse as sp

ATLAS = ("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/datasets/"
         "speciesot-human-mouse-hvg/hvg_{flavor}_atlas_full_v07.h5ad")
SRC   = "/path/to/bcg_human_unvax.h5ad"     # raw counts, ENSG in .var_names
OUT   = ("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/datasets/"
         "speciesot-human-mouse-hvg/bcg_unvax_human_target_{flavor}.h5ad")

src = ad.read_h5ad(SRC)
if "counts" in src.layers:
    src.X = src.layers["counts"].astype("float32")
xs = src.X[:50].toarray().ravel() if sp.issparse(src.X) else np.asarray(src.X[:50]).ravel()
assert np.allclose(xs, np.round(xs)), "human target must be raw integer counts"

X = src.X.toarray() if sp.issparse(src.X) else np.asarray(src.X)
pos = {str(g): i for i, g in enumerate(src.var_names)}

for flavor in ("seurat_v3", "pearson_residuals"):
    genes = [str(g) for g in ad.read_h5ad(ATLAS.format(flavor=flavor)).var_names]
    Xn = np.zeros((src.n_obs, len(genes)), dtype="float32")
    hit = 0
    for j, g in enumerate(genes):
        i = pos.get(g)
        if i is not None:
            Xn[:, j] = X[:, i]; hit += 1
    a = ad.AnnData(X=Xn, obs=pd.DataFrame(index=src.obs_names),
                   var=pd.DataFrame(index=pd.Index(genes, name="ensg")))
    sc.pp.normalize_total(a, target_sum=1e4); sc.pp.log1p(a)
    a.write_h5ad(OUT.format(flavor=flavor))
    print(f"{flavor}: coverage {hit}/{len(genes)} -> {OUT.format(flavor=flavor)}")
PY
```

Then round-trip each output through the older AnnData format the `CellOT` env reads,
exactly as `predict_new_input.sh` phase 2 does for the mouse side:

```bash
conda activate CellOT
python - <<'PY'
import anndata as ad
base = ("/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/datasets/"
        "speciesot-human-mouse-hvg/bcg_unvax_human_target_{flavor}.h5ad")
for flavor in ("seurat_v3", "pearson_residuals"):
    p = base.format(flavor=flavor)
    try:
        print(flavor, ad.read_h5ad(p).shape, "readable as-is")
    except Exception as e:
        print(flavor, "NOT readable in CellOT env:", e)
        print("  re-save it with the phase-2 converter in scripts/predict_new_input.sh")
PY
```

If a file is not readable, copy the phase-2 block out of `scripts/predict_new_input.sh`
(lines ~158–215) and point it at these files.

### Step 4 — score the prediction against the real human cells (`CellOT` env, ~2–5 min, CPU)

```bash
cd /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT
conda activate CellOT

D=cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg
python scripts/eval_external_target.py \
  --pred   $D/bcg_unvax_predicted_human_via_impact_cellot_pearson_residuals.h5ad \
  --target $D/bcg_unvax_human_target_pearson_residuals.h5ad \
  --source $D/bcg_unvax_aligned_pearson_residuals_v07.h5ad \
  --aedir  cellot/cellot_gpu/results/atlas_full_pearson_residuals/model-scgen \
  --tag    bcg_unvax_impact_pearson
```

The three clouds are: what the model predicted, what the human cells really are, and
what went in. `--aedir` must be the autoencoder belonging to the **same flavor** as the
prediction (`atlas_full_seurat_v3/model-scgen` for the `seurat_v3` predictions).

Results are written to
`results/external_eval/<tag>/external_target_metrics.{csv,json}` and printed to the
terminal.

Repeat for the other three prediction files to compare the two model families and the
two gene flavors.

### Step 5 — read the output

See §4. Nothing else needs to be run.

---

## 4. How to tell if it worked

The metrics compare three distributions of cells, all measured in the **decoded
frame** — that is, against references that have themselves been pushed through the
autoencoder, so the comparison is like-for-like with the model's output.

| quantity | meaning |
|---|---|
| `mmd_ae_recon_floor` | **floor**: the distance you get from a perfect prediction. Reconstructing the real human cells through the AE and comparing them to themselves. Nothing can beat this. |
| `mmd_decoded_ceiling` | **ceiling**: the distance if you do no transport at all — the mouse cells, AE-reconstructed, compared to real human. |
| `mmd_model` | what your prediction actually scored. Should land between the two. |
| `model_over_floor` | `mmd_model / floor`. **The number to trust.** |
| `frac_gap_closed_decoded` | fraction of the ceiling→floor distance the model covered. 1.0 = perfect, 0.0 = no better than doing nothing, negative = worse than doing nothing. |
| `decoded_denominator` | `ceiling − floor`, the length of the ruler. Read this *before* the fraction. |

### What good and bad look like

**`model_over_floor`** (1.0 = indistinguishable from a perfect prediction):

| value | reading |
|---|---|
| 1.0 – 1.5 | good — this is where the atlas benchmark models sit (1.29 for the reference run below) |
| 1.5 – 2.5 | mediocre; the prediction is recognizably off-distribution |
| > 3 | bad — for scale, doing *nothing* scores 3.8 on the atlas benchmark |

**`frac_gap_closed_decoded`**:

| value | reading |
|---|---|
| > 0.8 | strong |
| 0.4 – 0.8 | partial |
| ≈ 0 | the transport bought you nothing over leaving the mouse cells alone |
| < 0 | the transport moved the cells *away* from human |

**Guardrails**, printed alongside:

- `r2_model_dec` — did the average expression profile come out right? On the atlas
  benchmark this is ≈0.92 all-genes and ≈0.72 on the top-50 marker set. Its companion
  `frac_r2_closed_decoded` is 0 when the prediction is no better than the mouse input
  and 1 when it matches the best achievable.
- `mean_js` — per-gene Jensen–Shannon divergence, the metric to quote when the
  question is phrased in KL terms. Lower is better, but **only read it against the two
  reference values printed beside it** (`mean_js_ae_floor` and
  `mean_js_identity_decoded`); the absolute number is not meaningful on its own.

### The warning that matters most

**A gap-closed fraction computed on a small denominator is unreliable.** The fraction
divides by `decoded_denominator`. Ordinary run-to-run noise in the MMD estimate is
about ±0.005, so the fraction wobbles by `0.005 / denominator` — the script prints this
number for you. On the atlas the denominator is ~0.225, so the wobble is ±0.02 and the
fraction is trustworthy. On a cut where the denominator falls to ~0.02, the same noise
moves the fraction by ±0.23 and it carries **one usable digit at best**; the script
labels that case `ill_conditioned`.

Two further rules from `docs/conceptual_framework.md` §5.9:

1. **Never rank two models on the fraction when their floors differ.** The floor is a
   property of the model's own autoencoder, so different models are being graded with
   different-length rulers. Rank on `mmd_model`, `gap_above_ae_recon`, and
   `model_over_floor` instead.
2. **Always quote the fraction together with the denominator and `model_over_floor`.**
   The script prints all three every time, so quote what it prints.

### Reference numbers (what a working run looks like)

From the frozen atlas benchmark — held-out monocytes, `pearson_residuals`,
`impact_cellot`, at `ncells=80`. This is not the BCG experiment; it is the yardstick
for what "healthy" looks like:

| | model | AE-decoded no-transport null |
|---|---:|---:|
| `mmd_model` | 0.104 | 0.306 |
| `mmd_ae_recon_floor` | 0.080 | 0.080 |
| `mmd_decoded_ceiling` | 0.306 | 0.306 |
| `decoded_denominator` | 0.225 | 0.225 |
| `model_over_floor` | **1.29** | 3.80 |
| `frac_gap_closed_decoded` | **0.897** | 0.000 |
| `r2_model_dec` (all genes) | 0.922 | 0.578 |
| `frac_r2_closed_decoded` | 0.821 | 0.000 |

Expect the BCG numbers to be **worse than this**. The atlas benchmark holds out a cell
type from the same tissue atlas the model was trained on; the BCG study is a different
lab, a different protocol, and a different tissue context.

---

## 5. Known caveats

- **The deployment models are v07-era, built before the assay filter was enforced.**
  The `atlas_full_*` checkpoints were trained on data that still mixes sequencing
  platforms within each species — in particular Smart-seq2 cells alongside 10x. We
  later established that the Smart-seq2 minority has a very different expression
  distribution, that it accounts for most of the apparent within-species scatter, and
  that it **inflates MMD**; the filter (mouse `10x 3' v2`, human `10x 3' v3`) is now
  enforced in the data-prep path. See `docs/hub_usage.md` (prep step 2) and
  `docs/conceptual_framework.md` §5.10. **Rebuilding `atlas_full` at v08 and retraining
  is recommended before any headline claim** rests on these numbers. Everything you get
  today is directionally useful and provisional.
- **Genes with no mouse→human ortholog become zeros.** Coverage is printed in step 2.
  Low coverage silently drags the prediction toward zero for the missing genes.
- **The metrics are subsampled.** MMD is computed on 30/50/80 cells at a time, averaged
  over 10 repeats. Values are only comparable at equal `ncells`; the headline is 80.
  If your target has fewer than 80 cells, the script skips that size and warns.
- **The prediction must be an AE-decoded model output.** The decoded floor and ceiling
  only grade decoded predictions. If you pass a raw cell-by-gene matrix as `--pred`,
  the fraction becomes meaningless (it looks *better* than it is). The script detects
  this by the fraction of exact zeros and warns, but the warning is a heuristic.
- **`mean_js` inherits the same frame issue** — it compares a decoded prediction to a
  raw target, so its absolute value is dominated by the AE round-trip, not by model
  quality. Only the comparison against `mean_js_ae_floor` and
  `mean_js_identity_decoded` is informative.
- **No drug-effect transport exists.** Any statement about vaccinated human cells is
  outside what this repository can currently produce.

---

## 6. What is not yet verified

- The step-3 human-alignment snippet has **not** been executed against real human BCG
  data. The raw human BCG counts (GEO `GSE248728`, 14 10x capture matrices) sit under
  `/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/tb/data/human_bcg/`, but no
  assembled `.h5ad` exists and there is no per-capture vaccinated/unvaccinated
  assignment on disk. Building that object, with condition labels, is the prerequisite
  for the whole experiment.
- `scripts/eval_external_target.py` has been validated end to end on atlas cells used
  as a stand-in external dataset, where it reproduces the existing benchmark sidecar to
  eight significant figures, returns exactly 0.0 for a no-transport null, and correctly
  flags a raw-frame prediction. It has not been run on BCG data.

---

## 7. Paths you must change

These are literal absolute paths, not environment variables. Editing them is required
if you run outside the student's account.

| file | what to change |
|---|---|
| `scripts/predict_new_input.sh`, lines 36–38 | `BASE` (repo root), `ANALYSIS_PY`, `CELLOT_PY` (absolute interpreter paths for the two conda envs) |
| `scripts/predict_new_input.sh`, lines ~72–73 | `ORTHO_CACHE` and `SYMBOL_CACHE` inside the phase-1 heredoc — both hardcode the repo root again |
| the step-3 snippet above | `ATLAS`, `SRC`, `OUT` |

`scripts/eval_external_target.py` needs **no** editing: it locates the repository from
its own file location and takes every other path as a command-line argument. If you
copy it elsewhere, pass `--cellot-dir <repo>/cellot/cellot_gpu`.

Find your own interpreter paths with:

```bash
conda activate analysis && which python
conda activate CellOT  && which python
```

# Mentor runbook — running the mouse→human species transport on your own data

Written for someone who has never opened this repository. You do not need the `./hub`
CLI, the spec system, or any of the training machinery. Everything below is CPU-only
and runs in minutes on a Cannon login node.

Repository root used throughout: `/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT`
(call it `$REPO`). The two scripts you run find their own paths; only the inline
snippet in step 3 still hardcodes anything — see [§7](#7-paths-you-must-change).

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

Each exists in two gene-selection flavors, so a run produces **four** predictions.
`impact_cellot` + `pearson_residuals` is the usual headline pairing.

### The model sets

`predict_new_input.sh --model-set NAME` chooses which trained set to use. Each set has
its own flavors and, critically, its own 1,000-gene axis per flavor:

| `--model-set` | flavors | trained on |
|---|---|---|
| `atlas_full_v07` (default) | `seurat_v3`, `pearson_residuals` | the May-8 atlas cut, before the assay filter |
| `uncapped_v08` | `pearson_residuals`, `mixhvg` | the v08 assay-filtered atlas, ordinary `train_test` (no type holdout). Use when `results/hvg_{flavor}_uncapped_v08/*/cache/model.pt` exist |
| `uncapped_v08_iid` | `pearson_residuals`, `mixhvg` | the v08 assay-filtered atlas cut (toggle_ood-iid twins; interim until `uncapped_v08` finishes) |

**The gene axes are not interchangeable.** `hvg_pearson_residuals_atlas_full_v07.h5ad`
and `hvg_pearson_residuals_a_uncapped_v08.h5ad` are both 1,000 genes but share only
721 of them, so feeding one set's cells to the other set's checkpoint would not raise
an error — the vector positions would simply mean different genes and the prediction
would be quietly wrong. The script's phase 0 compares the axis it is about to project
onto against each checkpoint's own axis and aborts before writing anything if they
disagree. The axis of record is `results/<tag>/genes.txt` when that file exists
(see [§2](#what-you-actually-have-to-copy)), because it lives inside the
checkpoint's own directory and therefore cannot be crossed with another model set's
axis; otherwise it is the training `.h5ad` named in `config.data.path`.

---

## 2. Before you start

**Two conda environments.** They are not interchangeable.

| env | used for | why |
|---|---|---|
| `analysis` | gene mapping / preprocessing (step 2 below) | needs `scanpy >= 1.12` |
| `CellOT` | everything that touches a trained model (steps 2–4) | has the `torch` build the checkpoints were saved with |

`scripts/predict_new_input.sh` switches between them for you: it probes your own conda
install (`$HOME/miniforge3`, `$HOME/.conda`, `$HOME/miniconda3`, `$HOME/anaconda3`,
`$HOME/mambaforge`) for each env and falls back to the original author's absolute paths.
Override with `SPECIESOT_ANALYSIS_PY` / `SPECIESOT_CELLOT_PY` if it guesses wrong. The
evaluation script in step 4 you run yourself in `CellOT`.

**A third env, `CellOT_v3`, is available and is the easier one if you are starting
fresh** (python 3.11, anndata 0.10.9, torch 2.3.1). Unlike `CellOT` (anndata 0.7.6) it
reads **both** old and modern `.h5ad` files, which removes the whole
anndata-version dance in step 3. Select it with:

```bash
SPECIESOT_CELLOT_ENV=CellOT_v3 bash scripts/predict_new_input.sh ...
```

It was validated numerically against `CellOT`: predictions agree to 8.3e-07 (scGen) and
4.8e-06 (IMPACT), the scGen shift is bit-identical, and on the synthetic smoke test all
four predictions came out bit-identical between the two envs. `CellOT` remains the
default, and the script's phase-2 round-trip still runs under either env because the
legacy env needs it.

**Trained models.** All four deployment checkpoints are already on disk and are the
ones to use for external prediction, because they were trained on *all* atlas cells
with no holdout:

```
$REPO/cellot/cellot_gpu/results/atlas_full_{seurat_v3,pearson_residuals}/{scgen,impact_cellot}/cache/model.pt
```

The `uncapped_v08_iid` set is the v08 successor, at

```
$REPO/cellot/cellot_gpu/results/hvg_{pearson_residuals,mixhvg}_a_uncapped_v08_iid/{scgen,impact_cellot}/cache/model.pt
```

(The `*_v08_ood` models elsewhere in the tree deliberately withhold a cell type — they
are benchmark models, not deployment models. Do not use them here. The `_iid` variants
above hold out no cell type, which is what makes them deployment models.)

### What you actually have to copy

**The atlas training datasets are no longer needed for prediction**, provided the model
set has its two baked sidecars. For `atlas_full_v07` — the default set — copy:

| path | size | what it is |
|---|---:|---|
| `results/atlas_full_{seurat_v3,pearson_residuals}/{scgen,impact_cellot}/cache/model.pt` | 17.4 MB | the four trained checkpoints |
| `results/atlas_full_{seurat_v3,pearson_residuals}/{scgen,impact_cellot}/config.yaml` | 3 KB | how to rebuild each network |
| `results/atlas_full_{seurat_v3,pearson_residuals}/genes.txt` | 32 KB | **sidecar** — the model's 1,000-gene axis, one id per line |
| `results/atlas_full_{seurat_v3,pearson_residuals}/scgen/cache/scgen_shift.pt` | 6 KB | **sidecar** — the scGen latent shift (`code_means`) plus provenance |
| `scripts/.biomart_ortholog_cache.csv`, `scripts/.bcg_symbol_to_ensmusg.csv` | 1.2 MB | mouse→human ortholog and symbol tables |
| `scripts/predict_new_input.sh`, `h5ad_to_v07.py`, `eval_external_target.py`, `bake_model_artifacts.py` | 74 KB | the scripts |

**Total: 18.7 MB.** Keep the directory layout — every path above is derived from the
repository root, and `model-scgen` is a symlink to `scgen` in each tag directory.

Without the sidecars the same handover also needs both training `.h5ad` files, which
is 70.4 MB for `atlas_full_v07` (2 × 35.2 MB, 8,610 cells) and would be 732 MB for the
`uncapped_v08_iid` set (2 × 366 MB, 89,760 cells).

**This covers prediction (step 2) only.** The scoring step (§3, step 4)
still needs the flavor's atlas `.h5ad`: `eval_external_target.py` builds its decoded
floor and ceiling through `load_projectors`, which calls the upstream loader and so
reads the AE's `config.data.path`. If all you want is predicted human cells, 18.7 MB is
enough. If you also want the metrics, add the 35.2 MB atlas file for each flavor you
score.

The two sidecars are written by

```bash
conda activate CellOT        # or CellOT_v3
cd /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT
python scripts/bake_model_artifacts.py --model-set atlas_full_v07
python scripts/bake_model_artifacts.py --model-set atlas_full_v07 --verify   # optional
```

It never touches `cache/model.pt`; it only adds files next to it. It needs the training
dataset **once**, at bake time. `--verify` recomputes both sidecars and reports
`max|diff|` against what is on disk.

| model set | sidecars present? |
|---|---|
| `atlas_full_v07` | **yes**, baked 2026-08-03 for both flavors |
| `uncapped_v08_iid` | no — bake it once its four checkpoints finish training |

`predict_new_input.sh` falls back to the original behaviour (read the atlas for the gene
axis, re-encode the training cells to recover the shift) whenever a sidecar is missing,
so an unbaked model set still works exactly as before — it just needs its dataset.

The sidecar records the sha256 of the gene axis it was computed against, and both phase 0
and phase 3 refuse to run if that does not match the axis actually in use. This matters:
a latent shift silently applied on the wrong gene axis is the same class of error phase 0
already existed to prevent.

### Input file requirements (mouse)

Carried over from the header of `scripts/predict_new_input.sh`:

- An **AnnData `.h5ad`** containing mouse cells.
- **Default (raw mouse):** integer counts in `.layers['counts']` (else `.X`), and
  mouse gene names (`ENSMUSG…` or symbols). The script asserts integrality and
  then does `normalize_total` + `log1p` itself. Do not log-normalize first.
- **scANVI posed files (`--posed-ensg`):** `.var_names` are already human `ENSG…`,
  and `.layers['counts']` is atlas-posed **count-scale** expression (continuous;
  not integers). Add `--posed-ensg`. The script skips the integer check and the
  mouse→human hop, then still does `normalize_total` + `log1p`. Do **not**
  log1p these files yourself. Do not pass `counts_original` as the main matrix
  if you mean the posed decode.
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
environments itself; you do not need to `conda activate` anything. Add
`--model-set uncapped_v08_iid` to use the v08 models instead of the default
`atlas_full_v07` pair (§1); non-default sets suffix their output filenames with the set
name so the two sets' files cannot be confused for each other.

What it does: maps mouse genes → human orthologs via the cached BioMart table,
projects onto each atlas HVG list (genes with no ortholog are filled with zeros — the
printed **coverage** line tells you how many of the 1,000 genes were actually found),
log1p(CP10k)-normalizes, then runs all four trained models.

When the sidecars are present the run never opens an atlas `.h5ad`: phase 1 prints
`gene axis from .../genes.txt` and phase 3 prints `latent shift from scgen_shift.pt`.
If instead you see `gene axis from .../hvg_*.h5ad` and `recomputing the latent shift`,
the sidecars are missing for that model set and the training dataset is being read —
correct, but not the light-handover path.

It writes, into
`$REPO/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/`:

```
bcg_unvax_aligned_{flavor}.h5ad              # mouse input on the model gene axis
bcg_unvax_aligned_{flavor}_anndata07.h5ad    # same matrix, anndata 0.7 format (not model v07)
bcg_unvax_predicted_human_via_{scgen,impact_cellot}_{flavor}.h5ad
```

**Check the coverage line before going further.** If coverage is far below ~80% of
1,000 genes, the remaining genes are zeros and every downstream number is degraded.

### Step 3 — put the human ground truth on the same gene axis (`analysis` env → `CellOT` env, ~1 min)

`predict_new_input.sh` is mouse-only: it does the ortholog hop. A human file needs the
same treatment **minus** the ortholog step, because the shared axis already *is* human
Ensembl. There is no script for this yet; this is the snippet.

**Watch the coverage number it prints.** Both this snippet and
`predict_new_input.sh` silently fill missing genes with zeros. A run reporting
`coverage 201/1000` means 80% of the model's input was zeros — it will still produce
output, and that output will be meaningless. Anything below roughly 80% coverage
should be treated as a data-preparation problem, not a modelling result.

```bash
conda activate analysis
python - <<'PY'
import anndata as ad, numpy as np, os, pandas as pd, scanpy as sc, scipy.sparse as sp

REPO  = "/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT"
GENES = REPO + "/cellot/cellot_gpu/results/atlas_full_{flavor}/genes.txt"   # sidecar
ATLAS = (REPO + "/cellot/cellot_gpu/datasets/"
         "speciesot-human-mouse-hvg/hvg_{flavor}_atlas_full_v07.h5ad")      # fallback
SRC   = "/path/to/bcg_human_unvax.h5ad"     # raw counts, ENSG in .var_names
OUT   = (REPO + "/cellot/cellot_gpu/datasets/"
         "speciesot-human-mouse-hvg/bcg_unvax_human_target_{flavor}.h5ad")

src = ad.read_h5ad(SRC)
if "counts" in src.layers:
    src.X = src.layers["counts"].astype("float32")
xs = src.X[:50].toarray().ravel() if sp.issparse(src.X) else np.asarray(src.X[:50]).ravel()
assert np.allclose(xs, np.round(xs)), "human target must be raw integer counts"

X = src.X.toarray() if sp.issparse(src.X) else np.asarray(src.X)
pos = {str(g): i for i, g in enumerate(src.var_names)}

for flavor in ("seurat_v3", "pearson_residuals"):
    gpath = GENES.format(flavor=flavor)
    if os.path.exists(gpath):          # same axis the prediction was made on
        genes = [g for g in open(gpath).read().split("\n") if g]
    else:
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

**You must now convert each file to the older AnnData format**, and this is not
optional. The `CellOT` env runs anndata 0.7.6, which cannot read a file written by a
modern anndata; step 4 will abort with

```
AnnDataReadError: Above error raised while reading key '/layers' ...
```

This was hit during a real smoke test of this runbook, so expect it. There is a
converter for it — run it **in the CellOT env**, because the file has to be
*written* by anndata 0.7:

```bash
conda activate CellOT
cd /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT
D=cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg
for flavor in seurat_v3 pearson_residuals; do
  python scripts/h5ad_to_v07.py \
    $D/bcg_unvax_human_target_${flavor}.h5ad \
    $D/bcg_unvax_human_target_${flavor}_anndata07.h5ad
done
```

Pass the `_anndata07.h5ad` files to `--target` in step 4. That suffix is the
anndata 0.7 file format, not the `atlas_full_v07` model set.

`scripts/h5ad_to_v07.py` works on **any** `.h5ad` regardless of which anndata
wrote it, so use it whenever a file needs to cross between the two environments.
It reads the file with h5py — which is version-agnostic, since HDF5 is
self-describing — and rebuilds the object rather than relying on the anndata
reader. Note that simply deleting the offending `encoding-type` attributes does
*not* work: modern anndata also stores string columns as categorical groups,
which anndata 0.7 then misreads a second way. Verified to preserve `X`, layers,
categorical and numeric `obs`/`var` columns, and both indices exactly.

### Step 4 — score the prediction against the real human cells (`CellOT` env, ~2–5 min, CPU)

```bash
cd /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT
conda activate CellOT

D=cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg
python scripts/eval_external_target.py \
  --pred   $D/bcg_unvax_predicted_human_via_impact_cellot_pearson_residuals.h5ad \
  --target $D/bcg_unvax_human_target_pearson_residuals.h5ad \
  --source $D/bcg_unvax_aligned_pearson_residuals_anndata07.h5ad \
  --aedir  cellot/cellot_gpu/results/atlas_full_pearson_residuals/scgen \
  --tag    bcg_unvax_impact_pearson
```

The three clouds are: what the model predicted, what the human cells really are, and
what went in. `--aedir` must be the autoencoder belonging to the **same flavor** as the
prediction (`atlas_full_seurat_v3/scgen` for the `seurat_v3` predictions).

`--aedir` points at the **scgen** directory even when you are scoring an
IMPACT_CellOT prediction. The ICNN does not carry its own autoencoder — its
config declares `ae_emb.path: ./results/atlas_full_<flavor>/scgen/`, so both
model families decode through the same one.

`model-scgen` is a symlink to `scgen`, so either path works; `scgen` is used here
because it is the real directory. `load_projectors` needs only `<aedir>/config.yaml`
and `<aedir>/cache/model.pt`, both of which live there.

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

**Do not read the gap-closed fraction on its own — on garbage input it can look
respectable.** This is measured, not hypothetical. Feeding the pipeline synthetic
random counts (20% gene coverage, no biological signal at all) produced:

| model | flavor | `model_over_floor` | `frac_gap_closed_decoded` | `r2_model_dec` |
|---|---|---:|---:|---:|
| impact_cellot | pearson_residuals | 4.27 | **+0.52** | 0.17 |
| scgen | pearson_residuals | 9.34 | −0.23 | 0.22 |
| impact_cellot | seurat_v3 | 5.60 | +0.21 | 0.07 |
| scgen | seurat_v3 | 7.00 | −0.03 | 0.08 |

The first row is the cautionary one: a **52% gap-closed fraction on pure noise.** Across
the four runs the fraction swings from −0.23 to +0.52 on *identical* input, while
`model_over_floor` stays consistently terrible (4.3–9.3, against 1.29 for a healthy
run) and `r2_model_dec` stays near zero (against ~0.92).

So `model_over_floor` and `r2_model_dec` are the reliable discriminators. Treat the
gap-closed fraction as a summary to quote, never as the thing you judge by.

**A gap-closed fraction computed on a small denominator is also unreliable.** The fraction
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

- **The full chain HAS been smoke-tested** (2026-07-30) on synthetic mouse counts built
  from real ortholog-cache gene IDs. All three steps ran: `predict_new_input.sh` in 35 s
  producing four predictions, and `eval_external_target.py` in ~20 s for each of the
  four model × flavor combinations. The gene axis assertions, AE loading, floor/ceiling
  construction and sidecar writing all work, and the metrics correctly identified the
  synthetic input as meaningless. Two defects found in that run — the anndata-version
  conversion in step 3, and the silent zero-fill on low coverage — are now documented
  above.
- **`--model-set atlas_full_v07` (the default) is verified** (2026-08-03) to produce
  bit-identical predictions to the pre-`--model-set` version of the script, on the same
  synthetic input, for all four model × flavor combinations, with the same coverage and
  the same output filenames. Verified under both `CellOT` and `CellOT_v3`, which also
  agreed bit-identically with each other.
- **The baked sidecars are verified to change nothing numerically** (2026-08-03). On 400
  synthetic mouse cells built from real ortholog-cache `ENSMUSG` ids (100% coverage on
  both axes), `--model-set atlas_full_v07` was run three ways — with the sidecars, with
  them hidden behind a symlinked tree so the old code path ran, and in a tree containing
  **no atlas `.h5ad` at all** — and all four predictions came out byte-identical in every
  pairing (`max|diff| = 0.0`, equal buffers), as did the phase-1 aligned inputs. The
  guards were exercised too: a `genes.txt` swapped to the other flavor's axis, a
  `genes.txt` disagreeing with a present atlas file, and a `scgen_shift.pt` from the
  wrong flavor each abort with nothing written. Wall clock is unchanged — the step
  removed (re-encoding 6,888 training cells) costs 0.3–3.4 s per flavor against ~23–34 s
  total run-to-run scatter on a shared login node, so the win here is handover size, not
  speed. On a 89,760-cell set such as `uncapped_v08_iid` the removed step is roughly ten
  times larger.
- **`uncapped_v08_iid` has no sidecars yet** — its checkpoints were still training. Once
  they finish, `python scripts/bake_model_artifacts.py --model-set uncapped_v08_iid`
  bakes them; nothing else changes.
- **`eval_external_target.py` has not been made dataset-free.** Only prediction has. Its
  `load_projectors` call still reads the AE's `config.data.path`, so scoring needs the
  atlas file. Teaching `patch_scgen_shift` to read `scgen_shift.pt` would close that
  gap; it has not been attempted.
- **`--model-set uncapped_v08_iid` has NOT been run end to end.** Its `scgen` halves were
  still training and its `impact_cellot` halves had not started when this was written, so
  the script correctly refuses the set on the missing-checkpoint check. What *is* verified
  for it: the phase-0 axis binding for all four (flavor, model) pairs against the real
  `config.yaml` files, and the phase-1 projection onto both v08 axes (coverage 200/1000
  and 201/1000 on the synthetic input). Phase 3 — actually loading those checkpoints and
  predicting — is untested. Re-run `bash scripts/predict_new_input.sh --model-set
  uncapped_v08_iid <input.h5ad> <tag>` once training finishes.
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

Only one thing in this runbook still needs editing:

| file | what to change |
|---|---|
| the step-3 snippet above | `REPO` and `SRC` (`GENES`, `ATLAS`, `OUT` derive from `REPO`) |

`scripts/predict_new_input.sh` and `scripts/bake_model_artifacts.py` need **no** editing. It derives the repo root from its
own location and derives the ortholog/symbol cache paths from that, so a clone anywhere
works. Environment variables cover the rest:

| variable | effect |
|---|---|
| `SPECIESOT_ROOT` | repo root, for the case where the code and the results tree live apart |
| `SPECIESOT_ANALYSIS_PY` | interpreter for the `analysis` env |
| `SPECIESOT_CELLOT_PY` | interpreter for the model env |
| `SPECIESOT_CELLOT_ENV` | conda env *name* for the model env; default `CellOT`, set to `CellOT_v3` for the modern stack |

`scripts/eval_external_target.py` needs no editing either: it locates the repository
from its own file location and takes every other path as a command-line argument. If you
copy it elsewhere, pass `--cellot-dir <repo>/cellot/cellot_gpu`.

The script prints the paths it resolved in its header, so check that block before
trusting a run:

```
=== predict_new_input.sh ===
  input:      /path/to/mouse.h5ad
  tag:        my_tag
  model set:  atlas_full_v07  (flavors: seurat_v3 pearson_residuals)
  base:       /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT
  analysis:   /n/home01/.../envs/analysis/bin/python
  model env:  /n/home01/.../envs/CellOT/bin/python
```

Find your own interpreter paths with:

```bash
conda activate analysis && which python
conda activate CellOT  && which python
```

# speciesOT — experiments inventory

Companion to `experiments_inventory.csv`. One row per trained model artifact
(a `cache/` directory plus a `config.yaml`). 81 rows total, covering every
training run that has ever produced a `cache/status` file under
`cellot/cellot/results/` or `cellot/cellot_gpu/results/`, plus the one empty
placeholder directory we never trained.

The CSV is regenerated from disk by:

```bash
cd /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT
python scripts/build_experiments_inventory.py
```

The script reads `config.yaml`, `cache/status`, and `cache/last.pt` mtimes
from disk for each entry in its `CATALOG`, so the structural metadata
(dataset path, holdout, n_iters, etc.) is parsed live and stays accurate.
Only the editorial fields — `project_phase`, `group_label`, `notes`,
`analysis_notebooks`, `train_sbatch`, `eval_sbatch` — are hand-curated.

---

## What's in the CSV (the seven phases)

| Phase                          | Rows | Window         | What it is |
|--------------------------------|-----:|----------------|------------|
| `legacy_crossspecies_cpu`      |    2 | Mar 7 – 13     | First fork at `cellot/cellot/`. Public 4-species LPS6 dataset, rat held out. CellOT done; scGen cancelled mid-run after eval-loss converged. |
| `legacy_crossspecies_gpu`      |    3 | Mar 10 – 15    | GPU fork at `cellot/cellot_gpu/`. Includes one `never_started` placeholder (`cross_species_ood_cellot_gpu/` — empty directory). |
| `racing`                       |    2 | Mar 15         | 10k-iter CellOT race comparing CPU `shared` vs `gpu_requeue` partitions. |
| `speciesot_v1_iter1`           |    2 | Mar 18         | The original `speciesot_cpu/` — broad T-cell (`CL:0000084`) holdout. **Transport direction was reversed (human → mouse).** Flagged in notes. |
| `speciesot_v1_iter2_groupA` …D |   12 | Mar 25 – Apr 5 | The "Group A/B/C/D" experiments: CD8 / CD8-no-thymo / All-T-subtypes / CD4. Each = 1 scGen + 1 IMPACT + 1 CellOT. |
| `toggle`                       |   48 | Apr 9          | The toggle_ood matrix: 8 holdout groups (T1–T4, M1–M4) × 2 modes (iid / ood) × 3 models (scGen, IMPACT, CellOT). |
| `renorm`                       |   12 | Apr 21         | Same Groups A–D, rebuilt on the renormalized pipeline after the Apr-20 preprocessing audit. |

**Total = 81 rows.** This matches `find cellot -name config.yaml | wc -l` (= 80 configs that exist) plus the one empty placeholder.

---

## The columns

| Column                    | What it tells you |
|---------------------------|-------------------|
| `exp_id`                  | Stable identifier (`E001`–`E081`). Useful for referencing a row. |
| `train_finished`          | `cache/last.pt` mtime — best proxy for when training ended. |
| `project_phase`           | Which of the seven eras above the run belongs to. |
| `group_label`             | Human-readable holdout description (e.g. "Group A: CD8+ T cell holdout (CL:0000625)"). |
| `mode`                    | `iid` / `ood` / blank. Only populated for toggle_ood-style experiments. |
| `result_dir`              | Path to the model directory, relative to the project root. |
| `model_family`            | Canonical family — **scGen / IMPACT / CellOT**. Use this column when grouping. |
| `model_dir_subname`       | The on-disk leaf directory name (the source of all naming confusion; see below). |
| `framing_alias`           | All the names this same architecture has been called over the project's life. |
| `transport_direction`     | `source -> target` per the config. |
| `data_path`               | The h5ad file passed to training. |
| `ae_emb_path`             | For OT models: the scGen results dir whose encoder is reused. |
| `condition_var`           | Always `condition` so far; tracked in case it changes. |
| `source` / `target`       | The two values the OT model transports between. |
| `datasplit_name`          | `train_test` (legacy / Groups A–D / renorm) or `toggle_ood` (toggle / legacy crossspecies). |
| `holdout_key`             | `species` or `cell_type_ontology_term_id` (or `None` for autoencoder rows). |
| `holdout_value`           | The actual species or CL ID(s); CL ids are annotated with their human label. |
| `n_iters`                 | Configured training iterations (not necessarily completed — see `status`). |
| `batch_size`              | 128 for CellOT/IMPACT, 256 for scGen, 128 for the racing/legacy scGen. |
| `hidden_units`            | `[64,64,64,64]` for CellOT/IMPACT; `[256,256]` for scGen (renorm/groups); `[512,512]` for legacy scGen. |
| `latent_dim`              | Always 50 across the whole project. |
| `lr`                      | `1e-4` for OT models, `1e-3` for scGen. |
| `device`                  | `cuda` everywhere (the `cellot/cellot_gpu/` repo defaults that way; CPU jobs in `legacy_crossspecies_cpu` and `speciesot_v1_iter1` were also configured `cuda` and just fell back). |
| `status`                  | `done` / `running` (= cancelled mid-run) / `never_started`. |
| `evals_present`           | `data_space` / `latent_space` / `data+latent` / `none`. |
| `preprocessing_pipeline`  | `unrelated` (legacy public crossspecies) / `stale` (pre-Apr 20 mismatched-scale data) / `renorm` (post-Apr 20 fix). |
| `data_h5ad_format`        | The dataset family / version of the input h5ad (e.g. `…_v07.h5ad`, `…_renorm_v07.h5ad`). |
| `train_sbatch`            | The sbatch script that submitted this training. |
| `eval_sbatch`             | The sbatch script that produced the matching `evals_*` directory (when one was run). |
| `analysis_notebooks`      | Which `speciesOT/baseline/analysis/*.ipynb` notebooks consume this run. |
| `notes`                   | Free-form: framing rationale, known caveats, links to git-tracked mirror dirs, etc. |

---

## Naming chaos, decoded once

The **`model_family`** column is always the canonical answer. Use it for
filtering and grouping. The aliases below are kept in `framing_alias` so the
old names remain greppable, but you should not need to interpret them.

| Phase | scGen dir | IMPACT-OR (mouse → human, holdout = cell type) | CellOT (non_X → X, holdout = human) |
|-------|-----------|------------------------------------------------|---------------------------------------|
| Group A (`speciesot_cd8/`)             | `speciesot_scgen/` | `impact_or/`                | `cellot/`                |
| Groups B/C/D (`speciesot_*nothymo/cd4/tcell_subtypes/`) | `speciesot_scgen/` | `speciesot_cellot/`         | `speciesot_cellot_swapped/` |
| Toggle (`toggle_*_iid/ood/`)           | `scgen/`           | `impact/`                   | `cellot/`                |
| Renorm (`renorm_*/`)                   | `scgen/`           | `swapped_cellot/` ⚠         | `normal_cellot/`         |

⚠ **Important:** the directory name `swapped_cellot/` in the renorm phase
means **IMPACT-OR**, which is the OPPOSITE of what `speciesot_cellot_swapped/`
meant in Groups B/C/D. The two framings always mean the same thing
semantically; only the directory naming flipped. Every renorm row carries
this warning explicitly in its `notes` column.

The two framings, restated once for clarity:

- **IMPACT-OR (a.k.a. impact / impact_or / speciesot_cellot / swapped_cellot):**
  - `condition = species`
  - `source = mouse`, `target = human`
  - holdout is a cell type (e.g. `cell_type_ontology_term_id = CL:0000625`)
  - Reads: "given a mouse cell of held-out type X, predict its human counterpart."
- **CellOT, paper-style (a.k.a. cellot / speciesot_cellot_swapped / normal_cellot):**
  - `condition = cell_type_status` (an artificial label `non_X` vs `X`)
  - `source = non_X`, `target = X`
  - holdout is `species = human`
  - Reads: "given a human non-X cell, predict its X-state counterpart, having only seen mouse for the X transition."

---

## Status check

All 80 active runs report `done` in `cache/status`, except:

- **E002** `cellot/cellot/results/cross_species_ood_scgen` and
  **E004** `cellot/cellot_gpu/results/cross_species_ood_scgen_gpu` —
  status `running`. Both were cancelled by hand after eval-loss converged
  early; the `model.pt` checkpoints they produced are still good and were
  reused downstream. Documented in `research_log_2026-03-15`.
- **E005** `cellot/cellot_gpu/results/cross_species_ood_cellot_gpu` —
  status `never_started`. Empty placeholder directory, no `config.yaml`.

---

## Useful one-liners

The CSV opens cleanly in pandas:

```python
import pandas as pd
df = pd.read_csv("experiments_inventory.csv")

# All renorm IMPACT runs that produced latent-space evals:
df.query("project_phase == 'renorm' and model_family == 'IMPACT' and evals_present == 'latent_space'")

# Every experiment grouped by (phase, family):
df.groupby(["project_phase", "model_family"]).size()

# Find anything that is not 'done':
df.query("status != 'done'")[["exp_id", "result_dir", "status"]]

# Trace which sbatch produced a given result directory:
df.set_index("result_dir").loc[
    "cellot/cellot_gpu/results/renorm_cd8/normal_cellot",
    ["train_sbatch", "eval_sbatch"]
]
```

---

## Provenance

Every row's `notes` field cross-references the underlying source documents:

- `research_log_2026-03-15.txt` — scGen overtraining audit, the racing
  experiments, the gpu_requeue / shared partition decision.
- `research_log_2026-03-22.txt` — the wrong-direction iter-1 postmortem and
  the original CD8/CD4/monocyte holdout planning.
- `research_log_2026-03-30.txt` — Iteration 1 vs Iteration 2 comparison;
  autospeciesOT design.
- `research_log_2026-04-08.txt` — toggle_ood experimental design;
  metric-discrepancy resolution between notebook 06 and notebook 08;
  the `--where latent_space` standardization.
- `research_log_2026-04-13.txt` — toggle results and mentor sync (E15–E17).
- `research_log_2026-04-20.txt` — the full preprocessing audit that
  motivated the renorm phase; the renorm vs stale comparison numbers.
- `2026-04-21_mentor_meeting_slides.md` — the slide deck that summarized
  the audit.
- `autospeciesOT/results.tsv`,
  `autospeciesOT/results_renorm_vs_stale.tsv`,
  `autospeciesOT/results_renorm_vs_stale_delta.tsv` —
  the three flat tables that hold the actual `r2_means` / `mmd` numbers
  from the autoresearch loop, plus the renorm-vs-stale delta.
- `speciesOT/baseline/analysis/toggle_ood_all_results.csv` and
  `…/toggle_ood_iid_vs_ood_comparison.csv` — the comparable flat tables
  for the 48 toggle experiments.

---

## Caveats and known overlaps

- **Mirrored Group A.** A trimmed copy of the three `speciesot_cd8/`
  Group-A artifacts (configs + `evals.csv` + `imputed.h5ad`, no `model.pt`)
  is git-tracked at `speciesOT/baseline/results/speciesot_cd8/{cellot,impact_or,speciesot_scgen}/`.
  These are not separate experiments; they are the same E010 / E011 / E012
  with the heavy weights stripped so the directory can travel through git.
  Cross-referenced in those rows' `notes`.
- **Iteration-1 results were superseded.** The two `speciesot_v1_iter1`
  rows (E008, E009) used `human → mouse` transport on the small
  ~12k-cell matched-only dataset; they are kept in the inventory for
  history but the numbers should be treated as a learning artifact.
- **Stale vs renorm metrics aren't directly comparable.** Stale Groups
  A–D were originally evaluated `--where data_space`; renorm Groups A–D
  were evaluated `--where latent_space`. The 8.1 comparison notebook
  reports both with the caveat. To get a clean apples-to-apples,
  the stale Groups need to be re-evaluated in latent space. Tracked in
  `research_log_2026-04-20.txt §11` final to-do list.
- **`hidden_units` for legacy scGen** is `[512,512]`, not `[256,256]` —
  it inherited the public CellOT-paper defaults. All scGen runs from
  `speciesot_v1_iter2_groupA` onward use `[256,256]`. The CSV records the
  actual config so any reuse of an old encoder can be checked.

---

## Adding a new experiment

When a new training run lands on disk:

1. Append one tuple to `CATALOG` in
   `scripts/build_experiments_inventory.py`. The minimum is the `model_dir`
   path; the rest of the row is parsed from `config.yaml` and `cache/`.
2. Re-run `python scripts/build_experiments_inventory.py`.
3. The CSV gets a new row at the end with the next `exp_id`.

For a brand-new project phase, also extend the phase table at the top of
this README.

# Agent handoff — speciesOT (2026-06-05)

You are picking up an in-progress single-cell ML project. This doc gets you oriented fast: what the project is, how to read the repo, how to run things, the current status, and the conventions to honor. Read it top to bottom once, then keep it open.

---

## 0. TL;DR for your first 10 minutes

- **Project:** cross-species single-cell optimal transport. Predict **human** cells from **mouse** cells using an adapted CellOT (renamed **IMPACT_CellOT**) plus an scGen VAE baseline. Junyi owns the **in-vitro / atlas** track; his mentor owns the downstream **BCG / batch-correction / prediction** track. Do **not** touch BCG work.
- **Control panel:** everything routes through **`./hub`** (a CLI in `speciesOT/hub/`). Learn it first: `./hub list`, `./hub show <run_id>`, `./hub compare A B`, `./hub prep`, `./hub generate`, `./hub metrics`, `./hub handoff`.
- **Read these docs in order:** this file → [`docs/hub_usage.md`](hub_usage.md) (commands) → [`docs/conceptual_framework.md`](conceptual_framework.md) (the science; esp. §5.5–§5.10) → [`docs/hub_handoff.md`](hub_handoff.md) (hub internals) → [`docs/hub_design.md`](hub_design.md).
- **Current focus (2026-06-05):** we just finished a **v08 data cleanup** (enforce assay filter + stratify the OOD split) and re-ran m1/m2; an **uncapped full-atlas CD8** rebuild is prepping. See §6–§7.
- **Nothing is committed.** All the session's work is uncommitted on `main`. Do **not** `git commit` or `git push` unless Junyi explicitly asks.

---

## 1. What the project is

`/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT`. Junyi adapts Bunne et al. 2023's CellOT (drug-perturbation neural OT) to a **species-transport** framing: source = mouse, target = human, `condition` ∈ {mouse, human}. Three model families you'll see:

- **`impact_cellot`** — IMPACT_CellOT, the main model (neural OT in an autoencoder latent space). Aliases on disk: `impact`, `impact_or`, `swapped_cellot`, `speciesot_cellot`.
- **`scgen`** — the scGen VAE, used both as a baseline *and* as the autoencoder IMPACT_CellOT transports in. (An IMPACT cell dir has a sibling `scgen/` + a `model-scgen` symlink.)
- `cellot_celltype` / `cellot_legacy` — abandoned earlier framings; visible in the catalog, ignore for new work.

Conceptual depth (read it): [`docs/conceptual_framework.md`](conceptual_framework.md). The whiteboard division of labor: Junyi's track = atlas data → preprocessing → training → which *informs* the ideal preprocessing + model spec; the boundary artifact handed to the mentor is the processed dataset / preprocessing description / model spec (see `./hub handoff`).

---

## 2. How to read the repo

```
speciesOT/                                  ← workspace root (a git repo; remote "josh", diverged)
├── hub                                     ← `./hub` shell wrapper (auto-activates CellOT env)
├── speciesOT/hub/                          ← THE HUB (Python package). Read in this order:
│   ├── cli.py        — argparse entry; every ./hub subcommand
│   ├── spec.py       — ExperimentSpec dataclass + config/sbatch rendering + spec_from_record
│   ├── discover.py   — walks results trees → ModelRecord/EvalRecord
│   ├── catalog.py    — dataclasses (ModelRecord, EvalRecord, Catalog)
│   ├── readers.py    — parse config.yaml / evals.csv / extended_metrics.csv
│   ├── render.py     — list/show/card/compare/export markdown
│   ├── figures.py    — links EXISTING figures to cards (does not generate)
│   ├── prep.py       — `./hub prep`: build a training .h5ad from a spec (in-memory path)
│   └── prep_backed.py— backed-mode prep for the 43GB full atlas (NEW 2026-06-05)
├── specs/                                  ← declarative experiment specs (YAML). SOURCE OF TRUTH.
│   ├── m1_modern.yaml, m2_baseline.yaml, atlas_cd8_uncapped.yaml
├── cellot/cellot_gpu/                      ← the upstream CellOT codebase (the model + train/eval)
│   ├── cellot/  (the importable `cellot` package: data/, losses/, models/, train/, utils/)
│   ├── scripts/ (train.py, evaluate.py, + our mmd_floor.py / dump_eval_clouds.py / extended_metrics.py)
│   ├── datasets/speciesot-human-mouse-hvg/ ← the *_v07 / *_v08 .h5ad training files
│   └── results/<experiment_tag>/<model>/   ← trained models + evals_*/  (the catalog walks this)
├── speciesOT/baseline/analysis/            ← notebooks (numbered) + outputs
├── docs/                                   ← all the docs (this file lives here)
└── sbatch/{train,eval,eval_dataspace,prep}/← generated SLURM scripts
```

A "model" = a directory with a `config.yaml` under `cellot/cellot_gpu/results/` (or `speciesOT/baseline/results/`). Its `run_id` is like `gpu/hvg_pearson_residuals_m2_ood/impact_cellot` (the `gpu/` prefix = the cellot_gpu root). `./hub` accepts the unique suffix (`hvg_pearson_residuals_m2_ood/impact_cellot`).

---

## 3. Environments + running things (IMPORTANT)

Two conda envs, and they matter:

| env | has | used for |
|---|---|---|
| **`CellOT`** | scanpy 1.8, **torch 1.11.0+cu102**, the `cellot` pkg deps | the hub, training, eval, metrics |
| **`analysis`** | scanpy ≥1.12 (Pearson-residuals / seurat_v3 HVG), jupyter | `./hub prep` (HVG), running notebooks |

- `./hub ...` auto-activates **CellOT**. `./hub prep` internally shells out to **analysis** (HVG needs scanpy ≥1.12), then back to CellOT for an anndata-0.7 round-trip.
- Interpreters (hard-coded fallbacks; override with `SPECIESOT_ANALYSIS_PY` / `SPECIESOT_CELLOT_PY`):
  - CellOT: `/n/home01/jzhou1125/.conda/envs/CellOT/bin/python`
  - analysis: `/n/home01/jzhou1125/miniforge3/envs/analysis/bin/python`
- **`cellot` is NOT pip-installed.** To run its scripts you must set `PYTHONPATH=/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu` (the hub's generated sbatches do this; do it yourself for ad-hoc runs). Running from the repo root makes `import cellot` resolve to an *empty* outer namespace dir — a trap.
- **GPU:** the env's torch only supports CUDA ≤ **sm_70**, so GPU jobs **must pin V100** (`#SBATCH --constraint=v100`; `spec.py:_GPU_CONSTRAINT`). A40/A100/H100 jobs die with "no kernel image". The spec field `impact_train_device: gpu|cpu` chooses; scGen always trains on CPU. CPU avoids the V100 queue.
- **Training is iteration-bounded, not epoch-bounded:** `n_iters: 50000` = gradient steps (batch 128). Time ≈ constant regardless of dataset size; the model still sees all cells many times. (This is why capped and uncapped both take ~40 min.)
- **Notebooks:** run headless with `MPLBACKEND=Agg <analysis_py> -m jupyter nbconvert --to notebook --execute --inplace <nb>`. If nbconvert complains about an output schema, normalize first (set every code cell `outputs=[]`, `execution_count=None`).
- **Cluster note:** `./hub prep` runs in-process on the login node — fine for the ~50k sampled files, but the **43GB full atlas** must use the **backed** path as a batch job (see §7).

---

## 4. The hub workflow (the spine of everything)

```
(optional) ./hub spec dump <run_id> --out specs/new.yaml   # bootstrap a spec from a trained model
edit specs/new.yaml                                          # specs/ is the durable source of truth
./hub prep specs/new.yaml                                    # build the .h5ad named by data_file
./hub generate specs/new.yaml                                # write configs + sbatches, print submit chain
# copy-paste the printed sbatch chain (hub does NOT auto-submit — safety boundary)
./hub metrics <run_id>                                       # after evals: write extended_metrics.csv sidecar
./hub list / show / compare / card / handoff                 # inspect
```

**Gotcha — `./hub spec dump` is lossy.** It reconstructs a spec from the trained model's `config.yaml` (+ filename heuristics + sibling), NOT from any YAML. Fields *not* in config.yaml fall back to **defaults**: `assay_filter`, `cap_cells_per_type`, `source_datasets`, `ortholog_source`, `datasplit_stratify`, `impact_train_device`, `random_state`, `test_size`, `notes`. So **clone the spec file (`cp specs/...`) rather than re-dumping** when those "intent" fields matter. (Detailed in conversation; a future fix would persist the spec into the results dir.)

---

## 5. The evaluation metrics (you must understand these)

`evals.csv` reports per-`ncells` (30/50/80) `r2-means` (Pearson r — the hub **squares** it to true R²) and `mmd`. MMD uses an RBF-kernel ensemble averaged over `gammas = np.logspace(1,-3,50)`. We added a floor/ceiling framework (code in `cellot/cellot_gpu/cellot/losses/`):

- **MMD floor** = self-MMD of the real target (split-half) — the best achievable at finite `ncells` (`compute_mmd_floor` / `compute_mmd_two_sample(split_half=True)`).
- **MMD ceiling** = `MMD(mouse control, real human)` — the no-transport / identity-baseline gap.
- **gap_above_floor** = `MMD − floor` (sample-size-robust error).
- **frac_gap_closed** = `(ceiling − MMD)/(ceiling − floor)` — **1 = reached the floor, 0 = no better than identity, negative = WORSE than identity (OT overshoot).**
- **mean_JS** = mean per-gene Jensen-Shannon divergence (treated vs imputed marginals; `compute_marginal_divergence` in `losses/divergence.py`). The Figure-G marginal view; complements MMD (joint).

`extended_metrics.csv` also now carries the **R² floor/ceiling** (added 2026-06-05): `r2_identity` (no-transport: corr² of mouse vs human means), `r2_self` (best: split-half human means), `frac_r2_closed = (r2_model − r2_identity)/(r2_self − r2_identity)`.

**KNOWN CAVEAT — the MMD ceiling is currently misleading for AE-based models** (investigated 2026-06-05). The model's `imputed` is **decoded through the autoencoder** (encode→transport→decode), but `mmd_floor` (real self-MMD) and `mmd_ceiling` (RAW mouse vs human) are measured on **un-decoded** clouds. The AE round-trip alone costs ~0.083 MMD (measured: `MMD(decode(encode(human)), human)` for m1 v08), so the decoded model output sits *above* the raw-mouse ceiling → a spurious **negative `frac_gap_closed`**. The honest references are in **decoded space**: AE-recon floor = `MMD(decode(encode(treated)), treated)` (~0.083) and decoded-identity ceiling = `MMD(decode(encode(control)), treated)` (~0.31); with those, m1 v08 IMPACT closes ~91% of the gap. **TODO for the next model:** add these AE-space references to `extended_metrics.py` (load the AE via `cellot.utils.evaluate.load_projectors(model-scgen, "ae", "data_space")`) so `frac_gap_closed` is honest. R²'s `frac_r2_closed` does NOT have this problem (means are AE-robust → cleanly positive, ~0.83 for m1 v08).

How they're produced/surfaced: `scripts/dump_eval_clouds.py` caches `treated/imputed/control/genes` to `eval_clouds.npz`; `scripts/extended_metrics.py` (run via `./hub metrics <run_id>`) writes `extended_metrics.csv`; the catalog reads it and `show`/`card`/`compare`/`handoff` display it. Full write-up: `conceptual_framework.md` **§5.9** (MMD/gamma/floor) and **§5.10** (assay). Notebooks: `20_m1_mmd_investigation.ipynb` (gamma + floor + Figure-G), `22_v08_results.ipynb` (the v08 scorecard).

---

## 6. The v08 cleanup (what just happened, and why it matters)

Notebook `21_data_imbalanced.ipynb` discovered that the M1 held-out monocytes' within-population "scatter" was **Smart-seq2 contamination**: the atlas sources mix platforms, and the intended `assay_filter` (mouse `10x 3' v2` / human `10x 3' v3`) was recorded in specs but **never applied**. Two fixes were made, then m1/m2 were rebuilt as **v08**:

1. **Assay filter is now ENFORCED** in prep (`prep.py:_apply_assay_filter`, `prep_backed.py`), dropping Smart-seq2. Default keeps one droplet platform per species. (§5.10.)
2. **OOD split is now stratifiable** by species (`cell.py:split_cell_data_toggle_ood` takes `stratify=`; spec field `datasplit_stratify: condition`, opt-in). Fixes the unstratified 207/219 drift. (§5.7.)

**Result (the key finding):** raw R²/MMD looked mixed, but the **floor/ceiling view shows v08 genuinely improved IMPACT**. m1 IMPACT `frac_gap_closed` went **−0.71 → +0.06** (from "worse than identity" to actually helping), `gap_above_floor` 0.113 → 0.080; the **ceiling rose** (0.090 → 0.109) because removing Smart-seq2 un-masked the true cross-species gap. scGen's R² improved but it still overshoots distributionally. This is *why the new metrics exist* — they revealed a win the raw R² hid.

v07 vs v08 are **different test sets** (cleaner data), so weight `gap_above_floor` / `frac_gap_closed` over raw MMD when comparing.

---

## 7. Current status & in-flight work (2026-06-05)

- ✅ **m1/m2 v08** (`hvg_pearson_residuals_{m1,m2}_v08_ood`): trained, evaluated, extended metrics computed. The scorecard `speciesOT/baseline/analysis/22_v08_results.ipynb` reads it all.
- 🟡 **Atlas CD8 uncapped + assay** (`specs/atlas_cd8_uncapped.yaml`): a rerun of the uncapped full-atlas CD8 experiment (notebook 19) but **with** the assay filter it lacked. The **43GB** `tabula_*_all.h5ad` source needs the **backed** prep path (`prep_backed.py`, triggered by `source_backed: true`). The prep is **batch job `19449000`** (128G, `shared`) — **PENDING** behind a long-running dashboard job. First run of new backed code; **watch its early log** (`logs/prep_atlas_cd8_v08_*.out` — obs read → assay filter → match → materialize → ortholog → HVG).
  - **After prep finishes:** `./hub generate specs/atlas_cd8_uncapped.yaml` → submit the printed train chain (scGen CPU, IMPACT V100) → `./hub metrics hvg_pearson_residuals_a_uncapped_v08_ood/{impact_cellot,scgen}` → the scorecard's atlas rows populate (v07-no-assay vs v08-assay).
- 📋 **Everything is uncommitted** (see §9).

---

## 8. Conventions & gotchas (honor these)

- **No `git commit` / `git push` unless explicitly asked.** The `josh` remote (github.com/JoshuaPrice/speciesOT) is diverged; only push when told, never force-push main. Notebook 20 was pushed to `josh/cellot` earlier at the user's request.
- **The hub never auto-submits sbatches** — it prints the chain; the human submits. (You may submit when the user explicitly asks for a rerun.)
- **Don't full-load the 43GB atlas** on the login node — use the backed path / a high-mem batch job.
- **Conservative deletes**; archive over `rm` for tracked files.
- **Annotated files** the user keeps notes in: `cellot/cellot_gpu/cellot/utils/evaluate.py`, `scripts/evaluate.py`. The 2026-06-02 decision: don't write the floor/ceiling into `evals.csv` (keep them as sidecars), and don't edit `evaluate.py` for them.
- **Lint noise:** basedpyright flags `import numpy/scanpy/...` as "could not be resolved" in `prep.py` etc. — that's the linter env lacking the packages, not a real error.

---

## 9. Uncommitted state (as of 2026-06-05)

Nothing from this session is committed. New files: `speciesOT/hub/prep_backed.py`, `cellot/cellot_gpu/cellot/losses/divergence.py`, `cellot/cellot_gpu/scripts/{mmd_floor,dump_eval_clouds,extended_metrics}.py`, `specs/atlas_cd8_uncapped.yaml`, notebooks `20/21/22`, `handoff/`, output dirs. Modified: `cell.py` (stratify), `losses/mmd.py` + `__init__.py` (floor/ceiling/two-sample), the 6 hub modules, `specs/m1_modern.yaml` + `m2_baseline.yaml` (v08), and docs (`conceptual_framework.md` §5.9/§5.10, `hub_usage.md`, `hub_handoff.md`). If asked to commit, group logically (metrics, assay-enforcement, v08 specs, docs) and follow the existing `Hub vN:` / `feat(analysis):` commit styles.

---

## 10. Your likely next actions

1. Check the queue (`squeue -u jzhou1125`) and the atlas prep log; if `19449000` failed early on the new backed path, debug `prep_backed.py` (compare against `speciesOT/baseline/analysis/19_uncapped_cd8_ood_data_prep.py`, which is the proven original). If the `shared` queue is hopeless, consider a different partition.
2. When prep completes: `./hub generate specs/atlas_cd8_uncapped.yaml`, submit the train chain, then `./hub metrics`, then re-run notebook 22.
3. Keep using `gap_above_floor` / `frac_gap_closed` as the headline comparison metric, not raw R²/MMD.
4. Ask before committing/pushing.

When in doubt, run `./hub show <run_id>` and read `conceptual_framework.md`. Good luck.

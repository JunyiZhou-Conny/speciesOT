# scgen-cellot-unbalanced — Unbalanced OT for species transport

Isolated sibling of `speciesOT` / `cellot_gpu`. **Do not modify** production hub or
`cellot_gpu` in place. See [`PLAN.md`](PLAN.md) for the full study design.

## Status (2026-07-21)

| Piece | Status |
|-------|--------|
| Synthetic Sinkhorn UOT + Option-A bridge | **done** (`synthetic/`; guards pass) |
| Option A real-data scaffold (this sprint) | **in progress** — freeze LPS rat; code ready |
| Option B entropic UOT | not started |
| Option C unbalanced ICNN | **out of scope this sprint** |

## Freeze target (Plan D pick)

**LPS rat OOD IMPACT** — `paper_crossspecies_rat_ood`

| Item | Path / value |
|------|----------------|
| Frozen AE | `../cellot/cellot_gpu/results/paper_crossspecies_rat_ood/scgen/cache/model.pt` |
| Balanced baseline | `./hub show gpu/paper_crossspecies_rat_ood/impact_cellot` |
| Parity north-star | `frac_gap_closed_decoded` ≈ **0.076** @ ncells=80; ≈ **0.092** @ 500 |
| Tolerance | \|Δ\| ≤ **0.03** on fgc_decoded @ 80 for uniform retrain |

Rationale: smaller than atlas M2; does not collide with Plan B’s atlas scoreboard;
same ICNN + frozen AE recipe. Atlas M2 weights are a later handoff if LPS shows signal.

## Option A in one sentence

Estimate per-cell mass weights → train the **same** balanced CellOT ICNN with
`WeightedRandomSampler`. α=0 (uniform) = balanced parity end.

## Layout

```
uot/reweight.py          # weight estimators + WeightArtifact
metrics/uot_aware.py     # composition-matched MMD + kept-mass sidecar
configs/option_a/        # LPS rat configs
scripts/                 # estimate / train / eval / sbatch printer / unit tests
honest_metrics.py        # vendored from autoresearch
synthetic/               # mechanism proof (already green)
DELIVERABLE_D_option_a.md
```

## Quickstart (CellOT / CellOT_gpu env)

```bash
cd scgen-cellot-unbalanced
export PYTHONPATH=../cellot/cellot_gpu:$PWD

# unit tests (CPU)
python scripts/test_reweight_unit.py

# estimate weights
python scripts/estimate_weights.py \
  --config configs/option_a/lps_rat_balanced.yaml \
  --method louvain_match --alpha 1.0

# print sbatch chain (does NOT submit)
bash scripts/print_sbatch_chain.sh

# smoke train (50 iters, CPU)
python scripts/train_option_a.py \
  --config configs/option_a/lps_rat_smoke.yaml \
  --outdir results/lps_rat/smoke \
  --weights results/lps_rat/weights/weights_louvain_match_alpha1.npz
```

## Metrics

- **North-star (required):** `frac_gap_closed_decoded` (+ `frac_r2_closed_decoded`, `mean_js`)
- **Mass-aware sidecar:** `uot_aware_metrics.csv` — `effective_kept_mass`, `composition_matched_mmd`
- Do **not** claim UOT wins on full-cloud MMD alone (PLAN §5.2–5.4)

## Go / no-go

See [`DELIVERABLE_D_option_a.md`](DELIVERABLE_D_option_a.md). Option B only if α-sweep
improves composition-matched / kept-mass story without north-star collapse. **No Option C**
until then.

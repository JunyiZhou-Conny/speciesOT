# Deliverable D — Unbalanced OT Option A

**Date:** 2026-07-21  
**Work root:** `scgen-cellot-unbalanced/`  
**Scope:** Option A only (reweight-then-balanced, same ICNN). **No Option C.**

---

## 1. Freeze target pick

**Chosen: LPS rat OOD IMPACT** (`paper_crossspecies_rat_ood`)

| Why | Detail |
|-----|--------|
| Isolation from Plan B | Atlas M2/M1 scoreboard stays Plan B’s; we do not write `hvg_pearson_residuals_*_v08_ood/` |
| Size / iteration | LPS h5ad ~62k×1k; familiar Bunne Fig.4 OOD (holdout=rat) |
| Frozen AE path | `cellot/cellot_gpu/results/paper_crossspecies_rat_ood/scgen/cache/model.pt` |
| Balanced baseline | hub `gpu/paper_crossspecies_rat_ood/impact_cellot` |

**Rejected for this sprint:** atlas M2 v08 freeze (aligns with B but risks ownership collision; revisit if LPS shows signal — handoff weight files → B).

---

## 2. Parity gate

Existing decoded numbers (production IMPACT, no retrain):

| ncells | `frac_gap_closed_decoded` | `frac_r2_closed_decoded` |
|--------|---------------------------|--------------------------|
| 80 | **0.0759** | 0.457 |
| 500 | **0.0918** | 0.457 |
| 1000 | 0.0910 | 0.457 |

**Tolerance for Option-A uniform (α=0) retrain:**  
`|fgc_decoded(α=0) − 0.0759| ≤ 0.03` at ncells=80 (subsample / train-noise band).  
If uniform retrain fails this, stop and debug sampling before claiming any α>0 gain.

Synthetic τ→∞ parity already holds (`synthetic/results/synthetic_guards.csv`: ρ=50 ≈ balanced).

---

## 3. Option A design

| Knob | Meaning |
|------|---------|
| `method` | `uniform` \| `louvain_match` \| `density_ratio` |
| `alpha` ∈ [0,1] | blend: `w = (1−α)·uniform + α·w_method` — **α=0 is the almost-balanced end** |

- **louvain_match:** LPS has `louvain` clusters (no cell_type column). Reweight so shared-cluster mass matches geometric-mean composition; unique clusters near-discarded.
- **density_ratio:** kNN density ratio in frozen AE latent (source ∝ ρ̂_t/ρ̂_s).
- **Train:** identical ICNN dual / hyperparams; only `WeightedRandomSampler` on train source/target. Test loaders stay uniform.
- **Code:** `uot/reweight.py`, `scripts/{estimate_weights,train_option_a,eval_option_a}.py` — imports `cellot_gpu` read-only (no in-place fork of production train.py).

---

## 4. Mass-aware metrics (sidecar)

File: `<outdir>/uot_aware_metrics.csv`

| Metric | Formula / role |
|--------|----------------|
| `effective_kept_mass` | ESS/n of source weights = `1/(n Σ p_i²)`. Uniform → 1; aggressive reweight → ≪1 |
| `weight_entropy` | Normalized Shannon entropy of source weights |
| `composition_matched_mmd` | MMD after resampling pred & target to shared-louvain geometric-mean mix (ncells=80) |

**Decision rule (from PLAN §5.6):** Option A “helps” iff some α improves composition-matched MMD and/or kept-mass biology **without** north-star `frac_gap_closed_decoded` collapsing vs α=0. Full-cloud MMD alone is insufficient.

---

## 5. Comparative table (template — fill after GPU runs)

Baseline column filled from hub; Option-A columns pending submit of `print_sbatch_chain.sh`.

| run | α | method | fgc_dec@80 | fr2_dec | mean_js | eff_kept_mass | comp_matched_mmd | notes |
|-----|---|--------|------------|---------|---------|---------------|------------------|-------|
| hub IMPACT balanced | — | — | 0.076 | 0.457 | 0.446 | 1.0 | — | frozen baseline |
| option_a uniform | 0 | uniform | *TBD* | | | **1.000** | | weights on disk; train pending |
| option_a louvain | 0 | louvain_match | *TBD* | | | **1.000** | | α=0 blend = parity |
| option_a louvain | 0.25 | louvain_match | *TBD* | | | **0.947** | | weights ready |
| option_a louvain | 0.5 | louvain_match | *TBD* | | | **0.816** | | weights ready |
| option_a louvain | 1.0 | louvain_match | *TBD* | | | **0.526** | | smoke train (5 iters) OK |
| option_a density | 1.0 | density_ratio | *TBD* | | | *TBD* | | estimate via sbatch chain |

---

## 6. Implementation checklist

- [x] Freeze target chosen and AE path documented  
- [x] Balanced parity **numbers + tolerance** reported (retrain pending GPU submit)  
- [x] Option A implementation exists (`estimate_weights` + `train_option_a` + unit tests)  
- [x] Mass-aware sidecar specified + coded  
- [x] Explicit **no Option C** this sprint  
- [x] README for next agent  
- [ ] GPU α-sweep submitted + table filled  
- [ ] Go/no-go with evidence (below: provisional)

---

## 7. Go / no-go (provisional — pre–GPU sweep)

| Signal | Provisional call |
|--------|------------------|
| Synthetic Option-A bridge | **Go** — `reweight_then_balanced` beats balanced on shared_map_mse; blob leakage collapses (`synthetic_guards.csv`) |
| Real LPS α-sweep | **Pending** — do not claim Bunne Fig.4 fix until parity + table §5 filled |
| Option B | **Only if** some α improves comp-matched MMD without fgc_dec collapse |
| Option C (unbalanced ICNN) | **No** this sprint — Brenier maps are measure-preserving; needs new dual |

**Mentor one-liner:** UOT Option A = same ICNN, reweighted mass; neural UOT (Option C) deferred.

---

## 8. Risks (one line each)

1. North-star bias against mass dropping → always report sidecar.  
2. Without α→0 parity, α>0 results are uninterpretable.  
3. `louvain` ≠ biological cell type — density_ratio is the unsupervised control.  
4. Compositionality / BCG dual-UOT bookkeeping — out of scope.  
5. Do not confuse M1/M2 class imbalance narratives with UOT algorithms.

---

## 9. Handoff

- **→ Plan B:** if later freeze moves to M2, share `results/lps_rat/weights/` pattern + this deliverable.  
- **→ Future agent:** run `bash scripts/print_sbatch_chain.sh`, submit after review, fill §5, then decide Option B.

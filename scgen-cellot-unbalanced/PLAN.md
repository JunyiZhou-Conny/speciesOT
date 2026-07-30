# Unbalanced OT for species transport — a comprehensive plan

> **Status: PARTIAL (2026-07-21).** Synthetic §5.1 **done**. Option A real-data scaffold
> (LPS rat freeze, reweight + train/eval scripts, weight α-grid artifacts) **done** — see
> `README.md` + `DELIVERABLE_D_option_a.md`. GPU α-sweep / parity retrain **not yet
> submitted**. Options B/C not started. Isolation rule unchanged: do not modify production
> hub / `cellot_gpu` in place.
>
> **Purpose.** Test whether relaxing balanced OT's hard mass-conservation constraint
> (→ unbalanced OT, UOT) improves mouse→human species transport, where the two cell
> populations differ in composition and each has species-unique states. The hard part is
> not the code — it is *deciding whether it helped*, because our current north-star metric
> is defined for balanced transport and structurally penalizes what UOT is designed to do.

---

## 0. The one-paragraph answer to "balanced vs unbalanced"

**Balanced OT** (what CellOT does today) finds a map `T = ∇g` that pushes the *entire*
source distribution onto the *entire* target distribution: `T#μ = ν` exactly. Mass is
conserved — every mouse cell's mass must land somewhere in the human cloud, and every part
of the human cloud must be covered. It assumes the two clouds are the **same shape up to a
deformation**. **Unbalanced OT** replaces those hard marginal constraints with soft
KL-divergence penalties weighted by a relaxation parameter `τ` (a.k.a. `ρ`, `reg_m`):
`min_π ∫c dπ + τ·KL(π₁‖μ) + τ·KL(π₂‖ν)`. This lets the map **create/destroy mass** — it can
down-weight over-represented or species-unique source cells and under-fill target regions
that have no source counterpart. `τ→∞` recovers balanced OT; `τ→0` transports nothing. UOT
assumes the two clouds **mostly overlap but each may have extra/missing pieces, and only the
shared part should be transported.**

---

## 1. How the algorithmic difference translates to *our* data

Source = mouse cells in the frozen scGen latent space; target = human cells. Balanced OT is
forced to match the whole mouse latent distribution to the whole human latent distribution.
That is wrong precisely where cross-species biology is interesting:

1. **Cell-type composition mismatch.** If mouse is 40% T / 60% myeloid but human is 70% T /
   30% myeloid, balanced OT *must* move mass across type boundaries to satisfy the marginal
   constraint — it will transport surplus mouse myeloid cells into the human T-cell region,
   manufacturing biologically wrong mouse→human correspondences. UOT can instead re-weight
   the shared types into agreement and leave the wrong crossings untransported.

2. **Species-unique populations (no counterpart).** States present in mouse but not human
   (or vice-versa) have mass that balanced OT is obligated to place *somewhere*, smearing it
   onto the nearest human cells and corrupting the map globally. UOT can discard that mass at
   a bounded KL cost, so a mouse-only population does not distort the shared mapping.

3. **Outliers / doublets / ambient / low-quality cells.** Balanced OT is outlier-sensitive
   (every point's mass must land); UOT is robust — it discounts outlier mass.

The composition + unique-population arguments are **strongest on the species axis** (the
project headline), and also apply to the drug axis (unst→LPS/BCG) whenever stimulation
changes population proportions.

---

## 2. The trade-offs of switching to UOT (why this is genuinely hard to decide)

1. **A new, unavoidable hyperparameter `τ`.** It sets how much mass may be created/destroyed.
   Too aggressive → the model collapses toward the dense shared core, under-transports, and
   *throws away real but rare human states*. Too weak → it is just balanced OT again. The
   right value is data-dependent and unknown a priori; tuning it is the central difficulty.

2. **The metric denominator changes — our north-star fights us.** `frac_gap_closed_decoded`
   is `MMD(pred, target)` against the **full** human cloud. UOT deliberately does *not*
   reproduce the full target (it drops mass). A UOT model that *correctly* ignores a
   human-specific population looks **worse** on whole-distribution MMD even though it is
   doing the biologically right thing. **The balanced benchmark structurally penalizes the
   exact behavior UOT exists for.** Evaluation must separate "closed the shared-structure
   gap" from "reproduced the whole target." This is the crux of the project.

3. **Mass semantics for composition (the BCG endgame).** UOT outputs a *partial / reweighted*
   map → an unnormalized predicted cloud. The eventual goal of composing species-transport ∘
   drug-transport requires the mass bookkeeping to be consistent across two unbalanced maps.
   Balanced maps compose trivially; unbalanced ones need explicit mass handling.

4. **Algorithmic realization is non-trivial.** CellOT's ICNN/Brenier map is *intrinsically*
   balanced (a Brenier map is measure-preserving). Making it unbalanced is a real change of
   algorithm family, not a flag. Three viable routes, in increasing fidelity/cost — see §4.

---

## 3. Repo isolation (hard requirement: do not disturb anything)

New sibling repo `scgen-cellot-unbalanced/` that mimics `scgen-cellot-ablation/`:

- **Fork the CellOT stack** (copy, not symlink) so its `models/cellot.py`, `networks/icnns.py`,
  `train/train.py` can be modified freely. Add UOT as a **new model** (`model.name: cellot_uot`
  or a `model.unbalanced` block) *alongside* the untouched balanced `cellot`.
- **Freeze and REUSE the exact scGen AE checkpoints** from the ablation repo (same `model.pt`),
  so the latent space is byte-identical. The AE is *not* retrained — the only variable in the
  whole study is the OT map. (Mirror the ae_study "metric-parity contract".)
- **Reuse `honest_metrics.py` verbatim** (vendor a copy) + the same eval manifests, `v08` OOD
  cuts, `random_state=0`, `ncells={30,50,80}` (headline 80), 50 RBF gammas `logspace(1,-3,50)`.
  Results write to `experiments.csv`-compatible CSVs so UOT rows merge into the existing
  leaderboard and `./hub scorecard` can rank them next to balanced runs.
- **Never** import from or write into `speciesOT/`, `cellot/cellot_gpu/`, or
  `scgen-cellot-ablation/`. Never `git commit`/`push` without explicit ask (repo hard rule).

---

## 4. Three realization options for UOT (pick a starting rung in §7)

**Option A — reweight-then-balanced (cheapest, reuses the entire existing stack).**
Estimate per-cell mass weights that align the two clouds' shared structure (e.g. a density
ratio / classifier-based importance weight, or cell-type-proportion matching), then run the
*existing balanced CellOT* on the reweighted problem. This is a legitimate, well-understood
form of unbalancedness ("relax marginals = reweight marginals") and needs almost no new OT
code. Best first rung: it isolates "does fixing composition help?" from "do we need a new
solver?" Limitation: weights are estimated up front, not jointly with the map.

**Option B — entropic UOT via `ott-jax` / POT `sinkhorn_unbalanced` (mature solver).**
Solve UOT on empirical latent batches with KL-relaxed marginals; obtain a soft coupling.
Turn it into an out-of-sample map via a **barycentric projection** (or amortize it with a
small map network trained to the coupling). Gives a principled `τ` knob and battle-tested
solvers, but it is a *plan/coupling* first and needs the projection step to produce the
OOD map we require for held-out cells.

**Option C — neural unbalanced ICNN map (highest fidelity, most work).**
Keep CellOT's amortized ICNN dual (so we still get a clean out-of-sample map) but add the KL
marginal-relaxation terms to the dual objective (unbalanced Monge-map / Makkuva-style), or
learn an accompanying mass-reweighting head. Most faithful to CellOT and to the composition
endgame, but the most implementation and validation effort.

Recommended sequence: **A → B → C**, stopping as soon as a rung shows (or convincingly fails
to show) benefit on the §5 evaluation.

---

## 5. Evaluation — how we decide if UOT helped (the heart of the plan)

The trap: the frozen benchmark is defined for balanced transport. Layered evaluation:

**5.1 Synthetic ground-truth first (prove the mechanism before real data).**
Construct a toy where the correct answer is known: take the mouse latent cloud, apply a known
deformation to synthesize a "human" cloud, then deliberately (a) inject a mouse-only blob and
(b) skew cell-type composition. We know the truth: map ≈ the known deformation on shared
structure, discard the blob. Show balanced OT gets corrupted by the blob / composition skew,
and that UOT recovers the true map and *identifies the discarded mass as the injected blob*.
This is the analogue of ae_study's "correctness guards" and gates everything downstream.

**5.2 Parity guard (τ→∞ must equal balanced CellOT).** At the balanced limit, the UOT model
must reproduce the existing CellOT leaderboard number on the v08 cuts to within subsample
noise. Without this, no comparison is trustworthy.

**5.3 Report the frozen north-star anyway.** Score `frac_gap_closed_decoded` (+ guardrails
`frac_r2_closed_decoded`, `mean_js`) on the same v08 OOD cuts, headline `ncells=80`. This is
the apples-to-apples number vs the balanced leaderboard — necessary but *not sufficient*.

**5.4 Add UOT-aware metrics (so we stop penalizing correct mass-dropping):**
- **Composition-matched MMD:** reweight target (or prediction) to a common cell-type
  composition, then compute MMD — removes the composition penalty so we measure shared-shape
  fidelity, not proportion agreement.
- **Per-shared-type MMD/R²:** compute the metric only on cell types present in *both* species
  and aggregate — measures whether shared populations are reproduced well.
- **Kept-mass report:** fraction of source mass transported vs discarded, and *which* cells
  are discarded — are they the biologically expected mouse-specific ones? (This is a feature,
  not just a diagnostic.)
- **No-hallucination check:** does the prediction avoid filling human-only regions that have
  no mouse counterpart?

**5.5 Composition-robustness stress test (the practical win).** Resample the mouse *input* to
several cell-type compositions and measure prediction stability. Balanced OT predictions
should swing with input composition (they must match the fixed target marginal); a good UOT
should be markedly more invariant. Stability across compositions is the headline argument if
whole-distribution MMD is a wash.

**5.6 `τ` ablation curve.** Sweep `τ` from balanced-limit to aggressive; plot, on one figure:
north-star `frac_gap_closed_decoded`, the composition-matched / per-shared-type metric, and
kept-mass. **Decision rule:** UOT "helps" iff some `τ` improves the shared-structure metric
and/or composition-robustness *without* the north-star collapsing — and the discarded mass is
biologically sensible. If no `τ` beats balanced on the shared-structure metric, UOT does not
help for this data and we report that cleanly.

---

## 6. Phased roadmap (with acceptance criteria)

1. **Repo scaffold (§3).** Fork ablation stack, wire frozen AE checkpoints, vendor
   `honest_metrics`, reproduce ONE balanced CellOT v08 number end-to-end.
   *Acceptance:* balanced number reproduced to subsample noise (parity proof).
2. **Synthetic ground-truth harness (§5.1).** Toy generator + the correctness guards.
   *Acceptance:* balanced OT demonstrably corrupted by injected blob; harness ready.
3. **Option A — reweight-then-balanced (§4A).** Weight estimation + reweighted balanced run.
   *Acceptance:* recovers true toy map; parity at uniform weights; first real-data τ-sweep.
4. **UOT-aware metrics (§5.4) + composition stress test (§5.5).** Build as sidecars, schema-
   compatible; retro-apply to balanced runs for a fair baseline column.
5. **Option B — entropic UOT + barycentric/amortized map (§4B).** τ knob, OOD map.
   *Acceptance:* τ→∞ parity; τ-ablation curve (§5.6) on v08 cuts.
6. **Decision gate.** Evaluate §5.6 decision rule. Only proceed to Option C (§4C) if A/B show
   a real, mechanism-backed signal that a jointly-learned unbalanced map would sharpen.
7. **(Conditional) Option C — neural unbalanced ICNN**, then re-run the full §5 battery.
8. **Composition semantics for the BCG endgame (§2.3).** Define how two unbalanced maps
   compose (mass bookkeeping) — only once single-axis UOT is validated.

CPU-friendly rungs (1–4, Option A) come first; GPU retraining enters at Options B/C. Check in
with the user after Phase 2 (synthetic result) and at the Phase 6 decision gate.

---

## 7. File layout (mirrors ablation + ae_study conventions)

```
scgen-cellot-unbalanced/
  PLAN.md                  # this file
  cellot/                  # forked balanced CellOT stack (UOT added as a new model)
  honest_metrics.py        # vendored verbatim from autoresearch (metric parity)
  synthetic/               # §5.1 toy generator + correctness guards
  uot/
    reweight.py            # §4A Option A
    entropic.py            # §4B Option B (ott-jax / POT)
    neural_icnn.py         # §4C Option C (conditional)
  metrics/
    uot_aware.py           # §5.4 composition-matched / per-shared-type / kept-mass sidecars
    composition_stress.py  # §5.5
  results/                 # experiments.csv-schema CSVs (merge into the leaderboard)
  configs/                 # cellot_uot model configs + τ sweep
```

---

## 8. Risks / care

- **Metric mismatch (the big one)** → never judge UOT on whole-distribution MMD alone; §5.4/§5.5.
- **`τ` collapse** → sweep from the balanced limit; enforce the §5.2 parity guard.
- **Barycentric projection ≠ out-of-sample map** → Option B needs the amortization step for OOD.
- **Composition of unbalanced maps** → defer to §6.8; keep single-axis mass semantics explicit.
- **Silent divergence from the frozen protocol** → reuse `honest_metrics` + identical manifests/
  ncells/gammas/seed; touch no knobs (mirror ae_study §0).
- **Frozen AE drift** → reuse the exact checkpoints; never retrain the AE in this study.
- **Never commit/push** without explicit ask; never write into the existing repos.
```

# Plan D — Unbalanced OT Option A (freeze everything else)

**Owner agent:** 1 dedicated eng/science agent  
**Parallel with:** A, B, C — work only under `scgen-cellot-unbalanced/` (+ optional read-only freeze of one AE)  
**Deliverable:** Real-data Option A experiment design + implementation start + parity gate  
**ETA:** medium for Option A; do **not** start Option C (unbalanced ICNN) in this sprint

---

## Background (read this before doing anything)

CellOT (Bunne et al. 2023) learns a transport map with **ICNNs** (input-convex networks) parameterizing a Brenier-type potential — clever because the map is a gradient of a convex function, matching OT theory for **balanced** (mass-preserving) coupling. In speciesOT, IMPACT_CellOT uses that idea in a **frozen scGen AE latent space**.

**Unbalanced OT** relaxes mass conservation: some source/target mass may be discarded (birth/death of mass). That is attractive when cell-type composition or density differs across species (atlas M1/M2 imbalance narratives; notebook `21_data_imbalanced.ipynb`). It is **not** a free lunch: the project north-star `frac_gap_closed_decoded` compares full predicted vs full target clouds and can **punish** a model that correctly drops mass.

There is already an isolated sibling project:

`/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/scgen-cellot-unbalanced/`

Status (as of audit 2026-07-21):

- `PLAN.md` — full study plan; states not fully executed  
- `synthetic/` — **done**: Sinkhorn UOT toy proof (guards pass; reweight-then-balanced recovers map)  
- **Missing:** real CellOT fork, hub wiring, v08/LPS trained UOT models, README  

The parent PLAN’s options:

| Option | Idea | Keep ICNN CellOT? |
|--------|------|-------------------|
| **A** | Estimate mass weights; train **same** balanced CellOT with reweighted samples | **Yes** — first |
| **B** | Entropic UOT coupling (+ barycentric/amortized map) | Different family |
| **C** | Unbalanced ICNN dual / mass head | **Algorithm change** — Brenier maps are measure-preserving; deferred |

User intent for this agent: **only change balance**. Keep ICNN recipe otherwise. That is **Option A**, not C. Prove τ→∞ (or ρ→∞) parity with balanced CellOT before claiming gains.

LPS vs atlas: either is acceptable if **frozen**. Recommendation: start on **one** small frozen setting — either `paper_crossspecies_rat_ood` IMPACT (familiar, smaller) **or** atlas M2 v08 IMPACT AE freeze (aligns with Plan B). Pick one in the design doc and stick to it. Do not HPO AE.

Isolation rule from the unbalanced PLAN: prefer not to modify `speciesOT/hub` or production `cellot_gpu` in place — fork into `scgen-cellot-unbalanced/` (vendor or symlink carefully).

---

## Goal

1. Choose freeze target (LPS rat OOD **or** atlas M2 v08).  
2. Reproduce **balanced** CellOT metrics (parity).  
3. Implement **Option A** (reweight-then-balanced) with the **same** ICNN + frozen AE.  
4. Score with north-star **plus** at least one mass-aware diagnostic (kept-mass / composition-matched MMD or similar — define in deliverable).  
5. Document whether Option A moves decoded gap vs balanced; decide go/no-go for Option B.

---

## Non-goals

- Option C (unbalanced ICNN dual) — out of scope this sprint  
- AE retraining / VAE (Plan C)  
- Atlas scoreboard ownership (Plan B)  
- Claiming “UOT fixed Bunne Fig.4” without parity + controls  

---

## Hard constraints

- Work root: `scgen-cellot-unbalanced/` (create code there)  
- Freeze AE: load existing `model.pt` from chosen freeze target; do not retrain AE  
- Same latent dim, ICNN depth/width, seeds as balanced baseline where possible  
- Hub never auto-submits; print sbatches  
- Read `scgen-cellot-unbalanced/PLAN.md` end-to-end before coding  
- Re-read synthetic results: `synthetic/results/synthetic_guards.csv`

---

## Required reading

1. `scgen-cellot-unbalanced/PLAN.md` (all options + metric warnings)  
2. `scgen-cellot-unbalanced/synthetic/` (what already passed)  
3. `cellot/cellot_gpu/cellot/models/cellot.py` (balanced dual losses)  
4. `docs/conceptual_framework.md` §5.1 (n≠m note) + §5.9 (decoded north-star)  
5. Freeze-target configs:  
   - LPS: `results/paper_crossspecies_rat_ood/impact_cellot/config.yaml`  
   - or atlas: `results/hvg_pearson_residuals_m2_v08_ood/impact_cellot/config.yaml`  
6. `AGENTS.md` safety: no commit/push unless asked  

---

## Work steps

1. **Design pick:** LPS rat vs M2 v08 — write rationale in `DELIVERABLE_D_option_a.md`.  
2. **Scaffold:** package layout under `scgen-cellot-unbalanced/` (`uot/`, `configs/`, `scripts/`) per PLAN §7; add a short README.  
3. **Parity run:** train or re-eval balanced CellOT with frozen AE; match published/local decoded number within tolerance (document tolerance).  
4. **Weight estimation:** define mass weights (e.g. cell-type or kernel density ratio) **once**, save artifact.  
5. **Option A train:** identical CellOT hyperparameters; only sampling/weights change.  
6. **Metrics:**  
   - standard `frac_gap_closed_decoded`, `frac_r2_closed_decoded`, `mean_js`  
   - **plus** mass-aware sidecar (specify formula; do not rely on full-cloud MMD alone)  
7. **Sweep:** small ρ/τ grid including “almost balanced” end → must approach parity.  
8. **Go/no-go:** recommend stop / try Option B / (later) Option C — with evidence.  
9. Optional canvas: `unbalanced-ot-option-a-metrics.canvas.tsx` using metric-atlas skill.

---

## Key scientific/engineering concerns (address in deliverable)

1. **ICNN + balanced dual assumes mass preservation** — Option A sidesteps by reweighting marginals; Option C needs new math.  
2. **North-star bias** against mass dropping — need matched-support or reweighted target metrics.  
3. **Hyperparameter ρ/τ** — without τ→∞ parity, results are uninterpretable.  
4. **Compositionality** (BCG later) — out of scope; one sentence in risks.  
5. **Do not confuse** “unbalanced OT” with “class imbalance in M1/M2” — related motivation, different algorithms.

---

## Success criteria

- [ ] Freeze target chosen and AE path documented  
- [ ] Balanced parity attempted and reported  
- [ ] Option A implementation exists (trainable)  
- [ ] At least one comparative table: balanced vs Option A on decoded + mass-aware metric  
- [ ] Explicit **no Option C** in this sprint  
- [ ] README so the next agent can continue  

---

## Success is NOT

- Beating Plan B’s atlas IMPACT number with a half-finished UOT  
- Rewriting `cellot_gpu` in place without a fork story  

---

## Handoff

- **→ B:** if freeze was M2, share weight files for optional follow-up  
- **→ Mentor:** “UOT Option A = same ICNN, reweighted mass; neural UOT deferred”  
- **→ Future agent:** Option B only if A shows signal

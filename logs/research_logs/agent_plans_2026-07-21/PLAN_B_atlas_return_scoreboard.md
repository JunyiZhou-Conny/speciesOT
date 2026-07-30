# Plan B — Return to human–mouse atlas scoreboard (main science)

**Owner agent:** 1 ops + metrics agent  
**Parallel with:** A (consume its brief), C (fenced — do not share result dirs), D (independent)  
**Deliverable:** Fresh `./hub scorecard` reading + Stage-0-style metric atlases for v08 M2 (primary) and M1  
**ETA:** medium (mostly verify/submit metrics, not HPO)

---

## Background (read this before doing anything)

speciesOT wants to predict **human** cells from **mouse** cells via a shared autoencoder latent space and a transport map. The atlas track (`speciesOT/baseline`, hub specs, `cellot/cellot_gpu/results/hvg_pearson_residuals_*`) is the dataset we actually care about for publication. LPS Hagai work was a **replication / metric-education** detour.

On atlas, the standing protocol is:

- Framing: **IMPACT** = mouse→human species effect; hold out cell type(s) never seen in training (`toggle_ood`).  
- Baseline: hub **scGen** = PyTorch **AE** (`beta: 0`) + **latent mean shift** (Bunne-style “scGen”, not Lotfollahi VAE).  
- Contender: **IMPACT_CellOT** = ICNN OT in that AE’s latent space.  
- Frozen cuts: `hvg_pearson_residuals_{m1,m2,a_uncapped}_v08_ood`, `random_state=0`, headline `ncells=80`.  
- North-star: **`frac_gap_closed_decoded`** (guardrails: `frac_r2_closed_decoded`, `mean_js`). Raw `frac_gap_closed` is diagnostic only (AE tax).

**M1** = non-classical monocyte alone (`CL:0000875`). **M2** = non-classical + generic monocyte. Mentor preference historically: M2 is the realistic task; M1 is cleaner for interpreting means. Early raw MMD made M1 look broken; decoded frame + v08 assay filter largely explained that.

July 2026 conclusion (LPS era): chasing global AE HPO / ETH Fig.4 lockstep is an **infinite game**. The same metric lessons (mean ≠ cloud; weak AE identity can coexist with high mean R²) should now be applied on **atlas**, not abandoned. Plan B is the return: **one declared scoreboard**, one question — does ICNN beat AE+shift on decoded gap-closed?

Everything routes through `./hub` (`AGENTS.md`). Hub **never auto-submits** sbatches — print chain; human or you submit only if the user asked. Do not full-load 43GB `tabula_*_all` on a login node.

Plan C may build a paper VAE on atlas **in parallel** under a **separate** root. You own the **existing** v08 `scgen/` + `impact_cellot/` trees. Do not convert hub scGen into a VAE.

---

## Goal

Answer, with atlases:

> On v08 OOD (start **M2**, then **M1**), does **IMPACT_CellOT** beat hub **scGen AE+shift** on `frac_gap_closed_decoded` (ncells=80), with mean-R² and JS guardrails?

Secondary: confirm checkpoints still healthy; refresh metrics sidecars if needed.

---

## Non-goals

- No AE architecture / LR / gene-count HPO  
- No ETH / LPS Fig.4 work  
- No unbalanced OT (Plan D)  
- No editing Plan C’s VAE dirs  
- No claiming “beat Lotfollahi scGen” (wrong model)

---

## Hard constraints

- Specs are SoT: `specs/m2_baseline.yaml`, `specs/m1_modern.yaml` (optional later: `atlas_cd8_uncapped.yaml`)  
- Clone specs if you need variants; do not lossy `./hub spec dump` for intent fields  
- Two envs: `./hub` → CellOT; `./hub prep` → analysis; GPU → CellOT_gpu when needed  
- Metric atlases: `.cursor/skills/metric-atlas-canvas/` + gold template `scgen-fig5-stage0-metrics.canvas.tsx`  
- Prefer **M2 first** (mentor “right task”), then M1

---

## Inventory (do first)

```bash
cd /n/holylabs/mooney_lab/Lab/junyizhou/speciesOT
./hub list | rg 'm1_v08|m2_v08|a_uncapped_v08'
./hub scorecard   # or filtered if supported — note decoded column
./hub show gpu/hvg_pearson_residuals_m2_v08_ood/impact_cellot
./hub show gpu/hvg_pearson_residuals_m2_v08_ood/scgen
# same for m1
```

Check presence of:

- `datasets/.../hvg_pearson_residuals_m{1,2}_v08.h5ad`  
- `results/..._v08_ood/{scgen,impact_cellot}/cache/model.pt`  
- `evals_*_data_space/` + `extended_metrics.csv` + `decoded_frame_metrics.csv`

Read Plan A deliverable if available:  
`logs/research_logs/agent_plans_2026-07-21/DELIVERABLE_A_*`

---

## Work steps

1. **Sanity:** list/show M2 IMPACT + scGen; record run_ids, status, existing decoded numbers.  
2. **Metrics refresh** if decoded sidecar missing/stale:  
   `./hub metrics <run_id>` for each of the four (M2×2, M1×2).  
   If hub says “no data_space eval”, locate actual eval dir name and run  
   `cellot/cellot_gpu/scripts/decoded_frame_metrics.py` with correct `--evalprefix` (pattern used for paper_crossspecies).  
3. **Optional recon identity** JSON (encode→decode train-like vs holdout treated) for atlas metric atlas §1 — same spirit as Stage 0 / Bunne atlases.  
4. **Scorecard snapshot** written to  
   `logs/research_logs/agent_plans_2026-07-21/DELIVERABLE_B_scorecard_m1_m2.md`  
5. **Canvases** (Stage-0 section order):  
   - `atlas-m2-v08-metrics.canvas.tsx` (IMPACT | scGen columns)  
   - `atlas-m1-v08-metrics.canvas.tsx`  
6. **Decision paragraph:** OT win / tie / loss on decoded north-star; note mean-R²/JS; do **not** reopen AE HPO if IMPACT already wins cleanly.  
7. If checkpoints **missing**, print `./hub generate` + sbatch chain from the v08 spec — **do not invent new hyperparameters**; user submits unless they asked you to submit.

---

## Success criteria

- [ ] M2 IMPACT vs scGen decoded gap numbers on disk + in a canvas  
- [ ] M1 same  
- [ ] Explicit one-sentence answer to the Goal question  
- [ ] No HPO; no VAE conversion; no LPS rabbit hole  

---

## Suggested canvas stats strip

| Stat | Source |
|------|--------|
| IMPACT decoded fgc | north-star |
| scGen decoded fgc | baseline |
| IMPACT frac_r2_closed_decoded | guardrail |
| recon_target_r2_pergene (shared AE) | identity honesty |

---

## Handoff

- **→ Mentor / human:** atlases + decision sentence  
- **→ C:** “B owns these run_ids; do not overwrite”  
- **→ D:** if D wants atlas instead of LPS, use M2 v08 AE freeze path from B’s notes

# Plan C — Paper-like scGen VAE on the human–mouse atlas (scaffolded in parallel)

**Owner agent:** 1 research/engineering agent  
**Parallel with:** A, B, D — **hard fence** against Plan B’s hub AE-scGen trees  
**Deliverable:** Design + stub configs/scripts + gap analysis; optional dry-run; **no** overwriting v08 hub `scgen/`  
**ETA:** large (treat this sprint as scaffold + feasibility, not full Fig.5-on-Tabula completion)

---

## Background (read this before doing anything)

Two different things are called “scGen” in this repo:

1. **Lotfollahi paper scGen (Stage 0 / Fig. 5)** — TensorFlow **VAE** (`VAEArith`), width 800–800, `z=100`, dropout 0.2, KL weight α≈5e-5, latent arithmetic (two-path / average-δ). Replicated on **Hagai LPS**, 6619 genes, hold out **rat LPS** with rat unst **in** train. Achieves mean `r2_all≈0.91` with **weak** recon (`recon_target_r2_pergene≈0.086`) and **negative** decoded MMD gap. Lesson: mean matching ≠ cloud matching; identity baseline was already `r2_identity≈0.867`.

2. **Hub / CellOT “scGen”** — PyTorch **AE** (`beta: 0`), `[512,512]`, `z=50`, mean shift. This is what `./hub generate` trains on atlas v08 next to IMPACT_CellOT. It is the fair baseline for Bunne’s “OT vs linear shift” claim, **not** a faithful VAE replica.

The user wants, longer-term, **three** models on the atlas they care about: paper-like VAE, AE+shift, and ICNN. Today hub only first-classes (2) and (3). Plan C explores bringing (1) onto **Tabula human–mouse** without destroying (2).

July 2026 mentor synthesis: LPS HPO / ETH lockstep are infinite games; return science judgment to atlas. Plan B re-scores existing AE+IMPACT. Plan C is the **optional third stack** — valuable, but must not block B.

Also remember: even a “perfect” recon does not guarantee good transport mean R² or MMD; AE/VAE training optimizes recon (+KL), not post-transport metrics. Do not sell VAE-on-atlas as automatically solving decoded gap.

---

## Goal

Produce a **feasible plan + isolated scaffold** for training/evaluating a **Lotfollahi-like VAE** on **v08 atlas data** (start with M2 OOD cells), scored with the **same honest metric atlas** as Stage 0 / Plan B (recon, mean R², raw/decoded MMD, JS).

This sprint succeeds if the next agent (or you in a follow-up) can train without touching hub AE paths.

---

## Non-goals

- Do **not** edit `specs/m1_modern.yaml`, `m2_baseline.yaml`, `atlas_cd8_uncapped.yaml`  
- Do **not** overwrite  
  `cellot/cellot_gpu/results/hvg_pearson_residuals_*_v08_ood/scgen/`  
- Do **not** change `speciesOT/hub` so that `family=scgen` becomes a VAE  
- Do **not** require matching Stage 0 `r2_all=0.91` on atlas (different biology/split)  
- No unbalanced OT (Plan D)

---

## Hard fence (read twice)

| Allowed | Forbidden |
|---------|-----------|
| New result root e.g. `results/atlas_paper_vae_m2_v08_ood/` | Writing into existing v08 `scgen/` or `impact_cellot/` |
| New spec e.g. `specs/atlas_paper_vae_m2_v08.yaml` with a **new tag** | Renaming hub generate to emit VAE as `scgen` |
| TF env / separate conda (Stage 0 used TF1 / scgen_tf paths) | Breaking CellOT_gpu AE training for Plan B |
| Read-only use of v08 `.h5ad` | Re-prep that changes v08 fingerprint without a new tag |

If unsure: **new tag + new directory**. Always.

---

## Required reading

1. `scgen-cellot-ablation/scripts/04_stage0_fig5_eval.py` + `results/stage0/metrics.json`  
2. `scgen-cellot-ablation/scgen-reproducibility/code/scgen/models/_vae.py` (arch)  
3. `AGENTS.md` + `logs/research_logs/research_log_2026-07-20.txt`  
4. `specs/m2_baseline.yaml` (data contract to **mirror**, not overwrite)  
5. Plan A deliverable confusion table (if present)  
6. `.cursor/skills/metric-atlas-canvas/SKILL.md`

---

## Design questions to answer in the deliverable

1. **Data:** Use existing `hvg_pearson_residuals_m2_v08.h5ad` as-is (1000 genes, Chromium filter, stratified OOD)? Or need 6619-style ortholog space? (Default recommendation: **same v08 h5ad** for apples-to-apples vs Plan B.)  
2. **Split:** Map atlas `toggle_ood` + condition mouse/human to VAE training masks analogous to “hold out human monocytes treated/target.” Be explicit about what is in train.  
3. **Prediction rule:** Single mean shift in z vs Fig.5 two-path (species+stim). Atlas task is species effect — **single δ** is the honest analogue of hub scGen; document choice.  
4. **Env:** Can TF VAE train on cluster? Point to Stage 0 env notes; prefer GPU if available.  
5. **Metrics:** Reuse `honest_metrics.py` / decoded_frame pattern so canvas matches Stage 0 sections 1–6.  
6. **IMPACT coupling:** Out of scope for this sprint to put ICNN on VAE latents — mention as Phase 2 only.

---

## Work steps (this sprint)

1. Write `DELIVERABLE_C_vae_atlas_design.md` covering the design questions.  
2. Propose directory layout + naming (`atlas_paper_vae_*`).  
3. Stub: config YAML (arch hyperparameters from Stage 0), train script entrypoint sketch, eval script that writes Stage-0-like `metrics.json`.  
4. **Dry-run:** load v08 h5ad in analysis/CellOT env; print shapes, split counts, confirm holdout definition — no full train required for success.  
5. Cost estimate: walltime, GPU mem, whether 300-epoch TF recipe transfers.  
6. Explicit risk list: env fragility, split mismatch, mean-R² fooling (report identity baseline always).  
7. Optional: one tiny overfit smoke train on 1k cells if env works — mark clearly as smoke, not result.

---

## Success criteria

- [ ] Design doc answers data/split/δ/env/metrics  
- [ ] Fence respected (no v08 hub scgen writes)  
- [ ] Stub paths exist and are documented  
- [ ] Dry-run split table printed  
- [ ] Clear “Phase 2 = full train + atlas metric canvas” handoff  

---

## Suggested Phase 2 (not this agent unless time left)

Full VAE train on M2 v08 → honest metrics → canvas `atlas-paper-vae-m2-v08-metrics.canvas.tsx` beside Plan B’s AE-scGen canvas → only then discuss VAE-latent IMPACT.

---

## Handoff

- **→ B:** “C will not touch your run_ids; compare later on matched v08 cells”  
- **→ Mentor:** third model is scaffolded, not yet a scoreboard claim

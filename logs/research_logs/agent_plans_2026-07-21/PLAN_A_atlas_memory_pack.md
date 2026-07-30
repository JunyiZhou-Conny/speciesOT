# Plan A — Atlas memory pack (read-only briefing)

**Owner agent:** 1 explore/write agent  
**Parallel with:** B, C, D (this plan must not submit jobs or edit training code)  
**Deliverable:** One mentor-ready canvas or markdown brief + pointer list  
**ETA:** short (hours)

---

## Background (read this before doing anything)

speciesOT’s long-term goal is **mouse → human** species transport (eventually composed with drug transport on the BCG line). For months the active work lived under `speciesOT/baseline/`: Tabula Muris × Tabula Sapiens, shared scGen-style AE + IMPACT_CellOT (ICNN OT in latent space), with scGen mean-shift as the baseline.

That atlas track did **not** mainly invent new architectures. It varied **scientific objectives** (which cell types are held out) and **preprocessing** (HVG flavor, renorm, assay filters, stratified OOD splits). CD4/CD8 ladders were judged “saturated”; attention moved to monocytes (**M1** / **M2**). Raw MMD on M1 looked paradoxical versus R²; investigation showed **AE round-trip tax** plus **Smart-seq2 / 10x mixing**. That produced the **v08** freeze (Chromium-only + stratified OOD) and the project north-star **`frac_gap_closed_decoded`**.

In June–July 2026 the team pivoted to **LPS paper replication** (scGen Fig. 5 Stage 0; Bunne CellOT Fig. 4). Mentor synthesis (2026-07-20) concluded several LPS/AE-HPO threads are **infinite games**. The decision is to **stop chasing ETH Fig. 4 lockstep / global G=6619 HPO**, keep the metric lessons, and return judgment to the **human–mouse atlas** — but first someone must **reconstitute institutional memory** of what atlas already showed, because it has been months.

Your job is that memory pack. You do **not** retrain. You do **not** change specs. You produce a clear brief so Plans B/C/D and the human mentor share the same facts.

Canonical rules: repo root `AGENTS.md`. Science/metrics: `docs/conceptual_framework.md` §1.2–1.4 and §5.9–5.10. Recent synthesis: `logs/research_logs/research_log_2026-07-20.txt`. Detail atlases (LPS era): Cursor canvases `scgen-fig5-stage0-metrics`, `bunne-fig4-crossspecies-metrics`, `mentor-paper-replication-synthesis`.

---

## Goal

Produce a **single atlas memory brief** that answers:

1. What were M1 vs M2 (and why M1≠“better” automatically)?  
2. What prep decisions are frozen in v08?  
3. What do we already believe about IMPACT vs scGen on v08 (decoded north-star)?  
4. Which artifacts should Plan B reopen first?  
5. What must Plan C **not** confuse with hub atlas scGen?

---

## Non-goals

- No `sbatch`, no `./hub generate`, no model training  
- No editing `specs/*.yaml` or result trees  
- No LPS re-analysis except one-line “why we left”  
- No unbalanced OT (Plan D)

---

## Hard constraints

- Read-only except writing your deliverable under  
  `logs/research_logs/agent_plans_2026-07-21/DELIVERABLE_A_atlas_memory.*`  
  and/or a Cursor canvas `atlas-v08-memory-pack.canvas.tsx`  
- Prefer citing paths + numbers from disk over memory  
- Follow metric-atlas skill section order if you make a canvas  
  (`.cursor/skills/metric-atlas-canvas/`)

---

## Required reading (in order)

1. `AGENTS.md` (north-star + v08 freeze)  
2. `docs/conceptual_framework.md` §1.2–1.4, §5.7–5.10  
3. `specs/m1_modern.yaml`, `specs/m2_baseline.yaml`, `specs/atlas_cd8_uncapped.yaml`  
4. `speciesOT/baseline/analysis/22_v08_results.ipynb` + `v08_scorecard_dual.csv`  
5. `speciesOT/baseline/analysis/20_m1_mmd_investigation.ipynb` (skim narrative)  
6. `speciesOT/baseline/analysis/21_data_imbalanced.ipynb` (Smart-seq2 → v08)  
7. `logs/research_logs/research_log_2026-06-09.txt`  
8. `logs/research_logs/research_log_2026-07-20.txt` (LPS pivot / stop list)

Optional: `01.5_*hvg*`, `hvg_flavor_run_matrix.md`, `meeting_notes_2026-04-30.md`.

---

## Definitions you must get right

| Tag | Holdout | Meaning |
|-----|---------|---------|
| **M1** | `CL:0000875` | Non-classical monocyte **alone** |
| **M2** | `CL:0000875` + `CL:0000576` | Non-classical + **generic** monocyte |
| **IMPACT** | — | Species effect mouse→human; cell-type OOD |
| **Hub scGen (atlas)** | — | PyTorch AE `beta=0` + mean shift — **not** Lotfollahi VAE |
| **Paper scGen** | — | TF VAE Fig.5 — LPS track only today |

---

## Work steps

1. Confirm v08 dataset + result dirs exist; note paths.  
2. Extract dual-frame scorecard numbers (raw vs decoded) for M1/M2/(optional CD8) IMPACT vs scGen at ncells=80.  
3. Write 1 page: “Why raw MMD lied on M1” (AE tax + assay mix) in plain language.  
4. Rank objectives clear→muddy (IMPACT species OOD vs abandoned cell-type OT; M2 vs saturated CD8).  
5. Produce **Top 10 reopen list** with absolute paths for Plan B.  
6. Explicit **confusion table**: Lotfollahi VAE vs hub AE-scGen vs IMPACT (for Plan C fence).  
7. End with 5 bullet “standing claims we can tell the mentor without new runs.”

---

## Success criteria

- [ ] Mentor could read only your deliverable and know M1/M2/v08/north-star  
- [ ] Every numeric claim has a file citation  
- [ ] Plan B’s first commands are obvious from your reopen list  
- [ ] Zero training / zero spec edits  

---

## Handoff to other plans

- **→ B:** reopen list + current best decoded numbers  
- **→ C:** “hub scGen ≠ VAE”; do not touch v08 scgen dirs  
- **→ D:** atlas vs LPS choice note (D may use either; A only documents)

# AGENTS.md — read this first

This is the **speciesOT** cross-species single-cell OT project (predict human cells from mouse via IMPACT_CellOT + scGen).

## Start here
**Read [`docs/agent_handoff_2026-06-05.md`](docs/agent_handoff_2026-06-05.md) top to bottom** — it's the full onboarding (what the project is, how to read the repo, environments, the metric framework, current status, and in-flight work). Then skim [`docs/hub_usage.md`](docs/hub_usage.md) and [`docs/conceptual_framework.md`](docs/conceptual_framework.md) (§5.5–§5.10).

## Hard rules (do not violate)
- **Never `git commit` or `git push` unless the user explicitly asks.** All current work is uncommitted on `main`; the `josh` remote is diverged — never force-push.
- **Everything routes through `./hub`** (CLI in `speciesOT/hub/`): `list`, `show`, `compare`, `prep`, `generate`, `metrics`, `handoff`. The hub never auto-submits sbatches — it prints the chain; the human (or you, only when asked) submits.
- **Two conda envs:** `CellOT` (torch 1.11, the hub/train/eval) and `analysis` (scanpy ≥1.12, for `./hub prep` HVG + notebooks). `cellot` is not pip-installed — set `PYTHONPATH=<repo>/cellot/cellot_gpu` to import it.
- **GPU jobs must pin V100** (`--constraint=v100`); the env's torch only supports ≤ sm_70. CPU is the safe fallback (`impact_train_device: cpu`).
- **Don't full-load the 43GB `tabula_*_all.h5ad` atlas** — use the backed prep path (`speciesOT/hub/prep_backed.py`, `source_backed: true`) as a high-mem batch job.
- **Judge models by `gap_above_floor` / `frac_gap_closed`** (floor/ceiling-normalized), not raw R²/MMD. See conceptual_framework §5.9.
- **`specs/*.yaml` are the source of truth.** `./hub spec dump` is lossy for "intent" fields (assay_filter, datasplit_stratify, device, ...) — clone the spec file instead of re-dumping when those matter.

## Current focus (2026-06-05)
v08 cleanup (enforced assay filter + stratified OOD split) done for m1/m2; an uncapped full-atlas CD8 rebuild is prepping (batch job `19449000`). Details + next actions in the handoff doc §7/§10.

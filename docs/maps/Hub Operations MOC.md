---
title: Hub Operations MOC
type: moc
tags:
  - moc
  - hub
---

# Hub Operations MOC

The **hub map** — everything routes through `./hub`. This is the playground where ideas
from the [[Concepts MOC]] become experiments. The hub never auto-submits SLURM jobs; it
prints the chain and *you* submit (a deliberate safety boundary).

## The spine (one experiment, end to end)

```
        ┌─────────────┐   edit YAML    ┌──────────────┐   build .h5ad   ┌──────────────┐
        │ [[hub spec]]│ ─────────────▶ │  specs/*.yaml │ ──────────────▶ │ [[hub prep]] │
        │   (dump)    │                │ SOURCE OF TRUTH│                │              │
        └─────────────┘                └──────────────┘                 └──────┬───────┘
                                                                                │
   inspect ◀───────────────┐                                                    ▼
 [[hub list]] [[hub show]]  │        submit printed sbatch chain        ┌────────────────┐
 [[hub compare]]            └────────────── (you) ◀──────────────────── │ [[hub generate]]│
        ▲                                                               │ configs+sbatch │
        │   write sidecar metrics                                       └────────┬───────┘
        │                                                                        │ train + eval
   ┌──────────────┐         ┌──────────────┐         regenerate graph           ▼
   │[[hub metrics]]│◀────────│  evals on disk│ ──────────────────────▶ [[hub vault]] → Obsidian
   └──────────────┘         └──────────────┘
```

## Commands

| Command | One-liner | Note |
|---|---|---|
| `list` | filter/sort the catalog of all runs | [[hub list]] |
| `show` | full detail for one run | [[hub show]] |
| `compare A B` | spec deltas (cause) + metric deltas (effect) | [[hub compare]] |
| `spec dump` | bootstrap a YAML spec from a trained run (**lossy** — clone the file instead when intent fields matter) | [[hub spec]] |
| `prep` | build the training `.h5ad` from a spec (enforces [[assay filter]]) | [[hub prep]] |
| `generate` | write configs + sbatches, print the submit chain | [[hub generate]] |
| `metrics` | write `extended_metrics.csv` ([[frac_gap_closed]], floor/ceiling, JS) | [[hub metrics]] |
| `vault` | regenerate the Obsidian experiment notes (this graph) | [[hub vault]] |
| `card` / `attach-figures` | rich HPC-only cards + figure links | — |
| `handoff` | the boundary artifact for the mentor | — |

## Gotchas worth internalizing

- **`spec dump` is lossy** — fields not in `config.yaml` (assay_filter, datasplit_stratify,
  device, …) fall back to defaults. **Clone the spec file** when those matter.
- **GPU jobs must pin V100** (`--constraint=v100`); the env's torch is ≤ sm_70.
- **Don't full-load the 43 GB atlas** — use `source_backed: true` (the backed prep path).
- **Judge by [[frac_gap_closed]] / `gap_above_floor`**, not raw R²/MMD.

## See also

- The ideas that drive new runs: [[Concepts MOC]]
- The runs themselves: [[Hub Experiments MOC]]
- Full prose: `hub_usage.md` · `hub_design.md` · `hub_handoff.md`

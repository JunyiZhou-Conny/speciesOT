---
title: the four-corner goal
type: concept
tags:
  - concept
  - thesis
source_doc: "conceptual_framework.md §3"
---

# the four-corner goal

The eventual scientific target. We can observe three corners; we want to predict the
fourth.

```
                   T_drug (learnable on mouse)
   mouse_untreated ─────────────────────────► mouse_treated
        │                                            │
   T_species                                    T_species
        ▼                                            ▼
   human_untreated ─────────────────────────► human_treated
                   T_drug' (desired, unobserved)
```

We have mouse-untreated, mouse-treated, human-untreated in real data. We want
**human-treated**. Three candidate routes:

- **(a) species-invariant drug effect** — apply mouse-learned `T_drug` to human. Strong,
  testable.
- **(b) compose transports** — `T_drug' ≈ T_species ∘ T_drug ∘ T_species⁻¹`. Needs
  invertibility (problematic for ICNN-OT) and that composition is meaningful.
- **(c) joint conditional model** — one model conditioned on (species, treatment), the
  missing corner imputed during training.

## Where we are today

Only the **species** leg ([[IMPACT_CellOT]] vs [[scGen]]) is being measured — the whole
current matrix. The **drug** leg is the exploratory BCG line (notebooks `16/17`). The
**composition** is future work. Current matrix work = making each species transport
reliable in isolation before composing anything.

## Related

- The current building block: [[IMPACT_CellOT]]
- Overview of the pieces: [[the three model variants]]

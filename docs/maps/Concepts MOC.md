---
title: Concepts MOC
type: moc
tags:
  - moc
---

# Concepts MOC

The front door to the **spider-web** — the intuitions and heuristics picked up along the
way, each an atomic note that links to its neighbors. Start anywhere and follow links;
the [[#The graph|graph view]] shows the whole web at once.

These are peeled from the long-form `conceptual_framework.md` (still the source of
truth). When you learn something new, add a note here and link it — that's how the web
grows.

## Models & framing

- [[the three model variants]] — one architecture, three jobs
- [[IMPACT_CellOT]] — the main model (mouse → human species transport)
- [[scGen]] — the baseline *and* IMPACT's autoencoder
- [[the four-corner goal]] — the endgame (predict human-treated)

## Metrics (how we judge a run)

- [[MMD floor and ceiling]] — the reference frame for MMD
- [[frac_gap_closed]] — the headline MMD metric
- [[AE round-trip tax]] — why IMPACT's `frac_gap_closed` can lie

## Preprocessing & evaluation gotchas

- [[assay filter]] — the enforced single-platform-per-species treatment
- [[OOD split stratification]] — the unstratified holdout split drift
- [[OOD vs IID evaluation]] — the overloaded "OOD" word

## The graph

Open the graph view (left ribbon) and color-group by tag (`#concept`, `#metric`,
`#model`, `#gotcha`). Greyed nodes are concepts referenced but not yet written — your
to-write list. Candidates to add next: `renorm vs stale`, `the --embedding/--where bug
(§5.5)`, `latent vs data space (§5.6)`, `multi-seed variance (§5.8)`, `BCG drug line`.

## See also

- [[Hub Operations MOC]] — the playground where these ideas become experiments
- [[Hub Experiments MOC]] — the runs that exhibit these concepts

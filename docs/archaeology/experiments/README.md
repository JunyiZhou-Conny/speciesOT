# Experiment families

Each family page follows the same template:

- question
- setup
- what was done and what came out
- verdict
- why it stopped
- problems
- terms
- what the package needs
- open questions
- sources

Each page was drafted by one agent from the primary record and then checked
claim by claim by a second, independent agent (172–330 claims per page; 18–31
corrections each). The README of this folder's parent explains the evidence
labels ([../README.md](../README.md)).

Status values: **worked** · **partly worked** · **did not work** ·
**inconclusive** · **abandoned unfinished** · **infrastructure**.

## Josh's cross-species cell-matching work

| id | family | period | status | in one line |
|---|---|---|---|---|
| [F01](F01-gw-feasibility-and-simulations.md) | Gromov-Wasserstein (GW) feasibility on real data, and simulations of its failure modes | 2024-06 → 2026-02 | partly worked | Label-free GW paired mouse and human cells at or below chance in most runs. Simulations named the main failure, "symmetry mismatch"; the seeded-anchor fix rests on few runs. |
| [F02](F02-perturbot.md) | PerturbOT: label-constrained OT pairing | 2025-10 → 2026-07 | did not work | The ε ≈ 1e-8 "gain" came only from failed (NaN) solver runs. Converged pairs did no better than random same-type pairs, and the held-out cell type was never predicted. |
| [F03](F03-labels-ontology-and-distances.md) | Labels, ontologies and distribution distances on immune data | 2025-10 → 2026-04 | partly worked | Cross-species matching scored about as well as always guessing the most common type. The lasting product is the exact ontology matcher used for all later atlas data. |
| [F04](F04-gene-priors-and-standard-ot.md) | Gene-level priors: ortholog FGW, gene correlations, learned weights, plain OT, AGW | 2026-02 → 2026-06 | partly worked | The best result (90.1% on 213 lung cells) used the scored labels to choose genes. Learned weights never helped; plain OT in the 1,000-gene space reached 18–25%. |

## Conny's scGen / CellOT translation work

| id | family | period | status | in one line |
|---|---|---|---|---|
| [F05](F05-first-cellot-runs-on-lps.md) | First CellOT runs on the cross-species LPS data | 2026-03-04 → 03-16 | abandoned unfinished | A pipeline shake-down scored only in code space, with no baseline. Later docs describe these runs wrongly. |
| [F06](F06-tcell-holdouts-speciesot-v1.md) | speciesot_v1: T-cell holdouts; scGen vs IMPACT-OR vs cell-type CellOT | 2026-03-16 → 05-10 | inconclusive | IMPACT-OR matched human CD8 means best (r² 0.72), but on mis-scaled data, with leaky HVGs, one seed and no do-nothing baseline. |
| [F07](F07-toggle-iid-ood-and-renorm.md) | Toggle IID vs OOD (T1–T4, M1–M4) and the renormalisation fix | 2026-04-08 → 04-21 | partly worked | The scale bug was found and fixed. The IID encoder had seen the evaluation cells, and spaces were mixed, so neither the IID–OOD gap nor the renorm gain was measured cleanly. |
| [F08](F08-hvg-flavor-matrix.md) | The five-flavor HVG matrix | 2026-04-24 → 05-12 | partly worked | Within a flavor, in latent space, IMPACT beat the baseline on R² in 19/20 IID but 11/20 OOD cases (on MMD in 20/20 and 17/20). 29 of the 40 "data_space" IMPACT evaluations are actually latent. |
| [F09](F09-hub-and-metrics-infrastructure.md) | The `hub` CLI, specs, vault and metric sidecars | 2026-05-08 → 08-18 | infrastructure | It worked as a launcher and as the home of the decoded metric. Its saved views went stale, and its scorecard ranks incomparable numbers. |
| [F10](F10-monocytes-floor-ceiling-and-v08.md) | Monocyte holdouts, MMD floor/ceiling, decoded metrics, the v08 cut, capped vs uncapped | 2026-05-26 → 06-11 | partly worked | On v08, IMPACT beats the scGen-style baseline on MMD in every cut and improves gene means a lot. But unchanged mouse cells are about as close as a distribution, and score 0.874 on the decoded metric against IMPACT's 0.897. |
| [F11](F11-bunne-lps-replication.md) | Replicating the CellOT paper's cross-species LPS result | 2026-06-12 → 06-22 | partly worked | The rat MMD order was reversed and the mouse gap was much smaller than published. In the authors' own file, doing nothing has the best mean correlation. |
| [F12](F12-scgen-fig5-stage0-and-stage1.md) | scGen Fig. 5 reproduction (Stage 0) and the split × gene-set grid (Stage 1) | 2026-06-15 → 07-23 | partly worked | Paper scGen reproduced (0.907 vs 0.910), but doing nothing scores 0.867. The training split, not the gene set, explains most of the gap between the two papers; paper scGen was never run on the hard split. |
| [F13](F13-autoresearch-loop.md) | The autoresearch loop: 338 logged LPS experiments and the ICNN ladder | 2026-06-22 → 07-18 | partly worked | On MMD, a plain gene-space mean shift beat the autoencoder pipeline almost everywhere. The one CellOT-on-autoencoder run lost to a mean shift. |
| [F14](F14-july-plans-a-to-d.md) | July Plans A–D: atlas scoreboard, paper VAE on the atlas, unbalanced OT | 2026-07-21 → 07-30 | partly worked | Re-reading the existing single runs (Plans A, B) confirmed IMPACT over the scGen-style baseline on v08. The paper VAE was not better. The unbalanced-OT outputs are lost. |
| [F15](F15-ae-repair-rounds-and-calibration.md) | Repairing the paper-scGen autoencoder; variance checks; devar | 2026-07-23 → 07-30 | did not work | No variant passed its own rules. The variance correction failed its permuted control, so `AGENTS.md`'s "E3 helps" is out of date. |
| [F16](F16-deployment-models-and-mixhvg.md) | Deployment models, external-target evaluation, mixhvg | 2026-05-08 → 08-18 | partly worked | The tooling passed its own checks, but no deployment model was scored on held-out atlas cells against a floor, ceiling or identity baseline. The mixhvg result is inconclusive. |

## Joint work and the package

| id | family | period | status | in one line |
|---|---|---|---|---|
| [F17](F17-bcg-application.md) | The BCG application (mouse → human vaccination response of blood stem cells) | 2026-05-05 → 08-26 | abandoned unfinished | Both models' predictions fit worse (r² 0.50, 0.49) than the unchanged mouse-treated cells (0.63). No treatment map was ever built. |
| [F18](F18-oop-package.md) | The OOP package `src/speciesot`: every version | 2026-09-03 → 10-15 | infrastructure | No version runs end to end. The package's R² equals only Stage 0's reconstruction metric, and its MMD matches no earlier setting, so neither reproduces an earlier prediction score. Two AI-built lines were never proposed to Josh. |

Cross-cutting pages: [timeline](../timeline.md) · [critique](../critique.md) ·
[reference experiments](../reference_experiments.md) · [models](../models.md)
· [metrics](../metrics.md) · [data](../data.md) · [glossary](../glossary.md) ·
[sources](../sources.md) · [open questions](../open_questions.md).

Every tracked notebook, spec, script and log is tagged with its family, or
with "vendored CellOT", in [`../inventory.csv`](../inventory.csv) (column
`family`).

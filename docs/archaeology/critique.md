# What went wrong, and what it means for the conclusions

This page collects the methodological problems that recur across the
experiment families, ranked by how much they weaken the project's conclusions.
Each problem names the families where it occurs; the family pages hold the
evidence. Problems specific to one family are listed only on its page, under
"Problems in how it was done". [What went right](#what-went-right) is at the
end.

## The short version

1. **The baseline was usually missing, and where it exists it often wins.**
   Most "model A beats model B" statements never asked whether either beats
   doing nothing. Where a do-nothing or plain-mean-shift baseline was scored,
   it was often as good as or better than the models. This includes the
   CellOT authors' own results file.
2. **The 50-dimensional autoencoder limited everything built on it.**
   Every hub model, scGen-style or CellOT, predicts through the same kind of
   autoencoder. That autoencoder keeps only a small part of the cell-to-cell
   variation. Comparisons between transport maps in its latent space are
   capped by it.
3. **Numbers with the same name are often different computations.** r vs r²,
   MMD at different sample sizes, latent vs gene space. Several apparent
   improvements were artifacts of this.
4. **Almost every result is one unseeded run.** Where a rerun exists, the
   spread is often as large as the differences being claimed.
5. **AI-written summaries ran ahead of the evidence.** Concept notes,
   `AGENTS.md`, run cards and the scorecard contain claims that the result
   files contradict.

The result: on the evidence in this record, no method in the project was shown
to predict human cells better than a simple baseline on a fair test.
Transport maps did improve gene *means* over unchanged mouse cells on the
atlas. They did not bring the *distribution* of predicted cells reliably closer
to real human cells, and on the one real application (BCG) both models scored
worse than doing nothing.

## 1. Missing or losing baselines (highest impact)

| where | what the record shows |
|---|---|
| [F06](experiments/F06-tcell-holdouts-speciesot-v1.md) | IMPACT-OR beat the other two models on the CD8 holdout. No do-nothing score was ever computed for these runs, so it is unknown whether any model helped. |
| [F10](experiments/F10-monocytes-floor-ceiling-and-v08.md), [F16](experiments/F16-deployment-models-and-mixhvg.md) | On M1 v08, IMPACT closes 0.897 of the decoded gap, and *unchanged raw mouse cells* close 0.874. Their MMD to the real human cells is about the same (0.104 vs 0.109). IMPACT does improve the gene means (R² 0.92 vs 0.55). |
| [F12](experiments/F12-scgen-fig5-stage0-and-stage1.md) | Paper scGen reproduces Fig. 5 (r2_all 0.907), but doing nothing already scores 0.867. As a distribution, its prediction is further from the real LPS rat cells than the unstimulated input is (MMD 0.201 vs 0.045). On the out-of-distribution split, CellOT's autoencoder scGen scores at or below doing nothing (0.654 vs 0.866 at 6,619 genes). |
| [F11](experiments/F11-bunne-lps-replication.md), [F12](experiments/F12-scgen-fig5-stage0-and-stage1.md) | In the CellOT authors' own per-species file (`ablation:species.csv`, OOD rat), doing nothing has the highest mean correlation: r 0.798, against scGen 0.693 and CellOT 0.677. scGen's MMD is worse than doing nothing (0.265 vs 0.253). So CellOT's MMD win (0.234) is a win over a baseline that is itself worse than doing nothing. The paper's Fig. 4f does not show the identity baseline. |
| [F13](experiments/F13-autoresearch-loop.md) | A plain mean shift in gene space (`raw_shift`) beat CellOT's autoencoder pipeline almost everywhere: only 11 of 301 autoencoder runs beat it. The one CellOT run on a frozen autoencoder lost to a mean shift on the same latent space. |
| [F17](experiments/F17-bcg-application.md) | On BCG, both models' predicted human-treated profiles fit worse (r² 0.50, 0.49) than the unchanged mouse-treated cells (0.63). Human untreated cells alone score 0.97. |
| [F01](experiments/F01-gw-feasibility-and-simulations.md)–[F04](experiments/F04-gene-priors-and-standard-ot.md) | Josh's cross-species pairing accuracies were rarely set against chance or the majority-class guess. Where they were, label-free GW scored about the same as always guessing the most common type (e.g. 45.5% vs 44.2%). |

**For the package:** every evaluation should report the identity baseline,
and where meaningful the `observed` reference and a plain mean shift, on the
same cells and in the same frame as the model. The `IdentityModel` already
exists ([F18](experiments/F18-oop-package.md)).

## 2. The autoencoder bottleneck (high impact)

- At 6,619 genes no deep autoencoder recipe reconstructed held-out cells well
  (per-gene R² ≤ 0.13). The default 50-d autoencoder made predictions worse
  than skipping it ([F13](experiments/F13-autoresearch-loop.md)).
- The paper VAE's decoder keeps about 4% of within-group variance on LPS rat
  cells; atlas slices keep 3–30% ([F15](experiments/F15-ae-repair-rounds-and-calibration.md)).
  Decoded predictions on the CD8 holdout had standard deviations more than 10×
  too small for 9 of 16 CD8-distinctive genes ([F06](experiments/F06-tcell-holdouts-speciesot-v1.md)).
- On v08, decoding accounts for about 46–92% of IMPACT's distance from the
  real cells above the raw floor ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)).
- No repair worked. Neither the dropout and KL rounds nor the extra loss
  terms helped, and the post-hoc variance correction gave the same gain with
  shuffled gene labels or a single global factor
  ([F15](experiments/F15-ae-repair-rounds-and-calibration.md)).

What this means: an OT map in this latent space can only be as good as the
round trip through the autoencoder. "IMPACT beats scGen" on the atlas
([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md),
[F14](experiments/F14-july-plans-a-to-d.md)) compares two maps on top of the
same lossy round trip. It is a real result within that setting, not evidence
that either predicts human cells well.

**For the package:** keep transport and representation separable, and test a
gene-space mean shift and a linear/Gaussian OT baseline before any neural
model.

## 3. Inconsistent metric definitions (high impact)

Details in [metrics.md](metrics.md). The ones that changed conclusions:

- **r vs r².** `evals.csv`'s `r2-means` is unsquared r. An r-vs-r² mix-up
  produced an apparent improvement between notebooks 06 and 08
  ([F06](experiments/F06-tcell-holdouts-speciesot-v1.md)). Notebook 10 and the
  hub cards square at different steps: (mean r)² vs mean(r²)
  ([F07](experiments/F07-toggle-iid-ood-and-renorm.md)).
- **Biased MMD at different n.** The estimator's floor is about 2/n (0.064 at
  n = 30, 0.024 at n = 80) ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)).
  Even so:
  - scGen was scored on full clouds and IMPACT on subsamples
    ([F07](experiments/F07-toggle-iid-ood-and-renorm.md));
  - flavors in one matrix used different n
    ([F08](experiments/F08-hvg-flavor-matrix.md), [metrics.md](metrics.md) §2);
  - the hub's headline is "at the largest n", whatever that was
    ([F09](experiments/F09-hub-and-metrics-infrastructure.md)).
- **One fraction, many denominators.** The scorecard ranks 17 runs from nine
  datasets on `frac_gap_closed_decoded`, whose denominator varies 3.5-fold
  and which reaches 1.032
  ([F09](experiments/F09-hub-and-metrics-infrastructure.md),
  [F16](experiments/F16-deployment-models-and-mixhvg.md)). In the autoresearch
  runs the same metric was NaN in 42, above 1 in 16 and below 0 in 46 of 301
  ([F13](experiments/F13-autoresearch-loop.md)).
- **The package's metrics match nothing.** `R2Evaluation` is a paired-cell
  metric, and `MMDEvaluation` uses one bandwidth on full clouds
  ([F18](experiments/F18-oop-package.md)).

## 4. Wrong or mixed evaluation space (high impact where it occurs)

- 29 of the 40 IMPACT "data_space" evaluations in the HVG matrix are actually
  latent-space numbers. The hub reads the space from the folder name
  ([F08](experiments/F08-hvg-flavor-matrix.md),
  [F09](experiments/F09-hub-and-metrics-infrastructure.md)).
- The renorm-vs-stale comparison changed the data and the evaluation space at
  once ([F07](experiments/F07-toggle-iid-ood-and-renorm.md)). So did the
  capped-vs-uncapped comparison ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)).
- The first LPS model was scored only in code space
  ([F05](experiments/F05-first-cellot-runs-on-lps.md)). Toggle IID and OOD
  were scored in two different latent spaces
  ([F07](experiments/F07-toggle-iid-ood-and-renorm.md)).

**For the package:** store the frame, n, number of draws and seed as columns
of every result. Never infer them from a path.

## 5. Leakage (medium–high impact)

- The toggle IID encoder was trained on the evaluation cells
  ([F07](experiments/F07-toggle-iid-ood-and-renorm.md)).
- In speciesot_v1, HVGs were chosen with the held-out cells included
  ([F06](experiments/F06-tcell-holdouts-speciesot-v1.md)).
- The best pairing number (90.1%) used the scored labels to rank genes and to
  balance the cell sets ([F04](experiments/F04-gene-priors-and-standard-ot.md)).
  OTDD and CellTypist "wins" used labels on both sides
  ([F03](experiments/F03-labels-ontology-and-distances.md)).
- Settings were chosen on the test set
  ([F04](experiments/F04-gene-priors-and-standard-ot.md)), and checkpoints on
  one test batch ([F05](experiments/F05-first-cellot-runs-on-lps.md),
  [F06](experiments/F06-tcell-holdouts-speciesot-v1.md),
  [F11](experiments/F11-bunne-lps-replication.md)).

## 6. One run, no seeds (high impact on small differences)

Nearly every number in the project is a single unseeded training run. The
autoresearch seed wiring was a known, unfixed bug
([F13](experiments/F13-autoresearch-loop.md)). Where reruns exist, they show
how large the noise is:

- the top-100 DEG R² of paper scGen was 0.742 in one training and 0.694 in
  another ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md));
- Stage 1 arm reruns differ by up to 0.05
  ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md));
- a seeded and an unseeded run of one autoencoder config differ by up to 0.05
  in fgc ([F13](experiments/F13-autoresearch-loop.md)).

Differences smaller than these spreads, which includes most model and flavor
rankings, are not established.

## 7. Data preparation errors (high impact for the affected families)

- **Mouse vs human scale mismatch.** Until 2026-04-20 the mouse input was
  clipped at 10 and scaled per gene ([F06](experiments/F06-tcell-holdouts-speciesot-v1.md),
  [F07](experiments/F07-toggle-iid-ood-and-renorm.md)). Josh's FGW work
  re-normalized already transformed values, differently in each species
  ([F04](experiments/F04-gene-priors-and-standard-ot.md)).
- **Mixed platforms.** Smart-seq2 cells were mixed with droplet data until the
  v08 assay filter ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)).
- **Unpinned ortholog tables.** They came from live BioMart queries
  ([F04](experiments/F04-gene-priors-and-standard-ot.md),
  [F08](experiments/F08-hvg-flavor-matrix.md)). The only cache file was
  gitignored and is not in the backup
  ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)).
- **BCG preprocessing.** The mouse mitochondrial filter tested the wrong
  column and removed nothing. Model inputs were normalized differently from
  the training data, and only the predictions went through the autoencoder
  ([F17](experiments/F17-bcg-application.md)).

## 8. Failed solvers read as results (high impact for Josh's OT work)

- PerturbOT's headline ε ≈ 1e-8 gain came only from runs whose solver
  returned a NaN cost ([F02](experiments/F02-perturbot.md)).
- Several of the higher OTDD and CellTypist numbers came from non-converged
  Sinkhorn runs ([F03](experiments/F03-labels-ontology-and-distances.md)).
- The ε sweep that seemed to favour ε ≈ 0.1 probably never varied ε
  ([F01](experiments/F01-gw-feasibility-and-simulations.md)).

**For the package:** if OT pairing is ever added, check convergence and that
the cost is finite before using a plan.

## 9. Documents that contradict the record (medium impact; misleading)

- `AGENTS.md` says the variance correction (E3) "found the first intervention
  that helps". The result files and the 07-27 log record it failing its
  permuted control and being closed
  ([F15](experiments/F15-ae-repair-rounds-and-calibration.md)).
- `docs/concepts/scGen.md` calls the hub's scGen "a VAE"; it is a
  deterministic autoencoder ([models.md](models.md)).
- The concept note on the first LPS runs gets their direction, space and gene
  count wrong ([F05](experiments/F05-first-cellot-runs-on-lps.md)).
- "The three model variants" says the paper's own CellOT task was never run;
  it was, twice ([F05](experiments/F05-first-cellot-runs-on-lps.md),
  [F11](experiments/F11-bunne-lps-replication.md)).
- The mixhvg spec compares its floor to the wrong reference
  ([F16](experiments/F16-deployment-models-and-mixhvg.md)).
- The runbook mislabels the default model set
  ([F16](experiments/F16-deployment-models-and-mixhvg.md)), and a deployment
  spec claims training on "all" cells
  ([F16](experiments/F16-deployment-models-and-mixhvg.md)).
- The vault and model cards froze in May and June, so the Obsidian
  leaderboard is empty ([F09](experiments/F09-hub-and-metrics-infrastructure.md)).
- The autoresearch loop is described as "autonomous", but its director ran
  once, rule-based, and its LLM was never used
  ([F13](experiments/F13-autoresearch-loop.md)).

**For the package and the repo:** treat `AGENTS.md`, `docs/concepts/` and
`docs/experiments/` as superseded where this archaeology disagrees. Updating
them is listed in [open_questions.md](open_questions.md); this branch does
not change them.

## 10. Lost or unpreserved work (medium impact)

- The unbalanced-OT outputs are lost: the jobs completed, but the folders are
  empty ([F14](experiments/F14-july-plans-a-to-d.md)). So is the library
  OTDD code that ran ([F03](experiments/F03-labels-ontology-and-distances.md)).
- The late-July ablation code exists only uncommitted on FASRC
  ([sources.md](sources.md)).
- The metric canvases exist only in a Cursor project folder
  ([F15](experiments/F15-ae-repair-rounds-and-calibration.md)). Several
  notebooks' saved code no longer produces their saved outputs
  ([F04](experiments/F04-gene-priors-and-standard-ot.md),
  [F17](experiments/F17-bcg-application.md)).

## 11. Too many changes at once (medium impact)

- v07 → v08 changed the platforms, the split, half of the genes and the
  evaluation ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)).
- The mixhvg "one-factor" ablation changed both selection and evaluation
  ([F16](experiments/F16-deployment-models-and-mixhvg.md)).
- The Bunne replication differs from the paper in data, gene selection, split
  and checkpoint rule ([F11](experiments/F11-bunne-lps-replication.md)).
- Stage 1 never ran paper scGen on the hard split, which is the comparison
  that would settle the baseline question
  ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md)).

## 12. Tooling outgrew validation (process)

AI agents built a CLI, a vault, an autoresearch harness, a ten-PR package
stack and a second package repo within weeks
([F09](experiments/F09-hub-and-metrics-infrastructure.md),
[F13](experiments/F13-autoresearch-loop.md),
[F18](experiments/F18-oop-package.md)). Each produced more output than was
ever checked. The saved views went stale, the scorecard ranked incomparable
numbers, and two package lines were never reviewed or proposed to Josh. The
mentor's plan, a small package written by hand and judged against
reproduced experiments, is the corrective.

## What went right

- The **floor/ceiling framework** correctly identified the biased-MMD offset
  and the decoding cost, and its code agrees with an independent
  implementation to 1e-8
  ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md),
  [F09](experiments/F09-hub-and-metrics-infrastructure.md)).
- The **v08 cut** (assay filter, species-stratified split) fixed real data
  problems, and its counts reproduce exactly
  ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)).
- **Stage 0** faithfully reproduced the scGen paper with the authors' own
  code and settings, and added the missing identity baseline
  ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md)).
- The **late-July study** pre-registered pass rules and used a permuted
  control. That control is what caught the false positive
  ([F15](experiments/F15-ae-repair-rounds-and-calibration.md)).
- The **deployment tooling** guards the gene axis and bakes the shift into
  the model folder ([F16](experiments/F16-deployment-models-and-mixhvg.md)).
- **Josh's skeleton** gives the package a small, fair core. Every model is
  scored on the same test cells against an identity baseline
  ([F18](experiments/F18-oop-package.md)).

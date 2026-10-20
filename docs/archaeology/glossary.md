# Glossary

Many labels in this project mean different things in different places. Each
entry below gives the meaning and where it applies, and links to the family
page with the evidence ([experiments/](experiments/README.md)). Labels that
were reused are marked **(overloaded)**.

## Biology and data

| term | meaning |
|---|---|
| single-cell RNA-seq, AnnData, `.h5ad` | Gene expression measured per cell. AnnData is the Python container: a cells × genes matrix `.X`, a cell table `.obs`, a gene table `.var`, and optional `layers` and `.raw`. `.h5ad` is its file format. |
| `.X` vs `.raw` vs `layers['counts']` | Josh's atlas files store transformed values in `.X` and raw counts in `.raw`. The mouse `.X` was also clipped at 10 and, judging from its value pattern, scaled per gene; this caused the April scale bug ([F07](experiments/F07-toggle-iid-ood-and-renorm.md)). In the batch-corrected BCG files, `layers['counts']` holds scANVI-decoded "posed counts". These are reconstructions, not measured counts ([F17](experiments/F17-bcg-application.md)). |
| Tabula Muris / Tabula Sapiens (TM / TS) | Mouse and human cell atlases; the main mouse→human data. Raw files are in Josh's FASRC folder ([sources.md](sources.md)). |
| capped / uncapped, `1000-cap` | Josh's `sampled_*_shared.h5ad` keep at most 1,000 cells per cell type and species ("capped"). "Uncapped" cuts start from the full `tabula_*_all.h5ad` files ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)). |
| one-to-one orthologs, BioMart | Genes with exactly one counterpart in the other species. The tables came from a live BioMart query that was never pinned to a release ([F08](experiments/F08-hvg-flavor-matrix.md)). The atlas pipeline uses 14,451 of them. |
| HVG, HVG flavor | Highly variable genes: the 1,000 genes kept as model input. A flavor is the scanpy ranking recipe (seurat, cell_ranger, seurat_v3, seurat_v3_paper, pearson_residuals), plus the ensemble `mixhvg` ([F08](experiments/F08-hvg-flavor-matrix.md), [F16](experiments/F16-deployment-models-and-mixhvg.md)). |
| assay filter | Keep only one droplet platform per species: mouse 10x 3' v2, human 10x 3' v3. Smart-seq2 cells had caused much of the M1 "scatter" ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)). |
| `shared_cell_type` | Josh's coarse cell type shared by both species, e.g. "T cell", "monocyte" ([F01](experiments/F01-gw-feasibility-and-simulations.md)–[F04](experiments/F04-gene-priors-and-standard-ot.md)). |
| identity **(overloaded)** | (1) The "do nothing" baseline: predict that the target looks like the unchanged source. (2) In Josh's matcher, the pair (cell-type ontology ID, tissue ontology ID) ([F03](experiments/F03-labels-ontology-and-distances.md)). (3) In the summer AE work, how well an autoencoder reproduces its own input, as in "identity panel" ([F15](experiments/F15-ae-repair-rounds-and-calibration.md)). |
| matched cells | An equal number of mouse and human cells per (cell type, tissue) identity, made by Josh's ontology matcher. It became the cell-pairing step for all atlas data ([F03](experiments/F03-labels-ontology-and-distances.md)). |
| LPS, `unst`, `LPS6` | The cross-species LPS dataset (Hagai et al. 2018): mononuclear phagocytes from mouse, rat, rabbit and pig. `unst` = unstimulated, `LPS6` = 6 h of LPS. The CellOT authors' config calls the label `LPS` ([F05](experiments/F05-first-cellot-runs-on-lps.md), [F11](experiments/F11-bunne-lps-replication.md)). |
| BCG, PBS, LT-HSC, MPP, d0 / d90 | BCG is a tuberculosis vaccine and PBS its mouse control. LT-HSC (long-term haematopoietic stem cells) and MPP (multipotent progenitors) are the cells studied. Human samples are day 0 and day 90 ([F17](experiments/F17-bcg-application.md)). |
| four-corner goal; species leg, drug leg | Observed: mouse untreated, mouse treated, human untreated. To predict: human treated. The species leg (mouse → human) was built; the drug leg never was ([F17](experiments/F17-bcg-application.md)). |

## Data versions and splits

| term | meaning |
|---|---|
| `v07` **(overloaded)** | At first only a file-format suffix: the file was rewritten so anndata 0.7 in the CellOT env can read it. Later it was read as the pre-assay-filter data version ([F07](experiments/F07-toggle-iid-ood-and-renorm.md), [F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)). |
| `v08` | Data rebuilt in June with the assay filter and a species-stratified split. Its three OOD cuts are the "frozen benchmark" ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)). |
| stale / renorm | Atlas data built from the transformed upstream `.X` (stale) vs rebuilt from raw counts (renorm, 2026-04-20) ([F07](experiments/F07-toggle-iid-ood-and-renorm.md)). |
| `toggle_ood` | CellOT's split for held-out cell types. Held-out cells are halved into `ood` (scored) and `ignore` (unused in OOD mode, used in IID mode). All other cells go to `train` / `test` (`test_size` 0.2, seed 0) ([F07](experiments/F07-toggle-iid-ood-and-renorm.md), [F16](experiments/F16-deployment-models-and-mixhvg.md)). |
| IID / OOD **(overloaded)** | In the atlas runs, the *training mode*: whether the transport saw half of the held-out type (iid) or none of it (ood). Both are scored on the same `ood` half (`--setting ood`). In the toggle runs the IID encoder saw all held-out cells. The CellOT paper's i.i.d. model is also a training setting, trained "with additional access to half of the cells in the holdout sample" [P]. In F11, `--setting iid` instead means scoring the training species' test cells ([F07](experiments/F07-toggle-iid-ood-and-renorm.md), [F11](experiments/F11-bunne-lps-replication.md)). |
| scGen split vs Bunne OOD split | On LPS: in the scGen split only rat LPS6 is held out, so rat unstimulated cells are in training (easier). In the Bunne OOD split all rat cells are held out ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md)). |

### Holdout groups, side by side

| label | where | held-out cell types |
|---|---|---|
| T1 = group a = Group A, "CD8" | toggle (F07), HVG matrix (F08), speciesot_v1 (F06), v08 `a` (F10, F16) | CD8⁺ αβ T cell (CL:0000625) |
| T2 = group b | toggle, HVG matrix | CD8⁺ T + thymocyte (CL:0000625, CL:0000893) |
| Group B (speciesot_v1 and renorm) | F06, F07 | CD8, with thymocytes removed from the autoencoder's training. Its renorm folder `renorm_cd8_thymo` is easily confused with T2's `cd8_thymo` label |
| T3 = group c = Group C | toggle, HVG matrix, speciesot_v1 | CD4⁺ + CD8⁺ T + thymocyte (CL:0000624, CL:0000625, CL:0000893) |
| T4 = group d = Group D, "CD4" | toggle, HVG matrix, speciesot_v1 | CD4⁺ αβ T cell (CL:0000624) |
| M1 **(overloaded)** | toggle (F07) and v08 (F10, F14, F15) | non-classical monocyte (CL:0000875). Same holdout in both, but on different data versions. In the 2026-03-22 log, "M1/M2" also meant macrophage polarization states. |
| M2 | toggle and v08 | non-classical + generic monocyte (CL:0000875, CL:0000576) |
| M3 | toggle | all monocyte subtypes (CL:0000875, CL:0000860, CL:0002393, CL:0000576) |
| M4 | toggle | classical monocyte (CL:0000860) |

Source: `conny:speciesOT/baseline/analysis/09_data_prep_toggle_experiments.ipynb#c9`
(`GROUPS`), `fasrc:BK/docs/model_cards/INDEX.md`, and the family pages.

## Models

[models.md](models.md) has the full comparison.

| term | meaning |
|---|---|
| scGen **(overloaded)** | Four programs. (1) Paper scGen: a TensorFlow 1 VAE, `VAEArith` ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md), [F14](experiments/F14-july-plans-a-to-d.md)). (2) `scgen` 2.x: the scvi-tools rewrite, `SCGEN`; used by no experiment. (3) The hub's "scgen": CellOT's deterministic autoencoder plus a latent mean shift. Every hub result used this one; Plan C used the paper VAE instead. (4) The package's `scGenModel`, a stub ([F18](experiments/F18-oop-package.md)). `conny:docs/concepts/scGen.md` calls the hub's model "a VAE", which is wrong. |
| `raw_shift` | Add the mouse→human (or unst→LPS) mean difference directly in gene space; no autoencoder ([F13](experiments/F13-autoresearch-loop.md)). |
| CellOT | An input-convex neural network (ICNN) that learns an optimal-transport map. Here it is usually applied in a frozen autoencoder's 50-d latent space. Exceptions: the March run on 6,619 genes ([F05](experiments/F05-first-cellot-runs-on-lps.md)) and F13's ICNN run on an 800-d latent ([F13](experiments/F13-autoresearch-loop.md)). |
| IMPACT, IMPACT-OR, IMPACT_CellOT, `impact_cellot`, `impact_or`, `speciesot_cellot`, `swapped_cellot` (renorm) **(overloaded)** | CellOT trained mouse → human in the scGen autoencoder's latent space, with decoded predictions. What "IMPACT" stands for is not recorded. Other uses: iteration 1 ran human → mouse ([F06](experiments/F06-tcell-holdouts-speciesot-v1.md)); F11's `impact_cellot` folders hold unst → LPS6 runs; and in notebook 10's code, `IMPACT_CellOT` labels the cell-type model instead ([F07](experiments/F07-toggle-iid-ood-and-renorm.md)). |
| cell-type CellOT, CellOT-ct, `cellot`, `normal_cellot`, `speciesot_cellot_swapped` | CellOT from non-held-out to held-out cell types; abandoned ([F06](experiments/F06-tcell-holdouts-speciesot-v1.md), [F07](experiments/F07-toggle-iid-ood-and-renorm.md)). |
| `swapped` **(overloaded)** | Meant the cell-type framing in speciesot_v1 (`speciesot_cellot_swapped`) and the species framing (IMPACT) in the renorm runs (`swapped_cellot`) ([F06](experiments/F06-tcell-holdouts-speciesot-v1.md), [F07](experiments/F07-toggle-iid-ood-and-renorm.md)). |
| two-path, average delta, `single_species_delta` | Prediction rules. Fig. 5's average of two latent routes to LPS rat; one pooled δ; one mouse→human δ ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md), [F14](experiments/F14-july-plans-a-to-d.md)). |
| GW, entropic GW, FGW (α), OTDD, AGW, EMD, Sinkhorn (ε) | OT methods Josh used to *match* cells across species. GW compares distances inside each species. FGW mixes in a cross-species feature cost, with α the GW weight. OTDD adds label distances. AGW is augmented GW. EMD is exact OT. ε is the entropy smoothing ([F01](experiments/F01-gw-feasibility-and-simulations.md)–[F04](experiments/F04-gene-priors-and-standard-ot.md)). |
| PerturbOT | Genentech's package. Here only its label-constrained entropic GW matcher was used ([F02](experiments/F02-perturbot.md)). |
| symmetry mismatch | GW pairs whole populations with the wrong partner because they look alike in shape ([F01](experiments/F01-gw-feasibility-and-simulations.md)). |
| anchor, seeded GW | A known correct pair, used to start the GW solver (seeded GW) or built into the cost in other anchoring variants ([F01](experiments/F01-gw-feasibility-and-simulations.md)). |

## Metrics

[metrics.md](metrics.md) has the formulas and code locations.

| term | meaning |
|---|---|
| R², `r2-means`, `r2_all`, `r_50`, `R2Evaluation` **(overloaded)** | `r2-means` in `evals.csv` is *unsquared* r of mean vectors. The hub's "R²", autoresearch's `r2_all` and the scGen paper's R² are squared. `r_50` is unsquared r on the top-50 marker genes. The package's `R2Evaluation` is a per-gene correlation across *paired* cells, a different metric. |
| MMD | A distance between two cell clouds. Every implementation here is the biased estimator, so its value depends on the number of cells n ([metrics.md](metrics.md) §2). |
| floor, ceiling | The best possible MMD (target vs itself) and the do-nothing MMD (source vs target) ([metrics.md](metrics.md) §3). |
| `frac_gap_closed` (fgc, fgc_raw), `frac_gap_closed_decoded` (fgc_dec), `frac_gap_closed_latent` | (ceiling − model)/(ceiling − floor), in the raw, decoded or latent frame. |
| `north-star`, `guardrails` | The repo's names for its single ranking metric (fgc_dec) and its two cross-checks (`frac_r2_closed_decoded`, `mean_js`). |
| model/floor, `model_over_floor` | Model MMD ÷ the autoencoder's own decoded floor. |
| `AE round-trip tax` | The repo's name for the extra MMD caused only by passing cells through encode → decode. |
| frozen benchmark | The three v08 OOD cuts (M1, M2, CD8), split seed 0, n = 30/50/80, headline at n = 80 ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)). |
| `gate` | The repo's name for a pass/fail threshold, e.g. Stage 0's r2_all ∈ [0.88, 0.93] ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md), [F15](experiments/F15-ae-repair-rounds-and-calibration.md)). |
| COD, paired Pearson²/gene, variance kept | Autoencoder reconstruction scores on paired cells ([F15](experiments/F15-ae-repair-rounds-and-calibration.md)). |
| kBET, kNN purity | kBET scores how well batches mix; kNN purity scores how well cell labels are kept ([F17](experiments/F17-bcg-application.md)). |
| pairing (mapping) accuracy | Share of cells whose OT partner has the same label ([F01](experiments/F01-gw-feasibility-and-simulations.md)–[F04](experiments/F04-gene-priors-and-standard-ot.md)). |

## Experiment and process labels

| term | meaning |
|---|---|
| E1 … E24 | Josh's notebook numbers ([F01](experiments/F01-gw-feasibility-and-simulations.md)–[F04](experiments/F04-gene-priors-and-standard-ot.md), [F17](experiments/F17-bcg-application.md)). |
| E1, E2, E3 **(overloaded)** | Also the three inference-only checks of late July; E3 is the "devar" variance correction ([F15](experiments/F15-ae-repair-rounds-and-calibration.md)). |
| speciesot_v1, iteration 1/2, Groups A–D | The first atlas runs, March–April ([F06](experiments/F06-tcell-holdouts-speciesot-v1.md)). |
| Stage 0, Stage 1, Stage 2 | scGen Fig. 5 reproduction; the 2×2 split × gene-set grid; the planned ICNN grid, never run ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md)). |
| arms A–D **(overloaded letters)** | Stage 1 cells: scGen split or Bunne OOD × 6,619 or 1,000 genes ([F12](experiments/F12-scgen-fig5-stage0-and-stage1.md)). |
| Plans A–D **(overloaded letters)** | The four agent plans of 2026-07-21 ([F14](experiments/F14-july-plans-a-to-d.md)). |
| Options A–C, Proposals A–C **(overloaded letters)** | Unbalanced-OT routes ([F14](experiments/F14-july-plans-a-to-d.md)); data-cut proposals ([F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)). |
| Round 1–4, Track B, Phase A/B | The late-July autoencoder repair rounds, the identity audit, and the devar confirmation stages ([F15](experiments/F15-ae-repair-rounds-and-calibration.md)). |
| tier, one-delta, L1/L2/L3 | Autoresearch batch labels; exactly one setting changed per run; loop / proposer / director ([F13](experiments/F13-autoresearch-loop.md)). |
| `infinite game` | The 2026-07-20 log's term for open-ended work to stop. |
| hub, spec, sidecar, card, vault | The `./hub` CLI; a YAML experiment spec; a metric CSV beside `evals.csv`; a per-run Markdown card; the Obsidian notes in `docs/` ([F09](experiments/F09-hub-and-metrics-infrastructure.md)). |
| `model-scgen` | A symlink in each run folder that tells CellOT's eval scripts which autoencoder to use. |
| deployment model, model set | A model meant for new data, trained with no held-out type (the iid twins hold out CD8 cells); a named group of such models in `predict_new_input.sh` ([F16](experiments/F16-deployment-models-and-mixhvg.md)). |
| PR-0 … PR-6, PRs A–J | The AI-written PR stack on this repo (#1–#10), and the PRs of the AI-built `speciesost-package` ([F18](experiments/F18-oop-package.md)). |

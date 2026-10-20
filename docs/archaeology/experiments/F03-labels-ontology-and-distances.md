# F03 · Labels, ontologies and distribution distances on real immune data

> Josh asked whether better labels, better cell pairing or a better distance would let optimal transport (OT) match mouse and human cells of the same type on real atlas data [I]. He clustered donors by Gromov-Wasserstein (GW) distance (e2), counted the PCA dimensions that separate cell types (e9), paired cells by identical cell-type and tissue ontology IDs (e10), tried OTDD, which adds label information to the OT cost (e11), and relabelled cells with CellTypist (e13) [C]. In e2 every donor's closest other donor was of the same species, but the margins were small [I]. Label-free cross-species matching scored 45.5% (e10 c15 [N]), about the score of always guessing the most common type (44.2% [I]). The two high within-species numbers (95.9% in e11 c40, 75% in e13 c37 [N]) both used labels on both sides, and both came from solver runs that reported no convergence (e11 c39, e13 c30 [N]). Every result is a single run kept only as a saved notebook output [N]. The lasting product is the exact ontology matcher, which later became the cell-pairing step of the scGen/CellOT data [N].

| | |
|---|---|
| Period | 2025-10-21 → 2026-04-14 [G]: first commit `josh@9b1530f`, last content change `josh@f02467d` (2026-03-25, cells c5 and c6 of e10), last commit `josh@6597c56` (kernel name only). By commit date the runs were on 2025-10-21 (e2; the 10-23 commit only adds a metadata tag), 2026-02-03..25 (e9–e13) and 2026-03-25 (e10 c2–c6 re-run) [G]. |
| People | Joshua Price wrote, ran and committed all five notebooks and the helper functions they use [G]. Junyi (Conny) Zhou did not run or edit these experiments. Conny's only commit on the five notebooks (`josh@953e669`) changed notebook metadata in e10 and e11. Conny's three commits to `speciesot_helpers.py` on `cellot` came after the runs; the only code change to a function used here is to `top_n_organisms_from_species` (`josh@44a995e`, 2026-05-10) (see "Who did what") [G]. |
| Status | partly worked |
| Main code | `josh@main:e2_gromov_clustering.ipynb` and `josh@main:e9_immune_cell_dimensionality.ipynb` · `josh@main:e10_ontology_matching.ipynb` · `josh@main:e11_otdd_standard.ipynb` · `josh@main:e13_celltypist_labels.ipynb` · `josh@main:speciesot_helpers.py:323,455` (split and match by ontology IDs) · `josh@main:speciesot_simulation_helpers.py:266,287,495` (GW, accuracy, seeded GW) |
| Results live in | No result files. All numbers are saved outputs inside the notebooks. Copies: e2, e9 and e13 are identical on `josh@main`, `josh@cellot`, `josh@scgen-model-impl`, `ai_package@src` and in `conny:speciesOT/archive/exploratory_notebooks/`. For e10 and e11, the `conny` archive holds the `cellot` version, while `josh@scgen-model-impl` and `ai_package@src` hold the `main` version (`conny:docs/archaeology/inventory.csv`) [G]. The only file the notebooks write (e11 c69, `data/otdd_regy_eps_accuracy_021126.csv`) was not found on FASRC (shallow `find` in Josh's `speciesOT/` folder, 2026-10-20) [I]. |

## The question

Earlier work (F01) found that GW paired many mouse cells with human cells of the wrong type (`conny:docs/archaeology/timeline.md`) [D]. This family asks where that failure comes from, and whether better labels or distances fix it. The research questions in cell c1 of each notebook are [D]:

- e2: "Which attributes do mice and humans cluster by based on GW distances with no labels, when equal cell type frequencies are enforced?"
- e9: "How informative / noisy are different PCA and HVG dimensions in the task of identifying immune cell populations? ... How discriminative are the PCA and HVG dimensions in separating CD4 and CD8 T cells?"
- e10: "Does matching cell and tissues across species according to cell and tissue ontology IDs yield sufficient cells for mapping?"
- e11: "Does OTDD improve class matching accuracy and subclass accuracy compared to base entropic GW?"
- e13: "Do cell type labels based on CellTypist result in more sensible nearest neighbor pairings?"

Terms used on this page:

- **OT** finds a *coupling*: a table that says how much of each source cell is sent to each target cell, at the lowest total cost.
- **GW** is an OT variant that compares the distances *inside* each dataset. It does not need the two datasets to share features, so it can compare mouse and human cells in separately computed PCA spaces. *Entropic* GW adds a blur term of weight ε (epsilon) that makes the coupling smoother and easier to compute.
- **Ontology matching (e10).** The CELLxGENE versions of both atlases give every cell a Cell Ontology ID (for example `CL:0000084` = T cell) and a tissue ID from the UBERON anatomy ontology (for example `UBERON:0002048` = lung) (`josh@cellot:baseline/analysis/01_data_preprocessing.ipynb#c8`) [C]. `match_cells_by_celltype_tissue` keeps every (cell-type ID, tissue ID) pair that occurs in both datasets. For each pair it keeps min(n1, n2) random cells from each side (seed 0) (`josh@main:speciesot_helpers.py:455-589`) [C]. Only exact ID equality is used; the ontology tree (parent and child terms) is not [C].
- **OTDD** (optimal transport dataset distance; the `otdd` library from the paper "Geometric Dataset Distances via Optimal Transport", per its README) compares two *labelled* datasets [C]. The cost between two cells is their feature distance plus a distance between the feature distributions of their two labels, weighted by `λ_x` and `λ_y`, so OT prefers to send cells to cells whose labels look alike (`fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/otdd/otdd/pytorch/distance.py:67-106,795-804`) [C]. The library's `IncomparableDatasetDistance` class runs GW on such label-augmented costs for datasets with different features (same file :1086-1171) [C]. This FASRC folder is Josh's clone of the library; the notebook imported an installed copy that no longer exists (see e11) [C][I].
- **CellTypist** is a cell-type annotation tool with pretrained models. `Immune_All_Low` is its fine-grained immune model (e13 c10-c11) [N]. With *majority voting*, it over-clusters the cells (resolution 10 here) and gives each cluster its most common prediction (e13 c12 output) [N].

## Setup

**Data.** Tabula Sapiens (human) and Tabula Muris (mouse), CELLxGENE versions with ontology IDs in `obs` (e10 c6, e9 c29 outputs) [N]. The mouse ages of 3 and 18 months in e2 c7 suggest the Tabula Muris Senis release [I].
- `josh@main:tabula_make_samples.ipynb#c3,c10,c13,c20` sampled at most 1,000 cells per atlas cell type (seed 42 in c10 and c13, the default seed 0 in c20) [C].
- `josh@main:intraspecies_vs_interspecies_dists.ipynb#c10-c14,c19-c21` kept only cells whose type maps to one of the 31 coarse `shared_cell_type` names of the hand-made table in `tabula_make_samples.ipynb#c22` [C].
- The resulting files `sampled_human_shared.h5ad` (6.1 GB) and `sampled_mouse_shared.h5ad` (1.6 GB) are dated 2025-10-03 in `fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_sapiens/` and `.../tabula_muris/` (listing, 2026-10-20) [R].
- Their total cell counts are not printed in the five notebooks. Conny's later notebooks concatenate the donors returned by `top_n_organisms_from_species(dir, -1, …)`. One prints 58,931 human and 47,807 mouse cells from 24 and 40 donors (`josh@cellot:baseline/analysis/01_data_preprocessing.ipynb#c5,c7`); the other prints 58,852 and 47,802 (`josh@cellot:baseline/analysis/07_data_prep_all_holdouts.ipynb#c3`, the numbers quoted in `conny:logs/research_logs/research_log_2026-04-13.txt`) [N].
- With the helper as committed then, `n = -1` means `index[:-1]`, which drops the smallest donor (`josh@cdd18bf:speciesot_helpers.py:39`) [C]. Both notebooks imported the helper from Conny's working tree, whose uncommitted state at run time is unknown (01 c1, 07 c1) [C]. The gaps (79 human and 5 mouse cells) look like one run dropping a small donor and the other not, but which total is the full file is unknown [I].
- The files cover all tissues, not only immune cells. Only e13 restricts to immune classes [C].

**Donors.** `top_n_organisms_from_species` ranks donors by cell count in these files (`josh@main:speciesot_helpers.py:35`) [C]. "Donor [0]" is the largest. By the comments in e2 c5, human [0] is the male 59-year-old and human [1] the female 61-year-old [C].

**Features.** Most runs use the `obsm['X_pca']` stored in the files (50 dimensions for human, e9 c10) [N]. Josh's sampling code has no PCA step (`tabula_make_samples.ipynb`, `intraspecies_vs_interspecies_dists.ipynb#c10-c21`) [C], and the human file also carries `X_scvi` and several atlas UMAPs (e9 c29) [N]. So `X_pca` was probably computed by the atlas authors on each full atlas, not on these samples [I]; this was not checked against the atlas documentation. Some runs recompute a 50-component PCA (arpack solver) on all genes of each subset, with no explicit HVG step (e10 c49, c61; e11 c13, c76) [C]. e13 uses highly variable genes (HVGs), scaling and PCA per half (c24-c25) [C]. Conny's later audit says the human `.X` is log-normalised, while the mouse `.X` is also divided by each gene's SD and clipped at 10 (`conny:logs/research_logs/research_log_2026-04-20.txt`, section 1) [D, not checked]. That would make mouse and human PCA spaces differently scaled [I].

**Methods.**
- Base GW: POT `entropic_gromov_wasserstein` with square loss, the PPA solver, Euclidean distances divided by their maximum, and uniform weights. ε = 0.01 in e2 (`josh@c57ee12:speciesot_helpers.py:53-70`) and 0.1 in e9/e10 (`josh@main:speciesot_simulation_helpers.py:266-284`) [C].
- *Seeded* GW (`gw_seeded`, :495-522) starts from a coupling whose anchor pairs are boosted 50× [C].
- *Geodesic* distances are shortest paths on a kNN plus minimum-spanning-tree graph (:161) [C].
- Custom OTDD, CellTypist and PerturbOT are described in their sub-sections.

**Evaluation.**
- *Mapping accuracy* (`compute_mapping_acc`, :287-301): each source cell takes the label of the target cell with its largest coupling entry. The score is the fraction of labels that agree [C].
- *Sub-label accuracy* does the same for cells that carry a monocyte subtype code (:868) [C].
- No notebook computes a chance level: `calc_random_mean_std` is imported but never called [C]. The chance levels on this page are mine, computed from the printed label counts [I].
- e2 and e9 sample cells with unseeded pandas shuffles (`sample_equal_cell_types`, `josh@main:speciesot_helpers.py:101`) [C]. The matching and splitting helpers use seed 0 [C].
- Every number is a single run in an interactive notebook on FASRC [N].
- Package versions at run time are not recorded. The `gw_seeded` docstring names POT v0.9.5 (`josh@main:speciesot_simulation_helpers.py:499`) [C]. `josh@main:requirements.txt` was added on 2026-08-03 [G]; it pins POT 0.9.6.post1 and jax 0.10.2 and lists no `otdd` [C], so it describes a later environment (PerturbOT needed jax < 0.6.0 in 2025-10, `josh@7e69bb1`) [G][I].

## What was done and what came out

### e2 · Do donors cluster by species, age or sex under GW? (2025-10-21 → 10-23)

Notebook `josh@main:e2_gromov_clustering.ipynb`. Cell numbers below refer to it.

The notebook chose 4 mice (male and female, 3 and 18 months) and 4 humans (male 59, female 61, male 33, female 37 years) (c5, c7, c9) [C]. For each of the 36 donor pairs, including each donor with itself, it drew 200 cells per side with the same `shared_cell_type` mix and ran entropic GW with ε = 0.01 on `X_pca` (c10) [C]. The printed "Log GW dist" is the GW value from POT's `log` dictionary, not a logarithm (`josh@c57ee12:speciesot_helpers.py:70`) [C]. Every call warned "Sinkhorn did not converge" (c10) [N].

| Pair group | Pairs | GW range | Mean |
|---|---|---|---|
| same donor, two samples | 8 | 0.0015–0.0050 | 0.0029 |
| mouse–mouse | 6 | 0.0036–0.0202 | 0.0097 |
| human–human | 6 | 0.0073–0.0171 | 0.0101 |
| mouse–human | 16 | 0.0114–0.0329 | 0.0180 |

Grouping and statistics are mine [I], from the 36 values printed in c10 [N].

- For all 8 donors, the closest other donor is the same species [I].
- In 169 of the 192 within-versus-between comparisons, the within-species pair is closer [I].
- Three within-species pairs are farther apart than the closest mouse–human pair (0.0114): mouse male 3 mo–male 18 mo 0.0202, human female 37–female 61 0.0171, mouse female 3 mo–male 3 mo 0.0124 [I].
- I rebuilt the dendrogram from the printed values. Ward linkage (used in c15), average and single linkage all split the two species at the top; complete linkage does not (the human female 37 joins last) [I]. Within each species, the first merge joins two donors of the same sex and different ages (mouse females 3 and 18 months; human males 33 and 59), and the others then join one at a time [I].
- Stated conclusions: "Interspecies distances are usually, but not always, further from each other" (c1) and "Organisms cluster by species first, then inconsistently by sex and age" (`josh@main:notebook_descriptions.md:12`) [D].
- The planned next step, "Repeat mulitple times to determine if results are consistent or need to averaged" (c1, spelling as in the source) [D], was not found. The last commit, `josh@25ae5b9`, only adds a metadata tag [G].

### e9 · How many dimensions carry cell-type information? (2026-02-03)

Notebook `josh@main:e9_immune_cell_dimensionality.ipynb`.

- **Cells.** Mouse donor [0] and human donor [0]; 200 cells each with matched shared labels (c5-c6) [C]. The 4 types with more than 10 cells were kept: B cell 22, endothelial 27, macrophage 43, monocyte 62, i.e. 154 cells per species (c8-c10, c21; my sum) [N][I].
- **Method.** For each dimension and each pair of groups, z = |mean difference| / larger of the two SDs. A dimension is "informative" if z ≥ 1 (c13) [C].

| Comparison | Features | Informative | Source |
|---|---|---|---|
| 4 types, human | 50 PCs from file | 25.7% (154 of 600 pair-dimensions) | c15, c17 [N] |
| 4 types, human | top 50 HVGs | 17.7% | c33 [N] |
| classical (27) vs intermediate (21) monocytes, human | 50 PCs | 16% (8 of 50) | c21, c23 [N] |
| same pair, human | top 50 HVGs chosen on these 48 cells | 2% (1 of 50) | c36-c39 [N] |
| 4 types, mouse | 50 PCs from file | 50.3% | c46 [N] |
| classical vs intermediate monocytes, mouse | 50 PCs | 10% (5 of 50) | c51-c52 [N] |

- **GW mouse → human on the 154 cells (ε = 0.1).** 35.7% (55 of 154) without anchors (c59). The same 35.7% with one hand-picked anchor pair, a bone-marrow monocyte with a bone-marrow intermediate monocyte (c64-c69) [N]. With this label mix, random matching scores 29.1%, and mapping every cell to a monocyte scores 40.3% [I].
- **Untested hypothesis.** Hypothesis 2 (CD4 vs CD8 T cells) was never tested. T cells had 10 or fewer cells in the sample, so they were dropped and monocytes were used instead (c8, c19, c21) [N][I].
- **Stated conclusion.** "Despite these reasonably informative/discriminative dimensions, cross-species pairing fails, which may be due to different cell subtype representation and tissue sources" (c1) [D]. Commit `josh@4427104`: "Atlas PCA dimensionality promising" [G].

### e10 · Pairing cells by identical ontology IDs, then GW (2026-02-03 → 02-10; c5 and c6 changed 03-25)

Notebook `josh@main:e10_ontology_matching.ipynb`. The first version is `josh@4427104` (2026-02-03). There the matcher is defined inline (c3); it is the same code as `josh@main:speciesot_helpers.py:455-589` apart from two docstring lines [C].

**Cross-species, mouse [0] with human [0], 2026-02-03.**
- 312 matched cells in 12 cell types. Intermediate monocytes are 108 of them, and only 3 tissues occur: lung 169, bone marrow 97, spleen 46 (`josh@4427104:e10_ontology_matching.ipynb#c7,c8`) [N].
- "6% of cells are available" is 312/5,286. The printed 0.05902383… equals 312/5,286 exactly, so it comes from the 312-cell run (main c8 = `josh@4427104` c9) [N][I]. The 5,286 is the smaller of the two donors' cell counts in the sampled file (c8 code) [C], so it is mouse donor [0]: human donor [1] alone has 8,356 cells (`josh@cellot:baseline/analysis/01_data_preprocessing.ipynb#c5`) [N], and donor [0] is at least as large [I].
- GW on these cells: 45.5%, which is 142 of 312 (c15) [N]. Chance is 27.0%, and always guessing "monocyte" gives 44.2% [I].

**Code/output mismatch.** On 2026-03-25 Josh switched c5 to donors [1], re-ran c2–c4 and c5 in a fresh kernel (execution counts 1, 2, 3, 22) and replaced c6 with a cell that shows 381 cells (`josh@f02467d`) [G]. Cells c7, c8 and c14-c16 still show the 2026-02-03 outputs computed on donors [0] [G][I]. If c8 were re-run now, it would divide 381 by the donor-[0] size [I]. The `cellot` copy keeps the original c5/c6, because this change came after `cellot` split off on 2026-02-25 (`josh@a7f7301`) [G] and Conny's 2026-04-13 sync copied only e15–e17 from main (`conny:logs/research_logs/research_log_2026-04-13.txt`) [D]. So the lead's "two code cells differ" is correct: they are c5 and c6; c2's output and the execution counts of c3–c4 also differ [G].

**Two humans (donors [0] and [1], same atlas).**

| Cells | Variant | Accuracy | Source |
|---|---|---|---|
| 100 | GW, file PCA | 19% | c24 [N] |
| 100 | seeded GW, singleton anchors | 46% | `josh@4427104:e10_ontology_matching.ipynb#c31` [N]; lost since `josh@c07eed9` (2026-02-09; main c29 shows KeyboardInterrupt) [G] |
| 100 | GW, geodesic k = 3 | 8% | c33 [N] |
| 100 | seeded GW, geodesic | 27% | c37 [N] |
| 500 | seeded GW, file PCA | 47.6% | c45 [N] |
| 500 | GW, PCA recomputed per donor (2026-02-09) | 40% | c52 [N] |

The mass-fraction table of the last run shows two kinds of error (c55) [N]:
- T cells and thymocytes mix: thymocyte → T cell 0.84, T cell → thymocyte 0.40.
- Whole classes switch: mesenchymal stem cell → pulmonary alveolar 1.0, bladder urothelial → fibroblast 1.0.

The c1 conclusion calls this "whole class switching (MSCs and bladder alveolar cells), some class mixing (T cells and thymocytes)" [D].

**Same donor split in two halves (100 + 100 cells, PCA per half, 2026-02-10).**
- 53% at ε = 0.1 (c70) [N].
- ε sweep: 1e-4 → 3%, 1e-3 → 48%, 1e-2 → 52%, 0.1 → 53%, 1 → 57% (c71) [N].
- Geodesic k sweep: k = 3 → 10%, 5 → 9%, 10 → 13%, 20 → 29%, 50 → 38% (c72) [N]. The output also has a line "100 0.57", but k = 100 is not in the code of any commit, from the first one (`josh@f53a00d`) on (c72) [N][G].
- c73: "k=100 is equivalent to using Euclidean distance, so there is no advantage to using geodesic distance" [D].

**Stated conclusions.** c1: "6% of cells from a mouse are used after exact ontology matching. Euclidean distance appears superior to knn graph geodesic with any k" [D]. Commit `josh@4427104`: "Cell type matching not working with regular gromov, even with ontology matching" [G].

### e11 · OTDD: library version and Josh's own version (2026-02-10 → 02-16; code cleanup 02-25)

Notebook `josh@main:e11_otdd_standard.ipynb`. It is identical on `josh@cellot` apart from metadata [G].

**Library OTDD.**
- The MNIST-vs-USPS tutorial gives OTDD = 932.70 (c4-c6) [N].
- First attempt on real data (`josh@f53a00d:e11_otdd_standard.ipynb`, 2026-02-10 12:51; halves from `split_adata_by_celltype_tissue(cell_number=200)` without the later filters) [C]:
  - `dist.distance(maxsamples=1000)` printed "OTDD(src,tgt)=1795.65478515625" (c18-c19) [N]. Which object it used is unclear: c17, which builds `IncomparableDatasetDistance`, has a later execution count (28) than c18-c19 (21-22) [N][I].
  - `dist.compute_coupling(entreg=0.1)` failed with "RuntimeError: This function was deprecated since version 1.9 and is now removed", raised for `torch.symeig` (c20) [N].
  - By the next commit, `josh@7dcd6c1`, the `distance()` cells were deleted and the coupling call had its final form (below) [G].
- Final version: one call, `IncomparableDatasetDistance(...).compute_coupling(entreg=0.01, λ_y=0.0)` (c20-c21) [C]. It was applied to the same-donor halves: 200 pairs from `split_adata_by_celltype_tissue(cell_number=200, min_per_cell_type=5)`, PCA per half, shared types with ≥2 cells, leaving 195 + 195 cells (c11-c17, c22) [C][N].
- Result: mapping accuracy is 10.3%, i.e. 20 of 195 (c25) [N]. In the same session (exec 116-122), Sinkhorn did not converge (c21) and the largest coupling entry is 0.0051 ≈ 1/195 (c23) [N][I]. So at least one cell sends almost all its mass to a single target, yet the labels mostly disagree [I].
- Beware of c26. On main it prints an almost uniform coupling (printed entries 2.35e-5 to 3.0e-5; a uniform coupling would be 2.6e-5). Its exec count (36) shows it comes from a different kernel session than the run above [N][I]. The printout of the real coupling (printed entries 3.6e-24 to 6.4e-4) is kept in `josh@7dcd6c1:e11_otdd_standard.ipynb#c26` and in c25 at `josh@f7b65cd`, `josh@c19b047` and `josh@398e9fe`; `josh@109bbec` replaced it with a NameError [G][N].
- Which code ran is unknown. The notebook imported the installed copy `speciesOT_env/lib/python3.12/site-packages/otdd/` (path in the f53a00d c20 warning) [N]. That copy no longer exists on FASRC (listing, 2026-10-20) [I]. In Josh's clone `fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/otdd/`, every source file keeps the clone time (2026-02-10 11:27) except `otdd/pytorch/sqrtm.py`, changed at 13:37 that day, i.e. between `josh@f53a00d` (12:51) and `josh@7dcd6c1` (16:19) [C]. Its `symsqrt_v2` now calls `torch.linalg.eigh` (`sqrtm.py:54`), while other `torch.symeig` calls remain (`sqrtm.py:29,78`; `moments.py:334`) [C]. The clone's `distance.py` is unchanged and would still fail (next bullet) [C][I]. So the copy that ran was patched in ways the clone does not show [I].
- In the clone's code, `compute_coupling` is inherited from the same-feature-space class: it compares the two halves' coordinates directly (`distance.py:780-816`) [C]. The GW-based `distance()` (:1154-1171) is not called in the final notebook [C]. The subclass's `_get_label_distances()` returns a pair (:1136), on which `compute_coupling` calls `.to()` (:802), so as written this path fails [C][I].
- `λ_y` is a constructor argument (default 1.0, :153). Passed to `compute_coupling`, it goes through `**kwargs` into `ot.sinkhorn` (:786, :811) [C]. So, if the installed copy matched the clone here, it did not switch the label term off [I].

**Custom OTDD ("my own implementation", c27-c40).** For each dataset separately:
1. The label-to-label distance is the cost of unbalanced entropic OT between the cells of the two labels (POT `sinkhorn_unbalanced2`, reg 0.05, reg_m 10, squared Euclidean cost divided by its maximum) (c28-c29) [C].
2. The cell-to-cell distance becomes (d_X² + `reg_y` · label distance)^½ (c33) [C].
3. Entropic GW couples the two augmented distance matrices (c38) [C].

Each side's labels go into its own matrix (c34, c37, c58-c59), so the method needs labels on both sides [C].

| Pair | Cells | `reg_y` | ε | Accuracy | Monocyte sub-labels | Source |
|---|---|---|---|---|---|---|
| same-donor halves | 195 | 1e5 | 0.01 | 95.9% (187/195) | 90% = 9 of 10 cells | c40, c43, c48 [N][I] |
| two donors (500 matched pairs), generic "monocyte" removed | 491 | 5,000 | 0.01 | 66.0% (324/491) | 0% of 47 | c51-c63, c67 [N][I] |
| two donors (250 matched pairs), also no pulmonary alveolar cells, PCA per donor | ≈228 | 5e4 | 0.05 | 68.4% (≈156/228) | 20% | c72-c86, c90 [N][I] |

The cell counts are mine, solved from the printed fractions [I]. 491 is exact (324/491 cannot be reduced, and the set has at most 500 cells). The monocyte count is 47 or a multiple of 47. 0.6842105… is 13/19, so the last set has a multiple of 19 cells; 228 best fits the expected number of removed cells, but 209 or 247 cannot be ruled out [I]. All three GW runs warned "Sinkhorn did not converge" (c39, c61, c84) [N].

Grid for the 491-cell pair (c68) [N]: accuracy, with the monocyte sub-label rate in brackets.

| `reg_y` \ ε | 0.001 | 0.01 | 0.1 |
|---|---|---|---|
| 1,000 | 29.1% (4.3%) | 57.8% (36.2%) | 63.3% (34.0%) |
| 5,000 | 65.8% (0) | 66.0% (0) | 57.4% (0) |
| 10,000 | 16.9% (0) | 66.2% (0) | 66.2% (0) |
| 50,000 | 20.2% (0) | 54.8% (0) | 63.1% (0) |
| 100,000 | 19.8% (0) | 55.0% (0) | 62.9% (0) |

- c70: "OTDD still has symmetry issues. At least two major cell types always swapped" [D].
- c1: "OTDD better than base GW, but still has class-level mismatch ... OTDD alone is insufficient for accomplishing class accuracy with no anchoring" [D]. The hypothesis was "above 90%+ for couplings between individuals, 80% between humans, and 50% between species" (c1) [D]. The record has 95.9% for one donor's halves and 66–68% for two humans [N]; e11 never ran mouse vs human [C].
- Commit messages follow the same path: `josh@7dcd6c1` "monocyte sublabel matching rate of 90%", `josh@f7b65cd` "works better than base GW across two humans", `josh@c19b047` "usually has symmetry issues", `josh@109bbec` "OTDD and PerturbOT have low sublabel acc with untransformed PCA dims" [G]. At `f7b65cd` the two-human GW cell (then with ε = 0.1) has no execution count and only a convergence warning, and the accuracy cell has no output; 66.0% first appears at `c19b047` [G][N].
- **Lead correction.** "Two humans ≤ 66%" is slightly wrong. The last section reached 68.4% (c86) [N].

### e13 · CellTypist labels (2026-02-23 → 02-25)

Notebook `josh@main:e13_celltypist_labels.ipynb`.

- **Cells and labelling.** Human donor [0], with gene IDs converted to symbols through the online mygene.info service (c4) [N]. Immune broad classes only, 5,924 cells (c7-c8, c12) [N]. `normalize_total` + `log1p` (c9) [C], then CellTypist `Immune_All_Low` with majority voting (c12) [C].
- **Input warning.** CellTypist warned "invalid expression matrix, expect ALL genes and log1p normalized expression to 10000 counts per cell" and used 6,058 genes (c12) [N]. If the file's `.X` was already log-normalised, as Conny's audit says [D], c9 normalised it a second time [I].
- **Agreement measure.** *Nearest-neighbour agreement* is the share of cells whose nearest neighbour, in a kNN graph on 50 PCs of the HVGs of the same 5,924 cells (c16, scanpy defaults otherwise), has the same label (`josh@main:speciesot_helpers.py:1135`) [C].

| Labels | Nearest-neighbour agreement | Source |
|---|---|---|
| CellTypist, majority voting | 88.3% | c17 [N] |
| CellTypist, per cell (`predicted_labels`) | 59.9% | c18 [N] |
| Tabula Sapiens `cell_type` | 79.2% | c19 [N] |

**Lead correction.** The lead's "88% vs 79%" is right, but per-cell CellTypist labels score lower than the atlas labels (59.9%, c18) [N].

**T-cell subtypes with PerturbOT.**
- The donor was split into halves by (CellTypist label with all T-cell subtypes merged into "T cells", tissue) (c22-c23) [C]. Each half has 1,368 T cells (c26) [N].
- PerturbOT's labelled entropic GW (`get_coupling_egw_labels_ott`, run with ott-jax) returns one coupling per label (c29-c33) [C]. Method details are on the F02 page.
- On the T-cell block at ε = 1e-5, fine CellTypist T-subtypes agree for 75.4% of cells, i.e. 1,031 of 1,368 (c37) [N][I]. For that run ott printed "The last Sinkhorn iteration has converged: False ... The final regularized GW cost is: -inf" (c30) [N].

| ε | Accuracy | Solver report | Source |
|---|---|---|---|
| 0.1 | 38.9% | converged | c39 [N] |
| 1e-3 | 41.8% | converged | c39 [N] |
| 5e-5 | 62.8% | not converged | c40 [N] |
| 1e-5 | 75.4% | not converged, cost −inf | c39 [N] |
| 5e-6 | 75.3% | not converged, cost −inf | c40 [N] |
| 1e-7, 1e-8 | 9.9% | cost nan | c39, c40 [N] |

**Baselines (all mine) [I].**
- Random matching with these subtype counts scores 20.3%.
- Pairing T cells at random within the same tissue scores 48.2%. This is the diagonal of the c36 crosstab, which pairs the two halves' cells by list position, not by the coupling.
- 9.9% equals 136/1,368, the share of "Follicular helper T cells" (the first label in sorted order) in half a. That fits every cell being mapped to one target cell.
- The two converged runs (38.9%, 41.8%) score below the within-tissue pairing (48.2%).

**Stated conclusions.** c1: "Yes, CellTypist labels ~90% nearest neighbor match (low-level cell type), Tabula Sapiens is ~80%. T cell sublabel accuracy of ~75% with CellTypist labels" [D]. Commit `josh@9b01900`: "Perturb-OT with CellTypist has 75% T cell subtype accuracy" [G].

### Who did what, and what happened afterwards

- `git log --follow` of e2, e9, e10, e11 and e13 on `main` and `cellot` shows only Joshua Price for all content changes [G].
- Conny's one commit on these notebooks is `josh@953e669` (2026-03-16, `cellot`) [G]. In e10, e11, e12 and e14 it only changed the kernel name ("speciesOT" → "Python 3 (ipykernel)") and the Python version (3.12.5 → 3.12.11); no cell or output changed [G]. It also added two docstring lines to `match_cells_by_celltype_tissue`: "cell type is inferred, subjective / tissue is ground truth" [G]. Josh later carried those lines to main (`josh@75d14f6`, 2026-04-07) [G].
- Conny's other commits to `speciesot_helpers.py` on `cellot` came after these runs: `josh@ddc56ad` (2026-03-24) added BioMart ortholog functions, and `josh@44a995e` (2026-05-10, co-authored with Cursor) made `top_n_organisms_from_species(…, -1, …)` return every donor [G].
- **Lead correction.** Conny's first commits in Josh's repo are `josh@9124d02` and `josh@e86c1df` (2026-03-04, files under `prediction/`), not e10–e14 work in 2026-02. No commit by Conny before 2026-03-04 exists on any branch [G].
- The matcher lived on as the cell-pairing step of the later work [N]:
  - `josh@cellot:baseline/analysis/01_data_preprocessing.ipynb#c8-c9` (2026-03-24), 6,495 pairs;
  - `07_data_prep_all_holdouts.ipynb#c6`, 6,418 pairs;
  - `01.3_data_prep_all_holdouts_renorm.ipynb#c11` and `01.5_data_prep_all_holdouts_hvg_flavors.ipynb#c7`, 6,495 pairs each;
  - Josh's `josh@main:e20_lab_meeting_051226.ipynb#c4-c5`, 4,027 pairs after assay filters (c2).

  The 6,418 and 6,495 come from different input totals (58,852 vs 58,931 human cells, see Setup) [N][I]. These pipelines are covered on the F06, F07 and F08 pages.
- Conny's repo archived copies of the notebooks on 2026-05-15 (`conny@c342331`); the e10 and e11 copies are the `cellot` versions [G]. None of the package code (`conny:src/speciesot` on main and the `pr-*` branches, `ai_package@src:src/speciesot/`, `josh@scgen-model-impl:src/speciesot/`) contains ontology matching, OTDD or CellTypist code [C]. The old `speciesot_helpers.py` with the matcher sits beside the package at the root of `josh@scgen-model-impl` and `ai_package@src` (`conny:docs/archaeology/inventory.csv`) [G].

## Verdict

- **Supported, weakly.** On these samples, GW puts mouse donors closer to mouse donors than to human donors (e2): 8 of 8 nearest neighbours are the same species, and 169 of 192 comparisons go the expected way [I]. But the margins are small: 3 within-species pairs are farther apart than the closest mouse–human pair, and two samples of the same donor differ by up to 0.0050 [I]. The two species also come from different atlases with separately computed PCA spaces and possibly different scaling, so the split need not be biological [I]. The evidence is one unseeded run with no repeats [N][C].
- **Supported.** Label-free GW does not match cell types across species, even after exact ontology pairing. 45.5% is about the score of always guessing the dominant type (44.2%), and e9's 35.7% is below it (40.3%) [N][I]. Within one atlas, Euclidean base GW is also weak: 19–57% depending on donor pair, size and ε, and 3% at ε = 1e-4 (e10 c24-c71) [N].
- **Weak.** OTDD "beats" base GW only in a narrow sense. Josh's version builds both cost matrices from known labels. It reaches 95.9% when the two halves have identical label counts, and 66–68% across two donors [N]. The comparison with base GW uses different cell sets and sizes (e10 vs e11) [I]. The library OTDD was effectively not tested: one final call on separately fitted PCAs, Sinkhorn not converged, 10.3%, and the library code that ran is lost [N][I].
- **Weak.** CellTypist majority-voting labels are smoother in PCA space than the atlas labels. Part of this is by construction, because majority voting gives whole clusters one label. Per-cell CellTypist labels are less smooth than the atlas labels [N][I]. The 75% T-subtype score beats both baselines (20.3%, 48.2%) [I], but it appears only at ε values where the solver reports no convergence. The converged runs give 39–42% [N], below simple pairing within the same tissue (48.2%) [I].
- **Descriptive only.** The e9 dimension counts come from one donor per species and 154 cells. The mouse/human difference (50.3% vs 25.7%) compares PCA spaces made by different upstream pipelines [N][I].

## Why it stopped

There is no stated reason for the family as a whole. Each notebook names its successor:
- e9 → "Can we successfully map across organisms in the same species?" (taken up in e10) [D];
- e10 → "Explore options to use cell types, particularly OTDD and Perturb-OT" [D];
- e11 → "See if Perturb-OT has better sublabel accuracy than OTDD", which became e12 on the F02 page [D];
- e13 → "Look into integrating gene information with augmented GW", which became e14 onwards on the F04 page [D].

After 2026-02-25 Josh's commits are about fused GW, gene correlations and later experiments (F04) [G]. From March, the project's focus moved to Conny's scGen/CellOT translation work (`conny:docs/archaeology/timeline.md`) [D]. The record suggests that the family ended because its methods kept failing across species, and the work moved to adding gene information (F04) [I].

## Problems in how it was done

- **No chance baselines.** No notebook reports one [C]. The headline cross-species score (45.5%) roughly equals the majority-class rate (44.2%) [I]. So "matching not working" is right, and the 45.5% should not be read as partial success [I].
- **Single, unseeded runs.** e2 and e9 draw unseeded samples [C]. Nothing is repeated, although e2 planned repeats (c1) [D]. The spread of any number is unknown.
- **Mixed kernel sessions.**
  - e10 execution counts repeat and jump across several sessions [N].
  - Its c5 code no longer produced the outputs below it (see e10) [G].
  - Its c72 output contains a k = 100 line that the code has in no commit [N][G].
  - Its seeded 100-cell result (46%) survives only in `josh@4427104` [N].
  - e13 uses an `obs` column `voting_no_t` that no cell defines (c26-c32), already in its first commit `josh@9b01900`; only `voting_grouped_t` is created (c22) [C][G]. Run top to bottom, the notebook would fail [I].
  - e11 contains NameError outputs (c24, c30, c41) [N]. Its data cells c11-c17 (exec 4-10) were re-run after the library-OTDD and custom-OTDD outputs were made; at `josh@7dcd6c1` the same cells had exec 5-8 and 92-94 [G][N].
- **The "6%" has a different denominator than it appears.** The 5,286 is mouse donor [0]'s cell count in a file that holds at most 1,000 cells per atlas cell type, not the donor's full data (e10 c8; `tabula_make_samples.ipynb#c3,c10`) [C][I].
- **Labels used on both sides.** Custom OTDD builds each side's cost from that side's true labels [C]. The singleton anchors of e10 are cells whose ontology identity occurs once, and they are paired by that identity [C][I]. These are not label-free results.
- **Tiny sub-label samples.** The "monocyte sublabel matching rate of 90%" (commit `josh@7dcd6c1`) rests on 10 cells (e11 c43, c48) [N][I].
- **Library OTDD misused.** e11 called the same-space coupling, with a keyword that the clone's code ignores, on two halves whose PCAs were fitted separately and so do not share axes [C][I]. Sinkhorn did not converge (c21) [N]. Its 10.3% says nothing about OTDD.
- **Library code that ran is lost.** The run used an installed `otdd` copy that was patched after the `torch.symeig` failure, and that copy no longer exists; the FASRC clone shows only one such edit (`sqrtm.py`, 13:37) [N][C][I]. The e11 library result cannot be re-created as it ran.
- **Unequal comparison with base GW.** e11's two-human OTDD runs drop generic monocytes (and in the last run pulmonary alveolar cells), use other ε values and other cell counts than the base-GW runs of e10 (100 or 500 cells, nothing removed) [C]. So "OTDD better than base GW" (e11 c1) is not a like-for-like result [I].
- **Unchecked commit message.** `josh@f7b65cd` claims OTDD "works better than base GW across two humans", but at that commit the two-human OTDD accuracy had not been printed [G][N].
- **Non-converged solver.** Many runs warn "Sinkhorn did not converge": every e2 call, the e9 seeded run, most e10 runs, and all e11 couplings, including the 95.9% one (e11 c21, c39, c61, c84) [N]. e13's best results come from runs with cost −inf, and its nan runs collapse onto one target [N][I].
- **Mislabelled crosstab.** The e13 c36 crosstab looks like the OT result, but it is a positional pairing [C][I].
- **Misaligned CSV.** e11 c69 builds its table from lists of lengths 5, 3, 15 and 15, so the `reg_y` and ε columns do not line up with the accuracies [C]. The file was not found on FASRC anyway [I].
- **Possibly double-normalised input in e13.** c9 applies `normalize_total` + `log1p`, and CellTypist then warned that the input was not log1p-normalised to 10,000 counts (c12) [C][N]. If the human `.X` was already log-normalised, as Conny's 2026-04-20 audit says [D], the CellTypist labels were computed on transformed-twice data [I].
- **e2 analysis.**
  - The same-donor values (up to 0.0050) are as large as some between-donor values (0.0036, 0.0039), so sampling noise is of the same size as the differences. The notebook sets the diagonal to 0 before clustering (c14) [N][I].
  - c15 uses Ward linkage on GW values, which are not Euclidean distances. It also fits an `AgglomerativeClustering` model with a different linkage (average) whose comment says "must match", and never uses it [C].
- **Unequal donor-pair compositions.** In e2 each pair's cell-type mix follows the first donor's proportions, so pairs are not compared on the same composition [C][I].
- **Mouse vs human PCA spaces not comparable.** Mouse and human `X_pca` come from different upstream pipelines, and possibly different scaling [D][I]. This affects e9's 50.3% vs 25.7%.
- **Unreproducible inputs in e13.** Gene symbols come from an online lookup, and all CellTypist models were downloaded on the day with `force_update=True` (c4, c10) [N].

## Terms used here

- `shared_cell_type`: one of 31 coarse names that map atlas labels of both species to a common type (`josh@main:tabula_make_samples.ipynb#c22`).
- donor [0], [1]: donors ranked by cell count in the sampled files; human [0] is the male 59-year-old (e2 c5 comment).
- identity: the pair (cell-type ontology ID, tissue ontology ID) used by the matcher and the splitter.
- "same human", halves: one donor split by `split_adata_by_celltype_tissue` into two halves with identical identity counts.
- "two humans": human donors [0] and [1] matched by identity.
- acc / mapping accuracy: argmax label agreement (`compute_mapping_acc`).
- sub_acc / sublabel accuracy: the same, restricted to cells with a monocyte subtype code.
- informative / discriminative dimension (e9): a PC or gene with z ≥ 1 between two groups.
- seeded or anchored GW: GW started from a coupling with anchor pairs boosted 50×.
- singleton anchors: cells whose identity occurs exactly once in a matched set.
- geodesic, k: shortest-path distance on a kNN plus minimum-spanning-tree graph with k neighbours.
- custom OTDD, `reg_y`: Josh's label-augmented GW; `reg_y` weights the label term.
- "symmetry issues": GW sends a whole class to another class of similar shape (term from the F01 simulations).
- `majority_voting`, `predicted_labels`: CellTypist labels after cluster voting, and per cell.
- `voting_grouped_t` / `voting_no_t`: majority-voting labels with all T-cell subtypes merged into "T cells". Only `voting_grouped_t` is defined in the saved notebook; `voting_no_t` looks like an older name for the same column [I].
- "Log GW dist" (e2): the GW value from POT's log dictionary, not a logarithm.

## What the package needs from this

1. **Exact ontology matcher. Worth a reference test.** The later scGen/CellOT data (F06–F08) and Josh's e20 were built with it, and its pair counts are deterministic.
   - Inputs: `fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_muris/sampled_mouse_shared.h5ad` and `.../tabula_sapiens/sampled_human_shared.h5ad` [R]. Donors in `obs['donor_id'].value_counts()` order. Keys `cell_type_ontology_term_id` and `tissue_ontology_term_id`, seed 0. Code: `josh@main:speciesot_helpers.py:455-589`, the same as the inline copy that produced the numbers (`josh@4427104:e10_ontology_matching.ipynb#c3`) [C].
   - Expected, mouse [0] with human [0]: 312 pairs [N] (`josh@4427104:e10_ontology_matching.ipynb#c7,c8`):
     - cell types: intermediate monocyte 108, hematopoietic precursor cell 61, plasma cell 41, basophil 40, classical monocyte 15, monocyte 15, vein endothelial cell 11, natural killer cell 10, pulmonary alveolar type 2 cell 5, macrophage 4, B cell 1, bronchial smooth muscle cell 1;
     - tissues: lung 169, bone marrow 97, spleen 46.
   - Expected, mouse donor [0] size: 5,286 cells (312 / 0.05902383654937571, `josh@4427104` c9) [I].
   - Expected, mouse [1] with human [1]: 381 pairs (`josh@main:e10_ontology_matching.ipynb#c6`) [N].
   - Tolerance: exact. Each count is a sum of min(n1, n2) per identity and does not depend on the random generator [C]. Which cells are picked depends on numpy `default_rng(0)` and the input order [C].
   - The pooled counts (6,418 and 6,495) depend on which donors were concatenated (see Setup). They belong on the F07/F08 pages.
2. **Same-donor split plus custom OTDD (e11). Only if the package adds OT pairing.**
   - Inputs: human donor [0]; `split_adata_by_celltype_tissue(cell_number=200, min_per_cell_type=5)`; 50-PC arpack PCA per half; shared types with ≥2 cells; `pairwise_uot_w2_by_label(reg=0.05, reg_m=10)` per half; `reg_y` = 1e5; entropic GW with ε = 0.01 (c11-c40) [C].
   - Expected: 195 cells and 187/195 = 95.9% (e11 c22, c40) [N][I].
   - Tolerance: none in the record (single run). Sinkhorn did not converge (c39) [N], so the number may depend on the POT version and its iteration limits [I].
3. **Not worth reproducing as tests.** e2 and e9 use unseeded sampling, single runs and no spread. e13 depends on an online gene lookup, a CellTypist model downloaded on the day, and non-converged ott runs. At most they can serve as qualitative checks, such as the species split at the top of the e2 dendrogram.

## Open questions

- Was the `obsm['X_pca']` in the sampled files really computed by the atlas authors (see Setup), and on scaled data? It feeds e2, e9, e10 and parts of e11.
- Is the mouse/human scaling mismatch in Conny's 2026-04-20 log real for these files [D]? If so, e9's species comparison and e13's re-normalisation need rechecking.
- What exactly did e11's library call run? In the clone, the base `compute_coupling` calls `.to()` on the result of `_get_label_distances()`, and the subclass returns a pair (`distance.py:802`, `:1136`) [C], so as written it should fail, yet the notebook shows a coupling [N]. The patched installed copy that explains this is gone, and the clone records only the `sqrtm.py` edit [C][I]. How the label term entered the final coupling is therefore unknown. It is also unclear which object produced the 1795.65 at `josh@f53a00d` c19.
- Does the 75% T-subtype result hold with a converged solver, with other donors, or across species?
- Where did `data/otdd_regy_eps_accuracy_021126.csv` go, and was it used? Josh's `data/` folder now holds no CSV at all, not even `tabula_cell_type_table.csv`, which `intraspecies_vs_interspecies_dists.ipynb#c2` reads, so it was probably cleaned up (FASRC listing, 2026-10-20) [I].
- How many cells do the two sampled files hold? The two printed totals disagree (Setup).
- Were e2's planned repeats ever run? Not found in git.

## Sources

- `josh@main` and `josh@cellot`: `e2_gromov_clustering.ipynb`, `e9_immune_cell_dimensionality.ipynb`, `e10_ontology_matching.ipynb`, `e11_otdd_standard.ipynb`, `e13_celltypist_labels.ipynb` (all cells and outputs); `git log --follow` of each on both branches.
- `josh@4427104:e10_ontology_matching.ipynb`, `josh@4427104:e9_immune_cell_dimensionality.ipynb`, `josh@41683ec:e9_immune_cell_dimensionality.ipynb`; e10 at `josh@c07eed9`, `josh@f53a00d`, `josh@7dcd6c1`, `josh@f02467d`, `josh@6597c56`; e11 at `josh@f53a00d`, `josh@7dcd6c1`, `josh@f7b65cd`, `josh@c19b047`, `josh@398e9fe`, `josh@109bbec`, `josh@a7ff6a0`; e13 at `josh@9b01900`, `josh@a7ff6a0`; e2 diff at `josh@25ae5b9`.
- `josh@main:speciesot_helpers.py`, `josh@cellot:speciesot_helpers.py`, `josh@c57ee12:speciesot_helpers.py`, `josh@7dcd6c1:speciesot_helpers.py`, `josh@a7ff6a0:speciesot_helpers.py`, `josh@cdd18bf:speciesot_helpers.py`; diffs `josh@757b952`, `josh@25ae5b9`, `josh@953e669`, `josh@ddc56ad`, `josh@44a995e`, `josh@75d14f6`, `josh@f02467d`, `josh@6597c56`, `josh@a7ff6a0`.
- `josh@main:speciesot_simulation_helpers.py`, `josh@4427104:speciesot_simulation_helpers.py`.
- `josh@main:tabula_make_samples.ipynb`, `josh@main:intraspecies_vs_interspecies_dists.ipynb`, `josh@main:notebook_descriptions.md` (and `josh@897360c^`), `josh@main:README.md`, `josh@main:requirements.txt`, `josh@main:e20_lab_meeting_051226.ipynb#c0-c7`; commit messages `josh@7e69bb1`, `josh@a7f7301`.
- `josh@cellot` commit list `origin/main..origin/cellot`; `git log --all --author=Junyi` and `--author=Conny`; `josh@9124d02`, `josh@e86c1df`, `josh@6f964c6`, `josh@232b65e`; `josh@cellot:baseline/analysis/01_data_preprocessing.ipynb#c0-c11`, `07_data_prep_all_holdouts.ipynb#c1-c12` (also at `josh@cdd18bf` and `josh@f10f1cf`), `01.3_data_prep_all_holdouts_renorm.ipynb#c11`, `01.5_data_prep_all_holdouts_hvg_flavors.ipynb#c7`.
- `josh@scgen-model-impl`: root file list, grep of `src/` for ontology/OTDD/CellTypist code.
- `conny:docs/archaeology/inventory.csv`, `conny:docs/archaeology/timeline.md`, `conny:docs/archaeology/models.md` (one line), `conny:logs/research_logs/research_log_2026-04-13.txt`, `conny:logs/research_logs/research_log_2026-04-20.txt`, `conny:speciesOT/archive/exploratory_notebooks/` (listing; e10 c5 and metadata), `conny@c342331`; `conny:src/speciesot` on `main` and `origin/pr-0`…`pr-6` (grep).
- `ai_package@src`: file list, `src/speciesot/pairing.py`, grep for OTDD/CellTypist/ontology code.
- FASRC, outside the backup (read-only, 2026-10-20): `fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/` (listings of the folder, `tabula_sapiens/`, `tabula_muris/`, `human/`, `human_ref/`); `find -maxdepth 3` for `otdd_regy*` and `tabula_cell_type_table.csv` in `.../joshprice/speciesOT/`; `.../speciesOT/speciesOT_env/lib/python3.12/site-packages/` (listing; no `otdd`); `.../speciesOT/otdd/` (full file times of the clone, `build/`, `otdd.egg-info/` and `.git/`; `.git/HEAD`; `README.md` head; grep for `symeig` in `otdd/pytorch/*.py`); `.../speciesOT/otdd/otdd/pytorch/distance.py:60-106,140-160,770-845,1080-1185`; `.../otdd/otdd/pytorch/sqrtm.py:18-82`. `fasrc:BK/` mirror searched; no F03 files.

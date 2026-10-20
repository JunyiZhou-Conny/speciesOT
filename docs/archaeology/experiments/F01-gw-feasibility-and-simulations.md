# F01 · Gromov-Wasserstein feasibility on real data, and simulations of its failure modes

> Josh tested whether Gromov-Wasserstein (GW) optimal transport can pair single cells across species using only the internal geometry of each dataset, counting a pair as correct when both cells share a cell-type label. On pig, mouse and human blood cells and Tabula atlas cells (July–October 2025), mouse-to-mouse pairing reached about 51–66% and human-to-human 13.5–48.5% (chance 20%), while cross-species pairing was at or below chance in most saved runs; two single runs were above it (46.5% against 20%, and 32.7% against 16.7%). In January 2026 he moved to simulated Gaussian clouds and named the main failure "symmetry mismatch": GW swaps whole populations, and in four sweeps 26–46% of unanchored runs scored 0.7 or less, mostly through such swaps. Starting the solver from known correct pairs ("seeded anchors") removed the swaps in a handful of toy runs. Status: partly worked; the real-data test did not work, and the simulations measured a real failure mode, but the evidence for the fix is weak (few unseeded runs, hand-picked anchors, coding slips).

| | |
|---|---|
| Period | 2024-06-15 → 2026-02-03: first commit of `tabula_eda.ipynb` (josh@a9b9705) to last E8 commit (josh@41683ec) [G]. Real-data part ends 2025-10-04 (josh@41e608c); simulations run 2026-01-06 → 2026-02-03 [G]. |
| People | Joshua Price wrote and ran everything; he made every commit to these files on josh@main [G]. Conny copied the notebooks into Conny's repo (conny@c342331, 2026-05-15). Later conny@8a9a103 cleared one pip message and changed the kernel name in `tabula_make_samples`; the execution counts are unchanged, so Conny did not re-run it [G][I]. |
| Status | partly worked |
| Main code | josh@main:phylogeny/pig_human_gromov.ipynb · josh@main:intraspecies_vs_interspecies_dists.ipynb · josh@main:speciesot_helpers.py (`run_ot`, `ot_between_organisms`, `sample_equal_cell_types`, `calc_random_mean_std`) · josh@main:speciesot_simulation_helpers.py · josh@main:e5_simulated_distribution_maps.ipynb to e8_generative_distributional_discrepancy.ipynb |
| Results live in | Mostly saved notebook outputs. The CSVs that E5, E7 and E8 wrote to Josh's `data/` folder are gone. One E5 CSV survives as a Jupyter checkpoint copy (`varying_cloud_size_010625-checkpoint.csv`), next to a checkpoint of an older cell-type table, in fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/.ipynb_checkpoints/ [R]. The Tabula sample files of section 4 still exist [R]. Nothing under fasrc:BK. |

## The question

1. 2025, real data: can GW pair cells across species so that paired cells have the same cell type? No notebook states this as a formal question. The closest is a "Next steps" list: find the human partner of each pig cell, label cell types, and "quantify whether cell types were correctly paired" (josh@main:phylogeny/pig_human_gromov.ipynb#c31) [D]. The commit messages track progress (josh@c861dce, josh@393065f, josh@7f16bb7) [G].
2. 2026, simulations: E5 asks "for what ranges of cell numbers, dimensions, population count, and entropy regularization does Gromov OT perform well?" (josh@main:e5_simulated_distribution_maps.ipynb#c1) [D]. E6 asks whether fused GW or a seeded start prevents symmetry mismatch (josh@main:e6_anchoring_methods_simulations.ipynb#c1) [D]. E7 asks what share of dimensions must separate two subpopulations (josh@main:e7_subpopulation_discrimination_sim.ipynb#c1) [D]. E8 asks how far source and target distributions may differ before alignment fails (josh@main:e8_generative_distributional_discrepancy.ipynb#c1) [D].

Why cell pairing mattered is not written down [I]. The next notebooks use entropic-GW pairings of mouse and human cells as the first step of PerturbOT (josh@main:notebook_descriptions.md, Experiment #1) [D]; see F02 ([F02-perturbot.md](F02-perturbot.md)).

## Setup

**GW in plain words.** GW optimal transport pairs the points of two datasets that live in different spaces. It never compares a pig cell with a human cell directly. It only compares the two tables of within-dataset distances, and it looks for a pairing under which cells that are close in one dataset go to cells that are close in the other [I]. The output is a transport plan: a matrix whose entry (i, j) says how much of source cell i goes to target cell j. Here each source cell is paired with the target cell of largest plan weight (the "argmax") [C] (josh@main:speciesot_helpers.py:82-98). Entropic GW adds a smoothing term of strength ε (epsilon); POT, the Python OT library used, solves it with the proximal point algorithm (PPA) or projected gradient (PGD); exact GW uses conditional gradient (CG) [C] (josh@main:phylogeny/pot_tutorial.ipynb#c5).

**What "symmetry mismatch" means.** GW sees only distances inside each dataset [C] (josh@main:speciesot_simulation_helpers.py:266-284). Mirror or rotate a cloud of cells and GW sees exactly the same input, because no distance changes [I]. Suppose populations A and B sit in similar positions relative to the rest. Then the swapped pairing (A→B, B→A) scores almost as well as the true one, and the solver lands on one of the two more or less by chance [I]. The plan still looks clean and confident, but whole populations go to the wrong partner. Josh calls this "symmetry mismatch" (e5 #c1, e8 #c15) [D]; his code counts runs without it as `non_flipping_examples` (e8 #c18) [C]. In the saved runs it shows up as class accuracies that move in steps of one population (0.2, 0.4, 0.6 with five populations), and as values near 0 with two populations [N] (josh@main:e7_subpopulation_discrimination_sim.ipynb#c19; josh@710cc22:e5_simulated_distribution_maps.ipynb#c12).

**Real data.** PBMC means peripheral blood mononuclear cells (white blood cells). 10x is a droplet single-cell platform. Tabula Muris and Tabula Sapiens are mouse and human atlases covering many organs. Leiden is a graph clustering method. HVG means highly variable genes. Unless stated, preprocessing was: drop cells with < 100 genes and genes in < 3 cells, normalize totals, log1p, 2,000 HVGs, scanpy PCA with 50 components, computed separately for each dataset [C] (josh@main:phylogeny/pig_human_gromov.ipynb#c4, #c15; mouse_human_gromov.ipynb#c4, #c17). GW input = Euclidean distances between PCA coordinates, divided by their maximum, with uniform cell weights [C] (pig_human_gromov.ipynb#c28-#c29).

| Notebook (last commit) | Comparison | Data | Cells per side | Labels | GW | Source |
|---|---|---|---|---|---|---|
| phylogeny/pig_human_gromov (2025-09-30) | pig → human | pig 10x matrix `data/pig/` (origin not recorded); human `pbmc_10k_v3_raw_feature_bc_matrix.h5` | 100 (July), 500 (Sept) | Sept: Leiden clusters named by hand (pig resolution 0.1, human 0.2) into coarse groups such as T/NK; July: resolution 1 (pig) and 0.1 (human), clusters not named | CG, PPA and PGD, ε = 5e-4; pairs from the CG plan (Sept, #c32) or the PPA plan (July) | [C] #c2, #c3, #c7, #c11, #c14, #c17, #c19, #c29, #c32; July: josh@c861dce #c2, #c7, #c16, #c31 |
| phylogeny/mouse_human_gromov (2025-07-17) | mouse → human | mouse `5k_Mouse_PBMCs_5p_gem-x` filtered matrix; same human file | 100 | same procedure (mouse 0.1) | pairs from PPA, ε = 5e-4 | [C] #c2, #c3, #c7, #c11, #c34, #c37 |
| phylogeny/mouse_human_gromov-applegrant (2025-07-21) | human–human, human–mouse | Tabula Sapiens PBMC (`data/human/tabula_sapiens_pbmc.h5ad`), 10x cells of donors TSP1, 2, 8, 10, 21; same mouse file | 100 random, or 6 types × 50 | atlas labels (CD4/CD8 T merged); mouse Leiden clusters given atlas names | PPA, ε = 5e-4 | [C] #c2, #c11, #c18, #c21-#c28, #c35 |
| intraspecies_vs_interspecies_dists (2025-10-04) | 6 mice, 6 humans | Tabula samples from section 4 | 5 types × 40 | `shared_cell_type` | atlas `X_pca` stored in the files; PPA, ε = 5e-4 | [C] #c10, #c19, #c28, #c34 |
| pca_sinkhorn_optimization (2025-10-04) | 10 pairs of mice | same mouse sample | 10–300 | `shared_cell_type` | PCA redone per mouse; PPA, ε 1e-7 to 0.1 | [C] #c3, #c9, #c16, #c22 |

Notebooks ran in Jupyter on FASRC in Josh's `speciesOT_env` (Python 3.12, scanpy 1.11.3, anndata 0.11.4 in July 2025) [N] (mouse_human_gromov.ipynb#c0). The POT version used in speciesOT_env is not recorded. In July 2025 the tutorial's first cell installed POT 0.9.5, but into a Python 3.8 Anaconda module, not speciesOT_env [N] (pot_tutorial.ipynb#c0). A docstring says "POT v0.9.5" [C] (josh@main:speciesot_simulation_helpers.py:495-501). Today speciesOT_env holds POT 0.9.6.post1 (dist-info dated 2026-04-07) and scanpy 1.11.5 (dated 2026-06-22) [C] (listing of fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/speciesOT_env/lib/python3.12/site-packages/), the versions pinned in `requirements.txt` of 2026-08-03 [C]. So the environment changed after the 2025 runs [I]. `tabula_eda` ran on Josh's laptop (`/Users/jprice/...`) [C] (josh@main:tabula_eda.ipynb#c3, #c26).

**Simulations (E5–E8).** `generate_point_clouds(N, P, M, A, B)` draws N populations ("clouds") of P points in M dimensions, with means uniform in [−A, A] and random full covariances scaled by B [C] (josh@main:speciesot_simulation_helpers.py:21-49). The defaults are A = B = 1; E5–E8 call it, or its subpopulation version, with A = 2, B = 0.5, except the 6 January cloud-size run (B = 1) [C] (e5 #c5; e7 #c19; josh@710cc22 e5 #c7). The target is a fresh sample from the same means and covariances [C] (:123-142). E7 and E8 give population 0 two subpopulations offset by ±1 standard deviation along the first `P_disc` dimensions (they pass `discriminative_strength=2`), and can add "noise" dimensions that have the same mean and variance in every population [C] (:565-724). The generator also pushes subpopulation 1 by 2 standard deviations along dimension `P_disc` toward another population (:714-718) [C]. When noise dimensions are present, that is the first noise dimension, so the "noise" is not quite identical across populations [C][I]. `run_ot` uses Euclidean distances or "geodesic" distances (shortest paths on a k-nearest-neighbour graph joined with a minimum spanning tree), divided by their maximum, and entropic GW with PPA; its default is ε = 0.1 [C] (:161-284). Class accuracy is the share of source points whose argmax partner is in the same population [C] (:287-300); chance is 1/N [I]. Sublabel accuracy is the share of population 0's 20 points paired with a target point of the same subpopulation [C] (:868-896). Chance is about 0.5 if population 0 is matched to population 0, lower otherwise [I]. No simulation sets a seed (`seed=None`) [C].

**Non-standard choices.** Uniform weights force every cell to be paired, even when the two samples have different cell-type proportions [C][I]. The human 10x file is the raw (unfiltered) barcode matrix [C], and 14,264 barcodes passed the 100-gene filter for a "10k" PBMC library [N] (mouse_human_gromov.ipynb#c20). In the grant notebook, the preprocessing cell printed "adata.X seems to be already log-transformed." once for each of four donors (applegrant #c29, execution 133) [N]. Scanpy prints this whenever the object already carries a `log1p` record [C] (scanpy `preprocessing/_simple.py:394-395` in ~/miniconda3/envs/analysis, scanpy 1.12.1). A freshly sliced TSP21 object preprocessed later printed nothing (#c30, execution 194) [N]. So the warning comes from a second normalize + log1p pass in the same session; it says nothing about whether the file itself was already log-normalized [I]. The balanced samples (#c33, execution 168) were drawn after that second pass; the unbalanced ones (#c31, execution 27) before it [N][I]. Scores use the argmax pair only.

## What was done and what came out

### 1. Exploration and POT tutorial (2024-06-15 → 2025-07-17)

`tabula_eda` ran QC, HVG, PCA, UMAP and Leiden on the Tabula Muris marrow sample Marrow-10X_P7_2 (1,981 cells × 13,403 genes after filtering) and on the Tabula Sapiens bone-marrow file `TS_Bone_Marrow.h5ad` (12,297 cells × 58,870 genes as loaded) [N] (josh@main:tabula_eda.ipynb#c23, #c27). It has no cross-species step and no conclusion [C]. `pot_tutorial` is POT's own example: GW between 30 points in 2-D and 30 points in 3-D [C] (josh@main:phylogeny/pot_tutorial.ipynb#c2-#c6).

### 2. Pig → human PBMC (2025-07-14 → 2025-09-30)

| Version | Cells | Result | Source |
|---|---|---|---|
| 2025-07-17 | 100 + 100 | 7 pairs checked by hand in a note (Leiden cluster numbers): 4 same type (naive T→naive T twice, NK→NK twice), 1 wrong (naive T→cDC2), 2 unclear | [D] josh@c861dce:phylogeny/pig_human_gromov.ipynb#c35 |
| 2025-09-30 (main) | 500 + 500 | type match 43.2% | [N] josh@main:phylogeny/pig_human_gromov.ipynb#c36 |
| same | same | type match after shuffling both label lists: 45.6% | [N] #c39 |
| same | same | chance expected from the label counts: 45.0% | [I] from #c41, #c42 |

The 07-17 commit says "pig-to-human v1 implemented, checked a few cells and saw successful translation in most" [D] (josh@c861dce). The 500-cell run does not support it: GW did no better than shuffled labels [N]. The pairing looks one-to-one: the type counts of the 500 partners in #c35 equal the human sample's counts in #c42 exactly, which fits the exact CG plan whose argmax #c32 takes [N][C][I]. For a one-to-one pairing with these label counts, at most 409 of the 500 pairs (81.8%) could have matched [I] (#c41, #c42). None of the 75 pig Monocyte/DC cells went to a human Monocyte/DC cell, while 122 of the 363 pig T/NK cells were paired with a human Monocyte/DC cell [N] (counted from #c35). The saved GW cell (#c29) shows a shape error; the pairs came from an earlier, unsaved execution [N] (execution counts 111–116 vs 131).

### 3. Mouse → human PBMC and the grant figure (2025-07-17 → 07-21)

`mouse_human_gromov` paired 100 mouse with 100 human cells. 19 of 100 pairs share a type [N] (counted from josh@main:phylogeny/mouse_human_gromov.ipynb#c39). If partners were drawn at random with the label mix of the actual partners, about 23% would match [I]; the human sample's own label counts were not printed. 59 of the 100 mouse cells were B cells, but only 10 of their 59 partners were B cells [N] (#c39). The notebook prints no accuracy itself. Commit: "up to cell type pairs on mouse-human, but pairs aren't correct." [D] (josh@393065f).

The `-applegrant` copy was made for an Apple Scholars grant application [D] (josh@586bb69). It compares GW distances (POT's `gw_dist`, the GW objective value):

| comparison | "unbalanced" (100 random cells) | "balanced" (6 types × 50 cells) |
|---|---|---|
| human–human | TSP1–TSP8 0.0965; TSP8–TSP10 0.0151 | TSP1–TSP2 0.0094; TSP1–TSP10 0.0043; TSP2–TSP10 0.0007 |
| human–mouse | TSP1 0.0227; TSP8 0.0270; TSP10 0.0250 | TSP1 0.0934; TSP2 0.1039; TSP21 0.0560; TSP10 NaN |

Sources: [N] josh@main:phylogeny/mouse_human_gromov-applegrant.ipynb#c37-#c41, #c43-#c49. The unbalanced runs print a sample size of 100; `n_samples` was set to 300 only later (#c2, execution 166) [N][I]. Only in the balanced design is every human–human distance below every human–mouse distance [N]. The two designs also differ in preprocessing (see Setup, Non-standard choices) [N][I]. The commit reads "human distances closer than mouse-human when erythrocytes included" [D] (josh@586bb69). TSP8's 10x cells are 4,558 neutrophils out of 4,988 [N] (#c32); this is a likely reason for its large distance to TSP1, but TSP10's composition was not printed [I]. The balanced design samples five of the six types with replacement [C] (#c18), and anndata warns "Observation names are not unique" when the balanced samples are built, so they contain duplicate cells [N] (#c19, #c33).

The same notebook gives 32.7% type match for human TSP1 against mouse, both balanced (#c64), which is 98 of 300 cells [N][I]. Chance is 1/6 = 16.7% [I]. The target labels were read from `tsp2_balanced` instead of the mouse sample; this gives the right labels only because every balanced sample lists the six types, with the same names, in the same order [C][I] (#c11, #c18, #c62).

### 4. Shared cell-type table and atlas samples (2025-09-30 → 10-03)

`tabula_make_samples` keeps at most 1,000 cells per cell type from `tabula_muris_all.h5ad` and from the six Tabula Sapiens compartment files (seed 42; a second pass on the merged human file uses seed 0) [C] (josh@main:tabula_make_samples.ipynb#c3, #c10, #c13, #c20). It defines a 31-row mouse↔human cell-type table and writes `data/tabula_cell_type_table.csv` [C] (#c22, #c24). Commit: "selecting 1000 cells per cell type from tabula datasets for HDSI-AWS visualizations" [D] (josh@e883909). The samples still exist: `sampled_mouse_1000.h5ad` (3.3 GB), `sampled_mouse_shared.h5ad` (1.6 GB), `sampled_human_1000.h5ad` (12.5 GB), `sampled_human_shared.h5ad` (6.1 GB) [R] (ls of fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_muris/ and tabula_sapiens/, 2026-10-20). The final CSV is gone; a checkpoint copy from 2025-10-02 holds an older 33-row version [R] (fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/.ipynb_checkpoints/tabula_cell_type_table-checkpoint.csv).

### 5. Within- versus between-species pairing on Tabula data (2025-10-03 → 10-04)

Josh took the six donors with most cells per species, the five types with at least 40 cells in every donor (T cell, endothelial cell, macrophage, monocyte, smooth muscle cell), and 40 cells per type (seed 42) [N][C] (josh@main:intraspecies_vs_interspecies_dists.ipynb#c16, #c22, #c26-#c31). Chance is 20% [I].

| pairs | type match (%) | source |
|---|---|---|
| mouse–mouse (3 pairs) | 55.5, 65.5, 50.5 | [N] #c49 |
| human–human (3 pairs) | 13.5, 42.5, 48.5 | [N] #c50 |
| mouse–human (6 pairs) | 6.0, 46.5, 10.0, 7.0, 14.5, 2.0 (mean 14.3) | [N] #c51; mean [I] |

Commit: "within-species OT okay, between-species OT not better than random yet" [D] (josh@7f16bb7). One of the three human–human pairs (13.5%) is below chance [N]. These cells ran before the final `min_cell_count = 40` cell (execution counts 366–368 vs 453), with an older two-argument `ot_between_organisms` than the saved three-argument one (#c47) [N][C]. The 0.5-point steps fit 200 cells, so 5 × 40 is likely but not certain [N][I]. GW distances printed even earlier (#c37-#c39), probably on the older 7 types × 10 samples (see Terms), are 0.014–0.018 human–human, 0.022–0.034 mouse–mouse and 0.017–0.032 mouse–human [N][I]; between-species distances were not larger than within-mouse ones [I].

The last cells paired mouse 0 with mouse 1 at growing sizes: 70.0%, 59.0%, 38.5% and 25.7% for 50, 100, 200 and 300 cells [N] (#c61). Commit: "adding more data makes accuracy go down currently" [D] (josh@36f44dc). This is within-mouse, on all shared types (not only the five), at ε = 5e-4, with a "Sinkhorn did not converge" warning for every size and no chance level per size [N][C] (#c34, #c60).

### 6. PCA dimension, ε and cell-number sweeps on mice (2025-10-04)

`pca_sinkhorn_optimization` used 20 mice in 10 disjoint pairs; `sample_equal_cell_types` gives both samples of a pair the same cell-type mix [C] (josh@main:pca_sinkhorn_optimization.ipynb#c3, #c4; josh@860446a:speciesot_helpers.py:81-100). The shuffled-label baseline at 100 cells (1,000 draws; code josh@7e69bb1:speciesot_helpers.py:103-124) is printed twice with different values: 10.894% (#c12, execution 73) and 10.88% (#c6, execution 100) [N]. A spread of 5.1% is printed under the name `random_ste` (#c7), which no saved cell defines; the plots use `random_std` (#c13) [N][C]. It swept PCA 5/10/50/100 dims at 50 cells and ε = 0.01 (#c9), ε from 1e-7 to 0.1 at 100 cells (#c16), and 10–300 cells at ε = 0.01 (#c22) [C]. All results are plots only; no number and no conclusion is written [N].

The solver warnings matter more than the plots. In the ε sweep, all 40 runs at ε = 1e-7 to 1e-4 printed "Solver failed to produce a transport plan", and all 30 runs at ε = 1e-3 to 0.1 printed "Sinkhorn did not converge" (#c16; one warning per run, in loop order) [N][I]. The PCA sweep and the cell-number sweep print the same warning 40 and 50 times, once per run (#c9, #c22) [N][I]. In POT, the failure warning means the plan's total mass is not 1; the bad plan is still returned and used for the argmax [C] (fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/speciesOT_env/lib/python3.12/site-packages/ot/gromov/_bregman.py:244-248, POT 0.9.6.post1). The header promises dimension 25, which was not run, and two plot titles disagree on the cell count (50 vs 100) [C] (#c8, #c11, #c13). The notebook mixes at least two kernel sessions (execution count 4 appears in #c2 and #c15) [N]. Which PCA dimension the cell-number sweep (#c22, execution 169) used is not recorded; if it ran in the same session as the PCA sweep (#c9, execution 25), the last PCA computed there had 100 dimensions [I]. The sampler version used here silently pairs a cell with an arbitrary, possibly already used, cell when the second mouse has run out of that type; a guard was added two days later (josh@b296e07) [C].

### 7. E5: GW on simulated clouds (2026-01-06 → 01-21)

Stated conclusion (#c1): "Symmetry mismatch is the most common failure for Gromov OT. More cells, more dimensions, fewer distinct populations, and entropy regularization coefficient of ~0.1 are optimal." [D]

- **Cloud size, 2 clouds in 2-D.** One fixed pair of Gaussians (A = 2, B = 1) was resampled 50 times, ε = 1e-3 [C] (josh@710cc22:e5_simulated_distribution_maps.ipynb#c7, #c11). Mean class accuracy rose from 0.68 at 10 points per cloud to 0.91 at 100, but not steadily (0.74 at 50, 0.73 at 70). 6 of 50 runs fell below 0.5, down to 0.03; values near 0 mean the two clouds had swapped [N][R][I] (josh@710cc22 e5 #c12; identical to fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/.ipynb_checkpoints/varying_cloud_size_010625-checkpoint.csv). Commit: "increasing cloud size increases performance in E5" [D] (josh@710cc22).
- **Other sweeps.** Cloud size with 5 clouds in 10-D, 2–10 populations, 2–50 dimensions, geodesic distances: plots only; the CSVs they wrote are not in Josh's `data/` folder [N][R] (#c8-#c36; ls 2026-10-20).
- **Single examples.** The 0.76 in #c22 is left over from 6 January (same value and execution count 174 in josh@710cc22 #c25). Its inputs were flattened at executions 163–164, before the cells now above them ran (186–189), so their size is not recorded; the code above it now builds 4 clouds in 5-D [N][I]. 5 clouds × 20 points in 2-D gave 0.81 (#c43) [N]. 4 clouds × 50 points in 50-D with ε = 0.1 gave 100%; I checked the saved argmax array [N][I] (#c73-#c76).
- **ε × k grid.** Geodesic distances, the 10 most bimodal of 50 dimensions (ranked by a 1- vs 2-component Gaussian-mixture BIC), 5 clouds × 10 points, 5 runs per cell [C] (#c60-#c61). The best cell is 0.656 ± 0.417 at ε = 0.1, k = 10 [N] (#c64). Averaged over k, ε = 10 scores highest (0.373), then 0.1 (0.338), 0.01 (0.322), 1e-3 (0.258) and 1 (0.252) [I]. The loop never passes ε to `run_ot` [C]. It varied ε only if the `run_ot` in memory read a global variable, as the 6–7 January versions did (josh@710cc22 and josh@ecb5685, e5 #c6) [C]. In the 20 January commit (josh@92841d0) the notebook's only `run_ot` already had its own default ε = 0.1 and was last executed at count 53, before the grid ran (counts 73–77); the grid output is identical in all later commits [C][N]. So, unless that cell was edited after it ran, all five "ε" columns used ε = 0.1 and differ only by run-to-run noise [I]. An earlier heatmap (#c49) comes from code that is no longer in the notebook; the visible loop (#c46) never calls `run_ot`, although its saved traceback shows that the version that ran called the solver and was interrupted [C][N]. So the record does not single out ε ≈ 0.1 [I].
- **Anchors.** Two plots compare one anchored and one unanchored 4 × 20-point 2-D case (#c86-#c89) [N]. Commit: "visualizing symmetry mismatch, implemented far-away anchor approach" [D] (josh@2e0e731).
- **Bug.** "Same with 2 dimensions" (#c77) draws the target from the 50-D parameters of another simulation, so its 17% (from the saved argmax array, #c79) means nothing [C][I].

### 8. E6: anchoring methods (2026-01-21 → 01-26)

An anchor is one source–target pair known to be correct. Three ways to use it [C]:
- outlier anchor (`run_ot_with_anchor`): add 10 to every distance from the anchor in both datasets, so the two anchors become matching outliers (#c16);
- FGW label anchors (`fgw_with_label_anchors`): fused GW (FGW) adds a feature cost, here 10 between an anchor and any non-partner; α = 0.1 is the weight POT gives to the GW part (#c11, #c12). This is exact (not entropic) FGW on distances that are not divided by their maximum, so it is not a like-for-like comparison with the entropic GW used elsewhere [C];
- seeded GW (`gw_seeded`): start entropic GW (ε = 0.1) from a plan with 50× weight on the anchor pairs (#c20; helpers:474-523).

Stated conclusion (#c1): "Seeded GOT results in invidiual point pairing, but ideally have one anchor per population. FGW only results in individual point pairing, not symmetric alignment." [D] Commit: "Showed that initialization anchoring works for fixing symmetry issue, Fused GW does not" [D] (josh@c7b8333). The evidence for FGW and for the outlier anchor is one plot each (#c14, #c18) [N].

Headline (#c55): "Average 76% accuracy without anchoring, 100% accuracy with single seeded anchoring approach." [D] The values are never printed (#c51, #c54); only a plot exists (#c57) [N]. The seeded loop (#c53) passes `cloud_coords1, cloud_coords2`, which hold the last of the five simulations, instead of `coords1_list[i]` [C]. So "anchored" is five runs on one simulation with five different anchor pairs, while "unanchored" covers five simulations [I]. The anchors were picked by eye from PCA plots, and each pair lies in one population (2↔6, 11↔15 in population 0; 39↔34, 34↔21, 21↔24 in population 1) [C][I] (#c48, #c52). The "automated" picker uses the true labels of both datasets (#c25, #c36), and the 50-D test then used hand-typed anchors 88 and 95, not its output (8, 5) [C] (#c39, #c40). #c35 plots the plan of the 2-D example under the 50-D title [C].

### 9. E7: how many dimensions must separate subpopulations (2026-01-26 → 01-29)

Five populations × 20 points in 50 dimensions; population 0 has two subpopulations [C] (#c19). The sweep uses unanchored GW (`run_ot`, ε = 0.1), although the question says "anchored GOT" [C][D] (#c1, #c19). Runs were kept only if class accuracy was above 0.6; 15 of 25 runs were kept [C][N] (#c19).

| discriminative dimensions (of 50) | 2 | 5 | 10 | 25 | 50 |
|---|---|---|---|---|---|
| sublabel accuracy, 3 kept runs | 0.4, 0.4, 0.5 | 0.8, 0.5, 0.8 | 0.9, 1.0, 0.9 | 1.0, 0.9, 1.0 | 1.0, 1.0, 1.0 |

Source: [N] #c24, read back from a CSV that is now lost. Stated conclusion: "20% or more of dimensions need to show moderate subpopulation discrimination for GOT to match them. Sublabel accuracy does not appear to be affected by noise dimensions, but overall class accuracy is." [D] (#c1). The first sentence fits the table (10 of 50 dimensions give a mean of 0.93) [I]. In the noise sweep (10 discriminative dimensions, 0–40 noise dimensions, keep if above 0.7), 4 of 7 runs failed at 40 noise dimensions and the kept runs scored 0.84, 0.74 and 0.92 [N] (#c32). Failures were not monotonic in noise: 0 of 3 runs failed at 0 noise dimensions, 5 of 8 at 10, 0 of 3 at 20, 1 of 4 at 30 and 4 of 7 at 40 [N][I] (#c32). Sublabel values for this sweep exist only as a plot (#c36) [N].

### 10. E8: how far target means can move (2026-01-28 → 02-03)

Part 1, unanchored (#c17-#c22): 5 × 20 points, 50 dimensions (25 discriminative, 25 noise). A source/target pair was kept only if its class accuracy was above 0.7. The source was then matched to a new sample whose population means had each moved, in a random direction, by a fraction of the mean distance from each population centre to its nearest neighbour [C] (#c3, #c18). E8 defines this shift in its own `resample_point_clouds_subpops` (#c3); the helper's version has no shift option [C] (helpers:727-734). Shifted runs still above 0.7 [N] (#c22):

| mean shift | 0 | 0.05 | 0.10 | 0.15 | 0.20 | 0.50 | 1.00 |
|---|---|---|---|---|---|---|---|
| runs above 0.7, of 5 | 2 | 4 | 4 | 4 | 4 | 1 | 1 |

Even with no shift, 3 of 5 fresh samples failed: a swap is decided per run, not per distribution [N][I].

Part 2, seeded (#c25-#c32). The plan was 5 pairs with one anchor in each of the 5 populations [D] (#c25). The code ran three source/target pairs, shifted the same target sample step by step (`perturb_clouds_like_resample`, #c26) and ran `gw_seeded` with four hand-picked anchors per pair, one in each of populations 1–4 [C][I] (#c30, #c31). Population 0, whose subpopulations are scored, was never anchored [C][I]. Class / sublabel accuracy [N] (#c32):

| mean shift | 0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 1.0 |
|---|---|---|---|---|---|---|---|
| pair 0 | 1.0 / 0.9 | 1.0 / 0.9 | 1.0 / 0.9 | 1.0 / 0.9 | 1.0 / 1.0 | 0.4 / 0.0 | 0.0 / 0.0 |
| pair 1 | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 0.9 | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 0.9 |
| pair 2 | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 1.0 | 1.0 / 1.0 |

Stated conclusion: "Symmetry issues remain the dominant issue when moving distribution means. When there are not symmetry issues, both accuracy and sublabel accuracy are >=90% up to 40% of the the mean distance between nearest centroids when half of the dimensions are noise and half are discriminative." [D] (#c1; commit josh@3923f53). It holds for the three anchored pairs [N]. Part 2 differs from part 1 in two ways at once, the seeded start and a shifted copy of one target sample instead of a fresh sample, and has no unanchored run on the same pairs. So the gain cannot be credited to the seed alone [C][I].

### How often unanchored GW swapped populations

All runs: 5 populations × 20 points, 50 dimensions, ε = 0.1 [C].

| sweep | runs | class accuracy ≤ 0.7 | source |
|---|---|---|---|
| E7 first sweep, 2026-01-26 | 46 | 21 (46%) | [N][I] josh@fc6a940:e7_subpopulation_discrimination_sim.ipynb#c22 |
| E7 discriminative dimensions | 25 | 10 (40%) | [N][I] josh@main:e7_subpopulation_discrimination_sim.ipynb#c19 |
| E7 noise dimensions (some failures are lost signal, not swaps) | 25 | 10 (40%) | [N][I] #c32 |
| E8 part 1, unshifted pairs | 47 | 12 (26%) | [N][I] josh@main:e8_generative_distributional_discrepancy.ipynb#c18 |

### Leads that turned out wrong or incomplete

- "Successful translation in most" (josh@c861dce) rests on 7 hand-checked pairs; the 500-cell run is at chance [D][N]. The phylogeny work ran to 2025-09-30, not 07-21 [G].
- "32.7% type match" is human TSP1 against mouse in the grant notebook, one run of 6 types × 50 cells; chance is 16.7% [N][I].
- `tabula_make_samples` "differs on junyi and in Conny's repo": the only changes are one deleted pip message and the kernel metadata (name and Python version) (conny@8a9a103) [G].
- The 70 → 26% drop with more cells is mouse 0 against mouse 1, not cross-species [C].
- E5 "ε ≈ 0.1 best" is not supported by any valid saved sweep (section 7) [I]. E6 "76% → 100%" is markdown only, and its anchored half reused one simulation [C][D].
- The January pivot is josh@897360c ("started E5 (simulated Gromov exploration)", 2026-01-06); josh@c7b8333 and josh@3923f53 carry the anchoring conclusions [G].
- Byte-identical copies (same git blob) are confirmed for every F01 notebook and for `speciesot_simulation_helpers.py` on josh@main, josh@cellot, josh@junyi and in Conny's repo (conny:speciesOT/; E5–E8 under conny:speciesOT/archive/exploratory_notebooks/), with two exceptions [G]. `tabula_make_samples` differs on junyi and in Conny's repo (above). `speciesot_helpers.py` diverged after the split: Conny extended the cellot copy in three commits (josh@953e669, josh@ddc56ad, josh@44a995e; 2026-03-16 → 05-10; Conny's repo has the same file), while Josh kept editing main's copy until josh@ed90684 (2026-04-29) [G]. Conny's changes add functions and an option to `top_n_organisms_from_species`; they do not touch `run_ot`, `ot_between_organisms` or the samplers [C] (git diff a7f7301 origin/cellot).

## Verdict

Real data. In each design Josh tried, label-free GW on PCA coordinates computed separately for each dataset (or stored in each atlas) paired cells across species no better than chance on average: pig→human 43.2% vs 45.0%, mouse→human 19% vs about 23%, Tabula mouse→human mean 14.3% vs 20% [N][I]. Two single runs were above chance (46.5% vs 20%; 32.7% vs 16.7%) [N][I]. Within species the picture is mixed: mouse–mouse 50.5–65.5%, but human–human 13.5–48.5%, against 20% chance [N]. Every comparison is one run on 100–500 cells per side [C][N]. Unequal type proportions under uniform weights are a confound in the pig and mouse PBMC runs [I]. The evidence is enough to say that plain GW was not a working cross-species matcher in this setup. It is not enough to rank datasets, PCA dimensions or ε. The ε sweep cannot rank ε at all: the four smallest values gave no valid plan and the rest did not converge (section 6) [N].

Simulations. The firmest finding is that unanchored entropic GW often swaps whole populations even when source and target come from one distribution: 26–46% of runs in four sweeps had class accuracy ≤ 0.7 [N][I]. A correct seed was followed by perfect class accuracy in E8 part 2. But that is three pairs with four of five populations anchored by hand, and part 2 also changed how the target was made (section 10) [N][C]. E6's 76% → 100% cannot be used (loop bug, values never printed) [C]. E7's "20% of dimensions" rests on three kept runs per setting after failed runs were dropped, and E8's "40% shift" on three seeded pairs [C][N]. The claim "ε ≈ 0.1" is not supported; the grid that seemed to vary ε probably ran at ε = 0.1 throughout [I]. Whether anchoring helps on real cells was not tested in F01 [I].

The status "partly worked" reflects this split: a clear negative on real data, and a measured failure mode whose fix is not proven [I].

## Why it stopped

No stated reason. Real data: the last F01 notebook commit is josh@41e608c (2025-10-04). On 2025-10-06 Josh committed his first PerturbOT notebook (josh@7e69bb1, F02); josh@a9b9705's message mentions a PerturbOT tutorial, but that commit adds only `tabula_eda` [G]. Simulations: E8's "Potential Next Steps" (vary the variance; test whether within-population correlations prevent symmetry mismatch) were not run in F01 [D][G] (e8…#c1). The next commit started E9 on human immune data (josh@41683ec), and josh@4427104 reports "Cell type matching not working with regular gromov, even with ontology matching" [D]. That work continues in F03 (GW clustering, e2, e9–e11, e13; [F03-labels-ontology-and-distances.md](F03-labels-ontology-and-distances.md)) and F04 (FGW with orthologs, e14–e17, e19; [F04-gene-priors-and-standard-ot.md](F04-gene-priors-and-standard-ot.md)). The record suggests that the fix found here needs known correct pairs, which pushed the work toward label- and gene-informed variants [I].

## Problems in how it was done

- **Uniform weights with unequal cell-type mixes.** GW must pair every cell, so different type proportions force wrong-type pairs whatever the geometry. In the pig run, which looks one-to-one, at most 81.8% of pairs could match; the pig and mouse results mix this with any real failure (pig_human_gromov.ipynb#c41-#c42; mouse_human_gromov.ipynb#c39) [N][I].
- **Labels.** Labels are hand-named Leiden clusters at species-specific resolutions, lumped into coarse groups; the label sets differ between species (pig "Erythrocyte"; human "Macrophage", "pDC"), so some cells can never match (pig_human_gromov.ipynb#c11, #c19) [C].
- **Input quality.** The raw human 10x matrix likely includes empty droplets (14,264 barcodes) [C][N][I]. In the grant notebook the balanced Tabula Sapiens samples went through normalize + log1p twice, the unbalanced ones once, so the balanced-vs-unbalanced comparison also changes preprocessing (applegrant #c29-#c31, #c33) [N][I].
- **Species confounded with dataset.** Human–human GW distances compare samples from one atlas; human–mouse distances compare that atlas with another lab's data [I] (applegrant #c3, #c21).
- **Duplicates.** Sampling with replacement puts identical cells into the balanced grant samples (applegrant #c18; warnings in #c19, #c33) [C][N].
- **Few runs, no seeds in the simulations.** Every real-data comparison is one run. The simulations never set a seed (`seed=None`), and each setting has 3–5 kept runs [C]. The real-data subsamples used scanpy `subsample`, whose default `random_state=0` makes them repeatable for the same input (scanpy 1.11.5: mac:scGen v.s. CellOT/cellot/.venv/lib/python3.11/site-packages/scanpy/preprocessing/_deprecated/sampling.py:24; Josh had 1.11.3) [C][I]. The grant's balanced samples (`sc.pp.sample`, unseeded by default, same venv `preprocessing/_simple.py:898, 973`), the label shuffles and `sample_equal_cell_types` (pandas `.sample(frac=1)`) are not seeded [C].
- **Mixed kernel states.** Outputs are out of execution order or stale: pig_human #c29 vs #c36; applegrant #c29 (re-run) vs #c31 and #c33; e5 #c22; intraspecies #c49-#c51; pca_sinkhorn (two sessions, two baseline values, undefined `random_ste`) [N][C].
- **Selection on success.** E7 and E8 keep only runs above 0.6 or 0.7, so their plots and sublabel scores assume no swap happened (e7 #c19, #c32; e8 #c18, #c20) [C].
- **Oracle anchors.** Anchors were chosen by eye or from true labels (e6 #c25, #c36, #c52; e8 #c31). In E8 part 2 four of five populations were anchored, which leaves little for GW to decide [I]. The real problem has no known correct pairs [C][I].
- **Comparisons that change two things.** E8 part 2 vs part 1 changes both the seed and the way the target is made; E6 compares exact FGW on unnormalized distances with entropic GW on normalized ones (sections 8, 10) [C][I].
- **Code slips.** e6 #c53 reuses one simulation; e6 #c35 plots the 2-D plan under the 50-D title; e5 #c77 uses the wrong target; e5 #c61 never passes ε; applegrant #c62 reads target labels from the wrong sample (harmless only by luck); e7 #c22 writes the letters of "euclidean" into the distance column (harmless) [C].
- **Solver failures and convergence.** In pca_sinkhorn the warnings are printed once per run: the ε sweep gave no valid plan for ε ≤ 1e-4, and every other run there did not converge (#c9, #c16, #c22) [N][I]. Many other GW cells print "Sinkhorn did not converge" at least once (e.g. mouse_human #c34, applegrant #c39, intraspecies #c60, e5 #c8, e7 #c19, e8 #c18), so some plans there may be unconverged too [N][I].
- **Lost results.** The CSVs from E5, E7 and E8 are gone, except one checkpoint copy; many results exist only as plots [R][N].
- **Helper drift.** Re-running saved cells today changes results: `run_ot` now defaults to ε = 0.1 instead of reading the global 1e-3 of the early E5 cells [C]; `ot_between_organisms` on main returns three values while pca_sinkhorn unpacks two [C] (josh@main:speciesot_helpers.py:82-98); `sample_equal_cell_types` gained a missing-type guard after the October runs (josh@b296e07) [C]; `calc_random_mean_std` was committed two days after the notebook that imports it (josh@7e69bb1 vs josh@41e608c) [G]; E8 shadows the helper's resampler with its own (#c3) [C].
- **Fragile label lookup.** The cell-type table is read from CSV, so each list is a string and `in` does substring matching (intraspecies #c2, #c4) [C]. Applied to the checkpoint lists of atlas cell types, this gives a shared label to the mouse types "endothelial cell" and "smooth muscle cell", which are not in the table's mouse lists. It also maps the human types "muscle cell" to "smooth muscle cell", "glial cell" to "microglial cell" and "acinar cell" to "pancreatic acinar cell" [R][I] (fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_muris/.ipynb_checkpoints/tm_cell_types-checkpoint.csv, …/tabula_sapiens/.ipynb_checkpoints/ts_cell_types-checkpoint.csv). Endothelial and smooth muscle cells are two of the five section-5 types; how many such cells were in the samples was not checked.
- **Claims stronger than results.** "Successful translation in most", "within-species OT okay" (one human–human pair below chance), "ε ~0.1 optimal" and "76% → 100%" go beyond the saved outputs [D][N].

## Terms used here

- `E5`–`E8`: Josh's experiment numbers; cell 1 of each notebook holds Question, Hypothesis and Conclusion.
- `GOT`: Josh's short name for Gromov(-Wasserstein) OT, used in plot titles and conclusions.
- symmetry mismatch, "flipping": GW pairs whole populations with the wrong partner (see Setup).
- anchor, seeded GOT, "anchored initialization", "init anchoring": a known correct pair; with `gw_seeded`, used as the solver's starting plan.
- outlier-forced anchoring: `run_ot_with_anchor`, which makes the anchors far-away outliers.
- class accuracy: `compute_mapping_acc`; matching accuracy: `ot_between_organisms`, in percent.
- sublabel accuracy: subpopulation agreement inside population 0 (`sublabel_match_rate_from_gw`).
- discriminative dimensions (`P_disc`), noise dimensions (`noise_dims`): coordinates that separate subpopulations, and coordinates meant to be identical across populations.
- mean shift (`mean_change`): movement of target population means, as a fraction of the mean nearest-centre distance.
- `fully_paired_examples`, `non_flipping_examples`: counts of runs kept because class accuracy was above 0.6 or 0.7.
- `shared_cell_type`: label from Josh's mouse↔human table (31 rows in the final notebook; an older 33-row version also existed); `universal_cell_types`: types with at least 40 cells in every donor.
- `human_70_adatas`, `mouse_70_adatas`: per-donor samples named after an older 7 types × 10 cells version (intraspecies #c45, #c54).
- "unbalanced" / "balanced" (grant notebook): random cells vs 50 cells for each of six types.

## What the package needs from this

The package translates expression (scGen, CellOT) and evaluates it (R2, MMD); it has no GW or cell-pairing component [C] (josh@scgen-model-impl:src/speciesot/speciesot_core.py; ai_package@src:src/speciesot/pairing.py checks R2 inputs, not OT; no POT import under ai_package@src:src/). Nothing in F01 is a reference test for the current package [I].

If a GW pairing module is added, one synthetic test is worth keeping:

- **Name:** GW population swap and its seeded fix.
- **Inputs:** no files. Generate with josh@main:speciesot_simulation_helpers.py `generate_point_clouds_subpops(5, 20, 50, A=2, B=0.5, P_disc=25, SP=2, disc_pops=[0], discriminative_strength=2, noise_dims=25)` and `resample_point_clouds_subpops` with the same arguments (E8 part 1, e8 #c18) [C]. For mean shifts use E8's own `perturb_clouds_like_resample` (e8 #c26); the helper's resampler cannot shift [C].
- **Config:** Euclidean distances divided by their maximum; uniform weights; POT `entropic_gromov_wasserstein`, square loss, PPA, ε = 0.1; argmax pairing. Seeded version = `gw_seeded` (boost 50, 200 scaling steps) with one same-population anchor pair in each of populations 1–4, as in E8 part 2 (#c31; typed by hand, probably read off the plots in #c30) [C][I].
- **Expected:** unanchored, 12 of 47 runs in this setting (26%) had class accuracy ≤ 0.7, mostly at multiples of 0.2 [N] (e8 #c18); across all four sweeps the share was 26–46% [N]. Seeded, class accuracy 1.0 for 3 of 3 pairs at shifts up to 0.4 [N] (e8 #c32).
- **Tolerance:** no fixed configuration was ever rerun. For the 26% share, sampling error alone gives a binomial 95% interval of about 15–40% for 47 runs [I]. Seeds were never set, so new expected values must come from seeded runs; the old numbers only check the order of magnitude.

Not worth reproducing: the cross-species real-data runs. The pig matrix, the human `pbmc_10k_v3` file and the mouse 5k PBMC file are not in Josh's `data/` folder; the grant notebook's `data/human/tabula_sapiens_pbmc.h5ad` is [R] (ls, 2026-10-20). The final cell-type CSV is lost [R]. The outputs come from mixed kernel states, and each is a single run near chance [N][C]. The Tabula samples of section 4 exist and the section-5 per-type samples are seeded (seed 42), but the saved section-5 accuracies came from an older function definition and an uncertain sample size (section 5) [N][C]. `sample_equal_cell_types` and `calc_random_mean_std` draw without a seed [C] (josh@main:speciesot_helpers.py:101-155).

## Open questions

- What did the lost E5 sweeps show (5-cloud size, 2–10 populations, 2–50 dimensions, geodesic)? Only the PNG plots inside the notebook remain; I did not read images.
- Did the E5 ε × k grid vary ε? The record points to ε = 0.1 throughout (section 7), unless the `run_ot` cell was edited after it last ran.
- What were E6's five unanchored and five anchored accuracies, and what was unanchored accuracy on the fifth simulation alone?
- Do the six Tabula Sapiens compartment files share one `X_pca`? `ad.concat` keeps each file's `obsm['X_pca']`; if they were fitted separately, human cross-compartment distances in section 5 mean nothing. Not checked (no .h5ad opened).
- Was a grant comparison without erythrocytes run? An earlier execution shows 250 pairs (5 types × 50) (applegrant #c65) [N][I], but no distances for it.
- Where does the pig 10x data come from, and why was the raw human matrix used? The pig marker list cites Figure 4C of a 2021 Frontiers in Genetics paper (pig_human_gromov #c9) [D], which may also be the data source [I].
- Which POT version ran the 2025 notebooks (see Setup)?
- Were the Tabula Sapiens files (`TS_Bone_Marrow.h5ad` in `tabula_eda`, `tabula_sapiens_pbmc.h5ad` in the grant notebook) already log-normalized in `.X`? Conny's log says the CELLxGENE Tabula Sapiens `.X` is log-normalized [D] (conny:logs/research_logs/research_log_2026-04-20.txt:96-102); neither file was checked, and the grant notebook's warning is not evidence either way (Setup).
- Which settings produced intraspecies #c49-#c51 (execution counts 366–368), and which PCA dimension the pca_sinkhorn cell-number sweep used?

## Sources

- josh@main: README.md, notebook_descriptions.md (covers E1–E4 only), requirements.txt, tabula_eda.ipynb, tabula_make_samples.ipynb, phylogeny/pot_tutorial.ipynb, phylogeny/pig_human_gromov.ipynb, phylogeny/mouse_human_gromov.ipynb, phylogeny/mouse_human_gromov-applegrant.ipynb, intraspecies_vs_interspecies_dists.ipynb, pca_sinkhorn_optimization.ipynb, e5_simulated_distribution_maps.ipynb, e6_anchoring_methods_simulations.ipynb, e7_subpopulation_discrimination_sim.ipynb, e8_generative_distributional_discrepancy.ipynb, speciesot_helpers.py, speciesot_simulation_helpers.py.
- Older versions: josh@a9b9705 (tabula_eda); josh@b2782fb, josh@c861dce, josh@393065f, josh@e883909 (pig_human_gromov); josh@341b553, josh@7f16bb7, josh@36f44dc, josh@c1538ac, josh@860446a (intraspecies); josh@897360c, josh@710cc22, josh@ecb5685, josh@92841d0, josh@3fccffa, josh@2e0e731, josh@c7b8333 (e5); josh@c7b8333, josh@fc6a940 (e6); josh@2779936, josh@fc6a940, josh@75c55c5, josh@77a9e98 (e7); josh@860446a, josh@41e608c, josh@7e69bb1, josh@b296e07, josh@b5b2f79, josh@757b952 (speciesot_helpers.py); speciesot_simulation_helpers.py at josh@2e0e731, josh@c7b8333, josh@2779936, josh@fc6a940, josh@75c55c5, josh@77a9e98, josh@3923f53.
- Git: `git log` of josh origin/main for all files above; blob hashes on origin/main, origin/cellot, origin/junyi and conny HEAD; `git diff a7f7301 origin/cellot -- speciesot_helpers.py` and its log (josh@953e669, josh@ddc56ad, josh@44a995e); josh@scgen-model-impl:src/speciesot/speciesot_core.py; ai_package@src:src/speciesot/pairing.py, file list and a search for OT imports under src/.
- conny: docs/archaeology/inventory.csv, docs/archaeology/sources.md, docs/archaeology/models.md, docs/archaeology/metrics.md, speciesOT/tabula_make_samples.ipynb, conny@8a9a103 (diff), conny@c342331, logs/research_logs/research_log_2026-04-20.txt, logs/research_logs/research_log_2026-07-30_repo_plan.txt; headers of F02, F03 and F04 pages in docs/archaeology/experiments/.
- FASRC, Josh's directory (outside BK; ls on 2026-10-20): /n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/ and its subfolders human/, human_ref/, .ipynb_checkpoints/, tabula_muris/ (and its .ipynb_checkpoints/), tabula_sapiens/ (and its .ipynb_checkpoints/); …/speciesOT_env/lib/python3.12/site-packages/ (pot and scanpy dist-info) and …/ot/gromov/_bregman.py (grep). Files read: fasrc:/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/.ipynb_checkpoints/varying_cloud_size_010625-checkpoint.csv, …/tabula_cell_type_table-checkpoint.csv, …/data/tabula_muris/.ipynb_checkpoints/tm_cell_types-checkpoint.csv, …/data/tabula_sapiens/.ipynb_checkpoints/ts_cell_types-checkpoint.csv.
- fasrc:BK: searched the local mirror for E5/E7/E8 CSVs and Tabula files (none found); fasrc:BK/offline_data_manifest.txt.
- Library code read locally: scanpy 1.12.1 `preprocessing/_simple.py` in ~/miniconda3/envs/analysis; scanpy 1.11.5 `preprocessing/_simple.py` and `preprocessing/_deprecated/sampling.py` in mac:scGen v.s. CellOT/cellot/.venv/lib/python3.11/site-packages/scanpy/.

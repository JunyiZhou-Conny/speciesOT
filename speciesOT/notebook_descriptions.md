Each notebook addresses is an experiment with a research question, a hypothesis, and if finished, conclusions.

**Experiment #1**: e1_perturbot_interspecies1.ipynb
- Question: Does prior alignment (pairings) of cells within across species using Perturb-OT improve cell type prediction accuracy of a MLP+kNN approach?
- Hypothesis: Yes, because pairwise correspondences will enable better supervised learning of the relationships between genes across species.
- Conclusion: Using a Perturb-OT "get_coupling_egw_labels_ott" Sinkhorn entropy parameter of ~1e-8 when generating point-to-point pairings of mouse and human cells results in significantly higher cell type prediction accuracy.

**Experiment #2**: e2_gromov_clustering.ipynb
- Question: Which attributes do mice and humans cluster by based on GW distances with no labels, when equal cell type frequencies are enforced?
- Hypothesis: YOrganisms will first cluster by species, then by age, then by sex.
- Results:  Interspecies distances are usually, but not always, further from each other.
- Conclusion: Organisms cluster by species first, then inconsistently by sex and age.

**Experiment #3**: e3_oos_predictions_perturbot.ipynb
- Research question: Can PerturbOT predict the expression of out-of-sample cell types or subtypes excluded during Gromov mapping?
- Hypothesis: PerturbOT will be able to predict the expression of cells close to other cell types (e.g., CD4 T cells when other T cell are included in the Gromov step), but will not be able to predict the expression of cell types not well represented in the training set.
- Conclusion: This approach cannot predict OOS for hematopoeitic stem cells, regulatory T cells, or mast cells. I did not find any cell types this works for.

**Experiment #4**: e4_monocyte_subtype_alignment.ipynb
- Question: Can regular Gromov OT or PerturbOT correctly pair cell subtypes between mice and humans?
- Hypothesis: Perturb-OT will be able to pair cell subtypes for cell types where those subtypes are functionally similar and there are at least 3 subtypes. Regular entropic gromov OT will be inferior to Perturb-OT.
- Conclusion: Could not align T cells (CD4, CD8, and Tregs).
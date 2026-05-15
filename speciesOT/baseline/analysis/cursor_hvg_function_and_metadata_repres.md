# HVG function and metadata representation
_Exported on 4/19/2026 at 15:06:51 EDT from Cursor (3.0.12)_

---

**User**

@speciesOT/baseline/analysis/01.1_hvg_investigation.ipynb 
Are you aware of the `scanpy` library, which is for scRNA-seq analysis? There is a function that is trying to retrieve the highly variable genes, and I'm just curious about how this function operates on the annotated data objects. I'm aware that, being annotated in the object, there is a specific metadata that stores the different representations of the big UMI matrix (usually PCA, maybe other forms of representation).

I'm just thinking: when we're trying to use the HVG function, what does it do? I'm just wondering what it does. Also, what if we perform a lot of data preprocessing on this HVG matrix? Let's say we select columns with `filter_columns`, filter rows and filter columns and end up with a quite different UMI matrix, but still an H5AD file, if we perform that? I mean, we read in an H5AD file that operates very similarly to how a PANDAS library would do; it's essentially a matrix.

For instance, in my Jupyter notebook, I would assign these to a variable, let's just say `polished`. If we take a look at this `polished`, I think we can still see a lot of metadata, like the size of the matrix and the metadata alongside it. The metadata was inherited from the unpolished, the initial raw annotated data. From my perspective, it seems that the metadata after polishing is no longer a good representation of the polished data. 

And to follow up with that, is this a design choice by the annotated data itself, or is this something that I'm doing wrong, or I could be entirely wrong?

The next thing I want to investigate is that, after having this polished annotated dataset, we perform HVG on it. Granted, what I said is true. The HVG process data, let's just say we are selecting 1,000 genes, but the metadata is still inherited from the original annotated data, which is a false representation of the initial dataset.

The reason why I am thinking about this is because I am trying to examine our pre-processing steps. My mentor told me that there is a particular gene called PtPRC that should exist after performing HVG; however, it doesn't. I start tracing back. Before the HVG, what we did was try to do an ORS log mapping, a one-to-one ORS log mapping, and it results in a gene feature space of 14k. I try to see if this PtPRC gene is within that 14k, and it is, but after the HVG it doesn't exist anymore. 

There is my first confusion at the point that I saw my mentor, who believes that PtPRC should be within that, because I think she takes a look at the U-map and is trying to highlight the cells with PtPRC expressed. It is very much expressed, and I think I've seen it, so I believe PtPRC should be within that as well, but it does not exist in there.

Aside from that, for the 1000 HVG, I try to visualize the UMAP. The top ten should, at first, give me, for instance, the most highly expressed genes. Somehow it is actually ranked alphabetically, so it doesn't work that well. Later on, I am trying to rank them against dispersion norm, which I think is how HVG gets selected, and I still don't see a very good result. Maybe somewhere I am wrong, but this is definitely an experiment that I need to replicate in order to compare.

Let's say I visualize the top ten by dispersion norm, and then I try to visualize the PtPRC. If PtPRC doesn't exist in that 1000 HVG, however, from the UMAP it is highly expressed, then there must be something wrong that's going off, right? 

Another thing is that I don't fully grasp how this U-map gets to be visualized. I think this is one of the biggest issues. I think the U-map is also one of the metadata that exists in the annotated dataset; however, after iterations of data preprocessing, this U-map never gets updated. It's inherited from the top layer. I'm not sure if this is true, but this is my suspicion.

You can imagine that initially we have like 10,000 cells, but later on we'll reduce it to maybe only 5,000 cells, and also the gene column space also gets reduced. Does the U-map stay the same? Will we recalculate the U-map? Maybe not. We just inherit it from the top layers.

When we're doing the visualization to see which genes are highly expressed, what exactly are the UMAP specifics that we are visualizing? I mean, a fair comparison would be, okay, since PtPRC we know PtPRC doesn't exist in HVG space but it exists in the 14k space, which is after the one-to-one biomarker matching. Maybe a fair comparison would be: let's try to visualize the UMAP of this 14k genes and then highlight, let's say, the top 10 genes that have been selected by HVG and then PtPRC, and then let's do a comparison within that space. Maybe that's a fair comparison, because I couldn't do a comparison in the 1,000 HPG space, right, because PtPRC doesn't exist there. Or I'm wrong; I'm thinking I'm thinking about this entire thing wrong. 

---

**Cursor**

Let me read your notebook first to understand the specific workflow and then address all your questions.

This is a great set of questions, and your instincts are largely correct. Let me walk through each point systematically, referencing your specific code.

---

## 1. How `sc.pp.highly_variable_genes` works

This function does **not** select the most highly *expressed* genes. It selects the most highly *variable* genes -- genes whose expression varies the most across cells relative to other genes with similar mean expression. With `flavor='seurat'`, the algorithm:

1. Bins genes by their mean expression level
2. Within each bin, computes the dispersion (variance / mean) for each gene
3. Z-normalizes that dispersion within each bin, producing `dispersions_norm`
4. Ranks all genes by `dispersions_norm` and keeps the top `n_top_genes`

The critical implication: **a gene can be highly and uniformly expressed yet fail HVG selection**. PTPRC (CD45, `ENSG00000081237`) is a pan-leukocyte marker -- it's expressed in virtually all immune cells in your dataset. Because it's expressed broadly and relatively uniformly, its cell-to-cell variability is low compared to genes that sharply distinguish between cell types. That's precisely why it doesn't make the top 1000 HVGs even though it lights up beautifully on a UMAP.

Your mentor is right that PTPRC is clearly expressed (it's a canonical marker), and you're right that it's not in the HVG set. Both facts are consistent -- HVG and "highly expressed" are different things.

---

## 2. Metadata inheritance in AnnData -- your suspicion is correct

This is the core of your confusion and **you've correctly identified the issue**. When you subset an AnnData object:

```python
h = human_shared.copy()          # subset to ~14k ortholog genes
train_h = h[mask].copy()         # subset to non-T-cell rows
train_h = train_h[:, hvgs].copy() # subset to 1000 HVG columns
```

Each of these operations carries forward the `.obsm` dictionary, which contains `X_umap` and `X_pca`. Those embeddings were computed on the **original** dataset (all cells, all genes, possibly with different normalization). AnnData does not automatically recompute them.

This is **by design** in AnnData. AnnData is a container -- it stores whatever you put in it and doesn't make assumptions about what's stale. It's the analyst's responsibility to recompute embeddings after subsetting. This is pragmatic (recomputing UMAP every time you subset a column would be expensive and often unwanted), but it does create exactly the trap you've fallen into.

So when you run this in cell 38 of `01_data_preprocessing.ipynb`:

```72:76:speciesOT/baseline/analysis/01_data_preprocessing.ipynb
sc.pl.umap(train_h, color=[*hvgs[:10], 'cell_type'],
           ncols=3, frameon=False, s=10,
           title=[*[f'{g} (CD8 marker)' for g in hvgs[:10]], 'cell_type'])
plt.tight_layout()
plt.show()
```

The UMAP coordinates are **inherited from the original data** (before ortholog alignment, before holdout removal, before HVG selection). The x/y positions of cells on that plot reflect the original full gene space. Only the color overlay (gene expression values) comes from the current subset. This gives you a misleading picture because:

- The spatial layout doesn't represent the 1000-HVG space
- T cells were removed, so you see gaps in the plot where they used to be
- The neighborhood structure implied by cell proximity is from a different feature space entirely

---

## 3. What you should do instead

You correctly identified this in cell 16 of your investigation notebook, where you **recompute** everything from scratch:

```42:51:speciesOT/baseline/analysis/01.1_hvg_investigation.ipynb
sc.pp.scale(adata_for_umap, max_value=10)
sc.tl.pca(adata_for_umap, n_comps=50, random_state=42)
sc.pp.neighbors(adata_for_umap, n_neighbors=15, use_rep="X_pca", random_state=42)
sc.tl.umap(adata_for_umap, min_dist=0.3, random_state=42)

sc.pl.umap(
    adata_for_umap,
    color=[*hvg_df.index[:10].tolist(), "cell_type"],
    ncols=3, frameon=False, s=10,
)
```

This is the correct approach: PCA -> neighbors -> UMAP -> plot, all on the current data. Any time you substantially change the feature space (subset genes, subset cells, change normalization), you need to rerun this pipeline before the UMAP means anything.

---

## 4. The fair comparison you're proposing

Your intuition is sound. Here's what I'd suggest:

**Comparison A -- within the 14k ortholog space (before HVG):**
1. Take `human_shared` (the 14k-gene object after ortholog alignment)
2. Recompute PCA -> neighbors -> UMAP on it
3. Visualize PTPRC expression on this UMAP
4. Visualize the top 10 HVGs (by `dispersions_norm`) on this same UMAP
5. Now you're comparing PTPRC against the HVGs in a common coordinate system

**Comparison B -- within the 1000 HVG space:**
1. Take the HVG-subset data
2. Recompute PCA -> neighbors -> UMAP (as you did in cell 16 of 01.1)
3. Visualize the top 10 HVGs on this UMAP
4. You can't overlay PTPRC here because it's not in the 1000 columns, which is fine -- that's the point

Comparison A is the one that will answer your question: "Is the UMAP structure driven by genes like PTPRC, or by the HVGs?" You'll likely find that the HVGs capture the cluster structure well (that's what they're selected for), while PTPRC is expressed broadly and doesn't drive cluster separation.

---

## 5. Why the top-10-by-alphabetical issue happened

When you looked at `hvgs[:10]` and they appeared alphabetical, that's because `combined.var_names[combined.var.highly_variable]` returns genes in their **original column order** (which for Ensembl IDs is essentially alphabetical), not ranked by importance. To get the top 10 by dispersion, you need to sort explicitly as you did in cell 13 of 01.1:

```34:38:speciesOT/baseline/analysis/01.1_hvg_investigation.ipynb
hvg_df = combined.var.loc[combined.var.highly_variable].copy()
hvg_df = hvg_df.sort_values("dispersions_norm", ascending=False)

print("Top 10 HVGs by dispersion_norm:")
print(hvg_df[["means", "dispersions", "dispersions_norm"]].head(10))
```

Then use `hvg_df.index[:10]` instead of `hvgs[:10]` for your top-10 visualizations.

---

## Summary

| Your suspicion | Verdict |
|---|---|
| Metadata (UMAP, PCA) is inherited and never updated after subsetting | **Correct** -- AnnData preserves stale embeddings by design |
| PTPRC should be in HVGs because it's highly expressed | **Incorrect** -- HVG measures variability, not expression level. PTPRC is uniformly expressed across immune cells |
| The UMAP visualizations in the preprocessing notebook are misleading | **Correct** -- they use inherited coordinates from the original full-gene space |
| A fair comparison requires recomputing UMAP on the current feature space | **Correct** -- and you already did this in cell 16 of 01.1 |
| Something is "wrong" in the pipeline | **Partially** -- PTPRC not being in HVGs is expected behavior, but the stale UMAP coordinates in the preprocessing notebook are a genuine issue that should be fixed |

---

**User**

In terms of the first point, how these highly variable genes actually work, I think you might be true that a gene that is highly expressed doesn't necessarily mean that it's highly variable. Highly variable refers to genes whose expression varies the most across cells relative to other genes with similar mean expression. Things get confused by their mean expression level within each thing. Confuse the dispersion for each team, normalize the dispersion within each being produced as a discussion of its origin. All right, what's the point of doing highly variable genes? Selecting the ones that are highly variable would just mean I would just say it's different, just genes that express themselves quite differently, right?

I saw that there is a lot of data preprocessing in this life, and high-value genes seem to be something that is pretty common. I don't know why we are inputting this data into a model eventually. How does HVG assist or help with the prediction in the end?

You said that PDP-RC is clearly expressed. I don't know why you make that statement. I don't know why my mentor makes that statement. Maybe it's just a fact, just a kind of heuristic thing, but I just felt like my mentor thinks that PDP-RC should be in the HVG sets.

Yeah, I think I was right. The UMAP does not reflect the 1000 HVG space, but I'm still trying to visualize that, that's the top 10 highly variable genes in the original data space. Do you think this is an issue? Do you think I'm doing this wrong?

it's true that I did the re-computation. I standardized the data set using \`pp.scale\` using the PCA to reduce that functionality using the neighborhoods, and I set up to create a UMAP and then try to map the top ten. I kind of substantially changed the feature space. You're saying that every time I substantially change the feature space, I need to re-run this pipeline before the UMAP means anything? Okay, before the UMAP means anything, so what I previously did was not correct? I'm just thinking about the implication, like what kind of information is the UMAP trying to convey? Between the current approach, which you think is the correct approach, I'm just being very skeptical about PCA, neighbor, UMAP, and then POP. How does it compare to our previous approach? We're still operating on the initial UMAP, but then I'm trying to light up the PAG, like what does it, what does it tell us differently? How would it tell us differently, because I believe for you mouth we're looking at the UMAP; we're still seeing tons of cells, right, so the number of points on that map will be the same. Because of the feature space difference, how the cells cluster together is kind of different, right


---

**Cursor**

These are excellent questions. Let me address each one.

---

## Why do HVG selection at all?

The purpose is dimensionality reduction for downstream modeling. Your data starts with ~14k genes after ortholog alignment. Most of those genes are either:

- **Not expressed** (or barely expressed) in your cell population -- they add noise
- **Expressed uniformly** across all cells -- they carry no discriminative information

If you feed all 14k genes into a model (whether it's PCA, an autoencoder, or an optimal transport solver), the signal from the truly informative genes gets diluted by the noise from the uninformative ones. HVG selection keeps the genes that actually distinguish cell states from each other. Think of it as: "which genes, if I told you their expression level, would help you predict what type of cell you're looking at?" A gene that reads ~5 in every single cell tells you nothing. A gene that reads ~20 in T cells and ~0 in everything else tells you a lot -- and that gene would have high dispersion.

For your specific pipeline (cross-species optimal transport), HVG selection also reduces computational cost. OT solvers scale poorly with dimensionality, so going from 14k to 1000 features makes the problem tractable while retaining the most informative features.

---

## On PTPRC

I shouldn't have stated "PTPRC is clearly expressed" as if it were obvious from your data alone. Let me be more precise about why your mentor (and I) say that.

PTPRC (Protein Tyrosine Phosphatase Receptor Type C), also known as CD45, is one of the most well-characterized genes in immunology. It's the canonical pan-leukocyte marker -- it's expressed on the surface of essentially every white blood cell. This is textbook knowledge, not something derived from your specific UMAP. Your mentor likely knows this from domain expertise, and when she looked at the UMAP and saw PTPRC lighting up broadly, that confirmed what she already knew.

But here's the key: your mentor saying "PTPRC should be in the HVG set" might be a statement about what she thinks the pipeline *should* retain for biological reasons (it's an important marker gene), not a statement about what the statistical HVG algorithm will select. These are different things. The HVG algorithm is purely statistical -- it doesn't know that PTPRC is biologically important. If PTPRC is expressed uniformly across all your immune cells, the algorithm will rank it low on variability, even though biologists consider it essential. This is a well-known limitation of HVG selection: it can drop biologically meaningful genes that happen to be uniformly expressed within your particular dataset.

---

## The UMAP question -- what's actually different between the two approaches

This is the most important question you're asking, so let me be precise.

**What a UMAP is:** UMAP takes a high-dimensional point cloud (your cells, each described by N gene expression values) and projects it into 2D, trying to preserve the neighborhood structure. Cells that are "close" in the original N-dimensional space should be close on the UMAP.

**Your old approach** (cell 30 and 38 in `01_data_preprocessing.ipynb`): You take the inherited UMAP, which was computed on the *original* full gene set from the Tabula Sapiens data. The x/y position of each cell was determined by all ~20k+ original human genes. Then you color each dot by the expression of one of your 1000 HVGs.

**Your new approach** (cell 16 in `01.1_hvg_investigation.ipynb`): You recompute PCA, neighbors, and UMAP using only the 1000 HVGs. Now the x/y position of each cell is determined by just those 1000 genes.

**What changes concretely:**

The number of dots on the plot is the same (same cells). What changes is *where* each dot sits -- i.e., which cells are neighbors of which.

In the old UMAP, two cells might sit close together because they share expression patterns across 20k genes, even if their 1000-HVG profiles are quite different. In the new UMAP, proximity means similarity specifically in the HVG space, which is the space your model actually operates in.

Here's a concrete example. Suppose cell A and cell B are both macrophages, and they look very similar across all 20k genes. On the inherited UMAP, they sit right next to each other. But suppose the 1000 HVGs you selected happen to capture a tissue-level distinction (lung vs. liver macrophage), and cells A and B come from different tissues. On the recomputed UMAP, these two cells might be far apart -- because in the HVG space, the tissue signal dominates.

**So what does the old approach actually tell you?** When you overlay HVG expression onto the inherited UMAP, you're asking: "Among cells organized by their full transcriptomic profile, how does this particular HVG's expression distribute?" That's a valid biological question -- but it's not telling you how your model sees the data. Your model only sees 1000 genes. The recomputed UMAP shows you the structure *as your model perceives it*.

Neither approach is "wrong" in an absolute sense -- they answer different questions. But if you're trying to understand what your downstream OT model is working with, the recomputed UMAP is the honest one. The inherited UMAP can be actively misleading: clusters that look well-separated on it might collapse in HVG space, and vice versa.

---

## So when does re-computation matter?

You need to recompute when:

1. You **subset genes** significantly (14k to 1000) -- the feature space changed
2. You **remove cells** (dropping T cells) -- the neighborhood graph changed
3. You **change normalization** (scaling, log-transform) -- distances between cells changed

You do *not* need to recompute if you're just looking at the data to explore it informally and you understand what the inherited coordinates mean. But the moment you're making claims like "this gene drives cluster separation in my model's feature space," you need a UMAP that was built from that feature space.


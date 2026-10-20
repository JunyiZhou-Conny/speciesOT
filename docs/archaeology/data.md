# Data: datasets, preprocessing versions, and where they live

Every experiment used one of three data families: the mouse/human cell atlas,
the cross-species LPS data, or the BCG data. Each went through several
preprocessing versions, and the version matters as much as the model. This
page maps them. Counts and paths come from the family pages, which cite the
notebook cells and files. Locations are explained in [sources.md](sources.md),
and labels such as `v08` in the [glossary](glossary.md).

## 1. The mouse/human atlas (Tabula Muris, Tabula Sapiens)

**Raw inputs** are in Josh's FASRC folder (`fasrc:JOSH/data/`):

- the full atlases `tabula_muris/tabula_muris_all.h5ad` (about 6 GB) and
  `tabula_sapiens/tabula_sapiens_all.h5ad` (about 45 GB);
- the capped samples `sampled_mouse_shared.h5ad` (47,807 cells) and
  `sampled_human_shared.h5ad` (58,931 cells), with at most 1,000 cells per
  cell type and species ([F08](experiments/F08-hvg-flavor-matrix.md)).

In these files `.X` holds transformed values and `.raw` holds counts. The
mouse `.X` is clipped at 10 and scaled per gene
([F07](experiments/F07-toggle-iid-ood-and-renorm.md)).

**The preparation steps**, in order, as the hub's `prep` finally did them
([F09](experiments/F09-hub-and-metrics-infrastructure.md),
[F10](experiments/F10-monocytes-floor-ceiling-and-v08.md)):

1. **Orthologs.** BioMart one-to-one pairs: 14,451. The table is pinned only
   in git history, at `conny@c342331:scripts/.biomart_ortholog_cache.csv`.
2. **Assay filter** (v08 onward). Keep mouse 10x 3' v2 and human 10x 3' v3
   cells only.
3. **Cell matching.** Josh's ontology matcher keeps equal mouse and human
   counts per (cell type, tissue) pair, with seed 0
   ([F03](experiments/F03-labels-ontology-and-distances.md)).
4. **Normalization from raw counts.** `normalize_total` to 10,000, then
   `log1p`. Before 2026-04-20 the upstream `.X` was used instead (the "stale"
   data).
5. **HVG selection.** 1,000 genes, scored per species and merged; in the
   capped pool only 269 were variable in both species. Selection uses
   non-held-out cells only from May 2026 (decided on 2026-04-30); before that,
   held-out cells leaked in ([F06](experiments/F06-tcell-holdouts-speciesot-v1.md)).
   The flavor choice is covered in [F08](experiments/F08-hvg-flavor-matrix.md).
6. **Split.** `toggle_ood` on held-out cell types: `test_size` 0.2, seed 0,
   stratified by species from v08 on.
7. **Write** for anndata 0.7 (the `_v07` suffix).

**Versions:**

| version | dates | built from | what changed | used in |
|---|---|---|---|---|
| speciesot_v1, "stale" | 2026-03-18 → 04-20 | capped samples, upstream `.X` | mouse and human on different scales; HVGs include held-out cells | [F06](experiments/F06-tcell-holdouts-speciesot-v1.md), [F07](experiments/F07-toggle-iid-ood-and-renorm.md) |
| renorm | from 2026-04-21 | capped samples, `.raw` counts | scale bug fixed; 6,495 + 6,495 = 12,990 matched cells | [F07](experiments/F07-toggle-iid-ood-and-renorm.md) |
| HVG-flavor files `hvg_{flavor}_{group}_v07` | May 2026 | the 12,990-cell renorm pool | five HVG flavors × four T-cell holdouts | [F08](experiments/F08-hvg-flavor-matrix.md) |
| capped M1 / M2 v07 | May 2026 | same pool | monocyte holdouts | [F10](experiments/F10-monocytes-floor-ceiling-and-v08.md) |
| uncapped CD8 (v07) | 2026-05-26 → | full atlases | about 124,886 instead of 12,990 cells | [F10](experiments/F10-monocytes-floor-ceiling-and-v08.md) |
| **v08** M1, M2, CD8-uncapped (the "frozen benchmark") | from 2026-06-05 | capped samples (M1, M2: 8,054 cells) or full atlases (CD8: 89,760 cells, 44,880 pairs) | assay filter + species-stratified split | [F10](experiments/F10-monocytes-floor-ceiling-and-v08.md), [F14](experiments/F14-july-plans-a-to-d.md), [F15](experiments/F15-ae-repair-rounds-and-calibration.md), [F16](experiments/F16-deployment-models-and-mixhvg.md) |
| deployment sets `atlas_full` (v07), `*_uncapped_v08_iid`, `*_uncapped_v08` | May → 2026-08-18 | as above, no held-out type (or the iid twin) | used on BCG; never validated on the atlas | [F16](experiments/F16-deployment-models-and-mixhvg.md) |

The full per-cut table (cells, held-out cells, scored cells) is in
[F10](experiments/F10-monocytes-floor-ceiling-and-v08.md), "Setup".

Derived files are in `fasrc:BK/cellot/cellot_gpu/datasets/` (23 GB):
`speciesot-human-mouse/`, `-renorm/` and `-hvg/`. They are mostly in the
anndata-0.7 format.

Holdout groups (CD8, CD4, thymocyte, monocyte subsets) are decoded in the
[glossary](glossary.md#holdout-groups-side-by-side).

## 2. The cross-species LPS data (Hagai et al. 2018)

Bone-marrow mononuclear phagocytes from mouse, rat, rabbit and pig,
unstimulated (`unst`) or after 6 h of LPS (`LPS6`).

| file | what it is | used in |
|---|---|---|
| `train_species.h5ad` (`fasrc:BK/scgen-cellot-ablation/data/raw/`; also kept as `hvg-top1k-train-only.6619-backup.h5ad`) | scGen authors' training file: 62,114 cells × 6,619 one-to-one orthologs. With the validation file (15,528 cells) this is the paper's 77,642. | [F05](experiments/F05-first-cellot-runs-on-lps.md), [F12](experiments/F12-scgen-fig5-stage0-and-stage1.md), [F13](experiments/F13-autoresearch-loop.md), [F15](experiments/F15-ae-repair-rounds-and-calibration.md) |
| `hvg-top1k-train-only.h5ad` (`fasrc:BK/cellot/cellot_gpu/datasets/scrna-crossspecies/`) | A local cut to 1,000 HVGs (seurat flavor, all cells) for the CellOT-paper task. It is not the CellOT authors' own file. | [F11](experiments/F11-bunne-lps-replication.md) |
| Stage 1 arms A–D and the G250–G4000 arms (`fasrc:BK/scgen-cellot-ablation/data/processed/arms/`) | The same cells, with two splits and several gene sets | [F12](experiments/F12-scgen-fig5-stage0-and-stage1.md), [F13](experiments/F13-autoresearch-loop.md) |

The two splits are explained in the [glossary](glossary.md). In the scGen
split, rat unstimulated cells are in training; in the Bunne OOD split, no
rat cell is.

## 3. The BCG data

| data | source | cells after QC | final LT-HSC files |
|---|---|---|---|
| mouse PBS (untreated) and BCG (treated) | GEO GSE108067, 10x | 6,768 and 2,248 | 387 and 251 cells (`…_081826`) |
| human day 0 and day 90 | GEO GSE248728, captures 3 and 4 | 954 and 1,246 | 230 (day 0) and 392 (day 90) (`…_082626`) |

All of it is in Josh's folder `fasrc:JOSH/tb/data/`, which is outside the
backup. Batch-corrected (scANVI) files carry date tags: `080526`, `081826`,
`082626`. Model predictions are in
`fasrc:BK/cellot/cellot_gpu/datasets/speciesot-human-mouse-hvg/bcg_*`.

Known problems ([F17](experiments/F17-bcg-application.md)):

- the mouse mitochondrial filter did nothing;
- model inputs were normalized differently from the training atlas;
- the 1,000-gene axis holds few stem-cell genes;
- which human capture is day 0 and which is day 90 is not documented.

## 4. Other data

- CellOT's own benchmark datasets (4i, sciplex3, statefate, lupus patients)
  were downloaded to `fasrc:BK/cellot/cellot_gpu/datasets/`, but nothing in
  the results tree was trained on them ([models.md](models.md)).
- Josh's earlier PBMC files (pig, human 10k, mouse 5k) for the 2025 GW work
  are no longer in his data folder ([F01](experiments/F01-gw-feasibility-and-simulations.md)).

## 5. What `TrainingData` must decide

These follow from the steps above; [F18](experiments/F18-oop-package.md)
lists them among the package's open decisions.

- Whether gene alignment (orthologs) happens before the package or inside
  it, and with which table. Pinning the 14,451-pair cache reproduces the old
  data.
- Whether to split one joint mouse + human AnnData, as all old results did,
  or each species file separately, as the uncommitted code does. Only the
  joint split can be stratified by species and match the old split counts
  ([reference_experiments.md](reference_experiments.md) R3.4).
- Which normalization, and on which gene universe: normalize over the 14,451
  orthologs, then take the 1,000 HVGs. External data such as BCG must be
  treated the same way ([F16](experiments/F16-deployment-models-and-mixhvg.md)).
- How large files are read: the full human atlas is 45 GB, and the e24 test
  files alone are 7.7 GB ([F18](experiments/F18-oop-package.md)).

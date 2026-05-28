# experiments_inventory

Auto-generated from `./hub export md` (175 models).

Same data as `experiments_inventory.csv`. Grouped by family for browsability.

## IMPACT_CellOT (73)

| run_id | hvg | holdout | mode | R² | MMD | status |
|---|---|---|---|---|---|---|
| `baseline/speciesot_cd8/impact_or` | `—` | — | — | 0.681 | — | never_started |
| `gpu/atlas_full_pearson_residuals/impact_cellot` | `pearson_residuals` | — | — | — | — | done |
| `gpu/atlas_full_seurat_v3/impact_cellot` | `seurat_v3` | — | — | — | — | done |
| `gpu/hvg_cell_ranger_a_iid/impact_cellot` | `cell_ranger` | CL:0000625 | iid | 0.742 | 0.061 | done |
| `gpu/hvg_cell_ranger_a_ood/impact_cellot` | `cell_ranger` | CL:0000625 | ood | 0.759 | 0.062 | done |
| `gpu/hvg_cell_ranger_b_iid/impact_cellot` | `cell_ranger` | CL:0000625, CL:0000893 | iid | 0.843 | 0.038 | done |
| `gpu/hvg_cell_ranger_b_ood/impact_cellot` | `cell_ranger` | CL:0000625, CL:0000893 | ood | 0.510 | 0.079 | done |
| `gpu/hvg_cell_ranger_c_iid/impact_cellot` | `cell_ranger` | CL:0000624, CL:0000625, CL:0000893 | iid | 0.851 | 0.030 | done |
| `gpu/hvg_cell_ranger_c_ood/impact_cellot` | `cell_ranger` | CL:0000624, CL:0000625, CL:0000893 | ood | 0.628 | 0.067 | done |
| `gpu/hvg_cell_ranger_d_iid/impact_cellot` | `cell_ranger` | CL:0000624 | iid | 0.791 | 0.068 | done |
| `gpu/hvg_cell_ranger_d_ood/impact_cellot` | `cell_ranger` | CL:0000624 | ood | 0.833 | 0.066 | done |
| `gpu/hvg_pearson_residuals_a_iid/impact_cellot` | `pearson_residuals` | CL:0000625 | iid | 0.753 | 0.054 | done |
| `gpu/hvg_pearson_residuals_a_ood/impact_cellot` | `pearson_residuals` | CL:0000625 | ood | 0.897 | 0.105 | done |
| `gpu/hvg_pearson_residuals_a_ood_uncapped/impact_cellot` | `pearson_residuals` | CL:0000625 | ood | 0.848 | 0.051 | done |
| `gpu/hvg_pearson_residuals_b_iid/impact_cellot` | `pearson_residuals` | CL:0000625, CL:0000893 | iid | 0.843 | 0.026 | done |
| `gpu/hvg_pearson_residuals_b_ood/impact_cellot` | `pearson_residuals` | CL:0000625, CL:0000893 | ood | 0.861 | 0.083 | done |
| `gpu/hvg_pearson_residuals_c_iid/impact_cellot` | `pearson_residuals` | CL:0000624, CL:0000625, CL:0000893 | iid | 0.963 | 0.059 | done |
| `gpu/hvg_pearson_residuals_c_ood/impact_cellot` | `pearson_residuals` | CL:0000624, CL:0000625, CL:0000893 | ood | 0.896 | 0.078 | done |
| `gpu/hvg_pearson_residuals_d_iid/impact_cellot` | `pearson_residuals` | CL:0000624 | iid | 0.762 | 0.064 | done |
| `gpu/hvg_pearson_residuals_d_ood/impact_cellot` | `pearson_residuals` | CL:0000624 | ood | 0.921 | 0.105 | done |
| `gpu/hvg_pearson_residuals_m2_iid/impact_cellot` | `pearson_residuals` | CL:0000875, CL:0000576 | iid | 0.967 | 0.121 | done |
| `gpu/hvg_pearson_residuals_m2_ood/impact_cellot` | `pearson_residuals` | CL:0000875, CL:0000576 | ood | 0.930 | 0.108 | done |
| `gpu/hvg_seurat_a_iid/impact_cellot` | `seurat` | CL:0000625 | iid | 0.775 | 0.054 | done |
| `gpu/hvg_seurat_a_ood/impact_cellot` | `seurat` | CL:0000625 | ood | 0.812 | 0.101 | done |
| `gpu/hvg_seurat_b_iid/impact_cellot` | `seurat` | CL:0000625, CL:0000893 | iid | 0.889 | 0.089 | done |
| `gpu/hvg_seurat_b_ood/impact_cellot` | `seurat` | CL:0000625, CL:0000893 | ood | 0.646 | 0.063 | done |
| `gpu/hvg_seurat_c_iid/impact_cellot` | `seurat` | CL:0000624, CL:0000625, CL:0000893 | iid | 0.912 | 0.091 | done |
| `gpu/hvg_seurat_c_ood/impact_cellot` | `seurat` | CL:0000624, CL:0000625, CL:0000893 | ood | 0.736 | 0.099 | done |
| `gpu/hvg_seurat_d_iid/impact_cellot` | `seurat` | CL:0000624 | iid | 0.844 | 0.059 | done |
| `gpu/hvg_seurat_d_ood/impact_cellot` | `seurat` | CL:0000624 | ood | 0.803 | 0.067 | done |
| `gpu/hvg_seurat_v3_a_iid/impact_cellot` | `seurat_v3` | CL:0000625 | iid | 0.776 | 0.050 | done |
| `gpu/hvg_seurat_v3_a_ood/impact_cellot` | `seurat_v3` | CL:0000625 | ood | 0.824 | 0.106 | done |
| `gpu/hvg_seurat_v3_b_iid/impact_cellot` | `seurat_v3` | CL:0000625, CL:0000893 | iid | 0.811 | 0.032 | done |
| `gpu/hvg_seurat_v3_b_ood/impact_cellot` | `seurat_v3` | CL:0000625, CL:0000893 | ood | 0.571 | 0.072 | done |
| `gpu/hvg_seurat_v3_c_iid/impact_cellot` | `seurat_v3` | CL:0000624, CL:0000625, CL:0000893 | iid | 0.847 | 0.030 | done |
| `gpu/hvg_seurat_v3_c_ood/impact_cellot` | `seurat_v3` | CL:0000624, CL:0000625, CL:0000893 | ood | 0.518 | 0.069 | done |
| `gpu/hvg_seurat_v3_d_iid/impact_cellot` | `seurat_v3` | CL:0000624 | iid | 0.806 | 0.061 | done |
| `gpu/hvg_seurat_v3_d_ood/impact_cellot` | `seurat_v3` | CL:0000624 | ood | 0.884 | 0.107 | done |
| `gpu/hvg_seurat_v3_m2_iid/impact_cellot` | `seurat_v3` | CL:0000875, CL:0000576 | iid | 0.952 | 0.110 | done |
| `gpu/hvg_seurat_v3_m2_ood/impact_cellot` | `seurat_v3` | CL:0000875, CL:0000576 | ood | 0.903 | 0.136 | done |
| `gpu/hvg_seurat_v3_paper_a_iid/impact_cellot` | `seurat_v3_paper` | CL:0000625 | iid | 0.786 | 0.053 | done |
| `gpu/hvg_seurat_v3_paper_a_ood/impact_cellot` | `seurat_v3_paper` | CL:0000625 | ood | 0.773 | 0.056 | done |
| `gpu/hvg_seurat_v3_paper_b_iid/impact_cellot` | `seurat_v3_paper` | CL:0000625, CL:0000893 | iid | 0.797 | 0.035 | done |
| `gpu/hvg_seurat_v3_paper_b_ood/impact_cellot` | `seurat_v3_paper` | CL:0000625, CL:0000893 | ood | 0.397 | 0.082 | done |
| `gpu/hvg_seurat_v3_paper_c_iid/impact_cellot` | `seurat_v3_paper` | CL:0000624, CL:0000625, CL:0000893 | iid | 0.854 | 0.026 | done |
| `gpu/hvg_seurat_v3_paper_c_ood/impact_cellot` | `seurat_v3_paper` | CL:0000624, CL:0000625, CL:0000893 | ood | 0.681 | 0.050 | done |
| `gpu/hvg_seurat_v3_paper_d_iid/impact_cellot` | `seurat_v3_paper` | CL:0000624 | iid | 0.785 | 0.062 | done |
| `gpu/hvg_seurat_v3_paper_d_ood/impact_cellot` | `seurat_v3_paper` | CL:0000624 | ood | 0.774 | 0.062 | done |
| `gpu/renorm_cd4/swapped_cellot` | `—` | — | — | 0.816 | 0.044 | done |
| `gpu/renorm_cd8/swapped_cellot` | `—` | — | — | 0.775 | 0.060 | done |
| `gpu/renorm_cd8_thymo/swapped_cellot` | `—` | — | — | 0.747 | 0.057 | done |
| `gpu/renorm_tcell_subtypes/swapped_cellot` | `—` | — | — | 0.666 | 0.068 | done |
| `gpu/speciesot_cd4/speciesot_cellot` | `—` | — | — | 0.597 | 0.082 | done |
| `gpu/speciesot_cd8/impact_or` | `—` | — | — | 0.685 | 0.080 | done |
| `gpu/speciesot_cd8_nothymo/speciesot_cellot` | `—` | — | — | 0.674 | 0.073 | done |
| `gpu/speciesot_cpu/speciesot_cellot` | `—` | CL:0000084 | ood | — | — | done |
| `gpu/speciesot_tcell_subtypes/speciesot_cellot` | `—` | — | — | 0.641 | 0.058 | done |
| `gpu/toggle_m1_iid/impact` | `—` | CL:0000875 | iid | 0.790 | 0.032 | done |
| `gpu/toggle_m1_ood/impact` | `—` | CL:0000875 | ood | 0.731 | 0.036 | done |
| `gpu/toggle_m2_iid/impact` | `—` | CL:0000875, CL:0000576 | iid | 0.821 | 0.027 | done |
| `gpu/toggle_m2_ood/impact` | `—` | CL:0000875, CL:0000576 | ood | 0.752 | 0.031 | done |
| `gpu/toggle_m3_iid/impact` | `—` | CL:0000875, CL:0000860, CL:0002393, CL:0000576 | iid | 0.824 | 0.024 | done |
| `gpu/toggle_m3_ood/impact` | `—` | CL:0000875, CL:0000860, CL:0002393, CL:0000576 | ood | 0.641 | 0.032 | done |
| `gpu/toggle_m4_iid/impact` | `—` | CL:0000860 | iid | 0.680 | 0.056 | done |
| `gpu/toggle_m4_ood/impact` | `—` | CL:0000860 | ood | 0.714 | 0.051 | done |
| `gpu/toggle_t1_iid/impact` | `—` | CL:0000625 | iid | 0.867 | 0.022 | done |
| `gpu/toggle_t1_ood/impact` | `—` | CL:0000625 | ood | 0.841 | 0.022 | done |
| `gpu/toggle_t2_iid/impact` | `—` | CL:0000625, CL:0000893 | iid | 0.844 | 0.018 | done |
| `gpu/toggle_t2_ood/impact` | `—` | CL:0000625, CL:0000893 | ood | 0.829 | 0.020 | done |
| `gpu/toggle_t3_iid/impact` | `—` | CL:0000624, CL:0000625, CL:0000893 | iid | 0.872 | 0.015 | done |
| `gpu/toggle_t3_ood/impact` | `—` | CL:0000624, CL:0000625, CL:0000893 | ood | 0.797 | 0.023 | done |
| `gpu/toggle_t4_iid/impact` | `—` | CL:0000624 | iid | 0.760 | 0.049 | done |
| `gpu/toggle_t4_ood/impact` | `—` | CL:0000624 | ood | 0.773 | 0.049 | done |

## scGen (74)

| run_id | hvg | holdout | mode | R² | MMD | status |
|---|---|---|---|---|---|---|
| `baseline/speciesot_cd8/speciesot_scgen` | `—` | — | — | — | — | never_started |
| `gpu/atlas_full_pearson_residuals/scgen` | `pearson_residuals` | — | — | — | — | done |
| `gpu/atlas_full_seurat_v3/scgen` | `seurat_v3` | — | — | — | — | done |
| `gpu/cross_species_ood_scgen_gpu` | `—` | — | ood | — | — | running |
| `gpu/hvg_cell_ranger_a_iid/scgen` | `cell_ranger` | CL:0000625 | iid | 0.827 | 0.118 | done |
| `gpu/hvg_cell_ranger_a_ood/scgen` | `cell_ranger` | CL:0000625 | ood | 0.835 | 0.128 | done |
| `gpu/hvg_cell_ranger_b_iid/scgen` | `cell_ranger` | CL:0000625, CL:0000893 | iid | 0.882 | 0.106 | done |
| `gpu/hvg_cell_ranger_b_ood/scgen` | `cell_ranger` | CL:0000625, CL:0000893 | ood | 0.654 | 0.137 | done |
| `gpu/hvg_cell_ranger_c_iid/scgen` | `cell_ranger` | CL:0000624, CL:0000625, CL:0000893 | iid | 0.868 | 0.101 | done |
| `gpu/hvg_cell_ranger_c_ood/scgen` | `cell_ranger` | CL:0000624, CL:0000625, CL:0000893 | ood | 0.708 | 0.126 | done |
| `gpu/hvg_cell_ranger_d_iid/scgen` | `cell_ranger` | CL:0000624 | iid | 0.801 | 0.124 | done |
| `gpu/hvg_cell_ranger_d_ood/scgen` | `cell_ranger` | CL:0000624 | ood | 0.851 | 0.117 | done |
| `gpu/hvg_pearson_residuals_a_iid/scgen` | `pearson_residuals` | CL:0000625 | iid | 0.827 | 0.121 | done |
| `gpu/hvg_pearson_residuals_a_ood/scgen` | `pearson_residuals` | CL:0000625 | ood | 0.858 | 0.125 | done |
| `gpu/hvg_pearson_residuals_a_ood_uncapped/scgen` | `pearson_residuals` | CL:0000625 | ood | 0.932 | 0.116 | done |
| `gpu/hvg_pearson_residuals_b_iid/scgen` | `pearson_residuals` | CL:0000625, CL:0000893 | iid | 0.943 | 0.091 | done |
| `gpu/hvg_pearson_residuals_b_ood/scgen` | `pearson_residuals` | CL:0000625, CL:0000893 | ood | 0.845 | 0.117 | done |
| `gpu/hvg_pearson_residuals_c_iid/scgen` | `pearson_residuals` | CL:0000624, CL:0000625, CL:0000893 | iid | 0.947 | 0.086 | done |
| `gpu/hvg_pearson_residuals_c_ood/scgen` | `pearson_residuals` | CL:0000624, CL:0000625, CL:0000893 | ood | 0.902 | 0.105 | done |
| `gpu/hvg_pearson_residuals_d_iid/scgen` | `pearson_residuals` | CL:0000624 | iid | 0.878 | 0.121 | done |
| `gpu/hvg_pearson_residuals_d_ood/scgen` | `pearson_residuals` | CL:0000624 | ood | 0.902 | 0.122 | done |
| `gpu/hvg_pearson_residuals_m2_iid/scgen` | `pearson_residuals` | CL:0000875, CL:0000576 | iid | 0.936 | 0.142 | done |
| `gpu/hvg_pearson_residuals_m2_ood/scgen` | `pearson_residuals` | CL:0000875, CL:0000576 | ood | 0.892 | 0.146 | done |
| `gpu/hvg_seurat_a_iid/scgen` | `seurat` | CL:0000625 | iid | 0.866 | 0.107 | done |
| `gpu/hvg_seurat_a_ood/scgen` | `seurat` | CL:0000625 | ood | 0.831 | 0.116 | done |
| `gpu/hvg_seurat_b_iid/scgen` | `seurat` | CL:0000625, CL:0000893 | iid | 0.854 | 0.102 | done |
| `gpu/hvg_seurat_b_ood/scgen` | `seurat` | CL:0000625, CL:0000893 | ood | 0.768 | 0.149 | done |
| `gpu/hvg_seurat_c_iid/scgen` | `seurat` | CL:0000624, CL:0000625, CL:0000893 | iid | 0.876 | 0.091 | done |
| `gpu/hvg_seurat_c_ood/scgen` | `seurat` | CL:0000624, CL:0000625, CL:0000893 | ood | 0.809 | 0.119 | done |
| `gpu/hvg_seurat_d_iid/scgen` | `seurat` | CL:0000624 | iid | 0.856 | 0.098 | done |
| `gpu/hvg_seurat_d_ood/scgen` | `seurat` | CL:0000624 | ood | 0.866 | 0.103 | done |
| `gpu/hvg_seurat_v3_a_iid/scgen` | `seurat_v3` | CL:0000625 | iid | 0.834 | 0.107 | done |
| `gpu/hvg_seurat_v3_a_ood/scgen` | `seurat_v3` | CL:0000625 | ood | 0.828 | 0.113 | done |
| `gpu/hvg_seurat_v3_b_iid/scgen` | `seurat_v3` | CL:0000625, CL:0000893 | iid | 0.835 | 0.091 | done |
| `gpu/hvg_seurat_v3_b_ood/scgen` | `seurat_v3` | CL:0000625, CL:0000893 | ood | 0.643 | 0.125 | done |
| `gpu/hvg_seurat_v3_c_iid/scgen` | `seurat_v3` | CL:0000624, CL:0000625, CL:0000893 | iid | 0.875 | 0.080 | done |
| `gpu/hvg_seurat_v3_c_ood/scgen` | `seurat_v3` | CL:0000624, CL:0000625, CL:0000893 | ood | 0.668 | 0.111 | done |
| `gpu/hvg_seurat_v3_d_iid/scgen` | `seurat_v3` | CL:0000624 | iid | 0.854 | 0.101 | done |
| `gpu/hvg_seurat_v3_d_ood/scgen` | `seurat_v3` | CL:0000624 | ood | 0.869 | 0.103 | done |
| `gpu/hvg_seurat_v3_m2_iid/scgen` | `seurat_v3` | CL:0000875, CL:0000576 | iid | 0.891 | 0.126 | done |
| `gpu/hvg_seurat_v3_m2_ood/scgen` | `seurat_v3` | CL:0000875, CL:0000576 | ood | 0.862 | 0.136 | done |
| `gpu/hvg_seurat_v3_paper_a_iid/scgen` | `seurat_v3_paper` | CL:0000625 | iid | 0.838 | 0.105 | done |
| `gpu/hvg_seurat_v3_paper_a_ood/scgen` | `seurat_v3_paper` | CL:0000625 | ood | 0.840 | 0.112 | done |
| `gpu/hvg_seurat_v3_paper_b_iid/scgen` | `seurat_v3_paper` | CL:0000625, CL:0000893 | iid | 0.816 | 0.108 | done |
| `gpu/hvg_seurat_v3_paper_b_ood/scgen` | `seurat_v3_paper` | CL:0000625, CL:0000893 | ood | 0.642 | 0.124 | done |
| `gpu/hvg_seurat_v3_paper_c_iid/scgen` | `seurat_v3_paper` | CL:0000624, CL:0000625, CL:0000893 | iid | 0.848 | 0.079 | done |
| `gpu/hvg_seurat_v3_paper_c_ood/scgen` | `seurat_v3_paper` | CL:0000624, CL:0000625, CL:0000893 | ood | 0.688 | 0.112 | done |
| `gpu/hvg_seurat_v3_paper_d_iid/scgen` | `seurat_v3_paper` | CL:0000624 | iid | 0.837 | 0.100 | done |
| `gpu/hvg_seurat_v3_paper_d_ood/scgen` | `seurat_v3_paper` | CL:0000624 | ood | 0.851 | 0.098 | done |
| `gpu/renorm_cd4/scgen` | `—` | — | — | — | — | done |
| `gpu/renorm_cd8/scgen` | `—` | — | — | — | — | done |
| `gpu/renorm_cd8_thymo/scgen` | `—` | — | — | — | — | done |
| `gpu/renorm_tcell_subtypes/scgen` | `—` | — | — | — | — | done |
| `gpu/speciesot_cd4/speciesot_scgen` | `—` | — | — | — | — | done |
| `gpu/speciesot_cd8/speciesot_scgen` | `—` | — | — | — | — | done |
| `gpu/speciesot_cd8_nothymo/speciesot_scgen` | `—` | — | — | — | — | done |
| `gpu/speciesot_cpu/speciesot_scgen` | `—` | CL:0000084 | ood | — | — | done |
| `gpu/speciesot_tcell_subtypes/speciesot_scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_m1_iid/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_m1_ood/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_m2_iid/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_m2_ood/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_m3_iid/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_m3_ood/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_m4_iid/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_m4_ood/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_t1_iid/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_t1_ood/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_t2_iid/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_t2_ood/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_t3_iid/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_t3_ood/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_t4_iid/scgen` | `—` | — | — | — | — | done |
| `gpu/toggle_t4_ood/scgen` | `—` | — | — | — | — | done |

## CellOT (cell-type framing, abandoned) (25)

| run_id | hvg | holdout | mode | R² | MMD | status |
|---|---|---|---|---|---|---|
| `baseline/speciesot_cd8/cellot` | `—` | — | — | 0.615 | — | never_started |
| `gpu/_archive/toggle_cellot_subdirs/toggle_m1_iid/cellot` | `—` | species=human | iid | 0.949 | 0.019 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_m1_ood/cellot` | `—` | species=human | ood | 0.595 | 0.055 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_m2_iid/cellot` | `—` | species=human | iid | 0.945 | 0.019 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_m2_ood/cellot` | `—` | species=human | ood | 0.680 | 0.090 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_m3_iid/cellot` | `—` | species=human | iid | 0.972 | 0.008 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_m3_ood/cellot` | `—` | species=human | ood | 0.458 | 0.097 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_m4_iid/cellot` | `—` | species=human | iid | 0.776 | 0.058 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_m4_ood/cellot` | `—` | species=human | ood | 0.494 | 0.111 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_t1_iid/cellot` | `—` | species=human | iid | 0.909 | 0.016 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_t1_ood/cellot` | `—` | species=human | ood | 0.712 | 0.032 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_t2_iid/cellot` | `—` | species=human | iid | 0.917 | 0.012 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_t2_ood/cellot` | `—` | species=human | ood | 0.681 | 0.052 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_t3_iid/cellot` | `—` | species=human | iid | 0.884 | 0.013 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_t3_ood/cellot` | `—` | species=human | ood | 0.728 | 0.041 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_t4_iid/cellot` | `—` | species=human | iid | 0.796 | 0.045 | done |
| `gpu/_archive/toggle_cellot_subdirs/toggle_t4_ood/cellot` | `—` | species=human | ood | 0.415 | 0.080 | done |
| `gpu/renorm_cd4/normal_cellot` | `—` | — | — | 0.769 | 0.057 | done |
| `gpu/renorm_cd8/normal_cellot` | `—` | — | — | 0.730 | 0.086 | done |
| `gpu/renorm_cd8_thymo/normal_cellot` | `—` | — | — | 0.691 | 0.069 | done |
| `gpu/renorm_tcell_subtypes/normal_cellot` | `—` | — | — | 0.484 | 0.074 | done |
| `gpu/speciesot_cd4/speciesot_cellot_swapped` | `—` | — | — | 0.572 | 0.121 | done |
| `gpu/speciesot_cd8/cellot` | `—` | — | — | 0.624 | 0.109 | done |
| `gpu/speciesot_cd8_nothymo/speciesot_cellot_swapped` | `—` | — | — | 0.558 | 0.113 | done |
| `gpu/speciesot_tcell_subtypes/speciesot_cellot_swapped` | `—` | — | — | 0.507 | 0.053 | done |

## CellOT (legacy crossspecies) (3)

| run_id | hvg | holdout | mode | R² | MMD | status |
|---|---|---|---|---|---|---|
| `gpu/cross_species_ood` | `—` | — | ood | — | — | done |
| `gpu/race_cpu` | `—` | — | ood | 0.715 | 0.216 | done |
| `gpu/race_gpu_requeue` | `—` | — | ood | — | — | done |

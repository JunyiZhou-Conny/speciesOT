from __future__ import annotations
import pandas as pd
import scanpy as sc
import anndata as ad
import scipy as sp
from scipy import sparse
import matplotlib.pylab as pl
import matplotlib.pyplot as plt
import ot
import random
import torch
from sklearn.neighbors import NearestNeighbors
from sklearn.decomposition import PCA
import umap
from typing import Any, Dict, Hashable, List, Optional, Sequence, Tuple, Union

import re
import numpy as np


def label_uniform_cell_type_row(adata, shared_cell_type_table, species='human'):
    species_cell_types = adata.obs['cell_type']
    shared_cell_type_list = []
    for i in range(len(species_cell_types)):
        species_cell_type = species_cell_types.iloc[i]
        shared_cell_type = None
        for idx, row in shared_cell_type_table.iterrows():
            if species_cell_type in row[species+'_cell_types']:
                shared_cell_type = row['shared_cell_type']
        shared_cell_type_list.append(shared_cell_type)
    return shared_cell_type_list


def top_n_organisms_from_species(data_dir, n, species):
    # takes folder with .h5ad file containing all donors
    # returns list of n adata objects from the donors ordered by how many cells each has
    # pass n=-1 (or n=None) to return every donor

    all_adata = sc.read_h5ad(data_dir+'sampled_'+species+'_shared.h5ad')
    donor_counts = all_adata.obs['donor_id'].value_counts()

    if n is None or n == -1:
        top_organisms = donor_counts.index.tolist()
    elif isinstance(n, int) and n >= 0:
        top_organisms = donor_counts.index[:n].tolist()
    else:
        raise ValueError(
            f"n must be a non-negative int, -1, or None; got {n!r}"
        )

    top_adatas = []
    for organism in top_organisms:
        this_organism_adata = all_adata[all_adata.obs['donor_id']==organism]
        top_adatas.append(this_organism_adata)
    return top_adatas


def cell_types_with_n_per_organism(adata_list, n):
    # takes a list of adatas (species agnostic as long as they have 'shared_cell_type' obs
    # returns all cell types with n cells in each donor 
    
    universal_cell_types = set(adata_list[0].obs['shared_cell_type'].unique().tolist())

    for i in range(1,len(adata_list)):
        cell_type_vc = adata_list[i].obs['shared_cell_type'].value_counts()
        greater_than_n = set(cell_type_vc[cell_type_vc>=n].index.tolist())
        universal_cell_types = universal_cell_types.intersection(greater_than_n)

    return list(universal_cell_types)


def run_ot(d1, d2, n_samples, epsilon):
    # uses POT entropic GW
    xs = d1.obsm['X_pca']
    xt = d2.obsm['X_pca']
    C1 = sp.spatial.distance.cdist(xs, xs)
    C2 = sp.spatial.distance.cdist(xt, xt)

    C1 /= C1.max()
    C2 /= C2.max()
    
    p = ot.unif(n_samples)
    q = ot.unif(n_samples)
    
    # Proximal Point algorithm with Kullback-Leibler as proximal operator
    gw, log = ot.gromov.entropic_gromov_wasserstein(
    C1, C2, p, q, "square_loss", epsilon=epsilon, solver="PPA", log=True)
    
    return log["gw_dist"], gw


def ot_between_organisms(adata1, adata2, n_samples, epsilon):
    # uses POT entropic GW between two adatas
    d, gw = run_ot(adata1, adata2, n_samples, epsilon)
    argmax_arr = np.argmax(gw, axis=1)
    adata1_labels = adata1.obs['shared_cell_type'].tolist()
    adata2_labels = adata2.obs['shared_cell_type'].iloc[argmax_arr].tolist()
    
    matches = 0
    match_pairs = []
    for i in range(len(adata1_labels)):
        match_pairs.append((adata1_labels[i], adata2_labels[i]))
        if adata1_labels[i] == adata2_labels[i]:
            matches += 1
            
    matching_accuracy = 100*matches/adata1.n_obs
    
    return matching_accuracy, match_pairs, d


def sample_equal_cell_types(adata1, adata2, sample_size, exact_cell_type_match=None):
    # takes two adata objects
    # returns two adata objects with equal cell types in each, totaling sample_size # of cells
    
    cell_series_1 = adata1.obs["shared_cell_type"].sample(frac=1)
    cell_series_2 = adata2.obs["shared_cell_type"].sample(frac=1)
    
    index_list_1 = []
    index_list_2 = []
    
    cell_series_exact_1 = adata1[cell_series_1.index].obs["cell_type"]
    cell_series_exact_2 = adata2[cell_series_2.index].obs["cell_type"]

    i = 0
    while len(index_list_1) < sample_size:
        idx = cell_series_1.index[i]
        shared_cell_type = cell_series_1[idx]
        exact_cell_type = cell_series_exact_1[idx] # when we ant to force exact match between cell "subtypes" (like Tregs)
        if exact_cell_type == exact_cell_type_match:
            matches = (cell_series_exact_2 == exact_cell_type)
        else:
            matches = (cell_series_2 == shared_cell_type)
        if sum(matches) > 0:
            first_paired_idx = matches.idxmax()
            index_list_1.append(idx)
            index_list_2.append(first_paired_idx)
            cell_series_2[first_paired_idx] = None
            cell_series_exact_2[first_paired_idx] = None
        i += 1 
        
    return adata1[index_list_1], adata2[index_list_2]


def calc_random_mean_std(adatas, pairs, n):
    '''
    Calculates the mean and std of accuracy under null hypothesis of random pairings.
    * adatas = list of adata objects representing organisms
    * pairs = list of 2-tuples representing the possible pairings of adatas, indexed by their position in the adatas list
    * n = number of cells to include in each analysis (number of points that would be used in OT)
    '''
    random_accs = []
    for i in range(1000):
        pair = random.choice(pairs)
        adata1, adata2 = sample_equal_cell_types(adatas[pair[0]],adatas[pair[1]], n)
        types1 = adata1.obs['shared_cell_type'].sample(frac=1)
        types2 = adata2.obs['shared_cell_type']
        matches = 0
        for cell_num in range(len(types1)):
            if types1[cell_num] == types2[cell_num]:
                matches += 1
        random_accs.append(matches / len(types1))

    random_mean = np.mean(random_accs)    
    random_std = np.std(random_accs)
    return random_mean, random_std

def test_train_split_adata(a1, a2, train_ratio):
    num_cells = a1.shape[0]
    num_cells_train = int(num_cells * train_ratio)
    num_cells_test = num_cells - num_cells_train
    
    random_number_sample = random.sample(range(num_cells), num_cells_train)
    random_train_indices = a1[random_number_sample].obs_names
    random_test_indices = a2[random_number_sample].obs_names
    
    a1_train = a1[random_train_indices]
    a1_test = a1[~a1.obs_names.isin(random_train_indices)]
    a2_train = a2[random_test_indices]
    a2_test = a2[~a2.obs_names.isin(random_test_indices)]
    
    return a1_train, a1_test, a2_train, a2_test


def get_cell_type_from_index(adata, index):
    return adata[index].obs['shared_cell_type']


def create_label_to_sample_dicts(a1, a2):
    # takes two adata objects
    # returns X_dict, Y_dict, which are dicts of cell type # -> list of PCA embeddings of cells
    # also returns X_full_dict, Y_full_dict, which are dicts of cell type # -> list of full dim representations of cells
    # also retursn X_index_dict, Y_index_dict, which are dicts of cell type # -> list of indices of cells
    
    X_dict = {} # contains PCA (50-dim) embeddings
    Y_dict = {}
    X_full_dict = {} # contains full data points (20k+-dim), same order as X_full_dict
    Y_full_dict = {}
    X_index_dict = {} # contains indices of points corresponding to X_dict and X_full_dict
    Y_index_dict = {}

    n_samples = a1.shape[0]
    
    ct_list = a1.obs['shared_cell_type'].unique().tolist() # list of cell types
    ct_keys = {ct_list[i]: i for i in range(len(ct_list))} # dict of cell type -> number

    for ct in a1.obs['shared_cell_type'].unique().tolist():
        X_dict[ct_keys[ct]] = []
        X_full_dict[ct_keys[ct]] = []
        X_index_dict[ct_keys[ct]] = []

    for ct in a2.obs['shared_cell_type'].unique().tolist():
        Y_dict[ct_keys[ct]] = []
        Y_full_dict[ct_keys[ct]] = []
        Y_index_dict[ct_keys[ct]] = []

    for i in range(n_samples):
        ct_x = a1.obs['shared_cell_type'].iloc[i]
        rowx_i = a1[a1.obs['shared_cell_type'].index[i]].obsm['X_pca'].ravel() # just 50 PCA dims
        X_dict[ct_keys[ct_x]].append(rowx_i)
        full_rowx_i = a1[a1.obs['shared_cell_type'].index[i]].X.toarray().ravel()
        X_full_dict[ct_keys[ct_x]].append(full_rowx_i)
        X_index_dict[ct_keys[ct_x]].append(a1.obs['shared_cell_type'].index[i])

        ct_y = a2.obs['shared_cell_type'].iloc[i]
        rowy_i = a2[a2.obs['shared_cell_type'].index[i]].obsm['X_pca'].ravel()
        Y_dict[ct_keys[ct_y]].append(rowy_i)
        full_rowy_i = a2[a2.obs['shared_cell_type'].index[i]].X.toarray().ravel()
        Y_full_dict[ct_keys[ct_y]].append(full_rowy_i)
        Y_index_dict[ct_keys[ct_y]].append(a2.obs['shared_cell_type'].index[i])

    for k in list(X_dict.keys()):
        X_dict[k] = np.array(X_dict[k]).astype('float64')
        X_full_dict[k] = np.array(X_full_dict[k]).astype('float64')
        X_index_dict[k] = pd.Index(X_index_dict[k])

    for k in list(Y_dict.keys()):
        Y_dict[k] = np.array(Y_dict[k]).astype('float64')
        Y_full_dict[k] = np.array(Y_full_dict[k]).astype('float64')
        Y_index_dict[k] = pd.Index(Y_index_dict[k])
        
    return X_dict, Y_dict, X_full_dict, Y_full_dict, X_index_dict, Y_index_dict


def concat_index(indexes):
    """Concatenate multiple pd.Index objects vertically (preserve order & dups)."""
    idxs = [pd.Index(ix) for ix in indexes if ix is not None and len(ix) > 0]
    if not idxs:
        return pd.Index([], dtype=object)
    name = next((ix.name for ix in idxs if ix.name is not None), None)
    values = np.concatenate([ix.to_numpy() for ix in idxs])
    return pd.Index(values, name=name)


def show_cell_type_results(nn_indices, sorted_index, adata):
    # takes list of lists of cell indices
    # outputs list of list of cell types
    outer_lst = []
    for row in nn_indices:
        inner_lst = []
        for j in row:
            inner_lst.append(get_cell_type_from_index(adata, sorted_index[j]).iloc[0])
        outer_lst.append(inner_lst)
    return outer_lst


def cell_type_knn_acc(model, # trained pytorch model
                      X_eval, # numpy array to apply model to
                      Y_reference, # numpy array of target examples for use in kNN (often the training Y)
                      target_adata, # test Y adata object with cell type labels
                      sorted_reference_index, # sorted index of reference (often training Y) cells
                      sorted_test_index, # sorted index of test cells
                      n_neighbors=1 # k in kNN
                     ): #
    model.eval()
    device = next(model.parameters()).device
    with torch.inference_mode():
        preds = model(torch.from_numpy(X_eval).to(device).float()).cpu().numpy()
        
    nbrs = NearestNeighbors(n_neighbors=n_neighbors, algorithm='ball_tree').fit(Y_reference)
    
    reference_distances, reference_indices = nbrs.kneighbors(preds)
    cell_type_results_from_reference = show_cell_type_results(reference_indices, sorted_reference_index, target_adata)
    
    cell_type_result_list = []
    for i in range(len(cell_type_results_from_reference)):
        consensus_ct = max(set(cell_type_results_from_reference[i]), key=cell_type_results_from_reference[i].count)
        cell_type_result_list.append(consensus_ct)
        
    pred_ct_series = pd.Series(cell_type_result_list, index=sorted_test_index,)  # not actually correct index, but necessary for Series comparison
    true_ct_series = target_adata[sorted_test_index,].obs['shared_cell_type'] 
    
    baseline_acc = 100 * sum(true_ct_series == pred_ct_series) / len(pred_ct_series)
    return baseline_acc


def plot_predictions(train_adata, test_adata, pred_arr, pred_label, plot_pca=True, plot_umap=True):
    # PCA plot
    cell_groups = [train_adata.obsm['X_pca'], test_adata.obsm['X_pca'], pred_arr] # train, true, pred
    colors = ["navy", "turquoise", "darkorange"]
    labels = ["train", "true", "predicted"]
    
    if plot_pca:
        for i in range(len(cell_groups)):
            plt.scatter(cell_groups[i][:,0], cell_groups[i][:,1], color=colors[i], label=labels[i])
        plt.legend(loc="best", shadow=False, scatterpoints=1)
        plt.xlabel('PC 1')
        plt.ylabel('PC 2')
        plt.title("Predictions for " + pred_label + "s with Perturb-OT pre-alignment");
    
    if plot_umap:
    # UMAP plot
        all_cells = np.concatenate(cell_groups, axis=0)
        all_cell_labels = []
        all_cell_colors = []
        for i in range(len(cell_groups)):
            all_cell_labels += [labels[i]] * len(cell_groups[i])
            all_cell_colors += [colors[i]] * len(cell_groups[i])

        reducer = umap.UMAP()
        embedding = reducer.fit_transform(all_cells)

        plt.figure()
        plt.scatter(
            embedding[:, 0],
            embedding[:, 1],
            color=all_cell_colors,
            label=all_cell_labels
            )
        #plt.legend(loc="best", shadow=False, scatterpoints=1)
        plt.title('UMAP projection Perturb-OT predictions for ' + pred_label);


def split_adata_by_celltype_tissue(
    adata: "ad.AnnData",
    cell_type_key: str = "cell_type_ontology_term_id",
    tissue_key: str = "tissue_ontology_term_id",
    seed: int = 0,
    dropna: bool = True,
    cell_number: Optional[int] = None,
    min_per_cell_type: int = 1,
    return_match_table: bool = False,
) -> Tuple["ad.AnnData", "ad.AnnData"] | Tuple["ad.AnnData", "ad.AnnData", pd.DataFrame]:
    """
    Split a single AnnData into two AnnData objects that have identical multisets
    of (cell_type_key, tissue_key) identities.

    Only cell types with at least `min_per_cell_type` total cells are used.

    Default behavior (no cell_number):
      For each identity (cell_type, tissue) keep floor(n/2) pairs.

    If cell_number is provided:
      - Build the full matched-pair pool
      - Randomly sample exactly `cell_number` matched pairs

    Returns two subset copies of the original AnnData. If return_match_table=True
    also returns a DataFrame with columns ("cell_type","tissue","n","n_pairs").
    """
    for k in (cell_type_key, tissue_key):
        if k not in adata.obs:
            raise KeyError(f"{k!r} not found in adata.obs")

    rng = np.random.default_rng(seed)

    def _prep(a: ad.AnnData) -> pd.DataFrame:
        df = a.obs[[cell_type_key, tissue_key]].copy()
        df[cell_type_key] = df[cell_type_key].astype("string")
        df[tissue_key] = df[tissue_key].astype("string")
        if dropna:
            df = df.dropna(subset=[cell_type_key, tissue_key])
        df["__key__"] = df[cell_type_key].astype(str) + "|" + df[tissue_key].astype(str)
        return df

    obs = _prep(adata)

    # === NEW: filter by minimum cells per cell type ===
    if min_per_cell_type > 1:
        ct_counts = obs[cell_type_key].value_counts()
        keep_cell_types = ct_counts[ct_counts >= min_per_cell_type].index
        obs = obs[obs[cell_type_key].isin(keep_cell_types)]

    if obs.empty:
        empty_a = adata[:0].copy()
        empty_b = adata[:0].copy()
        if return_match_table:
            mt = pd.DataFrame(columns=["cell_type", "tissue", "n", "n_pairs"])
            return empty_a, empty_b, mt
        return empty_a, empty_b

    # counts per identity
    c = obs["__key__"].value_counts()
    n_pairs = (c // 2).astype(int)

    keep_keys = n_pairs[n_pairs > 0].index
    if len(keep_keys) == 0:
        empty_a = adata[:0].copy()
        empty_b = adata[:0].copy()
        if return_match_table:
            mt = pd.DataFrame(columns=["cell_type", "tissue", "n", "n_pairs"])
            return empty_a, empty_b, mt
        return empty_a, empty_b

    def _indices_by_key(df: pd.DataFrame, keys: pd.Index) -> dict[str, np.ndarray]:
        sub = df[df["__key__"].isin(keys)]
        return {k: g.index.to_numpy() for k, g in sub.groupby("__key__", sort=False)}

    idxs = _indices_by_key(obs, keep_keys)

    idx_a_list, idx_b_list, pair_key_list = [], [], []

    for key in keep_keys:
        k_pairs = int(n_pairs.at[key])
        if k_pairs <= 0:
            continue

        all_idx = idxs[key]
        perm = rng.permutation(all_idx)
        needed = 2 * k_pairs
        perm = perm[:needed]

        a_idx = perm[:k_pairs]
        b_idx = perm[k_pairs:needed]

        pair_key_list.append(np.repeat(key, k_pairs))
        idx_a_list.append(a_idx)
        idx_b_list.append(b_idx)

    idx_a_full = np.concatenate(idx_a_list)
    idx_b_full = np.concatenate(idx_b_list)

    total_pairs = idx_a_full.size

    if cell_number is not None:
        if cell_number > total_pairs:
            raise ValueError(f"cell_number={cell_number} exceeds total available pairs={total_pairs}")
        if cell_number < total_pairs:
            sel = rng.choice(total_pairs, size=cell_number, replace=False)
            idx_a_full = idx_a_full[sel]
            idx_b_full = idx_b_full[sel]

    a_split = adata[idx_a_full].copy()
    b_split = adata[idx_b_full].copy()

    if not return_match_table:
        return a_split, b_split

    cell_type = [k.split("|", 1)[0] for k in keep_keys]
    tissue = [k.split("|", 1)[1] for k in keep_keys]

    mt = (
        pd.DataFrame(
            {
                "cell_type": cell_type,
                "tissue": tissue,
                "n": c.loc[keep_keys].to_numpy(),
                "n_pairs": n_pairs.loc[keep_keys].to_numpy(),
            }
        )
        .sort_values(["cell_type", "tissue"])
        .reset_index(drop=True)
    )

    return a_split, b_split, mt

def match_cells_by_celltype_tissue(
    adata1: "ad.AnnData",
    adata2: "ad.AnnData",
    cell_type_key: str = "cell_type_ontology_term_id",
    tissue_key: str = "tissue_ontology_term_id",
    seed: int = 0,
    dropna: bool = True,
    cell_number: Optional[int] = None,
    return_match_table: bool = False,
) -> Tuple["ad.AnnData", "ad.AnnData"] | Tuple["ad.AnnData", "ad.AnnData", pd.DataFrame]:
    """
    Default: returns the maximum number of matched cells under exact identity matching:
      identity = (cell_type_key, tissue_key)
      cell type is inferred, subjective
      tissue is ground truth
      keep per-identity min(n1, n2) cells in each AnnData (total maximized).

    If cell_number is provided:
      - first build the full matched pool (same as above),
      - then randomly sample EXACTLY `cell_number` matched cell-pairs (one cell from each adata)
        from the full pool, preserving identity equality one-to-one.

    Returns two new AnnData objects (subset copies) with the same multiset of identities.
    """

    for k in (cell_type_key, tissue_key):
        if k not in adata1.obs:
            raise KeyError(f"{k!r} not found in adata1.obs")
        if k not in adata2.obs:
            raise KeyError(f"{k!r} not found in adata2.obs")

    rng = np.random.default_rng(seed)

    def _prep(a: ad.AnnData) -> pd.DataFrame:
        df = a.obs[[cell_type_key, tissue_key]].copy()
        df[cell_type_key] = df[cell_type_key].astype("string")
        df[tissue_key] = df[tissue_key].astype("string")
        if dropna:
            df = df.dropna(subset=[cell_type_key, tissue_key])
        # single stable key (avoids pandas tuple-indexing ambiguity)
        df["__key__"] = df[cell_type_key].astype(str) + "|" + df[tissue_key].astype(str)
        return df

    obs1 = _prep(adata1)
    obs2 = _prep(adata2)

    c1 = obs1["__key__"].value_counts()
    c2 = obs2["__key__"].value_counts()
    shared = c1.index.intersection(c2.index)

    if len(shared) == 0:
        empty1 = adata1[:0].copy()
        empty2 = adata2[:0].copy()
        if return_match_table:
            mt = pd.DataFrame(columns=["cell_type", "tissue", "n1", "n2", "n_keep"])
            return empty1, empty2, mt
        return empty1, empty2

    # per-identity max keep
    n_keep = pd.Series(
        np.minimum(c1.loc[shared].to_numpy(), c2.loc[shared].to_numpy()),
        index=shared,
        dtype=int,
    )

    # Build matched "slots": one row per matched cell-pair (idx1, idx2 share the same identity)
    # This enables uniform sampling of `cell_number` matched pairs across the full pool.
    def _indices_by_key(df: pd.DataFrame, keys: pd.Index) -> dict[str, np.ndarray]:
        sub = df[df["__key__"].isin(keys)]
        return {k: g.index.to_numpy() for k, g in sub.groupby("__key__", sort=False)}

    idxs1 = _indices_by_key(obs1, n_keep.index)
    idxs2 = _indices_by_key(obs2, n_keep.index)

    key_list = []
    i1_list = []
    i2_list = []

    for key in n_keep.index:
        k = int(n_keep.at[key])
        if k <= 0:
            continue

        a1 = idxs1[key]
        a2 = idxs2[key]

        # choose exactly k cells per dataset for this identity (without replacement)
        pick1 = a1 if a1.size == k else rng.choice(a1, size=k, replace=False)
        pick2 = a2 if a2.size == k else rng.choice(a2, size=k, replace=False)

        key_list.append(np.repeat(key, k))
        i1_list.append(pick1)
        i2_list.append(pick2)

    keys_expanded = np.concatenate(key_list) if key_list else np.array([], dtype=object)
    idx1_full = np.concatenate(i1_list) if i1_list else np.array([], dtype=object)
    idx2_full = np.concatenate(i2_list) if i2_list else np.array([], dtype=object)

    total_matched = idx1_full.size

    # Optional downsampling to a fixed number of matched pairs
    if cell_number is not None:
        if cell_number < 0:
            raise ValueError("cell_number must be >= 0")
        if cell_number > total_matched:
            raise ValueError(f"cell_number={cell_number} exceeds total matched pairs={total_matched}")
        if cell_number < total_matched:
            sel = rng.choice(total_matched, size=cell_number, replace=False)
            idx1_full = idx1_full[sel]
            idx2_full = idx2_full[sel]
            keys_expanded = keys_expanded[sel]

    a1m = adata1[idx1_full].copy()
    a2m = adata2[idx2_full].copy()

    if not return_match_table:
        return a1m, a2m

    # Aggregated match table (based on the MAX pool, not necessarily the downsampled selection)
    cell_type = [k.split("|", 1)[0] for k in shared]
    tissue = [k.split("|", 1)[1] for k in shared]
    mt = (
        pd.DataFrame(
            {
                "cell_type": cell_type,
                "tissue": tissue,
                "n1": c1.loc[shared].to_numpy(),
                "n2": c2.loc[shared].to_numpy(),
                "n_keep": n_keep.loc[shared].to_numpy(),
            }
        )
        .sort_values(["cell_type", "tissue"])
        .reset_index(drop=True)
    )
    return a1m, a2m, mt


def combine_transport_plans(
    T_dict: Dict[Hashable, Union[np.ndarray, "sparse.spmatrix"]],
    source_index_dict: Dict[Hashable, Sequence[str]],
    target_index_dict: Dict[Hashable, Sequence[str]],
    source_adata: Any,
    target_adata: Any,
    *,
    key_order: Optional[Sequence[Hashable]] = None,
    return_dense: bool = True,
) -> Tuple[
    Union[np.ndarray, "sparse.spmatrix"],
    List[Any], List[Any],
    List[Any], List[Any],
]:
    """
    Combine per-cell-type transport plans into one big block-diagonal matrix,
    and return ordered cell type + subtype lists for BOTH source rows and target columns.

    Annotations are pulled from:
      - adata.obs['shared_cell_type']  (cell type)
      - adata.obs['cell_type']         (subtype)

    Parameters
    ----------
    T_dict
        Dict: key -> transport plan matrix for that key (shape: n_src_key x n_tgt_key).
    source_index_dict
        Dict: key -> list of SOURCE cell IDs for the ROWS of T_dict[key].
    target_index_dict
        Dict: key -> list of TARGET cell IDs for the COLS of T_dict[key].
    source_adata, target_adata
        AnnData-like objects for source/target; cell IDs must match obs index.
    key_order
        Optional explicit ordering of keys for stacking blocks.
    return_dense
        If True, return dense numpy array; if False and scipy available, return CSR sparse.

    Returns
    -------
    T_big
        Combined (non-normalized) transport plan matrix (block diagonal).
    source_cell_types
        List aligned with rows of T_big: source_adata.obs['shared_cell_type'].
    source_cell_subtypes
        List aligned with rows of T_big: source_adata.obs['cell_type'].
    target_cell_types
        List aligned with columns of T_big: target_adata.obs['shared_cell_type'].
    target_cell_subtypes
        List aligned with columns of T_big: target_adata.obs['cell_type'].
    """
    # ---- validate keys ----
    t_keys = set(T_dict.keys())
    s_keys = set(source_index_dict.keys())
    g_keys = set(target_index_dict.keys())

    if t_keys != s_keys or t_keys != g_keys:
        raise ValueError(
            "Keys must match across T_dict, source_index_dict, and target_index_dict.\n"
            f"Missing in source_index_dict: {sorted(t_keys - s_keys) if (t_keys - s_keys) else None}\n"
            f"Missing in target_index_dict: {sorted(t_keys - g_keys) if (t_keys - g_keys) else None}\n"
            f"Extra in source_index_dict: {sorted(s_keys - t_keys) if (s_keys - t_keys) else None}\n"
            f"Extra in target_index_dict: {sorted(g_keys - t_keys) if (g_keys - t_keys) else None}"
        )

    # ---- determine order ----
    if key_order is not None:
        key_list = list(key_order)
        if set(key_list) != t_keys:
            raise ValueError("key_order must contain exactly the same keys as T_dict.")
    else:
        # try sorting; if not sortable, fall back to insertion order
        try:
            key_list = sorted(T_dict.keys())
        except TypeError:
            key_list = list(T_dict.keys())  # insertion order (Py3.7+)

    # ---- collect blocks, ids, shapes ----
    blocks: List[Union[np.ndarray, "sparse.spmatrix"]] = []
    src_ids_ordered: List[str] = []
    tgt_ids_ordered: List[str] = []
    row_block_sizes: List[int] = []
    col_block_sizes: List[int] = []
    any_sparse = False

    for k in key_list:
        T = T_dict[k]
        if sp is not None and sparse.issparse(T):
            any_sparse = True
            r, c = T.shape
        else:
            T = np.asarray(T)
            r, c = T.shape

        s_ids = list(source_index_dict[k])
        t_ids = list(target_index_dict[k])

        if len(s_ids) != r:
            raise ValueError(
                f"Row count mismatch for key {k}: "
                f"T_dict[{k}].shape[0]={r} but len(source_index_dict[{k}])={len(s_ids)}"
            )
        if len(t_ids) != c:
            raise ValueError(
                f"Col count mismatch for key {k}: "
                f"T_dict[{k}].shape[1]={c} but len(target_index_dict[{k}])={len(t_ids)}"
            )

        blocks.append(T_dict[k])
        src_ids_ordered.extend(s_ids)
        tgt_ids_ordered.extend(t_ids)
        row_block_sizes.append(r)
        col_block_sizes.append(c)

    total_rows = int(np.sum(row_block_sizes))
    total_cols = int(np.sum(col_block_sizes))

    # ---- build combined matrix ----
    use_sparse = (not return_dense) and (sp is not None)

    if use_sparse:
        if sp is None:
            raise ImportError("scipy is required to return a sparse matrix.")
        T_big = sparse.csr_matrix((total_rows, total_cols), dtype=float)
        r0 = 0
        c0 = 0
        for T in blocks:
            r, c = T.shape
            T_block = T if sparse.issparse(T) else sparse.csr_matrix(np.asarray(T))
            T_big[r0:r0 + r, c0:c0 + c] = T_block
            r0 += r
            c0 += c
        T_big = T_big.tocsr()
    else:
        T_big = np.zeros((total_rows, total_cols), dtype=float)
        r0 = 0
        c0 = 0
        for T in blocks:
            r, c = T.shape
            if sp is not None and sparse.issparse(T):
                T = T.toarray()
            else:
                T = np.asarray(T)
            T_big[r0:r0 + r, c0:c0 + c] = T
            r0 += r
            c0 += c

    # ---- helper: annotate ids from an adata ----
    def _annotate(adata: Any, ids: List[str], side: str) -> Tuple[List[Any], List[Any]]:
        obs = adata.obs
        if "shared_cell_type" not in obs.columns:
            raise KeyError(f"{side}_adata.obs must contain 'shared_cell_type'.")
        if "cell_type" not in obs.columns:
            raise KeyError(f"{side}_adata.obs must contain 'cell_type'.")

        obs_sub = obs.reindex(ids)

        if obs_sub.isnull().all(axis=None):
            raise ValueError(
                f"None of the provided {side} cell IDs were found in {side}_adata.obs index. "
                f"Make sure {side}_index_dict values match {side}_adata.obs_names / {side}_adata.obs.index."
            )

        missing_mask = obs_sub["shared_cell_type"].isna() | obs_sub["cell_type"].isna()
        if bool(missing_mask.any()):
            missing_ids = obs_sub.index[missing_mask]
            raise ValueError(
                f"{len(missing_ids)} {side} cell IDs were not found or lacked annotations in {side}_adata.obs. "
                f"Example IDs: {list(missing_ids[:10])}"
            )

        return obs_sub["shared_cell_type"].tolist(), obs_sub["cell_type"].tolist()

    source_cell_types, source_cell_subtypes = _annotate(source_adata, src_ids_ordered, "source")
    target_cell_types, target_cell_subtypes = _annotate(target_adata, tgt_ids_ordered, "target")

    return (
        T_big,
        source_cell_types, source_cell_subtypes,
        target_cell_types, target_cell_subtypes,
    )

def convert_ensembl_to_gene_symbols(
    adata,
    species: str = "human",
    make_unique: bool = True,
    keep_original_if_missing: bool = True,
    store_in_var: bool = True,
    var_symbol_key: str = "gene_symbol",
):
    """
    Convert adata.var_names from Ensembl gene IDs to gene symbols (robust to NaNs/duplicates).

    - Strips Ensembl version suffixes (ENSG... .15 -> ENSG...)
    - Maps via mygene
    - Ensures var_names are strings (prevents var_names_make_unique TypeError)
    - For missing mappings, keeps original ID (default) so no NaNs in var_names

    Modifies adata in place.
    """
    import re
    import numpy as np

    try:
        import mygene
    except ImportError as e:
        raise ImportError("Please install mygene: pip install mygene") from e

    # Original IDs as strings
    orig_ids = adata.var_names.astype(str)

    # Clean IDs (remove version suffix)
    clean_ids = np.array([re.sub(r"\.\d+$", "", gid) for gid in orig_ids], dtype=object)

    mg = mygene.MyGeneInfo()

    # Query mapping; return a list of dicts (easier to robustly parse than dataframe)
    res = mg.querymany(
        clean_ids.tolist(),
        scopes="ensembl.gene",
        fields="symbol",
        species=species,
        as_dataframe=False,
        returnall=False,
        verbose=False,
    )

    # Build mapping clean_id -> symbol
    symbol_map = {}
    for r in res:
        # r example keys: 'query', '_id', 'symbol', 'notfound'
        q = r.get("query")
        if not q:
            continue
        if r.get("notfound", False):
            continue
        sym = r.get("symbol", None)
        if sym is None:
            continue
        symbol_map[q] = sym

    # Construct new names, avoiding NaN/None
    new_names = []
    for orig, clean in zip(orig_ids.tolist(), clean_ids.tolist()):
        sym = symbol_map.get(clean, None)
        if sym is None:
            new_names.append(orig if keep_original_if_missing else clean)
        else:
            new_names.append(str(sym))

    # Optionally store fields in .var
    if store_in_var:
        adata.var["ensembl_id"] = orig_ids
        adata.var["ensembl_id_stripped"] = clean_ids
        adata.var[var_symbol_key] = new_names

    # Set var_names (must be strings)
    adata.var_names = np.array(new_names, dtype=str)

    # Make unique (now safe because everything is str)
    if make_unique:
        adata.var_names_make_unique()


def strip_ensembl_gene_id(x: str) -> str:
    """Remove Ensembl version suffix from a gene id (e.g. ``ENSG....15`` -> ``ENSG...``)."""
    return re.sub(r"\.\d+$", "", str(x))


# Ensembl regional BioMart mirrors (try next if one returns Query ERROR / DB down).
_DEFAULT_BIOMART_HOSTS: Tuple[str, ...] = (
    "www.ensembl.org",
    "useast.ensembl.org",
    "uswest.ensembl.org",
    "asia.ensembl.org",
)


def _normalize_biomart_host(host: str) -> str:
    from urllib.parse import urlparse

    h = host.strip()
    if h.startswith("http://") or h.startswith("https://"):
        h = urlparse(h).netloc or h
    return h


def _biomart_host_order(primary: str, extra: Optional[Sequence[str]]) -> list[str]:
    """Unique host list: ``extra`` first if given, else ``primary`` then defaults (deduped)."""
    seen: set[str] = set()
    out: list[str] = []
    if extra is not None:
        for h in extra:
            hn = _normalize_biomart_host(str(h))
            if hn and hn not in seen:
                seen.add(hn)
                out.append(hn)
        return out
    for h in (_normalize_biomart_host(primary),) + _DEFAULT_BIOMART_HOSTS:
        if h and h not in seen:
            seen.add(h)
            out.append(h)
    return out


def fetch_human_mouse_one2one_orthologs(
    human_ensembl_ids: Optional[Sequence[str]] = None,
    mouse_ensembl_ids: Optional[Sequence[str]] = None,
    *,
    biomart_host: str = "www.ensembl.org",
    biomart_hosts: Optional[Sequence[str]] = None,
    human_dataset: str = "hsapiens_gene_ensembl",
    one2one_only: bool = True,
    max_attempts_per_host: int = 3,
    retry_pause_sec: float = 2.0,
) -> pd.DataFrame:
    """
    Query Ensembl BioMart (via ``pybiomart``) for human↔mouse homologs.

    Same ortholog source as ``ortholog_pearson_r2_by_celltype_biomart`` in
    ``e14_fused_gw.ipynb``: human dataset ``hsapiens_gene_ensembl`` with mouse
    homolog columns; optionally keep only ``ortholog_one2one`` rows.

    If ``human_ensembl_ids`` and/or ``mouse_ensembl_ids`` are provided, only rows
    whose human and mouse Ensembl IDs (after version stripping) lie in the
    corresponding sets are kept (client-side filter after the BioMart query).

    BioMart occasionally fails with server-side MySQL errors; this function retries
    and cycles through Ensembl regional mirrors (``biomart_hosts`` or defaults).

    Returns
    -------
    DataFrame with columns including:
        ``human_ensembl_id``, ``mouse_ensembl_id``, ``human_gene_name``,
        ``mouse_gene_name``, ``orthology_type`` (when present).

    Requires
    --------
    ``pip install pybiomart``
    """
    import time

    try:
        from pybiomart import Dataset
    except ModuleNotFoundError as e:
        raise ModuleNotFoundError(
            "pybiomart is required. Install with: pip install pybiomart"
        ) from e

    hosts = _biomart_host_order(biomart_host, biomart_hosts)

    attrs = [
        "ensembl_gene_id",
        "external_gene_name",
        "mmusculus_homolog_ensembl_gene",
        "mmusculus_homolog_associated_gene_name",
        "mmusculus_homolog_orthology_type",
    ]

    n_att = max(1, int(max_attempts_per_host))

    ortho: Optional[pd.DataFrame] = None
    last_err: Optional[BaseException] = None

    for host in hosts:
        for attempt in range(n_att):
            try:
                human = Dataset(name=human_dataset, host=host)
                ortho = human.query(attributes=attrs).copy()
                last_err = None
                break
            except Exception as e:
                # BiomartException (Query ERROR / server DB), timeouts, SSL, etc.
                last_err = e
                if attempt + 1 < n_att:
                    time.sleep(retry_pause_sec)
        if ortho is not None:
            break

    if ortho is None:
        raise RuntimeError(
            "BioMart query failed on all tried hosts "
            f"{hosts!r} ({n_att} attempts each). "
            "Ensembl mart servers sometimes return internal MySQL errors; retry later, "
            "or pass biomart_hosts explicitly. "
            f"Last error: {last_err!r}"
        ) from last_err

    col_map = {
        "ensembl_gene_id": "human_ensembl_id",
        "external_gene_name": "human_gene_name",
        "mmusculus_homolog_ensembl_gene": "mouse_ensembl_id",
        "mmusculus_homolog_associated_gene_name": "mouse_gene_name",
        "mmusculus_homolog_orthology_type": "orthology_type",
        "Gene stable ID": "human_ensembl_id",
        "Gene name": "human_gene_name",
        "Mouse gene stable ID": "mouse_ensembl_id",
        "Mouse gene name": "mouse_gene_name",
        "Mouse homology type": "orthology_type",
    }
    ortho = ortho.rename(columns={c: col_map.get(c, c) for c in ortho.columns})

    if not {"human_ensembl_id", "mouse_ensembl_id"}.issubset(set(ortho.columns)):
        raise RuntimeError(
            f"BioMart query did not return expected columns. Got: {list(ortho.columns)}"
        )

    ortho["human_ensembl_id"] = ortho["human_ensembl_id"].astype(str).map(strip_ensembl_gene_id)
    ortho["mouse_ensembl_id"] = ortho["mouse_ensembl_id"].astype(str).map(strip_ensembl_gene_id)

    ortho = ortho[~ortho["mouse_ensembl_id"].isin(("", "nan", "NaN", "None"))]
    ortho = ortho[ortho["mouse_ensembl_id"].notna()]

    if one2one_only and "orthology_type" in ortho.columns:
        ortho = ortho[ortho["orthology_type"] == "ortholog_one2one"].copy()

    if human_ensembl_ids is not None:
        hs = {strip_ensembl_gene_id(x) for x in human_ensembl_ids}
        ortho = ortho[ortho["human_ensembl_id"].isin(hs)]
    if mouse_ensembl_ids is not None:
        ms = {strip_ensembl_gene_id(x) for x in mouse_ensembl_ids}
        ortho = ortho[ortho["mouse_ensembl_id"].isin(ms)]

    ortho = ortho.drop_duplicates(subset=["human_ensembl_id", "mouse_ensembl_id"]).reset_index(
        drop=True
    )

    return ortho


def subset_matched_adatas_by_ortholog_table(
    adata_mouse: "ad.AnnData",
    adata_human: "ad.AnnData",
    ortho_df: pd.DataFrame,
    *,
    mouse_ensembl_col: Optional[str] = None,
    human_ensembl_col: Optional[str] = None,
) -> Tuple["ad.AnnData", "ad.AnnData", pd.DataFrame]:
    """
    Subset two AnnData objects to rows of ``ortho_df`` that appear in both objects.

    ``ortho_df`` must contain ``human_ensembl_id`` and ``mouse_ensembl_id``.
    Columns are paired in table order; both outputs share ``var_names`` (human
    Ensembl id per column). Copies ``.var`` annotations ``human_ensembl_id`` and
    ``mouse_ensembl_id``.
    """
    required = {"human_ensembl_id", "mouse_ensembl_id"}
    if not required.issubset(ortho_df.columns):
        raise KeyError(f"ortho_df must contain columns {required}; got {list(ortho_df.columns)}")

    def _first_var_index_map(adata: "ad.AnnData", ensembl_col: Optional[str]) -> Dict[str, int]:
        m: Dict[str, int] = {}
        if ensembl_col is None:
            for i, vn in enumerate(adata.var_names):
                eid = strip_ensembl_gene_id(vn)
                if eid not in m:
                    m[eid] = i
        else:
            if ensembl_col not in adata.var.columns:
                raise KeyError(f"'{ensembl_col}' not found in adata.var")
            for i, raw in enumerate(adata.var[ensembl_col].astype(str)):
                eid = strip_ensembl_gene_id(raw)
                if eid not in m:
                    m[eid] = i
        return m

    h_map = _first_var_index_map(adata_human, human_ensembl_col)
    m_map = _first_var_index_map(adata_mouse, mouse_ensembl_col)

    o = ortho_df.copy()
    ok = o["human_ensembl_id"].isin(h_map) & o["mouse_ensembl_id"].isin(m_map)
    o = o.loc[ok].reset_index(drop=True)

    if o.empty:
        raise RuntimeError(
            "No ortholog pairs from ortho_df overlap with var_names (or Ensembl columns) in both AnnData objects."
        )

    h_idx = [h_map[eid] for eid in o["human_ensembl_id"].values]
    m_idx = [m_map[eid] for eid in o["mouse_ensembl_id"].values]

    out_h = adata_human[:, h_idx].copy()
    out_m = adata_mouse[:, m_idx].copy()

    names = pd.Index(o["human_ensembl_id"].astype(str).values)
    out_h.var_names = names
    out_m.var_names = names
    out_h.var["human_ensembl_id"] = o["human_ensembl_id"].astype(str).values
    out_h.var["mouse_ensembl_id"] = o["mouse_ensembl_id"].astype(str).values
    out_m.var["human_ensembl_id"] = o["human_ensembl_id"].astype(str).values
    out_m.var["mouse_ensembl_id"] = o["mouse_ensembl_id"].astype(str).values

    return out_m, out_h, o


def align_adatas_biomart_one2one(
    adata_mouse: "ad.AnnData",
    adata_human: "ad.AnnData",
    *,
    mouse_ensembl_col: Optional[str] = None,
    human_ensembl_col: Optional[str] = None,
    biomart_host: str = "www.ensembl.org",
    biomart_hosts: Optional[Sequence[str]] = None,
    human_dataset: str = "hsapiens_gene_ensembl",
    one2one_only: bool = True,
    max_attempts_per_host: int = 3,
    retry_pause_sec: float = 2.0,
) -> Tuple["ad.AnnData", "ad.AnnData", pd.DataFrame]:
    """
    Fetch BioMart one-to-one human↔mouse orthologs and subset both AnnData objects.

    Convenience wrapper around :func:`fetch_human_mouse_one2one_orthologs` and
    :func:`subset_matched_adatas_by_ortholog_table` using the Ensembl IDs
    present in each object.
    """
    if human_ensembl_col is None:
        human_ids = [strip_ensembl_gene_id(x) for x in adata_human.var_names]
    else:
        human_ids = adata_human.var[human_ensembl_col].astype(str).map(strip_ensembl_gene_id).tolist()

    if mouse_ensembl_col is None:
        mouse_ids = [strip_ensembl_gene_id(x) for x in adata_mouse.var_names]
    else:
        mouse_ids = adata_mouse.var[mouse_ensembl_col].astype(str).map(strip_ensembl_gene_id).tolist()

    ortho = fetch_human_mouse_one2one_orthologs(
        human_ensembl_ids=human_ids,
        mouse_ensembl_ids=mouse_ids,
        biomart_host=biomart_host,
        biomart_hosts=biomart_hosts,
        human_dataset=human_dataset,
        one2one_only=one2one_only,
        max_attempts_per_host=max_attempts_per_host,
        retry_pause_sec=retry_pause_sec,
    )
    return subset_matched_adatas_by_ortholog_table(
        adata_mouse,
        adata_human,
        ortho,
        mouse_ensembl_col=mouse_ensembl_col,
        human_ensembl_col=human_ensembl_col,
    )


def nearest_neighbor_cell_type(adata, label_key: str = "cell_type") -> pd.Series:
    """
    After sc.pp.neighbors(adata), return a pandas Series giving, for each cell,
    the `label_key` of its nearest neighbor (excluding itself).

    Uses adata.obsp['distances'] if present (preferred), otherwise falls back to
    adata.obsp['connectivities'] (chooses the strongest edge).

    Parameters
    ----------
    adata
        AnnData object that already has neighbors computed (sc.pp.neighbors).
    label_key
        Column in adata.obs to read labels from (default: 'cell_type').

    Returns
    -------
    nn_labels
        pd.Series indexed by adata.obs_names with the nearest-neighbor label for each cell.
    """
    if label_key not in adata.obs:
        raise KeyError(f"adata.obs does not contain '{label_key}'.")

    # Prefer distances (true nearest neighbor by smallest distance)
    if "distances" in adata.obsp:
        D = adata.obsp["distances"]
        if not sparse.issparse(D):
            D = sparse.csr_matrix(D)

        D = D.tocsr()
        n = D.shape[0]
        nn_idx = np.empty(n, dtype=int)

        for i in range(n):
            start, end = D.indptr[i], D.indptr[i + 1]
            cols = D.indices[start:end]
            vals = D.data[start:end]

            # Exclude self edge if present
            mask = cols != i
            cols = cols[mask]
            vals = vals[mask]

            if cols.size == 0:
                nn_idx[i] = -1
            else:
                nn_idx[i] = cols[np.argmin(vals)]

        labels = adata.obs[label_key].to_numpy()
        out = np.array([labels[j] if j >= 0 else np.nan for j in nn_idx], dtype=object)
        return pd.Series(out, index=adata.obs_names, name=f"nn_{label_key}")

    raise ValueError(
        "No neighbor graph found. Run sc.pp.neighbors(adata) first "
        "and ensure adata.obsp contains 'distances'."
    )

def nn_gene_r2(adata, num_to_output=20, genes_to_output=None, layer='log1p', obsp_key="distances"):
    D = adata.obsp[obsp_key]
    D = D.tocsr() if sparse.issparse(D) else sparse.csr_matrix(D)

    # nearest neighbor per cell from distances (exclude self / zeros)
    nn = np.full(adata.n_obs, -1, dtype=int)
    for i in range(adata.n_obs):
        s, e = D.indptr[i], D.indptr[i+1]
        idx, dat = D.indices[s:e], D.data[s:e]
        m = (idx != i) & (dat > 0)
        if m.any():
            nn[i] = idx[m][np.argmin(dat[m])]
    keep = nn >= 0
    idx1 = np.where(keep)[0]
    idx2 = nn[keep]

    X = adata.layers[layer] if layer else adata.X
    hv = adata.var.get("highly_variable", np.ones(adata.n_vars, bool)).to_numpy().astype(bool)
    gnames = adata.var_names.to_numpy()

    if genes_to_output is not None:
        genes_to_output = [g for g in genes_to_output if g in adata.var_names]
        hv = hv & np.isin(gnames, genes_to_output)

    cols = np.where(hv)[0]
    if cols.size == 0:
        raise ValueError("No genes selected (check highly_variable or genes_to_output).")

    A = X[idx1, :][:, cols]
    B = X[idx2, :][:, cols]
    A = A.toarray() if hasattr(A, "toarray") else np.asarray(A)
    B = B.toarray() if hasattr(B, "toarray") else np.asarray(B)

    A -= A.mean(0); B -= B.mean(0)
    denom = np.sqrt((A*A).sum(0) * (B*B).sum(0)) + 1e-12
    r2 = ((A*B).sum(0) / denom) ** 2

    order = np.argsort(-r2) if genes_to_output is not None else np.argsort(-r2)[:min(num_to_output, r2.size)]
    for j in order:
        print(f"{gnames[cols[j]]}\tR^2={r2[j]:.4f}")


def plot_ot_transport_by_celltype(
    transport,
    src_cell_types,
    tgt_cell_types,
    cmap="viridis",
    vmax=None,
    vmin=None,
    figsize=(8, 6),
):
    """
    Plot an OT transport plan heatmap grouped by cell type blocks.

    Parameters
    ----------
    transport : array-like (n_src, n_tgt)
        OT transport plan.
    src_cell_types : sequence of length n_src
        Cell-type labels for source cells.
    tgt_cell_types : sequence of length n_tgt
        Cell-type labels for target cells.
    """

    T = np.asarray(transport)

    src_ct = pd.Series(src_cell_types)
    tgt_ct = pd.Series(tgt_cell_types)

    # order cells by cell type (preserve first-seen order)
    src_order = src_ct.groupby(src_ct).indices
    tgt_order = tgt_ct.groupby(tgt_ct).indices

    src_idx = np.concatenate(list(src_order.values()))
    tgt_idx = np.concatenate(list(tgt_order.values()))

    M = T[np.ix_(src_idx, tgt_idx)]
    print(M)

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(M, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)
    plt.colorbar(im, ax=ax)

    # draw block boundaries
    for y in np.cumsum([len(v) for v in src_order.values()])[:-1]:
        ax.axhline(y - 0.5, color="white", lw=1)
    for x in np.cumsum([len(v) for v in tgt_order.values()])[:-1]:
        ax.axvline(x - 0.5, color="white", lw=1)

    # label blocks at centers
    ax.set_yticks(
        np.cumsum([0] + [len(v) for v in src_order.values()])[:-1]
        + np.array([len(v) for v in src_order.values()]) / 2
    )
    ax.set_yticklabels(list(src_order.keys()))

    ax.set_xticks(
        np.cumsum([0] + [len(v) for v in tgt_order.values()])[:-1]
        + np.array([len(v) for v in tgt_order.values()]) / 2
    )
    ax.set_xticklabels(list(tgt_order.keys()), rotation=90)

    ax.set_xlabel("target cells")
    ax.set_ylabel("source cells")
    ax.set_title("OT transport plan grouped by cell type")

    plt.tight_layout()
    return fig, ax


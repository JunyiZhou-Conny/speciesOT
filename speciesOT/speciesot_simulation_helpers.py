import numpy as np
import pandas as pd
import scanpy as sc
import anndata as ad
import scipy as sp
import matplotlib.pylab as pl
import matplotlib.pyplot as plt
import ot
from sklearn.neighbors import NearestNeighbors
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import minimum_spanning_tree, dijkstra
from sklearn.decomposition import PCA
from scipy.stats import gaussian_kde
from matplotlib.lines import Line2D
import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import pairwise_distances



def generate_point_clouds(N, P, M, A=1.0, B=1.0, seed=None, eps=1e-6):
    """
    N clouds, each with P points in M dims.
    Means ~ U[-1,1] * A
    Covariances are full SPD matrices scaled by B.
    
    Returns:
      clouds: (N, P, M)
      means:  (N, M)
      covs:   (N, M, M)
    """
    rng = np.random.default_rng(seed)

    means = A * 2*(rng.random((N, M))-0.5)        # (N,M)

    covs = np.empty((N, M, M))
    clouds = np.empty((N, P, M))

    for i in range(N):
        R = rng.standard_normal((M, M))
        cov = (R @ R.T) / M                         # SPD-ish
        cov = B * cov + eps * np.eye(M)             # scale + stabilize
        covs[i] = cov

        L = np.linalg.cholesky(cov)                 # cov = L L^T
        Z = rng.standard_normal((P, M))             # (P,M)
        clouds[i] = means[i] + Z @ L.T              # (P,M)

    return clouds, means, covs


def plot_first_two_dims(
    clouds,
    sublabels=None,                  # (N,P) or (N*P,)
    alpha=0.6,
    s=10,
    annotate=False,
    text_offset=(0.01, 0.01),
    pca=False
):
    """
    Color = population (cloud index).
    Marker shape = subpopulation label (from sublabels).

    clouds: (N, P, M)
    sublabels: optional subclass labels per point (N,P) or flattened (N*P,)
    """
    N, P, M = clouds.shape
    global_idx = 0

    # coords to plot
    if pca:
        X_all = clouds.reshape(-1, M)
        XY = PCA(n_components=2).fit_transform(X_all).reshape(N, P, 2)
    else:
        XY = clouds[:, :, :2]

    # sublabels handling
    if sublabels is None:
        sub = np.zeros((N, P), dtype=int)
    else:
        sub = np.asarray(sublabels)
        sub = sub.reshape(N, P) if sub.size == N * P else sub
        if sub.shape != (N, P):
            raise ValueError("sublabels must be shape (N,P) or flattened length N*P")

    # marker mapping for subpops
    markers = ['o', 's', '^', 'D', 'v', 'P', 'X', '*', '<', '>', 'h', '+', 'x', '1', '2', '3', '4']
    uniq_sub = np.unique(sub)
    marker_map = {lab: markers[i % len(markers)] for i, lab in enumerate(uniq_sub)}

    # fixed colors for populations from matplotlib's cycle
    cmap = plt.get_cmap("tab10")

    for pop in range(N):
        color = cmap(pop % 10)
        x = XY[pop, :, 0]
        y = XY[pop, :, 1]

        # plot each subpopulation with a different marker, same color (population)
        for lab in np.unique(sub[pop]):
            m = (sub[pop] == lab)
            plt.scatter(x[m], y[m], s=s, alpha=alpha, marker=marker_map[lab], color=color)

            if annotate:
                dx, dy = text_offset
                for xi, yi in zip(x[m], y[m]):
                    plt.text(xi + dx, yi + dy, str(global_idx), fontsize=8, alpha=alpha, color=color)
                    global_idx += 1

        if not annotate:
            global_idx += P

    plt.xlabel("PC 1" if pca else "Dimension 1")
    plt.ylabel("PC 2" if pca else "Dimension 2")
    plt.axis("equal")
    plt.tight_layout()
    plt.show()




def resample_point_clouds(means, covs, P, seed=None):
    """
    means: (N, M)
    covs:  (N, M, M)
    P:     number of points per cloud

    Returns:
      clouds: (N, P, M)
    """
    rng = np.random.default_rng(seed)

    N, M = means.shape
    clouds = np.empty((N, P, M))

    for i in range(N):
        L = np.linalg.cholesky(covs[i])      # cov = L L^T
        Z = rng.standard_normal((P, M))
        clouds[i] = means[i] + Z @ L.T

    return clouds


def flatten_clouds(clouds):
    """
    clouds: (N, P, M)

    Returns:
      X: (N*P, M) numpy array of all points
      labels: pandas Series of length N*P indicating cloud index
    """
    N, P, _ = clouds.shape

    X = clouds.reshape(N * P, -1)
    labels = pd.Series(np.repeat(np.arange(N), P), name="cloud_id")

    return X, labels


def knn_geodesic_distance_matrix(X, k=3, metric="euclidean", eps=1e-12, visualize=False):
    """
    Build a graph that is the union of:
      - the Minimum Spanning Tree (on the full pairwise distance graph), and
      - the kNN graph (directed->undirected)
    Then compute all-pairs shortest-path (geodesic) distances with Dijkstra,
    fill disconnected pairs (shouldn't exist) with the maximum finite distance,
    and normalize so outputs lie in [0, 1] (diag is 0).

    X: (N, M) array
    Returns:
      D_norm: (N, N) normalized geodesic distance matrix
    """
    X = np.asarray(X)
    N = X.shape[0]
    if N == 0:
        return np.empty((0, 0))
    if N == 1:
        return np.zeros((1, 1))

    k = min(int(k), N - 1)

    # 1) kNN graph (exclude self)
    nn = NearestNeighbors(n_neighbors=k + 1, metric=metric).fit(X)
    dists_knn, inds_knn = nn.kneighbors(X, return_distance=True)
    dists_knn, inds_knn = dists_knn[:, 1:], inds_knn[:, 1:]  # drop self

    row = np.repeat(np.arange(N), k)
    col = inds_knn.reshape(-1)
    data = dists_knn.reshape(-1)
    A_knn = csr_matrix((data, (row, col)), shape=(N, N))
    # make undirected: union (take min or max? distances symmetric so we take minimum of both directed weights)
    G_knn = A_knn.minimum(A_knn.T)
    # if minimum gives zeros for missing edges, use maximum to preserve distances both ways:
    G_knn = G_knn.maximum(G_knn.T)

    if visualize:
        edges_knn = list(zip(row.tolist(), col.tolist(), data.tolist()))
        try:
            plot_knn_graph(X, edges_knn)
        except Exception:
            pass

    # 2) Minimum Spanning Tree on full pairwise distances
    # compute full pairwise distance matrix (dense). This is O(N^2) memory.
    D_full = pairwise_distances(X, metric=metric)  # shape (N, N)
    # build sparse full graph (we can use the dense distances directly as weights)
    full_sparse = csr_matrix(D_full)
    mst = minimum_spanning_tree(full_sparse)  # returns a sparse upper-triangular MST
    # make MST undirected (symmetric) by adding transpose
    mst_undirected = mst + mst.T

    if visualize:
        mst_coo = mst_undirected.tocoo()
        edges_mst = list(zip(mst_coo.row.tolist(), mst_coo.col.tolist(), mst_coo.data.tolist()))
        try:
            plot_knn_graph(X, edges_mst)
        except Exception:
            pass

    # 3) union MST and kNN: take minimum edge weight when both exist
    # (we want shortest-path semantics; using minimum is sensible)
    G_union = mst_undirected.copy().tolil()
    # add kNN edges, keeping the smaller weight if an edge already exists
    knn_coo = G_knn.tocoo()
    for i, j, w in zip(knn_coo.row, knn_coo.col, knn_coo.data):
        # if there's already an MST edge weight, keep min(mst_weight, knn_weight)
        prev = G_union[i, j]
        if prev == 0:
            G_union[i, j] = w
        else:
            # prev may be a matrix scalar type; convert to float
            prev_w = float(prev)
            G_union[i, j] = min(prev_w, float(w))

    # ensure symmetry
    G_union = G_union.tocsr()
    G_union = G_union.maximum(G_union.T)

    # optional visualize combined graph
    if visualize:
        u_coo = G_union.tocoo()
        edges_union = list(zip(u_coo.row.tolist(), u_coo.col.tolist(), u_coo.data.tolist()))
        try:
            plot_knn_graph(X, edges_union)
        except Exception:
            pass

    # 4) All-pairs shortest paths (geodesic distances)
    D = dijkstra(G_union, directed=False)

    # 5) Fill disconnected pairs (shouldn't happen because MST connects all), normalize
    finite = np.isfinite(D)
    if not finite.any():
        return np.zeros_like(D)

    max_finite = D[finite].max()
    if max_finite <= eps:
        return np.zeros_like(D)

    D_filled = np.where(finite, D, max_finite)
    D_norm = D_filled / max_finite
    return D_norm


def run_ot(xs, xt, n_samples, epsilon=0.1, distance_method="euclidean", knn_k = 3, visualize=False):
    if distance_method == "geodesic":
        C1 = knn_geodesic_distance_matrix(xs, k=knn_k, visualize=visualize)
        C2 = knn_geodesic_distance_matrix(xt, k=knn_k, visualize=visualize)
    else:
        C1 = sp.spatial.distance.cdist(xs, xs)
        C2 = sp.spatial.distance.cdist(xt, xt)

    C1 /= C1.max()
    C2 /= C2.max()

    p = ot.unif(n_samples)
    q = ot.unif(n_samples)

    # Proximal Point algorithm with Kullback-Leibler as proximal operator
    gw, log = ot.gromov.entropic_gromov_wasserstein(
    C1, C2, p, q, "square_loss", epsilon=epsilon, solver="PPA", log=True)
    
    return gw


def compute_mapping_acc(transport_plan, source_labels, target_true_labels):
    """
    transport_plan: (n_source, n_target)
    source_labels: (n_source,) array-like (numpy or pandas Series)
    target_true_labels: (n_target,) array-like (numpy or pandas Series)
    """
    T = np.asarray(transport_plan)
    src = np.asarray(source_labels)          # drops pandas index
    tgt = np.asarray(target_true_labels)     # drops pandas index

    target_pred_idx = np.argmax(T, axis=1)   # length n_source
    pred_target_labels = tgt[target_pred_idx]

    return float(np.mean(src == pred_target_labels))


def plot_knn_graph(X, edges, node_size=40, edge_alpha=0.4):
    """
    Visualize a kNN graph.

    X:     (N, M) points
    edges: list of (i, j, w) edges (indices and weight)
    """
    X = np.asarray(X)

    plt.figure(figsize=(6, 6))

    # Plot edges
    for i, j, w in edges:
        plt.plot(
            [X[i, 0], X[j, 0]],
            [X[i, 1], X[j, 1]],
            color="gray",
            alpha=edge_alpha,
            linewidth=1
        )

    # Plot nodes
    plt.scatter(X[:, 0], X[:, 1], s=node_size, c="black")

    plt.title("kNN Graph (geodesic distances)")
    plt.axis("equal")
    plt.tight_layout()
    plt.show()
    

def plot_got_best_matches_with_labels(
    X_source,
    X_target,
    coupling,
    labels1,
    labels2,
    *,
    dims=(0, 1),
    source_label="Source",
    target_label="Target",
    cmap="tab10",
    ax=None,
    title="GOT argmax matches with class consistency",
    show_legend=True,
):
    """
    Plot best target match for each source point using a Gromov OT coupling,
    coloring points by class labels and edges by class agreement.

    - Points are colored according to their class labels.
    - Edges are black if source and target classes match, red otherwise.

    Parameters
    ----------
    X_source : (n_source, d) array
    X_target : (n_target, d) array
    coupling : (n_source, n_target) array
    labels1 : array-like, length n_source
        Class labels for source points.
    labels2 : array-like, length n_target
        Class labels for target points.
    dims : tuple(int, int)
        Dimensions to plot (default: (0, 1)).
    cmap : str or Colormap
        Matplotlib colormap for classes.
    ax : matplotlib.axes.Axes or None
    title : str
    show_legend : bool

    Returns
    -------
    fig, ax
    """
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    Xs = np.asarray(X_source)
    Xt = np.asarray(X_target)
    C = np.asarray(coupling)
    labels1 = np.asarray(labels1)
    labels2 = np.asarray(labels2)

    if C.shape != (Xs.shape[0], Xt.shape[0]):
        raise ValueError("Coupling shape must be (n_source, n_target).")

    d0, d1 = dims
    if max(d0, d1) >= Xs.shape[1] or max(d0, d1) >= Xt.shape[1]:
        raise ValueError("Requested plot dimensions exceed data dimensionality.")

    # Row-wise argmax
    best_j = np.argmax(C, axis=1)

    # Build a shared label -> color mapping
    all_labels = np.unique(np.concatenate([labels1, labels2]))
    label_to_idx = {lab: i for i, lab in enumerate(all_labels)}
    label_idx1 = np.vectorize(label_to_idx.get)(labels1)
    label_idx2 = np.vectorize(label_to_idx.get)(labels2)

    cmap = plt.get_cmap(cmap, len(all_labels))

    if ax is None:
        fig, ax = plt.subplots(figsize=(7, 6))
    else:
        fig = ax.figure

    # Scatter plots
    ax.scatter(
        Xs[:, d0],
        Xs[:, d1],
        c=label_idx1,
        cmap=cmap,
        marker="o",
        s=35,
        edgecolors="black",
        linewidths=0.7,
        alpha=0.9,
        label=source_label,
    )

    ax.scatter(
        Xt[:, d0],
        Xt[:, d1],
        c=label_idx2,
        cmap=cmap,
        marker="^",
        s=45,
        edgecolors="black",
        linewidths=0.7,
        alpha=0.9,
        label=target_label,
    )

    # Draw edges
    for i in range(Xs.shape[0]):
        j = best_j[i]
        same_class = labels1[i] == labels2[j]
        edge_color = "black" if same_class else "red"

        ax.plot(
            [Xs[i, d0], Xt[j, d0]],
            [Xs[i, d1], Xt[j, d1]],
            color=edge_color,
            linewidth=1.0,
            alpha=0.5,
            zorder=0,
        )

    ax.set_xlabel(f"dim {d0}")
    ax.set_ylabel(f"dim {d1}")
    ax.set_title(title)
    ax.axis("equal")

    if show_legend:
        legend_elements = [
            Line2D([0], [0], marker="o", color="w",
                   markerfacecolor="gray", markeredgecolor="black",
                   markersize=7, label=source_label),
            Line2D([0], [0], marker="^", color="w",
                   markerfacecolor="gray", markeredgecolor="black",
                   markersize=8, label=target_label),
            Line2D([0], [0], color="black", lw=1.5, label="Same class"),
            Line2D([0], [0], color="red", lw=1.5, label="Different class"),
        ]
        ax.legend(handles=legend_elements, frameon=True)

    # Minimal change: only return fig, ax (no arrays printed in notebooks)
    return fig, ax



def make_seeded_G0(p, q, src_anchors, tgt_anchors, boost=50.0, n_ipfp=200, eps=1e-12):
    """
    Build an initial coupling G0 with the right marginals (p,q) but biased toward anchor pairs.
    boost: multiplicative factor for anchor entries (bigger => stronger seeding)
    """
    p = np.ones(n1) / n1 if p is None else np.asarray(p, float).ravel()
    q = np.ones(n2) / n2 if q is None else np.asarray(q, float).ravel()
    G0 = np.outer(p, q)  # feasible start

    # multiplicatively boost anchor entries
    for i, j in zip(src_anchors, tgt_anchors):
        G0[i, j] *= boost

    # IPFP / matrix scaling to enforce row sums = p and col sums = q
    # (keeps positivity and preserves anchor bias)
    for _ in range(n_ipfp):
        G0 *= (p / (G0.sum(axis=1) + eps))[:, None]
        G0 *= (q / (G0.sum(axis=0) + eps))[None, :]

    return G0

def gw_seeded(xs, xt, n_samples, src_anchors, tgt_anchors, alpha=0.2,
                      p=None, q=None, boost=50.0, n_ipfp=200, epsilon=0.1, knn_k=3, visualize=False,
                      distance_method="euclidean", **fgw_kwargs):
    """
    Runs FGW with a seeded initialization coupling (G0) in POT v0.9.5.
    M: (n1,n2) feature cost matrix

    """
    if distance_method == "geodesic":
        C1 = knn_geodesic_distance_matrix(xs, k=knn_k, visualize=visualize)
        C2 = knn_geodesic_distance_matrix(xt, k=knn_k, visualize=visualize)
    else:
        C1 = sp.spatial.distance.cdist(xs, xs)
        C2 = sp.spatial.distance.cdist(xt, xt)

    C1 /= C1.max()
    C2 /= C2.max()
    
    n1, n2 = C1.shape[0], C2.shape[0]
    p = np.ones(n1) / n1 if p is None else np.asarray(p, float).ravel()
    q = np.ones(n2) / n2 if q is None else np.asarray(q, float).ravel()

    G0 = make_seeded_G0(p, q, src_anchors, tgt_anchors, boost=boost, n_ipfp=n_ipfp)

    # Proximal Point algorithm with Kullback-Leibler as proximal operator
    pi, _ = ot.gromov.entropic_gromov_wasserstein(
        C1, C2, p, q, "square_loss", G0=G0, epsilon=epsilon, solver="PPA", log=True)
    
    return pi

def plot_side_by_side_accs(seeded_accs, unseeded_accs, jitter=0.08):
    x0, x1 = 0, 1

    plt.figure(figsize=(4, 4))

    # transparent mean bars
    plt.bar(
        x1, np.mean(seeded_accs),
        width=0.4, alpha=0.25
    )
    plt.bar(
        x0, np.mean(unseeded_accs),
        width=0.4, alpha=0.25
    )

    # jittered points
    plt.scatter(
        x1 + jitter * np.random.randn(len(seeded_accs)),
        seeded_accs,
        alpha=0.7,
        s=40,
        color="gray"
    )
    plt.scatter(
        x0 + jitter * np.random.randn(len(unseeded_accs)),
        unseeded_accs,
        alpha=0.7,
        s=40,
        color="gray"
    )

    plt.xticks([x0, x1], ["Unanchored", "Anchored"])
    plt.ylabel("Accuracy")
    plt.ylim(0, 1.1)
    plt.xlim(-0.5, 1.5)
    plt.tight_layout()
    plt.title('Accuracy improves with initialization anchor')
    plt.show()

    
def generate_point_clouds_subpops(
    N, P, M, A=1.0, B=1.0, seed=None, eps=1e-6,
    P_disc=0, SP=1, disc_pops=None, discriminative_strength=4.0,
    noise_dims=None
):
    """
    Generate N Gaussian point clouds (N, P, M) with optional subpopulations
    and optional "noise dimensions" that are shared (same mean & variance)
    across all populations.

    Parameters (new/important):
    - noise_dims: None (default), an integer (count) or an iterable of indices.
        * If int > 0: select that many noise dims from the first dims after P_disc.
        * If iterable: used as indices directly (will be sanitized).
        For each noise-dimension we choose one shared mean and one shared variance,
        and force all populations to have that mean & variance (and zero cross-covariances)
        on those dimensions.

    Returns:
      clouds:        (N, P, M)
      means:         (N, M)
      covs:          (N, M, M)
      pop_labels:    (N, P)
      subpop_labels: (N, P)
      disc_dims:     (P_disc,)
      disc_pops:     sorted np.ndarray of discriminative population indices
      noise_dims:    sorted np.ndarray of noise dimension indices (possibly empty)
      shared_noise_means: (len(noise_dims),) array of chosen shared means
      shared_noise_vars:  (len(noise_dims),) array of chosen shared variances (not std)
    """
    rng = np.random.default_rng(seed)

    # sanitize basic inputs
    N = int(N); P = int(P); M = int(M)
    P_disc = int(min(max(P_disc, 0), M))
    SP = int(max(SP, 1))
    discriminative_strength = float(discriminative_strength)

    disc_dims = np.arange(P_disc)

    # disc_pops sanitization
    if disc_pops is None:
        disc_pops = np.arange(N, dtype=int)
    else:
        disc_pops = np.asarray(disc_pops, dtype=int)
        disc_pops = disc_pops[(disc_pops >= 0) & (disc_pops < N)]
        disc_pops = np.unique(disc_pops)
    disc_pops = np.sort(disc_pops)
    disc_pops_set = set(disc_pops.tolist())

    # ---------- noise_dims handling ----------
    # normalize noise_dims input into an array of indices (possibly empty)
    if noise_dims is None:
        noise_dims_idx = np.array([], dtype=int)
    elif isinstance(noise_dims, (int, np.integer)):
        n_noise = int(noise_dims)
        if n_noise <= 0:
            noise_dims_idx = np.array([], dtype=int)
        else:
            # pick the first n_noise dims after P_disc (but within M)
            start = P_disc
            available = np.arange(start, M)
            if n_noise > available.size:
                raise ValueError("Requested more noise_dims than available dimensions")
            noise_dims_idx = np.array(available[:n_noise], dtype=int)
    else:
        # treat as iterable of indices
        noise_dims_idx = np.unique(np.asarray(list(noise_dims), dtype=int))
        # sanitize range
        noise_dims_idx = noise_dims_idx[(noise_dims_idx >= 0) & (noise_dims_idx < M)]
        # also avoid overlapping with discriminative dims (disc_dims = 0..P_disc-1)
        # (But if user explicitly specified overlap, we'll still remove duplicates)
        noise_dims_idx = noise_dims_idx[~np.isin(noise_dims_idx, disc_dims)]

    noise_dims_idx = np.sort(noise_dims_idx)
    n_noise = noise_dims_idx.size

    # ---------- sample shared noise means & variances ----------
    # If there are noise dims, choose a single shared mean (Uniform[-A,A]) and
    # a single shared variance for each noise dim. We'll obtain variances by
    # creating one random SPD matrix (same procedure used for pop covs) and use
    # its diagonal elements for the noise dims (times B and plus eps).
    if n_noise > 0:
        # shared means for noise dims
        shared_noise_means = A * 2.0 * (rng.random(n_noise) - 0.5)

        # create one random SPD to get realistic per-dim variances
        R_tmp = rng.standard_normal((M, M))
        cov_tmp = (R_tmp @ R_tmp.T) / max(1, M)
        cov_tmp = B * cov_tmp + eps * np.eye(M)
        shared_noise_vars = np.maximum(np.diag(cov_tmp)[noise_dims_idx], eps)
    else:
        shared_noise_means = np.array([], dtype=float)
        shared_noise_vars = np.array([], dtype=float)

    # ---------- prepare base means & covs ----------
    means = A * 2.0 * (rng.random((N, M)) - 0.5)

    covs = np.empty((N, M, M))
    clouds = np.empty((N, P, M))

    pop_labels = np.repeat(np.arange(N)[:, None], P, axis=1)
    subpop_labels = np.zeros((N, P), dtype=int)

    # first non-discriminative population reference (for signed bias)
    non_disc = [j for j in range(N) if j not in disc_pops_set]
    ref_pop = non_disc[0] if non_disc else None
    # bias dimension: first non-discriminative dimension (if exists)
    bias_dim = P_disc if P_disc < M else None

    disc_pops_set = set(disc_pops.tolist())

    for i in range(N):
        # create random SPD covariance for this population
        R = rng.standard_normal((M, M))
        cov = (R @ R.T) / max(1, M)
        cov = B * cov + eps * np.eye(M)

        # overwrite noise-dim covariances so noise dims are independent and share the same variance
        if n_noise > 0:
            # zero out cross-covariances involving noise dims
            for d in noise_dims_idx:
                cov[d, :] = 0.0
                cov[:, d] = 0.0
                cov[d, d] = shared_noise_vars[np.where(noise_dims_idx == d)[0][0]]

        covs[i] = cov

        # ensure means for noise dims are shared
        if n_noise > 0:
            means[i, noise_dims_idx] = shared_noise_means

        # sample baseline points with this mean/cov
        L = np.linalg.cholesky(cov)
        Z = rng.standard_normal((P, M))
        base = means[i] + Z @ L.T

        # apply subpopulation structure to discriminative populations
        if (P_disc > 0) and (SP > 1) and (i in disc_pops_set):
            sub = (np.arange(P) % SP) + 1
            rng.shuffle(sub)
            subpop_labels[i] = sub

            std = np.sqrt(np.diag(cov))
            centers = (sub - (SP + 1) / 2.0)

            offsets = np.zeros((P, M))
            offsets[:, disc_dims] = centers[:, None] * (discriminative_strength * std[disc_dims])[None, :]

            # signed adjustment so sub==1 moves toward ref_pop along bias_dim
            if (ref_pop is not None) and (bias_dim is not None):
                delta = means[ref_pop, bias_dim] - means[i, bias_dim]
                sign = 1.0 if delta >= 0 else -1.0
                offsets[sub == 1, bias_dim] += sign * discriminative_strength * std[bias_dim]

            clouds[i] = base + offsets
        else:
            clouds[i] = base

    return (clouds, means, covs, pop_labels, subpop_labels)


def resample_point_clouds_subpops(
    means, covs, P, seed=None,
    P_disc=0, SP=1, disc_pops=None,
    discriminative_strength=4,
    noise_dims=None,
    shared_noise_means=None,
    shared_noise_vars=None
):
    """
    Resample clouds from stored means/covs, optionally re-imposing subpopulations,
    and optionally enforcing "noise dimensions" so those dims have the same mean
    and variance across all populations.

    New parameters:
    - noise_dims: None, int, or iterable of indices (same semantics as in generator).
    - shared_noise_means: optional array of length n_noise to force exact shared mean.
      If None and noise_dims is provided, we will derive shared means from `means` by averaging across populations.
    - shared_noise_vars: optional array of length n_noise to force exact shared variance.
      If None and noise_dims is provided, we will derive shared variances from `covs` by averaging the diag variances across populations.

    Returns:
      clouds: (N, P, M)
      pop_labels, subpop_labels
    """
    rng = np.random.default_rng(seed)

    means = np.asarray(means, float)
    covs = np.asarray(covs, float)

    N, M = means.shape
    if N == 0:
        return np.empty((0, 0, M)), np.empty((0, 0), dtype=int), np.empty((0, 0), dtype=int)

    # sanitize inputs
    P_disc = int(min(max(int(P_disc), 0), M))
    SP = int(max(int(SP), 1))
    discriminative_strength = float(discriminative_strength)
    disc_dims = np.arange(P_disc)

    # disc_pops sanitization
    if disc_pops is None:
        disc_pops = np.arange(N, dtype=int)
    else:
        disc_pops = np.unique(np.asarray(disc_pops, dtype=int))
        disc_pops = disc_pops[(disc_pops >= 0) & (disc_pops < N)]
    disc_pops = np.sort(disc_pops)
    disc_set = set(disc_pops.tolist())

    # ---------- noise_dims handling (same logic as generator) ----------
    if noise_dims is None:
        noise_dims_idx = np.array([], dtype=int)
    elif isinstance(noise_dims, (int, np.integer)):
        n_noise = int(noise_dims)
        if n_noise <= 0:
            noise_dims_idx = np.array([], dtype=int)
        else:
            start = P_disc
            available = np.arange(start, M)
            if n_noise > available.size:
                raise ValueError("Requested more noise_dims than available dimensions")
            noise_dims_idx = np.array(available[:n_noise], dtype=int)
    else:
        noise_dims_idx = np.unique(np.asarray(list(noise_dims), dtype=int))
        noise_dims_idx = noise_dims_idx[(noise_dims_idx >= 0) & (noise_dims_idx < M)]
        noise_dims_idx = noise_dims_idx[~np.isin(noise_dims_idx, disc_dims)]
    noise_dims_idx = np.sort(noise_dims_idx)
    n_noise = noise_dims_idx.size

    # if noise dims present and shared means/vars not provided, derive them
    if n_noise > 0:
        if shared_noise_means is None:
            # derive a shared mean by averaging the per-population means
            shared_noise_means = means[:, noise_dims_idx].mean(axis=0)
        else:
            shared_noise_means = np.asarray(shared_noise_means, float)
            if shared_noise_means.shape[0] != n_noise:
                raise ValueError("shared_noise_means length mismatch with noise_dims")

        if shared_noise_vars is None:
            # derive shared variance by averaging diagonal variances across populations
            per_pop_vars = np.asarray([np.diag(cov)[noise_dims_idx] for cov in covs])
            shared_noise_vars = per_pop_vars.mean(axis=0)
        else:
            shared_noise_vars = np.asarray(shared_noise_vars, float)
            if shared_noise_vars.shape[0] != n_noise:
                raise ValueError("shared_noise_vars length mismatch with noise_dims")
    else:
        shared_noise_means = np.array([], dtype=float)
        shared_noise_vars = np.array([], dtype=float)

    # apply the shared noise constraints to the given means/covs (in a copy, don't mutate inputs)
    means_c = means.copy()
    covs_c = covs.copy()
    if n_noise > 0:
        for d_idx, d in enumerate(noise_dims_idx):
            means_c[:, d] = shared_noise_means[d_idx]
            # zero cross-covariances and set diag to shared var
            for i in range(N):
                covs_c[i, d, :] = 0.0
                covs_c[i, :, d] = 0.0
                covs_c[i, d, d] = max(shared_noise_vars[d_idx], 1e-12)

    # now we can resample as before but using means_c and covs_c
    clouds = np.empty((N, P, M))
    pop_labels = np.repeat(np.arange(N)[:, None], P, axis=1)
    subpop_labels = np.zeros((N, P), dtype=int)

    # reference population and bias dim, for signed bias
    non_disc = [j for j in range(N) if j not in disc_set]
    ref_pop = non_disc[0] if non_disc else None
    bias_dim = P_disc if P_disc < M else None

    use_subpops = (P_disc > 0) and (SP > 1)

    for i in range(N):
        L = np.linalg.cholesky(covs_c[i])
        Z = rng.standard_normal((P, M))
        base = means_c[i] + Z @ L.T

        if use_subpops and (i in disc_set):
            sub = (np.arange(P) % SP) + 1
            rng.shuffle(sub)
            subpop_labels[i] = sub

            std = np.sqrt(np.diag(covs_c[i]))
            centers = (sub - (SP + 1) / 2.0)
            offsets = np.zeros((P, M))
            offsets[:, disc_dims] = centers[:, None] * (discriminative_strength * std[disc_dims])[None, :]

            if (ref_pop is not None) and (bias_dim is not None):
                delta = means_c[ref_pop, bias_dim] - means_c[i, bias_dim]
                sign = 1.0 if delta >= 0 else -1.0
                offsets[sub == 1, bias_dim] += sign * discriminative_strength * std[bias_dim]

            clouds[i] = base + offsets
        else:
            clouds[i] = base

    return clouds, pop_labels, subpop_labels


def sublabel_match_rate_from_gw(gw, labels1, labels2, sublabels1, sublabels2):
    T = np.asarray(gw)
    if T.ndim != 2:
        raise ValueError(f"gw must be 2D, got shape {T.shape}")

    n_source, n_target = T.shape

    # Flatten labels/sublabels to 1D (handles inputs shaped (N,P))
    s1 = np.asarray(sublabels1).ravel()
    s2 = np.asarray(sublabels2).ravel()

    if len(s1) != n_source:
        raise ValueError(f"sublabels1 length {len(s1)} != gw n_source {n_source}")
    if len(s2) != n_target:
        raise ValueError(f"sublabels2 length {len(s2)} != gw n_target {n_target}")

    # argmax target index per source
    j_hat = np.argmax(T, axis=1)  # (n_source,)

    # score only source points with non-zero sublabels
    mask = (s1 != 0)
    n_eval = int(mask.sum())
    if n_eval == 0:
        return 0.0, 0

    j_sel = j_hat[mask]
    correct = (s1[mask] == s2[j_sel]) & (s2[j_sel] != 0)

    return float(np.mean(correct))

def plot_mean_std(df, x="cloud size", y="accuracy"):
    stats = df.groupby(x)[y].agg(["mean", "std"]).reset_index()

    plt.plot(stats[x], stats["mean"], marker="o")
    plt.fill_between(
        stats[x],
        stats["mean"] - stats["std"],
        stats["mean"] + stats["std"],
        alpha=0.3
    )

    #plt.xlabel(x)
    #plt.ylabel(y)
    plt.tight_layout()
    plt.show()
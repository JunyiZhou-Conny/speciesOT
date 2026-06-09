import numpy as np
from sklearn.metrics.pairwise import rbf_kernel


def mmd_distance(x, y, gamma):
    xx = rbf_kernel(x, x, gamma)
    xy = rbf_kernel(x, y, gamma)
    yy = rbf_kernel(y, y, gamma)

    return xx.mean() + yy.mean() - 2 * xy.mean()


def compute_mmd_two_sample(
    A,
    B=None,
    ncells_list=(30, 50, 80),
    gammas=None,
    n_reps=10,
    random_state=0,
    split_half=False,
):
    """Subsampled MMD between two cell clouds at matched sample sizes.

    The eval (``scripts/evaluate.py``) computes MMD on size-``ncells`` subsamples,
    averaged over reps, with ``gammas = np.logspace(1, -3, num=50)``. Mirror those
    so the result is directly comparable. This one routine powers the three
    quantities in the floor/ceiling framework:

      - model MMD : ``compute_mmd_two_sample(imputed, treated)``
      - ceiling   : ``compute_mmd_two_sample(control, treated)`` -- the cross-species
                    / identity-baseline gap a no-op (predict-source-as-target) model
                    would incur; the worst MMD a sensible model should beat.
      - floor     : ``compute_mmd_two_sample(treated, split_half=True)`` -- the
                    irreducible self-MMD of the target (see ``compute_mmd_floor``).

    Parameters
    ----------
    A, B : array-like, shape (n_cells, n_features)
        The two clouds. With ``split_half=True`` only ``A`` is used.
    split_half : bool
        If True, draw two disjoint size-``ncells`` subsamples from ``A`` alone (the
        self-MMD floor). If False, draw independent subsamples from ``A`` and ``B``.

    Returns
    -------
    pandas.DataFrame
        Long-form rows ``[ncells, rep, mmd]``.
    """
    import pandas as pd

    if gammas is None:
        gammas = np.logspace(1, -3, num=50)
    gammas = np.asarray(list(gammas))

    A = np.asarray(A)
    rng = np.random.default_rng(random_state)

    rows = []
    if split_half:
        n = len(A)
        all_idx = np.arange(n)
        for ncells in ncells_list:
            ncells = int(ncells)
            if ncells > n:
                continue
            for rep in range(n_reps):
                idx_a = rng.choice(n, size=ncells, replace=False)
                remaining = np.setdiff1d(all_idx, idx_a, assume_unique=False)
                # disjoint halves when the pool allows; else fall back (may overlap)
                if len(remaining) >= ncells:
                    idx_b = rng.choice(remaining, size=ncells, replace=False)
                else:
                    idx_b = rng.choice(n, size=ncells, replace=False)
                mmd = float(np.mean([mmd_distance(A[idx_a], A[idx_b], g) for g in gammas]))
                rows.append((ncells, rep, mmd))
    else:
        if B is None:
            raise ValueError("B is required unless split_half=True")
        B = np.asarray(B)
        nmin = min(len(A), len(B))
        for ncells in ncells_list:
            ncells = int(ncells)
            if ncells > nmin:
                continue
            for rep in range(n_reps):
                idx_a = rng.choice(len(A), size=ncells, replace=False)
                idx_b = rng.choice(len(B), size=ncells, replace=False)
                mmd = float(np.mean([mmd_distance(A[idx_a], B[idx_b], g) for g in gammas]))
                rows.append((ncells, rep, mmd))

    return pd.DataFrame(rows, columns=["ncells", "rep", "mmd"])


def compute_mmd_floor(target, ncells_list, gammas=None, n_reps=10, random_state=0):
    """Irreducible "MMD floor" (self-MMD) of a target distribution.

    A model's eval MMD is ``MMD(treated.sample(ncells), imputed.sample(ncells))``.
    Even a perfect model that resampled the real target cannot drive this to zero,
    because the MMD between two finite samples of the SAME distribution is strictly
    positive (finite-sample bias of the V-statistic). This estimates that floor by
    drawing two disjoint size-``ncells`` subsamples from ``target`` and averaging
    over ``n_reps``. Pass the SAME ``gammas`` and ``ncells_list`` the eval uses.

    Thin wrapper over ``compute_mmd_two_sample(..., split_half=True)``; returns rows
    ``[ncells, rep, mmd_floor]`` for backward compatibility.
    """
    df = compute_mmd_two_sample(
        target, B=None, ncells_list=ncells_list, gammas=gammas,
        n_reps=n_reps, random_state=random_state, split_half=True,
    )
    return df.rename(columns={"mmd": "mmd_floor"})


def compute_scalar_mmd(target, transport, gammas=None):
    if gammas is None:
        gammas = [2, 1, 0.5, 0.1, 0.01, 0.005]

    def safe_mmd(*args):
        try:
            mmd = mmd_distance(*args)
        except ValueError:
            mmd = np.nan
        return mmd

    return np.mean(list(map(lambda x: safe_mmd(target, transport, x), gammas)))

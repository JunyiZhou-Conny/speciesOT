"""Option A — reweight-then-balanced mass estimators.

Estimates per-cell source/target sampling weights once, then the *existing*
balanced CellOT ICNN is trained with WeightedRandomSampler. Uniform weights
(or blend strength α=0) recover the balanced baseline (τ→∞ / ρ→∞ parity end).

Methods
-------
- uniform         : parity / control
- louvain_match   : match cluster proportions (LPS has ``louvain``; atlas uses
                    cell_type ontology when available)
- density_ratio   : kNN density ratio in frozen AE latent — source weight
                    ∝ p̂_target / p̂_source (clipped), so source mass in
                    target-scarce regions is down-weighted
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional

import numpy as np

Method = Literal["uniform", "louvain_match", "density_ratio"]


@dataclass
class WeightArtifact:
    """Saved once; consumed by train_option_a.py."""

    obs_names: np.ndarray
    source_mask: np.ndarray
    target_mask: np.ndarray
    source_weights: np.ndarray
    target_weights: np.ndarray
    method: str
    alpha: float
    meta: dict

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            obs_names=self.obs_names.astype(str),
            source_mask=self.source_mask.astype(bool),
            target_mask=self.target_mask.astype(bool),
            source_weights=self.source_weights.astype(np.float64),
            target_weights=self.target_weights.astype(np.float64),
            method=np.asarray(self.method),
            alpha=np.asarray(self.alpha, dtype=np.float64),
            meta_keys=np.asarray(list(self.meta.keys()), dtype=str),
            meta_vals=np.asarray([str(self.meta[k]) for k in self.meta], dtype=str),
        )

    @classmethod
    def load(cls, path: Path) -> "WeightArtifact":
        z = np.load(Path(path), allow_pickle=False)
        meta = dict(zip(z["meta_keys"].tolist(), z["meta_vals"].tolist()))
        return cls(
            obs_names=z["obs_names"],
            source_mask=z["source_mask"].astype(bool),
            target_mask=z["target_mask"].astype(bool),
            source_weights=z["source_weights"].astype(np.float64),
            target_weights=z["target_weights"].astype(np.float64),
            method=str(z["method"]),
            alpha=float(z["alpha"]),
            meta=meta,
        )


def normalize_weights(w: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    w = np.asarray(w, dtype=np.float64)
    w = np.clip(w, eps, None)
    return w / w.sum()


def uniform_weights(n: int) -> np.ndarray:
    return np.full(n, 1.0 / max(n, 1), dtype=np.float64)


def blend_weights(w: np.ndarray, alpha: float) -> np.ndarray:
    """α=0 → uniform (balanced parity); α=1 → full reweight."""
    alpha = float(np.clip(alpha, 0.0, 1.0))
    u = uniform_weights(len(w))
    return normalize_weights((1.0 - alpha) * u + alpha * normalize_weights(w))


def louvain_match_weights(
    labels_source: np.ndarray,
    labels_target: np.ndarray,
    *,
    mode: Literal["match_target", "geometric_mean"] = "geometric_mean",
    eps: float = 1e-3,
) -> tuple[np.ndarray, np.ndarray]:
    """Reweight source (and optionally target) so cluster masses agree.

    For each shared label ℓ:
      w_source_i ∝ π*_ℓ / π_source_ℓ
      w_target_j ∝ π*_ℓ / π_target_ℓ
    where π* is the target composition (``match_target``) or the geometric mean
    of the two empirical compositions (``geometric_mean``).
    Labels present in only one side get weight ``eps`` on that side (near-discard).
    """
    labels_source = np.asarray(labels_source)
    labels_target = np.asarray(labels_target)
    cats = sorted(set(labels_source.tolist()) | set(labels_target.tolist()), key=str)

    def _props(labels):
        n = max(len(labels), 1)
        return {c: float(np.mean(labels == c)) for c in cats}

    ps, pt = _props(labels_source), _props(labels_target)
    if mode == "match_target":
        pstar = pt
    elif mode == "geometric_mean":
        pstar = {
            c: float(np.sqrt(max(ps[c], eps) * max(pt[c], eps))) for c in cats
        }
        z = sum(pstar.values()) or 1.0
        pstar = {c: v / z for c, v in pstar.items()}
    else:
        raise ValueError(mode)

    def _w(labels, p_emp, other_props):
        out = np.empty(len(labels), dtype=np.float64)
        for i, lab in enumerate(labels):
            pe = max(p_emp[lab], eps)
            # cluster absent on the other side → near-discard
            if other_props.get(lab, 0.0) < eps:
                out[i] = eps
            else:
                out[i] = pstar[lab] / pe
        return normalize_weights(out)

    return _w(labels_source, ps, pt), _w(labels_target, pt, ps)


def density_ratio_weights(
    X_source: np.ndarray,
    X_target: np.ndarray,
    *,
    k: int = 20,
    clip: tuple[float, float] = (0.05, 20.0),
) -> tuple[np.ndarray, np.ndarray]:
    """kNN density-ratio weights in latent space.

    Source weight ∝ ρ̂_t(x) / ρ̂_s(x); target weight ∝ ρ̂_s(y) / ρ̂_t(y).
    Uses inverse distance to the k-th neighbor as a local density proxy.
    """
    from sklearn.neighbors import NearestNeighbors

    Xs = np.asarray(X_source, dtype=np.float64)
    Xt = np.asarray(X_target, dtype=np.float64)
    lo, hi = clip

    def _density(points, ref):
        nn = NearestNeighbors(n_neighbors=min(k + 1, len(ref)), algorithm="auto")
        nn.fit(ref)
        dist, _ = nn.kneighbors(points)
        # last column ≈ distance to k-th neighbor (skip self when ref is same cloud)
        d = dist[:, -1]
        d = np.maximum(d, 1e-8)
        return 1.0 / d

    rho_s_on_s = _density(Xs, Xs)
    rho_t_on_s = _density(Xs, Xt)
    rho_t_on_t = _density(Xt, Xt)
    rho_s_on_t = _density(Xt, Xs)

    w_s = np.clip(rho_t_on_s / rho_s_on_s, lo, hi)
    w_t = np.clip(rho_s_on_t / rho_t_on_t, lo, hi)
    return normalize_weights(w_s), normalize_weights(w_t)


def estimate_weights(
    *,
    method: Method,
    alpha: float,
    source_mask: np.ndarray,
    target_mask: np.ndarray,
    obs_names: np.ndarray,
    labels: Optional[np.ndarray] = None,
    latent: Optional[np.ndarray] = None,
    louvain_mode: str = "geometric_mean",
    knn_k: int = 20,
) -> WeightArtifact:
    """Build a WeightArtifact for the full AnnData row order."""
    n = len(obs_names)
    source_mask = np.asarray(source_mask, dtype=bool)
    target_mask = np.asarray(target_mask, dtype=bool)
    assert source_mask.shape == (n,) and target_mask.shape == (n,)

    if method == "uniform":
        ws = uniform_weights(int(source_mask.sum()))
        wt = uniform_weights(int(target_mask.sum()))
    elif method == "louvain_match":
        if labels is None:
            raise ValueError("louvain_match requires labels")
        ws, wt = louvain_match_weights(
            labels[source_mask], labels[target_mask], mode=louvain_mode  # type: ignore[arg-type]
        )
    elif method == "density_ratio":
        if latent is None:
            raise ValueError("density_ratio requires latent embeddings")
        ws, wt = density_ratio_weights(
            latent[source_mask], latent[target_mask], k=knn_k
        )
    else:
        raise ValueError(method)

    ws = blend_weights(ws, alpha)
    wt = blend_weights(wt, alpha)

    # expand to full-length arrays (0 outside the side)
    source_full = np.zeros(n, dtype=np.float64)
    target_full = np.zeros(n, dtype=np.float64)
    source_full[source_mask] = ws
    target_full[target_mask] = wt

    return WeightArtifact(
        obs_names=np.asarray(obs_names).astype(str),
        source_mask=source_mask,
        target_mask=target_mask,
        source_weights=source_full,
        target_weights=target_full,
        method=method,
        alpha=float(alpha),
        meta={
            "louvain_mode": louvain_mode,
            "knn_k": knn_k,
            "n_source": int(source_mask.sum()),
            "n_target": int(target_mask.sum()),
        },
    )

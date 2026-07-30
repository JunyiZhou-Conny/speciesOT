#!/usr/bin/env python3
"""Five-axis + marker AE identity audit for a trained atlas paper-VAE.

Track B of the bounded AE study: no retraining. Restores an existing
atlas-paper-vae checkpoint and computes the same identity panel the LPS Stage-0
audit produces, so the two datasets can be compared on identical definitions.

Slices: train subsample, mouse OOD (source), human OOD (target).
Marker set: top-100 Wilcoxon human-vs-mouse genes on the OOD slice,
EVALUATION ONLY (never used for training or model selection).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scanpy as sc
import yaml


REPO = Path(__file__).resolve().parents[2]
SCRIPTS = Path(__file__).resolve().parent
ABLATION_SCRIPTS = REPO / "scgen-cellot-ablation" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ABLATION_SCRIPTS))

from _data import load_atlas  # noqa: E402
from stage0_metric_helpers import (  # noqa: E402
    dense_float32,
    distribution_summary,
    file_manifest,
    percell_table,
    pergene_table,
    reconstruction_metrics,
    runtime_manifest,
    write_json,
)


def chunked_roundtrip(X_all, encode, decode, chunk_size):
    n_cells, n_genes = X_all.shape
    X = np.empty((n_cells, n_genes), dtype=np.float32)
    Xhat = np.empty_like(X)
    Z = None
    for lower in range(0, n_cells, chunk_size):
        upper = min(lower + chunk_size, n_cells)
        chunk = np.ascontiguousarray(X_all[lower:upper], dtype=np.float32)
        latent = np.asarray(encode(chunk), dtype=np.float32)
        recon = np.asarray(decode(latent), dtype=np.float32)
        if recon.shape != chunk.shape:
            raise RuntimeError(
                "Round-trip shape mismatch: {} vs {}".format(chunk.shape, recon.shape)
            )
        if Z is None:
            Z = np.empty((n_cells, latent.shape[1]), dtype=np.float32)
        X[lower:upper] = chunk
        Xhat[lower:upper] = recon
        Z[lower:upper] = latent
    return X, Xhat, Z


def baseline_suite(X, Xhat, train_gene_mean, rng):
    shuffled = Xhat[rng.permutation(len(Xhat))]
    out = {
        "autoencoder_mu": reconstruction_metrics(X, Xhat),
        "exact_identity": reconstruction_metrics(X, X),
        "shuffled_reconstruction": reconstruction_metrics(X, shuffled),
        "train_gene_mean": reconstruction_metrics(
            X, np.broadcast_to(train_gene_mean, X.shape)
        ),
        "slice_gene_mean_oracle": reconstruction_metrics(
            X, np.broadcast_to(X.mean(axis=0), X.shape)
        ),
        "zero": reconstruction_metrics(X, np.zeros_like(X)),
    }
    ae_mse = out["autoencoder_mu"]["mse"]
    tm = out["train_gene_mean"]["mse"]
    zm = out["zero"]["mse"]
    out["calibration"] = {
        "mse_gain_vs_train_gene_mean": float(1.0 - ae_mse / tm) if tm > 0 else None,
        "mse_gain_vs_zero": float(1.0 - ae_mse / zm) if zm > 0 else None,
        "pearson_r2_margin_over_shuffled": float(
            out["autoencoder_mu"]["pearson_r2_pergene_mean"]
            - out["shuffled_reconstruction"]["pearson_r2_pergene_mean"]
        ),
    }
    return out


def marker_genes(adata, ood_mask, condition_column, target, n_genes=100):
    """Top-N Wilcoxon target-vs-source genes on the OOD slice (eval only)."""
    sub = adata[ood_mask].copy()
    sub.X = dense_float32(sub.X)
    sc.tl.rank_genes_groups(
        sub, groupby=condition_column, method="wilcoxon", n_genes=int(n_genes)
    )
    return [str(g) for g in sub.uns["rank_genes_groups"]["names"][target]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--train-cells", type=int, default=10000)
    parser.add_argument("--sample-cells", type=int, default=500)
    parser.add_argument("--stochastic-reps", type=int, default=5)
    parser.add_argument("--stochastic-cells", type=int, default=512)
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--n-markers", type=int, default=100)
    args = parser.parse_args()

    cfg = yaml.safe_load(args.config.resolve().read_text())
    result_dir = (REPO / cfg["result_dir"]).resolve()
    if "atlas_paper_vae" not in str(result_dir):
        raise SystemExit("FENCE: bad result_dir {}".format(result_dir))
    model_path = result_dir / "model" / "scgen"
    if not model_path.with_suffix(".index").exists():
        raise FileNotFoundError(str(model_path.with_suffix(".index")))

    sys.path.insert(0, str((REPO / cfg["eval"]["scgen_code_path"]).resolve()))
    sys.path.insert(
        0, str((REPO / cfg["eval"]["honest_metrics_path"]).resolve().parent)
    )
    import anndata  # noqa: E402
    import honest_metrics  # noqa: E402
    import scgen  # noqa: E402
    import tensorflow as tf  # noqa: E402

    rng = np.random.default_rng(args.seed)
    adata = load_atlas(REPO, cfg)
    split = pd.read_csv(result_dir / "split.csv", index_col=0)["split"]
    split = split.reindex(adata.obs_names)
    if split.isna().any():
        raise RuntimeError("split.csv does not cover every cell")

    cond = cfg["condition_column"]
    source, target = cfg["source"], cfg["target"]
    conditions = adata.obs[cond].astype(str)
    is_ood = (split == "ood").to_numpy()

    markers = marker_genes(adata, is_ood, cond, target, args.n_markers)
    marker_rank = {g: i + 1 for i, g in enumerate(markers)}
    marker_mask = np.asarray(
        [str(g) in marker_rank for g in adata.var_names], dtype=bool
    )

    network = scgen.VAEArith(
        x_dimension=adata.n_vars,
        z_dimension=int(cfg["vae"]["z_dimension"]),
        alpha=float(cfg["vae"]["alpha"]),
        dropout_rate=float(cfg["vae"]["dropout_rate"]),
        learning_rate=float(cfg["vae"]["learning_rate"]),
        model_path=str(model_path),
    )
    network.restore_model()

    def encode_mean(X):
        X = np.asarray(X, dtype=np.float32)
        return network.sess.run(
            network.mu, feed_dict={network.x: X, network.is_training: False}
        )

    def encode_sample(X):
        return network.to_latent(np.asarray(X, dtype=np.float32))

    def decode(Z):
        return network.reconstruct(np.asarray(Z, dtype=np.float32), use_data=True)

    X_all = dense_float32(adata.X)
    train_idx_all = np.flatnonzero((split == "train").to_numpy())
    n_train = min(args.train_cells, len(train_idx_all))
    slices = [
        (
            "train_subsample",
            np.sort(rng.choice(train_idx_all, n_train, replace=False)),
        ),
        ("mouse_ood_source", np.flatnonzero(is_ood & (conditions == source).to_numpy())),
        ("human_ood_target", np.flatnonzero(is_ood & (conditions == target).to_numpy())),
    ]

    slice_summaries = {}
    gene_frames = []
    cell_frames = []
    sampled = {"genes": np.asarray([str(g) for g in adata.var_names], dtype="U")}
    train_gene_mean = None

    for number, (name, idx) in enumerate(slices):
        print("[audit] {}: {} cells x {} genes".format(name, len(idx), adata.n_vars), flush=True)
        X, Xhat, Z = chunked_roundtrip(X_all[idx], encode_mean, decode, args.chunk_size)
        if train_gene_mean is None:
            train_gene_mean = X.mean(axis=0)
        srng = np.random.default_rng(args.seed + 1000 + number)
        baselines = baseline_suite(X, Xhat, train_gene_mean, srng)
        recon_mmd = honest_metrics.mmd_two_sample_mean(
            Xhat, X, ncells_list=(80,), n_reps=10, random_state=args.seed
        )
        baselines["autoencoder_mu"]["mmd_at80"] = float(recon_mmd[80])

        gene_arrays = pergene_table(X, Xhat)
        gene_frames.append(
            pd.DataFrame(
                {
                    "slice": name,
                    "gene": np.asarray([str(g) for g in adata.var_names]),
                    "is_marker": marker_mask,
                    "marker_rank": [
                        marker_rank.get(str(g), np.nan) for g in adata.var_names
                    ],
                    **gene_arrays,
                }
            )
        )
        cell_arrays = percell_table(X, Xhat)
        cell_frames.append(
            pd.DataFrame(
                {
                    "slice": name,
                    "cell_id": np.asarray([str(c) for c in adata.obs_names[idx]]),
                    **cell_arrays,
                }
            )
        )

        n_stoch = min(args.stochastic_cells, len(X))
        stoch_idx = srng.choice(len(X), n_stoch, replace=False)
        stoch_X = X[stoch_idx]
        stoch_runs = []
        for rep in range(args.stochastic_reps):
            m = reconstruction_metrics(stoch_X, decode(encode_sample(stoch_X)))
            m["rep"] = int(rep)
            stoch_runs.append(m)

        n_sample = min(args.sample_cells, len(X))
        s_idx = srng.choice(len(X), n_sample, replace=False)
        sampled[name + "_X"] = X[s_idx]
        sampled[name + "_Xhat"] = Xhat[s_idx]
        sampled[name + "_Z_mu"] = Z[s_idx]

        slice_summaries[name] = {
            "n_cells": int(len(X)),
            "n_genes": int(X.shape[1]),
            "baselines": baselines,
            "feature_sets": {
                "top{}_species_markers".format(args.n_markers): {
                    "selection": (
                        "OOD-slice Wilcoxon {} vs {}; evaluation only".format(
                            target, source
                        )
                    ),
                    "n_genes": int(marker_mask.sum()),
                    "identity": reconstruction_metrics(
                        X[:, marker_mask], Xhat[:, marker_mask]
                    ),
                    "other_genes_identity": reconstruction_metrics(
                        X[:, ~marker_mask], Xhat[:, ~marker_mask]
                    ),
                }
            },
            "percell_mse": distribution_summary(cell_arrays["mse"]),
            "percell_pearson_r": distribution_summary(cell_arrays["pearson_r"]),
            "percell_cosine": distribution_summary(cell_arrays["cosine"]),
            "stochastic_sampled_z": {
                "n_cells": int(n_stoch),
                "n_reps": int(args.stochastic_reps),
                "pearson_r2_mean_across_reps": float(
                    np.mean([r["pearson_r2_pergene_mean"] for r in stoch_runs])
                ),
                "mse_mean_across_reps": float(
                    np.mean([r["mse"] for r in stoch_runs])
                ),
                "runs": stoch_runs,
            },
        }
        del X, Xhat, Z

    pergene_path = result_dir / "recon_identity_pergene.csv"
    percell_path = result_dir / "recon_identity_percell.csv"
    summary_path = result_dir / "recon_identity_extended.json"
    sampled_path = result_dir / "recon_identity_sampled_clouds.npz"
    pd.concat(gene_frames, ignore_index=True).to_csv(pergene_path, index=False)
    pd.concat(cell_frames, ignore_index=True).to_csv(percell_path, index=False)
    np.savez_compressed(sampled_path, **sampled)

    write_json(
        summary_path,
        {
            "experiment_tag": cfg["experiment_tag"],
            "model": "TensorFlow scgen.VAEArith (restored, no retraining)",
            "latent_dim": int(cfg["vae"]["z_dimension"]),
            "dropout": float(cfg["vae"]["dropout_rate"]),
            "alpha": float(cfg["vae"]["alpha"]),
            "deterministic_primary": "decode(network.mu(X))",
            "stochastic_sensitivity": "decode(network.to_latent(X)); sampled z",
            "marker_set": {
                "n": len(markers),
                "selection": "OOD-slice Wilcoxon {} vs {}; evaluation only".format(
                    target, source
                ),
                "genes": markers,
            },
            "metric_semantics": {
                "pearson_r2_pergene": (
                    "Per gene, Pearson correlation across paired cells, squared; "
                    "mean over genes. Not standard COD."
                ),
                "cod_pergene": "Per gene, 1 - SSE/SST across paired cells.",
                "mean_vector_pearson_r2": (
                    "Pearson squared across raw vs reconstructed gene-mean vectors."
                ),
            },
            "slices": slice_summaries,
            "seed": int(args.seed),
        },
    )

    files = [
        args.config.resolve(),
        model_path.with_suffix(".index"),
        model_path.with_suffix(".data-00000-of-00001"),
        result_dir / "split.csv",
        result_dir / "metrics.json",
        Path(__file__).resolve(),
        ABLATION_SCRIPTS / "stage0_metric_helpers.py",
    ]
    write_json(
        result_dir / "audit_manifest.json",
        {
            "files": [file_manifest(p) for p in files if p.exists()],
            "data_shape": [int(adata.n_obs), int(adata.n_vars)],
            "split_counts": {
                str(k): int(v) for k, v in split.value_counts().items()
            },
            "condition_counts": {
                str(k): int(v) for k, v in conditions.value_counts().items()
            },
            "var_names_sha256": hashlib.sha256(
                "\n".join(str(g) for g in adata.var_names).encode("utf-8")
            ).hexdigest(),
            "runtime": {
                **runtime_manifest(),
                "scanpy": sc.__version__,
                "anndata": anndata.__version__,
                "tensorflow": tf.__version__,
            },
            "seed": int(args.seed),
            "outputs": {
                "summary": str(summary_path),
                "pergene": str(pergene_path),
                "percell": str(percell_path),
                "sampled_clouds": str(sampled_path),
            },
        },
    )
    network.sess.close()
    print("[audit] wrote {}".format(summary_path), flush=True)


if __name__ == "__main__":
    main()

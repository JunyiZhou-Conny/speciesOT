"""Five-axis autoencoder identity panel for a hub scGen AE, per data slice.

The transport sidecars (``extended_metrics.csv``, ``decoded_frame_metrics.csv``)
score the *transport*. This one scores the *autoencoder underneath it*: how well
does ``decode(encode(x))`` reproduce ``x``, separately for cells the AE trained
on and for the held-out cell type it never saw.

Reported jointly, because no single axis decides whether an AE is good:
  - mse                        absolute error scale
  - pearson_r2_pergene_mean    paired-cell Pearson2 per gene (pattern across cells)
  - cod_pergene_mean           coefficient of determination per gene (amplitude too)
  - mean_vector_pearson_r2     Pearson2 between gene-mean vectors (the easy axis)
  - percell_pearson_r_mean     per-cell profile correlation
  - mmd_recon                  MMD(recon, true) on the same slice
plus median per-gene variance retention, which is what separates "the pattern is
right but the amplitude is squashed" from "the pattern is wrong".

Medians are reported beside the two per-gene means because the means are not
robust: COD is unbounded below, so a handful of genes with almost no variance can
dominate it. Measured on the a_uncapped train/target slice, 5 of 1000 genes had
COD < -10 (worst -963.6 at var_true 3e-6), pulling the mean to -0.69 while the
median sat at +0.565. Read the median as the typical gene and the mean only
together with ``n_genes_cod_below_neg1``.

Metric definitions are imported from the Stage-0 helpers rather than reimplemented,
so these numbers are directly comparable to the LPS Stage-0 audit and the atlas
paper-VAE Track B audit.

Slices come from the run's own ``datasplit``, so they match what the model saw:
  train/{source,target}   cells the AE fit on
  test/{source,target}    held-out cells of *seen* cell types (iid generalization)
  ood/{source,target}     the held-out cell type (the real OOD question)
  ignore/{source,target}  the other half of the holdout pool, also never seen

``source``/``target`` are the config's species (mouse/human for speciesOT).

Note the AE is shared: a run's ``impact_cellot`` config points ``ae_emb.path`` at
the same ``scgen/`` directory, so one panel per cut covers both models.

USAGE (CellOT env, from cellot_gpu/):
    PYTHONPATH=. python scripts/ae_identity_metrics.py \\
        --aedir ./results/hvg_pearson_residuals_m1_v08_ood/scgen
"""

from pathlib import Path
import argparse
import json
import sys

import numpy as np
import pandas as pd

from cellot.losses import compute_mmd_two_sample
from cellot.utils import load_config
from cellot.utils.evaluate import load_projectors
from cellot.utils.loaders import load_data

# Single source of truth for the metric definitions (shared with the TF audits).
_REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO / "scgen-cellot-ablation" / "scripts"))
from stage0_metric_helpers import (  # noqa: E402
    dense_float32,
    percell_table,
    pergene_table,
    reconstruction_metrics,
)


def _log(msg):
    print(f"[ae-identity] {msg}", flush=True)


def _iter_slices(dataset):
    """Yield (split, transport, adata) for every (split, transport) group present.

    ``load_data(split_on=["split", "transport"])`` returns a nested dot-dict whose
    outer keys are split values and inner keys are transport values. Enumerated
    rather than hardcoded because which splits exist depends on datasplit.mode.
    """
    outer = dataset.keys() if hasattr(dataset, "keys") else []
    for split in outer:
        group = dataset[split]
        if not hasattr(group, "keys"):
            continue
        for transport in group.keys():
            node = group[transport]
            adata = getattr(node, "adata", None)
            if adata is not None and adata.n_obs > 0:
                yield str(split), str(transport), adata


def _roundtrip(df, encode, decode, chunk_size):
    """decode(encode(df)) in row chunks, preserving row and column order."""
    out = []
    for start in range(0, len(df), chunk_size):
        block = df.iloc[start : start + chunk_size]
        out.append(np.asarray(decode(encode(block)).values, dtype=np.float32))
    return np.vstack(out)


def _recon_mmd(recon, true, ncells_list, n_reps, random_state):
    """MMD(recon, true) per ncells; NaN where the slice is too small to sample."""
    usable = [nc for nc in ncells_list if nc <= min(len(recon), len(true))]
    result = {nc: float("nan") for nc in ncells_list}
    if not usable:
        return result
    frame = compute_mmd_two_sample(
        recon,
        true,
        ncells_list=usable,
        gammas=np.logspace(1, -3, num=50),
        n_reps=n_reps,
        random_state=random_state,
    )
    for nc in usable:
        result[nc] = float(frame[frame["ncells"] == nc]["mmd"].mean())
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--aedir", required=True,
                    help="AE dir with config.yaml + cache/model.pt (a run's scgen/)")
    ap.add_argument("--outdir", default=None,
                    help="output dir (default: <aedir>/ae_identity)")
    ap.add_argument("--n_cells", default="30,50,80",
                    help="ncells values for the reconstruction MMD")
    ap.add_argument("--n_reps", type=int, default=10)
    ap.add_argument("--random_state", type=int, default=0)
    ap.add_argument("--chunk_size", type=int, default=4096)
    ap.add_argument("--percell_max", type=int, default=5000,
                    help="cap rows written to the per-cell sidecar per slice")
    args = ap.parse_args()

    aedir = Path(args.aedir)
    outdir = Path(args.outdir) if args.outdir else aedir / "ae_identity"
    outdir.mkdir(parents=True, exist_ok=True)
    ncells_list = [int(x) for x in args.n_cells.split(",")]

    config = load_config(aedir / "config.yaml")
    if "ae_emb" in config.data:
        raise SystemExit(
            f"[ae-identity] {aedir} looks like a transport run, not an AE. "
            "Point --aedir at the run's scgen/ directory."
        )

    _log(f"loading data for {aedir} (holdout={config.datasplit.get('holdout')})")
    dataset = load_data(config, split_on=["split", "transport"], return_as="dataset")

    _log("loading AE (encode -> decode round trip)")
    encode, decode = load_projectors(aedir, "ae", "data_space")

    summary_rows = []
    pergene_frames = []
    percell_frames = []
    rng = np.random.default_rng(args.random_state)

    for split, transport, adata in _iter_slices(dataset):
        label = f"{split}/{transport}"
        df = adata.to_df()
        X = dense_float32(df.values)
        Xhat = _roundtrip(df, encode, decode, args.chunk_size)

        panel = reconstruction_metrics(X, Xhat)
        pg = pergene_table(X, Xhat)
        pc = percell_table(X, Xhat)
        mmd = _recon_mmd(Xhat, X, ncells_list, args.n_reps, args.random_state)

        species = sorted(set(str(v) for v in adata.obs[config.data.condition]))
        for nc in ncells_list:
            summary_rows.append({
                "slice": label,
                "split": split,
                "transport": transport,
                "species": "|".join(species),
                "n_cells_slice": int(adata.n_obs),
                "n_genes": int(adata.n_vars),
                "ncells": nc,
                "mmd_recon": mmd[nc],
                "mse": panel["mse"],
                "pearson_r2_pergene_mean": panel["pearson_r2_pergene_mean"],
                "pearson_r2_pergene_median": float(np.nanmedian(pg["pearson_r2"])),
                "cod_pergene_mean": panel["cod_pergene_mean"],
                "cod_pergene_median": float(np.nanmedian(pg["cod"])),
                "n_genes_cod_below_neg1": int(np.nansum(pg["cod"] < -1.0)),
                "mean_vector_pearson_r2": panel["mean_vector_pearson_r2"],
                "percell_pearson_r_mean": float(np.nanmean(pc["pearson_r"])),
                "explained_variance_pergene_mean":
                    panel["explained_variance_pergene_mean"],
                "variance_retention_median":
                    float(np.nanmedian(pg["variance_retention_ratio"])),
                "zero_fraction_true": float(np.mean(pg["zero_fraction_true"])),
                "zero_fraction_recon": float(np.mean(pg["zero_fraction_recon"])),
            })

        frame = pd.DataFrame({k: v for k, v in pg.items()})
        frame.insert(0, "gene", list(adata.var_names))
        frame.insert(0, "slice", label)
        pergene_frames.append(frame)

        cell_frame = pd.DataFrame({k: v for k, v in pc.items()})
        cell_frame.insert(0, "cell_id", list(adata.obs_names))
        cell_frame.insert(0, "slice", label)
        if len(cell_frame) > args.percell_max:
            keep = rng.choice(len(cell_frame), size=args.percell_max, replace=False)
            cell_frame = cell_frame.iloc[np.sort(keep)]
        percell_frames.append(cell_frame)

        _log(
            f"{label:16s} n={adata.n_obs:6d}  "
            f"pairR2={panel['pearson_r2_pergene_mean']:.3f}  "
            f"COD(med)={np.nanmedian(pg['cod']):.3f}  "
            f"meanvecR2={panel['mean_vector_pearson_r2']:.3f}  "
            f"varret={np.nanmedian(pg['variance_retention_ratio']):.3f}"
        )

    if not summary_rows:
        raise SystemExit("[ae-identity] no non-empty (split, transport) slices found")

    summary = pd.DataFrame(summary_rows)
    summary.to_csv(outdir / "ae_identity_metrics.csv", index=False)
    pd.concat(pergene_frames).to_csv(outdir / "ae_identity_pergene.csv", index=False)
    pd.concat(percell_frames).to_csv(outdir / "ae_identity_percell.csv", index=False)

    manifest = {
        "aedir": str(aedir),
        "data_path": str(config.data.path),
        "condition": str(config.data.condition),
        "source": str(config.data.source),
        "target": str(config.data.target),
        "datasplit": dict(config.datasplit),
        "random_state": args.random_state,
        "n_reps": args.n_reps,
        "ncells": ncells_list,
        # The prepped atlas h5ads carry no varm/uns (hub prep strips them), so
        # there is no stored marker/DEG ranking to score a DEG panel against.
        "marker_set_available": False,
    }
    (outdir / "ae_identity_manifest.json").write_text(json.dumps(manifest, indent=2))

    headline = summary[summary["ncells"] == max(ncells_list)]
    cols = ["slice", "n_cells_slice", "mse", "pearson_r2_pergene_mean",
            "cod_pergene_median", "cod_pergene_mean", "mean_vector_pearson_r2",
            "percell_pearson_r_mean", "variance_retention_median", "mmd_recon"]
    pd.set_option("display.float_format", lambda v: f"{v:.4f}")
    print(headline[cols].to_string(index=False))
    _log(f"wrote {outdir}/ae_identity_metrics.csv")


if __name__ == "__main__":
    main()

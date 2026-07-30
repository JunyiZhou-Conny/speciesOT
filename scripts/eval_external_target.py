#!/usr/bin/env python3
"""Score a species-transport prediction against an EXTERNAL ground-truth target.

Every other metric path in this repo compares a prediction against cells that were
held out *inside* the atlas (`extended_metrics.py`, `decoded_frame_metrics.py`, the
hub scorecard). `scripts/predict_new_input.sh` runs a brand-new mouse file through
the deployment `atlas_full_*` models and stops at "predictions written". This script
is the missing second half: given a prediction, the real target cells it should have
matched, and the source cells that produced it, it computes the decoded-frame metric
set this project judges on and writes a sidecar CSV + JSON.

Frame
-----
All references are built in the **decoded frame** (docs/conceptual_framework.md 5.9),
because that is where the model's output actually lives:

    mmd_model            = MMD(pred,                 target)
    mmd_ae_recon_floor   = MMD(decode(encode(target)), target)   <- FLOOR
    mmd_decoded_ceiling  = MMD(decode(encode(source)), target)   <- CEILING (no transport)

    decoded_denominator      = ceiling - floor
    model_over_floor         = mmd_model / floor
    frac_gap_closed_decoded  = (ceiling - mmd_model) / (ceiling - floor)

Per 5.9 the gap-closed fraction is NOT rankable across models whose AE floors
differ, and it carries roughly one usable digit once the denominator drops toward
~0.02. So `decoded_denominator` and `model_over_floor` are printed and written
unconditionally, next to the fraction, and a conditioning verdict is emitted.

Guardrails reported alongside: R2 of per-gene means (all genes and a marker set, in
both raw and decoded reference frames) and mean per-gene Jensen-Shannon divergence.

Gene-axis alignment is the main correctness risk with an external target: the three
clouds must be on the SAME genes in the SAME order, and that axis must match the
axis the autoencoder was trained on. All four are asserted; a mismatch aborts with a
diff report rather than silently intersecting.

USAGE (CellOT env)
------------------
    conda activate CellOT
    python scripts/eval_external_target.py \
        --pred   .../bcg_unvax_predicted_human_via_impact_cellot_pearson_residuals.h5ad \
        --target .../bcg_unvax_human_aligned_pearson_residuals_v07.h5ad \
        --source .../bcg_unvax_mouse_aligned_pearson_residuals_v07.h5ad \
        --aedir  cellot/cellot_gpu/results/atlas_full_pearson_residuals/model-scgen \
        --tag    bcg_unvax_impact_pearson

Writes `<outdir>/external_target_metrics.{csv,json}` (default outdir:
`results/external_eval/<tag>/`). CPU only; a few minutes for ~10^3 cells x 10^3 genes.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CELLOT_DIR = REPO_ROOT / "cellot" / "cellot_gpu"
HONEST_METRICS_DIR = REPO_ROOT / "scgen-cellot-autoresearch"

# Reuse the vendored, dependency-free kernels rather than reimplementing them.
# mmd_two_sample_mean mirrors cellot.losses.compute_mmd_two_sample exactly (same
# gammas, same rng draw order, same aggregation), so numbers are directly
# comparable with decoded_frame_metrics.csv.
sys.path.insert(0, str(HONEST_METRICS_DIR))
from honest_metrics import (  # noqa: E402
    DEFAULT_GAMMAS,
    compute_mean_js,
    mmd_two_sample_mean,
)

# Ordinary subsample noise on MMD at ncells=80, n_reps=10 (5.9).
MMD_NOISE = 0.005
# Below this the gap-closed fraction has ~one usable digit (5.9: LPS cut = 0.022).
DENOM_ILL_CONDITIONED = 0.10


# --------------------------------------------------------------------- loading
def _load_cloud(path: Path, layer: str | None, label: str):
    """Return (dense float64 matrix, ordered gene list) from an .h5ad."""
    import anndata as ad

    try:
        adata = ad.read_h5ad(str(path))
    except Exception as exc:  # anndata 0.7 cannot read files written by 0.8+
        raise SystemExit(
            f"[external-eval] could not read {label} at {path}\n"
            f"  {type(exc).__name__}: {exc}\n"
            "  If this file was written by a modern anndata, use the '_v07' variant "
            "produced by scripts/predict_new_input.sh phase 2, or re-run that "
            "round-trip on it."
        )

    if layer:
        if layer not in adata.layers:
            raise SystemExit(
                f"[external-eval] {label}: layer '{layer}' not found "
                f"(available: {list(adata.layers.keys())})"
            )
        X = adata.layers[layer]
    else:
        X = adata.X

    X = np.asarray(X.todense()) if hasattr(X, "todense") else np.asarray(X)
    X = np.asarray(X, dtype=np.float64)
    if not np.all(np.isfinite(X)):
        raise SystemExit(f"[external-eval] {label}: matrix contains non-finite values")
    genes = [str(g) for g in adata.var_names]
    print(f"[external-eval] {label:<7} {path}")
    print(f"[external-eval]         shape={X.shape}  min={X.min():.4f} max={X.max():.4f}")
    return X, genes


def _warn_if_raw_counts(X: np.ndarray, label: str) -> str | None:
    """The whole pipeline works on log1p(CP10k). Raw counts here are a silent killer."""
    sample = X[: min(len(X), 200)]
    looks_integer = bool(np.allclose(sample, np.round(sample)))
    if looks_integer and X.max() > 50:
        msg = (
            f"{label} looks like RAW INTEGER COUNTS (max={X.max():.0f}, all-integer). "
            "Every model in this repo consumes log1p(normalize_total(counts, 1e4)). "
            "Predictions and metrics will be meaningless."
        )
        print(f"[external-eval] WARNING: {msg}")
        return msg
    return None


def _zero_fraction(X: np.ndarray) -> float:
    return float(np.mean(X == 0.0))


def _warn_if_pred_not_decoded(pred: np.ndarray, target: np.ndarray) -> str | None:
    """The decoded references only grade an AE-decoded prediction.

    A decoded cloud is dense (the decoder essentially never emits exact zeros); a
    raw log1p(CP10k) cloud is mostly zeros. Feeding a raw cloud in as --pred silently
    compares two different frames and inflates the gap-closed fraction (the AE
    round-trip tax, conceptual_framework.md 5.9).
    """
    pred_zeros = _zero_fraction(pred)
    if pred_zeros > 0.2 and pred_zeros > 0.5 * _zero_fraction(target):
        msg = (
            f"--pred is {100 * pred_zeros:.0f}% exact zeros, so it looks like a RAW "
            "cloud rather than an AE-decoded model output. The decoded floor/ceiling "
            "grade decoded predictions; a raw prediction is on a different scale and "
            "its frac_gap_closed_decoded is not interpretable."
        )
        print(f"[external-eval] WARNING: {msg}")
        return msg
    return None


def _assert_gene_axis(axes: "dict[str, list[str]]") -> list[str]:
    """Require identical, identically-ordered gene axes. Never silently intersect."""
    labels = list(axes)
    ref_label, reference = labels[0], axes[labels[0]]
    ok = True
    for label in labels[1:]:
        other = axes[label]
        if other == reference:
            continue
        ok = False
        print(f"[external-eval] GENE AXIS MISMATCH: '{ref_label}' vs '{label}'", file=sys.stderr)
        print(f"[external-eval]   n_genes: {len(reference)} vs {len(other)}", file=sys.stderr)
        set_ref, set_other = set(reference), set(other)
        print(
            f"[external-eval]   shared={len(set_ref & set_other)}  "
            f"only_in_{ref_label}={len(set_ref - set_other)}  "
            f"only_in_{label}={len(set_other - set_ref)}",
            file=sys.stderr,
        )
        if set_ref == set_other:
            first = next(
                (i for i, (a, b) in enumerate(zip(reference, other)) if a != b), None
            )
            print(
                f"[external-eval]   same gene SET but different ORDER; "
                f"first divergence at index {first}: {reference[first]!r} vs {other[first]!r}",
                file=sys.stderr,
            )
        else:
            missing = [g for g in reference if g not in set_other][:5]
            extra = [g for g in other if g not in set_ref][:5]
            print(f"[external-eval]   e.g. missing from {label}: {missing}", file=sys.stderr)
            print(f"[external-eval]   e.g. extra in {label}: {extra}", file=sys.stderr)
    if not ok:
        raise SystemExit(
            "[external-eval] aborting: the prediction, the target and the source must "
            "sit on the same gene axis in the same order. Re-run "
            "scripts/predict_new_input.sh on BOTH species files so they are projected "
            "onto the same atlas HVG list; do not intersect them by hand."
        )
    print(f"[external-eval] gene axis OK: {len(reference)} genes, identical and ordered")
    return reference


# --------------------------------------------------------------------- markers
def _resolve_markers(genes, target, source, markers_file, n_markers):
    """Return (indices, names, provenance string)."""
    if markers_file:
        names = [
            line.strip()
            for line in Path(markers_file).read_text().splitlines()
            if line.strip() and not line.startswith("#")
        ]
        index = {g: i for i, g in enumerate(genes)}
        missing = [g for g in names if g not in index]
        if missing:
            raise SystemExit(
                f"[external-eval] {len(missing)} marker genes are not on the gene axis, "
                f"e.g. {missing[:5]}"
            )
        return [index[g] for g in names], names, f"file:{markers_file}"

    if not n_markers:
        return None, None, "none"

    n_markers = min(int(n_markers), len(genes))
    delta = np.abs(target.mean(0) - source.mean(0))
    idx = np.argsort(delta)[::-1][:n_markers]
    idx = sorted(int(i) for i in idx)
    provenance = (
        f"derived:top{n_markers}_abs_mean_diff(target_vs_source); "
        "evaluation-only, never used for training or model selection"
    )
    return idx, [genes[i] for i in idx], provenance


# ----------------------------------------------------------------------- stats
def _r2_means(A, B) -> float:
    a, b = np.asarray(A).mean(0), np.asarray(B).mean(0)
    if a.std() < 1e-12 or b.std() < 1e-12:
        return float("nan")
    r = np.corrcoef(a, b)[0, 1]
    return float(r * r)


def _split_half_r2(cloud, n_reps: int, rng) -> float:
    cloud = np.asarray(cloud)
    n = len(cloud)
    if n < 4:
        return float("nan")
    return float(
        np.mean(
            [
                _r2_means(cloud[perm[: n // 2]], cloud[perm[n // 2 :]])
                for perm in (rng.permutation(n) for _ in range(n_reps))
            ]
        )
    )


def _r2_block(pred, target, source, target_dec, source_dec, n_reps, seed, cols=None):
    """R2-of-means floor/ceiling in both the raw and the decoded reference frame."""
    sl = (slice(None), cols) if cols is not None else (slice(None), slice(None))
    p, t, s = pred[sl], target[sl], source[sl]
    t_dec, s_dec = target_dec[sl], source_dec[sl]

    rng = np.random.default_rng(seed)
    r2_self = _split_half_r2(t, n_reps, rng)
    r2_identity = _r2_means(s, t)
    r2_model = _r2_means(p, t)

    rng = np.random.default_rng(seed)
    r2_self_dec = _split_half_r2(t_dec, n_reps, rng)
    r2_identity_dec = _r2_means(s_dec, t_dec)
    r2_model_dec = _r2_means(p, t_dec)

    def frac(model, identity, self_):
        if not (np.isfinite(model) and np.isfinite(identity) and np.isfinite(self_)):
            return float("nan")
        return (model - identity) / (self_ - identity) if self_ > identity else float("nan")

    return {
        "r2_model": r2_model,
        "r2_identity": r2_identity,
        "r2_self": r2_self,
        "frac_r2_closed": frac(r2_model, r2_identity, r2_self),
        "r2_model_dec": r2_model_dec,
        "r2_identity_dec": r2_identity_dec,
        "r2_self_dec": r2_self_dec,
        "frac_r2_closed_decoded": frac(r2_model_dec, r2_identity_dec, r2_self_dec),
    }


def _frac(ceiling, model, floor) -> float:
    if not all(np.isfinite(v) for v in (ceiling, model, floor)):
        return float("nan")
    if ceiling <= floor:
        return float("nan")
    return (ceiling - model) / (ceiling - floor)


# ------------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--pred", required=True, help="predicted-human .h5ad (predict_new_input.sh output)")
    ap.add_argument("--target", required=True, help="REAL target-human .h5ad (external ground truth)")
    ap.add_argument("--source", required=True, help="source mouse .h5ad that produced --pred")
    ap.add_argument("--aedir", required=True,
                    help="trained AE dir for the decoded frame, e.g. "
                         "cellot/cellot_gpu/results/atlas_full_pearson_residuals/model-scgen")
    ap.add_argument("--tag", default=None, help="label for the output dir / JSON")
    ap.add_argument("--outdir", default=None,
                    help="default: <repo>/results/external_eval/<tag>")
    ap.add_argument("--layer", default=None, help="read this .layers[...] instead of .X (all three files)")
    ap.add_argument("--embedding", default="ae", choices=["ae", "pca"])
    ap.add_argument("--where", default="data_space", choices=["data_space", "latent_space"])
    ap.add_argument("--n-cells", dest="n_cells", default="30,50,80")
    ap.add_argument("--n-reps", dest="n_reps", type=int, default=10)
    ap.add_argument("--random-state", dest="random_state", type=int, default=0)
    ap.add_argument("--markers", default=None, help="file with one marker gene id per line")
    ap.add_argument("--n-markers", dest="n_markers", type=int, default=50,
                    help="if --markers is absent, derive this many evaluation-only "
                         "markers as the top |mean(target)-mean(source)| genes (0 disables)")
    ap.add_argument("--cellot-dir", dest="cellot_dir", default=str(DEFAULT_CELLOT_DIR))
    args = ap.parse_args()

    pred_path = Path(args.pred).resolve()
    target_path = Path(args.target).resolve()
    source_path = Path(args.source).resolve()
    aedir = Path(args.aedir).resolve()
    cellot_dir = Path(args.cellot_dir).resolve()
    tag = args.tag or pred_path.stem
    outdir = Path(args.outdir).resolve() if args.outdir else REPO_ROOT / "results" / "external_eval" / tag
    outdir.mkdir(parents=True, exist_ok=True)

    for label, path in (("aedir", aedir), ("cellot-dir", cellot_dir)):
        if not path.exists():
            raise SystemExit(f"[external-eval] {label} does not exist: {path}")
    if not (aedir / "config.yaml").exists() or not (aedir / "cache" / "model.pt").exists():
        raise SystemExit(
            f"[external-eval] {aedir} is not a trained AE dir "
            "(needs config.yaml and cache/model.pt)"
        )

    print("=== eval_external_target ===")
    pred, pred_genes = _load_cloud(pred_path, args.layer, "pred")
    target, target_genes = _load_cloud(target_path, args.layer, "target")
    source, source_genes = _load_cloud(source_path, args.layer, "source")

    warnings: list[str] = []
    for label, X in (("target", target), ("source", source)):
        w = _warn_if_raw_counts(X, label)
        if w:
            warnings.append(w)
    w = _warn_if_pred_not_decoded(pred, target)
    if w:
        warnings.append(w)

    genes = _assert_gene_axis(
        {"pred": pred_genes, "target": target_genes, "source": source_genes}
    )

    # ---- autoencoder for the decoded reference frame --------------------------
    sys.path.insert(0, str(cellot_dir))
    from cellot.utils.evaluate import load_projectors  # noqa: E402

    cwd = Path.cwd()
    try:
        # AE configs carry a data.path relative to cellot_gpu/.
        os.chdir(cellot_dir)
        print(f"[external-eval] loading AE from {aedir} ...", flush=True)
        encode, decode = load_projectors(aedir, args.embedding, args.where)
    finally:
        os.chdir(cwd)

    frame = pd.DataFrame(target[:1], columns=genes)
    ae_genes = [str(g) for g in decode(encode(frame)).columns]
    if ae_genes != genes:
        raise SystemExit(
            "[external-eval] the autoencoder was trained on a different gene axis than "
            f"the clouds ({len(ae_genes)} AE genes vs {len(genes)} cloud genes; "
            f"shared={len(set(ae_genes) & set(genes))}). Project the external data onto "
            "the same atlas HVG list this AE was trained on "
            "(scripts/predict_new_input.sh phase 1 does exactly that)."
        )
    print(f"[external-eval] AE gene axis OK ({len(ae_genes)} genes)")

    def roundtrip(X):
        return np.asarray(
            decode(encode(pd.DataFrame(X, columns=genes))).values, dtype=np.float64
        )

    print("[external-eval] round-tripping target and source through the AE ...", flush=True)
    target_dec = roundtrip(target)
    source_dec = roundtrip(source)

    # ---- MMD: model, decoded floor, decoded ceiling ---------------------------
    requested = [int(x) for x in args.n_cells.split(",")]
    nmin = min(len(pred), len(target), len(source))
    ncells_list = [n for n in requested if n <= nmin]
    skipped = [n for n in requested if n > nmin]
    if skipped:
        warnings.append(
            f"ncells {skipped} skipped: smallest cloud has only {nmin} cells "
            f"(pred={len(pred)}, target={len(target)}, source={len(source)})"
        )
        print(f"[external-eval] WARNING: {warnings[-1]}")
    if not ncells_list:
        raise SystemExit(
            f"[external-eval] no feasible ncells: smallest cloud has {nmin} cells, "
            f"requested {requested}"
        )

    kw = dict(
        ncells_list=ncells_list,
        gammas=DEFAULT_GAMMAS,
        n_reps=args.n_reps,
        random_state=args.random_state,
    )
    print(f"[external-eval] computing MMD at ncells={ncells_list} ...", flush=True)
    mmd_model = mmd_two_sample_mean(pred, target, **kw)
    mmd_floor = mmd_two_sample_mean(target_dec, target, **kw)
    mmd_ceiling = mmd_two_sample_mean(source_dec, target, **kw)

    # ---- R2 guardrails: all genes and the marker set --------------------------
    marker_idx, marker_names, marker_provenance = _resolve_markers(
        genes, target, source, args.markers, args.n_markers
    )
    print(f"[external-eval] markers: {marker_provenance}")

    r2_all = _r2_block(pred, target, source, target_dec, source_dec,
                       args.n_reps, args.random_state)
    r2_markers = (
        _r2_block(pred, target, source, target_dec, source_dec,
                  args.n_reps, args.random_state, cols=marker_idx)
        if marker_idx is not None
        else {}
    )

    # ---- JS guardrail ---------------------------------------------------------
    print("[external-eval] computing per-gene Jensen-Shannon ...", flush=True)
    mean_js = compute_mean_js(target, pred)
    mean_js_ae_floor = compute_mean_js(target, target_dec)
    mean_js_identity_decoded = compute_mean_js(target, source_dec)

    # ---- assemble -------------------------------------------------------------
    rows = []
    for nc in ncells_list:
        m, f, c = mmd_model[nc], mmd_floor[nc], mmd_ceiling[nc]
        denominator = c - f
        rows.append(
            {
                "ncells": nc,
                "mmd_model": m,
                "mmd_ae_recon_floor": f,
                "mmd_decoded_ceiling": c,
                "gap_above_ae_recon": m - f,
                "decoded_denominator": denominator,
                "model_over_floor": m / f if f > 0 else float("nan"),
                "frac_gap_closed_decoded": _frac(c, m, f),
                "frac_sensitivity_per_0.005_mmd": (
                    MMD_NOISE / denominator if denominator > 0 else float("nan")
                ),
                "r2_model_dec": r2_all["r2_model_dec"],
                "r2_self_dec": r2_all["r2_self_dec"],
                "r2_identity_dec": r2_all["r2_identity_dec"],
                "frac_r2_closed_decoded": r2_all["frac_r2_closed_decoded"],
                "r2_markers_model_dec": r2_markers.get("r2_model_dec", float("nan")),
                "frac_r2_closed_markers_decoded": r2_markers.get(
                    "frac_r2_closed_decoded", float("nan")
                ),
                "mean_js": mean_js,
                "mean_js_ae_floor": mean_js_ae_floor,
                "mean_js_identity_decoded": mean_js_identity_decoded,
            }
        )
    table = pd.DataFrame(rows)

    headline_nc = ncells_list[-1]
    head = table[table["ncells"] == headline_nc].iloc[0]
    denominator = float(head["decoded_denominator"])
    conditioning = (
        "ill_conditioned" if not np.isfinite(denominator) or denominator < DENOM_ILL_CONDITIONED
        else "well_conditioned"
    )

    payload = {
        "tag": tag,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "inputs": {
            "pred": str(pred_path),
            "target": str(target_path),
            "source": str(source_path),
            "aedir": str(aedir),
            "layer": args.layer,
            "embedding": args.embedding,
            "where": args.where,
        },
        "shapes": {
            "n_genes": len(genes),
            "n_pred_cells": int(len(pred)),
            "n_target_cells": int(len(target)),
            "n_source_cells": int(len(source)),
            "zero_fraction_pred": _zero_fraction(pred),
            "zero_fraction_target": _zero_fraction(target),
            "zero_fraction_source": _zero_fraction(source),
        },
        "settings": {
            "ncells": ncells_list,
            "ncells_requested": requested,
            "n_reps": args.n_reps,
            "random_state": args.random_state,
            "gammas": "logspace(1, -3, 50)",
        },
        "markers": {
            "provenance": marker_provenance,
            "n": 0 if marker_names is None else len(marker_names),
            "genes": marker_names or [],
        },
        "headline_ncells": headline_nc,
        "headline": {
            "mmd_model": float(head["mmd_model"]),
            "mmd_ae_recon_floor": float(head["mmd_ae_recon_floor"]),
            "mmd_decoded_ceiling": float(head["mmd_decoded_ceiling"]),
            "gap_above_ae_recon": float(head["gap_above_ae_recon"]),
            "decoded_denominator": denominator,
            "model_over_floor": float(head["model_over_floor"]),
            "frac_gap_closed_decoded": float(head["frac_gap_closed_decoded"]),
            "conditioning": conditioning,
            "mean_js": mean_js,
            "mean_js_ae_floor": mean_js_ae_floor,
            "mean_js_identity_decoded": mean_js_identity_decoded,
        },
        "r2_all_genes": r2_all,
        "r2_markers": r2_markers,
        "per_ncells": table.to_dict(orient="records"),
        "warnings": warnings,
    }

    csv_path = outdir / "external_target_metrics.csv"
    json_path = outdir / "external_target_metrics.json"
    table.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(payload, indent=2, default=float))

    # ---- report ---------------------------------------------------------------
    pd.set_option("display.float_format", lambda v: f"{v:.4f}")
    print()
    print(table[[
        "ncells", "mmd_model", "mmd_ae_recon_floor", "mmd_decoded_ceiling",
        "decoded_denominator", "model_over_floor", "frac_gap_closed_decoded",
    ]].to_string(index=False))
    print()
    print(f"--- headline (ncells={headline_nc}) ---")
    print(f"  decoded_denominator      = {denominator:.4f}   [{conditioning}]")
    print(f"  model_over_floor         = {float(head['model_over_floor']):.4f}   (1.0 = at the AE floor)")
    print(f"  frac_gap_closed_decoded  = {float(head['frac_gap_closed_decoded']):.4f}")
    if np.isfinite(denominator) and denominator > 0:
        print(f"  a 0.005 MMD wobble moves the fraction by {MMD_NOISE / denominator:.3f}")
    if conditioning == "ill_conditioned":
        print("  WARNING: small denominator -> the gap-closed fraction carries about one")
        print("           usable digit. Rank on mmd_model / gap_above_ae_recon /")
        print("           model_over_floor instead (conceptual_framework.md 5.9).")
    print("  NOTE: per 5.9 the gap-closed fraction is not comparable across models whose")
    print("        AE floors differ. Always quote it with the denominator and model/floor.")
    print()
    print(f"  r2_model_dec (all genes) = {r2_all['r2_model_dec']:.4f}   "
          f"identity={r2_all['r2_identity_dec']:.4f}  self={r2_all['r2_self_dec']:.4f}  "
          f"frac_closed={r2_all['frac_r2_closed_decoded']:.4f}")
    if r2_markers:
        print(f"  r2_model_dec (markers)   = {r2_markers['r2_model_dec']:.4f}   "
              f"identity={r2_markers['r2_identity_dec']:.4f}  "
              f"self={r2_markers['r2_self_dec']:.4f}  "
              f"frac_closed={r2_markers['frac_r2_closed_decoded']:.4f}")
    print(f"  mean_js                  = {mean_js:.4f}   "
          f"(AE floor {mean_js_ae_floor:.4f}, no-transport {mean_js_identity_decoded:.4f})")
    for w in warnings:
        print(f"  WARNING: {w}")
    print()
    print(f"[external-eval] wrote {csv_path}")
    print(f"[external-eval] wrote {json_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

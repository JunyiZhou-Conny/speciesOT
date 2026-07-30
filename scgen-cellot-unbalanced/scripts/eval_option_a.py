#!/usr/bin/env python3
"""Score an Option-A (or parity) CellOT outdir + write mass-aware sidecar.

1. Prints / optionally runs production ``evaluate.py`` + decoded_frame_metrics.
2. Always writes ``uot_aware_metrics.csv`` from the weight artifact (kept-mass)
   and, if ``imputed.h5ad`` exists with louvain labels, composition-matched MMD.

Usage::

  PYTHONPATH=../cellot/cellot_gpu:$PWD python scripts/eval_option_a.py \\
      --outdir results/lps_rat/option_a_louvain_alpha1 \\
      --weights results/lps_rat/weights/weights_louvain_match_alpha1.npz \\
      --run-eval
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CELLOT_GPU = ROOT.parent / "cellot" / "cellot_gpu"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=Path, required=True)
    ap.add_argument("--weights", type=Path, default=None)
    ap.add_argument("--run-eval", action="store_true", help="invoke evaluate.py")
    ap.add_argument("--setting", default="ood")
    ap.add_argument("--n-cells", default="80,500,1000")
    args = ap.parse_args()

    outdir = Path(args.outdir).resolve()
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(CELLOT_GPU))

    from uot.reweight import WeightArtifact
    from metrics.uot_aware import kept_mass_report, composition_matched_mmd

    rows = []

    if args.weights is not None:
        art = WeightArtifact.load(args.weights)
        src_w = art.source_weights[art.source_mask]
        report = kept_mass_report(src_w)
        row = {
            "outdir": str(outdir),
            "method": art.method,
            "alpha": art.alpha,
            **{k: report[k] for k in ("effective_kept_mass", "weight_entropy", "weight_cv")},
        }
        rows.append(row)
        print("[eval_option_a] kept-mass:", report)
    else:
        rows.append(
            {
                "outdir": str(outdir),
                "method": "balanced_no_weights",
                "alpha": 0.0,
                "effective_kept_mass": 1.0,
                "weight_entropy": 1.0,
                "weight_cv": 0.0,
            }
        )

    # Composition-matched MMD if imputed + labels available
    eval_dir = outdir / f"evals_{args.setting}_data_space"
    # paper-style prefix used by LPS runs
    alt = outdir / f"evals_{args.setting}_data_space_paper"
    for ed in (eval_dir, alt):
        imp = ed / "imputed.h5ad"
        if not imp.exists():
            continue
        try:
            import anndata as ad

            pred = ad.read_h5ad(imp)
            if "louvain" not in pred.obs.columns:
                print(f"[eval_option_a] {imp}: no louvain; skip composition-matched MMD")
                break
            # Need treated cloud — from eval_clouds or skip
            clouds = ed / "eval_clouds.npz"
            if not clouds.exists():
                print(f"[eval_option_a] missing {clouds}; skip composition-matched MMD")
                break
            z = np.load(clouds)
            treated = z["treated"]
            imputed = np.asarray(
                pred.X.todense() if hasattr(pred.X, "todense") else pred.X
            )
            # labels for treated unknown in npz — use pred labels only if same length
            # Fallback: skip if shapes mismatch
            if "treated_louvain" in z.files:
                tlab = z["treated_louvain"]
                plab = pred.obs["louvain"].astype(str).values
                cm = composition_matched_mmd(imputed, treated, plab, tlab, ncells=80)
                rows[0].update(cm)
                print("[eval_option_a] composition-matched:", cm)
            else:
                print("[eval_option_a] no treated_louvain in npz; kept-mass only")
        except Exception as exc:
            print(f"[eval_option_a] composition-matched failed: {exc}")
        break

    side = outdir / "uot_aware_metrics.csv"
    keys = sorted({k for r in rows for k in r})
    with open(side, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"[eval_option_a] wrote {side}")

    # Standard evaluate chain (printed always; run if --run-eval)
    cmds = [
        [
            "python",
            str(CELLOT_GPU / "scripts" / "evaluate.py"),
            f"--outdir={outdir}",
            f"--setting={args.setting}",
            "--where=data_space",
            "--embedding=ae",
            f"--n_cells={args.n_cells}",
        ],
        [
            "python",
            str(CELLOT_GPU / "scripts" / "decoded_frame_metrics.py"),
            f"--outdir={outdir}",
            f"--setting={args.setting}",
            "--where=data_space",
            "--embedding=ae",
        ],
    ]
    print("\n# Eval chain (hub never auto-submits; run from cellot_gpu with PYTHONPATH=.):")
    for c in cmds:
        print(" \\\n  ".join(c))

    if args.run_eval:
        # Symlink model-scgen for decoded_frame_metrics hardcode
        parent = outdir.parent
        link = parent / "model-scgen"
        ae_src = CELLOT_GPU / "results" / "paper_crossspecies_rat_ood" / "scgen"
        if not link.exists() and ae_src.exists():
            link.symlink_to(ae_src)
            print(f"[eval_option_a] symlinked {link} -> {ae_src}")
        for c in cmds:
            print("[eval_option_a] running:", " ".join(c))
            subprocess.check_call(c, cwd=str(CELLOT_GPU), env={**dict(**__import__("os").environ), "PYTHONPATH": str(CELLOT_GPU)})


if __name__ == "__main__":
    main()

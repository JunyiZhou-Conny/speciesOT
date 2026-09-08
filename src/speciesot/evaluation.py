from __future__ import annotations

import sys
from pathlib import Path

from .speciesot_core import AbstractEvaluation


HEADLINE = "frac_gap_closed_decoded"
GUARDRAILS = ("frac_r2_closed_decoded", "mean_js")
SIDECAR_DECODED = "decoded_frame_metrics.csv"
SIDECAR_EXTENDED = "extended_metrics.csv"
FROZEN_CUTS = (
    "hvg_pearson_residuals_m1_v08_ood",
    "hvg_pearson_residuals_m2_v08_ood",
    "hvg_pearson_residuals_a_uncapped_v08_ood",
)
SCRIPTS = ("extended_metrics.py", "decoded_frame_metrics.py")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_repo_on_path() -> Path:
    root = _repo_root()
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    return root


def frac_gap_closed_decoded(c, m, f):
    return (c - m) / (c - f)


class DecodedFrameEvaluation(AbstractEvaluation):
    """AE-honest north-star. Frozen cuts: hvg_pearson_residuals_m1_v08_ood,
    hvg_pearson_residuals_m2_v08_ood, hvg_pearson_residuals_a_uncapped_v08_ood.

    Headline is frac_gap_closed_decoded at ncells=80. Guardrails are
    frac_r2_closed_decoded and raw-sidecar mean_js. Do not rank on raw
    frac_gap_closed. Writes the same sidecar names as ./hub metrics:
    decoded_frame_metrics.csv and extended_metrics.csv.
    """

    headline = HEADLINE
    frozen_cuts = FROZEN_CUTS
    scripts = SCRIPTS

    def __init__(self, eval_dir=None, ncells=80, random_state=0):
        self.eval_dir = Path(eval_dir) if eval_dir is not None else None
        self.ncells = ncells
        self.random_state = random_state

    def evaluate(self, model=None, test_data=None, eval_dir=None):
        directory = eval_dir or self.eval_dir or self._from_model(model)
        if directory is None:
            raise FileNotFoundError(
                f"DecodedFrameEvaluation needs an eval dir with {SIDECAR_DECODED}"
            )
        directory = Path(directory)
        decoded = directory / SIDECAR_DECODED
        extended = directory / SIDECAR_EXTENDED
        if not decoded.is_file():
            raise FileNotFoundError(
                f"{SIDECAR_DECODED} missing at {directory}; "
                "run ./hub metrics or the decoded_frame_metrics.py script"
            )
        if not extended.is_file():
            raise FileNotFoundError(
                f"{SIDECAR_EXTENDED} missing at {directory}; "
                "run ./hub metrics or the extended_metrics.py script"
            )
        return self.read(directory)

    def _from_model(self, model):
        spec = getattr(model, "spec", None)
        tag = getattr(spec, "experiment_tag", None) if spec is not None else None
        if not tag:
            return None
        return (
            _repo_root()
            / "cellot"
            / "cellot_gpu"
            / "results"
            / tag
            / "impact_cellot"
            / "evals_ood_data_space"
        )

    def read(self, eval_dir):
        _ensure_repo_on_path()
        import pandas as pd
        from speciesOT.hub.readers import read_decoded_metrics, read_extended_metrics

        directory = Path(eval_dir)
        decoded = pd.read_csv(directory / SIDECAR_DECODED)
        row = decoded.loc[decoded["ncells"] == self.ncells]
        if row.empty:
            raise ValueError(f"no ncells={self.ncells} row in {SIDECAR_DECODED}")
        row = row.iloc[0]
        _floor, _ceil, raw_frac, mean_js = read_extended_metrics(directory)
        fgc, fr2, _ae_floor, _dec_ceil = read_decoded_metrics(directory)
        return {
            HEADLINE: float(row[HEADLINE]),
            "frac_r2_closed_decoded": float(row["frac_r2_closed_decoded"]),
            "mean_js": None if mean_js is None else float(mean_js),
            "ncells": int(self.ncells),
            "random_state": int(self.random_state),
            "raw_frac_gap_closed": None if raw_frac is None else float(raw_frac),
            "hub_fgc_decoded": fgc,
            "hub_fr2_decoded": fr2,
        }

    def rank(self, rows):
        return sorted(
            rows,
            key=lambda item: (
                item.get(HEADLINE) if item.get(HEADLINE) is not None else -1e9
            ),
            reverse=True,
        )

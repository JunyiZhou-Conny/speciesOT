from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from .speciesot_core import AbstractModel


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _ensure_repo_on_path() -> Path:
    root = _repo_root()
    root_s = str(root)
    if root_s not in sys.path:
        sys.path.insert(0, root_s)
    return root


def _cellot_root() -> Path:
    return _repo_root() / "cellot" / "cellot_gpu"


def _load_hub_spec(spec_path: str):
    _ensure_repo_on_path()
    from speciesOT.hub.spec import load_spec_yaml

    return load_spec_yaml(Path(spec_path))


def _render_chain(spec) -> str:
    _ensure_repo_on_path()
    from speciesOT.hub.spec import render_submission_chain

    return render_submission_chain(spec)


def _interpreter_for_device(device: str) -> str:
    if device in {"gpu", "cuda", "CellOT_gpu"}:
        return "CellOT_gpu"
    return "CellOT"


@dataclass(frozen=True)
class JobPlan:
    text: str
    interpreter: str
    experiment_tag: str
    submitted: bool = False


class AutoEncoderModel(AbstractModel):
    """Wraps cellot.train.train.train_auto_encoder. Does not submit sbatch."""

    def __init__(self, spec_path: str, outdir: str | None = None):
        self.spec_path = spec_path
        self.spec = None
        self.outdir = Path(outdir) if outdir is not None else None

    def setup(self):
        self.spec = _load_hub_spec(self.spec_path)
        if self.outdir is None:
            self.outdir = (
                _cellot_root() / "results" / self.spec.experiment_tag / "scgen"
            )

    def job_plan(self, device: str = "cpu") -> JobPlan:
        if self.spec is None:
            self.setup()
        text = _render_chain(self.spec)
        return JobPlan(
            text=text,
            interpreter=_interpreter_for_device(device),
            experiment_tag=self.spec.experiment_tag,
            submitted=False,
        )

    def train(self, *, device: str = "cpu", local: bool = False):
        if not local:
            return self.job_plan(device=device)
        return self._train_local(device=device)

    def _train_local(self, device: str = "cpu"):
        if self.spec is None:
            self.setup()
        if sys.version_info >= (3, 12):
            raise RuntimeError(
                "AutoEncoderModel local train refuses this interpreter; "
                "use CellOT or CellOT_gpu"
            )
        cellot_root = str(_cellot_root())
        if cellot_root not in sys.path:
            sys.path.insert(0, cellot_root)
        from cellot.train.train import train_auto_encoder
        from cellot.utils import load_config

        config_path = self.outdir / "config.yaml"
        if not config_path.is_file():
            raise FileNotFoundError(config_path)
        config = load_config(config_path)
        if device in {"gpu", "cuda", "CellOT_gpu"}:
            config.device = "cuda"
        else:
            config.device = "cpu"
        return train_auto_encoder(self.outdir, config)

    def last_pt_shift(self):
        if self.outdir is None:
            self.setup()
        path = self.outdir / "cache" / "last.pt"
        if not path.is_file():
            return (
                "missing: last.pt not written; "
                "code_means land on last.pt after compute_scgen_shift"
            )
        import torch

        ckpt = torch.load(path, map_location="cpu")
        if "code_means" in ckpt:
            return ckpt["code_means"]
        return "missing: last.pt has no code_means"

    def predict(self, test_data=None):
        raise NotImplementedError("FrozenAE.encode owns AE predict")

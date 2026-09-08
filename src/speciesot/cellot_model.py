from __future__ import annotations

import sys

from .ae import JobPlan, _cellot_root, _ensure_repo_on_path, _interpreter_for_device, _load_hub_spec, _render_chain
from .speciesot_core import AbstractModel


def _ensure_cellot_on_path():
    root = str(_cellot_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    return root


class CellOTModel(AbstractModel):
    """Wraps ICNN-OT. fit is latent-only. predict calls transport_cellot."""

    def __init__(self, spec_path: str, frozen_ae=None):
        self.spec_path = spec_path
        self.frozen_ae = frozen_ae
        self.spec = None
        self.model = None

    def setup(self):
        if self.frozen_ae is None:
            raise FileNotFoundError("missing FrozenAE handle")
        self.spec = _load_hub_spec(self.spec_path)

    def job_plan(self, device: str | None = None) -> JobPlan:
        if self.spec is None:
            self.spec = _load_hub_spec(self.spec_path)
        device = device or getattr(self.spec, "impact_train_device", "cpu")
        _ensure_repo_on_path()
        from speciesOT.hub.spec import render_train_sbatch

        chain = _render_chain(self.spec)
        impact = render_train_sbatch(self.spec, "impact_cellot")
        pythonpath = str(_cellot_root())
        text = (
            f"export PYTHONPATH={pythonpath}\n"
            f"{chain}\n"
            f"# impact sbatch\n"
            f"{impact}\n"
        )
        return JobPlan(
            text=text,
            interpreter=_interpreter_for_device(device),
            experiment_tag=self.spec.experiment_tag,
            submitted=False,
        )

    def train(self, *, device: str | None = None, local: bool = False):
        if not local:
            return self.job_plan(device=device)
        if self.spec is None:
            self.setup()
        _ensure_cellot_on_path()
        from cellot.train.train import train_cellot
        from cellot.utils import load_config

        outdir = _cellot_root() / "results" / self.spec.experiment_tag / "impact_cellot"
        config = load_config(outdir / "config.yaml")
        return train_cellot(outdir, config)

    def fit(self, latent, composed_estimator=None):
        if composed_estimator is None and self._is_gene_space(latent):
            raise ValueError("latent space is required")
        return self._smoke_transport(latent)

    def _is_gene_space(self, latent):
        n_vars = getattr(latent, "n_vars", None)
        if n_vars is not None and n_vars > 200:
            return True
        shape = getattr(latent, "shape", None)
        if shape is not None and len(shape) == 2 and int(shape[1]) > 200:
            return True
        return False

    def _smoke_transport(self, latent):
        import torch

        _ensure_cellot_on_path()
        from cellot.networks.icnns import ICNN

        if hasattr(latent, "X"):
            import numpy as np

            x = torch.as_tensor(np.asarray(latent.X), dtype=torch.float32)
        else:
            x = latent if torch.is_tensor(latent) else torch.as_tensor(latent, dtype=torch.float32)
        g = ICNN(input_dim=int(x.shape[1]), hidden_units=[32, 32])
        self.model = (None, g)
        return g.transport(x.requires_grad_(True))

    def predict(self, inputs):
        import torch

        if torch.is_inference_mode_enabled():
            raise RuntimeError("ICNN transport cannot run under inference_mode")
        _ensure_cellot_on_path()
        from cellot.transport import transport_cellot

        if self.model is None:
            raise RuntimeError("CellOTModel has no fitted ICNN")
        if not torch.is_tensor(inputs):
            inputs = torch.as_tensor(inputs, dtype=torch.float32)
        if not inputs.requires_grad:
            inputs = inputs.requires_grad_(True)
        return transport_cellot(self.model, inputs)

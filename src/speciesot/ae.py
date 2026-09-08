from __future__ import annotations

import importlib.util
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


def _bake_mod():
    path = _repo_root() / "scripts" / "bake_model_artifacts.py"
    spec = importlib.util.spec_from_file_location("bake_model_artifacts", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _resolve_scgen_dir(path: Path) -> Path:
    path = Path(path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"missing FrozenAE handle: {path}")
    path = path.resolve()
    if (path / "cache" / "model.pt").is_file():
        return path
    link = path / "model-scgen"
    if link.exists():
        return _resolve_scgen_dir(link)
    nested = path / "scgen"
    if (nested / "cache" / "model.pt").is_file():
        return nested
    raise FileNotFoundError(f"missing FrozenAE handle: {path}")


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


class FrozenAE:
    """Directory handle for a trained scGen AE. encode uses eval() and no_grad."""

    def __init__(self, directory: Path, gene_axis_sha256=None, genes=None, checkpoint_sha256=None):
        self.directory = Path(directory)
        self.model_pt = self.directory / "cache" / "model.pt"
        self.last_pt = self.directory / "cache" / "last.pt"
        self.shift_pt = self.directory / "cache" / "scgen_shift.pt"
        self.gene_axis_sha256 = gene_axis_sha256
        self.genes = genes
        self.checkpoint_sha256 = checkpoint_sha256

    @classmethod
    def load(cls, path):
        directory = _resolve_scgen_dir(Path(path))
        bake = _bake_mod()
        checkpoint_sha256 = bake.file_sha256(directory / "cache" / "model.pt")
        genes = None
        axis = None
        genes_txt = directory / "genes.txt"
        if not genes_txt.is_file():
            genes_txt = directory.parent / "genes.txt"
        if genes_txt.is_file():
            genes = genes_txt.read_text().splitlines()
            axis = bake.gene_axis_sha256(genes)
        handle = cls(
            directory,
            gene_axis_sha256=axis,
            genes=genes,
            checkpoint_sha256=checkpoint_sha256,
        )
        if handle.shift_pt.is_file():
            handle._assert_shift_fresh()
            if handle.gene_axis_sha256 is None:
                import torch

                payload = torch.load(handle.shift_pt, map_location="cpu")
                handle.gene_axis_sha256 = payload.get("gene_axis_sha256")
        return handle

    def _assert_shift_fresh(self):
        import torch

        payload = torch.load(self.shift_pt, map_location="cpu")
        axis = payload.get("gene_axis_sha256")
        if self.gene_axis_sha256 and axis and axis != self.gene_axis_sha256:
            raise ValueError(f"stale scgen_shift.pt gene_axis_sha256 {axis}")
        ckpt_sha = payload.get("model_checkpoint_sha256")
        if ckpt_sha and self.checkpoint_sha256 and ckpt_sha != self.checkpoint_sha256:
            raise ValueError(f"stale scgen_shift.pt model hash {ckpt_sha}")

    def _load_autoencoder(self):
        cellot_root = str(_cellot_root())
        if cellot_root not in sys.path:
            sys.path.insert(0, cellot_root)
        from cellot.models.ae import load_autoencoder_model
        from cellot.utils import load_config

        config = load_config(self.directory / "config.yaml")
        input_dim = len(self.genes) if self.genes else None
        if input_dim is None and self.shift_pt.is_file():
            import torch

            payload = torch.load(self.shift_pt, map_location="cpu")
            input_dim = payload.get("n_genes")
        if input_dim is None:
            bake = _bake_mod()
            results_root = self.directory.resolve()
            cellot_dir = results_root
            while cellot_dir.name != "cellot_gpu" and cellot_dir != cellot_dir.parent:
                cellot_dir = cellot_dir.parent
            if cellot_dir.name != "cellot_gpu":
                cellot_dir = _cellot_root()
            train_path = bake.resolve_train_path(config, str(cellot_dir))
            genes = bake.h5ad_var_names(train_path)
            input_dim = len(genes)
            if self.genes is None:
                self.genes = genes
            if self.gene_axis_sha256 is None:
                self.gene_axis_sha256 = bake.gene_axis_sha256(genes)
        kwargs = {"input_dim": int(input_dim)}
        model, _ = load_autoencoder_model(
            config,
            restore=str(self.model_pt),
            device="cpu",
            **kwargs,
        )
        if not hasattr(model, "code_means"):
            if self.shift_pt.is_file():
                self._assert_shift_fresh()
                import torch

                payload = torch.load(self.shift_pt, map_location="cpu")
                model.code_means = payload["code_means"]
            elif self.last_pt.is_file():
                import torch

                ckpt = torch.load(self.last_pt, map_location="cpu")
                if "code_means" in ckpt:
                    model.code_means = ckpt["code_means"]
        return model

    def encode(self, inputs):
        import torch

        model = self._load_autoencoder()
        if not torch.is_tensor(inputs):
            inputs = torch.as_tensor(inputs)
        with torch.no_grad():
            return model.eval().encode(inputs)

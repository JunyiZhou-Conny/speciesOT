from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

from .ae import FrozenAE, _bake_mod, _cellot_root, _ensure_repo_on_path


ATLAS_BASENAME = "tabula_sapiens_all.h5ad"


def strip_ens(name):
    name = str(name)
    if name.startswith("ENS") and "." in name:
        return name.split(".", 1)[0]
    return name


def project_genes(matrix, source_names, target_names):
    """Name-project onto the model axis. First-wins on duplicate source names."""
    index = {}
    dupes = []
    for i, name in enumerate(source_names):
        key = strip_ens(name)
        if key in index:
            dupes.append(key)
            continue
        index[key] = i
    if dupes:
        warnings.warn(
            f"duplicate gene names; first-wins kept, later ignored: {dupes[:8]}",
            stacklevel=2,
        )
    src = np.asarray(matrix)
    if hasattr(src, "toarray"):
        src = src.toarray()
    out = np.zeros((src.shape[0], len(target_names)), dtype=np.float32)
    for j, name in enumerate(target_names):
        i = index.get(strip_ens(name))
        if i is not None:
            out[:, j] = src[:, i]
    return out


def _read_matrix(path):
    import h5py

    with h5py.File(path, "r") as handle:
        node = handle["X"]
        if isinstance(node, h5py.Group):
            data = node["data"][:]
            indices = node["indices"][:]
            indptr = node["indptr"][:]
            shape = tuple(node.attrs.get("shape", node.attrs.get("h5sparse_shape")))
            from scipy import sparse

            encoding = node.attrs.get("encoding-type", b"csr_matrix")
            if isinstance(encoding, bytes):
                encoding = encoding.decode()
            matrix = (
                sparse.csc_matrix((data, indices, indptr), shape=shape)
                if "csc" in encoding
                else sparse.csr_matrix((data, indices, indptr), shape=shape)
            )
            matrix = matrix.toarray()
        else:
            matrix = node[:]
        group = handle["var"]
        key = group.attrs.get("_index", "_index")
        if isinstance(key, bytes):
            key = key.decode()
        names = [
            item.decode() if isinstance(item, (bytes, bytearray)) else str(item)
            for item in group[key][:]
        ]
    return np.asarray(matrix), names


def _ensure_cellot_on_path():
    root = str(_cellot_root())
    if root not in sys.path:
        sys.path.insert(0, root)
    return root


class ReferenceBundle:
    """Baked results dir: genes.txt, FrozenAE, scgen_shift.pt, CellOT weights.

    Same handover as scripts/predict_new_input.sh, not a second stack.
    Predict is atlas-free when those sidecars exist. Decoded scoring is not.
    """

    def __init__(self, results_dir, genes, frozen_ae, cellot_dir, gene_axis_sha256):
        self.results_dir = Path(results_dir)
        self.genes = genes
        self.frozen_ae = frozen_ae
        self.cellot_dir = Path(cellot_dir)
        self.gene_axis_sha256 = gene_axis_sha256
        self.model = None

    @classmethod
    def load(cls, results_dir):
        results_dir = Path(results_dir).expanduser().resolve()
        genes_txt = results_dir / "genes.txt"
        if not genes_txt.is_file():
            raise FileNotFoundError(f"missing genes.txt: {genes_txt}")
        genes = [g for g in genes_txt.read_text().splitlines() if g]
        bake = _bake_mod()
        axis = bake.gene_axis_sha256(genes)
        frozen = FrozenAE.load(results_dir / "model-scgen")
        if frozen.gene_axis_sha256 and frozen.gene_axis_sha256 != axis:
            raise ValueError(
                f"gene_axis_sha256 {frozen.gene_axis_sha256} does not match genes.txt {axis}"
            )
        if frozen.shift_pt.is_file():
            import torch

            rec = torch.load(frozen.shift_pt, map_location="cpu").get("gene_axis_sha256")
            if rec and rec != axis:
                raise ValueError(f"gene_axis_sha256 {rec} does not match genes.txt {axis}")
        cellot_dir = results_dir / "impact_cellot"
        if not (cellot_dir / "cache" / "model.pt").is_file():
            raise FileNotFoundError(f"missing CellOT weights: {cellot_dir}")
        return cls(results_dir, genes, frozen, cellot_dir, axis)

    def _assert_axis(self):
        if not self.frozen_ae.shift_pt.is_file():
            return
        import torch

        rec = torch.load(self.frozen_ae.shift_pt, map_location="cpu").get("gene_axis_sha256")
        if rec and rec != self.gene_axis_sha256:
            raise ValueError(
                f"gene_axis_sha256 {rec} does not match genes.txt {self.gene_axis_sha256}"
            )

    def _load_cellot(self):
        if self.model is not None:
            return self.model
        _ensure_cellot_on_path()
        try:
            from absl import flags

            if not flags.FLAGS.is_parsed():
                flags.FLAGS(["speciesot-bundle"])
        except Exception:
            pass
        from cellot.utils import load_config
        from cellot.utils.loaders import load_model

        config = load_config(self.cellot_dir / "config.yaml")
        restore = self.cellot_dir / "cache" / "model.pt"
        latent = config.model.get("latent_dim", 50)
        self.model, *_ = load_model(
            config, restore=str(restore), device="cpu", input_dim=int(latent)
        )
        return self.model

    def predict(self, path):
        path = Path(path)
        if path.name == ATLAS_BASENAME:
            raise RuntimeError(f"predict must not open {ATLAS_BASENAME}")
        self._assert_axis()
        import anndata as ad
        import torch
        from cellot.transport import transport_cellot

        _ensure_cellot_on_path()
        matrix, source_names = _read_matrix(path)
        projected = project_genes(matrix, source_names, self.genes)
        codes = self.frozen_ae.encode(torch.as_tensor(projected, dtype=torch.float32))
        if torch.is_inference_mode_enabled():
            raise RuntimeError("ICNN transport cannot run under inference_mode")
        if not codes.requires_grad:
            codes = codes.detach().requires_grad_(True)
        transported = transport_cellot(self._load_cellot(), codes)
        decoded = self.frozen_ae.decode(transported.detach())
        pred = decoded.detach().cpu().numpy().astype(np.float32)
        out = ad.AnnData(X=pred)
        out.var_names = self.genes
        out.uns["gene_axis_sha256"] = self.gene_axis_sha256
        out.uns["bundle"] = str(self.results_dir)
        return out

    def decoded_score(self, pred=None, atlas_path=None):
        raise FileNotFoundError(
            "decoded scoring still needs the training atlas "
            f"(tabula_sapiens_all.h5ad or the flavor h5ad); "
            f"atlas_path={atlas_path!r}; load_projectors cannot skip patch_scgen_shift"
        )

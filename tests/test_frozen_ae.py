import shutil
import tempfile
from pathlib import Path

from speciesot import Experiment, FrozenAE


BAKED = Path(
    "/n/holylabs/mooney_lab/Lab/junyizhou/speciesOT/cellot/cellot_gpu/results/atlas_full_pearson_residuals"
)
TINY = Path(__file__).resolve().parents[1] / "specs" / "e24_tiny_identity.yaml"


def test_two_experiments_share_one_handle():
    ae = FrozenAE.load(BAKED / "model-scgen")
    first = Experiment(str(TINY), frozen_ae=ae)
    second = Experiment(str(TINY), frozen_ae=ae)
    assert first.frozen_ae is second.frozen_ae
    assert first.frozen_ae.directory == second.frozen_ae.directory


def test_stale_gene_axis_hash_raises():
    import torch

    ae = FrozenAE.load(BAKED / "model-scgen")
    src = ae.shift_pt
    tmp = Path(tempfile.mkdtemp()) / "scgen"
    (tmp / "cache").mkdir(parents=True)
    shutil.copy2(ae.model_pt, tmp / "cache" / "model.pt")
    shutil.copy2(ae.directory / "config.yaml", tmp / "config.yaml")
    if (ae.directory.parent / "genes.txt").is_file():
        shutil.copy2(ae.directory.parent / "genes.txt", tmp.parent / "genes.txt")
    payload = torch.load(src, map_location="cpu")
    payload["gene_axis_sha256"] = "0" * 64
    torch.save(payload, tmp / "cache" / "scgen_shift.pt")
    try:
        FrozenAE.load(tmp)
    except ValueError as exc:
        assert "gene_axis_sha256" in str(exc)
    else:
        raise AssertionError("stale shift must raise")


if __name__ == "__main__":
    test_two_experiments_share_one_handle()
    test_stale_gene_axis_hash_raises()
    print("test_frozen_ae ok")

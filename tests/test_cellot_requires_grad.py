import torch

from speciesot.cellot_model import CellOTModel


def test_icnn_transport_requires_grad():
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "cellot" / "cellot_gpu"
    sys.path.insert(0, str(root))
    from cellot.networks.icnns import ICNN

    g = ICNN(input_dim=50, hidden_units=[16, 16])
    x = torch.randn(8, 50)
    assert x.requires_grad is False
    try:
        g.transport(x)
    except AssertionError:
        pass
    else:
        raise AssertionError("ICNN.transport must assert requires_grad")


def test_fit_refuses_gene_space():
    model = CellOTModel("specs/m2_baseline.yaml")
    genes = torch.randn(16, 1000)
    try:
        model.fit(genes)
    except ValueError as exc:
        assert "latent space is required" in str(exc)
    else:
        raise AssertionError("raw gene-space fit must refuse")


if __name__ == "__main__":
    test_icnn_transport_requires_grad()
    test_fit_refuses_gene_space()
    print("test_cellot_requires_grad ok")

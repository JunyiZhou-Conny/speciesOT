import os
from pathlib import Path

from speciesot import DummyEvaluation, Experiment, IdentityModel


def test_public_import_names():
    assert Experiment.__module__.startswith("speciesot")
    assert DummyEvaluation.__name__ == "DummyEvaluation"
    assert IdentityModel.__name__ == "IdentityModel"


def test_tiny_identity_evaluate_returns_one():
    repo = Path(__file__).resolve().parents[1]
    spec = repo / "specs" / "e24_tiny_identity.yaml"
    experiment = Experiment(str(spec))
    experiment.setup()
    experiment.train()
    predicted = experiment.predict()
    score = experiment.evaluate()
    assert score == 1
    assert predicted.n_obs == 251
    assert "tabula_sapiens_all.h5ad" not in os.fspath(experiment.training_data.source_training_data_path)


if __name__ == "__main__":
    test_public_import_names()
    test_tiny_identity_evaluate_returns_one()
    print("test_speciesot_import ok")

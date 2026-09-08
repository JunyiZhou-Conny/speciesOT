import abc
import inspect
from pathlib import Path

from speciesot.speciesot_core import DatasetHandle, Experiment, TestData, TrainingData

BCG_MOUSE = "/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/tb/data/mouse_bcg/bcg_treated_scanvi_081826.h5ad"
BCG_HUMAN = "/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/tb/data/human_bcg/bcg_treated_scanvi_082626.h5ad"
ATLAS_HUMAN = "/n/holylabs/mooney_lab/Lab/joshprice/speciesOT/data/tabula_sapiens/tabula_sapiens_all.h5ad"


def test_bcg_handle_counts_and_load_x():
    mouse = DatasetHandle(BCG_MOUSE)
    human = DatasetHandle(BCG_HUMAN)
    assert mouse.n_obs == 251
    assert human.n_obs == 392
    assert mouse.load_X().n_obs == 251
    assert human.load_X().n_obs == 392


def test_training_data_tiny_yaml_is_obs_only():
    repo = Path(__file__).resolve().parents[1]
    spec = repo / "specs" / "e24_tiny_identity.yaml"
    experiment = Experiment(str(spec))
    experiment.setup()
    assert experiment.training_data.source.n_obs == 251
    assert experiment.training_data.target.n_obs == 392
    source = inspect.getsource(TrainingData.__init__)
    assert "read_h5ad" not in source
    assert not issubclass(TrainingData, abc.ABC)
    assert not issubclass(TestData, abc.ABC)
    assert not issubclass(Experiment, abc.ABC)


def test_atlas_handle_refuses_load_x():
    handle = DatasetHandle(ATLAS_HUMAN)
    assert handle.n_obs == 1136218
    try:
        handle.load_X()
    except RuntimeError as exc:
        assert "named small slice" in str(exc)
    else:
        raise AssertionError("load_X must refuse the 43 GB atlas")


if __name__ == "__main__":
    test_bcg_handle_counts_and_load_x()
    test_training_data_tiny_yaml_is_obs_only()
    test_atlas_handle_refuses_load_x()
    print("test_dataset_handle ok")

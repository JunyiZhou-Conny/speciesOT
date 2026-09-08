import abc
import os

import h5py
import scanpy as sc
import yaml

_LOAD_X_MAX_OBS = 2000
_ATLAS_BASENAMES = frozenset(
    {
        "tabula_sapiens_all.h5ad",
        "tabula_muris_all.h5ad",
    }
)


def _decode_attr(value):
    if isinstance(value, (bytes, bytearray)):
        return value.decode()
    return value


def _read_axis_count(group):
    index_key = _decode_attr(group.attrs.get("_index", "_index")) or "_index"
    if index_key in group:
        return int(group[index_key].shape[0])
    if "_index" in group:
        return int(group["_index"].shape[0])
    if "index" in group:
        return int(group["index"].shape[0])
    raise KeyError("obs/var group has no index dataset")


def _read_counts(path):
    with h5py.File(path, "r") as handle:
        n_obs = _read_axis_count(handle["obs"])
        n_vars = _read_axis_count(handle["var"]) if "var" in handle else None
    return n_obs, n_vars


class DatasetHandle:
    """Obs-only handle. n_obs comes from h5py. load_X is for a small named slice."""

    def __init__(self, path: str):
        self.path = os.fspath(path)
        self.n_obs, self.n_vars = _read_counts(self.path)
        print(f"DatasetHandle n_obs={self.n_obs} n_vars={self.n_vars} path={self.path}")

    def obs_categories(self, column: str):
        with h5py.File(self.path, "r") as handle:
            if column not in handle["obs"]:
                raise KeyError(f"{self.path} obs has no column {column!r}")
            node = handle["obs"][column]
            if not isinstance(node, h5py.Group) or "categories" not in node:
                raise TypeError(f"{self.path} obs[{column!r}] is not categorical")
            cats = node["categories"][:]
        return [
            item.decode() if isinstance(item, (bytes, bytearray)) else str(item)
            for item in cats
        ]

    def load_X(self):
        basename = os.path.basename(self.path)
        if basename in _ATLAS_BASENAMES or self.n_obs > _LOAD_X_MAX_OBS:
            raise RuntimeError(
                f"load_X is only for a named small slice; refused {self.path} "
                f"n_obs={self.n_obs}"
            )
        return sc.read_h5ad(self.path)


class AbstractModel(abc.ABC):
    @abc.abstractmethod
    def setup(self):
        raise NotImplementedError

    @abc.abstractmethod
    def train(self):
        raise NotImplementedError

    @abc.abstractmethod
    def predict(self):
        raise NotImplementedError


class AbstractEvaluation(abc.ABC):
    @abc.abstractmethod
    def evaluate(self, model, test_data):
        raise NotImplementedError


class TrainingData:
    def __init__(self, source_training_data_path: str, target_training_data_path: str):
        self.source_training_data_path = source_training_data_path
        self.target_training_data_path = target_training_data_path
        self.source = DatasetHandle(source_training_data_path)
        self.target = DatasetHandle(target_training_data_path)

    @property
    def source_adata(self):
        return self.source.load_X()

    @property
    def target_adata(self):
        return self.target.load_X()


class TestData:
    def __init__(self, source_test_data_path: str, target_test_data_path: str):
        self.source_test_data_path = source_test_data_path
        self.target_test_data_path = target_test_data_path
        self.batch_corrected = False
        self.source = DatasetHandle(source_test_data_path)
        self.target = DatasetHandle(target_test_data_path)

    @property
    def source_adata(self):
        return self.source.load_X()

    @property
    def target_adata(self):
        return self.target.load_X()


class Experiment:
    def __init__(self, experiment_spec_path: str, frozen_ae=None):
        self.experiment_spec_path = experiment_spec_path
        self.experiment_spec = self.load_experiment_spec()
        self.training_data = None
        self.test_data = None
        self.models = []
        self.evaluations = []
        self.frozen_ae = frozen_ae

    @classmethod
    def from_spec(cls, path, frozen_ae=None):
        return cls(path, frozen_ae=frozen_ae)

    def load_experiment_spec(self):
        with open(self.experiment_spec_path, "r") as f:
            return yaml.safe_load(f)

    def setup(self):
        spec = self.experiment_spec
        models = spec.get("models") or []
        if "CellOTModel" in models and self.frozen_ae is None:
            raise FileNotFoundError("missing FrozenAE handle")
        self.training_data = TrainingData(
            spec["training_data"]["source_training_data_path"],
            spec["training_data"]["target_training_data_path"],
        )
        self.test_data = TestData(
            spec["test_data"]["source_test_data_path"],
            spec["test_data"]["target_test_data_path"],
        )
        if "IdentityModel" in models:
            self.models.append(IdentityModel())
        if "AutoEncoderModel" in models:
            from .ae import AutoEncoderModel

            self.models.append(AutoEncoderModel(self.experiment_spec_path))
        if "CellOTModel" in models:
            from .cellot_model import CellOTModel

            self.models.append(CellOTModel(self.experiment_spec_path, frozen_ae=self.frozen_ae))
        self.evaluations.append(DummyEvaluation())
        for model in self.models:
            model.setup()

    def train(self):
        for model in self.models:
            model.train()

    def predict(self):
        outputs = []
        for model in self.models:
            outputs.append(model.predict(self.test_data))
        return outputs[-1] if outputs else None

    def evaluate(self):
        results = []
        for model in self.models:
            for evaluation in self.evaluations:
                results.append(evaluation.evaluate(model, self.test_data))
        return results[-1] if results else None


class IdentityModel(AbstractModel):
    """No-transport ceiling. predict returns source cells as if they were the target."""

    def setup(self):
        pass

    def train(self):
        pass

    def predict(self, test_data: TestData):
        return test_data.source.load_X()


class DummyEvaluation(AbstractEvaluation):
    def evaluate(self, model, test_data):
        return 1

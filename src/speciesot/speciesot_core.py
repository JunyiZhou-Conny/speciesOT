import abc
import yaml
from typing import List
import scanpy as sc
import numpy as np
import pandas as pd


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
    def evaluate(self):
        raise NotImplementedError


class TrainingData(abc.ABC):
    def __init__(self, source_training_data_path: str, target_training_data_path: str):
        self.source_training_data_path = source_training_data_path
        self.target_training_data_path = target_training_data_path
        self.source_adata = sc.read_h5ad(source_training_data_path)
        self.target_adata = sc.read_h5ad(target_training_data_path)


class TestData(abc.ABC):
    def __init__(self, source_test_data_path: str, target_test_data_path: str):
        self.source_test_data_path = source_test_data_path
        self.target_test_data_path = target_test_data_path
        self.batch_corrected = False
        self.source_adata = sc.read_h5ad(source_test_data_path)
        self.target_adata = sc.read_h5ad(target_test_data_path)


class Experiment(abc.ABC):
    def __init__(self, experiment_spec_path: str):
        self.experiment_spec_path = experiment_spec_path
        self.experiment_spec = self.load_experiment_spec()
        self.training_data = None
        self.test_data = None
        self.models = []
        self.evaluations = []

    def load_experiment_spec(self):
        with open(self.experiment_spec_path, 'r') as f:
            return yaml.safe_load(f)

    def setup(self):
        # set up training data
        self.training_data = TrainingData(self.experiment_spec['training_data']['source_training_data_path'], self.experiment_spec['training_data']['target_training_data_path'])

        # set up test data
        self.test_data = TestData(self.experiment_spec['test_data']['source_test_data_path'], self.experiment_spec['test_data']['target_test_data_path'])

        # set up models
        if 'IdentityModel' in self.experiment_spec['models']:
            self.models.append(IdentityModel())

        for model in self.models:
            model.setup()

    def train(self):
        for model in self.models:
            model.train()

    def predict(self):
        for model in self.models:
            model.predict(self.test_data)

    def evaluate(self):
        for model in self.models:
            for evaluation in self.evaluations:
                evaluation.evaluate(model, self.test_data)


class IdentityModel(AbstractModel):
    def setup(self):
        pass

    def train(self):
        pass

    def predict(self, test_data: TestData):
        return test_data.source_adata


class DummyEvaluation(AbstractEvaluation):
    def evaluate(self):
        return 1




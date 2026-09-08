import abc
import yaml
from typing import List
import scanpy as sc
import numpy as np
import pandas as pd
import anndata as ad


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
    def evaluate(self, predicted: ad.AnnData, truth: ad.AnnData):
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
        self.predictions = []

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

        # set up models
        if 'R2Evaluation' in self.experiment_spec['evaluations']:
            self.evaluations.append(R2Evaluation())
            

    def train(self):
        for model in self.models:
            model.train()

    def predict(self):
        for model in self.models:
            p = model.predict(self.test_data) # p is an anndate object
            self.predictions.append(p)
        

    def evaluate(self):
        for p in self.predictions:
            for evaluation in self.evaluations:
                # Should it be predicted data set
                evaluation.evaluate(p, self.test_data.target_adata)
            


class IdentityModel(AbstractModel):
    def setup(self):
        pass

    def train(self):
        pass

    def predict(self, test_data: TestData):
        return test_data.source_adata


class DummyEvaluation(AbstractEvaluation):
    def evaluate(self, predicted: ad.AnnData, truth: ad.AnnData):
        return 1


class R2Evaluation(AbstractEvaluation):
    # Parent class no longer abstract, constructor inherited

    def evaluate(self, predicted: ad.AnnData, truth: ad.AnnData):
        # Check class inheritance
        # Chance that X is a sparse matrix
        a = predicted.X - predicted.X.mean(0)
        b = truth.X - truth.X.mean(0)
        numerator = (a * b).sum(0)
        denominator = np.sqrt((a**2).sum(0) * (b**2).sum(0))
        valid = denominator > 1e-12
        return float(np.mean((numerator[valid] / denominator[valid]) ** 2))



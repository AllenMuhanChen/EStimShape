from abc import ABC, abstractmethod
from sklearn.decomposition import PCA
from sklearn.manifold import MDS
import numpy as np


class DimensionalityReducer(ABC):
    def __init__(self, n_components: int = 2):
        self.n_components = n_components

    @abstractmethod
    def fit_transform(self, X: np.ndarray):
        pass

    @abstractmethod
    def get_name(self):
        pass


class PCAReducer(DimensionalityReducer):
    def fit_transform(self, X: np.ndarray):
        self.model = PCA(n_components=self.n_components)
        return self.model.fit_transform(X)

    def get_name(self):
        return "PCA"


class MDSReducer(DimensionalityReducer):
    def fit_transform(self, X: np.ndarray):
        self.model = MDS(n_components=self.n_components)
        return self.model.fit_transform(X)

    def get_name(self):
        return "MDS"
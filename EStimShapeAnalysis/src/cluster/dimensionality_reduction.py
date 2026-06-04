from abc import ABC, abstractmethod
from sklearn.decomposition import PCA, KernelPCA, SparsePCA
from sklearn.manifold import MDS, TSNE
import numpy as np


class DimensionalityReducer(ABC):
    def __init__(self, n_components: int = 2):
        self.n_components = n_components

    @abstractmethod
    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def get_name(self) -> str:
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


class TSNEReducer(DimensionalityReducer):
    def fit_transform(self, X: np.ndarray):
        self.model = TSNE(n_components=self.n_components)
        return self.model.fit_transform(X)

    def get_name(self):
        return "TSNE"


class KernelPCAReducer(DimensionalityReducer):
    def fit_transform(self, X: np.ndarray):
        self.model = KernelPCA(n_components=self.n_components, kernel='rbf')
        return self.model.fit_transform(X)

    def get_name(self):
        return "KernelPCA"


class SparsePCAReducer(DimensionalityReducer):
    def __init__(self, n_components: int = 2, alpha: float = 1.0):
        super().__init__(n_components=n_components)
        self.alpha = alpha

    def fit_transform(self, X: np.ndarray):
        self.model = SparsePCA(n_components=self.n_components, alpha=self.alpha)
        return self.model.fit_transform(X)

    def get_name(self):
        return "SparsePCA"

from abc import ABC, abstractmethod
from sklearn.decomposition import PCA, KernelPCA, SparsePCA
from sklearn.manifold import MDS, TSNE
import numpy as np


class DimensionalityReducer(ABC):
    # Upper bound on how many components this reducer can produce. None means
    # "no explicit cap" (limited only by the data dimensions). Subclasses that
    # cannot go arbitrarily high (e.g. TSNE) override this.
    max_components: int | None = None

    def __init__(self, n_components: int = 2):
        self.n_components = n_components

    @abstractmethod
    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        pass

    @abstractmethod
    def get_name(self) -> str:
        pass

    def get_explained_variance_ratio(self) -> np.ndarray | None:
        """Return the fraction of variance explained by each computed component,
        or None if this reducer does not expose such a quantity (e.g. MDS, TSNE).

        Used by the GUI to draw the "variance explained per PC" plot.
        """
        return None


class PCAReducer(DimensionalityReducer):
    def fit_transform(self, X: np.ndarray):
        self.model = PCA(n_components=self.n_components)
        return self.model.fit_transform(X)

    def get_name(self):
        return "PCA"

    def get_explained_variance_ratio(self):
        model = getattr(self, "model", None)
        if model is None:
            return None
        return model.explained_variance_ratio_


class MDSReducer(DimensionalityReducer):
    def fit_transform(self, X: np.ndarray):
        self.model = MDS(n_components=self.n_components)
        return self.model.fit_transform(X)

    def get_name(self):
        return "MDS"


class TSNEReducer(DimensionalityReducer):
    # The default (Barnes-Hut) TSNE only supports up to 3 output dimensions.
    max_components = 3

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

    def get_explained_variance_ratio(self):
        model = getattr(self, "model", None)
        eigenvalues = getattr(model, "eigenvalues_", None)
        if eigenvalues is None or len(eigenvalues) == 0:
            return None
        total = float(np.sum(eigenvalues))
        if total <= 0:
            return None
        return np.asarray(eigenvalues) / total


class SparsePCAReducer(DimensionalityReducer):
    def __init__(self, n_components: int = 2, alpha: float = 1.0):
        super().__init__(n_components=n_components)
        self.alpha = alpha

    def fit_transform(self, X: np.ndarray):
        self.model = SparsePCA(n_components=self.n_components, alpha=self.alpha)
        return self.model.fit_transform(X)

    def get_name(self):
        return "SparsePCA"

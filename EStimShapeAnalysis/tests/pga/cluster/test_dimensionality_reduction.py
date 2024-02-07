import unittest
import matplotlib.pyplot as plt
from sklearn.datasets import make_blobs
from sklearn.metrics import silhouette_score

from pga.gui.cluster import PCAReducer, MDSReducer

# Generate 3-dimensional dataset
X, y = make_blobs(n_samples=100, centers=3, n_features=3, random_state=42)


class TestDimensionalityReducers(unittest.TestCase):
    def test_pca(self):
        pca = PCAReducer(n_components=2)
        print(X.shape)
        reduced_data = pca.fit_transform(X)

        # Verify that the output has the correct shape
        self.assertEqual(reduced_data.shape, (100, 2))

        # Compute silhouette score
        score = silhouette_score(reduced_data, y)
        print(f'PCA silhouette score: {score}')

        plt.scatter(reduced_data[:, 0], reduced_data[:, 1], c=y)
        plt.title('PCA Dimensionality Reduction')
        plt.show()

    def test_mds(self):
        mds = MDSReducer(n_components=2)
        reduced_data = mds.fit_transform(X)

        # Verify that the output has the correct shape
        self.assertEqual(reduced_data.shape, (100, 2))

        # Compute silhouette score
        score = silhouette_score(reduced_data, y)
        print(f'MDS silhouette score: {score}')

        plt.scatter(reduced_data[:, 0], reduced_data[:, 1], c=y)
        plt.title('MDS Dimensionality Reduction')
        plt.show()



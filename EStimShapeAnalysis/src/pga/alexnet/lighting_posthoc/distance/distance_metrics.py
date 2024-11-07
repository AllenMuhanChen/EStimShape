import random
from abc import ABC, abstractmethod
from enum import Enum

import numpy as np
import ot
from matplotlib import pyplot as plt


class DistanceMetric(ABC):
    """Abstract base class for distance metrics"""

    @abstractmethod
    def compute_distance(self, arr1: np.ndarray, arr2: np.ndarray) -> float:
        """Compute distance between two arrays"""
        pass

    @abstractmethod
    def normalize_array(self, arr: np.ndarray) -> np.ndarray:
        """Normalize input array for distance computation"""
        pass


class EMDMetric(DistanceMetric):

    def __init__(self, n_shuffles: int = 3):
        self.n_shuffles = n_shuffles

    def normalize_array(self, arr: np.ndarray) -> np.ndarray:
        return arr / arr.max()

    def compute_distance(self, arr1: np.ndarray, arr2: np.ndarray) -> float:
        if arr1.size == 0 or arr2.size == 0:
            return np.nan

        # Normalize arrays
        arr1_norm = self.normalize_array(arr1)
        arr2_norm = self.normalize_array(arr2)

        # Calculate EMD
        emd = ot.sliced_wasserstein_distance(arr1_norm, arr2_norm)

        # Normalize by shuffle distance
        shuffle_dist1 = self._calculate_shuffle_distance(arr1_norm)
        shuffle_dist2 = self._calculate_shuffle_distance(arr2_norm)
        normalization_factor = (shuffle_dist1 + shuffle_dist2) / 2

        return emd / normalization_factor if normalization_factor > 0 else np.nan

    def _calculate_shuffle_distance(self, arr: np.ndarray) -> float:
        distances = []
        for _ in range(self.n_shuffles):
            shuffled = arr.copy()
            non_zero_mask = shuffled > 0
            non_zero_values = shuffled[non_zero_mask]
            np.random.shuffle(non_zero_values)
            shuffled[non_zero_mask] = non_zero_values
            # if random.random() < 0.001:
            #     plt.imshow(shuffled)
            #     plt.show()
            distance = ot.sliced_wasserstein_distance(arr, shuffled)
            distances.append(distance)
        return np.mean(distances)


class OverlapMetric(DistanceMetric):

    def __init__(self, threshold: float = 0.01, spatial_tolerance: int = 1):
        self.threshold = threshold
        self.spatial_tolerance = spatial_tolerance

    def normalize_array(self, arr: np.ndarray) -> np.ndarray:
        return arr / arr.max()

    def compute_distance(self, arr1: np.ndarray, arr2: np.ndarray) -> float:
        if arr1.size == 0 or arr2.size == 0:
            return np.nan

        # Normalize arrays
        arr1_norm = self.normalize_array(arr1)
        arr2_norm = self.normalize_array(arr2)

        # Get active pixels
        active1 = set((x, y) for x, y in zip(*np.where(arr1_norm > self.threshold)))
        active2 = set((x, y) for x, y in zip(*np.where(arr2_norm > self.threshold)))

        # Count matches
        matches = 0
        total_active = len(active1) + len(active2)

        if total_active == 0:
            return 0.0

        for p1 in active1:
            for p2 in active2:
                if (abs(p1[0] - p2[0]) <= self.spatial_tolerance and
                        abs(p1[1] - p2[1]) <= self.spatial_tolerance):
                    matches += 1
                    break

        for p2 in active2:
            for p1 in active1:
                if (abs(p1[0] - p2[0]) <= self.spatial_tolerance and
                        abs(p1[1] - p2[1]) <= self.spatial_tolerance):
                    matches += 1
                    break

        # Return similarity score (convert to distance by subtracting from 1)
        percent_overlap = matches / total_active
        return percent_overlap

class WeightedOverlapMetric(OverlapMetric):
    def compute_distance(self, arr1: np.ndarray, arr2: np.ndarray) -> float:
        if arr1.size == 0 or arr2.size == 0:
            return np.nan

        # Normalize arrays
        arr1_norm = self.normalize_array(arr1)
        arr2_norm = self.normalize_array(arr2)

        # Get active pixels
        active1 = set((x, y) for x, y in zip(*np.where(arr1_norm > self.threshold)))
        active2 = set((x, y) for x, y in zip(*np.where(arr2_norm > self.threshold)))

        # Count matches
        contribution_weighted_sum = 0
        total_active = len(active1) + len(active2)

        if total_active == 0:
            return 0.0

        for p1 in active1:
            for p2 in active2:
                if (abs(p1[0] - p2[0]) <= self.spatial_tolerance and
                        abs(p1[1] - p2[1]) <= self.spatial_tolerance):
                    contribution_weighted_sum += arr1_norm[p1[0], p1[1]]
                    break

        for p2 in active2:
            for p1 in active1:
                if (abs(p1[0] - p2[0]) <= self.spatial_tolerance and
                        abs(p1[1] - p2[1]) <= self.spatial_tolerance):
                    contribution_weighted_sum += arr2_norm[p2[0], p2[1]]
                    break

        # Return similarity score (convert to distance by subtracting from 1)

        return contribution_weighted_sum


class DistanceType(Enum):
    EMD = "emd"
    OVERLAP = "overlap"
    WEIGHTED_OVERLAP = "weighted overlap"

from math import pi, fabs
import random
from unittest import TestCase

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from src.analysis.rwa import rwa, Binner, generate_point_matrices, smooth_matrices, \
    RWAMatrix, AutomaticBinner, rwa
from src.mockga.mock_rwa_plot import slice_matrix


class Test(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.a_peak = 1
        self.b_peak = 0
        self.num_data_points = 100
        self.stims = self.generate_stim(self.num_data_points)
        self.response_vector = self.generate_resp(self.stims)
        num_bins = 10
        self.binner_for_fields = {"A": Binner(0, 1, num_bins), "B": Binner(0, 2 * pi, num_bins)}
        self.sigma_for_fields = {"A": 0.2, "B": 0.2}
        self.padding_for_fields = {"A": "mirror", "B": "wrap"}

    def high_dim_set_up(self):
        self.a_peak = 1
        self.b_peak = pi
        self.num_data_points = 100
        self.stims = self.generate_stim(self.num_data_points)
        self.response_vector = self.generate_resp(self.stims)
        num_bins = 10
        self.binner_for_fields = {"A": Binner(0, 1, num_bins), "B": Binner(0, 2 * pi, num_bins)}
        self.sigma_for_fields = {"A": 0.2, "B": 0.2}

    def test_padding_strategies(self):
        padding_strategies = ["reflect", "wrap", "mirror", "constant", "nearest"]
        fig, axes = plt.subplots(len(padding_strategies), 2)
        for padding_index, padding_strategy in enumerate(padding_strategies):
            self.padding_for_fields = {"A": padding_strategy, "B": padding_strategy}
            rwa_lin1 = next(
                rwa(self.stims, self.response_vector, self.binner_for_fields, self.sigma_for_fields,
                    self.padding_for_fields))
            self.setUp()
            rwa_lin2 = next(
                rwa(self.stims, self.response_vector, self.binner_for_fields, self.sigma_for_fields,
                    self.padding_for_fields))
            rwa_prod = None
            for lineage_index, r in enumerate([rwa_lin1, rwa_lin2]):
                lineage_rwa = r
                if lineage_index == 0:
                    template = lineage_rwa
                    rwa_prod = np.ones_like(lineage_rwa.matrix)
                rwa_prod = np.multiply(rwa_prod, lineage_rwa.matrix)
            rwa_prod = rwa_lin1.copy_labels(rwa_prod)
            self.draw_A_tuning(rwa_prod, axes[padding_index][0])
            self.draw_B_tuning(rwa_prod, axes[padding_index][1])
            axes[padding_index][1].set_title(padding_strategy)
        plt.show()

    def test_automatic_binner(self):
        num_bins = 10
        self.binner_for_fields = {"x": AutomaticBinner("x", self.stims, num_bins),
                                  "y": AutomaticBinner("y", self.stims, num_bins),
                                  "B": AutomaticBinner("B", self.stims, num_bins)}
        print(self.binner_for_fields["x"].min)
        print(self.binner_for_fields["x"].max)
        print(self.binner_for_fields["B"].min)
        print(self.binner_for_fields["B"].max)
        print(self.binner_for_fields["x"].bins)

    def test_rwa(self):
        response_weighted_average_optimized = next(
            rwa(self.stims, self.response_vector, self.binner_for_fields, self.sigma_for_fields,
                self.padding_for_fields))

        fig, axes = plt.subplots(1, 2)
        self.draw_A_tuning(response_weighted_average_optimized, axes[0])
        self.draw_B_tuning(response_weighted_average_optimized, axes[1])
        plt.show()

    def test_smoothing(self):
        self.stims = [[{"A": {"x": 0, "y": 0.99}, "B": self.generate_rand_b()}]]

        stim_point_matrices = generate_point_matrices(self.stims, self.binner_for_fields, self.sigma_for_fields,
                                                      self.padding_for_fields)
        smoothed_matrices = next(smooth_matrices(stim_point_matrices))
        fig, axes = plt.subplots(1, 2)
        self.draw_A_tuning(smoothed_matrices, axes[0])
        self.draw_B_tuning(smoothed_matrices, axes[1])
        plt.show()

    def generate_resp_for_stim(self, a_list, b_list):
        """Our test neuron cares that A.x is close to 0.5, doesn't care about A.y, and cares that
        B is close to pi"""

        a_distances_from_peak = [(fabs(a["x"] - self.a_peak)) for a in a_list]
        b_distances_from_peak = [(fabs(b - self.b_peak)) for b in b_list]
        a_normalized_distances_from_peak = [a_distance_from_peak / max(1 - self.a_peak, self.a_peak) for
                                            a_distance_from_peak in
                                            a_distances_from_peak]
        b_normalized_distances_from_peak = [b_distance_from_peak / max(2 * pi - self.b_peak, self.b_peak) for
                                            b_distance_from_peak
                                            in b_distances_from_peak]
        a_tunings = [1 - a_normalized_distance_from_peak for a_normalized_distance_from_peak in
                     a_normalized_distances_from_peak]
        b_tunings = [1 - b_normalized_distance_from_peak for b_normalized_distance_from_peak in
                     b_normalized_distances_from_peak]
        total_comps = len(a_tunings) + len(b_tunings)
        normalized_tuning = (sum(a_tunings) + sum(b_tunings)) / total_comps
        return normalized_tuning * 100

    def draw_A_tuning(self, matrix_to_draw, axis: plt.Axes):
        matrix = matrix_to_draw.matrix
        matrix_peak_location = np.unravel_index(np.argsort(matrix, axis=None)[-1:], matrix.shape)

        sliced_matrix = slice_matrix([0, 1], matrix, matrix_peak_location)
        axis.imshow(np.squeeze(np.transpose(sliced_matrix)), extent=[0, 1, 0, 1], origin="lower")
        labels = [label for label, label_indx in matrix_to_draw.names_for_axes.items()]
        axis.set_xlabel(labels[0])
        axis.set_ylabel(labels[1])

    def draw_B_tuning(self, matrix_to_draw, axis):
        matrix = matrix_to_draw.matrix
        matrix_peak_location = np.unravel_index(np.argsort(matrix, axis=None)[-1:], matrix.shape)
        sliced_matrix = slice_matrix(2, matrix, matrix_peak_location)

        bins = self.binner_for_fields["B"].bins
        x_axis = [bin.middle for bin in bins]
        axis.plot(x_axis, np.squeeze(sliced_matrix))
        axis.set_xlabel("B")
        # plt.show()

    def test_generate_resp(self):
        stims = self.generate_stim(100)
        responses = self.generate_resp(stims)
        self.assertTrue(len(responses) == 100)
        self.assertTrue(min(responses) >= 0 and max(responses) <= 100)

    def test_generate_stim(self):
        stims = self.generate_stim(100)
        print(stims)
        self.assertTrue(len(stims) == 100)

    def generate_stim(self, num_data_points):
        stims = []
        for i in range(num_data_points):
            if i % 2 == 0:
                stim_dict = [self.generate_stim_component(), self.generate_stim_component()]
            else:
                stim_dict = [self.generate_stim_component()]
            stims.append(stim_dict)

        return stims

    def generate_resp(self, stims):
        self.num_data_points = 100

        resp_list = []
        for stims in stims:
            a_values_xy = [field_value for component in stims for field_key, field_value in component.items() if
                           field_key == "A"]
            b_values = [field_value for component in stims for field_key, field_value in component.items() if
                        field_key == "B"]
            resp_list.append(self.generate_resp_for_stim(a_values_xy, b_values))
        return resp_list

    def generate_stim_component(self):
        return {"A": self.generate_rand_a(), "B": self.generate_rand_b()}

    def generate_high_dim_stim_component(self):
        return {"A": self.generate_rand_a(), "B": self.generate_rand_b(), "C": self.generate_rand_a(),
                "D": self.generate_rand_b(), "E": self.generate_rand_a()}

    def test_bins(self):
        bins = Binner(0, 1, 10)
        print(bins.bins)

    def generate_rand_b(self):
        return random.uniform(0, 1) * 2 * pi

    def generate_rand_a(self):
        return {"x": random.uniform(0, 1), "y": random.uniform(0, 1)}

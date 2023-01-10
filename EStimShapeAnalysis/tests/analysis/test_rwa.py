from math import pi, fabs
import random
from unittest import TestCase

import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from src.analysis.rwa import rwa, Binner, generate_point_matrices, smooth_matrices, calculate_response_weighted_average, LabelledMatrix


class Test(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.num_data_points = 10
        self.stims = self.generate_stim(self.num_data_points)
        self.response_vector = self.generate_resp(self.stims)
        num_bins = 10
        self.binner_for_field = {"A": Binner(0, 1, num_bins), "B": Binner(0, 2 * pi, num_bins)}

    def test_rwa(self):
        response_weighted_average = rwa(self.stims, self.response_vector, self.binner_for_field)
        print(response_weighted_average)
        self.draw_A_tuning(response_weighted_average)

    def test_smoothing(self):
        stim_point_matrices = generate_point_matrices(self.binner_for_field, self.stims)
        smoothed_matrices = smooth_matrices(stim_point_matrices)
        for stim_indx, smoothed_matrix in enumerate(smoothed_matrices):
            print(self.stims[stim_indx])
            matrix = smoothed_matrix.matrix
            matrix_summed = matrix.sum(1)
            normalized_matrix = np.divide(matrix_summed, matrix.shape[1])
            plt.imshow(np.transpose(normalized_matrix), extent=[0, 1, 0, 2*pi], origin="lower", aspect=1/(2*pi))
            labels = [label for label_indx, label in smoothed_matrix.indices_for_axes.items()]
            plt.xlabel(labels[0])
            plt.ylabel(labels[2])
            plt.colorbar()
            plt.show()
            # self.draw_A_tuning(smoothed_matrix)

    def draw_A_tuning(self, matrix_to_draw):
        matrix = matrix_to_draw.matrix
        print(matrix)
        matrix_summed = matrix.sum(2)
        normalized_matrix = np.divide(matrix_summed, matrix.shape[2])
        plt.imshow(np.transpose(normalized_matrix), extent=[0, 1, 0, 1], origin="lower")
        labels = [label for label, label_indx in matrix_to_draw.indices_for_axes.items()]
        plt.xlabel(labels[0])
        plt.ylabel(labels[1])
        plt.colorbar()
        plt.show()

    def test_point_matrices(self):
        stim_point_matrices = generate_point_matrices(self.binner_for_field, self.stims)

        self.assertTrue(len(stim_point_matrices) == self.num_data_points)
        for stim_indx, point_matrix in enumerate(stim_point_matrices):
            self.assertTrue(point_matrix.matrix.sum() == len(self.stims[stim_indx]))
        self.assertTrue(point_matrix.indices_for_axes["A.x"] == 0)
        self.assertTrue(point_matrix.indices_for_axes["A.y"] == 1)
        self.assertTrue(point_matrix.indices_for_axes["B"] == 2)

    def test_generate_resp(self):
        stims = self.generate_stim(100)
        responses = self.generate_resp(stims)
        self.assertTrue(len(responses) == 100)
        self.assertTrue(min(responses) >= 0 and max(responses) <= 100)

    def test_generate_stim(self):
        stims = self.generate_stim(100)
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

    def test_bins(self):
        bins = Binner(0, 1, 10)
        print(bins.bins)

    def generate_rand_b(self):
        return random.uniform(0, 1) * 2 * pi

    def generate_rand_a(self):
        return {"x": random.uniform(0, 1), "y": random.uniform(0, 1)}

    def generate_resp_for_stim(self, a_list, b_list):
        """Our test neuron cares that A.x is close to 0.5, doesn't care about A.y, and cares that
        B is close to pi"""
        a_peak = 0.5
        b_peak = pi
        a_distances_from_peak = [(fabs(a["x"] - a_peak)) for a in a_list]
        b_distances_from_peak = [(fabs(b - b_peak)) for b in b_list]
        a_normalized_distances_from_peak = [a_distance_from_peak / max(1 - a_peak, a_peak) for a_distance_from_peak in
                                            a_distances_from_peak]
        b_normalized_distances_from_peak = [b_distance_from_peak / max(2 * pi - b_peak, b_peak) for b_distance_from_peak
                                            in b_distances_from_peak]
        a_tunings = [1 - a_normalized_distance_from_peak for a_normalized_distance_from_peak in
                     a_normalized_distances_from_peak]
        b_tunings = [1 - b_normalized_distance_from_peak for b_normalized_distance_from_peak in
                     b_normalized_distances_from_peak]
        total_comps = len(a_tunings) + len(b_tunings)
        normalized_tuning = (sum(a_tunings) + sum(b_tunings)) / total_comps
        return normalized_tuning * 100

from math import pi, fabs
import random
from unittest import TestCase

import numpy as np
import pandas as pd

from src.analysis.rwa import rwa, Bins, generate_point_matrices


class Test(TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.num_data_points = 100
        self.stims = self.generate_stim(self.num_data_points)
        self.resp_list = self.generate_resp(self.stims)
        self.bins_for_field = {"A": Bins(0, 1, 10), "B": Bins(0, 2 * pi, 10)}

    def test_rwa(self):
        rwa(self.stims, self.resp_list, self.bins_for_field)

    def test_point_matrices(self):
        point_matrices = generate_point_matrices(self.bins_for_field, self.stims)

        assert (len(point_matrices) == self.num_data_points)
        for point_matrix in point_matrices:
            assert(point_matrix.sum() == 2)

    def test_generate_resp(self):
        stims = self.generate_stim(100)
        responses = self.generate_resp(stims)
        assert (len(responses) == 100)
        assert (min(responses) >= 0 and max(responses) <= 100)

    def test_generate_stim(self):
        stims = self.generate_stim(100)
        assert (len(stims) == 100)

    def generate_stim(self, num_data_points):
        stims = []
        for i in range(num_data_points):
            stim_dict = [self.generate_stim_component(), self.generate_stim_component()]
            stims.append(stim_dict)

        return stims

    def generate_resp(self, stims):
        self.num_data_points = 100

        resp_list = []
        for stims in stims:
            a_values = [field_value for component in stims for field_key, field_value in component.items() if
                        field_key == "A"]
            b_values = [field_value for component in stims for field_key, field_value in component.items() if
                        field_key == "B"]
            resp_list.append(self.generate_resp_for_stim(a_values, b_values))
        return resp_list

    def generate_stim_component(self):
        return {"A": self.generate_rand_a(), "B": self.generate_rand_b()}

    def test_bins(self):
        bins = Bins(0, 1, 10)
        print(bins.bins)

    def generate_rand_b(self):
        return random.uniform(0, 1) * 2 * pi

    def generate_rand_a(self):
        return random.uniform(0, 1)

    def generate_resp_for_stim(self, a_list, b_list):
        a_peak = 0.5
        b_peak = pi
        a_distances_from_peak = [(fabs(a - a_peak)) for a in a_list]
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

from math import pi
from random import random
from unittest import TestCase

from analysis.ga.rwa import Binner
from analysis.ga.oldmockga import collect_trials
from analysis.ga.oldmockga import condition_theta_and_phi, condition_spherical_angles, condition_for_inside_bins, \
    compile_data
from clat.util.dictionary_util import apply_function_to_subdictionaries_values_with_keys
from clat.util import time_util
from clat.util.connection import Connection


def random_number_between(min, max):
    return min + (max - min) * random()


def is_between(value, lower, upper):
    return lower <= value <= upper


class AngleConditionTest(TestCase):

    def test_condition_theta(self):
        self.test_theta(-3 * pi, -pi)
        self.test_theta(6 * pi, 0)
        self.test_theta(5 * pi, pi)
        self.test_theta(2 * pi, 0)
        self.test_theta(pi + pi / 2, -pi / 2)
        self.test_theta(pi / 2, pi / 2)
        for i in range(1000):
            self.assertTrue(
                is_between(condition_theta_and_phi({"theta": random_number_between(-10, 10), "phi": 0})["theta"], -pi,
                           pi))

    def test_condition_phi(self):
        for i in range(1000):
            self.assertTrue(
                is_between(condition_theta_and_phi({"theta": 0, "phi": random_number_between(-10, 10)})["phi"], 0, pi))

        self.test_phi(2 * pi, 0)
        self.test_phi(pi, pi)
        self.test_phi(0, 0)
        self.test_phi_and_theta(pi, pi + pi / 2, -pi, pi / 2)
        self.test_phi(-pi, pi)
        self.test_phi_and_theta(-pi, -pi / 2, pi, pi / 2)
        self.test_phi_and_theta(-pi, -pi - pi / 2, -pi, pi / 2)

    def test_theta(self, actual_theta, expected_theta):
        self.assertAlmostEqual(condition_theta_and_phi({"theta": actual_theta, "phi": 0})["theta"],
                               {"theta": expected_theta, "phi": 0}["theta"], 3)

    def test_phi(self, actual_phi, expected_phi):
        self.assertAlmostEqual(condition_theta_and_phi({"theta": 0, "phi": actual_phi})["phi"],
                               {"theta": 0, "phi": expected_phi}["phi"], 3)

    def test_phi_and_theta(self, actual_theta, actual_phi, expected_theta, expected_phi):
        self.assertAlmostEqual(condition_theta_and_phi({"theta": actual_theta, "phi": actual_phi})["theta"],
                               {"theta": expected_theta, "phi": expected_phi}["theta"], 3)
        self.assertAlmostEqual(condition_theta_and_phi({"theta": actual_theta, "phi": actual_phi})["phi"],
                               {"theta": expected_theta, "phi": expected_phi}["phi"], 3)


class Test(TestCase):

    def setUp(self) -> None:
        super().setUp()
        # PARAMETERS
        self.conn = Connection("allen_estimshape_dev_221110")
        self.bin_size = 10
        self.binner_for_shaft_fields = {
            "theta": Binner(-pi, pi, self.bin_size),
            "phi": Binner(0, pi, self.bin_size),
            "radialPosition": Binner(0, 100, self.bin_size),
            "length": Binner(0, 200, self.bin_size),
            "curvature": Binner(0, 1, self.bin_size),
            "radius": Binner(0, 20, self.bin_size),
        }

    def test_condition_for_inside_bins(self):
        trial_tstamps = collect_trials(self.conn, time_util.all())
        data = compile_data(self.conn, trial_tstamps[0:2])
        data = condition_spherical_angles(data)
        test_stim = data["Shaft"].iloc[0][0]

        def set_radial_position(d):
            d["radialPosition"] = 1000
            return d

        apply_function_to_subdictionaries_values_with_keys(test_stim, ['radialPosition'],
                                                           set_radial_position)
        for row in data.iterrows():
            print("pre-removal: ", [component["radialPosition"] for component in row[1]["Shaft"]])

        data = condition_for_inside_bins(data, self.binner_for_shaft_fields)
        for row in data.iterrows():
            print("post-removal: ", [component["radialPosition"] for component in row[1]["Shaft"]])

    def test_condition_for_spherical_angles(self):
        trial_tstamps = collect_trials(self.conn, time_util.all())
        data = compile_data(self.conn, trial_tstamps[0:100])
        data = condition_spherical_angles(data)
        for row in data.iterrows():
            print([component["angularPosition"] for component in row[1]["Shaft"]])

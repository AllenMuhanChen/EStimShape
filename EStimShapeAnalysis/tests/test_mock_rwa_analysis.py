from math import pi
from random import random
from unittest import TestCase

from src.mock.mock_rwa_analysis import condition_theta_and_phi


def random_number_between(min, max):
    return min + (max - min) * random()


def is_between(value, lower, upper):
    return lower <= value <= upper


class Test(TestCase):

    def test_condition_theta(self):
        self.test_theta(-3 * pi, -pi)
        self.test_theta(6 * pi, 0)
        self.test_theta(5*pi, pi)
        self.test_theta(2*pi, 0)
        self.test_theta(pi + pi/2, -pi/2)
        self.test_theta(pi/2, pi/2)
        for i in range(1000):
            self.assertTrue(
                is_between(condition_theta_and_phi({"theta": random_number_between(-10, 10), "phi": 0})["theta"], -pi, pi))


    def test_condition_phi(self):
        for i in range(1000):
            self.assertTrue(
                is_between(condition_theta_and_phi({"theta": 0, "phi": random_number_between(-10, 10)})["phi"], 0, pi))

        self.test_phi(2*pi, 0)
        self.test_phi(pi, pi)
        self.test_phi(0, 0)
        self.test_phi_and_theta(pi, pi+pi/2, -pi, pi/2)
        self.test_phi(-pi, pi)
        self.test_phi_and_theta(-pi, -pi/2, pi, pi/2)
        self.test_phi_and_theta(-pi, -pi-pi/2, -pi, pi/2)
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
from math import pi, fabs
import random
from unittest import TestCase

import numpy as np
import pandas as pd

from src.analysis.rwa import rwa, Bins


class Test(TestCase):
    def test_rwa(self):
        numDataPoints = 100

        stim_dict_list = []
        for i in range(numDataPoints):
            stim_dict = {"A": self.genRandA(), "B": self.genRandB()}
            stim_dict_list.append(stim_dict)


        resp_list = []
        for stim in stim_dict_list:
            resp_list.append(self.genResp(stim["A"], stim["B"]))

        bins_for_field = {"A": Bins(0, 1, 10), "B": Bins(0, 2 * pi, 10)}

        rwa(stim_dict_list, resp_list, bins_for_field)


    def test_bins(self):
        bins = Bins(0, 1, 10)
        print(bins.bins)


    def genRandB(self):
        return random.uniform(0, 1) * 2 * pi

    def genRandA(self):
        return random.uniform(0, 1)

    def genResp(self, a, b):
        a_peak = 0.5
        b_peak = pi
        a_distance_from_peak = (fabs(a - a_peak))
        b_distance_fromPeak = (fabs(b - b_peak))
        a_normalized_distance_from_peak = a_distance_from_peak / max(1-a_peak, a_peak)
        b_normalized_distance_from_peak = b_distance_fromPeak / max(2*pi-b_peak, b_peak)
        a_tuning = 1 - a_normalized_distance_from_peak
        b_tuning = 1 - b_normalized_distance_from_peak
        return a_tuning*50 + b_tuning*50

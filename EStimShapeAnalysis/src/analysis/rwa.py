from collections import namedtuple

import numpy as np
import pandas as pd


class Bins:
    def __init__(self, start, end, num_bins):
        self.num_bins = num_bins
        self.end = end
        self.start = start
        self._generate_bins()

    def _generate_bins(self):
        bin_size = (self.end - self.start) / self.num_bins

        # Initialize a list to hold the bin ranges
        bin_ranges = []

        # Iterate over the number of bins
        for i in range(self.num_bins):
            # Calculate the start and end of the bin range
            bin_start = self.start + i * bin_size
            bin_end = bin_start + bin_size
            bin_middle = (bin_start + bin_end) / 2

            # Add the bin range to the list
            BinRange = namedtuple('BinRange', 'start middle end')
            bin_range = BinRange(bin_start, bin_middle, bin_end)
            bin_ranges.append(bin_range)

        # Return the list of bin ranges
        self.bins = bin_ranges

    def assign_bin(self, value) -> (int, tuple):
        for i, bin_range in enumerate(self.bins):
            # Check if the value is within the current bin_range range
            if bin_range.start <= value < bin_range.end:
                # Return the current bin_range range
                return i, bin_range


def rwa(stims: list[dict], resp_vect: list[float], bins_for_field: dict[str, Bins]):
    point_matrices = generate_point_matrices(bins_for_field, stims)
    print(point_matrices)



def generate_point_matrices(bins_for_field: dict[str, Bins], stims) -> list[np.ndarray]:
    point_matrices = []
    for stim_index, stim_dict in enumerate(stims):
        assigned_bins_for_stim = assign_bins_for_stim(bins_for_field, stim_dict)
        point_matrix = generate_point_matrix_for_stim(assigned_bins_for_stim, bins_for_field, stim_dict)
        point_matrices.append(point_matrix)

    return point_matrices


def generate_point_matrix_for_stim(assigned_bins_for_stim, bins, stim_dict):
    number_bins = [bins[data_key].num_bins for data_key, data_value in stim_dict.items()]
    point_matrix = np.zeros(number_bins)
    bin_indices_for_stim = tuple([assigned_bin[0] for assigned_bin in assigned_bins_for_stim])
    point_matrix[bin_indices_for_stim] = 1
    return point_matrix


def assign_bins_for_stim(bins, stim_dict) -> list[(int, Bins)]:
    assigned_bins_for_stim = [bins[data_key].assign_bin(data_value) for data_key, data_value in stim_dict.items()]
    return assigned_bins_for_stim




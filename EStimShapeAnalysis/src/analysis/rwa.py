from collections import namedtuple

import numpy as np
import pandas as pd


class Binner:
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


def rwa(stims: list[list[dict]], resp_vect: list[float], binner_for_field: dict[str, Binner]):
    """stims are list[list[dict]]: each stim can have one or more component. Each component's data
    is represented by a dictionary. Each component for a stim should have the same data field keys/names
    (but not data values)

    If a stim only has one component, put it in a list still!"""

    point_matrices = generate_point_matrices(binner_for_field, stims)
    print(point_matrices)


def generate_point_matrices(binner_for_field: dict[str, Binner], stims: list[list[dict]]) -> list[np.ndarray]:
    """For each stimulus, generates a Stimulus Point Matrix.
    Each Stim Point Matrix is the summation of multiple Component Point Matrices.

    Each Component Point Matrix is a matrix whose dimensions represent the data fields
    for that component/stimulus.

    The size of each dimension of a point matrix is equal to the number of bins assigned to the data field
    represented by that dimension.

    Each Component Matrix is composed of zeros everywhere, except with a 1
    At the location that represents the bins assigned to that component"""
    stim_point_matrices = []

    # For each stimulus
    for stim_index, stim_components in enumerate(stims):
        axes, component_point_matrix = initialize_point_matrix(binner_for_field, stim_components)
        # For each component of the stimulus
        for component in stim_components:
            assigned_bins_for_component = assign_bins_for_component(binner_for_field, component)
            component_point_matrix = append_point_to_component_matrix(component_point_matrix,
                                                                      assigned_bins_for_component)
        stim_point_matrices.append(component_point_matrix)

    return axes, stim_point_matrices


def initialize_point_matrix(binner_for_field: dict[str, Binner], stim_components: list[dict]):
    """Initialize a zero matrix with a number of dimensions equal to the number of data fields.
    Each dimension has size equal to the number of bins specified for that field. """
    number_bins_for_each_field = [binner_for_field[field_key].num_bins for field_key, field_value in
                                  stim_components[0].items()]
    point_matrix = np.zeros(number_bins_for_each_field)
    axes = {field_key: index for index, (field_key, field_value) in enumerate(stim_components[0].items())}

    return axes, point_matrix


def assign_bins_for_component(binner_for_field: dict[str, Binner], component: dict) -> list[(int, Binner)]:
    """Assigns the values of every data field to a bin for a single component.
    Returns a list of tuples: (index, (min, middle, max)). One element per field """
    assigned_bin_for_component = [binner_for_field[field_key].assign_bin(field_value) for field_key, field_value in
                                  component.items()]
    return assigned_bin_for_component


def append_point_to_component_matrix(component_point_matrix: np.ndarray,
                                     assigned_index_and_bin_for_each_component: list[tuple[int, Binner]]) -> np.ndarray:
    """Sums onto component_point_matrix a 1 at the specified location (location = bins for a component)"""
    bin_indices_for_component = tuple(
        [assigned_index_and_bin[0] for assigned_index_and_bin in assigned_index_and_bin_for_each_component])
    component_point_matrix[bin_indices_for_component] += 1
    return component_point_matrix

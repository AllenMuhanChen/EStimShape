from __future__ import annotations

import inspect
from dataclasses import dataclass
from collections import namedtuple
from typing import Callable
import numpy as np
from scipy.ndimage.filters import gaussian_filter


@dataclass
class LabelledMatrix:
    indices_for_axes: dict[int, str]
    matrix: np.ndarray
    binners_for_axes: dict[int, Binner]

    def apply(self, func: Callable, *args, **kwargs) -> LabelledMatrix:
        """apply a function to self.matrix and return a LabelledMatrix with the new
        matrix"""
        return LabelledMatrix(self.indices_for_axes, func(self.matrix, *args, **kwargs), self.binners_for_axes)


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
            if bin_range.start <= float(value) < bin_range.end:
                # Return the current bin_range range
                return i, bin_range

        raise Exception("Value not in range: " + str(value) + " not in " + self.start + " to " + self.end)


def rwa(stims: list[list[dict]], response_vector: list[float], binner_for_field: dict[str, Binner]):
    """stims are list[list[dict]]: each stim can have one or more component. Each component's data
    is represented by a dictionary. Each data field within a component can be a number OR a dictionary.

    Each component for a stim should have the same data field keys/names
    (but not data values)

    If a stim only has one component, put it in a list still!"""

    point_matrices = generate_point_matrices(binner_for_field, stims)

    smoothed_matrices = smooth_matrices(point_matrices)

    response_weighted_average = calculate_response_weighted_average(smoothed_matrices, response_vector)
    # normalized_rwa = normalize_matrix(response_weighted_average)

    return response_weighted_average


def generate_point_matrices(binner_for_field: dict[str, Binner], stims: list[list[dict]]) -> list[LabelledMatrix]:
    """For each stimulus, generates a Stimulus Point Matrix.
    Each Stim Point Matrix is the summation of multiple Component Point Matrices.

    Each Component Point Matrix is a matrix whose dimensions represent the data fields
    for that component/stimulus.

    The size of each dimension of a point matrix is equal to the number of bins assigned to the data field
    represented by that dimension.

    Each Component Matrix is composed of zeros everywhere, except with a 1
    At the location that represents the bins assigned to that component"""
    print("Generating Point Matrices")
    # For each stimulus
    for stim_index, stim_components in enumerate(stims):
        stim_point_matrix = generate_stim_point_matrix(binner_for_field, stim_components)
        yield stim_point_matrix


def generate_stim_point_matrix(binner_for_field, stim_components):
    component_point_matrix = initialize_point_matrix(binner_for_field, stim_components)
    # For each component of the stimulus
    for component in stim_components:
        assigned_bins_for_component = assign_bins_for_component(binner_for_field, component)
        component_point_matrix = append_point_to_component_matrix(component_point_matrix,
                                                                  assigned_bins_for_component)
    return component_point_matrix


def initialize_point_matrix(binner_for_field: dict[str, Binner], stim_components: list[dict]):
    """Initialize a zero matrix with a number of dimensions equal to the number of data fields.
    Each dimension has size equal to the number of bins specified for that field.

    If a data field has multi-dimensions (i.e x,y position), then this will automatically unpack that.
    Currently, the multidimensional data field must be a dict for this to work.

    The total number of dimensions of this matrix will be equal to the total dimensionality of the data.

    Currently only unpacks one level deep"""
    # number_bins_for_each_field = [binner_for_field[field_key].num_bins for field_key, field_value in
    #                               stim_components[0].items()]

    number_bins_for_each_field = []
    axes = {}
    binner = {}
    total_field_index = 0
    for field_key, field_value in stim_components[0].items():
        if type(field_value) is not dict:
            number_bins_for_each_field.append(binner_for_field[field_key].num_bins)
            axes[total_field_index] = field_key
            binner[total_field_index] = binner_for_field[field_key]
            total_field_index += 1
        else:
            for sub_field_key, sub_field_value in field_value.items():
                try:
                    number_bins_for_each_field.append(binner_for_field[field_key].num_bins)
                    binner[total_field_index] = binner_for_field[field_key]
                except:
                    number_bins_for_each_field.append(binner_for_field[sub_field_key].num_bins)
                    binner[total_field_index] = binner_for_field[sub_field_key]

                axes[total_field_index] = field_key + "." + sub_field_key

                total_field_index += 1

    point_matrix = np.zeros(number_bins_for_each_field)
    return LabelledMatrix(axes, point_matrix, binner)


def assign_bins_for_component(binner_for_field: dict[str, Binner], component: dict) -> list[(int, Binner)]:
    """Assigns the values of every data field to a bin for a single component.
    Returns a list of tuples: (index, (min, middle, max)). One element per field.

     If a data field is multidimensional, will automatically unpack (must be a dict)"""
    assigned_bin_for_component = []
    for field_key, field_value in component.items():
        if type(field_value) is not dict:
            assigned_bin_for_component.append(binner_for_field[field_key].assign_bin(field_value))
        else:
            for sub_field_key, sub_field_value in field_value.items():
                try:
                    assigned_bin_for_component.append(binner_for_field[field_key].assign_bin(sub_field_value))
                except:
                    assigned_bin_for_component.append(binner_for_field[sub_field_key].assign_bin(sub_field_value))

    return assigned_bin_for_component


def append_point_to_component_matrix(component_point_matrix: LabelledMatrix,
                                     assigned_index_and_bin_for_each_component: list[
                                         tuple[int, Binner]]) -> LabelledMatrix:
    """Sums onto component_point_matrix a 1 at the specified location (location = bins for a component)"""
    bin_indices_for_component = tuple(
        [assigned_index_and_bin[0] for assigned_index_and_bin in assigned_index_and_bin_for_each_component])
    component_point_matrix.matrix[bin_indices_for_component] += 1
    return component_point_matrix


def smooth_matrices(labelled_matrices: list[LabelledMatrix]) -> list[LabelledMatrix]:
    print("Smoothing Point Matrices")
    for matrix_number, labelled_matrix in enumerate(labelled_matrices):
        print("smoothing matrix #", matrix_number + 1)
        sigmas = [binner.num_bins / 7 for axes_name, binner in labelled_matrix.binners_for_axes.items()]
        smoothed_matrix = labelled_matrix.apply(gaussian_filter, sigmas, truncate=7)
        yield smoothed_matrix


def calculate_response_weighted_average(labelled_matrices: list[LabelledMatrix],
                                        response_vector: list[float]) -> LabelledMatrix:
    print("Calculating RWA")
    for stim_index, labelled_matrix in enumerate(labelled_matrices):
        print("Response weighting matrix for stimulus: ", stim_index + 1)

        response = response_vector[stim_index]
        (unweighted_stim_matrix, response_weighted_stim_matrix) = response_weigh_matrices(labelled_matrix, response)

        if stim_index == 0:
            axes = labelled_matrix.indices_for_axes
            binners = labelled_matrix.binners_for_axes
            response_weighted_sum_matrix = np.zeros(response_weighted_stim_matrix.matrix.shape)
            unweighted_sum_matrix = np.zeros(unweighted_stim_matrix.matrix.shape)

        response_weighted_sum_matrix = np.add(response_weighted_sum_matrix, response_weighted_stim_matrix.matrix)
        unweighted_sum_matrix = np.add(unweighted_sum_matrix, unweighted_stim_matrix.matrix)

    response_weighted_average = np.divide(response_weighted_sum_matrix, unweighted_sum_matrix)
    return LabelledMatrix(axes, response_weighted_average, binners)


def response_weigh_matrices(labelled_matrix, response) -> (LabelledMatrix, LabelledMatrix):
    unweighted_matrix = labelled_matrix
    response_weighted_matrix = unweighted_matrix.apply(response_weigh_matrix, response)
    return unweighted_matrix, response_weighted_matrix


def response_weigh_matrix(matrix, response):
    return matrix * response


def normalize_matrix(labelled_matrix: LabelledMatrix):
    max_val = np.amax(labelled_matrix.matrix)
    normalized_matrix = labelled_matrix.apply(np.divide(), max_val)
    return normalized_matrix

from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from collections import namedtuple
import time
from typing import Callable, List, Any
import numpy as np
import scipy
from numpy import float32
from scipy.ndimage import fourier_gaussian
from scipy.ndimage.filters import gaussian_filter


@dataclass
class LabelledMatrix:
    indices_for_axes: dict[int, str]
    matrix: np.ndarray
    binners_for_axes: dict[int, Binner]
    sigmas_for_axes: dict[int, float]

    def apply(self, func: Callable, *args, **kwargs) -> LabelledMatrix:
        """apply a function to self.matrix and return a LabelledMatrix with the new
        matrix"""
        return LabelledMatrix(self.indices_for_axes, func(self.matrix, *args, **kwargs), self.binners_for_axes, self.sigmas_for_axes)

    def copy_labels(self, matrix: np.ndarray) -> LabelledMatrix:
        """copy the labels from self to a new LabelledMatrix with the given matrix"""
        return LabelledMatrix(self.indices_for_axes, matrix, self.binners_for_axes, self.sigmas_for_axes)


class Binner:
    def __init__(self, start: float, end: float, num_bins: int):
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

        raise Exception("Value not in range: " + str(value) + " not in " + str(self.start) + " to " + str(self.end))


def rwa(stims: list[list[dict]], response_vector: list[float], binner_for_field: dict[str, Binner], sigma_for_field: dict[str, float]):
    """stims are list[list[dict]]: each stim can have one or more component. Each component's data
    is represented by a dictionary. Each data field within a component can be a number OR a dictionary.

    Each component for a stim should have the same data field keys/names
    (but not data values)

    If a stim only has one component, put it in a list still!

    sigma_for_fields is expressed as a percentage of the number of bins for that dimension
    """

    point_matrices = generate_point_matrices(stims, binner_for_field, sigma_for_field)

    smoothed_matrices = smooth_matrices(point_matrices)

    response_weighted_average = calculate_response_weighted_average(smoothed_matrices, response_vector)
    # normalized_rwa = normalize_matrix(response_weighted_average)

    yield from response_weighted_average


def generate_point_matrices(stims: list[list[dict]], binner_for_field: dict[str, Binner], sigma_for_field: dict[str, float]) -> list[LabelledMatrix]:
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
        stim_point_matrix = generate_stim_point_matrix(stim_components, binner_for_field, sigma_for_field)
        yield stim_point_matrix


def generate_stim_point_matrix(stim_components, binner_for_field, sigma_for_field):
    component_point_matrix = initialize_point_matrix(stim_components, binner_for_field, sigma_for_field)
    # For each component of the stimulus
    for component in stim_components:
        assigned_bins_for_component = assign_bins_for_component(binner_for_field, component)
        component_point_matrix = append_point_to_component_matrix(component_point_matrix,
                                                                  assigned_bins_for_component)
    return component_point_matrix


def initialize_point_matrix(stim_components: list[dict], binner_for_field: dict[str, Binner], sigma_for_field: dict[str, float]) -> LabelledMatrix:
    """Initialize a zero matrix with a number of dimensions equal to the number of data fields.
    Each dimension has size equal to the number of bins specified for that field.

    If a data field has multi-dimensions (i.e x,y position), then this will automatically unpack that.
    Currently, the multidimensional data field must be a dict for this to work.

    The total number of dimensions of this matrix will be equal to the total dimensionality of the data.

    Currently only unpacks one level deep"""
    number_bins_for_each_field = []
    axes = {}
    binner = {}
    sigma = {}
    total_field_index = 0
    for field_key, field_value in stim_components[0].items():
        if type(field_value) is not dict:
            number_bins_for_each_field.append(binner_for_field[field_key].num_bins)
            axes[total_field_index] = field_key
            binner[total_field_index] = binner_for_field[field_key]
            sigma[total_field_index] = sigma_for_field[field_key]
            total_field_index += 1
        else:
            for sub_field_key, sub_field_value in field_value.items():
                try:
                    number_bins_for_each_field.append(binner_for_field[field_key].num_bins)
                    binner[total_field_index] = binner_for_field[field_key]
                    sigma[total_field_index] = sigma_for_field[field_key]
                except:
                    number_bins_for_each_field.append(binner_for_field[sub_field_key].num_bins)
                    binner[total_field_index] = binner_for_field[sub_field_key]
                    sigma[total_field_index] = sigma_for_field[sub_field_key]

                axes[total_field_index] = field_key + "." + sub_field_key

                total_field_index += 1

    point_matrix = np.zeros(number_bins_for_each_field, dtype=float32)
    return LabelledMatrix(axes, point_matrix, binner, sigma)


def assign_bins_for_component(binner_for_field: dict[str, Binner], component: dict) -> list[(int, tuple)]:
    """Assigns the values of every data field to a bin for a single component.
    Returns a list of tuples: (index, (min, middle, max)). One element per field.

     If a data field is multidimensional, will automatically unpack (must be a dict)"""
    assigned_bin_for_component: list[(int, tuple)] = []
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
                                         tuple[int, tuple]]) -> LabelledMatrix:
    """Sums onto component_point_matrix a 1 at the specified location (location = bins for a component)"""
    bin_indices_for_component = tuple(
        [assigned_index_and_bin[0] for assigned_index_and_bin in assigned_index_and_bin_for_each_component])
    component_point_matrix.matrix[bin_indices_for_component] += 1
    return component_point_matrix


def smooth_matrices(labelled_matrices: list[LabelledMatrix]) -> list[LabelledMatrix]:
    print("Smoothing Point Matrices")
    for matrix_number, labelled_matrix in enumerate(labelled_matrices):
        print("smoothing matrix #", matrix_number + 1)
        sigmas = [sigma * binner.num_bins for sigma, binner in zip(labelled_matrix.sigmas_for_axes.values(), labelled_matrix.binners_for_axes.values())]
        # smoothed_matrix = test_fourier(labelled_matrix, sigmas)
        smoothed_matrix = test_classic(labelled_matrix, sigmas)
        yield smoothed_matrix


def test_classic(labelled_matrix, sigmas):
    t = time.time()
    smoothed_matrix = smooth_spatial_domain(labelled_matrix, sigmas)
    print("elapsed classic: " + str(time.time() - t))
    return smoothed_matrix


def test_fourier(labelled_matrix, sigmas):
    t = time.time()
    smoothed_matrix = smooth_fourier_domain(labelled_matrix, sigmas)
    print("elapsed fourier: " + str(time.time() - t))
    return smoothed_matrix


def smooth_spatial_domain(labelled_matrix, sigmas):
    return labelled_matrix.apply(gaussian_filter, sigmas, truncate=2.5, mode='constant')


def smooth_fourier_domain(labelled_matrix, sigmas):
    labelled_matrix_frequency_domain = labelled_matrix.apply(scipy.fftpack.fftn)
    filtered_matrix_frequency_domain = labelled_matrix_frequency_domain.apply(fourier_gaussian, sigmas)
    smoothed_matrix = filtered_matrix_frequency_domain.apply(scipy.fftpack.ifftn)
    smoothed_matrix = smoothed_matrix.apply(np.real_if_close)
    return smoothed_matrix


def calculate_response_weighted_average(labelled_matrices: list[LabelledMatrix],
                                        response_vector: list[float]) -> LabelledMatrix:
    print("Calculating RWA")
    for stim_index, labelled_matrix in enumerate(labelled_matrices):
        print("Response weighting matrix for stimulus: ", stim_index + 1)
        try:
            response = response_vector[stim_index]
        except:
            response = response_vector.array[stim_index]

        (unweighted_stim_matrix, response_weighted_stim_matrix) = response_weigh_matrices(labelled_matrix, response)

        if stim_index == 0:
            template_matrix = labelled_matrix
            response_weighted_sum_matrix = np.zeros(response_weighted_stim_matrix.matrix.shape, dtype=float32)
            unweighted_sum_matrix = np.zeros(unweighted_stim_matrix.matrix.shape, dtype=float32)

        np.add(response_weighted_sum_matrix, response_weighted_stim_matrix.matrix, out=response_weighted_sum_matrix)
        np.add(unweighted_sum_matrix, unweighted_stim_matrix.matrix, out=unweighted_sum_matrix)

    response_weighted_average = divide_and_allow_divide_by_zero(response_weighted_sum_matrix, unweighted_sum_matrix)

    yield template_matrix.copy_labels(response_weighted_average)


def divide_and_allow_divide_by_zero(response_weighted_sum_matrix, unweighted_sum_matrix):
    """if attempt to divide by zero, returns 0"""
    output = np.zeros_like(response_weighted_sum_matrix)
    np.divide(response_weighted_sum_matrix, unweighted_sum_matrix,
              out=output, where=unweighted_sum_matrix != 0)
    return output


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

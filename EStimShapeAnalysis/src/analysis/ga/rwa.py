from __future__ import annotations

import math
import types
from dataclasses import dataclass
from collections import namedtuple
import time
from typing import Callable
import numpy as np
import pandas as pd
import scipy
from numpy import float32

from scipy.ndimage import fourier_gaussian
from scipy.ndimage.filters import gaussian_filter

from clat.util.dictionary_util import extract_values_with_key_into_list

data_type = float32


def rwa(stims: list[list[dict]], response_vector: list[float], binner_for_field: dict[str, Binner],
        sigma_for_field: dict[str, float], padding_for_field: dict[str, str]):
    """
    :param stims: n-list of m-lists of dictionaries with d entries, where the dictionary contains the fieldNames and the values for the data i.e {'curvature': 0.5, 'radius': 1.0}
    n: the number of stimuli
    m: the number components of the stimulus
    d: the number of dimensions in the data

    :param response_vector: n-list of floats, where each float is the response of the neuron to the corresponding stimulus

    :param binner_for_field: a dictionary of d field names and their corresponding Binner objects. Binner objects
    are responsible for binning the data for a given field.

    :param sigma_for_field: a dictionary of d field names and their corresponding sigma values for the gaussian kernel.
    The sigma specified is a percentage of the number of bins for the field. For example, if the number of bins for a field is 10,
    and the sigma is 0.1, then the sigma value for the gaussian kernel will be 1.0.
    see https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.gaussian_filter.html for more info on how sigma is used.

    :param padding_for_field: a dictionary of d field names and their corresponding padding types for the gaussian kernel
    see https://docs.scipy.org/doc/scipy/reference/generated/scipy.ndimage.gaussian_filter.html for possible paddings and more info
    """
    if isinstance(response_vector, pd.Series):
        response_vector = response_vector.to_list()

    print("generating point matrices")
    point_matrices = generate_point_matrices(stims, binner_for_field, sigma_for_field, padding_for_field)

    print("response weighing and summing point matrices")
    summed_response_weighted, summed_unweighted = get_next(
        response_weight_and_sum_point_matrices(point_matrices, response_vector))

    print("smoothing summed rw and uw matrices")
    smoothed_response_weighted = smooth_matrix(summed_response_weighted)
    smoothed_unweighted = smooth_matrix(summed_unweighted)

    print("dividing rw and uw matrices")
    response_weighted_average = divide_and_allow_divide_by_zero(get_next(smoothed_response_weighted).matrix,
                                                                get_next(smoothed_unweighted).matrix)
    response_weighted_average = summed_response_weighted.copy_labels(response_weighted_average)

    # response_weighted_average = normalize_matrix(response_weighted_average)
    yield response_weighted_average


def get_point_coordinates(rwa: RWAMatrix, stim: list[dict]) -> list[list[float]]:
    '''
    Given a RWAMatrix and a stimulus, returns the coordinates of the stimulus in the RWA matrix.
    Coordinates are in terms of bin middle values.
    '''

    binners_for_fields = {rwa.names_for_axes[str(i)]: rwa.binners_for_axes[str(i)] for i in range(len(rwa.binners_for_axes))}
    coordinates = []

    if not isinstance(stim, list):
        stim = [stim]

    for component in stim:
        component_coordinate = []



        assigned_bins_for_component = assign_bins_for_component(binners_for_fields, component)
        for index_and_assigned_bin in assigned_bins_for_component:
            assigned_bin = index_and_assigned_bin[1]
            component_coordinate.append(assigned_bin.middle)
        coordinates.append(component_coordinate)
    return coordinates


def get_point_indices(rwa: RWAMatrix, stim: list[dict]) -> list[list[int]]:
    '''
    Given a RWAMatrix and a stimulus, returns the coordinates of the stimulus in the RWA matrix
    in terms of bin indices.
    '''

    binners_for_fields = {rwa.names_for_axes[str(i)]: rwa.binners_for_axes[str(i)] for i in range(len(rwa.binners_for_axes))}
    bin_indices = []

    if not isinstance(stim, list):
        stim = [stim]

    for component in stim:
        component_bin_indices = []



        assigned_bins_for_component = assign_bins_for_component(binners_for_fields, component)
        for index_and_assigned_bin in assigned_bins_for_component:
            assigned_bin = index_and_assigned_bin[0]
            component_bin_indices.append(assigned_bin)
        bin_indices.append(component_bin_indices)
    return bin_indices

@dataclass
class RWAMatrix:
    """A matrix (np.ndarray) with metadata required to compute an RWA:
    the metadata is expressed as a dictionary between the data dimensions (as an index)
    and the metadata. The metadata:
    1. names_for_axes_indices: name of the data dimension (i.e radialPosition)
    2. binners_for_axes: binning behavior. Specifies how many bins, width of the bins, and
       is responsible for binning incoming stimulus data.
    3. sigmas_for_axes: sigma (as a proportion of number of bins) for the gaussian filter
       across this dimension.
    4. padding_for_axes: padding behavior for the gaussian filter across this dimension.
       see parameter "mode" under scipy.ndimage.filters.gaussian_filter for more details
    """
    names_for_axes: dict[int, str]
    matrix: np.ndarray
    binners_for_axes: dict[int, Binner]
    sigmas_for_axes: dict[int, float]
    padding_for_axes: dict[int, str]

    def apply(self, func: Callable, *args, **kwargs) -> RWAMatrix:
        """apply a function to self.matrix and return a RWAMatrix with the new
        matrix"""
        return RWAMatrix(self.names_for_axes, func(self.matrix, *args, **kwargs), self.binners_for_axes,
                         self.sigmas_for_axes, self.padding_for_axes)

    def copy_labels(self, matrix: np.ndarray) -> RWAMatrix:
        """copy the labels from self to a new RWAMatrix with the given matrix"""
        return RWAMatrix(self.names_for_axes, matrix, self.binners_for_axes, self.sigmas_for_axes,
                         self.padding_for_axes)


class Binner:
    """Generates a specified amount of bins for a given range of values.
       Stores these bins to be used for later in self.bins
       Assigns data values to one of the generated bins"""

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
            # BinRange = namedtuple('BinRange', 'start middle end')
            bin_range = BinRange(bin_start, bin_middle, bin_end)
            bin_ranges.append(bin_range)

        # Assign the list of bin ranges
        self.bins = bin_ranges

    def assign_bin(self, value) -> (int, tuple):
        for i, bin_range in enumerate(self.bins):
            # Check if the value is within the current bin_range range
            if bin_range.start <= float(value) < bin_range.end:
                # Return the current bin_range range
                return i, bin_range
        if not float(value) > self.end:
            return len(self.bins) - 1, self.bins[-1]
        # raise Exception("Value not in range: " + str(value) + " not in " + str(self.start) + " to " + str(self.end))


@dataclass
class BinRange:
    """Dataclass for the start, middle, and end of a single bin.
       This is not a NamedTuple because NamedTuples are incompatible with
       jsonpickle, which is used to store RWA Matrices for later use"""
    start: float
    middle: float
    end: float


class AutomaticBinner(Binner):
    """Given a field_name, and data containing that field_name, finds min and max for binning.
       The data can be a list of dictionaries or values.
       If the data is a list of values, field_name is ignored"""

    def __init__(self, field_name: str, data: list, num_bins: int):
        """The data can be a list of dictionaries/values for the field or a pd.Series of dictionaries/values"""
        self.field_name = field_name
        self.data = data
        self.min, self.max = self.calculate_min_max()
        super().__init__(self.min, math.ceil(math.ceil(self.max * 100000)) / 100000.0, num_bins)
        """rounding UP 5 decimal places to avoid floating point errors because bin end
        is exclusive"""

    def calculate_min_max(self):
        values = []
        for point in self.data:
            if isinstance(point, dict) or isinstance(point, list):
                extract_values_with_key_into_list(point, values, self.field_name)
            else:
                values.append(point)
        values = [float(v) for v in values]
        return min(values), max(values)


def normalize_and_combine_rwas(rwas):
    normalized_rwas, overall_max = normalize_rwas(rwas)
    rwa_product = multiply_rwas(rwas)
    rwa_normalized_product = normalize_matrix(rwa_product)
    rwa_normalized_product = rwa_normalized_product.apply(lambda m: np.power(m, 1 / len(rwas)))
    rwa_normalized_product = rwa_normalized_product.apply(lambda m: m * overall_max)
    return rwa_normalized_product


def combine_rwas(rwas):
    rwa_product = multiply_rwas(rwas)
    rwa_normalized_product = normalize_matrix(rwa_product)
    return rwa_normalized_product


def normalize_rwas(rwas):
    """divide rwas by the overall max across ALL rwas"""
    normalized_rwas = []
    overall_max = 0
    for lineage_rwa in rwas:
        lineage_max = np.max(lineage_rwa.matrix)
        if lineage_max > overall_max:
            overall_max = lineage_max
    for lineage_rwa in rwas:
        normalized_rwas.append(lineage_rwa.apply(lambda m: m / overall_max))

    return normalized_rwas, overall_max


def multiply_rwas(rwas):
    rwa_prod: np.ndarray
    template: RWAMatrix
    for lineage_index, r in enumerate(rwas):
        lineage_rwa = get_next(r)
        if lineage_index == 0:
            template = lineage_rwa
            rwa_prod = np.ones_like(lineage_rwa.matrix)
        np.multiply(rwa_prod, lineage_rwa.matrix, out=rwa_prod)
    return template.copy_labels(rwa_prod)


def get_next(possible_generator):
    """get the next element in a generator, but if the argument is not a generator
    return the argument"""
    if isinstance(possible_generator, types.GeneratorType):
        return next(possible_generator)
    else:
        return possible_generator


def raw_data(stims: list[list[dict]], response_vector: list[float], binner_for_field: dict[str, Binner],
             sigma_for_field: dict[str, float], padding_for_field: dict[str, str]):
    if isinstance(response_vector, pd.Series):
        response_vector = response_vector.to_list()

    print("generating point matrices")
    point_matrices = generate_point_matrices(stims, binner_for_field, sigma_for_field, padding_for_field)

    print("response weighing and summing point matrices")
    summed_response_weighted, summed_unweighted = get_next(
        response_weight_and_sum_point_matrices(point_matrices, response_vector))

    yield summed_response_weighted, summed_unweighted


def response_weight_and_sum_point_matrices(point_matrices: list[RWAMatrix], response_vector: list[float]) -> (
        RWAMatrix, RWAMatrix):
    point_matrices = (labelled_matrix for labelled_matrix in point_matrices)  # to unfold the generator objects

    for index, point_matrix in enumerate(point_matrices):
        # intializing we have to do because of generators
        if index == 0:
            template = point_matrix
            summed_response_weighted = np.zeros_like(template.matrix)
            summed_unweighted = np.zeros_like(template.matrix)
        if np.isnan(response_vector[index]).any():
            print("WARNING! NO RESPONSE VECTOR FOR POINT MATRIX " + str(index + 1) + " SETTING VALUE TO 0")
            response_vector[index] = 0

        np.add(summed_unweighted, point_matrix.matrix, out=summed_unweighted)

        print("response weighing and summing point matrix " + str(index + 1))
        matrix = point_matrix.apply(lambda m, r: np.multiply(m, r), float(response_vector[index])).matrix
        np.add(summed_response_weighted, matrix,
               out=summed_response_weighted)

    summed_response_weighted = template.copy_labels(summed_response_weighted)
    summed_unweighted = template.copy_labels(summed_unweighted)
    yield summed_response_weighted, summed_unweighted


def generate_point_matrices(stims: list[list[dict]], binner_for_field: dict[str, Binner],
                            sigma_for_field: dict[str, float], padding_for_field: dict[str, str]) -> list[
    RWAMatrix]:
    """For each stimulus, generates a Stimulus Point Matrix.
    Each Stim Point Matrix is the summation of multiple Component Point Matrices.

    Each Component Point Matrix is a matrix whose dimensions represent the data fields
    for that component/stimulus.

    The size of each dimension of a point matrix is equal to the number of bins assigned to the data field
    represented by that dimension.

    Each Component Matrix is composed of zeros everywhere, except with a 1
    At the location that represents the bins assigned to that component

    Plus we fill in the sigma, padding behavior, binner, and labels for each axis"""
    print("Generating Point Matrices")
    # For each stimulus
    for stim_index, stim_components in enumerate(stims):
        print("generating point matrix for stim " + str(stim_index))
        stim_point_matrix = generate_stim_point_matrix(stim_components, binner_for_field, sigma_for_field,
                                                       padding_for_field)
        yield stim_point_matrix


def generate_stim_point_matrix(stim_components, binner_for_field, sigma_for_field, padding_for_field):
    """For a single stimulus, generates a Stimulus Point Matrix."""

    component_point_matrix = initialize_point_matrix(stim_components, binner_for_field, sigma_for_field,
                                                     padding_for_field)
    # For each component of the stimulus

    if not isinstance(stim_components, list):
        stim_components = [stim_components]

    for component in stim_components:
        assigned_bins_for_component = assign_bins_for_component(binner_for_field, component)
        component_point_matrix = append_point_to_component_matrix(component_point_matrix,
                                                                  assigned_bins_for_component)
    return component_point_matrix


def initialize_point_matrix(stim_components: list[dict], binner_for_field: dict[str, Binner],
                            sigma_for_field: dict[str, float], padding_for_field: dict[str, str]) -> RWAMatrix:
    """Initialize a zero matrix with a number of dimensions equal to the number of data fields.
    Each dimension has size equal to the number of bins specified for that field.

    If a data field has multi-dimensions (i.e x,y position), then this will automatically unpack that.
    Currently, the multidimensional data field must be a dict for this to work.

    The total number of dimensions of this matrix will be equal to the total dimensionality of the data.

    Currently only unpacks one level deep

    Also converts the zero matrix ndarray into an RWAMatrix.
    This sets the sigma, padding behavior, binner, and labels for each axis"""
    number_bins_for_each_field = []
    axes = {}
    binner = {}
    sigma = {}
    padding = {}
    total_field_index = 0

    # If the stimulus is a single component, then we need to make it a list of one component
    if not isinstance(stim_components, list):
        stim_components = [stim_components]

    for field_key, field_value in stim_components[0].items():
        # "If the field is single dimensional (not a dict), then we assign the axes name, binner, sigma, padding, etc."
        if type(field_value) is not dict:
            number_bins_for_each_field.append(binner_for_field[field_key].num_bins)
            axes[total_field_index] = field_key
            binner[total_field_index] = binner_for_field[field_key]
            sigma[total_field_index] = sigma_for_field[field_key]
            padding[total_field_index] = padding_for_field[field_key]
            total_field_index += 1
        # "If the field is a dict, then we assume it is a multidimensional field"
        else:
            for sub_field_key, sub_field_value in field_value.items():
                # If the metadata is specified using the super field ONLY (i.e. angularPosition)
                # we want the sub-fields to inherit the super field's metadata
                try:
                    number_bins_for_each_field.append(binner_for_field[field_key].num_bins)
                    binner[total_field_index] = binner_for_field[field_key]
                    sigma[total_field_index] = sigma_for_field[field_key]
                    padding[total_field_index] = padding_for_field[field_key]
                # If the metadata is specified using the sub-field (i.e. theta in angularPosition.theta)
                # we want the sub-field to have its own metadata
                except:
                    try:
                        number_bins_for_each_field.append(binner_for_field[sub_field_key].num_bins)
                        binner[total_field_index] = binner_for_field[sub_field_key]
                        sigma[total_field_index] = sigma_for_field[sub_field_key]
                        padding[total_field_index] = padding_for_field[sub_field_key]
                    # If the metadata is specified using super_field.sub_field (i.e. angularPosition.theta)
                    # We want the sub_field associated with the correct super_field to inherit the specified metadata
                    except:
                        try:
                            combined_key: str = '%s.%s' % (field_key, sub_field_key)
                            number_bins_for_each_field.append(binner_for_field[combined_key].num_bins)
                            binner[total_field_index] = binner_for_field[combined_key]
                            sigma[total_field_index] = sigma_for_field[combined_key]
                            padding[total_field_index] = padding_for_field[combined_key]
                        # If the metadata or field doesn't exist, skip
                        except KeyError:
                            continue

                # Set the axis name to be the super field_name.sub_field_name
                axes[total_field_index] = field_key + "." + sub_field_key
                total_field_index += 1

    point_matrix = np.zeros(number_bins_for_each_field, dtype=data_type)
    return RWAMatrix(axes, point_matrix, binner, sigma, padding)


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
                    try:
                        assigned_bin_for_component.append(binner_for_field[sub_field_key].assign_bin(sub_field_value))
                    except:
                        try:
                            combined_key: str = '%s.%s' % (field_key, sub_field_key)
                            assigned_bin_for_component.append(
                                binner_for_field[combined_key].assign_bin(sub_field_value))
                        # If the metadata or field doesn't exist, skip
                        except KeyError:
                            continue

    return assigned_bin_for_component


def append_point_to_component_matrix(component_point_matrix: RWAMatrix,
                                     assigned_index_and_bin_for_each_component: list[
                                         tuple[int, tuple]]) -> RWAMatrix:
    """Sums onto component_point_matrix a 1 at the specified location (location = bins for a component)"""
    bin_indices_for_component = tuple(
        [assigned_index_and_bin[0] for assigned_index_and_bin in assigned_index_and_bin_for_each_component])
    component_point_matrix.matrix[bin_indices_for_component] += 1
    return component_point_matrix


def smooth_matrices(labelled_matrices: list[RWAMatrix]) -> list[RWAMatrix]:
    print("Smoothing Point Matrices")
    for matrix_number, labelled_matrix in enumerate(labelled_matrices):
        print("smoothing matrix #", matrix_number + 1)
        yield from smooth_matrix(labelled_matrix)


def smooth_matrix(labelled_matrix):
    sigmas = [sigma * binner.num_bins for sigma, binner in
              zip(labelled_matrix.sigmas_for_axes.values(), labelled_matrix.binners_for_axes.values())]
    padding = labelled_matrix.padding_for_axes.values()
    smoothed_matrix = test_classic(labelled_matrix, sigmas, padding)
    yield smoothed_matrix


def test_classic(labelled_matrix, sigmas, padding):
    t = time.time()
    smoothed_matrix = smooth_spatial_domain(labelled_matrix, sigmas, padding)
    print("elapsed classic: " + str(time.time() - t))
    return smoothed_matrix


def test_fourier(labelled_matrix, sigmas):
    t = time.time()
    smoothed_matrix = smooth_fourier_domain(labelled_matrix, sigmas)
    print("elapsed fourier: " + str(time.time() - t))
    return smoothed_matrix


def smooth_spatial_domain(labelled_matrix, sigmas, padding):
    if padding is None:
        padding = "nearest"
    return labelled_matrix.apply(gaussian_filter, sigmas, mode=padding, truncate=5)


def smooth_fourier_domain(labelled_matrix, sigmas):
    labelled_matrix_frequency_domain = labelled_matrix.apply(scipy.fftpack.fftn)
    filtered_matrix_frequency_domain = labelled_matrix_frequency_domain.apply(fourier_gaussian, sigmas)
    smoothed_matrix = filtered_matrix_frequency_domain.apply(scipy.fftpack.ifftn)
    smoothed_matrix = smoothed_matrix.apply(np.real_if_close)
    return smoothed_matrix


def divide_and_allow_divide_by_zero(response_weighted_sum_matrix, unweighted_sum_matrix):
    """if attempt to divide by zero, returns 0"""
    output = np.zeros_like(response_weighted_sum_matrix)
    np.divide(response_weighted_sum_matrix, unweighted_sum_matrix,
              out=output, where=unweighted_sum_matrix != 0)
    return output


def response_weigh_matrices(labelled_matrix, response) -> (RWAMatrix, RWAMatrix):
    unweighted_matrix = labelled_matrix
    response_weighted_matrix = unweighted_matrix.apply(response_weigh_matrix, response)
    return unweighted_matrix, response_weighted_matrix


def response_weigh_matrix(matrix, response):
    return matrix * response


def normalize_matrix(labelled_matrix: RWAMatrix):
    max_val = np.amax(labelled_matrix.matrix)
    normalized_matrix = labelled_matrix.apply(np.divide, max_val)
    return normalized_matrix

from __future__ import annotations
import random
from unittest import TestCase

import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import multivariate_normal

from src.analysis.rwa import Binner, rwa, raw_data, RWAMatrix, divide_and_allow_divide_by_zero, combine_rwas, get_next
from src.mock.mock_rwa_plot import draw_one_d_field, get_indices_for_fields


def plot_data_and_rwa_variations(response_weighted_averages, summed_response_weighted, summed_unweighted):
    fields = summed_response_weighted[0].names_for_axes.values()
    num_dims = len(fields)
    num_groups = 6
    group_titles = ["Unweighted Data - Sum", "Response Weighted Data - Sum", "Response Weighted Data - Max", "RWA-Sum",
                    "RWA - Max",
                    "RWA - Average"]
    data_to_plot = [summed_unweighted, summed_response_weighted, summed_response_weighted, response_weighted_averages,
                    response_weighted_averages, response_weighted_averages]
    fig = plt.figure(constrained_layout=True)
    subfigs = fig.subfigures(nrows=num_groups, ncols=1)
    for row, subfig in enumerate(subfigs):
        subfig.suptitle(group_titles[row])

        axes = subfig.subplots(nrows=1, ncols=num_dims)
        if row == 0 or row == 1 or row == 3:
            for field, axis in zip(fields, axes):
                for lineage in data_to_plot[row]:
                    plot_data_sum(axis, lineage, field)

        elif row == 2:
            for field, axis in zip(fields, axes):
                for lineage in data_to_plot[row]:
                    plot_data_max(axis, lineage, field)

        # rwa
        elif row == 4:
            for field, axis in zip(fields, axes):
                for lineage in data_to_plot[row]:
                    matrix_peak_location = np.unravel_index(np.argsort(lineage.matrix, axis=None)[-1:],
                                                            lineage.matrix.shape)
                    draw_one_d_field(lineage, field, matrix_peak_location, axis)
                axis.set_autoscale_on(True)

        elif row == 5:
            for field, axis in zip(fields, axes):
                for lineage in data_to_plot[row]:
                    plot_data_average(axis, lineage, field)

        # data
    plt.show()


def plot_data_average(axis, rwa_matrix: RWAMatrix, field_name):
    matrix = rwa_matrix.matrix

    indices_to_plot = get_indices_for_fields(rwa_matrix, [field_name])
    binner = rwa_matrix.binners_for_axes[indices_to_plot[0]]
    try:
        x_axis = [bin['py/newargs']['py/tuple'][1] for bin in binner.bins]
    except:
        x_axis = [bin.middle for bin in binner.bins]

    all_indices_except_to_plot = [index for index in rwa_matrix.names_for_axes.keys() if
                                  index not in indices_to_plot]
    y_axis = np.average(matrix, axis=tuple(all_indices_except_to_plot))
    axis.plot(x_axis, y_axis)


def plot_data_max(axis, rwa_matrix: RWAMatrix, field_name):
    matrix = rwa_matrix.matrix

    indices_to_plot = get_indices_for_fields(rwa_matrix, [field_name])
    binner = rwa_matrix.binners_for_axes[indices_to_plot[0]]
    try:
        x_axis = [bin['py/newargs']['py/tuple'][1] for bin in binner.bins]
    except:
        x_axis = [bin.middle for bin in binner.bins]

    all_indices_except_to_plot = [index for index in rwa_matrix.names_for_axes.keys() if
                                  index not in indices_to_plot]
    y_axis = np.amax(matrix, axis=tuple(all_indices_except_to_plot))
    axis.plot(x_axis, y_axis)


def plot_data_sum(axis, rwa_matrix: RWAMatrix, field_name):
    matrix = rwa_matrix.matrix

    indices_to_plot = get_indices_for_fields(rwa_matrix, [field_name])
    binner = rwa_matrix.binners_for_axes[indices_to_plot[0]]
    try:
        x_axis = [bin['py/newargs']['py/tuple'][1] for bin in binner.bins]
    except:
        x_axis = [bin.middle for bin in binner.bins]

    all_indices_except_to_plot = [index for index in rwa_matrix.names_for_axes.keys() if
                                  index not in indices_to_plot]
    y_axis = np.sum(matrix, axis=tuple(all_indices_except_to_plot))
    axis.plot(x_axis, y_axis)


class MultiDimAndLineageTestCase(TestCase):
    """Leaner test casefor testing multidimensional rwas, without the cruft of nested dicts and the such"""

    def setUp(self) -> None:
        super().setUp()
        self.num_lineages = 2
        self.num_dims = 8
        field_names = ["A", "B", "C", "D", "E", "F", "G", "H"]
        self.num_bins = [10, 10, 10, 10, 8, 8, 5, 5]

        binners = [Binner(0, 1, num_bins) for num_bins in self.num_bins]
        peak = [0.50 for _ in range(self.num_dims)]
        sigmas = [0.2 for _ in range(self.num_dims)]
        # paddings = ["nearest", "nearest", "constant", "constant", "reflect", "reflect", "mirror", "mirror"]
        paddings = ["nearest" for _ in range(self.num_dims)]
        self.fields = field_names[:self.num_dims]
        self.peak = peak[:self.num_dims]
        self.sigmas = sigmas[:self.num_dims]
        self.paddings = paddings[:self.num_dims]
        self.binners = binners[:self.num_dims]

        self.num_data_points = 200
        self.stims = self.generate_stim(self.num_data_points)
        self.responses = self.generate_responses()

    def test_compare_raw_data_sum_to_rwa_max(self):
        summed_response_weighted = []
        summed_unweighted = []
        response_weighted_averages = []
        for lineage in range(self.num_lineages):
            lineage_summed_response_weighed, lineage_summed_unweighted = get_next(
                raw_data(self.stims, self.responses, dict(zip(self.fields, self.binners)),
                         dict(zip(self.fields, self.sigmas)),
                         dict(zip(self.fields, self.paddings))))
            summed_response_weighted.append(lineage_summed_response_weighed)
            summed_unweighted.append(lineage_summed_unweighted)

            lineage_response_weighted_average = get_next(
                rwa(self.stims, self.responses, dict(zip(self.fields, self.binners)),
                    dict(zip(self.fields, self.sigmas)),
                    dict(zip(self.fields, self.paddings))))
            response_weighted_averages.append(lineage_response_weighted_average)
            self.setUp()

        response_weighted_average_multiplied = combine_rwas(response_weighted_averages)
        response_weighted_averages.append(response_weighted_average_multiplied)
        plot_data_and_rwa_variations(response_weighted_averages, summed_response_weighted, summed_unweighted)

    def test_multi_dim_rwa(self):
        response_weighted_average_1 = next(
            rwa(self.stims, self.responses, dict(zip(self.fields, self.binners)), dict(zip(self.fields, self.sigmas)),
                dict(zip(self.fields, self.paddings))))
        self.setUp()
        response_weighted_average_2 = next(
            rwa(self.stims, self.responses, dict(zip(self.fields, self.binners)), dict(zip(self.fields, self.sigmas)),
                dict(zip(self.fields, self.paddings))))

        response_weighted_average = combine_rwas([response_weighted_average_1, response_weighted_average_2])
        matrix = response_weighted_average.matrix
        matrix_peak_location = np.unravel_index(np.argsort(matrix, axis=None)[-1:], matrix.shape)
        fig, axes = plt.subplots(1, self.num_dims)
        for index, field_name in enumerate(self.fields):
            draw_one_d_field(response_weighted_average, field_name, matrix_peak_location, axes[index])
        plt.show()

    def generate_stim(self, num_data_points):
        stims = []
        for i in range(num_data_points):
            # random chance
            if random.random() < 0.5:
                stim_dict = [self.generate_stim_component() for _ in range(2)]
            else:
                stim_dict = [self.generate_stim_component() for _ in range(3)]

            stims.append(stim_dict)

        return stims

    def generate_stim_component(self):
        return {field_name: random.uniform(0, 1) for field_name in self.fields}

    def generate_responses(self):
        return [self.generate_resp_for(stim) for stim in self.stims]

    def generate_resp_for(self, stim):
        responses_per_component = []
        for component in stim:
            cov = [sigma * 1 for sigma in self.sigmas]
            total_energy = self.num_dims
            component = [component[field_name] for field_name in self.fields]
            response = total_energy * multivariate_normal.pdf(np.array(component), mean=np.array(self.peak), cov=cov,
                                                              allow_singular=True)
            responses_per_component.append(response)
        return np.max(responses_per_component)

    def test_generate_resp(self):
        print(self.generate_resp_for([dict(zip(self.fields, self.peak))]))

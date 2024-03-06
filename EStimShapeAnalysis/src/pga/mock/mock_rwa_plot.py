from __future__ import annotations
import types

import jsonpickle
import matplotlib
import numpy as np
from matplotlib import pyplot as plt, cm
matplotlib.use('TkAgg')

from analysis.ga.rwa import get_next
from clat.util.connection import Connection
from pga.mock.plot_rwa_top_n import plot_top_n_junctions_on_fig, plot_top_n_stimuli_on_termination, \
    plot_top_n_stimuli_on_shaft, find_distances_to_peak, print_top_stim_and_comp_ids


def main():
    conn = Connection("allen_estimshape_ga_dev_240207")
    n = 3

    shaft_rwa = jsonpickle.decode(
        open("/home/r2_allen/Documents/EStimShape/ga_dev_240207/rwa/shaft_rwa.json", "r").read())
    fig_shaft = plot_shaft_rwa_1d(get_next(shaft_rwa))
    plot_top_n_stimuli_on_shaft(n, fig_shaft, shaft_rwa, conn)
    distances_to_shaft_peak = find_distances_to_peak(shaft_rwa, n, conn, 'shaft')
    print("distances SHAFT: " + str(distances_to_shaft_peak))


    plt.suptitle("Combined SHAFT RWA")

    termination_rwa = jsonpickle.decode(open("/home/r2_allen/Documents/EStimShape/ga_dev_240207/rwa/termination_rwa.json", "r").read())
    fig_termination = plot_termination_rwa_1d(get_next(termination_rwa))
    plot_top_n_stimuli_on_termination(n, fig_termination, termination_rwa, conn)
    distances_to_termination_peak = find_distances_to_peak(termination_rwa, n, conn, 'termination')
    print("distances TERMINATION: " + str(distances_to_termination_peak))
    plt.suptitle("Combined TERMINATION RWA")


    junction_rwa = jsonpickle.decode(
        open("/home/r2_allen/Documents/EStimShape/ga_dev_240207/rwa/junction_rwa.json", "r").read())
    fig = plot_junction_rwa_1d(get_next(junction_rwa))
    plot_top_n_junctions_on_fig(n, fig, junction_rwa, conn)
    distances_to_junction_peak = find_distances_to_peak(junction_rwa, n, conn, 'junction')
    print("distances JUNCTION: " + str(distances_to_junction_peak))
    plt.suptitle("Combined JUNCTION RWA")

    print_top_stim_and_comp_ids(conn, distances_to_junction_peak, distances_to_shaft_peak,
                                distances_to_termination_peak, n)

    plt.show()


def plot_shaft_rwa_1d(shaft_rwa):
    matrix = shaft_rwa.matrix

    # matrix = np.flip(matrix)
    matrix_peak_location = np.unravel_index(np.argsort(matrix, axis=None)[-1:], matrix.shape)

    fig = plt.figure(figsize=(20, 10))
    ax_angular_position_theta = fig.add_subplot(1, 8, 1)
    ax_angular_position_phi = fig.add_subplot(1, 8, 2)
    ax_radial_position = fig.add_subplot(1, 8, 3)
    ax_orientation_theta = fig.add_subplot(1, 8, 4)
    ax_orientation_phi = fig.add_subplot(1, 8, 5)
    ax_radius = fig.add_subplot(1, 8, 6)
    ax_length = fig.add_subplot(1, 8, 7)
    ax_curvature = fig.add_subplot(1, 8, 8)

    # 1D SLICES
    draw_one_d_field(shaft_rwa, "angularPosition.theta", matrix_peak_location, ax_angular_position_theta)
    draw_one_d_field(shaft_rwa, "angularPosition.phi", matrix_peak_location, ax_angular_position_phi)
    draw_one_d_field(shaft_rwa, "radialPosition", matrix_peak_location, ax_radial_position)
    draw_one_d_field(shaft_rwa, "orientation.theta", matrix_peak_location, ax_orientation_theta)
    draw_one_d_field(shaft_rwa, "orientation.phi", matrix_peak_location, ax_orientation_phi)
    draw_one_d_field(shaft_rwa, "length", matrix_peak_location, ax_length)
    draw_one_d_field(shaft_rwa, "curvature", matrix_peak_location, ax_curvature)
    draw_one_d_field(shaft_rwa, "radius", matrix_peak_location, ax_radius)

    return fig


def plot_termination_rwa_1d(termination_rwa):
    matrix = termination_rwa.matrix

    # matrix = np.flip(matrix)
    matrix_peak_location = np.unravel_index(np.argsort(matrix, axis=None)[-1:], matrix.shape)

    fig = plt.figure(figsize=(20, 10))
    nCol = 6
    ax_angular_position_theta = fig.add_subplot(1, nCol, 1)
    ax_angular_position_phi = fig.add_subplot(1, nCol, 2)
    ax_radial_position = fig.add_subplot(1, nCol, 3)
    ax_direction_theta = fig.add_subplot(1, nCol, 4)
    ax_direction_phi = fig.add_subplot(1, nCol, 5)
    ax_radius = fig.add_subplot(1, nCol, 6)

    # 1D SLICES
    draw_one_d_field(termination_rwa, "angularPosition.theta", matrix_peak_location, ax_angular_position_theta)
    draw_one_d_field(termination_rwa, "angularPosition.phi", matrix_peak_location, ax_angular_position_phi)
    draw_one_d_field(termination_rwa, "radialPosition", matrix_peak_location, ax_radial_position)
    draw_one_d_field(termination_rwa, "direction.theta", matrix_peak_location, ax_direction_theta)
    draw_one_d_field(termination_rwa, "direction.phi", matrix_peak_location, ax_direction_phi)
    draw_one_d_field(termination_rwa, "radius", matrix_peak_location, ax_radius)

    return fig


def plot_junction_rwa_1d(junction_rwa):
    matrix = junction_rwa.matrix

    # matrix = np.flip(matrix)
    matrix_peak_location = np.unravel_index(np.argsort(matrix, axis=None)[-1:], matrix.shape)

    fig = plt.figure(figsize=(20, 10))
    nCol = 8
    ax_angular_position_theta = fig.add_subplot(1, nCol, 1)
    ax_angular_position_phi = fig.add_subplot(1, nCol, 2)
    ax_radial_position = fig.add_subplot(1, nCol, 3)
    ax_angle_bisector_direction_theta = fig.add_subplot(1, nCol, 4)
    ax_angle_bisector_direction_phi = fig.add_subplot(1, nCol, 5)
    ax_radius = fig.add_subplot(1, nCol, 6)
    ax_angular_subtense = fig.add_subplot(1, nCol, 7)
    ax_planar_rotation = fig.add_subplot(1, nCol, 8)

    # 1D SLICES
    draw_one_d_field(junction_rwa, "angularPosition.theta", matrix_peak_location, ax_angular_position_theta)
    draw_one_d_field(junction_rwa, "angularPosition.phi", matrix_peak_location, ax_angular_position_phi)
    draw_one_d_field(junction_rwa, "radialPosition", matrix_peak_location, ax_radial_position)
    draw_one_d_field(junction_rwa, "angleBisectorDirection.theta", matrix_peak_location,
                     ax_angle_bisector_direction_theta)
    draw_one_d_field(junction_rwa, "angleBisectorDirection.phi", matrix_peak_location, ax_angle_bisector_direction_phi)
    draw_one_d_field(junction_rwa, "radius", matrix_peak_location, ax_radius)
    draw_one_d_field(junction_rwa, "angularSubtense", matrix_peak_location, ax_angular_subtense)
    draw_one_d_field(junction_rwa, "planarRotation", matrix_peak_location, ax_planar_rotation)

    return fig


def plot_shaft_rwa(test_rwa):
    matrix = test_rwa.matrix

    # matrix = np.flip(matrix)
    matrix_peak_location = np.unravel_index(np.argsort(matrix, axis=None)[-1:], matrix.shape)

    # ARRANGING SUBPLOTS
    fig = plt.figure(figsize=(20, 10))
    ax_angular_position = fig.add_subplot(1, 6, 1, projection='3d')
    ax_radial_position = fig.add_subplot(1, 6, 2)
    ax_orientation = fig.add_subplot(1, 6, 3, projection='3d')
    ax_radius = fig.add_subplot(1, 6, 4)
    ax_length = fig.add_subplot(1, 6, 5)
    ax_curvature = fig.add_subplot(1, 6, 6)

    # 2D ANGULAR SLICE - angularPosition
    indices_to_slice = get_indices_for_fields(test_rwa, ["angularPosition.theta", "angularPosition.phi"])
    slice_to_draw = slice_matrix(indices_to_slice, matrix, matrix_peak_location)
    draw_spherical_slice(slice_to_draw, axes=ax_angular_position)
    ax_angular_position.set_title("angularPosition")

    # 2D ANGULAR SLICE - orientation
    indices_to_slice = get_indices_for_fields(test_rwa, ["orientation.theta", "orientation.phi"])
    slice_to_draw = slice_matrix(indices_to_slice, matrix, matrix_peak_location)
    draw_hemispherical_slice(slice_to_draw, axes=ax_orientation)
    ax_orientation.set_title("orientation")

    # 1D SLICES
    draw_one_d_field(test_rwa, "radialPosition", matrix_peak_location, ax_radial_position)
    draw_one_d_field(test_rwa, "length", matrix_peak_location, ax_length)
    draw_one_d_field(test_rwa, "curvature", matrix_peak_location, ax_curvature)
    draw_one_d_field(test_rwa, "radius", matrix_peak_location, ax_radius)

    plt.draw()


def plot_multi_peaks(test_rwa):
    matrix = test_rwa.matrix
    matrix_peaks = []
    number_of_peaks = 3
    matrix_peak_locations = np.unravel_index(np.argsort(matrix, axis=None)[-number_of_peaks:], matrix.shape)
    for i in range(number_of_peaks):
        peak_indices = [matrix_peak_location[i] for matrix_peak_location in matrix_peak_locations]
        matrix_peaks.append(peak_indices)
    print(matrix_peaks)
    # 2D ANGULAR SLICE - angularPosition
    # find indices to slice
    indices_to_slice_per_peak = get_indices_to_slice_per_peak(number_of_peaks, test_rwa,
                                                              ["angularPosition.theta", "angularPosition.phi"])
    slices_to_draw_per_peak = []
    for i in range(number_of_peaks):
        slice_to_draw = slice_matrix(indices_to_slice_per_peak[i], matrix, matrix_peaks[i])
        slices_to_draw_per_peak.append(slice_to_draw)
    draw_spherical_slices(slices_to_draw_per_peak)
    # 2D ANGULAR SLICE - orientation
    # find indices to slice
    indices_to_slice_per_peak = get_indices_to_slice_per_peak(number_of_peaks, test_rwa,
                                                              ["orientation.theta", "orientation.phi"])
    slices_to_draw_per_peak = []
    for i in range(number_of_peaks):
        slice_to_draw = slice_matrix(indices_to_slice_per_peak[i], matrix, matrix_peaks[i])
        slices_to_draw_per_peak.append(slice_to_draw)
    draw_hemispherical_slices(slices_to_draw_per_peak)
    # 1D RADIAL POSITION SUM SLICE
    # radial_position_sum = np.max(matrix, axis=(0,1,3,4,5,6,7))
    # plt.plot(radial_position_sum)
    # 1D SLICES
    draw_one_d_field_per_peak(matrix, matrix_peaks, number_of_peaks, test_rwa, "radialPosition")
    draw_one_d_field_per_peak(matrix, matrix_peaks, number_of_peaks, test_rwa, "length")
    draw_one_d_field_per_peak(matrix, matrix_peaks, number_of_peaks, test_rwa, "curvature")
    draw_one_d_field_per_peak(matrix, matrix_peaks, number_of_peaks, test_rwa, "radius")
    plt.show()


def draw_one_d_field_per_peak(matrix, matrix_peaks, number_of_peaks, test_rwa, field_name):
    indices_to_slice = get_indices_to_slice_per_peak(number_of_peaks, test_rwa, [field_name])
    fig, axes = plt.subplots(number_of_peaks)
    for axes, (peak_index, indices_to_slice_for_peak) in zip(axes, enumerate(indices_to_slice)):
        slice_to_draw = slice_matrix(indices_to_slice_for_peak, matrix, matrix_peaks[peak_index])
        binner = test_rwa.binners_for_axes[str(indices_to_slice_for_peak[0])]
        draw_1D_slice(slice_to_draw, binner.bins, axes)
        # labels
        axes.set_xlabel(field_name)


def draw_one_d_field(rwa, field_name, matrix_peak_location, axis):
    indices_to_slice = get_indices_for_fields(rwa, [field_name])
    slice_to_draw = slice_matrix(indices_to_slice, rwa.matrix, matrix_peak_location)
    try:
        binner = rwa.binners_for_axes[str(indices_to_slice[0])]
    except:
        binner = rwa.binners_for_axes[indices_to_slice[0]]
    draw_1D_slice(slice_to_draw, binner.bins, axes=axis)
    # labels
    axis.set_xlabel(field_name)
    axis.set_ylim([0, slice_to_draw.max() * 1.1])


def get_indices_to_slice_per_peak(number_of_peaks, test_rwa, fields):
    indices_to_slice_per_peak = []
    for i in range(number_of_peaks):
        indices_to_slice = get_indices_for_fields(fields, test_rwa)
        indices_to_slice_per_peak.append(indices_to_slice)
    return indices_to_slice_per_peak


def get_indices_for_fields(test_rwa, fields):
    indices_for_axes = test_rwa.names_for_axes
    indices_to_slice = [get_key_for_value(indices_for_axes, field) for field in fields]
    indices_to_slice = [int(index) for index in indices_to_slice]
    return indices_to_slice


def draw_1D_slice(slice_to_draw, bins, axes=None):
    if axes is None:
        fig = plt.figure()
        axes = fig.add_subplot(1, 1, 1)

    try:
        x_axis = [bin['py/newargs']['py/tuple'][1] for bin in bins]
        x_ticks = [round(bin['py/newargs']['py/tuple'][2], 2) for bin in bins]
    except:
        x_axis = [bin.middle for bin in bins]

        x_ticks = [round(bin.end, 2) for bin in bins]

    axes.plot(x_axis, np.squeeze(slice_to_draw))
    axes.set_xticks(x_ticks)
    axes.set_xticklabels(x_ticks, rotation=90, ha='center')


def slice_matrix(indices_to_slice_along, matrix, matrix_peak_location):
    slice_indices_to_draw = list(matrix_peak_location)
    try:
        for index_to_slice_along in indices_to_slice_along:
            slice_indices_to_draw[index_to_slice_along] = slice(None)
    except TypeError:
        slice_indices_to_draw[indices_to_slice_along] = slice(None)

    slice_to_draw = matrix[tuple(slice_indices_to_draw)]
    return slice_to_draw


def draw_spherical_slices(slices_to_draw):
    fig, subplots = plt.subplots(1, len(slices_to_draw), subplot_kw=dict(projection='3d'))

    for slice, subplot in zip(slices_to_draw, subplots):
        draw_spherical_slice(slice, subplot)
    plt.show()


def draw_spherical_slice(slice_to_draw: np.ndarray, axes=None):
    if isinstance(slice_to_draw, types.GeneratorType):
        slice_to_draw = get_next(slice_to_draw)
    theta, phi = np.linspace(-np.pi, np.pi, slice_to_draw.shape[0]), np.linspace(0, np.pi, slice_to_draw.shape[1])

    THETA, PHI = np.meshgrid(theta, phi)

    # R = np.cos(PHI ** 2)
    R = np.ones_like(THETA)
    X = R * np.sin(PHI) * np.cos(THETA)
    Y = R * np.sin(PHI) * np.sin(THETA)
    Z = R * np.cos(PHI)
    C = np.divide(slice_to_draw, np.max(slice_to_draw))

    if axes is None:
        fig = plt.figure()

    if axes is None:
        axes = fig.add_subplot(1, 1, 1, projection='3d')

    my_col = cm.plasma(C)
    plot = axes.plot_surface(
        X, Y, Z, rstride=1, cstride=1, cmap=plt.get_cmap('plasma'),
        linewidth=0, antialiased=False, alpha=1, facecolors=my_col)

    # plt.colorbar(plot)
    axes.set_xlabel("X")
    axes.set_ylabel("Y")
    axes.set_zlabel("Z")

    val = [1.5, 0, 0]
    labels = ['x', 'y', 'z']
    colors = ['r', 'g', 'b']
    for v in range(3):
        x = [val[v - 0], -val[v - 0]]
        y = [val[v - 1], -val[v - 1]]
        z = [val[v - 2], -val[v - 2]]
        axes.plot(x, y, z, 'k-', linewidth=3)
        axes.text(val[v - 0], val[v - 1], val[v - 2], labels[v], color=colors[v], fontsize=20)

    # Hide everything else
    # Hide axes ticks
    axes.set_xticks([])
    axes.set_yticks([])
    axes.set_zticks([])
    # make the panes transparent
    axes.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    axes.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    axes.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
    # Hide box axes
    axes._axis3don = False

    # Expand to remove white space
    axes.set_xlim(np.array([-1, 1]) * .57)
    axes.set_ylim(np.array([-1, 1]) * .57)
    axes.set_zlim(np.array([-1, 1]) * .57)
    if axes is None:
        plt.show()


def draw_hemispherical_slices(slices_to_draw):
    fig, subplots = plt.subplots(1, len(slices_to_draw), subplot_kw=dict(projection='3d'))

    for slice, subplot in zip(slices_to_draw, subplots):
        draw_hemispherical_slice(slice, subplot)
    plt.show()


def draw_hemispherical_slice(slice_to_draw, axes=None):
    if isinstance(slice_to_draw, types.GeneratorType):
        slice_to_draw = get_next(slice_to_draw)
    slice_to_draw = np.squeeze(slice_to_draw)
    theta, phi = np.linspace(-np.pi, np.pi, slice_to_draw.shape[0]), np.linspace(0, np.pi / 2, slice_to_draw.shape[1])

    THETA, PHI = np.meshgrid(theta, phi)

    # R = np.cos(PHI ** 2)
    R = np.ones_like(THETA)
    X = R * np.sin(PHI) * np.cos(THETA)
    Y = R * np.sin(PHI) * np.sin(THETA)
    Z = R * np.cos(PHI)
    C = slice_to_draw / np.max(slice_to_draw)

    if axes is None:
        fig = plt.figure()

    if axes is None:
        axes = fig.add_subplot(1, 1, 1, projection='3d')

    my_col = cm.plasma(np.squeeze(C))
    axes.plot_surface(
        X, Y, Z, rstride=1, cstride=1, cmap=plt.get_cmap('plasma'),
        linewidth=0, antialiased=False, alpha=1, facecolors=my_col)

    # plt.colorbar(plot)
    axes.set_xlabel("X")
    axes.set_ylabel("Y")
    axes.set_zlabel("Z")

    if axes is None:
        plt.show()


def get_key_for_value(dictionary, value):
    for key, val in dictionary.items():
        if val == value:
            return key
    return None


if __name__ == '__main__':
    main()

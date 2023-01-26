from __future__ import annotations
import types

import jsonpickle
import numpy as np
from matplotlib import pyplot as plt, cm
from scipy.ndimage import gaussian_filter


def main():
    test_rwa = jsonpickle.decode(open("/home/r2_allen/Documents/EStimShape/dev_221110/rwa/test_rwa.json", "r").read())
    #find peaks of matrix
    # matrix = np.flip(test_rwa.matrix)
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
    indices_to_slice_per_peak = get_indices_to_slice(number_of_peaks, test_rwa,
                                                     ["angularPosition.theta", "angularPosition.phi"])
    slices_to_draw_per_peak = []
    for i in range(number_of_peaks):
        slice_to_draw = slice_matrix(indices_to_slice_per_peak[i], matrix, matrix_peaks[i])
        slices_to_draw_per_peak.append(slice_to_draw)
    draw_spherical_slices(slices_to_draw_per_peak)


    # 2D ANGULAR SLICE - orientation
    # find indices to slice
    indices_to_slice_per_peak = get_indices_to_slice(number_of_peaks, test_rwa,
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
    draw_one_d_field(matrix, matrix_peaks, number_of_peaks, test_rwa, "radialPosition")
    draw_one_d_field(matrix, matrix_peaks, number_of_peaks, test_rwa, "length")
    draw_one_d_field(matrix, matrix_peaks, number_of_peaks, test_rwa, "curvature")
    draw_one_d_field(matrix, matrix_peaks, number_of_peaks, test_rwa, "radius")
    plt.show()


def draw_one_d_field(matrix, matrix_peaks, number_of_peaks, test_rwa, field_name):
    indices_to_slice = get_indices_to_slice(number_of_peaks, test_rwa, [field_name])
    fig, axes = plt.subplots(number_of_peaks)
    for axes, (peak_index, indices_to_slice_for_peak) in zip(axes, enumerate(indices_to_slice)):
        slice_to_draw = slice_matrix(indices_to_slice_for_peak, matrix, matrix_peaks[peak_index])
        binner = test_rwa.binners_for_axes[str(indices_to_slice_for_peak[0])]
        draw_1D_slice(slice_to_draw, binner.bins, axes)
        # labels
        axes.set_xlabel(field_name)


def get_indices_to_slice(number_of_peaks, test_rwa, fields):
    indices_to_slice_per_peak = []
    for i in range(number_of_peaks):
        indices_for_axes = test_rwa.indices_for_axes
        indices_to_slice = [get_key_for_value(indices_for_axes, field) for field in fields]
        indices_to_slice = [int(index) for index in indices_to_slice]
        indices_to_slice_per_peak.append(indices_to_slice)
    return indices_to_slice_per_peak


def draw_1D_slice(slice_to_draw, bins, axes=None):
    if axes is None:
        fig = plt.figure()
        axes = fig.add_subplot(1, 1, 1)


    x_axis = [bin['py/newargs']['py/tuple'][1] for bin in bins]
    axes.plot(x_axis, next(slice_to_draw))


    #matrices_to_draw = test_rwa.matrix.sum(indices_to_slice)


def slice_matrix(indices_to_slice, matrix, matrix_peak_location):
    slice_indices_to_draw = list(matrix_peak_location)
    try:
        for index_to_slice in indices_to_slice:
            slice_indices_to_draw[index_to_slice] = slice(None)
    except TypeError:
        slice_indices_to_draw[indices_to_slice] = slice(None)

    slice_to_draw = matrix[tuple(slice_indices_to_draw)]
    yield slice_to_draw


def draw_spherical_slices(slices_to_draw):
    fig, subplots = plt.subplots(1, len(slices_to_draw), subplot_kw=dict(projection='3d'))

    for slice, subplot in zip(slices_to_draw, subplots):
        draw_spherical_slice(slice, subplot)
    plt.show()


def draw_spherical_slice(slice_to_draw, axes=None):
    if isinstance(slice_to_draw, types.GeneratorType):
        slice_to_draw = next(slice_to_draw)
    theta, phi = np.linspace(-np.pi, np.pi, slice_to_draw.shape[0]), np.linspace(0, np.pi, slice_to_draw.shape[1])

    THETA, PHI = np.meshgrid(theta, phi)

    # R = np.cos(PHI ** 2)
    R = np.ones_like(THETA)
    X = R * np.sin(PHI) * np.cos(THETA)
    Y = R * np.sin(PHI) * np.sin(THETA)
    Z = R * np.cos(PHI)
    C = slice_to_draw/np.max(slice_to_draw)

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

    if axes is None:
        plt.show()


def draw_hemispherical_slices(slices_to_draw):
    fig, subplots = plt.subplots(1, len(slices_to_draw), subplot_kw=dict(projection='3d'))

    for slice, subplot in zip(slices_to_draw, subplots):
        draw_hemispherical_slice(slice, subplot)
    plt.show()

def draw_hemispherical_slice(slice_to_draw, axes=None):
    if isinstance(slice_to_draw, types.GeneratorType):
        slice_to_draw = next(slice_to_draw)
    theta, phi = np.linspace(-np.pi, np.pi, slice_to_draw.shape[0]), np.linspace(0, np.pi/2, slice_to_draw.shape[1])

    THETA, PHI = np.meshgrid(theta, phi)

    # R = np.cos(PHI ** 2)
    R = np.ones_like(THETA)
    X = R * np.sin(PHI) * np.cos(THETA)
    Y = R * np.sin(PHI) * np.sin(THETA)
    Z = R * np.cos(PHI)
    C = slice_to_draw/np.max(slice_to_draw)

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

    if axes is None:
        plt.show()

def get_key_for_value(dictionary, value):
    for key, val in dictionary.items():
        if val == value:
            return key
    return None



if __name__ == '__main__':
    main()
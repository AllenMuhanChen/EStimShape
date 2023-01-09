import jsonpickle
import numpy as np
from matplotlib import pyplot as plt, cm


def main():
    test_rwa = jsonpickle.decode(open("/home/r2_allen/Documents/EStimShape/dev_221110/rwa/test_rwa.json", "r").read())
    #find peak of matrix
    matrix = test_rwa.matrix
    matrix_peak_location = np.unravel_index(np.argmax(matrix, axis=None), matrix.shape)
    matrix_peak_location = [int(index) for index in matrix_peak_location]

    #find indices to slice
    indices_for_axes = test_rwa.indices_for_axes
    indices_to_slice = [get_key_for_value(indices_for_axes, "angularPosition.theta"), get_key_for_value(indices_for_axes, "angularPosition.phi")]
    indices_to_slice = [int(index) for index in indices_to_slice]

    # 2D ANGULAR SLICE
    slice_to_draw = slice_matrix(indices_to_slice, matrix, matrix_peak_location)

    print(slice_to_draw)
    draw_angular_slice(slice_to_draw)

    # 1D ANGULAR SLICES
    fig, axes = plt.subplots(2)
    for axes_index, index_to_slice in enumerate(indices_to_slice):
        slice_to_draw = slice_matrix(index_to_slice, matrix, matrix_peak_location)

        bins = test_rwa.binners_for_axes[str(index_to_slice)].bins

        x_axis = [bin['py/newargs']['py/tuple'][1] for bin in bins]
        axes[axes_index].plot(x_axis, slice_to_draw)
        axes[axes_index].set_title("Slice for index " + str(index_to_slice))

        #labels

    plt.show()





    #matrices_to_draw = test_rwa.matrix.sum(indices_to_slice)


def slice_matrix(indices_to_slice, matrix, matrix_peak_location):
    slice_indices_to_draw = list(matrix_peak_location)
    try:
        for index_to_slice in indices_to_slice:
            slice_indices_to_draw[index_to_slice] = slice(None)
    except TypeError:
        slice_indices_to_draw[indices_to_slice] = slice(None)

    slice_to_draw = matrix[tuple(slice_indices_to_draw)]
    return slice_to_draw




def draw_angular_slice(slice_to_draw):
    theta, phi = np.linspace(-np.pi, np.pi, slice_to_draw.shape[0]), np.linspace(0, np.pi, slice_to_draw.shape[1])

    THETA, PHI = np.meshgrid(theta, phi)

    # R = np.cos(PHI ** 2)
    R = np.ones_like(THETA)
    X = R * np.sin(PHI) * np.cos(THETA)
    Y = R * np.sin(PHI) * np.sin(THETA)
    Z = R * np.cos(PHI)
    C = slice_to_draw/np.max(slice_to_draw)


    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, projection='3d')

    my_col = cm.plasma(C)
    plot = ax.plot_surface(
        X, Y, Z, rstride=1, cstride=1, cmap=plt.get_cmap('plasma'),
        linewidth=0, antialiased=False, alpha=1, facecolors=my_col)
    plt.colorbar(plot)
    plt.xlabel("x")
    plt.ylabel("y")
    plt.clabel("z")
    plt.show()
def get_key_for_value(dictionary, value):
    for key, val in dictionary.items():
        if val == value:
            return key
    return None



if __name__ == '__main__':
    main()
import jsonpickle
import numpy as np
from matplotlib import pyplot as plt, cm


def main():
    test_rwa = jsonpickle.decode(open("/home/r2_allen/Documents/EStimShape/dev_221110/rwa/test_rwa.json", "r").read())
    indices_for_axes = test_rwa.indices_for_axes
    indices_to_slice = [get_key_for_value(indices_for_axes, "angularPosition.theta"), get_key_for_value(indices_for_axes, "angularPosition.phi")]
    indices_to_slice = [int(index) for index in indices_to_slice]

    #find peak of matrix
    matrix = test_rwa.matrix
    matrix_peak_location = np.unravel_index(np.argmax(matrix, axis=None), matrix.shape)
    matrix_peak_location = [int(index) for index in matrix_peak_location]

    #slice matrix
    slice_indices_to_draw = list(matrix_peak_location)
    for index_to_slice in indices_to_slice:
        slice_indices_to_draw[index_to_slice] = slice(0, -1, 1)
    slice_to_draw = matrix[tuple(slice_indices_to_draw)]

    print(slice_to_draw)
    draw_angular_slice(slice_to_draw)
    #matrices_to_draw = test_rwa.matrix.sum(indices_to_slice)


def draw_angular_slice(slice_to_draw):
    theta, phi = np.linspace(-np.pi, np.pi, slice_to_draw.shape[0]), np.linspace(0, np.pi, slice_to_draw.shape[1])

    THETA, PHI = np.meshgrid(theta, phi)

    # R = np.cos(PHI ** 2)
    R = np.ones_like(THETA)
    X = R * np.sin(PHI) * np.cos(THETA)
    Y = R * np.sin(PHI) * np.sin(THETA)
    Z = R * np.cos(PHI)
    C = slice_to_draw

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1, projection='3d')

    my_col = cm.plasma(C)
    plot = ax.plot_surface(
        X, Y, Z, rstride=1, cstride=1, cmap=plt.get_cmap('plasma'),
        linewidth=0, antialiased=False, alpha=1, facecolors=my_col)
    plt.colorbar(plot)
    plt.show()
def get_key_for_value(dictionary, value):
    for key, val in dictionary.items():
        if val == value:
            return key
    return None



def draw_angle_tuning(self, matrix_to_draw):
    matrix = matrix_to_draw.matrix
    print(matrix)
    matrix_summed = matrix.sum(2)
    normalized_matrix = np.divide(matrix_summed, matrix.shape[2])
    plt.imshow(np.transpose(normalized_matrix), extent=[0, 1, 0, 1], origin="lower")
    labels = [label for label, label_indx in matrix_to_draw.indices_for_axes.items()]
    plt.xlabel(labels[0])
    plt.ylabel(labels[1])
    plt.colorbar()
    plt.show()

if __name__ == '__main__':
    main()
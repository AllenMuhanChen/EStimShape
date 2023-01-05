import jsonpickle
import numpy as np
from matplotlib import pyplot as plt


def main():
    test_rwa = jsonpickle.decode(open("test_rwa.json", "r").read())
    indices_for_axes = test_rwa.indices_for_axes
    print(test_rwa)

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
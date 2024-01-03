import jsonpickle
from matplotlib import pyplot as plt

from analysis.ga.mockga.mock_rwa_plot import plot_shaft_rwa


def main():
    test_rwa = jsonpickle.decode(open("/home/r2_allen/Documents/Ram GA/170508_r-45/rwa_shaft.json", "r").read())
    plot_shaft_rwa(test_rwa)
    plt.suptitle("Combined RWA")
    plt.show()


if __name__ == '__main__':
    main()
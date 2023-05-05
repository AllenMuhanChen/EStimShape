import math
from unittest import TestCase

import numpy as np
import scipy
import scipy.optimize as opt
from src.analysis.MultiCustomNormalTuningFunction import MultiCustomNormalTuningFunction, tuning_width_to_sigma, sigma_to_kappa


class TestTuningFunction(TestCase):
    def test_pdf(self):
        # Parameters for the TuningFunction
        periodic_indices = [0, 1]
        non_periodic_indices = [2, 3, 4, 5, 6, 7]
        mu = np.array([0.0, 0, 0, 0, 0, 0, 0, 0])
        tuning_widths = [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0]
        max_spike_rate = 100

        # Create an instance of the TuningFunction
        tuning_function = MultiCustomNormalTuningFunction(mu, tuning_widths, periodic_indices, non_periodic_indices, max_spike_rate)

        # Tolerance for comparing spike rates
        tolerance = 1e-6

        # Test the case where the stimulus is directly on top of the mean (spike rate should be 100)
        print("Max Response Case")
        x_on_mean = mu
        spike_rate_on_mean = tuning_function.response(x_on_mean)
        self.assertAlmostEqual(spike_rate_on_mean, 100, delta=tolerance)

        # Test the case where the stimulus is half the tuning_width away (spike rate should be around 50)
        print("Half Tuning Width Away Case")
        shift = tuning_widths[2]/2.0  # Shift by half the tuning width
        x_half_tuning_width_away = x_on_mean + np.array([0, 0, shift, 0, 0, 0, 0, 0])
        print("sigma: ", shift)
        print("x_half_tuning_width_away:", x_half_tuning_width_away)
        spike_rate_half_tuning_width_away = tuning_function.response(x_half_tuning_width_away)
        adjusted_spike_rate = spike_rate_half_tuning_width_away
        print("Adjusted spike rate at half the tuning width away:", adjusted_spike_rate)
        tolerance = 1e-6
        self.assertAlmostEqual(adjusted_spike_rate, 50, delta=tolerance)


    def test_1d_half_tuning_width_for_normal(self):
        from scipy.stats import norm
        import numpy as np
        import matplotlib.pyplot as plt

        tuning_width = 5
        distance_from_mean = tuning_width / 2
        x = 0
        sigma = tuning_width_to_sigma(tuning_width)
        y1 = norm.pdf(x, loc=0, scale=sigma)

        sigma = tuning_width_to_sigma(tuning_width)
        y2 = norm.pdf(x+distance_from_mean, loc=0, scale=sigma)

        self.assertAlmostEqual(y1, y2 * 2, delta=1e-6)

    def test_vonmises_at_tuning_width_of_pi_over_4(self):
        from scipy.stats import vonmises
        import numpy as np
        import matplotlib.pyplot as plt
        x = np.linspace(-np.pi, np.pi, 100)

        tuning_width = math.pi/4
        sigma = tuning_width_to_sigma(tuning_width)
        kappa = sigma_to_kappa(sigma)
        y = vonmises.pdf(x, kappa=kappa, loc=0)
        plt.plot(x, y)

        # Set the x-axis ticks
        x_ticks = np.arange(-np.pi, np.pi + 0.1, np.pi / 2)
        x_tick_labels = ['$-\pi$', '$-\dfrac{\pi}{2}$', '$0$', '$\dfrac{\pi}{2}$', '$\pi$']
        plt.xticks(x_ticks, x_tick_labels)

        self.assertEqual(vonmises.pdf(0, kappa=kappa, loc=0), vonmises.pdf(2 * np.pi, kappa=kappa, loc=0))
        plt.show()

    def test_normal(self):
        from scipy.stats import norm
        import numpy as np
        import matplotlib.pyplot as plt
        x = np.linspace(-10, 10, 100)

        tuning_width = 5
        sigma = tuning_width_to_sigma(tuning_width)
        y = norm.pdf(x, loc=0, scale=sigma)
        plt.plot(x, y)

        plt.show()



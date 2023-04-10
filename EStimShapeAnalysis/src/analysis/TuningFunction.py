import math

import numpy as np
import scipy


def tuning_width_to_sigma(tuning_width):
    """ Estimates the sigma parameter of a normal distribution from the tuning_width,
    which is represented as FWHM (Full Width at Half Maximum)"""
    sigma = tuning_width / (2 * math.sqrt(2 * math.log(2)))
    return sigma


def sigma_to_kappa(sigma):
    """ Estimates the kappa parameter of a von Mises distribution from the sigma parameter"""
    return 1 / sigma ** 2


class TuningFunction:
    """ Represents the tuning function of a neuron as the custom multivariate distribution that is a product of von Mises and Gaussian distributions.
    The von Mises distribution is used for the periodic dimensions and the Gaussian distribution is used for the non-periodic dimensions.
    Tuning widths are defined as FWHM (Full Width at Half Maximum), which is used to estimate a sigma.
    Sigmas are used to compute the kappa parameter of the von Mises distribution."""
    def __init__(self, mu: np.array, tuning_widths, periodic_indices, non_periodic_indices, max_spike_rate):
        self.periodic_indices = periodic_indices
        self.non_periodic_indices = non_periodic_indices
        self.mu = np.array(mu)  # Convert mu to a NumPy array
        self.max_spike_rate = max_spike_rate

        self.kappa = []
        self.sigmas = []

        for index, tuning_width in enumerate(tuning_widths):
            if index in periodic_indices:
                sigma = tuning_width_to_sigma(tuning_width)
                self.kappa.append(sigma_to_kappa(sigma))
            else:
                self.sigmas.append(tuning_width_to_sigma(tuning_width))

        self.sigmas = np.diag(self.sigmas)  # Convert sigmas to a diagonal covariance matrix

        non_periodic_mu = self.mu[non_periodic_indices]  # Get the mean values for non-periodic dimensions
        self.non_periodic_dist = scipy.stats.multivariate_normal(mean=non_periodic_mu, cov=self.sigmas)

        # Compute the maximum value of the PDF (used for normalizing the PDF)
        max_response = np.prod([
            scipy.stats.vonmises.pdf(self.mu[i], loc=self.mu[i], kappa=self.kappa[i]) for i in periodic_indices] +
            [self.non_periodic_dist.pdf(non_periodic_mu)
        ])
        self.max_response = max_response


    def pdf(self, x):
        x = np.array(x)
        von_mises_pdf = np.prod([scipy.stats.vonmises.pdf(x[i], loc=self.mu[i], kappa=self.kappa[i]) for i in self.periodic_indices])
        non_periodic_pdf = self.non_periodic_dist.pdf(x[self.non_periodic_indices])

        pdf_value = von_mises_pdf * non_periodic_pdf

        # Normalize the PDF value using the max_response and max_spike_rate
        pdf_value_normalized = pdf_value / self.max_response * self.max_spike_rate
        return pdf_value_normalized

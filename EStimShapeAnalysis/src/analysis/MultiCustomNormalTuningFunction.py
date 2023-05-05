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


class MultiCustomNormalTuningFunction:
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
        self.non_periodic_dist = scipy.stats.multivariate_normal(mean=non_periodic_mu, cov=self.sigmas**2)

        # Compute the maximum value of the PDF (used for normalizing the PDF)
        self.max_response = self.pdf(self.mu)



    def pdf(self, x):
        x = np.array(x)
        von_mises_pdf = np.prod([scipy.stats.vonmises.pdf(x[combined_index], loc=self.mu[combined_index], kappa=self.kappa[periodic_index]) for periodic_index, combined_index in enumerate(self.periodic_indices)])
        non_periodic_pdf = self.non_periodic_dist.pdf(x[self.non_periodic_indices])
        pdf_value = von_mises_pdf * non_periodic_pdf
        return pdf_value

    def response(self, x):
        return self.pdf(x) / self.max_response * self.max_spike_rate

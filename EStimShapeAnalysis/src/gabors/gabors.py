import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
from colorspacious import cspace_convert


def create_gabor(size, lambda_px, theta, sigma, phase, offset):
    """Create a Gabor patch centered at (0,0)."""
    y, x = np.meshgrid(np.linspace(-size / 2, size / 2, size), np.linspace(-size / 2, size / 2, size))

    # Rotate coordinates
    x_theta = x * np.cos(theta) + y * np.sin(theta)
    y_theta = -x * np.sin(theta) + y * np.cos(theta)

    # Calculate grating
    grating = np.sin(2 * np.pi * x_theta / lambda_px + phase)

    # Calculate Gaussian
    gaussian = np.exp(-(x ** 2 + y ** 2) / (2 * sigma ** 2))

    # Combine grating and Gaussian
    gabor = grating * gaussian

    # Normalize to [-1, 1] range
    gabor = (gabor - gabor.min()) / (gabor.max() - gabor.min()) * 2 - 1

    return offset + gabor * (1 - offset)


def create_isochromatic_gabor(size, lambda_px, theta, sigma, phase, color, background="white"):
    """Create an isochromatic Gabor patch."""
    gabor = create_gabor(size, lambda_px, theta, sigma, phase, 0.5)

    if background == "white":
        return plt.cm.colors.to_rgb(color) * gabor[..., np.newaxis] + (1 - gabor)[..., np.newaxis]
    elif background == "black":
        return plt.cm.colors.to_rgb(color) * gabor[..., np.newaxis]


def create_isoluminant_gabor(size, lambda_px, theta, sigma, phase, color1, color2):
    """Create an isoluminant Gabor patch."""
    gabor = create_gabor(size, lambda_px, theta, sigma, phase, 0.5)

    lab1 = cspace_convert(plt.cm.colors.to_rgb(color1), "sRGB1", "CAM02-UCS")
    lab2 = cspace_convert(plt.cm.colors.to_rgb(color2), "sRGB1", "CAM02-UCS")

    # Interpolate in CAM02-UCS space
    lab_gabor = lab1[np.newaxis, np.newaxis, :] * (1 - gabor)[..., np.newaxis] + lab2[np.newaxis, np.newaxis, :] * \
                gabor[..., np.newaxis]

    # Convert back to sRGB
    return cspace_convert(lab_gabor, "CAM02-UCS", "sRGB1")


def create_mixed_gabor(size, lambda_px_color, theta_color, sigma_color, phase_color, color1, color2,
                       lambda_px_lum, theta_lum, sigma_lum, phase_lum, lum_weight=0.5):
    """Create a mixed Gabor patch with both color and luminance changes."""
    color_gabor = create_isoluminant_gabor(size, lambda_px_color, theta_color, sigma_color, phase_color, color1, color2)
    lum_gabor = create_isochromatic_gabor(size, lambda_px_lum, theta_lum, sigma_lum, phase_lum, "white", "black")

    # Combine color and luminance Gabors
    mixed_gabor = color_gabor * (1 - lum_weight) + lum_gabor * lum_weight

    # Clip values to ensure they're in the valid range
    return np.clip(mixed_gabor, 0, 1)


def create_aligned_mixed_gabor(size, lambda_px, theta, sigma, phase, color1, color2, lum_weight=0.5):
    """Create an aligned mixed Gabor patch where color and luminance changes are perfectly aligned."""
    return create_mixed_gabor(size, lambda_px, theta, sigma, phase, color1, color2,
                              lambda_px, theta, sigma, phase, lum_weight)


def create_misaligned_mixed_gabor(size, lambda_px, theta, sigma, phase, color1, color2, lum_weight=0.5):
    """Create a misaligned mixed Gabor patch where color and luminance changes are 90 degrees apart."""
    return create_mixed_gabor(size, lambda_px, theta, sigma, phase, color1, color2,
                              lambda_px, theta, sigma, phase+np.pi/2, lum_weight)


# Example usage
size = 256
lambda_px = 20
theta = np.pi / 4
sigma = 40
phase = 0

# Isochromatic (black/white)
bw_gabor = create_isochromatic_gabor(size, lambda_px, theta, sigma, phase, "black", "white")

# Isochromatic (red/black)
rb_gabor = create_isochromatic_gabor(size, lambda_px, theta, sigma, phase, "red", "black")

# Isoluminant (red/green)
rg_gabor = create_isoluminant_gabor(size, lambda_px, theta, sigma, phase, "red", "green")

# Isoluminant (blue/yellow)
by_gabor = create_isoluminant_gabor(size, lambda_px, theta, sigma, phase, "blue", "yellow")

# Aligned mixed Gabor (red/green on top of brightness)
aligned_mixed_gabor = create_aligned_mixed_gabor(size, lambda_px, theta, sigma, phase, "red", "green", 0.3)

# Misaligned mixed Gabor (red/green on top of brightness)
misaligned_mixed_gabor = create_misaligned_mixed_gabor(size, lambda_px, theta, sigma, phase, "red", "green", 0.3)

# Display results
fig, axs = plt.subplots(2, 3, figsize=(15, 10))
axs[0, 0].imshow(bw_gabor, cmap='gray')
axs[0, 0].set_title("Brightness Contrast Only (White)")
axs[0, 1].imshow(rb_gabor)
axs[0, 1].set_title("Brightness Contrast Only (Red)")
axs[0, 2].imshow(misaligned_mixed_gabor)
axs[0, 2].set_title("Mixed Contrast (Misaligned)")
axs[1, 0].imshow(rg_gabor)
axs[1, 0].set_title("Chromatic Contrast Only (Red/Green)")
axs[1, 1].imshow(by_gabor)
axs[1, 1].set_title("Chromatic Contrast Only Blue/Yellow")
axs[1, 2].imshow(aligned_mixed_gabor)
axs[1, 2].set_title("Mixed Contrast (Aligned)")
plt.tight_layout()
plt.show()
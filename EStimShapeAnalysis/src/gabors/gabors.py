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
    """Create a truly isoluminant Gabor patch."""
    gabor = create_gabor(size, lambda_px, theta, sigma, phase, 0.5)

    jab1 = cspace_convert(plt.cm.colors.to_rgb(color1), "sRGB1", "CAM02-UCS")
    jab2 = cspace_convert(plt.cm.colors.to_rgb(color2), "sRGB1", "CAM02-UCS")

    # Use the average lightness (J) for both colors
    J_avg = (jab1[0] + jab2[0]) / 2
    jab1[0] = J_avg
    jab2[0] = J_avg

    # Interpolate only the chromatic components (a and b)
    jab_gabor = np.zeros((*gabor.shape, 3))
    jab_gabor[..., 0] = J_avg
    jab_gabor[..., 1:] = jab1[np.newaxis, np.newaxis, 1:] * (1 - gabor)[..., np.newaxis] + \
                         jab2[np.newaxis, np.newaxis, 1:] * gabor[..., np.newaxis]

    # Convert back to sRGB
    return cspace_convert(jab_gabor, "CAM02-UCS", "sRGB1")


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
lambda_px = 40
theta = np.pi / 4
sigma = 40
phase = 0

# Generate Gabor patches
bw_gabor = create_isochromatic_gabor(size, lambda_px, theta, sigma, phase, "black", "white")
rb_gabor = create_isochromatic_gabor(size, lambda_px, theta, sigma, phase, "red", "black")
rg_gabor = create_isoluminant_gabor(size, lambda_px, theta, sigma, phase, "red", "green")
by_gabor = create_isoluminant_gabor(size, lambda_px, theta, sigma, phase, "cyan", "orange")
aligned_mixed_gabor = create_aligned_mixed_gabor(size, lambda_px, theta, sigma, phase, "red", "green", 0.3)
misaligned_mixed_gabor = create_misaligned_mixed_gabor(size, lambda_px, theta, sigma, phase, "red", "green", 0.3)

# Display results
fig, axs = plt.subplots(2, 3, figsize=(18, 12))  # Increased figure size

gabors = [bw_gabor, rb_gabor, misaligned_mixed_gabor,
          rg_gabor, by_gabor, aligned_mixed_gabor]

titles = ["Brightness Contrast Only (White)",
          "Brightness Contrast Only (Red)",
          "Mixed Contrast (Misaligned)",
          "Chromatic Contrast Only (Red/Green)",
          "Chromatic Contrast Only (Cyan/Orange)",
          "Mixed Contrast (Aligned)"]

for ax, gabor, title in zip(axs.flatten(), gabors, titles):
    im = ax.imshow(gabor, cmap='gray' if gabor.ndim == 2 else None)
    ax.set_title(title, fontsize=16, pad=20)  # Increased font size and padding
    ax.axis('off')  # This removes all axis ticks, numbers, and labels

plt.tight_layout()
plt.show()
import numpy as np
import matplotlib.pyplot as plt
from colorsys import hls_to_rgb

def create_saturation_grating(size, lambda_px, theta, phase):
    """Create a grating based on saturation modulation in HSL color space."""
    y, x = np.meshgrid(np.linspace(-size / 2, size / 2, size), np.linspace(-size / 2, size / 2, size))

    # Rotate coordinates
    x_theta = x * np.cos(theta) + y * np.sin(theta)

    # Calculate grating (saturation modulation)
    saturation = (np.sin(2 * np.pi * x_theta / lambda_px + phase) + 1) / 2  # Range [0, 1]

    # Create the HSL image
    hue = 1  # Red hue
    lightness = 0.5  # Middle lightness

    # Convert HSL to RGB
    rgb_grating = np.array([hls_to_rgb(hue, lightness, s) for s in saturation.flatten()])
    rgb_grating = rgb_grating.reshape(size, size, 3)

    return rgb_grating

# Parameters
size = 256
lambda_px = 20
theta = np.pi / 4
phase = 0

# Generate the saturation-based grating
saturation_grating = create_saturation_grating(size, lambda_px, theta, phase)

# Display the result
plt.figure(figsize=(10, 10))
plt.imshow(saturation_grating)
plt.title("Saturation-based Grating (Red Hue)", fontsize=16)
plt.axis('off')
plt.show()
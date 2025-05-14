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


def create_disk_mask(size, disk_radius, fade_sigma):
    """
    Create a disk mask with a Gaussian fade at the edges.

    Parameters:
    - size: Size of the image in pixels
    - disk_radius: Radius of the solid disk (in pixels)
    - fade_sigma: Sigma parameter for the Gaussian fade beyond the disk

    Returns:
    - A mask with values 1 inside the disk, fading to 0 outside
    """
    y, x = np.meshgrid(np.linspace(-size / 2, size / 2, size), np.linspace(-size / 2, size / 2, size))

    # Calculate distance from center for each pixel
    distance = np.sqrt(x ** 2 + y ** 2)

    # Create the mask
    mask = np.ones_like(distance)

    # Apply Gaussian fade outside the disk radius
    outside_disk = distance > disk_radius
    mask[outside_disk] = np.exp(-((distance[outside_disk] - disk_radius) ** 2) / (2 * fade_sigma ** 2))

    return mask


def create_isochromatic_gabor(size, lambda_px, theta, sigma, phase, color, background_color=(0, 0, 0)):
    """Create an isochromatic Gabor patch that transitions between a color and black, on a black background."""
    # Generate the raw gabor pattern (without Gaussian modulation)
    y, x = np.meshgrid(np.linspace(-size / 2, size / 2, size), np.linspace(-size / 2, size / 2, size))
    x_theta = x * np.cos(theta) + y * np.sin(theta)
    grating = np.sin(2 * np.pi * x_theta / lambda_px + phase)

    # Normalize to [0, 1] range for easier color interpolation
    grating = (grating + 1) / 2

    # Create a disk mask with Gaussian fade at edges
    disk_radius = size / 4  # Disk radius as 1/4 of the image size
    fade_sigma = sigma / 2  # Sigma for the fade
    mask = create_disk_mask(size, disk_radius, fade_sigma)

    # Convert colors to RGB
    if isinstance(background_color, tuple) or isinstance(background_color, list):
        background_rgb = np.array(background_color)
    elif isinstance(background_color, float) or isinstance(background_color, int):
        background_rgb = np.ones(3) * background_color
    else:
        background_rgb = plt.cm.colors.to_rgb(background_color)

    foreground_rgb = plt.cm.colors.to_rgb(color)
    black_rgb = np.zeros(3)

    # Create the result array
    result = np.zeros((*grating.shape, 3))

    # Fill with background color first
    for i in range(3):
        result[..., i] = background_rgb[i]

    # Apply the Gabor pattern within the mask area
    for i in range(3):
        # For each pixel, interpolate between color and black based on grating value
        color_black_interp = foreground_rgb[i] * grating + black_rgb[i] * (1 - grating)

        # Apply this interpolation only within the masked area
        result[..., i] = result[..., i] * (1 - mask) + color_black_interp * mask

    return np.clip(result, 0, 1)


def calculate_color_luminance(color):
    """Calculate the luminance of a color in CAM02-UCS space."""
    jab = cspace_convert(plt.cm.colors.to_rgb(color), "sRGB1", "CAM02-UCS")
    return jab[0]  # Return just the J (luminance) component


def calculate_isochromatic_luminance(color):
    """Calculate the average luminance of a color-to-black transition."""
    # Convert color to JAB color space
    jab_color = cspace_convert(plt.cm.colors.to_rgb(color), "sRGB1", "CAM02-UCS")
    # Black in JAB space
    jab_black = cspace_convert(np.zeros(3), "sRGB1", "CAM02-UCS")

    # Return the average luminance
    return (jab_color[0] + jab_black[0]) / 2


def create_isoluminant_gabor(size, lambda_px, theta, sigma, phase, color1, color2, target_luminance=None,
                             background_color=(0, 0, 0)):
    """
    Create a truly isoluminant Gabor patch that transitions between two colors, on a black background.

    Parameters:
    - target_luminance: If provided, sets both colors to this specific luminance.
                       If None, uses the average luminance of the two colors.
    """
    # Generate the raw gabor pattern (without Gaussian modulation)
    y, x = np.meshgrid(np.linspace(-size / 2, size / 2, size), np.linspace(-size / 2, size / 2, size))
    x_theta = x * np.cos(theta) + y * np.sin(theta)
    grating = np.sin(2 * np.pi * x_theta / lambda_px + phase)

    # Normalize to [0, 1] range for easier color interpolation
    grating = (grating + 1) / 2

    # Create a disk mask with Gaussian fade at edges
    disk_radius = size / 4  # Disk radius as 1/4 of the image size
    fade_sigma = sigma / 2  # Sigma for the fade
    mask = create_disk_mask(size, disk_radius, fade_sigma)

    # Convert colors to JAB color space
    jab1 = cspace_convert(plt.cm.colors.to_rgb(color1), "sRGB1", "CAM02-UCS")
    jab2 = cspace_convert(plt.cm.colors.to_rgb(color2), "sRGB1", "CAM02-UCS")

    # Set the luminance (J) for both colors
    if target_luminance is not None:
        # Use the provided target luminance
        J_target = target_luminance
    else:
        # Use the average luminance of the two colors
        J_target = (jab1[0] + jab2[0]) / 2

    jab1[0] = J_target
    jab2[0] = J_target

    # Convert background to RGB
    if isinstance(background_color, tuple) or isinstance(background_color, list):
        background_rgb = np.array(background_color)
    elif isinstance(background_color, float) or isinstance(background_color, int):
        background_rgb = np.ones(3) * background_color
    else:
        background_rgb = plt.cm.colors.to_rgb(background_color)

    # Create the JAB gabor pattern
    jab_gabor = np.zeros((*grating.shape, 3))
    jab_gabor[..., 0] = J_target  # Constant luminance

    # Interpolate between the two colors based on grating values
    for i in range(1, 3):  # Just the chromatic components a and b
        jab_gabor[..., i] = jab1[i] * (1 - grating) + jab2[i] * grating

    # Convert JAB gabor to RGB
    rgb_gabor = cspace_convert(jab_gabor, "CAM02-UCS", "sRGB1")
    rgb_gabor = np.clip(rgb_gabor, 0, 1)

    # Create the result array filled with background color
    result = np.zeros((*grating.shape, 3))
    for i in range(3):
        result[..., i] = background_rgb[i]

    # Apply the Gabor pattern only within the masked area
    for i in range(3):
        result[..., i] = result[..., i] * (1 - mask) + rgb_gabor[..., i] * mask

    return result

    # Convert background to RGB
    if isinstance(background_color, tuple) or isinstance(background_color, list):
        background_rgb = np.array(background_color)
    elif isinstance(background_color, float) or isinstance(background_color, int):
        background_rgb = np.ones(3) * background_color
    else:
        background_rgb = plt.cm.colors.to_rgb(background_color)

    # Create the JAB gabor pattern
    jab_gabor = np.zeros((*grating.shape, 3))
    jab_gabor[..., 0] = J_avg  # Constant luminance

    # Interpolate between the two colors based on grating values
    for i in range(1, 3):  # Just the chromatic components a and b
        jab_gabor[..., i] = jab1[i] * (1 - grating) + jab2[i] * grating

    # Convert JAB gabor to RGB
    rgb_gabor = cspace_convert(jab_gabor, "CAM02-UCS", "sRGB1")
    rgb_gabor = np.clip(rgb_gabor, 0, 1)

    # Create the result array filled with background color
    result = np.zeros((*grating.shape, 3))
    for i in range(3):
        result[..., i] = background_rgb[i]

    # Apply the Gabor pattern only within the masked area
    for i in range(3):
        result[..., i] = result[..., i] * (1 - mask) + rgb_gabor[..., i] * mask

    return result


# Example usage
size = 256
lambda_px = 40
theta = np.pi / 4
sigma = 40
phase = 0
gray_level = 0.5  # 50% gray background

# Generate Gabor patches with black background
background_color = (0, 0, 0)  # Black background

# Create isochromatic Gabors
red_gabor = create_isochromatic_gabor(size, lambda_px, theta, sigma, phase, "red", background_color)
green_gabor = create_isochromatic_gabor(size, lambda_px, theta, sigma, phase, "green", background_color)
cyan_gabor = create_isochromatic_gabor(size, lambda_px, theta, sigma, phase, "cyan", background_color)
orange_gabor = create_isochromatic_gabor(size, lambda_px, theta, sigma, phase, "orange", background_color)

# Calculate the target luminance for isoluminant Gabors based on the isochromatic versions
red_iso_lum = calculate_isochromatic_luminance("red")
green_iso_lum = calculate_isochromatic_luminance("green")
red_green_lum = (red_iso_lum + green_iso_lum) / 2  # Average of the red and green isochromatic luminances

cyan_iso_lum = calculate_isochromatic_luminance("cyan")
orange_iso_lum = calculate_isochromatic_luminance("orange")
cyan_orange_lum = (cyan_iso_lum + orange_iso_lum) / 2  # Average of the cyan and orange isochromatic luminances

# Create isoluminant Gabors with the target luminances
red_green_gabor = create_isoluminant_gabor(size, lambda_px, theta, sigma, phase, "red", "green",
                                           target_luminance=red_green_lum, background_color=background_color)
cyan_orange_gabor = create_isoluminant_gabor(size, lambda_px, theta, sigma, phase, "cyan", "orange",
                                             target_luminance=cyan_orange_lum, background_color=background_color)

# Display results
fig, axs = plt.subplots(2, 3, figsize=(20, 16), facecolor='white')  # Black figure background
plt.rcParams.update({'text.color': 'black'})  # White text

gabors = [red_gabor, green_gabor, red_green_gabor,
          cyan_gabor, orange_gabor, cyan_orange_gabor]

titles = ["Red Isochromatic",
          "Green Isochromatic",
          "Red/Green Isoluminant",
          "Cyan Isochromatic",
          "Orange Isochromatic",
          "Cyan/Orange Isoluminant"]

for ax, gabor, title in zip(axs.flatten(), gabors, titles):
    im = ax.imshow(gabor, cmap='gray' if gabor.ndim == 2 else None)
    ax.set_title(title, fontsize=36, pad=20)  # Increased font size and padding
    ax.axis('off')  # This removes all axis ticks, numbers, and labels
    ax.set_facecolor('black')  # Black subplot background

plt.tight_layout()
plt.show()

for ax, gabor, title in zip(axs.flatten(), gabors, titles):
    im = ax.imshow(gabor, cmap='gray' if gabor.ndim == 2 else None)
    ax.set_title(title, fontsize=16, pad=20)  # Increased font size and padding
    ax.axis('off')  # This removes all axis ticks, numbers, and labels

plt.tight_layout()
plt.show()
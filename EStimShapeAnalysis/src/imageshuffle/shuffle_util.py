import numpy as np
from matplotlib import pyplot as plt
from scipy import fftpack
from skimage import color as skcolor


def plot_orientation_spectrum(img, plot_color, label, alpha=0.7):
    """Plot orientation-specific power spectrum"""
    if img.shape[2] >= 3:
        # Convert to grayscale for spectrum analysis
        gray = skcolor.rgb2gray(img[:, :, :3])
    else:
        gray = img[:, :, 0]

    # Apply the same masking as used in processing for fair comparison
    if img.shape[2] == 4:  # Image has alpha channel
        rgb_for_background = img[:, :, :3]
    else:  # RGB image
        rgb_for_background = img

    # Find background pixel
    pixels = rgb_for_background.reshape(-1, rgb_for_background.shape[-1])
    unique_pixels, counts = np.unique(pixels, axis=0, return_counts=True)
    background_pixel = unique_pixels[np.argmax(counts)]

    # Create mask
    if img.shape[2] == 4:  # Image has alpha channel
        mask = np.logical_not(np.all(img[:, :, :3] == background_pixel, axis=-1))
    else:  # RGB image
        mask = np.logical_not(np.all(img == background_pixel, axis=-1))

    # Apply same soft masking to analysis:
    from scipy import ndimage
    soft_mask = ndimage.gaussian_filter(mask.astype(float), sigma=5)
    gray_masked = gray * soft_mask  # Consistent with processing

    # Calculate 2D FFT
    f_transform = fftpack.fft2(gray_masked)
    f_transform_shifted = np.fft.fftshift(f_transform)

    # Calculate power spectrum
    power_spectrum = np.abs(f_transform_shifted) ** 2

    # Get image dimensions and center
    h, w = gray.shape
    center_y, center_x = h // 2, w // 2

    # Simply exclude ONLY the DC component (cleanest approach)
    power_spectrum_no_dc = power_spectrum.copy()
    power_spectrum_no_dc[center_y, center_x] = 0

    # Create coordinate arrays
    y, x = np.ogrid[-center_y:h - center_y, -center_x:w - center_x]

    # Calculate angles (orientation) for each point
    angles = np.arctan2(y, x)

    # Convert to degrees and normalize to 0-180 range (since power spectrum is symmetric)
    angles_deg = np.degrees(angles) % 180

    # Create orientation bins
    orientation_bins = np.arange(0, 181, 5)  # 5-degree bins from 0 to 180
    orientation_power = np.zeros(len(orientation_bins) - 1)

    # Calculate power for each orientation bin
    for i in range(len(orientation_bins) - 1):
        angle_min = orientation_bins[i]
        angle_max = orientation_bins[i + 1]

        # Create mask for this orientation range
        angle_mask = (angles_deg >= angle_min) & (angles_deg < angle_max)

        # Sum power in this orientation
        if np.any(angle_mask):
            orientation_power[i] = np.mean(power_spectrum_no_dc[angle_mask])

    # NORMALIZE BY TOTAL POWER (this was missing!)
    total_power = np.sum(orientation_power)
    if total_power > 0:
        orientation_power_normalized = orientation_power / total_power
    else:
        orientation_power_normalized = orientation_power

    # Plot orientation spectrum
    bin_centers = (orientation_bins[:-1] + orientation_bins[1:]) / 2
    plt.plot(bin_centers, orientation_power_normalized, color=plot_color, alpha=alpha, label=label, linewidth=2)


def plot_2d_power_spectrum_diff(original_img, randomized_img):
    """Plot 2D power spectrum difference visualization"""

    def get_2d_power_spectrum(img):
        if img.shape[2] >= 3:
            gray = skcolor.rgb2gray(img[:, :, :3])
        else:
            gray = img[:, :, 0]

        # Apply the same masking as used in processing for fair comparison
        if img.shape[2] == 4:  # Image has alpha channel
            rgb_for_background = img[:, :, :3]
        else:  # RGB image
            rgb_for_background = img

        # Find background pixel
        pixels = rgb_for_background.reshape(-1, rgb_for_background.shape[-1])
        unique_pixels, counts = np.unique(pixels, axis=0, return_counts=True)
        background_pixel = unique_pixels[np.argmax(counts)]

        # Create mask
        if img.shape[2] == 4:  # Image has alpha channel
            mask = np.logical_not(np.all(img[:, :, :3] == background_pixel, axis=-1))
        else:  # RGB image
            mask = np.logical_not(np.all(img == background_pixel, axis=-1))

        # Apply mask to gray image (same as processing)
        gray_masked = gray * mask

        f_transform = fftpack.fft2(gray_masked)
        f_transform_shifted = np.fft.fftshift(f_transform)
        power_spectrum = np.abs(f_transform_shifted) ** 2

        # Exclude DC component for consistency with orientation analysis
        h, w = gray.shape
        center_y, center_x = h // 2, w // 2
        power_spectrum_no_dc = power_spectrum.copy()
        power_spectrum_no_dc[center_y, center_x] = 0

        return power_spectrum_no_dc

    orig_power = get_2d_power_spectrum(original_img)
    rand_power = get_2d_power_spectrum(randomized_img)

    # Normalize by total power for fair comparison
    orig_total = np.sum(orig_power)
    rand_total = np.sum(rand_power)

    if orig_total > 0 and rand_total > 0:
        orig_power_norm = orig_power / orig_total
        rand_power_norm = rand_power / rand_total
        power_diff = rand_power_norm - orig_power_norm
    else:
        power_diff = rand_power - orig_power

    # Display the difference
    im = plt.imshow(power_diff, cmap='RdBu_r', origin='lower')
    plt.colorbar(im, label='Normalized Power Difference')
    plt.xlabel('Frequency X')
    plt.ylabel('Frequency Y')

#!/usr/bin/env python3
"""
Magnitude shuffle processing script for Java integration via direct process execution.
Shuffles the magnitude while preserving phase information, color distribution,
and average luminance through histogram matching.

Usage: python magnitude_processing.py <input_path> <output_path> [--keep-intermediates]
"""

import sys
import os
import argparse
import numpy as np
from PIL import Image
from scipy import fftpack
from skimage import color as skcolor, exposure
import matplotlib.pyplot as plt
import matplotlib

matplotlib.use('Agg')  # Use non-interactive backend for server environments


def magnitude_randomize_preserve_contrast(image, mask=None):
    """
    Shuffles the magnitude while preserving phase information, color distribution,
    and average luminance through histogram matching.

    Args:
        image: Input image (can be color with alpha channel)
        mask: Binary mask (1 inside region to randomize, 0 outside)

    Returns:
        Magnitude-randomized image with preserved statistical properties
    """
    # Create a copy of the original image
    result = image.copy().astype(np.float32)

    # Extract alpha channel if exists
    if image.shape[2] == 4:
        rgb = result[:, :, :3]
        alpha = result[:, :, 3:4]
    else:
        rgb = result
        alpha = None

    # Handle mask creation if not provided
    if mask is None:
        # Find the most common pixel value (background)
        if image.shape[2] == 4:  # Image has alpha channel
            rgb_for_background = image[:, :, :3]
        else:  # RGB image
            rgb_for_background = image

        # Reshape to (num_pixels, num_channels) for easier processing
        pixels = rgb_for_background.reshape(-1, rgb_for_background.shape[-1])

        # Find unique pixels and their counts
        unique_pixels, counts = np.unique(pixels, axis=0, return_counts=True)

        # Get the most common pixel value (background)
        background_pixel = unique_pixels[np.argmax(counts)]

        # Create a mask where pixels are NOT equal to the background
        if image.shape[2] == 4:  # Image has alpha channel
            mask = np.logical_not(np.all(image[:, :, :3] == background_pixel, axis=-1))
        else:  # RGB image
            mask = np.logical_not(np.all(image == background_pixel, axis=-1))

    # Normalize RGB to 0-1 range if needed
    if rgb.max() > 1.0:
        rgb_norm = rgb / 255.0
    else:
        rgb_norm = rgb

    # Convert to LAB color space
    lab = skcolor.rgb2lab(rgb_norm)

    # Extract luminance channel
    L = lab[:, :, 0]  # Luminance channel

    # Save the original luminance values in the masked region for histogram matching later
    L_masked_orig = L[mask]

    # Apply mask to luminance channel
    L_roi = L * mask

    # Apply Fourier transform to the ROI
    fft_L_roi = fftpack.fft2(L_roi)

    # Extract phase (which we'll keep)
    phase = np.angle(fft_L_roi)

    # Extract original magnitude (which we'll randomize)
    original_magnitude = np.abs(fft_L_roi)

    # Create a randomized version of the magnitude spectrum
    # We'll randomize by shuffling the magnitude values while preserving their distribution
    magnitude_values = original_magnitude.flatten()
    np.random.shuffle(magnitude_values)
    shuffled_magnitude = magnitude_values.reshape(original_magnitude.shape)

    # Preserve DC component (0,0) magnitude to maintain average intensity
    shuffled_magnitude[0, 0] = original_magnitude[0, 0]

    # Combine shuffled magnitude with original phase
    real_part = shuffled_magnitude * np.cos(phase)
    imag_part = shuffled_magnitude * np.sin(phase)
    randomized_fft = real_part + 1j * imag_part

    # Apply inverse Fourier transform
    randomized_L_roi = np.real(fftpack.ifft2(randomized_fft))

    # Create a new luminance channel that replaces the masked region
    randomized_L = L.copy()
    randomized_L[mask] = randomized_L_roi[mask]

    # Now perform histogram matching to ensure the luminance distribution is preserved
    # Extract the randomized values in the masked region
    randomized_values = randomized_L[mask]

    # Match the histogram of the randomized values to the original values
    matched_values = exposure.match_histograms(
        randomized_values.reshape(-1, 1),
        L_masked_orig.reshape(-1, 1)
    ).flatten()

    # Replace the values in the randomized luminance channel
    L_matched = L.copy()
    L_matched[mask] = matched_values

    # Recombine LAB channels
    lab_new = lab.copy()
    lab_new[:, :, 0] = L_matched

    # Convert back to RGB
    rgb_new = skcolor.lab2rgb(lab_new)

    # Scale back to original range if needed
    if image.max() > 1.0:
        rgb_new = rgb_new * 255.0

    # Reattach alpha channel if needed
    if alpha is not None:
        result = np.concatenate([rgb_new, alpha], axis=2)
    else:
        result = rgb_new

    # Convert back to original data type
    if image.dtype == np.uint8:
        result = np.clip(result, 0, 255).astype(np.uint8)

    return result


def create_analysis_plot(original_image, randomized_image, output_path):
    """
    Create analysis plot showing histograms and power spectrum comparison.

    Args:
        original_image: Original image array
        randomized_image: Magnitude-shuffled image array
        output_path: Path to save the analysis plot
    """

    def analyze_image_stats(img, name="Image"):
        if img.shape[2] == 4:  # Handle alpha channel
            rgb = img[:, :, :3]
        else:
            rgb = img

        # Normalize if needed
        if rgb.max() > 1.0:
            rgb_norm = rgb / 255.0
        else:
            rgb_norm = rgb

        # Convert to LAB
        lab = skcolor.rgb2lab(rgb_norm)
        L = lab[:, :, 0]  # Luminance

        # Create mask for non-background pixels (find most common pixel as background)
        if img.shape[2] == 4:  # Image has alpha channel
            rgb_for_background = img[:, :, :3]
        else:  # RGB image
            rgb_for_background = img

        # Reshape to (num_pixels, num_channels) for easier processing
        pixels = rgb_for_background.reshape(-1, rgb_for_background.shape[-1])

        # Find unique pixels and their counts
        unique_pixels, counts = np.unique(pixels, axis=0, return_counts=True)

        # Get the most common pixel value (background)
        background_pixel = unique_pixels[np.argmax(counts)]

        # Create mask for non-background pixels
        if img.shape[2] == 4:  # Image has alpha channel
            mask = np.logical_not(np.all(img[:, :, :3] == background_pixel, axis=-1))
        else:  # RGB image
            mask = np.logical_not(np.all(img == background_pixel, axis=-1))

        # Get masked luminance values
        L_masked = L[mask]

        # Calculate statistics
        mean = np.mean(L_masked)
        std = np.std(L_masked)
        min_val = np.min(L_masked)
        max_val = np.max(L_masked)

        return mean, std, min_val, max_val, L_masked

    def plot_power_spectrum(img, plot_color, label, alpha=0.7):
        if img.shape[2] >= 3:
            # Convert to grayscale for spectrum analysis
            gray = skcolor.rgb2gray(img[:, :, :3])
        else:
            gray = img[:, :, 0]

        # Calculate 2D FFT
        f_transform = fftpack.fft2(gray)
        f_transform_shifted = np.fft.fftshift(f_transform)

        # Calculate power spectrum
        power_spectrum = np.abs(f_transform_shifted) ** 2

        # Calculate radial average (1D power spectrum)
        h, w = gray.shape
        center_y, center_x = h // 2, w // 2
        y, x = np.ogrid[-center_y:h - center_y, -center_x:w - center_x]
        r = np.sqrt(x * x + y * y)
        r = r.astype(np.int32)

        # Bin the radial values
        radial_bins = np.bincount(r.ravel(), weights=power_spectrum.ravel())
        radial_bins_count = np.bincount(r.ravel())
        radial_bins = radial_bins / radial_bins_count

        # Plot log-log scale
        plt.loglog(radial_bins[1:], color=plot_color, alpha=alpha, label=label)

    def plot_orientation_spectrum(img, plot_color, label, alpha=0.7):
        """Plot orientation-specific power spectrum"""
        if img.shape[2] >= 3:
            # Convert to grayscale for spectrum analysis
            gray = skcolor.rgb2gray(img[:, :, :3])
        else:
            gray = img[:, :, 0]

        # Calculate 2D FFT
        f_transform = fftpack.fft2(gray)
        f_transform_shifted = np.fft.fftshift(f_transform)

        # Calculate power spectrum
        power_spectrum = np.abs(f_transform_shifted) ** 2

        # Get image dimensions and center
        h, w = gray.shape
        center_y, center_x = h // 2, w // 2

        # Create coordinate arrays
        y, x = np.ogrid[-center_y:h - center_y, -center_x:w - center_x]

        # Calculate angles (orientation) for each point
        angles = np.arctan2(y, x)

        # Convert to degrees and normalize to 0-180 range (since power spectrum is symmetric)
        angles_deg = np.degrees(angles) % 180

        # EXCLUDE THE CENTER REGION to avoid DC dominance
        center_radius = 5  # Exclude central region
        distance_from_center = np.sqrt(y ** 2 + x ** 2)
        non_center_mask = distance_from_center > center_radius

        # Apply mask to both power spectrum and angles
        power_spectrum_masked = power_spectrum[non_center_mask]
        angles_deg_masked = angles_deg[non_center_mask]

        # Create orientation bins
        orientation_bins = np.arange(0, 181, 5)  # 5-degree bins from 0 to 180
        orientation_power = np.zeros(len(orientation_bins) - 1)

        # Calculate power for each orientation bin
        for i in range(len(orientation_bins) - 1):
            angle_min = orientation_bins[i]
            angle_max = orientation_bins[i + 1]

            # Create mask for this orientation range
            mask = (angles_deg_masked >= angle_min) & (angles_deg_masked < angle_max)

            # Sum power in this orientation
            if np.any(mask):
                orientation_power[i] = np.mean(power_spectrum_masked[mask])

        # Plot orientation spectrum
        bin_centers = (orientation_bins[:-1] + orientation_bins[1:]) / 2
        plt.plot(bin_centers, orientation_power, color=plot_color, alpha=alpha, label=label, linewidth=2)

    def plot_2d_power_spectrum_diff(original_img, randomized_img):
        """Plot 2D power spectrum difference visualization"""

        def get_2d_power_spectrum(img):
            if img.shape[2] >= 3:
                gray = skcolor.rgb2gray(img[:, :, :3])
            else:
                gray = img[:, :, 0]

            f_transform = fftpack.fft2(gray)
            f_transform_shifted = np.fft.fftshift(f_transform)
            power_spectrum = np.abs(f_transform_shifted) ** 2

            # Log scale for better visualization
            return np.log10(power_spectrum + 1e-10)

        orig_power = get_2d_power_spectrum(original_img)
        rand_power = get_2d_power_spectrum(randomized_img)

        # Calculate difference
        power_diff = rand_power - orig_power

        # Display the difference
        im = plt.imshow(power_diff, cmap='RdBu_r', origin='lower')
        plt.colorbar(im, label='Log Power Difference')
        plt.xlabel('Frequency X')
        plt.ylabel('Frequency Y')

    # Analyze both images
    orig_mean, orig_std, orig_min, orig_max, orig_values = analyze_image_stats(original_image, "Original")
    rand_mean, rand_std, rand_min, rand_max, rand_values = analyze_image_stats(randomized_image, "Randomized")

    # Create the analysis plot
    fig = plt.figure(figsize=(20, 12))

    # Image comparison
    plt.subplot(2, 3, 1)
    plt.title(f'Original Image\nMean: {orig_mean:.2f}, StdDev: {orig_std:.2f}')
    plt.imshow(original_image)
    plt.axis('off')

    plt.subplot(2, 3, 2)
    plt.title(f'Magnitude Randomized (Phase Preserved)\nMean: {rand_mean:.2f}, StdDev: {rand_std:.2f}')
    plt.imshow(randomized_image)
    plt.axis('off')

    # Histogram comparison
    plt.subplot(2, 3, 3)
    plt.title('Luminance Histograms')
    plt.hist(orig_values, bins=50, alpha=0.5, label='Original', color='blue')
    plt.hist(rand_values, bins=50, alpha=0.5, label='Randomized', color='red')
    plt.legend()
    plt.grid(alpha=0.3)

    # Radial power spectrum comparison
    plt.subplot(2, 3, 4)
    plt.title('Radial Power Spectrum')
    plot_power_spectrum(original_image, 'blue', 'Original')
    plot_power_spectrum(randomized_image, 'red', 'Randomized')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.xlabel('Spatial Frequency')
    plt.ylabel('Power')

    # Orientation power spectrum comparison
    plt.subplot(2, 3, 5)
    plt.title('Orientation Power Spectrum')
    plot_orientation_spectrum(original_image, 'blue', 'Original')
    plot_orientation_spectrum(randomized_image, 'red', 'Randomized')
    plt.legend()
    plt.grid(alpha=0.3)
    plt.xlabel('Orientation (degrees)')
    plt.ylabel('Power')

    # 2D Power spectrum visualization
    plt.subplot(2, 3, 6)
    plt.title('2D Power Spectrum Difference')
    plot_2d_power_spectrum_diff(original_image, randomized_image)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()  # Close to free memory


def process_image(input_path, output_path, keep_intermediates=False):
    """
    Process image with magnitude randomization while preserving contrast.

    Args:
        input_path: Path to input image
        output_path: Path for final output image
        keep_intermediates: Whether to save analysis plot showing histograms and power spectrum

    Returns:
        tuple: (analysis_plot_path, final_path) if keep_intermediates,
               else (None, final_path)
    """
    try:
        # Validate input file exists
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Generate analysis plot path
        base_name = os.path.splitext(output_path)[0]
        analysis_plot_path = f"{base_name}_analysis.png"

        # Open and process the image
        img = Image.open(input_path).convert('RGBA')
        img_array = np.array(img)

        # Apply magnitude randomization
        processed_array = magnitude_randomize_preserve_contrast(img_array)

        # Create analysis plot if requested
        if keep_intermediates:
            create_analysis_plot(img_array, processed_array, analysis_plot_path)

        # Save final shuffled image
        final_img = Image.fromarray(processed_array.astype(np.uint8))
        final_img.save(output_path)

        return (
            analysis_plot_path if keep_intermediates else None,
            output_path
        )

    except Exception as e:
        # Print error to stderr so Java can capture it
        print(f"ERROR: {str(e)}", file=sys.stderr)
        raise


def main():
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(
        description='Process images with magnitude randomization while preserving phase and contrast',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('input_path', help='Path to input image')
    parser.add_argument('output_path', help='Path for output image')
    parser.add_argument('--keep-intermediates', '-k', action='store_true',
                        help='Save intermediate processing files')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress output messages')

    args = parser.parse_args()

    try:
        # Process the image
        analysis_path, final_path = process_image(
            args.input_path,
            args.output_path,
            args.keep_intermediates
        )

        if not args.quiet:
            print(f"SUCCESS: {final_path}")
            if args.keep_intermediates and analysis_path:
                print(f"ANALYSIS: {analysis_path}")

        return 0

    except Exception as e:
        if not args.quiet:
            print(f"FAILED: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
"""
Orientation-preserving processing script for Java integration.
Preserves spatial frequency and orientation distributions while destroying spatial location.

Usage: python orientation_preserving_processing.py <input_path> <output_path> [--keep-intermediates]
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

from src.imageshuffle.shuffle_util import plot_orientation_spectrum, plot_2d_power_spectrum_diff, create_analysis_plot

matplotlib.use('Agg')  # Use non-interactive backend for server environments


def orientation_preserving_scramble(image, mask=None, num_orientation_bands=18):
    """
    Scramble spatial location while preserving orientation and spatial frequency distributions.

    This works by:
    1. Grouping frequency components by their orientation angle
    2. Shuffling phases within each orientation band
    3. Preserving magnitudes completely

    Args:
        image: Input image (can be color with alpha channel)
        mask: Binary mask (1 inside region to randomize, 0 outside)
        num_orientation_bands: Number of orientation bands to preserve (default: 18 = 10° bands)

    Returns:
        Image with preserved orientation/frequency distributions but scrambled spatial locations
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
    # L_roi = L * mask

    # Use soft masking:
    from scipy import ndimage
    soft_mask = ndimage.gaussian_filter(mask.astype(float), sigma=5)
    L_roi = L * soft_mask  # No sharp boundary artifacts

    # Apply Fourier transform to the MASKED ROI
    fft_L_roi = fftpack.fft2(L_roi)

    # Extract amplitude and phase
    amplitude = np.abs(fft_L_roi)
    original_phase = np.angle(fft_L_roi)

    # Get image dimensions
    h, w = fft_L_roi.shape
    center_y, center_x = h // 2, w // 2

    # Create coordinate arrays for frequency domain
    y, x = np.ogrid[-center_y:h - center_y, -center_x:w - center_x]

    # Calculate orientation for each frequency component
    # This gives the orientation of the spatial pattern represented by each frequency
    orientations = np.arctan2(y, x) * 180 / np.pi
    orientations = orientations % 180  # Normalize to 0-180° (since power spectrum is symmetric)

    # Create orientation bands
    orientation_band_size = 180.0 / num_orientation_bands

    # Initialize new phase array with original phases
    new_phase = original_phase.copy()

    # Shuffle phases within each orientation band
    for band in range(num_orientation_bands):
        angle_min = band * orientation_band_size
        angle_max = (band + 1) * orientation_band_size

        # Create mask for this orientation band
        band_mask = (orientations >= angle_min) & (orientations < angle_max)

        # Skip DC component (always preserve it)
        band_mask[center_y, center_x] = False

        if np.any(band_mask):
            # Get phases in this orientation band
            phases_in_band = original_phase[band_mask].copy()

            # Shuffle the phases within this orientation band
            # Generate random phases instead of shuffling existing ones
            phases_in_band = np.random.uniform(0, 2 * np.pi, len(phases_in_band))

            # Put shuffled phases back into the same orientation band
            new_phase[band_mask] = phases_in_band

    # Ensure DC component phase is preserved (usually 0)
    new_phase[center_y, center_x] = original_phase[center_y, center_x]

    # Combine original amplitude with orientation-band-shuffled phase
    randomized_fft = amplitude * np.exp(1j * new_phase)

    # Apply inverse Fourier transform
    randomized_L_roi = np.real(fftpack.ifft2(randomized_fft))

    # Create a new luminance channel that ONLY replaces the masked region
    randomized_L = L.copy()  # Start with original luminance
    randomized_L[mask] = randomized_L_roi[mask]  # Only update masked pixels

    # Perform histogram matching to ensure the luminance distribution is preserved
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


def process_image(input_path, output_path, keep_intermediates=False):
    """
    Process image with orientation-preserving scrambling.

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

        # Apply orientation-preserving scrambling
        processed_array = orientation_preserving_scramble(img_array)

        # Create analysis plot if requested
        if keep_intermediates:
            create_analysis_plot(img_array, processed_array, analysis_plot_path, "Orientation-Preserving Scrambled")

        # Save final scrambled image
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
        description='Process images with orientation-preserving scrambling (preserves frequency and orientation distributions)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('input_path', help='Path to input image')
    parser.add_argument('output_path', help='Path for output image')
    parser.add_argument('--keep-intermediates', '-k', action='store_true',
                        help='Save analysis plot showing histograms and power spectrum')
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

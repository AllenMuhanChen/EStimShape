#!/usr/bin/env python3
"""
Phase randomization processing script for Java integration via direct process execution.
Randomizes phase information while preserving magnitude and contrast distribution.

Usage: python phase_processing.py <input_path> <output_path> [--keep-intermediates]
"""

import sys
import os
import argparse
import numpy as np
from PIL import Image
from scipy import fftpack
from skimage import color as skcolor, exposure
import matplotlib

from shuffle_util import create_analysis_plot, apply_clean_interior_processing

matplotlib.use('Agg')  # Use non-interactive backend for server environments


def phase_shuffle_function(fft_clean_interior):
    """
    Phase shuffling function applied to CLEAN INTERIOR FFT only.

    This operates on the result of: FFT(original) - FFT(boundary_with_average)
    So it shuffles only the interior content phases, not boundary artifacts.

    Args:
        fft_clean_interior: Clean interior FFT (boundary artifacts removed)

    Returns:
        fft_processed_interior: FFT with shuffled phase, preserved magnitude
    """
    # Extract magnitude from clean interior FFT (which we'll keep)
    interior_magnitude = np.abs(fft_clean_interior)

    # Extract phase from clean interior FFT (which we'll randomize)
    original_interior_phase = np.angle(fft_clean_interior)

    # Phase shuffling: generate completely random phases for interior content
    # This breaks spatial relationships while preserving magnitude spectrum

    # Create a mask for non-DC components
    phase_mask = np.ones_like(original_interior_phase, dtype=bool)
    phase_mask[0, 0] = False  # Exclude DC component

    # Generate random phases for all non-DC components of interior content
    random_phases = original_interior_phase[phase_mask].flatten()
    np.random.shuffle(random_phases)
    # random_phases = np.random.uniform(0, 2 * np.pi, np.sum(phase_mask))

    # Create new phase array with random values
    shuffled_interior_phase = np.zeros_like(original_interior_phase)
    shuffled_interior_phase[0, 0] = 0  # Keep DC phase as 0
    shuffled_interior_phase[phase_mask] = random_phases

    # Combine original interior magnitude with shuffled interior phase
    fft_processed_interior = interior_magnitude * np.exp(1j * shuffled_interior_phase)

    return fft_processed_interior


def phase_shuffle_function_with_capture(fft_clean_interior, capture_dict=None):
    """
    Phase shuffling function that can capture FFTs for analysis.

    Args:
        fft_clean_interior: Clean interior FFT (boundary artifacts removed)
        capture_dict: Dictionary to store original and processed FFTs (if provided)

    Returns:
        fft_processed_interior: FFT with shuffled phase, preserved magnitude
    """
    # Capture original FFT if requested
    if capture_dict is not None:
        capture_dict['original_fft'] = fft_clean_interior.copy()

    # Extract magnitude from clean interior FFT (which we'll keep)
    interior_magnitude = np.abs(fft_clean_interior)

    # Extract phase from clean interior FFT (which we'll randomize)
    original_interior_phase = np.angle(fft_clean_interior)

    # Phase shuffling: generate completely random phases for interior content
    # This breaks spatial relationships while preserving magnitude spectrum

    # Create a mask for non-DC components
    phase_mask = np.ones_like(original_interior_phase, dtype=bool)
    phase_mask[0, 0] = False  # Exclude DC component

    # Generate random phases for all non-DC components of interior content
    random_phases = original_interior_phase[phase_mask].flatten()
    np.random.shuffle(random_phases)
    # random_phases = np.random.uniform(0, 2 * np.pi, np.sum(phase_mask))

    # Create new phase array with random values
    shuffled_interior_phase = np.zeros_like(original_interior_phase)
    shuffled_interior_phase[0, 0] = 0  # Keep DC phase as 0
    shuffled_interior_phase[phase_mask] = random_phases

    # Combine original interior magnitude with shuffled interior phase
    fft_processed_interior = interior_magnitude * np.exp(1j * shuffled_interior_phase)

    # Capture processed FFT if requested
    if capture_dict is not None:
        capture_dict['processed_fft'] = fft_processed_interior.copy()

    return fft_processed_interior


def phase_randomize_preserve_contrast(image, mask=None, capture_ffts=False):
    """
    Phase randomize the image while preserving contrast, color distribution,
    and average luminance through histogram matching.

    Args:
        image: Input image (can be color with alpha channel)
        mask: Binary mask (1 inside region to randomize, 0 outside)
        capture_ffts: If True, returns (result, original_fft, processed_fft)

    Returns:
        If capture_ffts=False: Phase-randomized image with preserved statistical properties
        If capture_ffts=True: (result, original_fft, processed_fft)
    """
    # Create a copy of the original image
    result = image.copy().astype(np.float32)

    # Dictionary to capture FFTs if requested
    fft_capture = {} if capture_ffts else None

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

    # Create processing function that captures FFTs
    def processing_func_with_capture(fft_clean_interior):
        return phase_shuffle_function_with_capture(fft_clean_interior, fft_capture)

    # Apply clean interior processing with boundary subtraction
    # This ensures phase shuffling operates on interior content only
    if capture_ffts:
        randomized_L_roi = apply_clean_interior_processing(
            L, mask, processing_func_with_capture, erosion_iterations=2
        )
    else:
        randomized_L_roi = apply_clean_interior_processing(
            L, mask, phase_shuffle_function, erosion_iterations=2
        )

    # The result already includes boundary reconstruction, so we can use it directly

    # Create a new luminance channel that replaces the masked region
    randomized_L = L.copy()
    randomized_L[mask] = randomized_L_roi[mask]

    # Now perform histogram matching to ensure the luminance distribution is preserved
    # Extract the randomized values in the masked region
    randomized_values = randomized_L[mask]

    # Match the histogram of the randomized values to the original values
    # More robust histogram matching
    matched_values = exposure.match_histograms(
        randomized_values.reshape(-1, 1),
        L_masked_orig.reshape(-1, 1),
        channel_axis=None
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

    # Return with or without FFTs
    if capture_ffts:
        return result, fft_capture.get('original_fft'), fft_capture.get('processed_fft')
    else:
        return result


def process_image(input_path, output_path, keep_intermediates=False):
    """
    Process image with phase randomization while preserving contrast.

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

        # Apply phase randomization with FFT capture if needed for analysis
        if keep_intermediates:
            processed_array, original_fft, processed_fft = phase_randomize_preserve_contrast(
                img_array, capture_ffts=True
            )

            # Create analysis plot with corrected FFT analysis
            create_analysis_plot(
                img_array, processed_array, analysis_plot_path, "Phase Randomized",
                original_fft=original_fft, processed_fft=processed_fft
            )
        else:
            processed_array = phase_randomize_preserve_contrast(img_array)

        # Save final phase-randomized image
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
        description='Process images with phase randomization while preserving magnitude and contrast',
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
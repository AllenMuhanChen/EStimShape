#!/usr/bin/env python3
"""
Pixel shuffle processing script for Java integration via direct process execution.
Shuffles pixels randomly within the foreground region while preserving the background.

Usage: python pixel_shuffle.py <input_path> <output_path> [--keep-intermediates]
"""

import sys
import os
import argparse
import numpy as np
from PIL import Image
import matplotlib

from src.imageshuffle.shuffle_util import create_analysis_plot

matplotlib.use('Agg')  # Use non-interactive backend for server environments


def pixel_randomize_preserve_contrast(image, mask=None):
    """
    Shuffles pixels randomly within the foreground region while preserving the background.

    Args:
        image: Input image (can be color with alpha channel)
        mask: Binary mask (1 inside region to randomize, 0 outside)

    Returns:
        Pixel-shuffled image with background preserved
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

    # Get the coordinates of all foreground pixels
    foreground_coords = np.where(mask)
    num_foreground_pixels = len(foreground_coords[0])

    if num_foreground_pixels == 0:
        # No foreground pixels to shuffle
        return result.astype(image.dtype)

    # Extract all foreground pixel values (RGB)
    foreground_pixels = rgb[foreground_coords]  # Shape: (num_pixels, 3)

    # Shuffle the pixel values
    shuffled_indices = np.random.permutation(num_foreground_pixels)
    shuffled_pixels = foreground_pixels[shuffled_indices]

    # Create the result image by copying the original
    rgb_shuffled = rgb.copy()

    # Replace the foreground pixels with shuffled values
    rgb_shuffled[foreground_coords] = shuffled_pixels

    # Reattach alpha channel if needed
    if alpha is not None:
        result = np.concatenate([rgb_shuffled, alpha], axis=2)
    else:
        result = rgb_shuffled

    # Convert back to original data type
    if image.dtype == np.uint8:
        result = np.clip(result, 0, 255).astype(np.uint8)

    return result


def process_image(input_path, output_path, keep_intermediates=False):
    """
    Process image with pixel shuffling.

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

        # Apply pixel shuffling
        processed_array = pixel_randomize_preserve_contrast(img_array)

        # Create analysis plot if requested
        if keep_intermediates:
            create_analysis_plot(img_array, processed_array, analysis_plot_path, "Pixel Shuffled")

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
        description='Process images with pixel shuffling while preserving background',
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
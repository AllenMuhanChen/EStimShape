#!/usr/bin/env python3
"""
Pixel shuffle processing script for Java integration via direct process execution.
Shuffles pixels randomly within the interior region while preserving boundaries and background.

Usage: python pixel_shuffle.py <input_path> <output_path> [--keep-intermediates]
"""

import sys
import os
import argparse
import numpy as np
from PIL import Image
from scipy import ndimage
import matplotlib

from shuffle_util import create_analysis_plot

matplotlib.use('Agg')  # Use non-interactive backend for server environments


def pixel_randomize_preserve_contrast(image, mask=None, erosion_iterations=5, shuffle_boundary=False):
    """
    Shuffles pixels randomly within the shape region while preserving the background.

    By default the shape's boundary contour is preserved: erosion defines an interior region
    and only interior pixels are shuffled, so the outline stays intact (consistent with the
    frequency domain methods). When ``shuffle_boundary`` is True the whole shape - interior
    *and* boundary contour - is shuffled together, so the outline is not preserved.

    In every case the background (pixels outside the mask) is left untouched.

    Args:
        image: Input image (can be color with alpha channel)
        mask: Binary mask (1 inside region to randomize, 0 outside)
        erosion_iterations: Number of erosion iterations to define the interior (ignored when
            ``shuffle_boundary`` is True)
        shuffle_boundary: If True, shuffle the whole shape including its boundary contour
            instead of only the eroded interior

    Returns:
        Pixel-shuffled image with the background preserved (and, unless ``shuffle_boundary``,
        the boundary contour preserved too)
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

    if shuffle_boundary:
        # Whole-contour shuffle: shuffle every masked pixel, boundary contour included.
        region_mask = mask
    else:
        # Create interior mask (well away from boundaries) - same as frequency methods.
        region_mask = ndimage.binary_erosion(mask, iterations=erosion_iterations)

    # Get the coordinates of all pixels in the region to shuffle
    region_coords = np.where(region_mask)
    num_region_pixels = len(region_coords[0])

    if num_region_pixels == 0:
        # No pixels to shuffle
        print("Warning: No pixels found for shuffling", file=sys.stderr)
        return result.astype(image.dtype)

    # Extract all region pixel values (RGB)
    region_pixels = rgb[region_coords]  # Shape: (num_pixels, 3)

    # Shuffle the pixel values within the region only
    shuffled_indices = np.random.permutation(num_region_pixels)
    shuffled_pixels = region_pixels[shuffled_indices]

    # Create the result image by copying the original
    rgb_shuffled = rgb.copy()

    # Replace ONLY the region pixels with shuffled values. For the default (interior) mode the
    # boundary contour remains exactly as original; for whole-contour mode it is shuffled too.
    rgb_shuffled[region_coords] = shuffled_pixels

    # Reattach alpha channel if needed
    if alpha is not None:
        result = np.concatenate([rgb_shuffled, alpha], axis=2)
    else:
        result = rgb_shuffled

    # Convert back to original data type
    if image.dtype == np.uint8:
        result = np.clip(result, 0, 255).astype(np.uint8)

    return result


def process_image(input_path, output_path, keep_intermediates=False, shuffle_boundary=False):
    """
    Process image with pixel shuffling.

    Args:
        input_path: Path to input image
        output_path: Path for final output image
        keep_intermediates: Whether to save analysis plot showing histograms and power spectrum
        shuffle_boundary: If True, shuffle the whole shape including its boundary contour
            instead of only the interior (see pixel_randomize_preserve_contrast)

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

        # Apply pixel shuffling (interior-only by default, whole-contour when requested)
        processed_array = pixel_randomize_preserve_contrast(
            img_array, erosion_iterations=1, shuffle_boundary=shuffle_boundary)

        # Create analysis plot if requested
        if keep_intermediates:
            plot_title = "Whole-Contour Pixel Shuffled" if shuffle_boundary else "Interior Pixel Shuffled"
            create_analysis_plot(img_array, processed_array, analysis_plot_path, plot_title)

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
        description='Process images with pixel shuffling while preserving the background '
                    '(and, by default, the shape boundary contour)',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('input_path', help='Path to input image')
    parser.add_argument('output_path', help='Path for output image')
    parser.add_argument('--keep-intermediates', '-k', action='store_true',
                        help='Save analysis plot showing histograms and power spectrum')
    parser.add_argument('--whole-contour', '-w', action='store_true',
                        help='Shuffle the whole shape including its boundary contour, '
                             'instead of preserving the outline and shuffling only the interior')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress output messages')

    args = parser.parse_args()

    try:
        # Process the image
        analysis_path, final_path = process_image(
            args.input_path,
            args.output_path,
            args.keep_intermediates,
            args.whole_contour
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
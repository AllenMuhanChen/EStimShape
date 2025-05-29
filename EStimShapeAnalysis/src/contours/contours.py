#!/usr/bin/env python3
"""
Image processing script for Java integration via direct process execution.
Converts images to grayscale and applies CIELAB-based colormapping.

Usage: python process_image.py <input_path> <output_path> [--keep-intermediates]
"""

import sys
import os
import argparse
import numpy as np
from PIL import Image
from skimage import color


def normalize_lightness(lightness):
    """Normalize lightness values to 0-1 range."""
    lightness_zeros_removed = lightness[lightness > 0]
    if len(lightness_zeros_removed) == 0:
        return lightness

    l_min, l_max = np.percentile(lightness_zeros_removed, [0, 100])
    if l_max == l_min:
        return np.zeros_like(lightness)

    lightness_normalized = np.clip((lightness - l_min) / (l_max - l_min), 0, 1)
    return lightness_normalized


def create_lab_colormap(hue_values):
    """Create CIELAB-based colormap from hue values."""
    L = np.full_like(hue_values, 75)  # Constant lightness
    a = np.cos(2 * np.pi * hue_values) * 100
    b = np.sin(2 * np.pi * hue_values) * 100
    lab = np.dstack((L, a, b))
    return color.lab2rgb(lab)


def process_image(input_path, output_path, keep_intermediates=False):
    """
    Process image with CIELAB-based colormapping.

    Args:
        input_path: Path to input image
        output_path: Path for final output image
        keep_intermediates: Whether to save intermediate grayscale and colormap images

    Returns:
        tuple: (grayscale_path, colormap_path, final_path) if keep_intermediates,
               else (None, None, final_path)
    """
    try:
        # Validate input file exists
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Create output directory if it doesn't exist
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        # Generate intermediate file paths
        base_name = os.path.splitext(output_path)[0]
        grayscale_output_path = f"{base_name}_grayscale.png"
        colormap_output_path = f"{base_name}_colormap.png"

        # Open and process the image
        img = Image.open(input_path).convert('RGBA')
        img_array = np.array(img)

        # Separate RGB and alpha
        rgb = img_array[:, :, :3].astype(float) / 255.0
        alpha = img_array[:, :, 3]

        # Convert RGB to grayscale using CIELAB luminance
        lab = color.rgb2lab(rgb)
        grayscale = lab[:, :, 0] / 100.0  # L channel normalized to 0-1

        # Save grayscale image if requested
        if keep_intermediates:
            grayscale_image = Image.fromarray((grayscale * 255).astype(np.uint8))
            grayscale_image.save(grayscale_output_path)

        # Normalize grayscale to create hue map
        hue_map = normalize_lightness(grayscale)

        # Create CIELAB-based colormap
        colormap = create_lab_colormap(hue_map)

        # Save colormap if requested
        if keep_intermediates:
            colormap_with_alpha = np.dstack((colormap, np.ones_like(grayscale)))
            Image.fromarray((colormap_with_alpha * 255).astype(np.uint8)).save(colormap_output_path)

        # Multiply grayscale image with CIELAB-based colormap
        colored_image = np.expand_dims(grayscale, axis=2) * colormap

        # Combine with original alpha channel
        final_image = np.dstack((colored_image, alpha / 255.0))

        # Save final image
        Image.fromarray((final_image * 255).astype(np.uint8)).save(output_path)

        return (
            grayscale_output_path if keep_intermediates else None,
            colormap_output_path if keep_intermediates else None,
            output_path
        )

    except Exception as e:
        # Print error to stderr so Java can capture it
        print(f"ERROR: {str(e)}", file=sys.stderr)
        raise


def main():
    """Main function for command-line execution."""
    parser = argparse.ArgumentParser(
        description='Process images with CIELAB-based colormapping',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('input_path', help='Path to input image')
    parser.add_argument('output_path', help='Path for output image')
    parser.add_argument('--keep-intermediates', '-k', action='store_true',
                        help='Save intermediate grayscale and colormap images')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress output messages')

    args = parser.parse_args()

    try:
        # Process the image
        grayscale_path, colormap_path, final_path = process_image(
            args.input_path,
            args.output_path,
            args.keep_intermediates
        )

        if not args.quiet:
            print(f"SUCCESS: {final_path}")
            if args.keep_intermediates:
                print(f"GRAYSCALE: {grayscale_path}")
                print(f"COLORMAP: {colormap_path}")

        return 0

    except Exception as e:
        if not args.quiet:
            print(f"FAILED: {str(e)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
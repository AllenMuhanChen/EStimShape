#!/usr/bin/env python3
"""
Image converter that creates isochromatic and isoluminant versions of an input image.

Requirements:
pip install pillow numpy scikit-image

Usage:
python image_converter.py path/to/your/image.jpg
"""

import sys
import numpy as np
from PIL import Image
from skimage import color
import os


def create_isochromatic(image_array):
    """
    Create isochromatic version: grayscale multiplied by red for red-black scale.

    Args:
        image_array: RGB image as numpy array (H, W, 3)

    Returns:
        Red-black scale image as numpy array
    """
    # Convert to grayscale using standard luminance weights
    grayscale = np.dot(image_array[..., :3], [0.299, 0.587, 0.114])

    # Create red-black scale by setting red channel to grayscale, others to 0
    red_black = np.zeros_like(image_array)
    red_black[..., 0] = grayscale  # Red channel
    red_black[..., 1] = 0  # Green channel
    red_black[..., 2] = 0  # Blue channel

    return red_black.astype(np.uint8)


def create_isoluminant(image_array):
    """
    Create isoluminant version: same average luminance for all pixels in CIELAB space.

    Args:
        image_array: RGB image as numpy array (H, W, 3)

    Returns:
        Isoluminant image as numpy array
    """
    # Normalize to 0-1 range for color space conversion
    image_normalized = image_array.astype(np.float64) / 255.0

    # Convert RGB to CIELAB
    lab_image = color.rgb2lab(image_normalized)

    # Calculate average luminance (L* channel)
    avg_luminance = np.mean(lab_image[..., 0])

    # Set all pixels to the same luminance while keeping a* and b* (color information)
    isoluminant_lab = lab_image.copy()
    isoluminant_lab[..., 0] = avg_luminance

    # Convert back to RGB
    isoluminant_rgb = color.lab2rgb(isoluminant_lab)

    # Convert back to 0-255 range and ensure valid range
    isoluminant_rgb = np.clip(isoluminant_rgb * 255, 0, 255)

    return isoluminant_rgb.astype(np.uint8)


def process_image(image_path):
    """
    Process an image to create isochromatic and isoluminant versions.

    Args:
        image_path: Path to the input image
    """
    try:
        # Load image
        image = Image.open(image_path)

        # Convert to RGB if necessary (handles RGBA, grayscale, etc.)
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Convert to numpy array
        image_array = np.array(image)

        print(f"Processing image: {image_path}")
        print(f"Image dimensions: {image_array.shape}")

        # Create isochromatic version
        print("Creating isochromatic (red-black) version...")
        isochromatic = create_isochromatic(image_array)

        # Create isoluminant version
        print("Creating isoluminant version...")
        isoluminant = create_isoluminant(image_array)

        # Generate output filenames
        base_name = os.path.splitext(image_path)[0]
        ext = os.path.splitext(image_path)[1]

        isochromatic_path = f"{base_name}_isochromatic{ext}"
        isoluminant_path = f"{base_name}_isoluminant{ext}"

        # Save images
        Image.fromarray(isochromatic).save(isochromatic_path)
        Image.fromarray(isoluminant).save(isoluminant_path)

        print(f"Saved isochromatic version: {isochromatic_path}")
        print(f"Saved isoluminant version: {isoluminant_path}")

        # Print some statistics
        original_lab = color.rgb2lab(image_array.astype(np.float64) / 255.0)
        print(f"\nOriginal image luminance range: {original_lab[..., 0].min():.2f} - {original_lab[..., 0].max():.2f}")
        print(f"Average luminance used for isoluminant: {np.mean(original_lab[..., 0]):.2f}")

    except Exception as e:
        print(f"Error processing image: {e}")


def main():
    image_path = "/home/r2_allen/git/EStimShape/EStimShapeAnalysis/src/contours/image_examples/0a5ae820-7051-4495-bcca-61bf02897472.jpg"

    process_image(image_path)


if __name__ == "__main__":
    main()
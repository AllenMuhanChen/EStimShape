#!/usr/bin/env python3
"""
Phase Congruency Analysis with Orientation Visualization

This script applies phase congruency analysis and returns results as XxYxN array
where N is the number of orientations, then visualizes using hue for orientation
and alpha for strength.

Usage: python clean_interior_phasecong.py
"""

import sys
import os
import numpy as np
from PIL import Image
from skimage import color as skcolor
import matplotlib.pyplot as plt
import matplotlib
from matplotlib.colors import hsv_to_rgb

# Import existing phase congruency function
from phasepack.phasecong import phasecong

matplotlib.use('Agg')  # Use non-interactive backend for server environments


def phasecong_orientation_stack(img, nscale=5, norient=10, minWaveLength=3, mult=2.1,
                                sigmaOnf=0.55, k=2., cutOff=0.5, g=10., noiseMethod=-1):
    """
    Phase congruency analysis returning XxYxN orientation stack.

    Args:
        img: Input image
        nscale: Number of wavelet scales
        norient: Number of filter orientations
        minWaveLength: Wavelength of smallest scale filter
        mult: Scaling factor between successive filters
        sigmaOnf: Ratio of standard deviation to center frequency
        k: Noise threshold parameter
        cutOff: Frequency spread cutoff
        g: Sigmoid sharpness parameter
        noiseMethod: Noise estimation method

    Returns:
        orientation_stack: XxYxN array where N is number of orientations
        angles: Array of orientation angles corresponding to each slice
        total_strength: XxY array of total phase congruency strength
        results: Full phasecong results dictionary
    """

    # Use existing phasecong function
    M, m, ori, ft, PC, EO, T = phasecong(
        img, nscale=nscale, norient=norient, minWaveLength=minWaveLength,
        mult=mult, sigmaOnf=sigmaOnf, k=k, cutOff=cutOff, g=g, noiseMethod=noiseMethod
    )

    # PC is a list of phase congruency images, one per orientation
    # Stack them into XxYxN array
    rows, cols = img.shape if img.ndim == 2 else img.shape[:2]
    orientation_stack = np.zeros((rows, cols, norient))

    for i, pc in enumerate(PC):
        orientation_stack[:, :, i] = pc

    # Calculate orientation angles
    angles = np.array([i * (np.pi / norient) for i in range(norient)])

    # Calculate total strength
    total_strength = np.sum(orientation_stack, axis=2)

    # Package results
    results = {
        'M': M,  # Maximum moment (edge strength)
        'm': m,  # Minimum moment (corner strength)
        'ori': ori,  # Orientation
        'ft': ft,  # Feature type
        'PC': PC,  # Phase congruency per orientation
        'EO': EO,  # Complex filter responses
        'T': T,  # Noise threshold
    }

    return orientation_stack, angles, total_strength, results


def create_orientation_visualization(orientation_stack, angles, total_strength, output_path, original_image=None):
    """
    Create visualization using hue for orientation and alpha for strength.

    Args:
        orientation_stack: XxYxN array of phase congruency per orientation
        angles: Array of orientation angles
        total_strength: XxY array of total phase congruency strength
        output_path: Path to save visualization
        original_image: Original color image for display
    """

    rows, cols, norient = orientation_stack.shape

    # Create HSV image where:
    # - Hue represents dominant orientation
    # - Saturation is fixed at 1
    # - Value/Alpha represents strength

    # Find dominant orientation at each pixel
    dominant_orientation_idx = np.argmax(orientation_stack, axis=2)
    dominant_strength = np.max(orientation_stack, axis=2)

    # Map orientation indices to hue values (0 to 1)
    hue = dominant_orientation_idx.astype(float) / norient

    # Create HSV image
    hsv_image = np.zeros((rows, cols, 3))
    hsv_image[:, :, 0] = hue  # Hue from orientation
    hsv_image[:, :, 1] = 1.0  # Full saturation
    hsv_image[:, :, 2] = 1.0  # Full value

    # Convert to RGB
    rgb_image = hsv_to_rgb(hsv_image)

    # Use strength as alpha
    alpha = dominant_strength / (np.max(dominant_strength) + 1e-10)  # Normalize to 0-1

    # Create RGBA image
    rgba_image = np.zeros((rows, cols, 4))
    rgba_image[:, :, :3] = rgb_image
    rgba_image[:, :, 3] = alpha

    # Create the plot
    fig = plt.figure(figsize=(16, 12))

    # Original image
    plt.subplot(2, 3, 1)
    if original_image is not None:
        plt.imshow(original_image)
        plt.title('Original Image')
    else:
        plt.imshow(np.zeros((rows, cols)), cmap='gray')
        plt.title('No Original Image')
    plt.axis('off')

    # Total strength
    plt.subplot(2, 3, 2)
    plt.imshow(total_strength, cmap='hot')
    plt.colorbar(label='Total Phase Congruency')
    plt.title('Total Phase Congruency Strength')
    plt.axis('off')

    # Dominant orientation (as hue)
    plt.subplot(2, 3, 3)
    plt.imshow(hue, cmap='hsv', vmin=0, vmax=1)
    plt.colorbar(label='Orientation (normalized)')
    plt.title('Dominant Orientation')
    plt.axis('off')

    # Strength as alpha
    plt.subplot(2, 3, 4)
    plt.imshow(alpha, cmap='gray', vmin=0, vmax=1)
    plt.colorbar(label='Normalized Strength')
    plt.title('Phase Congruency Strength')
    plt.axis('off')

    # Combined orientation visualization
    plt.subplot(2, 3, 5)
    plt.imshow(rgba_image)
    plt.title('Orientation Visualization\n(Hue = Orientation, Alpha = Strength)')
    plt.axis('off')

    # Create orientation colorbar/legend
    plt.subplot(2, 3, 6)
    plt.axis('off')

    # Create circular colorbar showing orientation mapping
    theta = np.linspace(0, 2 * np.pi, 100)
    radius = np.linspace(0, 1, 50)
    Theta, Radius = np.meshgrid(theta, radius)

    # Convert to HSV for colorbar
    colorbar_hsv = np.zeros((50, 100, 3))
    colorbar_hsv[:, :, 0] = Theta / (2 * np.pi)  # Hue from angle
    colorbar_hsv[:, :, 1] = 1.0  # Full saturation
    colorbar_hsv[:, :, 2] = Radius  # Value from radius

    colorbar_rgb = hsv_to_rgb(colorbar_hsv)

    # Plot in polar coordinates
    ax = plt.subplot(2, 3, 6, projection='polar')
    ax.pcolormesh(Theta, Radius, Radius, shading='auto')
    ax.set_ylim(0, 1)
    ax.set_title('Orientation Legend\n(Angle = Hue, Radius = Strength)', pad=20)

    # Add angle labels
    angle_labels = [f'{angle * 180 / np.pi:.0f}°' for angle in angles]
    for i, (angle, label) in enumerate(zip(angles, angle_labels)):
        ax.text(angle, 1.1, label, ha='center', va='center')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    return rgba_image


def main():
    # Test with hardcoded path
    img_path = "/home/r2_allen/Documents/EStimShape/allen_shuffle_exp_250620_0/stimuli/pngs/1750444527676502_base.png"
    output_path = "phase_congruency_orientation_analysis.png"

    # Open image as np.array
    from matplotlib.image import imread
    img = imread(img_path)

    print(f"Processing image: {img_path}")
    print(f"Image shape: {img.shape}")

    # Apply phase congruency analysis to get orientation stack
    orientation_stack, angles, total_strength, results = phasecong_orientation_stack(
        img, norient=8, nscale=4
    )

    print(f"Analysis complete!")
    print(f"Orientation stack shape: {orientation_stack.shape}")
    print(f"Number of orientations: {len(angles)}")
    print(f"Orientation angles (degrees): {[f'{a * 180 / np.pi:.1f}' for a in angles]}")
    print(f"Max total strength: {np.max(total_strength):.4f}")
    print(f"Noise threshold: {results['T']:.6f}")

    # Create orientation visualization
    rgba_vis = create_orientation_visualization(
        orientation_stack, angles, total_strength, output_path, img
    )
    print(f"Visualization saved: {output_path}")


if __name__ == "__main__":
    sys.exit(main())
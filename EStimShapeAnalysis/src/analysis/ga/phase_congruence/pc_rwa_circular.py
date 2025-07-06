#!/usr/bin/env python3
"""
Circular Lineage Response-Weighted Average Analysis

Computes RWA for all stimuli in each lineage separately using polar coordinates (R,O,N)
instead of Cartesian coordinates (X,Y,N), where:
- R: radial distance from object center of mass
- O: orientation angle from object center of mass
- N: phase congruency orientation bins

This enables analysis of radial and rotational patterns in phase congruency data.
"""

import pandas as pd
import numpy as np
import os
import gc
from matplotlib.image import imread
import matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb
from scipy.ndimage import gaussian_filter

from src.analysis import Analysis
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.repository.import_from_repository import import_from_repository
from phasepack.phasecong import phasecong
from src.startup.context import pc_maps_path


def calculate_pc_map(img, nscale=5, norient=6, minWaveLength=3, mult=2.1,
                     sigmaOnf=0.55, k=2., cutOff=0.5, g=10., noiseMethod=-1):
    """
    Phase congruency analysis returning XxYxN orientation stack.

    Returns:
        orientation_stack: XxYxN array where N is number of orientations
        angles: Array of orientation angles corresponding to each slice
    """
    # Use existing phasecong function
    M, m, ori, ft, PC, EO, T = phasecong(
        img, nscale=nscale, norient=norient, minWaveLength=minWaveLength,
        mult=mult, sigmaOnf=sigmaOnf, k=k, cutOff=cutOff, g=g, noiseMethod=noiseMethod
    )

    # PC is a list of phase congruency images, one per orientation
    # Stack them into XxYxN array
    rows, cols = img.shape if img.ndim == 2 else img.shape[:2]
    orientation_stack = np.zeros((rows, cols, norient), dtype=np.float32)

    for i, pc in enumerate(PC):
        orientation_stack[:, :, i] = pc.astype(np.float32)

    # Calculate orientation angles
    angles = np.array([i * (np.pi / norient) for i in range(norient)])

    # Clear memory
    del M, m, ori, ft, PC, EO, T
    gc.collect()

    return orientation_stack, angles


def find_object_center(img):
    """
    Find the center of mass of the object by averaging positions of foreground pixels.
    """
    # Convert to grayscale if needed
    if img.ndim == 3:
        if img.shape[2] == 4:  # RGBA
            rgb_for_background = img[:, :, :3]
        else:  # RGB
            rgb_for_background = img

        # Find background pixel (most common pixel value)
        pixels = rgb_for_background.reshape(-1, rgb_for_background.shape[-1])
        unique_pixels, counts = np.unique(pixels, axis=0, return_counts=True)
        background_pixel = unique_pixels[np.argmax(counts)]

        # Create mask for foreground pixels (not background)
        if img.shape[2] == 4:
            mask = np.logical_not(np.all(img[:, :, :3] == background_pixel, axis=-1))
        else:
            mask = np.logical_not(np.all(img == background_pixel, axis=-1))
    else:
        # Grayscale image - assume background is most common value
        unique_values, counts = np.unique(img, return_counts=True)
        background_value = unique_values[np.argmax(counts)]
        mask = img != background_value

    # Find foreground pixel coordinates
    foreground_coords = np.where(mask)

    if len(foreground_coords[0]) == 0:
        # No foreground pixels found, use image center
        center_y, center_x = img.shape[0] // 2, img.shape[1] // 2
    else:
        # Calculate center of mass
        center_y = np.mean(foreground_coords[0])
        center_x = np.mean(foreground_coords[1])

    return (center_x, center_y)


def convert_to_polar_coordinates(orientation_stack, object_center, n_radial_bins=20, n_angular_bins=36):
    """
    Convert XxYxN orientation stack to RxOxN polar coordinate representation.

    Args:
        orientation_stack: XxYxN array of phase congruency data
        object_center: (center_x, center_y) tuple
        n_radial_bins: Number of radial distance bins
        n_angular_bins: Number of angular bins around the center

    Returns:
        polar_stack: RxOxN array in polar coordinates
        radial_bins: Array of radial bin edges
        angular_bins: Array of angular bin edges (in radians)
    """
    rows, cols, norient = orientation_stack.shape
    center_x, center_y = object_center

    # Create coordinate arrays
    y_coords, x_coords = np.mgrid[0:rows, 0:cols]

    # Calculate polar coordinates relative to object center
    dx = x_coords - center_x
    dy = y_coords - center_y

    # Radial distance from center
    radial_distance = np.sqrt(dx ** 2 + dy ** 2)

    # Angular position from center (0 to 2*pi)
    angular_position = np.arctan2(dy, dx) + np.pi  # Shift to 0-2π range

    # Determine maximum radius for binning
    max_radius = np.sqrt((rows / 2) ** 2 + (cols / 2) ** 2)  # Diagonal half-distance

    # Create bins
    radial_bins = np.linspace(0, max_radius, n_radial_bins + 1)
    angular_bins = np.linspace(0, 2 * np.pi, n_angular_bins + 1)

    # Initialize polar coordinate array
    polar_stack = np.zeros((n_radial_bins, n_angular_bins, norient), dtype=np.float32)
    count_array = np.zeros((n_radial_bins, n_angular_bins), dtype=np.int32)

    # Convert each pixel to polar coordinates and accumulate
    for y in range(rows):
        for x in range(cols):
            r = radial_distance[y, x]
            theta = angular_position[y, x]

            # Find which radial bin this pixel belongs to
            r_bin = np.digitize(r, radial_bins) - 1
            r_bin = np.clip(r_bin, 0, n_radial_bins - 1)

            # Find which angular bin this pixel belongs to
            theta_bin = np.digitize(theta, angular_bins) - 1
            theta_bin = np.clip(theta_bin, 0, n_angular_bins - 1)

            # Accumulate phase congruency values
            polar_stack[r_bin, theta_bin, :] += orientation_stack[y, x, :]
            count_array[r_bin, theta_bin] += 1

    # Average the accumulated values (avoid division by zero)
    for r_bin in range(n_radial_bins):
        for theta_bin in range(n_angular_bins):
            if count_array[r_bin, theta_bin] > 0:
                polar_stack[r_bin, theta_bin, :] /= count_array[r_bin, theta_bin]

    return polar_stack, radial_bins, angular_bins


def create_smoothed_polar_map(polar_stack, sigma_r=1.0, sigma_theta=1.0):
    """
    Create gaussian-smoothed version of polar stack.

    Args:
        polar_stack: RxOxN array
        sigma_r: Standard deviation for radial smoothing
        sigma_theta: Standard deviation for angular smoothing
    """
    n_radial, n_angular, norient = polar_stack.shape
    smoothed_map = np.zeros_like(polar_stack)

    # Apply gaussian filter to each orientation layer
    # Note: we need to handle the circular nature of the angular dimension
    for i in range(norient):
        # For each radial bin, pad the angular dimension to handle wraparound
        layer = polar_stack[:, :, i]

        # Pad angular dimension to handle circular boundary
        padded_layer = np.concatenate([layer, layer, layer], axis=1)

        # Apply 2D gaussian filter
        smoothed_padded = gaussian_filter(padded_layer, sigma=[sigma_r, sigma_theta])

        # Extract the middle section (original size)
        smoothed_map[:, :, i] = smoothed_padded[:, n_angular:2 * n_angular]

    return smoothed_map


def process_single_stimulus_circular(stim_row, nscale=4, norient=8, sigma_r=1.0, sigma_theta=1.0,
                                     n_radial_bins=20, n_angular_bins=36, target_shape=None,
                                     pc_maps_dir=None, **phasecong_kwargs):
    """
    Process a single stimulus and return its contribution to the weighted average in polar coordinates.
    """
    stim_id = stim_row['StimSpecId']
    stim_path = stim_row['StimPath']
    ga_response = stim_row['GA Response']

    # Check for valid response
    if not np.isfinite(ga_response) or ga_response <= 0:
        print(f"    Warning: Invalid GA Response for {stim_id}: {ga_response}")
        return None, 0.0

    try:
        # Load image
        if not os.path.exists(stim_path):
            print(f"    Warning: Image file not found: {stim_path}")
            return None, 0.0

        img = imread(stim_path)

        # Generate phase congruency map
        orientation_stack, angles = calculate_pc_map(
            img,
            nscale=nscale,
            norient=norient,
            **phasecong_kwargs
        )

        # Find object center
        object_center = find_object_center(img)

        # Clear image from memory
        del img
        gc.collect()

        # Convert to polar coordinates
        polar_stack, radial_bins, angular_bins = convert_to_polar_coordinates(
            orientation_stack, object_center, n_radial_bins, n_angular_bins
        )

        # Set target shape from first image if not provided
        if target_shape is None:
            target_shape = polar_stack.shape

        # Check if polar stack size matches target
        if polar_stack.shape != target_shape:
            print(f"    Warning: Polar stack shape mismatch for {stim_id}: {polar_stack.shape} vs {target_shape}")
            return None, 0.0

        # Clear original orientation stack
        del orientation_stack
        gc.collect()

        # Create gaussian-smoothed polar map
        smoothed_polar_map = create_smoothed_polar_map(polar_stack, sigma_r, sigma_theta)

        # Clear unsmoothed polar stack
        del polar_stack
        gc.collect()

        # Save the processed PC map if directory is specified
        if pc_maps_dir:
            pc_map_file = os.path.join(pc_maps_dir, f"pc_polar_map_{stim_id}.npy")
            np.save(pc_map_file, smoothed_polar_map)

        # Weight by GA response
        weighted_contribution = smoothed_polar_map * ga_response

        # Clear smoothed map
        del smoothed_polar_map
        gc.collect()

        return weighted_contribution, ga_response

    except Exception as e:
        print(f"    Error processing stimulus {stim_id}: {str(e)}")
        return None, 0.0


class CircularLineageRWAAnalysis(PlotTopNAnalysis):
    """
    Memory-efficient analysis that computes RWA for each lineage using polar coordinates.
    """

    def __init__(self, nscale=4, norient=8, sigma_r=1.0, sigma_theta=1.0,
                 n_radial_bins=20, n_angular_bins=36, pc_maps_dir=None, **phasecong_kwargs):
        super().__init__()  # This will properly initialize response_table and other attributes
        self.nscale = nscale
        self.norient = norient
        self.sigma_r = sigma_r
        self.sigma_theta = sigma_theta
        self.n_radial_bins = n_radial_bins
        self.n_angular_bins = n_angular_bins
        self.pc_maps_dir = pc_maps_dir
        self.phasecong_kwargs = phasecong_kwargs

        # Create PC maps directory if specified
        if self.pc_maps_dir and not os.path.exists(self.pc_maps_dir):
            os.makedirs(self.pc_maps_dir)
            print(f"Created PC maps directory: {self.pc_maps_dir}")

    def analyze(self, channel, compiled_data=None):
        """
        Analyze all stimuli grouped by lineage and compute combined RWA in polar coordinates.
        """
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        print(f"Analyzing all stimuli for channel {channel} using polar coordinates")
        print(f"Polar coordinate settings:")
        print(f"  Radial bins: {self.n_radial_bins}")
        print(f"  Angular bins: {self.n_angular_bins}")
        print(f"  Radial smoothing sigma: {self.sigma_r}")
        print(f"  Angular smoothing sigma: {self.sigma_theta}")
        print(f"Total records in dataset: {len(compiled_data)}")

        # Group by StimSpecId and average the responses
        print("Grouping by StimSpecId and averaging responses...")

        # Define aggregation functions
        agg_functions = {
            'GA Response': 'mean',
            'StimPath': 'first',
            'Lineage': 'first',
            'StimType': 'first'
        }

        # Add other columns if they exist
        for col in ['Cluster Response', 'RegimeScore', 'Termination', 'Shaft', 'Junction', 'ThumbnailPath']:
            if col in compiled_data.columns:
                agg_functions[col] = 'first' if col not in ['Cluster Response', 'RegimeScore'] else 'mean'

        compiled_data = compiled_data.groupby('StimSpecId').agg(agg_functions).reset_index()

        # Filter out stimuli with NaN GA Response values
        original_count = len(compiled_data)
        compiled_data = compiled_data.dropna(subset=['GA Response'])
        compiled_data = compiled_data[compiled_data['GA Response'] != 0]
        filtered_count = len(compiled_data)

        if original_count != filtered_count:
            print(f"Filtered out {original_count - filtered_count} stimuli with NaN GA Response values")
            print(f"Remaining: {filtered_count} stimuli with valid responses")

        # Find top 3 lineages by stimulus count (after NaN filtering)
        lineage_counts = compiled_data.groupby('Lineage').size().sort_values(ascending=False)
        top_3_lineages = lineage_counts.head(3).index.tolist()

        print(f"Lineage stimulus counts:")
        for lineage, count in lineage_counts.items():
            marker = " ✓" if lineage in top_3_lineages else ""
            print(f"  Lineage {lineage}: {count} stimuli{marker}")

        print(f"\nProcessing top 3 lineages: {top_3_lineages}")

        # Filter to only top 3 lineages
        compiled_data = compiled_data[compiled_data['Lineage'].isin(top_3_lineages)]
        print(f"Filtered dataset: {len(compiled_data)} stimuli from top 3 lineages")

        # Group by lineage
        lineage_groups = compiled_data.groupby('Lineage')
        print(f"Processing {len(lineage_groups)} lineages (top 3 by stimulus count)")

        lineage_rwas = {}
        target_shape = None

        # Process each lineage
        for lineage_name, lineage_data in lineage_groups:
            print(f"\nProcessing Lineage {lineage_name}: {len(lineage_data)} stimuli")

            weighted_sum = None
            total_weight = 0.0
            processed_count = 0

            # Process each stimulus in this lineage
            for idx, stim_row in lineage_data.iterrows():
                stim_id = stim_row['StimSpecId']
                ga_response = stim_row['GA Response']

                print(
                    f"  Processing stimulus {processed_count + 1}/{len(lineage_data)}: {stim_id} (response: {ga_response:.4f})")

                # Process single stimulus in polar coordinates
                weighted_contribution, weight = process_single_stimulus_circular(
                    stim_row,
                    nscale=self.nscale,
                    norient=self.norient,
                    sigma_r=self.sigma_r,
                    sigma_theta=self.sigma_theta,
                    n_radial_bins=self.n_radial_bins,
                    n_angular_bins=self.n_angular_bins,
                    target_shape=target_shape,
                    pc_maps_dir=self.pc_maps_dir,
                    **self.phasecong_kwargs
                )

                if weighted_contribution is not None:
                    # Set target shape from first successful image
                    if target_shape is None:
                        target_shape = weighted_contribution.shape
                        print(
                            f"  Set target polar shape: {target_shape} (R={self.n_radial_bins}, O={self.n_angular_bins}, N={self.norient})")

                    # Accumulate weighted sum
                    if weighted_sum is None:
                        weighted_sum = weighted_contribution.copy()
                    else:
                        weighted_sum += weighted_contribution

                    total_weight += weight
                    processed_count += 1

                # Clear contribution from memory
                del weighted_contribution
                gc.collect()

            # Compute lineage RWA
            if weighted_sum is not None and total_weight > 0:
                lineage_rwa = weighted_sum / total_weight

                # Check for any NaN or infinite values in the result
                if np.any(~np.isfinite(lineage_rwa)):
                    print(f"  Warning: Invalid values detected in lineage {lineage_name} RWA")
                    continue

                lineage_rwas[lineage_name] = lineage_rwa

                print(f"  Lineage {lineage_name} RWA computed:")
                print(f"    Processed: {processed_count}/{len(lineage_data)} stimuli")
                print(f"    Total weight: {total_weight:.4f}")
                print(f"    Max strength: {np.max(np.sum(lineage_rwa, axis=2)):.4f}")

                # Clear weighted sum
                del weighted_sum
                gc.collect()
            else:
                print(f"  Warning: No valid stimuli processed for lineage {lineage_name}")
                print(f"    Processed: {processed_count}/{len(lineage_data)} stimuli")
                print(f"    Total weight: {total_weight:.4f}")

        if len(lineage_rwas) == 0:
            print("Error: No valid lineage RWAs computed!")
            return {
                'combined_rwa': None,
                'lineage_rwas': {},
                'channel': channel,
                'target_shape': target_shape,
                'analysis_params': {
                    'nscale': self.nscale,
                    'norient': self.norient,
                    'sigma_r': self.sigma_r,
                    'sigma_theta': self.sigma_theta,
                    'n_radial_bins': self.n_radial_bins,
                    'n_angular_bins': self.n_angular_bins
                },
                'error': 'No valid lineage RWAs computed'
            }

        # Combine lineage RWAs with pixel-wise multiplication
        print(f"\nCombining {len(lineage_rwas)} lineage RWAs...")

        combined_rwa = None

        for lineage_name, lineage_rwa in lineage_rwas.items():
            print(f"  Multiplying lineage {lineage_name} (max strength: {np.max(np.sum(lineage_rwa, axis=2)):.4f})")

            if combined_rwa is None:
                combined_rwa = lineage_rwa.copy()
            else:
                combined_rwa *= lineage_rwa

            # Normalize after each multiplication to prevent underflow
            max_val = np.max(combined_rwa)
            if max_val > 0:
                combined_rwa = combined_rwa / max_val

        if combined_rwa is None:
            print("Error: Failed to compute combined RWA!")
            return {
                'combined_rwa': None,
                'lineage_rwas': lineage_rwas,
                'channel': channel,
                'target_shape': target_shape,
                'analysis_params': {
                    'nscale': self.nscale,
                    'norient': self.norient,
                    'sigma_r': self.sigma_r,
                    'sigma_theta': self.sigma_theta,
                    'n_radial_bins': self.n_radial_bins,
                    'n_angular_bins': self.n_angular_bins
                },
                'error': 'Failed to compute combined RWA'
            }

        print(f"Combined polar RWA computed (max strength: {np.max(np.sum(combined_rwa, axis=2)):.4f})")

        # Create visualization (only if we have valid data)
        if combined_rwa is not None and len(lineage_rwas) > 0:
            self._create_polar_visualization(lineage_rwas, combined_rwa, channel)

            # Save the combined RWA as numpy array
            output_file = f"combined_polar_rwa_{self.session_id}_{channel}.npy"
            np.save(output_file, combined_rwa)
            print(f"Combined polar RWA saved as: {output_file}")

            if self.pc_maps_dir:
                print(f"Individual polar PC maps saved in: {self.pc_maps_dir}")
        else:
            print("Skipping visualization and file save due to invalid data")

        # Return results
        results = {
            'combined_rwa': combined_rwa,
            'lineage_rwas': lineage_rwas,
            'channel': channel,
            'target_shape': target_shape,
            'analysis_params': {
                'nscale': self.nscale,
                'norient': self.norient,
                'sigma_r': self.sigma_r,
                'sigma_theta': self.sigma_theta,
                'n_radial_bins': self.n_radial_bins,
                'n_angular_bins': self.n_angular_bins
            }
        }

        return results

    def _create_polar_visualization(self, lineage_rwas, combined_rwa, channel):
        """Create visualization of lineage RWAs and combined result in polar coordinates."""

        n_lineages = len(lineage_rwas)

        if n_lineages == 0:
            print("Warning: No lineage RWAs to visualize")
            return

        if combined_rwa is None:
            print("Warning: No combined RWA to visualize, showing only lineage RWAs")
            fig, axes = plt.subplots(2, n_lineages, figsize=(4 * n_lineages, 8))
        else:
            # Create figure with lineage RWAs and combined result
            n_cols = min(n_lineages + 1, 4)
            fig, axes = plt.subplots(2, n_cols, figsize=(4 * n_cols, 8))

        # Ensure axes is 2D
        if len(axes.shape) == 1:
            axes = axes.reshape(1, -1)
        if axes.shape[0] == 1:
            axes = np.vstack([axes, axes])  # Duplicate row if only one row

        # Plot each lineage RWA
        for i, (lineage_name, lineage_rwa) in enumerate(lineage_rwas.items()):
            # Total strength across orientations
            total_strength = np.sum(lineage_rwa, axis=2)  # Shape: (n_radial, n_angular)

            # Plot as polar heatmap
            im1 = axes[0, i].imshow(total_strength, cmap='hot', aspect='auto', origin='lower')
            axes[0, i].set_title(f'Lineage {lineage_name}\nMax: {np.max(total_strength):.3f}')
            axes[0, i].set_xlabel('Angular bins')
            axes[0, i].set_ylabel('Radial bins')
            plt.colorbar(im1, ax=axes[0, i], fraction=0.046, pad=0.04)

            # Orientation visualization - show dominant orientation
            dominant_orientation = np.argmax(lineage_rwa, axis=2)
            im2 = axes[1, i].imshow(dominant_orientation, cmap='hsv', aspect='auto', origin='lower')
            axes[1, i].set_title(f'Lineage {lineage_name} Dom. Orientations')
            axes[1, i].set_xlabel('Angular bins')
            axes[1, i].set_ylabel('Radial bins')
            plt.colorbar(im2, ax=axes[1, i], fraction=0.046, pad=0.04)

        # Plot combined result if available
        if combined_rwa is not None:
            combined_total_strength = np.sum(combined_rwa, axis=2)
            im3 = axes[0, -1].imshow(combined_total_strength, cmap='hot', aspect='auto', origin='lower')
            axes[0, -1].set_title(f'Combined RWA\nMax: {np.max(combined_total_strength):.3f}')
            axes[0, -1].set_xlabel('Angular bins')
            axes[0, -1].set_ylabel('Radial bins')
            plt.colorbar(im3, ax=axes[0, -1], fraction=0.046, pad=0.04)

            # Combined orientation visualization
            combined_dominant_orientation = np.argmax(combined_rwa, axis=2)
            im4 = axes[1, -1].imshow(combined_dominant_orientation, cmap='hsv', aspect='auto', origin='lower')
            axes[1, -1].set_title('Combined Dom. Orientations')
            axes[1, -1].set_xlabel('Angular bins')
            axes[1, -1].set_ylabel('Radial bins')
            plt.colorbar(im4, ax=axes[1, -1], fraction=0.046, pad=0.04)

        plt.tight_layout()

        # Save visualization
        output_path = f"circular_lineage_rwa_analysis_{channel}_sigmar{self.sigma_r}_sigmatheta{self.sigma_theta}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Polar visualization saved: {output_path}")

    def compile_and_export(self):
        """Required abstract method from Analysis base class"""
        pass

    def compile(self):
        """Required abstract method from Analysis base class"""
        pass


def main():
    """Example usage"""

    # Configuration
    session_id = "250507_0"
    channel = "A-002"

    # Initialize analysis with polar coordinate parameters
    analyzer = CircularLineageRWAAnalysis(
        nscale=4,  # 4 scales for phase congruency
        norient=8,  # 8 orientations for phase congruency
        sigma_r=1.0,  # Radial smoothing
        sigma_theta=1.0,  # Angular smoothing
        n_radial_bins=20,  # Number of radial distance bins
        n_angular_bins=36,  # Number of angular bins (10° each)
        pc_maps_dir=pc_maps_path,
    )

    # Run analysis using the inherited run method
    print(f"Starting circular lineage RWA analysis for session {session_id}, channel {channel}")
    analyzer.run(session_id, "raw", channel, compiled_data=None)

    print("\nCircular analysis complete!")
    print("Check the generated polar visualization and saved .npy file in the current directory.")


if __name__ == "__main__":
    main()
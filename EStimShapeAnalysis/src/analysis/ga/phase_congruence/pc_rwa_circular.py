#!/usr/bin/env python3
"""
Circular Response-Weighted Average Analysis

Computes overall RWA for top 50% responding stimuli using polar coordinates (R,O,N)
with element-wise normalization to prevent sampling bias.

Only analyzes stimuli in the top 50% of GA responses to focus on what actually
drives the cell. Each (r,o,n) bin is normalized by the count of stimuli that
contributed significant values (>10% of per-stimulus max) to that bin.

Coordinate system:
- R: radial distance from object center of mass
- O: orientation angle from object center of mass
- N: phase congruency orientation bins
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
    max_radius = max_radius / 4  # Focus on central region around object

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


def process_single_stimulus_circular(stim_row, nscale=4, norient=8, n_radial_bins=20, n_angular_bins=36,
                                     target_shape=None, pc_maps_dir=None, **phasecong_kwargs):
    """
    Process a single stimulus and return its weighted contribution and count mask in polar coordinates.
    Returns both weighted contribution and binary mask of significant values.
    """
    stim_id = stim_row['StimSpecId']
    stim_path = stim_row['StimPath']
    ga_response = stim_row['GA Response']

    # Check for valid response
    if not np.isfinite(ga_response) or ga_response <= 0:
        print(f"    Warning: Invalid GA Response for {stim_id}: {ga_response}")
        return None, None, 0.0

    try:
        # Load image
        if not os.path.exists(stim_path):
            print(f"    Warning: Image file not found: {stim_path}")
            return None, None, 0.0

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

        # Convert to float32 for speed and memory efficiency
        polar_stack = polar_stack.astype(np.float32)

        # Set target shape from first image if not provided
        if target_shape is None:
            target_shape = polar_stack.shape

        # Check if polar stack size matches target
        if polar_stack.shape != target_shape:
            print(f"    Warning: Polar stack shape mismatch for {stim_id}: {polar_stack.shape} vs {target_shape}")
            return None, None, 0.0

        # Clear original orientation stack
        del orientation_stack
        gc.collect()

        # Create significance mask: values > 10% of maximum
        max_value = np.max(polar_stack)
        significance_threshold = 0.1 * max_value
        significance_mask = polar_stack > significance_threshold

        # Weight by GA response (NO smoothing here - will smooth final RWA)
        weighted_contribution = polar_stack * ga_response

        # Clear unweighted polar stack
        del polar_stack
        gc.collect()

        return weighted_contribution, significance_mask, ga_response

    except Exception as e:
        print(f"    Error processing stimulus {stim_id}: {str(e)}")
        return None, None, 0.0


class CircularRWAAnalysis(PlotTopNAnalysis):
    """
    Memory-efficient analysis that computes overall RWA for top 50% responding stimuli using polar coordinates.
    Uses element-wise normalization: each (r,o,n) bin divided by count of significant contributors.
    This prevents low-responding stimuli from suppressing peaks from high-responding stimuli.
    Only analyzes stimuli in the top 50% of GA responses for cleaner results.
    Optimized to smooth only at the end rather than per-stimulus for efficiency.
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

        # Use float32 for memory efficiency
        self.dtype = np.float32

        # Create PC maps directory if specified
        if self.pc_maps_dir and not os.path.exists(self.pc_maps_dir):
            os.makedirs(self.pc_maps_dir)
            print(f"Created PC maps directory: {self.pc_maps_dir}")

    def analyze(self, channel, compiled_data=None):
        """
        Analyze all stimuli and compute overall RWA in polar coordinates.
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

        # Filter to top 50% of responding stimuli
        print("Filtering to top 50% of responding stimuli...")
        compiled_data_sorted = compiled_data.sort_values('GA Response', ascending=False)
        top_50_count = len(compiled_data_sorted) // 2
        compiled_data = compiled_data_sorted.head(top_50_count).reset_index(drop=True)

        print(f"Filtered from {len(compiled_data_sorted)} to {len(compiled_data)} stimuli (top 50%)")
        print(f"GA Response range: {compiled_data['GA Response'].min():.4f} - {compiled_data['GA Response'].max():.4f}")

        # Show lineage distribution for information
        lineage_counts = compiled_data.groupby('Lineage').size().sort_values(ascending=False)
        print(f"Lineage stimulus counts in top 50%:")
        for lineage, count in lineage_counts.items():
            print(f"  Lineage {lineage}: {count} stimuli")

        print(f"\nProcessing top 50% stimuli ({len(compiled_data)} stimuli)")
        print("  Note: Using element-wise normalization by significant contribution counts")
        print("  Significance threshold: >10% of per-stimulus maximum")

        weighted_sum = None
        count_matrix = None  # Tracks how many stimuli contribute significantly to each (r,o,n)
        total_weight = 0.0
        processed_count = 0
        target_shape = None

        # Process each stimulus
        for idx, stim_row in compiled_data.iterrows():
            stim_id = stim_row['StimSpecId']
            ga_response = stim_row['GA Response']

            print(
                f"  Processing stimulus {processed_count + 1}/{len(compiled_data)}: {stim_id} (response: {ga_response:.4f})")

            # Process single stimulus in polar coordinates (unsmoothed)
            weighted_contribution, significance_mask, weight = process_single_stimulus_circular(
                stim_row,
                nscale=self.nscale,
                norient=self.norient,
                n_radial_bins=self.n_radial_bins,
                n_angular_bins=self.n_angular_bins,
                target_shape=target_shape,
                pc_maps_dir=self.pc_maps_dir,
                **self.phasecong_kwargs
            )

            if weighted_contribution is not None and significance_mask is not None:
                # Set target shape from first successful image
                if target_shape is None:
                    target_shape = weighted_contribution.shape
                    print(
                        f"  Set target polar shape: {target_shape} (R={self.n_radial_bins}, O={self.n_angular_bins}, N={self.norient})")

                # Initialize matrices on first valid stimulus
                if weighted_sum is None:
                    weighted_sum = weighted_contribution.astype(self.dtype)
                    count_matrix = significance_mask.astype(np.int32)
                else:
                    # Accumulate weighted sum and count significant contributions
                    weighted_sum += weighted_contribution.astype(self.dtype)
                    count_matrix += significance_mask.astype(np.int32)

                total_weight += weight
                processed_count += 1

            # Clear contribution and mask from memory
            del weighted_contribution, significance_mask
            gc.collect()

        # Compute overall RWA with element-wise normalization
        if weighted_sum is not None and count_matrix is not None and total_weight > 0:
            # Element-wise division: each (r,o,n) bin normalized by its contribution count
            # Add small epsilon to avoid division by zero
            epsilon = 1e-8
            count_matrix_safe = np.maximum(count_matrix, 1).astype(np.float32)  # Avoid division by zero

            # Element-wise normalization - this is the key change!
            unsmoothed_rwa = weighted_sum / count_matrix_safe

            print(f"  Element-wise normalization completed:")
            print(f"    Average contributions per bin: {np.mean(count_matrix):.2f}")
            print(f"    Max contributions per bin: {np.max(count_matrix)}")
            print(f"    Bins with 1 contributor: {np.sum(count_matrix == 1)}")
            print(f"    Bins with >10 contributors: {np.sum(count_matrix > 10)}")

            # Check for any NaN or infinite values in the result
            if np.any(~np.isfinite(unsmoothed_rwa)):
                print(f"  Warning: Invalid values detected in overall RWA")
                return {
                    'overall_rwa': None,
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
                    'error': 'Invalid values in overall RWA'
                }

            # Now apply smoothing once to the final RWA (efficient!)
            overall_rwa = create_smoothed_polar_map(unsmoothed_rwa, self.sigma_r, self.sigma_theta)

            print(f"  Overall RWA computed with element-wise normalization:")
            print(f"    Processed: {processed_count}/{len(compiled_data)} stimuli")
            print(f"    Total weight: {total_weight:.4f}")
            print(f"    Max strength (after smoothing): {np.max(np.sum(overall_rwa, axis=2)):.4f}")

            # Clear intermediate arrays
            del weighted_sum, unsmoothed_rwa, count_matrix
            gc.collect()
        else:
            print(f"  Warning: No valid stimuli processed")
            print(f"    Processed: {processed_count}/{len(compiled_data)} stimuli")
            print(f"    Total weight: {total_weight:.4f}")
            print(f"    Weighted sum exists: {weighted_sum is not None}")
            print(f"    Count matrix exists: {count_matrix is not None}")
            return {
                'overall_rwa': None,
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
                'error': 'No valid stimuli processed'
            }

        # Create visualization
        if overall_rwa is not None:
            self._create_polar_rwa_visualization(overall_rwa, channel, total_weight, processed_count)

            # Save the overall RWA as numpy array
            output_file = f"top50_polar_rwa_{self.session_id}_{channel}.npy"
            np.save(output_file, overall_rwa)
            print(f"Top 50% polar RWA saved as: {output_file}")

            if self.pc_maps_dir:
                print(f"Individual polar PC maps saved in: {self.pc_maps_dir}")
                # Save overall RWA and count matrix for analysis
                overall_file = os.path.join(self.pc_maps_dir, f"overall_rwa_smoothed.npy")
                np.save(overall_file, overall_rwa)
        else:
            print("Skipping visualization and file save due to invalid data")

        # Return results
        results = {
            'overall_rwa': overall_rwa,
            'channel': channel,
            'target_shape': target_shape,
            'total_weight': total_weight,
            'processed_count': processed_count,
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

    def _plot_polar_heatmap(self, data_2d, ax, title="", cmap='hot'):
        """Plot 2D data (radial x angular) as a polar heatmap"""
        n_radial, n_angular = data_2d.shape

        # Create coordinate arrays
        theta = np.linspace(0, 2 * np.pi, n_angular, endpoint=False)
        radius = np.linspace(0, 1, n_radial)

        # Create meshgrid
        R, T = np.meshgrid(radius, theta, indexing='ij')

        # Plot
        im = ax.pcolormesh(T, R, data_2d, cmap=cmap, shading='auto')

        # Formatting
        ax.set_ylim(0, 1)
        ax.set_theta_zero_location('E')  # 0° points East (right)
        ax.set_theta_direction(1)  # Counter-clockwise
        ax.grid(True, alpha=0.3)
        ax.set_title(title, pad=20)

        return im

    def _create_true_polar_plot_with_same_colors(self, polar_stack, ax):
        """
        Create polar plot using EXACTLY the same color scheme as the Cartesian version
        """
        n_radial, n_angular, norient = polar_stack.shape

        # Create polar coordinate meshgrid
        theta = np.linspace(0, 2 * np.pi, n_angular, endpoint=False)
        radius = np.linspace(0, 1, n_radial)
        R, T = np.meshgrid(radius, theta, indexing='ij')

        # Find dominant orientation and strength - SAME logic as Cartesian
        dominant_orientation_idx = np.argmax(polar_stack, axis=2)
        dominant_strength = np.max(polar_stack, axis=2)

        # Create RGB colors using IDENTICAL mapping to Cartesian version
        hue = dominant_orientation_idx.astype(float) / norient

        # Create HSV values
        hsv_polar = np.zeros((n_radial, n_angular, 3))
        hsv_polar[:, :, 0] = hue  # Hue from orientation
        hsv_polar[:, :, 1] = 1.0  # Full saturation

        # Use strength as brightness
        max_strength = np.max(dominant_strength)
        if max_strength > 0:
            hsv_polar[:, :, 2] = dominant_strength / max_strength
        else:
            hsv_polar[:, :, 2] = 0

        # Convert to RGB
        rgb_polar = hsv_to_rgb(hsv_polar)

        # Plot using RGB colors directly (this preserves the exact color mapping)
        # We need to plot each color pixel individually for true color representation
        for r_idx in range(n_radial - 1):
            for t_idx in range(n_angular - 1):
                r_start, r_end = radius[r_idx], radius[r_idx + 1]
                t_start, t_end = theta[t_idx], theta[t_idx + 1]

                # Create patch for this polar cell
                theta_patch = np.linspace(t_start, t_end, 10)
                r_inner = np.full_like(theta_patch, r_start)
                r_outer = np.full_like(theta_patch, r_end)

                # Get the color for this cell
                cell_color = rgb_polar[r_idx, t_idx, :]

                # Plot filled area with the exact color
                ax.fill_between(theta_patch, r_inner, r_outer,
                                color=cell_color, alpha=0.8)

        # Formatting
        ax.set_ylim(0, 1)
        ax.set_theta_zero_location('E')  # 0° points East (right)
        ax.set_theta_direction(1)  # Counter-clockwise
        ax.grid(True, alpha=0.3)

        return ax

    def _create_polar_rwa_visualization(self, overall_rwa, channel, total_weight, processed_count):
        """Create polar visualization of the overall RWA with orientation profiles."""

        # Create figure with proper layout: polar plot + profile plots
        # Layout: Top = polar plot with orientation colors
        #         Bottom left = radial profiles, Bottom right = angular profiles
        fig = plt.figure(figsize=(16, 12))

        # Define colors for PC orientations
        colors = plt.cm.hsv(np.linspace(0, 1, self.norient))

        # Top: Polar plot with orientation colors
        ax_polar = plt.subplot(2, 2, (1, 2), projection='polar')
        self._create_true_polar_plot_with_same_colors(overall_rwa, ax_polar)

        # Calculate max strength for title
        total_strength = np.sum(overall_rwa, axis=2)
        max_strength = np.max(total_strength)

        ax_polar.set_title(f'Top 50% RWA - Channel {channel}\n'
                           f'Max: {max_strength:.3f} | Stimuli: {processed_count} | Weight: {total_weight:.1f}',
                           pad=30, fontsize=14, fontweight='bold')

        # Bottom left: Radial strength profiles by PC orientation
        ax_radial = plt.subplot(2, 2, 3)
        radial_bin_centers = np.arange(self.n_radial_bins)

        # Plot separate line for each PC orientation
        for orient_idx in range(self.norient):
            # Average across angular bins for this orientation
            radial_strength = np.mean(overall_rwa[:, :, orient_idx], axis=1)
            angle_deg = orient_idx * (180.0 / self.norient)

            ax_radial.plot(radial_bin_centers, radial_strength,
                           color=colors[orient_idx], linewidth=2,
                           label=f'{angle_deg:.0f}°')

        ax_radial.set_xlabel('Radial bin (center to edge)')
        ax_radial.set_ylabel('Average Strength')
        ax_radial.set_title('Radial Strength by PC Orientation')
        ax_radial.grid(True, alpha=0.3)
        ax_radial.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)

        # Bottom right: Angular strength profiles by PC orientation
        ax_angular = plt.subplot(2, 2, 4)
        angular_bin_centers = np.arange(self.n_angular_bins) * (360.0 / self.n_angular_bins)

        # Plot separate line for each PC orientation
        for orient_idx in range(self.norient):
            # Average across radial bins for this orientation
            angular_strength = np.mean(overall_rwa[:, :, orient_idx], axis=0)
            angle_deg = orient_idx * (180.0 / self.norient)

            ax_angular.plot(angular_bin_centers, angular_strength,
                            color=colors[orient_idx], linewidth=2,
                            label=f'{angle_deg:.0f}°')

        ax_angular.set_xlabel('Polar Angle (degrees)')
        ax_angular.set_ylabel('Average Strength')
        ax_angular.set_title('Angular Strength by PC Orientation')
        ax_angular.set_xlim(0, 360)
        ax_angular.grid(True, alpha=0.3)
        ax_angular.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)

        # Add overall subtitle
        fig.suptitle(f'Polar Response-Weighted Average Analysis\n'
                     f'σr={self.sigma_r}, σθ={self.sigma_theta} | '
                     f'Hue = PC Orientation, Brightness = Strength',
                     fontsize=12, y=0.95)

        plt.tight_layout()

        # Save visualization
        output_path = f"polar_top50_rwa_analysis_{channel}_sigmar{self.sigma_r}_sigmatheta{self.sigma_theta}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Top 50% polar RWA visualization saved: {output_path}")

        # Clear figure from memory
        del fig
        gc.collect()

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
    analyzer = CircularRWAAnalysis(
        nscale=4,  # 4 scales for phase congruency
        norient=8,  # 8 orientations for phase congruency
        sigma_r=1.0,  # Radial smoothing
        sigma_theta=1.0,  # Angular smoothing
        n_radial_bins=20,  # Number of radial distance bins
        n_angular_bins=36,  # Number of angular bins (10° each)
        pc_maps_dir=pc_maps_path,
    )

    # Run analysis using the inherited run method
    print(f"Starting top 50% polar RWA analysis for session {session_id}, channel {channel}")
    analyzer.run(session_id, "raw", channel, compiled_data=None)

    print("\nTop 50% polar analysis complete!")
    print("Check the generated polar visualization and saved .npy file in the current directory.")
    print("Analysis focused on stimuli that actually drive the cell well.")


if __name__ == "__main__":
    main()
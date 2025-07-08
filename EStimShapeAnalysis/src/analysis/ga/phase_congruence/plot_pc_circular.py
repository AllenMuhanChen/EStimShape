#!/usr/bin/env python3
"""
Top N Circular Phase Congruency Analysis

Finds and visualizes the top N stimuli based on their polar coordinate phase congruency patterns.
Converts phase congruency maps from Cartesian (X,Y,N) to polar coordinates (R,O,N) where:
- R: radial distance from object center of mass
- O: angular position around object center
- N: phase congruency orientation bins

Direct comparison between Cartesian and Polar coordinate representations.
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
    max_radius = max_radius / 4
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


class PlotTopNCircularPCAnalysis(PlotTopNAnalysis):
    """
    Analysis to find and visualize top N stimuli using polar coordinate phase congruency maps.
    """

    def __init__(self, n_top=10, nscale=4, norient=8, sigma_r=1.0, sigma_theta=1.0,
                 n_radial_bins=20, n_angular_bins=36, **phasecong_kwargs):
        """
        Initialize PlotTopNCircularPCAnalysis

        Args:
            n_top: Number of top stimuli to analyze
            nscale: Number of scales for phase congruency
            norient: Number of orientations for phase congruency
            sigma_r: Standard deviation for radial smoothing
            sigma_theta: Standard deviation for angular smoothing
            n_radial_bins: Number of radial distance bins
            n_angular_bins: Number of angular bins around center
            **phasecong_kwargs: Additional arguments for phase congruency
        """
        super().__init__()
        self.n_top = n_top
        self.nscale = nscale
        self.norient = norient
        self.sigma_r = sigma_r
        self.sigma_theta = sigma_theta
        self.n_radial_bins = n_radial_bins
        self.n_angular_bins = n_angular_bins
        self.phasecong_kwargs = phasecong_kwargs

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        """
        Analyze top N stimuli and generate polar coordinate phase congruency maps

        Args:
            channel: Channel identifier
            compiled_data: Pre-compiled data, if None will import from repository

        Returns:
            dict: Results containing polar pc_maps, stimuli info, and visualizations
        """
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        print(f"Analyzing top {self.n_top} stimuli for channel {channel} using polar coordinates")
        print(f"Polar coordinate settings:")
        print(f"  Radial bins: {self.n_radial_bins}")
        print(f"  Angular bins: {self.n_angular_bins}")
        print(f"  Radial smoothing sigma: {self.sigma_r}")
        print(f"  Angular smoothing sigma: {self.sigma_theta}")
        print(f"Total records in dataset: {len(compiled_data)}")

        # Group by StimSpecId and average the responses (reuse from plot_pc.py)
        print("Grouping by StimSpecId and averaging responses...")

        # Define aggregation functions for different column types
        agg_functions = {}

        # Columns to average (numeric response data)
        numeric_columns = ['GA Response', 'Cluster Response', 'RegimeScore']
        for col in numeric_columns:
            if col in compiled_data.columns:
                agg_functions[col] = 'mean'

        # Columns to take first value (should be same for same stimulus)
        single_value_columns = ['StimPath', 'Lineage', 'StimType', 'Termination',
                                'Shaft', 'Junction', 'ThumbnailPath']
        for col in single_value_columns:
            if col in compiled_data.columns:
                agg_functions[col] = 'first'

        # Group and aggregate
        compiled_data = compiled_data.groupby('StimSpecId').agg(agg_functions).reset_index()

        # Sort by GA_Response to get top N stimuli
        if 'GA Response' not in compiled_data.columns:
            raise ValueError("GA Response column not found in compiled_data")

        # Sort descending by GA Response and take top N
        top_stimuli = compiled_data.nlargest(self.n_top, 'GA Response')

        print(f"Top {self.n_top} GA Response values:")
        for i, (idx, row) in enumerate(top_stimuli.iterrows()):
            print(f"  {i + 1}. Stim ID {row['StimSpecId']}: GA Response = {row['GA Response']:.4f}")

        # Initialize accumulators for response-weighted average
        weighted_sum = None
        total_weight = 0.0
        processed_count = 0

        # Generate polar phase congruency maps for each top stimulus
        pc_results = {}

        for i, (idx, stim_row) in enumerate(top_stimuli.iterrows()):
            stim_id = stim_row['StimSpecId']
            stim_path = stim_row['StimPath']
            ga_response = stim_row['GA Response']

            print(f"\nProcessing stimulus {i + 1}/{self.n_top}: ID {stim_id}")
            print(f"  Path: {stim_path}")
            print(f"  GA Response: {ga_response:.4f}")

            try:
                # Load image
                if not os.path.exists(stim_path):
                    print(f"  Warning: Image file not found: {stim_path}")
                    continue

                img = imread(stim_path)
                print(f"  Image shape: {img.shape}")

                # Generate phase congruency map (Cartesian coordinates)
                orientation_stack, angles = calculate_pc_map(
                    img,
                    nscale=self.nscale,
                    norient=self.norient,
                    **self.phasecong_kwargs
                )

                total_strength = np.sum(orientation_stack, axis=2)
                print(f"  PC analysis complete - Max strength: {np.max(total_strength):.4f}")

                # Find object center
                object_center = find_object_center(img)
                print(f"  Object center: ({object_center[0]:.1f}, {object_center[1]:.1f})")

                # Create object-centered Cartesian version for comparison
                object_centered_orientation_stack = self._make_orientations_object_relative(
                    orientation_stack, object_center
                )

                # Convert to polar coordinates
                polar_stack, radial_bins, angular_bins = convert_to_polar_coordinates(
                    orientation_stack, object_center, self.n_radial_bins, self.n_angular_bins
                )

                print(f"  Converted to polar coordinates: {polar_stack.shape}")
                print(f"  Polar max strength: {np.max(np.sum(polar_stack, axis=2)):.4f}")

                # Create gaussian-smoothed polar map
                smoothed_polar_map = create_smoothed_polar_map(polar_stack, self.sigma_r, self.sigma_theta)

                print(f"  Smoothed polar map shape: {smoothed_polar_map.shape}")
                print(f"  Smoothed polar max strength: {np.max(np.sum(smoothed_polar_map, axis=2)):.4f}")

                # Accumulate response-weighted average
                if weighted_sum is None:
                    # Initialize on first stimulus
                    weighted_sum = smoothed_polar_map * ga_response
                else:
                    # Add weighted contribution
                    weighted_sum += smoothed_polar_map * ga_response

                total_weight += ga_response
                processed_count += 1

                print(f"  Added to weighted average with weight {ga_response:.4f}")

                # Store results
                pc_results[stim_id] = {
                    'stim_info': stim_row.to_dict(),
                    'image': img,
                    'object_center': object_center,
                    'orientation_stack': orientation_stack,  # Original XxYxN array
                    'object_centered_orientation_stack': object_centered_orientation_stack,
                    # Object-centered XxYxN array
                    'polar_stack': polar_stack,  # RxOxN polar array
                    'smoothed_polar_map': smoothed_polar_map,  # Smoothed RxOxN polar array
                    'radial_bins': radial_bins,
                    'angular_bins': angular_bins,
                    'angles': angles,
                    'total_strength': total_strength,
                    'rank': i + 1
                }

                # Clear image from memory
                del img
                gc.collect()

            except Exception as e:
                print(f"  Error processing stimulus {stim_id}: {str(e)}")
                continue

        print(f"\nSuccessfully processed {len(pc_results)} stimuli")

        # Compute response-weighted average
        response_weighted_average = None
        if weighted_sum is not None and total_weight > 0:
            response_weighted_average = weighted_sum / total_weight
            print(f"\nResponse-weighted average computed:")
            print(f"  Total weight: {total_weight:.4f}")
            print(f"  Processed stimuli: {processed_count}")
            print(f"  Weighted average max strength: {np.max(np.sum(response_weighted_average, axis=2)):.4f}")

        # Generate summary visualization
        self._create_polar_summary_visualization(pc_results, channel)

        # Generate response-weighted average visualization
        if response_weighted_average is not None:
            self._create_polar_weighted_average_visualization(response_weighted_average, channel, total_weight,
                                                              processed_count)

        return {
            'pc_results': pc_results,
            'top_stimuli_data': top_stimuli,
            'response_weighted_average': response_weighted_average,
            'total_weight': total_weight,
            'processed_count': processed_count,
            'channel': channel,
            'analysis_params': {
                'n_top': self.n_top,
                'nscale': self.nscale,
                'norient': self.norient,
                'sigma_r': self.sigma_r,
                'sigma_theta': self.sigma_theta,
                'n_radial_bins': self.n_radial_bins,
                'n_angular_bins': self.n_angular_bins
            }
        }

    def _find_object_center(self, img):
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
            print(f"    Warning: No foreground pixels found, using image center")
        else:
            # Calculate center of mass
            center_y = np.mean(foreground_coords[0])
            center_x = np.mean(foreground_coords[1])

        return (center_x, center_y)

    def _make_orientations_object_relative(self, orientation_stack, object_center):
        """
        Make orientation maps relative to object-centered position by shifting coordinates.
        """
        rows, cols, norient = orientation_stack.shape

        # Calculate image center
        img_center_x = cols // 2
        img_center_y = rows // 2

        # Calculate shift needed to put object center at image center
        shift_x = int(img_center_x - object_center[0])
        shift_y = int(img_center_y - object_center[1])

        print(f"    Shifting by: ({shift_x}, {shift_y}) pixels")

        # Shift each orientation layer
        object_centered_orientation_stack = np.zeros_like(orientation_stack)

        for i in range(norient):
            # Use numpy roll to shift the orientation map
            shifted = np.roll(orientation_stack[:, :, i], shift_y, axis=0)  # Shift Y
            shifted = np.roll(shifted, shift_x, axis=1)  # Shift X
            object_centered_orientation_stack[:, :, i] = shifted

        return object_centered_orientation_stack

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

    def _create_orientation_visualization_cartesian(self, orientation_stack, angles):
        """
        Create orientation visualization using same method as original plot_pc.py
        This ensures identical color mapping between original and polar views
        """
        rows, cols, norient = orientation_stack.shape

        # Find dominant orientation at each pixel
        dominant_orientation_idx = np.argmax(orientation_stack, axis=2)
        dominant_strength = np.max(orientation_stack, axis=2)

        # Map orientation indices to hue values (0 to 1) - SAME as original
        hue = dominant_orientation_idx.astype(float) / norient

        # Create HSV image
        hsv_image = np.zeros((rows, cols, 3))
        hsv_image[:, :, 0] = hue  # Hue from orientation
        hsv_image[:, :, 1] = 1.0  # Full saturation

        # Use strength as brightness (value)
        max_strength = np.max(dominant_strength)
        if max_strength > 0:
            hsv_image[:, :, 2] = dominant_strength / max_strength
        else:
            hsv_image[:, :, 2] = 0

        # Convert to RGB
        rgb_image = hsv_to_rgb(hsv_image)

        return rgb_image

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

    def _create_polar_summary_visualization(self, pc_results, channel):
        """Create summary visualization comparing original and polar PC maps with same colors"""

        n_results = len(pc_results)
        if n_results == 0:
            print("No results to visualize")
            return

        # Create figure with subplots (3 rows: original image, original PC orientation colors, polar PC orientation colors)
        fig, axes = plt.subplots(3, n_results, figsize=(4 * n_results, 12))
        if n_results == 1:
            axes = axes.reshape(-1, 1)

        for i, (stim_id, result) in enumerate(pc_results.items()):
            # Original image
            axes[0, i].imshow(result['image'])
            axes[0, i].set_title(
                f"Rank {result['rank']}: Stim {stim_id}\nGA Response: {result['stim_info']['GA Response']:.4f}")
            axes[0, i].axis('off')

            # Original PC with orientation colors (Cartesian coordinates)
            # Use the same color mapping as the original plot_pc.py
            original_orientation_vis = self._create_orientation_visualization_cartesian(
                result['object_centered_orientation_stack'], result['angles']
            )
            axes[1, i].imshow(original_orientation_vis)
            axes[1, i].set_title("Original PC (Cartesian)\nHue=PC Orientation, Brightness=Strength")
            axes[1, i].axis('off')

            # Remove the rectangular axis and create polar subplot
            axes[2, i].remove()
            ax_polar = fig.add_subplot(3, n_results, 2 * n_results + i + 1, projection='polar')

            # Create polar plot using SAME color scheme
            self._create_true_polar_plot_with_same_colors(result['smoothed_polar_map'], ax_polar)
            ax_polar.set_title("PC (Polar Coordinates)\nSame colors as above", pad=20)

        plt.tight_layout()

        # Save the main visualization
        output_path = f"top_{self.n_top}_polar_comparison_{channel}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Polar comparison visualization saved: {output_path}")

        # Create pure polar plots for each stimulus
        self._create_pure_polar_visualization(pc_results, channel)

    def _create_pure_polar_visualization(self, pc_results, channel):
        """Create visualization using only proper polar coordinate plots with same colors as Cartesian"""

        n_results = len(pc_results)
        if n_results == 0:
            return

        # Create figure with polar subplots
        fig = plt.figure(figsize=(6 * n_results, 12))

        for i, (stim_id, result) in enumerate(pc_results.items()):
            # Top row: Total strength in polar coordinates
            ax1 = plt.subplot(2, n_results, i + 1, projection='polar')
            total_strength = np.sum(result['smoothed_polar_map'], axis=2)
            self._plot_polar_heatmap(total_strength, ax1, title=f'Stim {stim_id}: Total PC Strength')

            # Bottom row: Orientation-colored polar plot using SAME colors as Cartesian
            ax2 = plt.subplot(2, n_results, n_results + i + 1, projection='polar')
            self._create_true_polar_plot_with_same_colors(result['smoothed_polar_map'], ax2)
            ax2.set_title(f'Stim {stim_id}: PC Orientations\n(Same colors as Cartesian view)', pad=20)

        # Add overall title
        fig.suptitle(f'Polar PC Analysis - Channel {channel}\n\n' +
                     'Direct comparison: Cartesian vs Polar coordinate representations\n' +
                     'Same color mapping: Hue = PC orientation, Brightness = strength',
                     fontsize=12, fontweight='bold')

        plt.tight_layout()

        # Save pure polar visualization
        output_path = f"top_{self.n_top}_pure_polar_pc_{channel}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Pure polar visualization saved: {output_path}")

    def _create_polar_weighted_average_visualization(self, response_weighted_average, channel, total_weight,
                                                     processed_count):
        """Create visualization of the response-weighted average polar orientation map"""

        # Calculate total strength for the weighted average
        weighted_total_strength = np.sum(response_weighted_average, axis=2)

        # Create figure with both rectangular and polar views
        fig = plt.figure(figsize=(20, 12))

        # Top row: Rectangular views (traditional heatmaps)
        # 1. Total strength rectangular heatmap
        ax1 = plt.subplot(2, 4, 1)
        im1 = ax1.imshow(weighted_total_strength, cmap='hot', aspect='auto', origin='lower')
        ax1.set_title(f'RWA Total Strength\nMax: {np.max(weighted_total_strength):.3f}')
        plt.colorbar(im1, ax=ax1, fraction=0.046, pad=0.04)

        # 2. Orientation visualization with colors
        ax2 = plt.subplot(2, 4, 2)
        weighted_orientation_vis = self._create_polar_orientation_visualization(response_weighted_average)
        ax2.imshow(weighted_orientation_vis, aspect='auto', origin='lower')
        ax2.set_title('PC Orientations by Color\n(Hue=Orientation, Brightness=Strength)')

        # 3. Radial strength profile by PC orientation
        ax3 = plt.subplot(2, 4, 3)
        radial_bin_centers = np.arange(self.n_radial_bins)

        # Plot separate line for each PC orientation
        colors = plt.cm.hsv(np.linspace(0, 1, self.norient))
        for orient_idx in range(self.norient):
            # Average across angular bins for this orientation
            radial_strength_by_orient = np.mean(response_weighted_average[:, :, orient_idx], axis=1)
            angle_deg = orient_idx * (180.0 / self.norient)
            ax3.plot(radial_bin_centers, radial_strength_by_orient,
                     color=colors[orient_idx], linewidth=2,
                     label=f'{angle_deg:.0f}°')

        ax3.set_xlabel('Radial bin (center to edge)')
        ax3.set_ylabel('Average Strength')
        ax3.set_title('Radial Strength by PC Orientation')
        ax3.grid(True, alpha=0.3)
        ax3.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)

        # 4. Angular strength profile by PC orientation
        ax4 = plt.subplot(2, 4, 4)
        angular_bin_centers = np.arange(self.n_angular_bins) * (360.0 / self.n_angular_bins)

        # Plot separate line for each PC orientation
        for orient_idx in range(self.norient):
            # Average across radial bins for this orientation
            angular_strength_by_orient = np.mean(response_weighted_average[:, :, orient_idx], axis=0)
            angle_deg = orient_idx * (180.0 / self.norient)
            ax4.plot(angular_bin_centers, angular_strength_by_orient,
                     color=colors[orient_idx], linewidth=2,
                     label=f'{angle_deg:.0f}°')

        ax4.set_xlabel('Polar Angle (degrees)')
        ax4.set_ylabel('Average Strength')
        ax4.set_title('Angular Strength by PC Orientation')
        ax4.set_xlim(0, 360)
        ax4.grid(True, alpha=0.3)
        ax4.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)

        # Bottom row: True polar coordinate plots
        # 5. Polar plot of total strength
        ax5 = plt.subplot(2, 4, 5, projection='polar')
        self._plot_polar_heatmap(weighted_total_strength, ax5,
                                 title='RWA Total Strength\n(Polar View)', cmap='hot')

        # 6. Polar plot of orientations
        ax6 = plt.subplot(2, 4, 6, projection='polar')
        self._create_true_polar_plot_with_same_colors(response_weighted_average, ax6)
        ax6.set_title('RWA PC Orientations\n(Polar View)', pad=20)

        # 7. Individual PC orientation polar plots (replace the pointless bar chart)
        ax7 = plt.subplot(2, 4, 7, projection='polar')

        # Show each PC orientation as a separate polar heatmap overlay
        # We'll show the strongest orientations with transparency
        orientation_total_strengths = np.sum(response_weighted_average, axis=(0, 1))
        strongest_orientations = np.argsort(orientation_total_strengths)[-3:]  # Top 3 orientations

        for i, orient_idx in enumerate(strongest_orientations):
            alpha = 0.4 + (i * 0.2)  # Varying transparency
            angle_deg = orient_idx * (180.0 / self.norient)
            orientation_data = response_weighted_average[:, :, orient_idx]

            # Normalize for better visualization
            if np.max(orientation_data) > 0:
                orientation_data_norm = orientation_data / np.max(orientation_data)
                im = self._plot_polar_heatmap(orientation_data_norm, ax7,
                                              cmap='hot', title='Top 3 PC Orientations\n(Overlaid)')

        # 8. Color legend explanation
        ax8 = plt.subplot(2, 4, 8)
        ax8.axis('off')

        # Create color legend showing PC orientation to color mapping
        legend_text = "COLOR MAPPING:\n\n"
        for i in range(self.norient):
            angle = i * (180.0 / self.norient)
            color = colors[i]
            legend_text += f"PC {angle:5.1f}° → "

            if angle == 0:
                legend_text += "Red\n"
            elif angle <= 22.5:
                legend_text += "Orange\n"
            elif angle <= 45:
                legend_text += "Yellow\n"
            elif angle <= 67.5:
                legend_text += "Green\n"
            elif angle <= 90:
                legend_text += "Cyan\n"
            elif angle <= 112.5:
                legend_text += "Blue\n"
            elif angle <= 135:
                legend_text += "Purple\n"
            else:
                legend_text += "Pink\n"

        legend_text += "\nRADIAL/ANGULAR PLOTS:\n"
        legend_text += "Each colored line shows\n"
        legend_text += "that PC orientation's\n"
        legend_text += "strength profile\n\n"
        legend_text += "BRIGHTNESS = Strength\n"
        legend_text += "of that orientation"

        ax8.text(0.1, 0.9, legend_text, transform=ax8.transAxes, fontsize=9,
                 verticalalignment='top', fontfamily='monospace')

        # Add overall title with statistics
        fig.suptitle(f'Polar Response-Weighted Average Analysis - Channel {channel}\n'
                     f'Stimuli: {processed_count}, Total Weight: {total_weight:.2f}, σr={self.sigma_r}, σθ={self.sigma_theta}',
                     fontsize=14, fontweight='bold')

        plt.tight_layout()

        # Save the visualization
        output_path = f"polar_response_weighted_average_{channel}_sigmar{self.sigma_r}_sigmatheta{self.sigma_theta}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Polar response-weighted average visualization saved: {output_path}")

    def _create_polar_orientation_visualization(self, polar_stack):
        """Create RGB visualization of polar stack showing orientation bins in different colors"""

        n_radial, n_angular, norient = polar_stack.shape

        # Find dominant orientation at each polar coordinate
        dominant_orientation_idx = np.argmax(polar_stack, axis=2)
        dominant_strength = np.max(polar_stack, axis=2)

        # Map orientation indices to hue values (0 to 1)
        hue = dominant_orientation_idx.astype(float) / norient

        # Create HSV image
        hsv_image = np.zeros((n_radial, n_angular, 3))
        hsv_image[:, :, 0] = hue  # Hue from PC orientation
        hsv_image[:, :, 1] = 1.0  # Full saturation

        # Use strength as brightness (value)
        max_strength = np.max(dominant_strength)
        if max_strength > 0:
            hsv_image[:, :, 2] = dominant_strength / max_strength
        else:
            hsv_image[:, :, 2] = 0

        # Convert to RGB
        rgb_image = hsv_to_rgb(hsv_image)

        return rgb_image

    def get_polar_pc_map_for_stimulus(self, stim_id, results, map_type='polar'):
        """Get the RxOxN polar phase congruency map for a specific stimulus"""
        if map_type == 'weighted_average':
            if 'response_weighted_average' not in results or results['response_weighted_average'] is None:
                raise ValueError("Response-weighted average not available in results")
            return results['response_weighted_average']

        if stim_id not in results['pc_results']:
            raise ValueError(f"Stimulus {stim_id} not found in results")

        if map_type == 'polar':
            return results['pc_results'][stim_id]['polar_stack']
        elif map_type == 'smoothed_polar':
            return results['pc_results'][stim_id]['smoothed_polar_map']
        elif map_type == 'original':
            return results['pc_results'][stim_id]['orientation_stack']
        else:
            raise ValueError(
                f"Invalid map_type: {map_type}. Use 'polar', 'smoothed_polar', 'original', or 'weighted_average'")

    def compile_and_export(self):
        """Required abstract method from Analysis base class"""
        pass

    def compile(self):
        """Required abstract method from Analysis base class"""
        pass


def main():
    """Example usage"""
    session_id = "250425_0"
    channel = "A-017"

    session_id = "250507_0"
    channel = "A-002"

    # Initialize analysis with polar coordinate parameters
    analyzer = PlotTopNCircularPCAnalysis(
        n_top=5,  # Analyze top 5 stimuli
        nscale=4,  # 4 scales for phase congruency
        norient=8,  # 8 orientations for phase congruency
        sigma_r=1.0,  # Radial smoothing
        sigma_theta=1.0,  # Angular smoothing
        n_radial_bins=20,  # Number of radial distance bins
        n_angular_bins=36,  # Number of angular bins (10° each)
    )

    # Run analysis
    print(f"Starting polar PC analysis for top {analyzer.n_top} stimuli")
    analyzer.run(session_id, "raw", channel, compiled_data=None)

    print("\nPolar PC analysis complete!")
    print("Check the generated polar visualizations in the current directory.")


if __name__ == "__main__":
    main()
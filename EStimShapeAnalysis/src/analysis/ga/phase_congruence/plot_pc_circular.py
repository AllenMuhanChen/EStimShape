#!/usr/bin/env python3
"""
Top N Circular Phase Congruency Analysis

Finds and visualizes the top N stimuli based on their polar coordinate phase congruency patterns.
Converts phase congruency maps from Cartesian (X,Y,N) to polar coordinates (R,O,N) where:
- R: radial distance from object center of mass
- O: angular position around object center
- N: phase congruency orientation bins

Reuses code from both plot_pc.py and pc_rwa_circular.py.
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
    max_radius = max_radius / 3
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

    def _create_polar_summary_visualization(self, pc_results, channel):
        """Create summary visualization of all top stimuli polar PC maps"""

        n_results = len(pc_results)
        if n_results == 0:
            print("No results to visualize")
            return

        # Create figure with subplots (4 rows: original image, original PC strength, polar PC strength, smoothed polar PC)
        fig, axes = plt.subplots(4, n_results, figsize=(4 * n_results, 16))
        if n_results == 1:
            axes = axes.reshape(-1, 1)

        for i, (stim_id, result) in enumerate(pc_results.items()):
            # Original image
            axes[0, i].imshow(result['image'])
            axes[0, i].set_title(
                f"Rank {result['rank']}: Stim {stim_id}\nGA Response: {result['stim_info']['GA Response']:.4f}")
            axes[0, i].axis('off')

            # Original total phase congruency strength (Cartesian)
            im1 = axes[1, i].imshow(result['total_strength'], cmap='hot')
            axes[1, i].set_title(f"Original PC Strength\n(Max: {np.max(result['total_strength']):.3f})")
            axes[1, i].axis('off')
            plt.colorbar(im1, ax=axes[1, i], fraction=0.046, pad=0.04)

            # Polar coordinate PC with orientation bins shown in color
            polar_orientation_vis = self._create_polar_orientation_visualization(result['polar_stack'])
            axes[2, i].imshow(polar_orientation_vis, aspect='auto', origin='lower')
            axes[2, i].set_title(f"Polar PC by Orientation\n(Hue=Orientation, Brightness=Strength)")
            axes[2, i].set_xlabel('Angular bins')
            axes[2, i].set_ylabel('Radial bins')

            # Smoothed polar coordinate PC with orientation bins shown in color
            smoothed_polar_orientation_vis = self._create_polar_orientation_visualization(result['smoothed_polar_map'])
            axes[3, i].imshow(smoothed_polar_orientation_vis, aspect='auto', origin='lower')
            axes[3, i].set_title(f"Smoothed Polar PC by Orientation\n(σr={self.sigma_r}, σθ={self.sigma_theta})")
            axes[3, i].set_xlabel('Angular bins')
            axes[3, i].set_ylabel('Radial bins')

        plt.tight_layout()

        # Save the main visualization
        output_path = f"top_{self.n_top}_polar_pc_analysis_{channel}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Polar summary visualization saved: {output_path}")

        # Create additional detailed visualization showing individual orientation bins
        self._create_individual_orientation_visualization(pc_results, channel)

    def _create_individual_orientation_visualization(self, pc_results, channel):
        """Create detailed visualization showing individual orientation bins for each stimulus"""

        n_results = len(pc_results)
        if n_results == 0:
            return

        # Create a figure showing individual orientation bins for each stimulus
        # Rows: stimuli, Columns: orientation bins
        fig, axes = plt.subplots(n_results, self.norient, figsize=(2 * self.norient, 3 * n_results))

        if n_results == 1:
            axes = axes.reshape(1, -1)
        if self.norient == 1:
            axes = axes.reshape(-1, 1)

        for i, (stim_id, result) in enumerate(pc_results.items()):
            for orient_idx in range(self.norient):
                # Get the smoothed polar map for this specific orientation
                orient_map = result['smoothed_polar_map'][:, :, orient_idx]

                # Plot this orientation bin
                im = axes[i, orient_idx].imshow(orient_map, cmap='hot', aspect='auto', origin='lower')

                # Calculate orientation angle in degrees
                orient_angle = orient_idx * (180.0 / self.norient)

                if i == 0:  # Only add column titles on top row
                    axes[i, orient_idx].set_title(f'{orient_angle:.0f}°', fontsize=10)

                if orient_idx == 0:  # Only add row labels on left column
                    axes[i, orient_idx].set_ylabel(f'Stim {stim_id}\nRank {result["rank"]}', fontsize=8)

                axes[i, orient_idx].set_xticks([])
                axes[i, orient_idx].set_yticks([])

                # Add small colorbar
                plt.colorbar(im, ax=axes[i, orient_idx], fraction=0.046, pad=0.04)

        plt.suptitle(f'Individual PC Orientation Bins (Polar Coordinates) - Channel {channel}',
                     fontsize=14, fontweight='bold')
        plt.tight_layout()

        # Save the detailed visualization
        output_path = f"top_{self.n_top}_polar_pc_orientations_{channel}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Individual orientation visualization saved: {output_path}")

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

    def _create_polar_weighted_average_visualization(self, response_weighted_average, channel, total_weight,
                                                     processed_count):
        """Create visualization of the response-weighted average polar orientation map"""

        # Calculate total strength for the weighted average
        weighted_total_strength = np.sum(response_weighted_average, axis=2)  # Shape: (n_radial, n_angular)

        # Create figure with multiple views of the weighted average
        fig, axes = plt.subplots(2, 3, figsize=(18, 10))

        # 1. Total strength polar heatmap
        im1 = axes[0, 0].imshow(weighted_total_strength, cmap='hot', aspect='auto', origin='lower')
        axes[0, 0].set_title(f'Polar RWA Total Strength\nMax: {np.max(weighted_total_strength):.3f}')
        axes[0, 0].set_xlabel('Angular bins')
        axes[0, 0].set_ylabel('Radial bins')
        plt.colorbar(im1, ax=axes[0, 0], fraction=0.046, pad=0.04)

        # 2. Orientation visualization with colors for different orientations
        weighted_orientation_vis = self._create_polar_orientation_visualization(response_weighted_average)
        axes[0, 1].imshow(weighted_orientation_vis, aspect='auto', origin='lower')
        axes[0, 1].set_title('PC Orientations by Color\n(Hue=Orientation, Brightness=Strength)')
        axes[0, 1].set_xlabel('Angular bins')
        axes[0, 1].set_ylabel('Radial bins')

        # 3. Radial strength profile (average across all angles)
        radial_strength = np.mean(weighted_total_strength, axis=1)  # Average across angular bins
        radial_bin_centers = np.arange(self.n_radial_bins)
        axes[0, 2].plot(radial_bin_centers, radial_strength, 'b-', linewidth=2)
        axes[0, 2].set_xlabel('Radial bin (center to edge)')
        axes[0, 2].set_ylabel('Average Strength')
        axes[0, 2].set_title('Radial Strength Profile')
        axes[0, 2].grid(True, alpha=0.3)

        # 4. Angular strength profile (average across all radii)
        angular_strength = np.mean(weighted_total_strength, axis=0)  # Average across radial bins
        angular_bin_centers = np.arange(self.n_angular_bins) * (360.0 / self.n_angular_bins)
        axes[1, 0].plot(angular_bin_centers, angular_strength, 'r-', linewidth=2)
        axes[1, 0].set_xlabel('Angle (degrees)')
        axes[1, 0].set_ylabel('Average Strength')
        axes[1, 0].set_title('Angular Strength Profile')
        axes[1, 0].set_xlim(0, 360)
        axes[1, 0].grid(True, alpha=0.3)

        # 5. PC Orientation strength distribution (summed over spatial dimensions)
        orientation_strengths = np.sum(response_weighted_average, axis=(0, 1))  # Sum over radial and angular dimensions
        orientation_angles_deg = np.arange(self.norient) * (180.0 / self.norient)

        axes[1, 1].bar(orientation_angles_deg, orientation_strengths,
                       width=180.0 / self.norient * 0.8, alpha=0.7,
                       color=plt.cm.hsv(np.linspace(0, 1, self.norient)))
        axes[1, 1].set_xlabel('PC Orientation (degrees)')
        axes[1, 1].set_ylabel('Total Strength')
        axes[1, 1].set_title('PC Orientation Distribution')
        axes[1, 1].set_xlim(-10, 180)
        axes[1, 1].grid(True, alpha=0.3)

        # 6. 2D Radial vs Angular strength
        im3 = axes[1, 2].imshow(weighted_total_strength, cmap='hot', aspect='auto', origin='lower',
                                extent=[0, 360, 0, self.n_radial_bins])
        axes[1, 2].set_title('Polar Strength Map\n(Radius vs Angle)')
        axes[1, 2].set_xlabel('Angle (degrees)')
        axes[1, 2].set_ylabel('Radial bin')
        plt.colorbar(im3, ax=axes[1, 2], fraction=0.046, pad=0.04)

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

        # Create additional detailed visualization showing individual orientation bins for RWA
        self._create_rwa_individual_orientation_visualization(response_weighted_average, channel, total_weight,
                                                              processed_count)

    def _create_rwa_individual_orientation_visualization(self, response_weighted_average, channel, total_weight,
                                                         processed_count):
        """Create detailed visualization showing individual orientation bins for response-weighted average"""

        # Create a figure showing individual orientation bins for RWA
        # Single row with orientation bins as columns
        fig, axes = plt.subplots(1, self.norient, figsize=(2 * self.norient, 4))

        if self.norient == 1:
            axes = [axes]

        for orient_idx in range(self.norient):
            # Get the RWA for this specific orientation
            orient_map = response_weighted_average[:, :, orient_idx]

            # Plot this orientation bin
            im = axes[orient_idx].imshow(orient_map, cmap='hot', aspect='auto', origin='lower')

            # Calculate orientation angle in degrees
            orient_angle = orient_idx * (180.0 / self.norient)

            axes[orient_idx].set_title(f'PC Orient {orient_angle:.0f}°\nMax: {np.max(orient_map):.3f}', fontsize=10)
            axes[orient_idx].set_xlabel('Angular bins')
            if orient_idx == 0:
                axes[orient_idx].set_ylabel('Radial bins')
            else:
                axes[orient_idx].set_yticks([])

            # Add colorbar
            plt.colorbar(im, ax=axes[orient_idx], fraction=0.046, pad=0.04)

        plt.suptitle(f'Response-Weighted Average by PC Orientation - Channel {channel}\n'
                     f'Stimuli: {processed_count}, Total Weight: {total_weight:.2f}',
                     fontsize=12, fontweight='bold')
        plt.tight_layout()

        # Save the detailed RWA visualization
        output_path = f"polar_rwa_by_orientation_{channel}_sigmar{self.sigma_r}_sigmatheta{self.sigma_theta}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"RWA individual orientation visualization saved: {output_path}")

    def get_polar_pc_map_for_stimulus(self, stim_id, results, map_type='polar'):
        """
        Get the RxOxN polar phase congruency map for a specific stimulus

        Args:
            stim_id: Stimulus ID
            results: Results dictionary from analyze()
            map_type: Type of map to return - 'polar', 'smoothed_polar', 'original', or 'weighted_average'

        Returns:
            orientation_stack: RxOxN array (for polar) or XxYxN array (for original)
        """
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

    def compare_polar_pc_maps(self, results, stim_ids=None):
        """
        Compare polar phase congruency maps between multiple stimuli

        Args:
            results: Results dictionary from analyze()
            stim_ids: List of stimulus IDs to compare (if None, uses all)
        """
        if stim_ids is None:
            stim_ids = list(results['pc_results'].keys())

        print(f"Comparing polar PC maps for stimuli: {stim_ids}")

        # Calculate cross-correlations or other comparison metrics
        comparisons = {}

        for i, stim_id1 in enumerate(stim_ids):
            for j, stim_id2 in enumerate(stim_ids[i + 1:], i + 1):
                polar_map1 = results['pc_results'][stim_id1]['polar_stack']
                polar_map2 = results['pc_results'][stim_id2]['polar_stack']

                # Calculate correlation between total polar strengths
                total1 = np.sum(polar_map1, axis=2)
                total2 = np.sum(polar_map2, axis=2)

                correlation = np.corrcoef(total1.flatten(), total2.flatten())[0, 1]

                comparisons[(stim_id1, stim_id2)] = {
                    'polar_strength_correlation': correlation,
                    'stim1_max_polar_strength': np.max(total1),
                    'stim2_max_polar_strength': np.max(total2)
                }

                print(f"  Stim {stim_id1} vs {stim_id2}: polar correlation = {correlation:.3f}")

        return comparisons

    def compile_and_export(self):
        """Required abstract method from Analysis base class"""
        pass

    def compile(self):
        """Required abstract method from Analysis base class"""
        pass


def main():
    """Example usage"""
    # session_id = "250507_0"
    # channel = "A-002"

    session_id = "250425_0"
    channel = "A-017"

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
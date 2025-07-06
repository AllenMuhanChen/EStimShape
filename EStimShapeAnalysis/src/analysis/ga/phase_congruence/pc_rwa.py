#!/usr/bin/env python3
"""
Lineage Response-Weighted Average Analysis

Computes RWA for all stimuli in each lineage separately, then combines them
with pixel-wise multiplication. Memory-efficient implementation that processes
one image at a time.
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


def make_orientations_object_relative(orientation_stack, object_center, target_shape):
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

    # Shift each orientation layer
    object_centered_orientation_stack = np.zeros_like(orientation_stack)

    for i in range(norient):
        # Use numpy roll to shift the orientation map
        shifted = np.roll(orientation_stack[:, :, i], shift_y, axis=0)  # Shift Y
        shifted = np.roll(shifted, shift_x, axis=1)  # Shift X
        object_centered_orientation_stack[:, :, i] = shifted

    return object_centered_orientation_stack


def create_smoothed_map(orientation_stack, sigma):
    """
    Create gaussian-smoothed version of orientation stack
    """
    rows, cols, norient = orientation_stack.shape
    smoothed_map = np.zeros_like(orientation_stack)

    # Apply gaussian filter to each orientation layer
    for i in range(norient):
        smoothed_map[:, :, i] = gaussian_filter(orientation_stack[:, :, i], sigma=sigma)

    return smoothed_map

def process_single_stimulus(stim_row, nscale=4, norient=8, sigma=2.0, target_shape=None, pc_maps_dir=None, **phasecong_kwargs):
    """
    Process a single stimulus and return its contribution to the weighted average.
    Memory-efficient: loads image, processes it, saves PC map if requested, and returns only the weighted result.
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

        # Set target shape from first image if not provided
        if target_shape is None:
            target_shape = orientation_stack.shape

        # Check if image size matches target - if not, skip (or could resize)
        if orientation_stack.shape != target_shape:
            print(f"    Warning: Image shape mismatch for {stim_id}: {orientation_stack.shape} vs {target_shape}")
            return None, 0.0

        # Find object center
        object_center = find_object_center(img)

        # Clear image from memory
        del img
        gc.collect()

        # Make orientations object-relative
        object_centered_orientation_stack = make_orientations_object_relative(
            orientation_stack, object_center, target_shape
        )

        # Clear original orientation stack
        del orientation_stack
        gc.collect()

        # Create gaussian-smoothed map
        smoothed_map = create_smoothed_map(object_centered_orientation_stack, sigma)

        # Clear object-centered stack
        del object_centered_orientation_stack
        gc.collect()

        # Save the processed PC map if directory is specified
        if pc_maps_dir:
            pc_map_file = os.path.join(pc_maps_dir, f"pc_map_{stim_id}.npy")
            np.save(pc_map_file, smoothed_map)

        # Weight by GA response
        weighted_contribution = smoothed_map * ga_response

        # Clear smoothed map
        del smoothed_map
        gc.collect()

        return weighted_contribution, ga_response

    except Exception as e:
        print(f"    Error processing stimulus {stim_id}: {str(e)}")
        return None, 0.0


class LineageRWAAnalysis(PlotTopNAnalysis):
    """
    Memory-efficient analysis that computes RWA for each lineage and combines them.
    """

    def __init__(self, nscale=4, norient=8, sigma=2.0, pc_maps_dir=None, **phasecong_kwargs):
        super().__init__()  # This will properly initialize response_table and other attributes
        self.nscale = nscale
        self.norient = norient
        self.sigma = sigma
        self.pc_maps_dir = pc_maps_dir
        self.phasecong_kwargs = phasecong_kwargs

        # Create PC maps directory if specified
        if self.pc_maps_dir and not os.path.exists(self.pc_maps_dir):
            os.makedirs(self.pc_maps_dir)
            print(f"Created PC maps directory: {self.pc_maps_dir}")

    def analyze(self, channel, compiled_data=None):
        """
        Analyze all stimuli grouped by lineage and compute combined RWA.
        """
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        print(f"Analyzing all stimuli for channel {channel}")
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

                # Process single stimulus
                weighted_contribution, weight = process_single_stimulus(
                    stim_row,
                    nscale=self.nscale,
                    norient=self.norient,
                    sigma=self.sigma,
                    target_shape=target_shape,
                    pc_maps_dir=self.pc_maps_dir,  # Pass PC maps directory
                    **self.phasecong_kwargs
                )

                if weighted_contribution is not None:
                    # Set target shape from first successful image
                    if target_shape is None:
                        target_shape = weighted_contribution.shape
                        print(f"  Set target shape: {target_shape}")

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
            # Create empty results to avoid breaking the framework
            return {
                'combined_rwa': None,
                'lineage_rwas': {},
                'channel': channel,
                'target_shape': target_shape,
                'analysis_params': {
                    'nscale': self.nscale,
                    'norient': self.norient,
                    'sigma': self.sigma
                },
                'error': 'No valid lineage RWAs computed'
            }

        # Combine lineage RWAs with pixel-wise multiplication
        print(f"\nCombining {len(lineage_rwas)} lineage RWAs...")

        if len(lineage_rwas) == 0:
            print("Error: No valid lineage RWAs to combine!")
            # Create empty results to avoid breaking the framework
            return {
                'combined_rwa': None,
                'lineage_rwas': {},
                'channel': channel,
                'target_shape': target_shape,
                'analysis_params': {
                    'nscale': self.nscale,
                    'norient': self.norient,
                    'sigma': self.sigma
                },
                'error': 'No valid lineage RWAs to combine'
            }

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
            # Create empty results to avoid breaking the framework
            return {
                'combined_rwa': None,
                'lineage_rwas': lineage_rwas,
                'channel': channel,
                'target_shape': target_shape,
                'analysis_params': {
                    'nscale': self.nscale,
                    'norient': self.norient,
                    'sigma': self.sigma
                },
                'error': 'Failed to compute combined RWA'
            }

        print(f"Combined RWA computed (max strength: {np.max(np.sum(combined_rwa, axis=2)):.4f})")

        # Create visualization (only if we have valid data)
        if combined_rwa is not None and len(lineage_rwas) > 0:
            self._create_visualization(lineage_rwas, combined_rwa, channel)

            # Save the combined RWA as numpy array
            output_file = f"combined_rwa_{self.session_id}_{channel}.npy"
            np.save(output_file, combined_rwa)
            print(f"Combined RWA saved as: {output_file}")

            if self.pc_maps_dir:
                print(f"Individual PC maps saved in: {self.pc_maps_dir}")
        else:
            print("Skipping visualization and file save due to invalid data")

        # Clear lineage RWAs from memory except for return
        results = {
            'combined_rwa': combined_rwa,
            'lineage_rwas': lineage_rwas,
            'channel': channel,
            'target_shape': target_shape,
            'analysis_params': {
                'nscale': self.nscale,
                'norient': self.norient,
                'sigma': self.sigma
            }
        }

        return results

    def _create_visualization(self, lineage_rwas, combined_rwa, channel):
        """Create visualization of lineage RWAs and combined result."""

        n_lineages = len(lineage_rwas)

        if n_lineages == 0:
            print("Warning: No lineage RWAs to visualize")
            return

        if combined_rwa is None:
            print("Warning: No combined RWA to visualize, showing only lineage RWAs")
            # Create figure with just lineage RWAs
            fig, axes = plt.subplots(2, n_lineages, figsize=(4 * n_lineages, 8))

            # Ensure axes is 2D
            if n_lineages == 1:
                axes = axes.reshape(2, 1)
            elif axes.ndim == 1:
                axes = axes.reshape(1, -1)

            # Plot each lineage RWA
            for i, (lineage_name, lineage_rwa) in enumerate(lineage_rwas.items()):
                # Total strength
                total_strength = np.sum(lineage_rwa, axis=2)
                im1 = axes[0, i].imshow(total_strength, cmap='hot')
                axes[0, i].set_title(f'Lineage {lineage_name}\nMax: {np.max(total_strength):.3f}')
                axes[0, i].axis('off')
                plt.colorbar(im1, ax=axes[0, i], fraction=0.046, pad=0.04)

                # Orientation visualization
                angles = np.array([j * (np.pi / self.norient) for j in range(self.norient)])
                orientation_vis = self._create_orientation_visualization(lineage_rwa, angles, total_strength)
                axes[1, i].imshow(orientation_vis)
                axes[1, i].set_title(f'Lineage {lineage_name} Orientations')
                axes[1, i].axis('off')

            plt.tight_layout()

            # Save visualization
            output_path = f"lineage_only_rwa_analysis_{channel}_sigma{self.sigma}.png"
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()

            print(f"Lineage-only visualization saved: {output_path}")
            return

        # Create figure with lineage RWAs and combined result
        # Use max of 4 columns (3 lineages + 1 combined) or actual number + 1
        n_cols = min(n_lineages + 1, 4)
        fig, axes = plt.subplots(2, n_cols, figsize=(4 * n_cols, 8))

        # Ensure axes is 2D
        if n_cols == 1:
            axes = axes.reshape(2, 1)
        elif axes.ndim == 1:
            axes = axes.reshape(1, -1)

        # Plot each lineage RWA
        for i, (lineage_name, lineage_rwa) in enumerate(lineage_rwas.items()):
            # Total strength
            total_strength = np.sum(lineage_rwa, axis=2)
            im1 = axes[0, i].imshow(total_strength, cmap='hot')
            axes[0, i].set_title(f'Lineage {lineage_name}\nMax: {np.max(total_strength):.3f}')
            axes[0, i].axis('off')
            plt.colorbar(im1, ax=axes[0, i], fraction=0.046, pad=0.04)

            # Orientation visualization
            angles = np.array([j * (np.pi / self.norient) for j in range(self.norient)])
            orientation_vis = self._create_orientation_visualization(lineage_rwa, angles, total_strength)
            axes[1, i].imshow(orientation_vis)
            axes[1, i].set_title(f'Lineage {lineage_name} Orientations')
            axes[1, i].axis('off')

        # Plot combined result
        combined_total_strength = np.sum(combined_rwa, axis=2)
        im2 = axes[0, -1].imshow(combined_total_strength, cmap='hot')
        axes[0, -1].set_title(f'Combined RWA\nMax: {np.max(combined_total_strength):.3f}')
        axes[0, -1].axis('off')
        plt.colorbar(im2, ax=axes[0, -1], fraction=0.046, pad=0.04)

        # Combined orientation visualization
        angles = np.array([j * (np.pi / self.norient) for j in range(self.norient)])
        combined_orientation_vis = self._create_orientation_visualization(combined_rwa, angles, combined_total_strength)
        axes[1, -1].imshow(combined_orientation_vis)
        axes[1, -1].set_title('Combined Orientations')
        axes[1, -1].axis('off')

        plt.tight_layout()

        # Save visualization
        output_path = f"lineage_rwa_analysis_{channel}_sigma{self.sigma}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Visualization saved: {output_path}")

    def _create_orientation_visualization(self, orientation_stack, angles, total_strength):
        """Create orientation visualization using hue for orientation and brightness for strength"""

        rows, cols, norient = orientation_stack.shape

        # Find dominant orientation at each pixel
        dominant_orientation_idx = np.argmax(orientation_stack, axis=2)
        dominant_strength = np.max(orientation_stack, axis=2)

        # Map orientation indices to hue values (0 to 1)
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

    def compile_and_export(self):
        """Required abstract method from Analysis base class"""
        # For this analysis, we don't need to compile and export anything
        # The visualization is saved in analyze()
        pass

    def compile(self):
        """Required abstract method from Analysis base class"""
        # For this analysis, we don't need additional compilation
        # The results are returned directly from analyze()
        pass

def main():
    """Example usage"""

    # Configuration
    session_id = "250507_0"
    channel = "A-002"

    # Initialize analysis
    analyzer = LineageRWAAnalysis(
        nscale=4,  # 4 scales for phase congruency
        norient=8,  # 8 orientations
        sigma=4.0, # Standard deviation for gaussian smoothing
        pc_maps_dir=pc_maps_path,
    )

    # Run analysis using the inherited run method that sets up session_id and response_table
    print(f"Starting lineage RWA analysis for session {session_id}, channel {channel}")
    analyzer.run(session_id, "raw", channel, compiled_data=None)

    print("\nAnalysis complete!")
    print("Check the generated visualization and saved .npy file in the current directory.")


if __name__ == "__main__":
    main()
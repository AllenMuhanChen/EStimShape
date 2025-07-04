import pandas as pd
import numpy as np
import os
from matplotlib.image import imread
import matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb
from scipy.ndimage import gaussian_filter  # Add this import

from src.analysis import Analysis
from src.analysis.ga.phase_congruence.calculate_pc_map import calculate_pc_map
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.repository.import_from_repository import import_from_repository

# Import the phase congruency function we created
from phasepack.phasecong import phasecong


def calculate_pc_map(img, nscale=5, norient=6, minWaveLength=3, mult=2.1,
                     sigmaOnf=0.55, k=2., cutOff=0.5, g=10., noiseMethod=-1):
    """
    Phase congruency analysis returning XxYxN orientation stack.

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


class PlotTopNPCAnalysis(PlotTopNAnalysis):

    def __init__(self, n_top=10, nscale=4, norient=8, sigma=2.0, **phasecong_kwargs):
        """
        Initialize PlotTopNPCAnalysis

        Args:
            n_top: Number of top stimuli to analyze
            nscale: Number of scales for phase congruency
            norient: Number of orientations for phase congruency
            sigma: Standard deviation for gaussian smoothing
            **phasecong_kwargs: Additional arguments for phase congruency
        """
        super().__init__()
        self.n_top = n_top
        self.nscale = nscale
        self.norient = norient
        self.sigma = sigma  # Add sigma parameter for gaussian smoothing
        self.phasecong_kwargs = phasecong_kwargs

    def analyze(self, channel, compiled_data: pd.DataFrame = None):
        """
        Analyze top N stimuli and generate phase congruency maps

        Args:
            channel: Channel identifier
            compiled_data: Pre-compiled data, if None will import from repository

        Returns:
            dict: Results containing pc_maps, stimuli info, and visualizations
        """
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        print(f"Analyzing top {self.n_top} stimuli for channel {channel}")
        print(f"Total records in dataset: {len(compiled_data)}")

        # Group by StimSpecId and average the responses
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

        # Generate phase congruency maps for each top stimulus
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

                # Generate phase congruency map
                orientation_stack, angles, total_strength, pc_detailed = calculate_pc_map(
                    img,
                    nscale=self.nscale,
                    norient=self.norient,
                    **self.phasecong_kwargs
                )

                print(f"  PC analysis complete - Max strength: {np.max(total_strength):.4f}")

                # Modify orientation_stack to be relative to object center
                object_centered_orientation_stack = self._make_orientations_object_relative(
                    img, orientation_stack, angles
                )

                print(f"  Object-centered orientation stack shape: {object_centered_orientation_stack.shape}")

                # Create gaussian-smoothed map
                smoothed_map = self._create_smoothed_map(object_centered_orientation_stack, self.sigma)

                print(f"  Smoothed map shape: {smoothed_map.shape}")
                print(f"  Smoothed map max strength: {np.max(np.sum(smoothed_map, axis=2)):.4f}")

                # Accumulate response-weighted average
                if weighted_sum is None:
                    # Initialize on first stimulus
                    weighted_sum = smoothed_map * ga_response
                else:
                    # Add weighted contribution
                    weighted_sum += smoothed_map * ga_response

                total_weight += ga_response
                processed_count += 1

                print(f"  Added to weighted average with weight {ga_response:.4f}")

                # Store results
                pc_results[stim_id] = {
                    'stim_info': stim_row.to_dict(),
                    'image': img,
                    'orientation_stack': orientation_stack,  # Original XxYxN array
                    'object_centered_orientation_stack': object_centered_orientation_stack,
                    # Object-relative XxYxN array
                    'smoothed_map': smoothed_map,  # Gaussian-smoothed XxYxN array
                    'angles': angles,
                    'total_strength': total_strength,
                    'rank': i + 1
                }

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
        self._create_summary_visualization(pc_results, channel)

        # Generate response-weighted average visualization
        if response_weighted_average is not None:
            self._create_weighted_average_visualization(response_weighted_average, channel, total_weight,
                                                        processed_count)

        return {
            'pc_results': pc_results,
            'top_stimuli_data': top_stimuli,
            'response_weighted_average': response_weighted_average,
            'total_weight': total_weight,
            'processed_count': processed_count,
            'channel': channel,
            # 'angles': angles,
            'analysis_params': {
                'n_top': self.n_top,
                'nscale': self.nscale,
                'norient': self.norient,
                'sigma': self.sigma
            }
        }

    def _create_smoothed_map(self, orientation_stack, sigma):
        """
        Create gaussian-smoothed version of orientation stack

        Args:
            orientation_stack: XxYxN orientation stack
            sigma: Standard deviation for gaussian filter

        Returns:
            smoothed_map: Gaussian-smoothed XxYxN array
        """
        rows, cols, norient = orientation_stack.shape
        smoothed_map = np.zeros_like(orientation_stack)

        # Apply gaussian filter to each orientation layer
        for i in range(norient):
            smoothed_map[:, :, i] = gaussian_filter(orientation_stack[:, :, i], sigma=sigma)

        return smoothed_map

    def _create_summary_visualization(self, pc_results, channel):
        """Create summary visualization of all top stimuli PC maps"""

        n_results = len(pc_results)
        if n_results == 0:
            print("No results to visualize")
            return

        # Create figure with subplots (5 rows: original, PC strength, original orientations, object-centered orientations, smoothed orientations)
        fig, axes = plt.subplots(5, n_results, figsize=(4 * n_results, 20))
        if n_results == 1:
            axes = axes.reshape(-1, 1)

        for i, (stim_id, result) in enumerate(pc_results.items()):
            # Original image
            axes[0, i].imshow(result['image'])
            axes[0, i].set_title(
                f"Rank {result['rank']}: Stim {stim_id}\nGA Response: {result['stim_info']['GA Response']:.4f}")
            axes[0, i].axis('off')

            # Total phase congruency strength
            im1 = axes[1, i].imshow(result['total_strength'], cmap='hot')
            axes[1, i].set_title(f"PC Strength (Max: {np.max(result['total_strength']):.3f})")
            axes[1, i].axis('off')
            plt.colorbar(im1, ax=axes[1, i], fraction=0.046, pad=0.04)

            # Original orientation visualization (hue = orientation, brightness = strength)
            original_orientation_vis = self._create_orientation_visualization(
                result['orientation_stack'],
                result['angles'],
                result['total_strength']
            )
            axes[2, i].imshow(original_orientation_vis)
            axes[2, i].set_title("Original Orientations\n(Hue=Orientation, Brightness=Strength)")
            axes[2, i].axis('off')

            # Object-centered orientation visualization
            object_total_strength = np.sum(result['object_centered_orientation_stack'], axis=2)
            object_orientation_vis = self._create_orientation_visualization(
                result['object_centered_orientation_stack'],
                result['angles'],
                object_total_strength
            )
            axes[3, i].imshow(object_orientation_vis)
            axes[3, i].set_title("Object-Centered Orientations\n(Relative to Object Center)")
            axes[3, i].axis('off')

            # Smoothed orientation visualization
            smoothed_total_strength = np.sum(result['smoothed_map'], axis=2)
            smoothed_orientation_vis = self._create_orientation_visualization(
                result['smoothed_map'],
                result['angles'],
                smoothed_total_strength
            )
            axes[4, i].imshow(smoothed_orientation_vis)
            axes[4, i].set_title(f"Smoothed Orientations\n(σ={self.sigma}, Max: {np.max(smoothed_total_strength):.3f})")
            axes[4, i].axis('off')

        plt.tight_layout()

        # Save the visualization
        output_path = f"top_{self.n_top}_pc_analysis_{channel}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Summary visualization saved: {output_path}")

    def _create_weighted_average_visualization(self, response_weighted_average, channel, total_weight, processed_count):
        """Create visualization of the response-weighted average orientation map"""

        # Calculate total strength for the weighted average
        weighted_total_strength = np.sum(response_weighted_average, axis=2)

        # Use the angles from the class (assuming 8 orientations by default)
        angles = np.array([i * (np.pi / self.norient) for i in range(self.norient)])

        # Create figure with multiple views of the weighted average
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))

        # 1. Total strength heatmap
        im1 = axes[0, 0].imshow(weighted_total_strength, cmap='hot')
        axes[0, 0].set_title(f'Response-Weighted Average\nTotal Strength (Max: {np.max(weighted_total_strength):.3f})')
        axes[0, 0].axis('off')
        plt.colorbar(im1, ax=axes[0, 0], fraction=0.046, pad=0.04)

        # 2. Orientation visualization (hue = orientation, brightness = strength)
        weighted_orientation_vis = self._create_orientation_visualization(
            response_weighted_average,
            angles,
            weighted_total_strength
        )
        axes[0, 1].imshow(weighted_orientation_vis)
        axes[0, 1].set_title('Weighted Average Orientations\n(Hue=Orientation, Brightness=Strength)')
        axes[0, 1].axis('off')

        # 3. Radial strength profile from center
        center_y, center_x = weighted_total_strength.shape[0] // 2, weighted_total_strength.shape[1] // 2
        y, x = np.ogrid[:weighted_total_strength.shape[0], :weighted_total_strength.shape[1]]
        r = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)

        # Create radial bins
        max_radius = min(center_x, center_y)
        radial_bins = np.arange(0, max_radius, 2)
        radial_strength = []

        for i in range(len(radial_bins) - 1):
            mask = (r >= radial_bins[i]) & (r < radial_bins[i + 1])
            if np.any(mask):
                radial_strength.append(np.mean(weighted_total_strength[mask]))
            else:
                radial_strength.append(0)

        bin_centers = (radial_bins[:-1] + radial_bins[1:]) / 2
        axes[1, 0].plot(bin_centers, radial_strength, 'b-', linewidth=2)
        axes[1, 0].set_xlabel('Distance from Center (pixels)')
        axes[1, 0].set_ylabel('Average Strength')
        axes[1, 0].set_title('Radial Strength Profile')
        axes[1, 0].grid(True, alpha=0.3)

        # 4. Orientation strength histogram
        orientation_strengths = np.sum(response_weighted_average, axis=(0, 1))  # Sum over spatial dimensions
        orientation_angles_deg = np.degrees(angles)

        axes[1, 1].bar(orientation_angles_deg, orientation_strengths,
                       width=360 / self.norient * 0.8, alpha=0.7,
                       color=plt.cm.hsv(np.linspace(0, 1, self.norient)))
        axes[1, 1].set_xlabel('Orientation (degrees)')
        axes[1, 1].set_ylabel('Total Strength')
        axes[1, 1].set_title('Orientation Strength Distribution')
        axes[1, 1].set_xlim(-10, 180)
        axes[1, 1].grid(True, alpha=0.3)

        # Add overall title with statistics
        fig.suptitle(f'Response-Weighted Average Analysis - Channel {channel}\n'
                     f'Stimuli: {processed_count}, Total Weight: {total_weight:.2f}, σ={self.sigma}',
                     fontsize=14, fontweight='bold')

        plt.tight_layout()

        # Save the visualization
        output_path = f"response_weighted_average_{channel}_sigma{self.sigma}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Response-weighted average visualization saved: {output_path}")

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

    def get_pc_map_for_stimulus(self, stim_id, results, map_type='original'):
        """
        Get the XxYxN phase congruency map for a specific stimulus

        Args:
            stim_id: Stimulus ID
            results: Results dictionary from analyze()
            map_type: Type of map to return - 'original', 'object_centered', 'smoothed', or 'weighted_average'

        Returns:
            orientation_stack: XxYxN array where N is number of orientations
        """
        if map_type == 'weighted_average':
            if 'response_weighted_average' not in results or results['response_weighted_average'] is None:
                raise ValueError("Response-weighted average not available in results")
            return results['response_weighted_average']

        if stim_id not in results['pc_results']:
            raise ValueError(f"Stimulus {stim_id} not found in results")

        if map_type == 'original':
            return results['pc_results'][stim_id]['orientation_stack']
        elif map_type == 'object_centered':
            return results['pc_results'][stim_id]['object_centered_orientation_stack']
        elif map_type == 'smoothed':
            return results['pc_results'][stim_id]['smoothed_map']
        else:
            raise ValueError(
                f"Invalid map_type: {map_type}. Use 'original', 'object_centered', 'smoothed', or 'weighted_average'")

    def get_response_weighted_average(self, results):
        """
        Get the response-weighted average orientation map

        Args:
            results: Results dictionary from analyze()

        Returns:
            weighted_average: XxYxN array representing response-weighted average
            statistics: Dict with total_weight and processed_count
        """
        if 'response_weighted_average' not in results or results['response_weighted_average'] is None:
            raise ValueError("Response-weighted average not available in results")

        return results['response_weighted_average'], {
            'total_weight': results['total_weight'],
            'processed_count': results['processed_count']
        }

    def compare_pc_maps(self, results, stim_ids=None):
        """
        Compare phase congruency maps between multiple stimuli

        Args:
            results: Results dictionary from analyze()
            stim_ids: List of stimulus IDs to compare (if None, uses all)
        """
        if stim_ids is None:
            stim_ids = list(results['pc_results'].keys())

        print(f"Comparing PC maps for stimuli: {stim_ids}")

        # Calculate cross-correlations or other comparison metrics
        comparisons = {}

        for i, stim_id1 in enumerate(stim_ids):
            for j, stim_id2 in enumerate(stim_ids[i + 1:], i + 1):
                pc_map1 = results['pc_results'][stim_id1]['orientation_stack']
                pc_map2 = results['pc_results'][stim_id2]['orientation_stack']

                # Calculate correlation between total strengths
                total1 = np.sum(pc_map1, axis=2)
                total2 = np.sum(pc_map2, axis=2)

                correlation = np.corrcoef(total1.flatten(), total2.flatten())[0, 1]

                comparisons[(stim_id1, stim_id2)] = {
                    'strength_correlation': correlation,
                    'stim1_max_strength': np.max(total1),
                    'stim2_max_strength': np.max(total2)
                }

                print(f"  Stim {stim_id1} vs {stim_id2}: correlation = {correlation:.3f}")

        return comparisons

    def _make_orientations_object_relative(self, img, orientation_stack, angles):
        """
        Make orientation maps relative to object-centered position by shifting coordinates.

        Args:
            img: Original image
            orientation_stack: XxYxN orientation stack
            angles: Array of orientation angles

        Returns:
            object_centered_orientation_stack: Shifted XxYxN array with object at center
        """

        # Find object center of mass
        object_center = self._find_object_center(img)

        print(f"    Object center of mass: ({object_center[0]:.1f}, {object_center[1]:.1f})")

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

    def _find_object_center(self, img):
        """
        Find the center of mass of the object by averaging positions of foreground pixels.

        Args:
            img: Input image

        Returns:
            tuple: (center_x, center_y) coordinates of object center
        """

        # Convert to grayscale if needed
        if img.ndim == 3:
            if img.shape[2] == 4:  # RGBA
                rgb = img[:, :, :3]
            else:  # RGB
                rgb = img

            # Find background pixel (most common pixel value)
            if img.shape[2] == 4:
                rgb_for_background = img[:, :, :3]
            else:
                rgb_for_background = img

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
    # session_id = "250507_0"
    # channel = "A-002"

    session_id = "250425_0"
    channel = "A-017"

    # Initialize analysis
    analyzer = PlotTopNPCAnalysis(
        n_top=5,  # Analyze top 5 stimuli
        nscale=4,  # 4 scales for phase congruency
        norient=8,  # 8 orientations
        sigma=2.0  # Standard deviation for gaussian smoothing
    )

    # Run analysis
    analyzer.run(session_id, "raw", channel, compiled_data=None)


if __name__ == "__main__":
    main()
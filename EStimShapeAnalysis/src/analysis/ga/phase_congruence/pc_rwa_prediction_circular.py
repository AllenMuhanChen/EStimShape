#!/usr/bin/env python3
"""
Polar RWA Prediction Analysis (Top 50% Threshold)

Loads a saved polar RWA, keeps only the top 50% of values (sets rest to zero),
and uses it to predict responses for each stimulus, then compares predictions
to actual responses with scatter plots.
Uses polar coordinate representation (R,O,N) for consistency with RWA.

Thresholding at 50th percentile creates a highly selective model that only
considers the strongest preferences, potentially improving prediction accuracy.
"""

import pandas as pd
import numpy as np
import os
import gc
from matplotlib.image import imread
import matplotlib.pyplot as plt
from scipy.stats import pearsonr, spearmanr
from scipy.ndimage import gaussian_filter
from sklearn.metrics import mean_squared_error, r2_score

from src.analysis import Analysis
from src.repository.import_from_repository import import_from_repository
from phasepack.phasecong import phasecong


def calculate_pc_map(img, nscale=5, norient=6, minWaveLength=3, mult=2.1,
                     sigmaOnf=0.55, k=2., cutOff=0.5, g=10., noiseMethod=-1):
    """
    Phase congruency analysis returning XxYxN orientation stack.
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

    # Clear memory
    del M, m, ori, ft, PC, EO, T
    gc.collect()

    return orientation_stack


def find_object_center(img):
    """Find the center of mass of the object."""
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

    return polar_stack


def create_smoothed_polar_map(polar_stack, sigma_r=1.0, sigma_theta=1.0):
    """
    Create gaussian-smoothed version of polar stack.
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


def process_stimulus_for_polar_prediction(stim_row, rwa_shape, pc_maps_dir=None, nscale=4, norient=8,
                                          n_radial_bins=20, n_angular_bins=36, sigma_r=1.0, sigma_theta=1.0,
                                          **phasecong_kwargs):
    """
    Process a single stimulus to generate polar prediction features.
    First tries to load saved polar PC map, computes it if not available.
    Returns the processed polar PC map in the same format as the polar RWA.
    """
    stim_id = stim_row['StimSpecId']
    stim_path = stim_row['StimPath']

    # Try to load saved polar PC map first
    if pc_maps_dir:
        pc_map_file = os.path.join(pc_maps_dir, f"pc_polar_map_unsmoothed_{stim_id}.npy")
        if os.path.exists(pc_map_file):
            try:
                saved_polar_map = np.load(pc_map_file)
                # Check if saved map has correct shape
                if saved_polar_map.shape == rwa_shape:
                    # Apply smoothing to match RWA processing
                    smoothed_polar_map = create_smoothed_polar_map(saved_polar_map, sigma_r, sigma_theta)
                    return smoothed_polar_map
                else:
                    print(
                        f"    Warning: Saved polar map shape mismatch for {stim_id}: {saved_polar_map.shape} vs {rwa_shape}")
            except Exception as e:
                print(f"    Warning: Error loading saved polar map for {stim_id}: {e}")

    # If we get here, need to compute polar map
    try:
        # Load image
        if not os.path.exists(stim_path):
            print(f"    Warning: Image file not found: {stim_path}")
            return None

        img = imread(stim_path)

        # Generate phase congruency map
        orientation_stack = calculate_pc_map(
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
        polar_stack = convert_to_polar_coordinates(
            orientation_stack, object_center, n_radial_bins, n_angular_bins
        )

        # Clear original orientation stack
        del orientation_stack
        gc.collect()

        # Check if polar stack size matches RWA target shape
        if polar_stack.shape != rwa_shape:
            print(f"    Warning: Polar stack shape mismatch for {stim_id}: {polar_stack.shape} vs {rwa_shape}")
            return None

        # Apply smoothing to match RWA processing
        smoothed_polar_map = create_smoothed_polar_map(polar_stack, sigma_r, sigma_theta)

        # Clear unsmoothed polar stack
        del polar_stack
        gc.collect()

        return smoothed_polar_map

    except Exception as e:
        print(f"    Error processing stimulus {stim_id}: {str(e)}")
        return None


class PolarRWAThresholdPredictionAnalysis(Analysis):
    """
    Analysis that uses a pre-computed polar RWA (top 50% threshold) to predict stimulus responses.
    Thresholding at 50th percentile creates a highly selective model that only considers
    the strongest preferences, zeroing out weaker signals.
    """

    def __init__(self, rwa_file_path, pc_maps_dir=None, nscale=4, norient=8,
                 n_radial_bins=20, n_angular_bins=36, sigma_r=1.0, sigma_theta=1.0, **phasecong_kwargs):
        super().__init__()
        self.rwa_file_path = rwa_file_path
        self.pc_maps_dir = pc_maps_dir
        self.nscale = nscale
        self.norient = norient
        self.n_radial_bins = n_radial_bins
        self.n_angular_bins = n_angular_bins
        self.sigma_r = sigma_r
        self.sigma_theta = sigma_theta
        self.phasecong_kwargs = phasecong_kwargs

        # Load the polar RWA and apply top 50% threshold
        self.rwa = self._load_and_threshold_rwa()

        # Check if we should use saved polar PC maps or compute them
        self.use_saved_pc_maps = pc_maps_dir and os.path.exists(pc_maps_dir)
        if self.use_saved_pc_maps:
            print(f"Will use saved polar PC maps from: {pc_maps_dir}")
        else:
            print("Will compute polar PC maps on-the-fly (slower)")
            if pc_maps_dir:
                print(f"  PC maps directory not found: {pc_maps_dir}")

    def _load_and_threshold_rwa(self):
        """Load the polar RWA from file and apply top 50% threshold."""
        if not os.path.exists(self.rwa_file_path):
            raise FileNotFoundError(f"Polar RWA file not found: {self.rwa_file_path}")

        rwa = np.load(self.rwa_file_path)
        print(f"Loaded polar RWA from {self.rwa_file_path}")
        print(f"Original polar RWA shape: {rwa.shape}")
        print(f"Original polar RWA max strength: {np.max(np.sum(rwa, axis=2)):.4f}")

        # Calculate 50th percentile threshold
        threshold_50 = np.percentile(rwa, 50)
        print(f"50th percentile threshold: {threshold_50:.6f}")

        # Apply threshold: keep top 50%, zero out bottom 50%
        rwa_thresholded = rwa.copy()
        rwa_thresholded[rwa < threshold_50] = 0.0

        # Calculate statistics
        original_nonzero = np.sum(rwa > 0)
        thresholded_nonzero = np.sum(rwa_thresholded > 0)

        print(f"Thresholded polar RWA max strength: {np.max(np.sum(rwa_thresholded, axis=2)):.4f}")
        print(
            f"Non-zero values: {original_nonzero} → {thresholded_nonzero} ({thresholded_nonzero / original_nonzero * 100:.1f}%)")
        print(
            f"Values zeroed out: {original_nonzero - thresholded_nonzero} ({(original_nonzero - thresholded_nonzero) / original_nonzero * 100:.1f}%)")

        return rwa_thresholded

    def compute_polar_similarity_metrics(self, stimulus_polar_map, polar_rwa):
        """
        Compute multiple similarity metrics between stimulus polar PC map and thresholded polar RWA.

        Args:
            stimulus_polar_map: RxOxN polar phase congruency map for stimulus
            polar_rwa: RxOxN polar response-weighted average map (thresholded)

        Returns:
            dict: Dictionary of similarity metrics
        """
        metrics = {}

        # 1. Dot product (element-wise multiplication and sum) - most intuitive
        metrics['dot_product'] = np.sum(stimulus_polar_map * polar_rwa)

        # 2. Normalized dot product (cosine similarity)
        stim_norm = np.linalg.norm(stimulus_polar_map)
        rwa_norm = np.linalg.norm(polar_rwa)
        if stim_norm > 0 and rwa_norm > 0:
            metrics['cosine_similarity'] = metrics['dot_product'] / (stim_norm * rwa_norm)
        else:
            metrics['cosine_similarity'] = 0.0

        # 3. Pearson correlation (flattened arrays)
        stim_flat = stimulus_polar_map.flatten()
        rwa_flat = polar_rwa.flatten()
        if np.std(stim_flat) > 0 and np.std(rwa_flat) > 0:
            metrics['pearson_correlation'] = pearsonr(stim_flat, rwa_flat)[0]
        else:
            metrics['pearson_correlation'] = 0.0

        # 4. Total strength weighted by RWA strength
        stim_strength = np.sum(stimulus_polar_map, axis=2)
        rwa_strength = np.sum(polar_rwa, axis=2)
        metrics['strength_weighted'] = np.sum(stim_strength * rwa_strength)

        # 5. Overlap with thresholded regions only
        # Only consider regions where RWA is non-zero (top 50%)
        rwa_mask = polar_rwa > 0
        if np.any(rwa_mask):
            overlap_numerator = np.sum(stimulus_polar_map[rwa_mask] * polar_rwa[rwa_mask])
            overlap_denominator = np.sum(rwa_mask)
            metrics['selective_overlap'] = overlap_numerator / overlap_denominator if overlap_denominator > 0 else 0.0
        else:
            metrics['selective_overlap'] = 0.0

        # 6. Orientation-specific correlations (average across orientations)
        orientation_correlations = []
        for i in range(stimulus_polar_map.shape[2]):
            stim_orient = stimulus_polar_map[:, :, i].flatten()
            rwa_orient = polar_rwa[:, :, i].flatten()
            if np.std(stim_orient) > 0 and np.std(rwa_orient) > 0:
                corr = pearsonr(stim_orient, rwa_orient)[0]
                orientation_correlations.append(corr)

        if orientation_correlations:
            metrics['avg_orientation_correlation'] = np.mean(orientation_correlations)
        else:
            metrics['avg_orientation_correlation'] = 0.0

        # 7. Radial-specific correlations (average across radial bins)
        radial_correlations = []
        for r in range(stimulus_polar_map.shape[0]):
            stim_radial = stimulus_polar_map[r, :, :].flatten()
            rwa_radial = polar_rwa[r, :, :].flatten()
            if np.std(stim_radial) > 0 and np.std(rwa_radial) > 0:
                corr = pearsonr(stim_radial, rwa_radial)[0]
                radial_correlations.append(corr)

        if radial_correlations:
            metrics['avg_radial_correlation'] = np.mean(radial_correlations)
        else:
            metrics['avg_radial_correlation'] = 0.0

        return metrics

    def analyze(self, channel, compiled_data=None):
        """
        Analyze all stimuli and predict responses using the thresholded polar RWA.
        """
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        print(f"Predicting responses for channel {channel} using top 50% thresholded polar RWA")
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

        # Storage for results
        predictions_data = []
        processed_count = 0
        saved_maps_used = 0
        computed_maps = 0

        print(f"Processing {len(compiled_data)} stimuli...")

        for idx, stim_row in compiled_data.iterrows():
            stim_id = stim_row['StimSpecId']
            actual_response = stim_row['GA Response']

            if processed_count % 50 == 0:
                print(f"  Processed {processed_count}/{len(compiled_data)} stimuli...")
                if self.use_saved_pc_maps:
                    print(f"    Using saved polar maps: {saved_maps_used}, Computing: {computed_maps}")

            # Check if we have a saved polar PC map for this stimulus
            pc_map_loaded = False
            if self.use_saved_pc_maps:
                pc_map_file = os.path.join(self.pc_maps_dir, f"pc_polar_map_unsmoothed_{stim_id}.npy")
                if os.path.exists(pc_map_file):
                    pc_map_loaded = True

            # Process stimulus to get polar PC map (try saved first, compute if needed)
            stimulus_polar_map = process_stimulus_for_polar_prediction(
                stim_row,
                self.rwa.shape,
                pc_maps_dir=self.pc_maps_dir,
                nscale=self.nscale,
                norient=self.norient,
                n_radial_bins=self.n_radial_bins,
                n_angular_bins=self.n_angular_bins,
                sigma_r=self.sigma_r,
                sigma_theta=self.sigma_theta,
                **self.phasecong_kwargs
            )

            if stimulus_polar_map is not None:
                # Track whether we used saved or computed map
                if pc_map_loaded:
                    saved_maps_used += 1
                else:
                    computed_maps += 1

                # Compute similarity metrics
                metrics = self.compute_polar_similarity_metrics(stimulus_polar_map, self.rwa)

                # Store results
                result_row = {
                    'StimSpecId': stim_id,
                    'ActualResponse': actual_response,
                    'Lineage': stim_row['Lineage'],
                    'StimType': stim_row.get('StimType', 'Unknown')
                }
                result_row.update(metrics)
                predictions_data.append(result_row)

                processed_count += 1

                # Clear memory
                del stimulus_polar_map
                gc.collect()

        if len(predictions_data) == 0:
            print("Error: No valid predictions computed!")
            return None

        # Convert to DataFrame
        predictions_df = pd.DataFrame(predictions_data)

        print(f"\nPolar thresholded RWA prediction analysis complete!")
        print(f"Successfully processed: {len(predictions_df)} stimuli")
        if self.use_saved_pc_maps:
            print(f"Efficiency: {saved_maps_used} saved polar maps used, {computed_maps} computed on-the-fly")
            efficiency_pct = (saved_maps_used / (saved_maps_used + computed_maps)) * 100 if (
                                                                                                    saved_maps_used + computed_maps) > 0 else 0
            print(f"Efficiency rate: {efficiency_pct:.1f}% (higher is better)")
        else:
            print(f"All {len(predictions_df)} polar PC maps computed on-the-fly")

        # Create comprehensive analysis
        self._create_polar_threshold_prediction_analysis(predictions_df, channel)

        return {
            'predictions_df': predictions_df,
            'channel': channel,
            'rwa_file': self.rwa_file_path,
            'analysis_params': {
                'nscale': self.nscale,
                'norient': self.norient,
                'n_radial_bins': self.n_radial_bins,
                'n_angular_bins': self.n_angular_bins,
                'sigma_r': self.sigma_r,
                'sigma_theta': self.sigma_theta
            }
        }

    def _create_polar_threshold_prediction_analysis(self, predictions_df, channel):
        """Create comprehensive polar threshold prediction analysis visualization."""

        # Define prediction metrics to analyze (including threshold-specific ones)
        prediction_metrics = [
            'dot_product',
            'cosine_similarity',
            'pearson_correlation',
            'strength_weighted',
            'selective_overlap',
            'avg_orientation_correlation',
            'avg_radial_correlation'
        ]

        # Create figure with subplots
        fig, axes = plt.subplots(3, 3, figsize=(18, 18))
        axes = axes.flatten()

        # Plot each prediction metric (no lineage colors/legends)
        for i, metric in enumerate(prediction_metrics):
            ax = axes[i]

            # Plot all points in single color (no lineage distinction)
            ax.scatter(predictions_df[metric], predictions_df['ActualResponse'],
                       alpha=0.6, s=20, color='steelblue')

            # Calculate correlation statistics
            if np.std(predictions_df[metric]) > 0:
                pearson_r, pearson_p = pearsonr(predictions_df[metric], predictions_df['ActualResponse'])
                spearman_r, spearman_p = spearmanr(predictions_df[metric], predictions_df['ActualResponse'])
                r2 = r2_score(predictions_df['ActualResponse'], predictions_df[metric])
            else:
                pearson_r = pearson_p = spearman_r = spearman_p = r2 = 0

            ax.set_xlabel(f'Predicted Response ({metric})')
            ax.set_ylabel('Actual GA Response')
            ax.set_title(f'{metric.replace("_", " ").title()}\n'
                         f'Pearson r={pearson_r:.3f} (p={pearson_p:.3f})\n'
                         f'Spearman ρ={spearman_r:.3f}, R²={r2:.3f}')
            ax.grid(True, alpha=0.3)

        # Summary statistics plot
        ax = axes[7]
        correlations = []
        metric_names = []

        for metric in prediction_metrics:
            if np.std(predictions_df[metric]) > 0:
                pearson_r, _ = pearsonr(predictions_df[metric], predictions_df['ActualResponse'])
                correlations.append(pearson_r)
                metric_names.append(metric.replace('_', ' ').title())
            else:
                correlations.append(0)
                metric_names.append(metric.replace('_', ' ').title())

        bars = ax.bar(range(len(correlations)), correlations, alpha=0.7,
                      color=['red' if c < 0 else 'steelblue' for c in correlations])
        ax.set_xlabel('Prediction Metric')
        ax.set_ylabel('Pearson Correlation with Actual Response')
        ax.set_title('Threshold Prediction Performance Summary')
        ax.set_xticks(range(len(metric_names)))
        ax.set_xticklabels(metric_names, rotation=45, ha='right')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)

        # Add correlation values on bars
        for bar, corr in zip(bars, correlations):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height + (0.01 if height >= 0 else -0.03),
                    f'{corr:.3f}', ha='center', va='bottom' if height >= 0 else 'top')

        # Remove unused subplot
        axes[8].remove()

        plt.tight_layout()

        # Save visualization
        output_path = f"polar_rwa_threshold_prediction_analysis_{channel}_r{self.n_radial_bins}_o{self.n_angular_bins}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Polar threshold RWA prediction analysis saved: {output_path}")

        # Save predictions data
        csv_path = f"polar_rwa_threshold_predictions_{channel}_r{self.n_radial_bins}_o{self.n_angular_bins}.csv"
        predictions_df.to_csv(csv_path, index=False)
        print(f"Polar threshold RWA predictions data saved: {csv_path}")

        # Print summary statistics
        print(f"\n=== POLAR THRESHOLD RWA PREDICTION SUMMARY ===")
        print(f"Best performing metric: {metric_names[np.argmax(correlations)]} (r={max(correlations):.3f})")
        print(f"Worst performing metric: {metric_names[np.argmin(correlations)]} (r={min(correlations):.3f})")
        print(f"\nCorrelations by metric:")
        for metric, corr in zip(metric_names, correlations):
            print(f"  {metric}: r={corr:.3f}")
        print(f"\nNote: Using top 50% threshold RWA (bottom 50% zeroed out) for maximum selectivity")

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
    polar_rwa_file = f"top50_polar_rwa_{session_id}_{channel}.npy"

    # PC maps directory - should match what was used in polar RWA analysis
    pc_maps_dir = f"/home/r2_allen/Documents/EStimShape/allen_ga_test_250626_0/pc_maps"

    # Check if polar RWA file exists
    if not os.path.exists(polar_rwa_file):
        print(f"Error: Polar RWA file not found: {polar_rwa_file}")
        print("Please run the polar RWA analysis first to generate the polar RWA file.")
        return

    # Initialize analysis
    analyzer = PolarRWAThresholdPredictionAnalysis(
        rwa_file_path=polar_rwa_file,
        pc_maps_dir=pc_maps_dir,  # Use saved polar PC maps for efficiency
        nscale=4,  # Same parameters as used to create polar RWA
        norient=8,
        n_radial_bins=20,
        n_angular_bins=36,
        sigma_r=1.0,
        sigma_theta=1.0
    )

    # Run analysis
    print(f"Starting polar threshold RWA prediction analysis for session {session_id}, channel {channel}")
    if analyzer.use_saved_pc_maps:
        print("Using saved polar PC maps for maximum efficiency!")
    analyzer.run(session_id, "raw", channel, compiled_data=None)

    print("\nPolar threshold RWA prediction analysis complete!")
    print("Check the generated visualization and CSV file for detailed results.")
    print("Note: RWA was thresholded at 50th percentile for maximum selectivity.")


if __name__ == "__main__":
    main()
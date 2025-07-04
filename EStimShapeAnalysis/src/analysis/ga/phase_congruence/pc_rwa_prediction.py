#!/usr/bin/env python3
"""
RWA Prediction Analysis

Loads a saved RWA and uses it to predict responses for each stimulus,
then compares predictions to actual responses with scatter plots.
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


def make_orientations_object_relative(orientation_stack, object_center):
    """Make orientation maps relative to object-centered position."""
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
    """Create gaussian-smoothed version of orientation stack."""
    rows, cols, norient = orientation_stack.shape
    smoothed_map = np.zeros_like(orientation_stack)

    # Apply gaussian filter to each orientation layer
    for i in range(norient):
        smoothed_map[:, :, i] = gaussian_filter(orientation_stack[:, :, i], sigma=sigma)

    return smoothed_map


def process_stimulus_for_prediction(stim_row, rwa_shape, pc_maps_dir=None, nscale=4, norient=8, sigma=2.0,
                                    **phasecong_kwargs):
    """
    Process a single stimulus to generate prediction features.
    First tries to load saved PC map, computes it if not available.
    Returns the processed PC map in the same format as the RWA.
    """
    stim_id = stim_row['StimSpecId']
    stim_path = stim_row['StimPath']

    # Try to load saved PC map first
    if pc_maps_dir:
        pc_map_file = os.path.join(pc_maps_dir, f"pc_map_{stim_id}.npy")
        if os.path.exists(pc_map_file):
            try:
                saved_pc_map = np.load(pc_map_file)
                # Check if saved map has correct shape
                if saved_pc_map.shape == rwa_shape:
                    return saved_pc_map
                else:
                    print(
                        f"    Warning: Saved PC map shape mismatch for {stim_id}: {saved_pc_map.shape} vs {rwa_shape}")
            except Exception as e:
                print(f"    Warning: Error loading saved PC map for {stim_id}: {e}")

    # If we get here, need to compute PC map
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

        # Check if image size matches RWA target shape
        if orientation_stack.shape != rwa_shape:
            print(f"    Warning: Image shape mismatch for {stim_id}: {orientation_stack.shape} vs {rwa_shape}")
            return None

        # Find object center
        object_center = find_object_center(img)

        # Clear image from memory
        del img
        gc.collect()

        # Make orientations object-relative
        object_centered_orientation_stack = make_orientations_object_relative(
            orientation_stack, object_center
        )

        # Clear original orientation stack
        del orientation_stack
        gc.collect()

        # Create gaussian-smoothed map
        smoothed_map = create_smoothed_map(object_centered_orientation_stack, sigma)

        # Clear object-centered stack
        del object_centered_orientation_stack
        gc.collect()

        return smoothed_map

    except Exception as e:
        print(f"    Error processing stimulus {stim_id}: {str(e)}")
        return None


class RWAPredictionAnalysis(Analysis):
    """
    Analysis that uses a pre-computed RWA to predict stimulus responses.
    """

    def __init__(self, rwa_file_path, pc_maps_dir=None, nscale=4, norient=8, sigma=2.0, **phasecong_kwargs):
        super().__init__()
        self.rwa_file_path = rwa_file_path
        self.pc_maps_dir = pc_maps_dir
        self.nscale = nscale
        self.norient = norient
        self.sigma = sigma
        self.phasecong_kwargs = phasecong_kwargs

        # Load the RWA
        self.rwa = self._load_rwa()

        # Check if we should use saved PC maps or compute them
        self.use_saved_pc_maps = pc_maps_dir and os.path.exists(pc_maps_dir)
        if self.use_saved_pc_maps:
            print(f"Will use saved PC maps from: {pc_maps_dir}")
        else:
            print("Will compute PC maps on-the-fly (slower)")
            if pc_maps_dir:
                print(f"  PC maps directory not found: {pc_maps_dir}")

    def _load_rwa(self):
        """Load the RWA from file."""
        if not os.path.exists(self.rwa_file_path):
            raise FileNotFoundError(f"RWA file not found: {self.rwa_file_path}")

        rwa = np.load(self.rwa_file_path)
        print(f"Loaded RWA from {self.rwa_file_path}")
        print(f"RWA shape: {rwa.shape}")
        print(f"RWA max strength: {np.max(np.sum(rwa, axis=2)):.4f}")

        return rwa

    def _load_saved_pc_map(self, stim_id):
        """
        Load a saved PC map for a stimulus.

        Args:
            stim_id: Stimulus ID

        Returns:
            pc_map: Loaded PC map or None if not found
        """
        if not self.use_saved_pc_maps:
            return None

        pc_map_file = os.path.join(self.pc_maps_dir, f"pc_map_{stim_id}.npy")

        if os.path.exists(pc_map_file):
            try:
                pc_map = np.load(pc_map_file)
                return pc_map
            except Exception as e:
                print(f"    Warning: Error loading saved PC map for {stim_id}: {e}")
                return None
        else:
            return None

    def compute_similarity_metrics(self, stimulus_pc_map, rwa):
        """
        Compute multiple similarity metrics between stimulus PC map and RWA.

        Args:
            stimulus_pc_map: XxYxN phase congruency map for stimulus
            rwa: XxYxN response-weighted average map

        Returns:
            dict: Dictionary of similarity metrics
        """
        metrics = {}

        # 1. Dot product (element-wise multiplication and sum) - most intuitive
        metrics['dot_product'] = np.sum(stimulus_pc_map * rwa)

        # 2. Normalized dot product (cosine similarity)
        stim_norm = np.linalg.norm(stimulus_pc_map)
        rwa_norm = np.linalg.norm(rwa)
        if stim_norm > 0 and rwa_norm > 0:
            metrics['cosine_similarity'] = metrics['dot_product'] / (stim_norm * rwa_norm)
        else:
            metrics['cosine_similarity'] = 0.0

        # 3. Pearson correlation (flattened arrays)
        stim_flat = stimulus_pc_map.flatten()
        rwa_flat = rwa.flatten()
        if np.std(stim_flat) > 0 and np.std(rwa_flat) > 0:
            metrics['pearson_correlation'] = pearsonr(stim_flat, rwa_flat)[0]
        else:
            metrics['pearson_correlation'] = 0.0

        # 4. Total strength weighted by RWA strength
        stim_strength = np.sum(stimulus_pc_map, axis=2)
        rwa_strength = np.sum(rwa, axis=2)
        metrics['strength_weighted'] = np.sum(stim_strength * rwa_strength)

        # 5. Orientation-specific correlations (average across orientations)
        orientation_correlations = []
        for i in range(stimulus_pc_map.shape[2]):
            stim_orient = stimulus_pc_map[:, :, i].flatten()
            rwa_orient = rwa[:, :, i].flatten()
            if np.std(stim_orient) > 0 and np.std(rwa_orient) > 0:
                corr = pearsonr(stim_orient, rwa_orient)[0]
                orientation_correlations.append(corr)

        if orientation_correlations:
            metrics['avg_orientation_correlation'] = np.mean(orientation_correlations)
        else:
            metrics['avg_orientation_correlation'] = 0.0

        return metrics

    def analyze(self, channel, compiled_data=None):
        """
        Analyze all stimuli and predict responses using the RWA.
        """
        if compiled_data is None:
            compiled_data = import_from_repository(
                self.session_id,
                "ga",
                "GAStimInfo",
                self.response_table
            )

        print(f"Predicting responses for channel {channel} using RWA")
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

            if processed_count % 1 == 0:
                print(f"  Processed {processed_count}/{len(compiled_data)} stimuli...")
                if self.use_saved_pc_maps:
                    print(f"    Using saved PC maps: {saved_maps_used}, Computing: {computed_maps}")

            # Check if we have a saved PC map for this stimulus
            pc_map_loaded = False
            if self.use_saved_pc_maps:
                pc_map_file = os.path.join(self.pc_maps_dir, f"pc_map_{stim_id}.npy")
                if os.path.exists(pc_map_file):
                    pc_map_loaded = True

            # Process stimulus to get PC map (try saved first, compute if needed)
            stimulus_pc_map = process_stimulus_for_prediction(
                stim_row,
                self.rwa.shape,
                pc_maps_dir=self.pc_maps_dir,
                nscale=self.nscale,
                norient=self.norient,
                sigma=self.sigma,
                **self.phasecong_kwargs
            )

            if stimulus_pc_map is not None:
                # Track whether we used saved or computed map
                if pc_map_loaded:
                    saved_maps_used += 1
                else:
                    computed_maps += 1
                # Compute similarity metrics
                metrics = self.compute_similarity_metrics(stimulus_pc_map, self.rwa)

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
                del stimulus_pc_map
                gc.collect()

        if len(predictions_data) == 0:
            print("Error: No valid predictions computed!")
            return None

        # Convert to DataFrame
        predictions_df = pd.DataFrame(predictions_data)

        print(f"\nPrediction analysis complete!")
        print(f"Successfully processed: {len(predictions_df)} stimuli")
        if self.use_saved_pc_maps:
            print(f"Efficiency: {saved_maps_used} saved PC maps used, {computed_maps} computed on-the-fly")
            efficiency_pct = (saved_maps_used / (saved_maps_used + computed_maps)) * 100 if (
                                                                                                        saved_maps_used + computed_maps) > 0 else 0
            print(f"Efficiency rate: {efficiency_pct:.1f}% (higher is better)")
        else:
            print(f"All {len(predictions_df)} PC maps computed on-the-fly")

        # Create comprehensive analysis
        self._create_prediction_analysis(predictions_df, channel)

        return {
            'predictions_df': predictions_df,
            'channel': channel,
            'rwa_file': self.rwa_file_path,
            'analysis_params': {
                'nscale': self.nscale,
                'norient': self.norient,
                'sigma': self.sigma
            }
        }

    def _create_prediction_analysis(self, predictions_df, channel):
        """Create comprehensive prediction analysis visualization."""

        # Define prediction metrics to analyze
        prediction_metrics = [
            'dot_product',
            'cosine_similarity',
            'pearson_correlation',
            'strength_weighted',
            'avg_orientation_correlation'
        ]

        # Create figure with subplots
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        axes = axes.flatten()

        # Colors for different lineages
        lineages = predictions_df['Lineage'].unique()
        colors = plt.cm.Set3(np.linspace(0, 1, len(lineages)))
        lineage_colors = dict(zip(lineages, colors))

        # Plot each prediction metric
        for i, metric in enumerate(prediction_metrics):
            ax = axes[i]

            # Plot by lineage
            for lineage in lineages:
                lineage_data = predictions_df[predictions_df['Lineage'] == lineage]
                ax.scatter(lineage_data[metric], lineage_data['ActualResponse'],
                           alpha=0.6, label=f'Lineage {lineage}',
                           color=lineage_colors[lineage], s=20)

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

            if i == 0:  # Only show legend on first plot
                ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

        # Summary statistics plot
        ax = axes[5]
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
                      color=['red' if c < 0 else 'blue' for c in correlations])
        ax.set_xlabel('Prediction Metric')
        ax.set_ylabel('Pearson Correlation with Actual Response')
        ax.set_title('Prediction Performance Summary')
        ax.set_xticks(range(len(metric_names)))
        ax.set_xticklabels(metric_names, rotation=45, ha='right')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)

        # Add correlation values on bars
        for bar, corr in zip(bars, correlations):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height + (0.01 if height >= 0 else -0.03),
                    f'{corr:.3f}', ha='center', va='bottom' if height >= 0 else 'top')

        plt.tight_layout()

        # Save visualization
        output_path = f"rwa_prediction_analysis_{channel}_sigma{self.sigma}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Prediction analysis saved: {output_path}")

        # Save predictions data
        csv_path = f"rwa_predictions_{channel}_sigma{self.sigma}.csv"
        predictions_df.to_csv(csv_path, index=False)
        print(f"Predictions data saved: {csv_path}")

        # Print summary statistics
        print(f"\n=== PREDICTION SUMMARY ===")
        print(f"Best performing metric: {metric_names[np.argmax(correlations)]} (r={max(correlations):.3f})")
        print(f"Worst performing metric: {metric_names[np.argmin(correlations)]} (r={min(correlations):.3f})")
        print(f"\nCorrelations by metric:")
        for metric, corr in zip(metric_names, correlations):
            print(f"  {metric}: r={corr:.3f}")

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
    rwa_file = f"combined_rwa_{session_id}_{channel}.npy"

    # PC maps directory - should match what was used in lineage RWA analysis
    pc_maps_dir = f"/home/r2_allen/Documents/EStimShape/allen_ga_test_250626_0/pc_maps"

    # Check if RWA file exists
    if not os.path.exists(rwa_file):
        print(f"Error: RWA file not found: {rwa_file}")
        print("Please run the lineage RWA analysis first to generate the RWA file.")
        return

    # Initialize analysis
    analyzer = RWAPredictionAnalysis(
        rwa_file_path=rwa_file,
        pc_maps_dir=pc_maps_dir,  # Use saved PC maps for efficiency
        nscale=4,  # Same parameters as used to create RWA
        norient=8,
        sigma=2.0
    )

    # Run analysis
    print(f"Starting RWA prediction analysis for session {session_id}, channel {channel}")
    if analyzer.use_saved_pc_maps:
        print("Using saved PC maps for maximum efficiency!")
    analyzer.run(session_id, "raw", channel, compiled_data=None)

    print("\nAnalysis complete!")
    print("Check the generated visualization and CSV file for detailed results.")


if __name__ == "__main__":
    main()
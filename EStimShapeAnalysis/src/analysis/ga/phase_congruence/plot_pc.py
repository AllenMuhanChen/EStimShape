import pandas as pd
import numpy as np
import os
from matplotlib.image import imread
import matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb

from src.analysis import Analysis
from src.analysis.ga.phase_congruence.calculate_pc_map import calculate_pc_map
from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.repository.import_from_repository import import_from_repository

# Import the phase congruency function we created
from phasepack.phasecong import phasecong


class PlotTopNPCAnalysis(PlotTopNAnalysis):

    def __init__(self, n_top=10,
                 nscale=4, norient=8, **phasecong_kwargs):
        """
        Initialize PlotTopNPCAnalysis

        Args:
            session_id: Session ID for analysis
            response_table: Response table name
            n_top: Number of top stimuli to analyze
            nscale: Number of scales for phase congruency
            norient: Number of orientations for phase congruency
            **phasecong_kwargs: Additional arguments for phase congruency
        """
        super().__init__()
        self.n_top = n_top
        self.nscale = nscale
        self.norient = norient
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
        # Generate phase congruency maps for each top stimulus
        pc_results = {}

        print(f"Analyzing top {self.n_top} stimuli for channel {channel}")
        print(f"Total stimuli in dataset: {len(compiled_data)}")

        # Check required columns
        # if 'GA Response' not in compiled_data.columns:
        #     raise ValueError("GA Response column not found in compiled_data")
        # if 'StimSpecId' not in compiled_data.columns:
        #     raise ValueError("StimSpecId column not found in compiled_data")

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

                # Store results
                pc_results[stim_id] = {
                    'stim_info': stim_row.to_dict(),
                    'image': img,
                    'orientation_stack': orientation_stack,  # XxYxN array
                    'angles': angles,
                    'total_strength': total_strength,
                    'pc_detailed': pc_detailed,
                    'rank': i + 1
                }

            except Exception as e:
                print(f"  Error processing stimulus {stim_id}: {str(e)}")
                continue

        print(f"\nSuccessfully processed {len(pc_results)} stimuli")

        # Generate summary visualization
        self._create_summary_visualization(pc_results, channel)

        return {
            'pc_results': pc_results,
            'top_stimuli_data': top_stimuli,
            'channel': channel,
            'analysis_params': {
                'n_top': self.n_top,
                'nscale': self.nscale,
                'norient': self.norient
            }
        }

    def _create_summary_visualization(self, pc_results, channel):
        """Create summary visualization of all top stimuli PC maps"""

        n_results = len(pc_results)
        if n_results == 0:
            print("No results to visualize")
            return

        # Create figure with subplots
        fig, axes = plt.subplots(3, n_results, figsize=(4 * n_results, 12))
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

            # Orientation visualization (hue = orientation, brightness = strength)
            orientation_vis = self._create_orientation_visualization(
                result['orientation_stack'],
                result['angles'],
                result['total_strength']
            )
            axes[2, i].imshow(orientation_vis)
            axes[2, i].set_title("Orientation Map\n(Hue=Orientation, Brightness=Strength)")
            axes[2, i].axis('off')

        plt.tight_layout()

        # Save the visualization
        output_path = f"top_{self.n_top}_pc_analysis_{channel}_{self.session_id}.png"
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()

        print(f"Summary visualization saved: {output_path}")

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

    def get_pc_map_for_stimulus(self, stim_id, results):
        """
        Get the XxYxN phase congruency map for a specific stimulus

        Args:
            stim_id: Stimulus ID
            results: Results dictionary from analyze()

        Returns:
            orientation_stack: XxYxN array where N is number of orientations
        """
        if stim_id not in results['pc_results']:
            raise ValueError(f"Stimulus {stim_id} not found in results")

        return results['pc_results'][stim_id]['orientation_stack']

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


def main():
    session_id = "250620_0"
    channel = "A-028"

    # Initialize analysis
    analyzer = PlotTopNPCAnalysis(
        n_top=5,  # Analyze top 5 stimuli
        nscale=4,  # 4 scales for phase congruency
        norient=8  # 8 orientations
    )

    # Run analysis
    analyzer.run(session_id, "raw", channel, compiled_data=None)



if __name__ == "__main__":
    main()
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from scipy import stats

from src.analysis.spi_vs_ici.plot_raw_spike_isochrom_vs_isolum_scores import load_data_by_source


# Import the data loading functions from the existing script


def main():
    # Example usage with different data sources
    create_isochrom_isolum_zscore_plots(
        save_path="/home/connorlab/Documents/plots/isochrom_vs_isolum_zscore",
        data_source='raw_validated'
    )


def create_isochrom_isolum_zscore_plots(save_path=None, data_source='raw_validated'):
    """
    Create plots showing isochromatic vs isoluminant z-scores for each frequency.
    Points are colored by 3D significance status.
    Only plots frequencies: 0.5, 1.0, 2.0, 4.0 Hz

    Args:
        save_path: Optional directory path to save plots. If None, plots are only displayed.
        data_source: Which data loading method to use. Options:
            - 'raw_validated': Raw channels validated by both GoodChannels AND ChannelFiltering
            - 'sorted_selective': Sorted units filtered by stimulus selectivity >5%
            - 'raw_clustered': Raw cluster channels from ClusterInfo table
    """

    metric_name = 'z_score'

    # Create save directory if specified
    if save_path is not None:
        os.makedirs(save_path, exist_ok=True)

    # Reuse the existing data loading function
    merged_df = load_data_by_source(data_source, metric_name)

    if merged_df is None or merged_df.empty:
        print(f"No data available for data source: {data_source}")
        return None

    # Get frequencies
    frequencies = [0.5, 1.0, 2.0, 4.0]
    frequencies = [f for f in frequencies if f in merged_df['frequency'].values]

    print(f"\nCreating z-score plots for {len(frequencies)} frequencies: {frequencies}")
    print(f"Total units/channels: {len(merged_df['unit_name'].unique())}")

    # Create plots
    create_combined_frequency_plots(merged_df, frequencies, save_path, data_source)

    return merged_df


def create_combined_frequency_plots(merged_df, frequencies, save_path=None, data_source='raw_validated'):
    """Create combined z-score plots for each frequency."""

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    data_source_labels = {
        'raw_validated': 'Validated raw channels (GoodChannels ∩ ChannelFiltering)',
        'sorted_selective': 'Stimulus-selective sorted units (>5% sig. pairs)',
        'raw_clustered': 'Cluster channels (ClusterInfo)'
    }

    fig.suptitle(
        f'Isochromatic vs Isoluminant Z-Scores by Frequency\n'
        f'({data_source_labels.get(data_source, data_source)})',
        fontsize=16)

    axes = axes.flatten()

    for freq_idx, frequency in enumerate(frequencies):
        ax = axes[freq_idx]
        freq_data = merged_df[merged_df['frequency'] == frequency]

        if freq_data.empty:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{frequency} Hz')
            continue

        x = freq_data['isochromatic_score'].values
        y = freq_data['isoluminant_score'].values
        p_values = freq_data['p_value'].values
        spi_values = freq_data['solid_preference_index'].values

        # Classify: Significant 3D vs others
        sig_3d_mask = (pd.notna(p_values)) & (p_values < 0.05) & (spi_values > 0)

        # Plot significant 3D
        if sig_3d_mask.any():
            ax.scatter(x[sig_3d_mask], y[sig_3d_mask],
                       c='blue', alpha=0.7, s=60, label='Significant 3D (p<0.05)',
                       edgecolors='black', linewidths=0.5)

        # Plot non-significant
        if (~sig_3d_mask).any():
            ax.scatter(x[~sig_3d_mask], y[~sig_3d_mask],
                       c='orange', alpha=0.7, s=60, label='Non-significant 3D',
                       edgecolors='black', linewidths=0.5)

        n_sig_3d = np.sum(sig_3d_mask)
        n_other = np.sum(~sig_3d_mask)

        ax.set_title(f'{frequency} Hz (n={len(freq_data)}, {n_sig_3d} sig. 3D, {n_other} non-sig)')
        ax.set_xlabel('Isochromatic Z-Score')
        ax.set_ylabel('Isoluminant Z-Score')

        # Add diagonal reference line (y=x)
        lims = [
            np.min([ax.get_xlim(), ax.get_ylim()]),
            np.max([ax.get_xlim(), ax.get_ylim()]),
        ]
        ax.plot(lims, lims, 'k--', alpha=0.3, zorder=0, linewidth=1)

        # Add grid
        ax.grid(True, alpha=0.3)

        # Add legend
        ax.legend(loc='lower right', fontsize=9)

    plt.tight_layout()

    if save_path is not None:
        filename = os.path.join(save_path, f'isochrom_vs_isolum_zscore_{data_source}.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Saved: {filename}")

    plt.show()


if __name__ == "__main__":
    main()
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from scipy import stats

from src.analysis.spi_vs_ici.plot_raw_spike_isochrom_vs_isolum_scores import load_data_by_source


def main():
    # Example usage with different data sources
    metric_name = 'z_score'
    # metric_name = 'max_normalized'
    create_isochrom_isolum_zscore_plots(
        save_path="/home/connorlab/Documents/plots/isochrom_vs_isolum_zscore",
        data_source='raw_validated',
        metric_name=metric_name,
    )


def create_isochrom_isolum_zscore_plots(save_path=None, data_source='raw_validated', metric_name='z_score'):
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

    metric_name = metric_name

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

    # Create scatter plots
    create_combined_frequency_plots(merged_df, frequencies, save_path, data_source)

    # Create isoluminant z-score histograms (raw counts)
    create_isoluminant_histograms(merged_df, frequencies, save_path, data_source)

    # Create isoluminant z-score histograms (percentage)
    create_isoluminant_histograms_percentage(merged_df, frequencies, save_path, data_source)

    return merged_df


def create_isoluminant_histograms(merged_df, frequencies, save_path=None, data_source='raw_validated'):
    """
    Create histograms of isoluminant z-scores split by significance groups.

    Args:
        merged_df: DataFrame with z-score and significance data
        frequencies: List of frequencies to plot
        save_path: Optional directory path to save plots
        data_source: Data source identifier for labeling
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    data_source_labels = {
        'raw_validated': 'Validated raw channels (GoodChannels ∩ ChannelFiltering)',
        'sorted_selective': 'Stimulus-selective sorted units (>5% sig. pairs)',
        'raw_clustered': 'Cluster channels (ClusterInfo)'
    }

    fig.suptitle(
        f'Isoluminant Z-Score Distribution by Significance\n'
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

        # Get isoluminant scores and classification
        isolum_scores = freq_data['isoluminant_score'].values
        p_values = freq_data['p_value'].values
        spi_values = freq_data['solid_preference_index'].values

        # Classify: Significant 3D vs Significant 2D vs Non-significant
        sig_3d_mask = (pd.notna(p_values)) & (p_values < 0.05) & (spi_values > 0)
        sig_2d_mask = (pd.notna(p_values)) & (p_values < 0.05) & (spi_values <= 0)
        nonsig_mask = ~(sig_3d_mask | sig_2d_mask)

        sig_3d_values = isolum_scores[sig_3d_mask]
        sig_2d_values = isolum_scores[sig_2d_mask]
        nonsig_values = isolum_scores[nonsig_mask]

        # Determine histogram range
        all_values = isolum_scores[~np.isnan(isolum_scores)]
        if len(all_values) == 0:
            continue

        hist_min = np.floor(np.min(all_values))
        hist_max = np.ceil(np.max(all_values))
        bins = np.linspace(hist_min, hist_max, 15)  # 15 bins

        # Plot overlapping histograms
        if len(sig_3d_values) > 0:
            ax.hist(sig_3d_values, bins=bins, alpha=0.6, color='blue',
                    label=f'Sig 3D (n={len(sig_3d_values)})', edgecolor='black', linewidth=0.5)

        if len(sig_2d_values) > 0:
            ax.hist(sig_2d_values, bins=bins, alpha=0.6, color='red',
                    label=f'Sig 2D (n={len(sig_2d_values)})', edgecolor='black', linewidth=0.5)

        if len(nonsig_values) > 0:
            ax.hist(nonsig_values, bins=bins, alpha=0.4, color='gray',
                    label=f'Non-sig (n={len(nonsig_values)})', edgecolor='black', linewidth=0.5)

        # Styling
        ax.set_xlabel('Isoluminant Z-Score')
        ax.set_ylabel('Number of Cells')
        ax.set_title(f'{frequency} Hz (n={len(freq_data)})')
        ax.axvline(x=0, color='black', linestyle='--', alpha=0.5)
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3, axis='y')

        # Add statistics
        # stats_text = []
        # if len(sig_3d_values) > 0:
        #     stats_text.append(f'Sig 3D: μ={np.mean(sig_3d_values):.2f}, σ={np.std(sig_3d_values):.2f}')
        # if len(sig_2d_values) > 0:
        #     stats_text.append(f'Sig 2D: μ={np.mean(sig_2d_values):.2f}, σ={np.std(sig_2d_values):.2f}')
        # if len(nonsig_values) > 0:
        #     stats_text.append(f'Non-sig: μ={np.mean(nonsig_values):.2f}, σ={np.std(nonsig_values):.2f}')
        #
        # if stats_text:
        #     ax.text(0.02, 0.98, '\n'.join(stats_text), transform=ax.transAxes,
        #             verticalalignment='top', horizontalalignment='left',
        #             bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8),
        #             fontsize=8)

    plt.tight_layout()

    if save_path is not None:
        filename = os.path.join(save_path, f'isoluminant_zscore_histogram_{data_source}.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Saved: {filename}")

    plt.show()


def create_isoluminant_histograms_percentage(merged_df, frequencies, save_path=None, data_source='raw_validated'):
    """
    Create histograms of isoluminant z-scores split by significance groups.
    Shows percentage of cells instead of raw counts.

    Args:
        merged_df: DataFrame with z-score and significance data
        frequencies: List of frequencies to plot
        save_path: Optional directory path to save plots
        data_source: Data source identifier for labeling
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    data_source_labels = {
        'raw_validated': 'Validated raw channels (GoodChannels ∩ ChannelFiltering)',
        'sorted_selective': 'Stimulus-selective sorted units (>5% sig. pairs)',
        'raw_clustered': 'Cluster channels (ClusterInfo)'
    }

    fig.suptitle(
        f'Isoluminant Z-Score Distribution by Significance (Percentage)\n'
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

        # Get isoluminant scores and classification
        isolum_scores = freq_data['isoluminant_score'].values
        p_values = freq_data['p_value'].values
        spi_values = freq_data['solid_preference_index'].values

        # Classify: Significant 3D vs Significant 2D vs Non-significant
        sig_3d_mask = (pd.notna(p_values)) & (p_values < 0.05) & (spi_values > 0)
        sig_2d_mask = (pd.notna(p_values)) & (p_values < 0.05) & (spi_values <= 0)
        nonsig_mask = ~(sig_3d_mask | sig_2d_mask)

        sig_3d_values = isolum_scores[sig_3d_mask]
        sig_2d_values = isolum_scores[sig_2d_mask]
        nonsig_values = isolum_scores[nonsig_mask]

        # Determine histogram range
        all_values = isolum_scores[~np.isnan(isolum_scores)]
        if len(all_values) == 0:
            continue

        hist_min = np.floor(np.min(all_values))
        hist_max = np.ceil(np.max(all_values))
        bins = np.linspace(hist_min, hist_max, 15)

        # Plot overlapping histograms with percentage normalization
        if len(sig_3d_values) > 0:
            weights_3d = np.ones_like(sig_3d_values) * 100.0 / len(sig_3d_values)
            ax.hist(sig_3d_values, bins=bins, weights=weights_3d, alpha=0.6, color='blue',
                    label=f'Sig 3D (n={len(sig_3d_values)})', edgecolor='black', linewidth=0.5)

        if len(sig_2d_values) > 0:
            weights_2d = np.ones_like(sig_2d_values) * 100.0 / len(sig_2d_values)
            ax.hist(sig_2d_values, bins=bins, weights=weights_2d, alpha=0.6, color='red',
                    label=f'Sig 2D (n={len(sig_2d_values)})', edgecolor='black', linewidth=0.5)

        if len(nonsig_values) > 0:
            weights_nonsig = np.ones_like(nonsig_values) * 100.0 / len(nonsig_values)
            ax.hist(nonsig_values, bins=bins, weights=weights_nonsig, alpha=0.4, color='gray',
                    label=f'Non-sig (n={len(nonsig_values)})', edgecolor='black', linewidth=0.5)

        # Styling
        ax.set_xlabel('Isoluminant Z-Score')
        ax.set_ylabel('Percentage of Cells (%)')
        ax.set_title(f'{frequency} Hz (n={len(freq_data)})')
        ax.axvline(x=0, color='black', linestyle='--', alpha=0.5)
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3, axis='y')

        # Add statistics
        stats_text = []
        if len(sig_3d_values) > 0:
            stats_text.append(f'Sig 3D: μ={np.mean(sig_3d_values):.2f}, σ={np.std(sig_3d_values):.2f}')
        if len(sig_2d_values) > 0:
            stats_text.append(f'Sig 2D: μ={np.mean(sig_2d_values):.2f}, σ={np.std(sig_2d_values):.2f}')
        if len(nonsig_values) > 0:
            stats_text.append(f'Non-sig: μ={np.mean(nonsig_values):.2f}, σ={np.std(nonsig_values):.2f}')

        if stats_text:
            ax.text(0.02, 0.98, '\n'.join(stats_text), transform=ax.transAxes,
                    verticalalignment='top', horizontalalignment='left',
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8),
                    fontsize=8)

    plt.tight_layout()

    if save_path is not None:
        filename = os.path.join(save_path, f'isoluminant_zscore_histogram_percentage_{data_source}.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Saved: {filename}")

    plt.show()


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

        # Classify: Significant 3D vs Significant 2D vs Non-significant
        sig_3d_mask = (pd.notna(p_values)) & (p_values < 0.05) & (spi_values > 0)
        sig_2d_mask = (pd.notna(p_values)) & (p_values < 0.05) & (spi_values <= 0)
        nonsig_mask = ~(sig_3d_mask | sig_2d_mask)

        # Plot significant 3D
        if sig_3d_mask.any():
            ax.scatter(x[sig_3d_mask], y[sig_3d_mask],
                       c='blue', alpha=0.7, s=60, label='Significant 3D (p<0.05, SPI>0)',
                       edgecolors='black', linewidths=0.5)

        # Plot significant 2D
        if sig_2d_mask.any():
            ax.scatter(x[sig_2d_mask], y[sig_2d_mask],
                       c='red', alpha=0.7, s=60, label='Significant 2D (p<0.05, SPI≤0)',
                       edgecolors='black', linewidths=0.5)

        # Plot non-significant
        if nonsig_mask.any():
            ax.scatter(x[nonsig_mask], y[nonsig_mask],
                       c='gray', alpha=0.5, s=60, label='Non-significant',
                       edgecolors='black', linewidths=0.5)

        n_sig_3d = np.sum(sig_3d_mask)
        n_sig_2d = np.sum(sig_2d_mask)
        n_nonsig = np.sum(nonsig_mask)

        ax.set_title(f'{frequency} Hz (n={len(freq_data)}, {n_sig_3d} 3D, {n_sig_2d} 2D, {n_nonsig} non-sig)')
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
        ax.legend(loc='lower left', fontsize=9)

    plt.tight_layout()

    if save_path is not None:
        filename = os.path.join(save_path, f'isochrom_vs_isolum_zscore_{data_source}.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Saved: {filename}")

    plt.show()


if __name__ == "__main__":
    main()
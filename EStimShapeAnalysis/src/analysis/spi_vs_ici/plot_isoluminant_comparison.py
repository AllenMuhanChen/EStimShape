import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
from scipy import stats

from clat.util.connection import Connection


def main():
    """Example usage"""
    create_isoluminant_comparison_plots(
        save_path="/home/connorlab/Documents/plots/isoluminant_comparison",
        data_source='raw_validated',
        metric_name='max_normalized',
    )


def create_isoluminant_comparison_plots(save_path=None, data_source='raw_validated', metric_name='max_normalized'):
    """
    Create scatter plots comparing red-green vs cyan-orange isoluminant responses.

    Args:
        save_path: Optional directory path to save plots. If None, plots are only displayed.
        data_source: Which data loading method to use. Options:
            - 'raw_validated': Raw channels validated by both GoodChannels AND ChannelFiltering
            - 'sorted_selective': Sorted units filtered by stimulus selectivity >5%
            - 'raw_clustered': Raw cluster channels from ClusterInfo table
        metric_name: The metric to plot from IsoluminantComparisons table
    """

    # Create save directory if specified
    if save_path is not None:
        os.makedirs(save_path, exist_ok=True)

    # Load data based on selected source
    merged_df = load_data_by_source(data_source, metric_name)

    if merged_df is None or merged_df.empty:
        print(f"No data available for data source: {data_source}")
        return None

    # Get frequencies
    frequencies = [0.5, 1.0, 2.0, 4.0]
    frequencies = [f for f in frequencies if f in merged_df['frequency'].values]

    print(f"\nCreating isoluminant comparison plots for {len(frequencies)} frequencies: {frequencies}")
    print(f"Total units/channels: {len(merged_df['unit'].unique())}")

    # Create plots
    create_combined_frequency_plots(merged_df, frequencies, save_path, data_source, metric_name)

    return merged_df


# ==================== DATA LOADING METHODS ====================

def load_data_by_source(data_source, metric_name):
    """
    Load and merge data based on the specified source.

    Args:
        data_source: String specifying which filtering method to use
        metric_name: The metric name to query from IsoluminantComparisons

    Returns:
        DataFrame with merged comparison and solid preference data
    """
    if data_source == 'raw_validated':
        return load_validated_raw_channels(metric_name)
    elif data_source == 'sorted_selective':
        return load_sorted_selective_units(metric_name)
    elif data_source == 'raw_clustered':
        return load_clustered_raw_channels(metric_name)
    else:
        raise ValueError(f"Unknown data_source: {data_source}. "
                         f"Options: 'raw_validated', 'sorted_selective', 'raw_clustered'")


def load_validated_raw_channels(metric_name):
    """
    Load raw channel data filtered by BOTH GoodChannels AND ChannelFiltering.
    """
    conn = Connection("allen_data_repository")

    # Query isoluminant comparison scores with both filters
    scores_query = """
                   SELECT ic.session_id,
                          ic.unit,
                          ic.frequency,
                          ic.metric_name,
                          ic.red_green,
                          ic.cyan_orange
                   FROM IsoluminantComparisons ic
                            JOIN GoodChannels g ON ic.session_id = g.session_id AND ic.unit = g.channel
                            JOIN ChannelFiltering c ON ic.session_id = c.session_id AND ic.unit = c.channel
                   WHERE ic.metric_name = %s
                     AND ic.frequency IN (0.5, 1.0, 2.0, 4.0) \
                   """

    # Query solid preference with both filters
    solid_query = """
                  SELECT s.session_id, s.unit_name, s.solid_preference_index, s.p_value
                  FROM SolidPreferenceIndices s
                           JOIN GoodChannels g ON s.session_id = g.session_id AND s.unit_name = g.channel
                           JOIN ChannelFiltering c ON s.session_id = c.session_id AND s.unit_name = c.channel \
                  """

    conn.execute(scores_query, params=(metric_name,))
    scores_data = conn.fetch_all()

    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    scores_df = pd.DataFrame(scores_data,
                             columns=['session_id', 'unit', 'frequency', 'metric_name',
                                      'red_green', 'cyan_orange'])
    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])

    # Merge on session_id and unit (scores_df has 'unit', solid_df has 'unit_name')
    merged_df = pd.merge(scores_df, solid_df,
                         left_on=['session_id', 'unit'],
                         right_on=['session_id', 'unit_name'],
                         how='inner')

    print(f"Found {len(merged_df['unit'].unique())} validated raw channels (GoodChannels ∩ ChannelFiltering)")

    return merged_df


def load_sorted_selective_units(metric_name):
    """
    Load sorted unit data filtered by stimulus selectivity.
    Units must have >5% significant pairwise comparisons.
    """
    conn = Connection("allen_data_repository")

    # Get selectivity-filtered units
    selectivity_query = """
                        SELECT session_id,
                               unit_name,
                               n_significant,
                               n_comparisons,
                               (n_significant / n_comparisons) as selectivity_ratio
                        FROM StimulusSelectivity
                        WHERE unit_name LIKE '%Unit%'
                          AND n_comparisons > 0
                          AND n_significant >= 5 * (n_stimuli - 5) \
                        """

    conn.execute(selectivity_query)
    selectivity_data = conn.fetch_all()

    if not selectivity_data:
        print("No units meet the stimulus selectivity threshold (>5% significant pairs)")
        return None

    selectivity_df = pd.DataFrame(selectivity_data,
                                  columns=['session_id', 'unit_name', 'n_significant',
                                           'n_comparisons', 'selectivity_ratio'])

    print(f"Found {len(selectivity_df)} sorted units meeting selectivity threshold (>5% significant pairs)")

    # Query scores (only sorted units)
    scores_query = """
                   SELECT session_id,
                          unit,
                          frequency,
                          metric_name,
                          red_green,
                          cyan_orange
                   FROM IsoluminantComparisons
                   WHERE metric_name = %s
                     AND frequency IN (0.5, 1.0, 2.0, 4.0)
                     AND unit LIKE '%Unit%' \
                   """

    conn.execute(scores_query, params=(metric_name,))
    scores_data = conn.fetch_all()

    scores_df = pd.DataFrame(scores_data,
                             columns=['session_id', 'unit', 'frequency', 'metric_name',
                                      'red_green', 'cyan_orange'])

    # Filter scores to only include selective units
    scores_df = scores_df[scores_df.apply(
        lambda row: any((selectivity_df['session_id'] == row['session_id']) &
                        (selectivity_df['unit_name'] == row['unit'])), axis=1)]

    # Query solid preference indices
    solid_query = """
                  SELECT session_id, unit_name, solid_preference_index, p_value
                  FROM SolidPreferenceIndices
                  WHERE unit_name LIKE '%Unit%' \
                  """

    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])

    # Merge
    merged_df = pd.merge(scores_df, solid_df,
                         left_on=['session_id', 'unit'],
                         right_on=['session_id', 'unit_name'],
                         how='inner')

    print(f"Found {len(merged_df['unit'].unique())} selective sorted units with data")

    return merged_df


def load_clustered_raw_channels(metric_name):
    """
    Load raw channels from ClusterInfo table.
    """
    conn = Connection("allen_data_repository")

    # Get channels from ClusterInfo
    cluster_query = """
                    SELECT DISTINCT e.session_id, ci.channel
                    FROM ClusterInfo ci
                             JOIN Experiments e ON ci.experiment_id = e.experiment_id \
                    """

    conn.execute(cluster_query)
    cluster_data = conn.fetch_all()

    if not cluster_data:
        print("No clustered channels found in ClusterInfo")
        return None

    cluster_df = pd.DataFrame(cluster_data, columns=['session_id', 'channel'])

    print(f"Found {len(cluster_df)} clustered raw channels from ClusterInfo")

    # Query scores
    scores_query = """
                   SELECT session_id,
                          unit,
                          frequency,
                          metric_name,
                          red_green,
                          cyan_orange
                   FROM IsoluminantComparisons
                   WHERE metric_name = %s
                     AND frequency IN (0.5, 1.0, 2.0, 4.0) \
                   """

    conn.execute(scores_query, params=(metric_name,))
    scores_data = conn.fetch_all()

    scores_df = pd.DataFrame(scores_data,
                             columns=['session_id', 'unit', 'frequency', 'metric_name',
                                      'red_green', 'cyan_orange'])

    # Filter to only clustered channels
    scores_df = scores_df[scores_df.apply(
        lambda row: any((cluster_df['session_id'] == row['session_id']) &
                        (cluster_df['channel'] == row['unit'])), axis=1)]

    # Query solid preference
    solid_query = """
                  SELECT session_id, unit_name, solid_preference_index, p_value
                  FROM SolidPreferenceIndices \
                  """

    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])

    # Merge
    merged_df = pd.merge(scores_df, solid_df,
                         left_on=['session_id', 'unit'],
                         right_on=['session_id', 'unit_name'],
                         how='inner')

    print(f"Found {len(merged_df['unit'].unique())} clustered channels with data")

    return merged_df


# ==================== PLOTTING FUNCTIONS ====================

def create_combined_frequency_plots(merged_df, frequencies, save_path=None, data_source='raw_validated',
                                    metric_name='max_normalized'):
    """Create combined plots showing red-green vs cyan-orange for each frequency."""

    # Create 2x2 subplot layout for 4 frequencies
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Update title to include data source
    data_source_labels = {
        'raw_validated': 'Validated raw channels (GoodChannels ∩ ChannelFiltering)',
        'sorted_selective': 'Stimulus-selective sorted units (>5% sig. pairs)',
        'raw_clustered': 'Cluster channels (ClusterInfo)'
    }

    fig.suptitle(
        f'Red-Green vs Cyan-Orange Isoluminant Responses by Frequency\n'
        f'Metric: {metric_name} ({data_source_labels.get(data_source, data_source)})',
        fontsize=16)

    axes = axes.flatten()

    # Plot each frequency
    for freq_idx, frequency in enumerate(frequencies):
        ax = axes[freq_idx]
        freq_data = merged_df[merged_df['frequency'] == frequency]

        if freq_data.empty:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{frequency} cpd')
            continue

        # Extract values
        x = freq_data['red_green'].values
        y = freq_data['cyan_orange'].values
        p_values = freq_data['p_value'].values
        spi_values = freq_data['solid_preference_index'].values

        # Classify points:
        # Significant 3D: p_value < 0.05 AND solid_preference_index > 0
        # Significant 2D: p_value < 0.05 AND solid_preference_index <= 0
        # Non-significant: everything else
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

        ax.set_title(f'{frequency} cpd (n={len(freq_data)}, {n_sig_3d} 3D, {n_sig_2d} 2D, {n_nonsig} non-sig)')
        ax.set_xlabel('Red-Green Response (normalized)')
        ax.set_ylabel('Cyan-Orange Response (normalized)')

        # Add diagonal reference line (y=x)
        lims = [
            np.min([ax.get_xlim(), ax.get_ylim()]),
            np.max([ax.get_xlim(), ax.get_ylim()]),
        ]
        ax.plot(lims, lims, 'k--', alpha=0.3, zorder=0, linewidth=1)

        # Add grid
        ax.grid(True, alpha=0.3)

        # Calculate correlation statistics for each group
        if n_sig_3d > 1:
            r_3d, p_3d = stats.pearsonr(x[sig_3d_mask], y[sig_3d_mask])
            print(f"  {frequency} cpd - Sig 3D correlation: r={r_3d:.3f}, p={p_3d:.3f}")

        if n_sig_2d > 1:
            r_2d, p_2d = stats.pearsonr(x[sig_2d_mask], y[sig_2d_mask])
            print(f"  {frequency} cpd - Sig 2D correlation: r={r_2d:.3f}, p={p_2d:.3f}")

        # Add legend
        ax.legend(loc='upper left', fontsize=9)

    plt.tight_layout()

    # Save if path provided
    if save_path is not None:
        filename = os.path.join(save_path, f'isoluminant_comparison_{metric_name}_{data_source}.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Saved: {filename}")

    plt.show()

    # Print summary statistics
    print(f"\nOverall Statistics for {metric_name} (data_source={data_source}):")
    for frequency in frequencies:
        freq_data = merged_df[merged_df['frequency'] == frequency]
        if not freq_data.empty:
            x = freq_data['red_green'].values
            y = freq_data['cyan_orange'].values
            p_vals = freq_data['p_value'].values
            spi_vals = freq_data['solid_preference_index'].values

            sig_3d_mask = (pd.notna(p_vals)) & (p_vals < 0.05) & (spi_vals > 0)
            sig_2d_mask = (pd.notna(p_vals)) & (p_vals < 0.05) & (spi_vals <= 0)
            n_sig_3d = np.sum(sig_3d_mask)
            n_sig_2d = np.sum(sig_2d_mask)
            n_nonsig = np.sum(~(sig_3d_mask | sig_2d_mask))

            print(f"  {frequency} cpd: n={len(freq_data)} ({n_sig_3d} sig 3D, {n_sig_2d} sig 2D, {n_nonsig} non-sig)")


if __name__ == "__main__":
    main()
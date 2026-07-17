import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os
import json
from scipy import stats
from clat.util.connection import Connection
from src.analysis.spi_vs_ici.spi_vs_ici_windowsorted import get_selectivity_query


def create_all_preference_plots(save_dir=None, threshold=0.7, filter_type='selectivity', spi_regression_max=None,
                                nf_n_bins=4, nf_bin_edges=None):
    """
    Create all three types of preference plots.

    Args:
        save_dir: Directory to save plots. If None, plots are only displayed.
        threshold: Minimum fraction of absolute max response required (default 0.7 = 70%)
        filter_type: Type of filtering to use. Options:
                    - 'selectivity': Uses stimulus selectivity threshold (original)
                    - 'double_filter': Uses GoodChannels AND ChannelFiltering (from spi_vs_ici.py)
                    - 'cluster': Uses cluster channels only via ClusterInfo (from spi_ici_clusters.py)
                    - 'mapped_channel': Cluster channels that are also in ReceptiveFieldInfo
        spi_regression_max: If not None, points with Solid Preference Index above this value
                    are excluded from every regression (they are still plotted).
        nf_n_bins: Number of normalized-frequency (freq / RF radius) quantile bins for Plot 4
                    (used only when nf_bin_edges is None).
        nf_bin_edges: Optional explicit normalized-frequency bin edges for Plot 4, e.g.
                    [0, 0.5, np.inf] for bins [0, 0.5] and [0.5, inf].
    """
    if save_dir is not None:
        os.makedirs(save_dir, exist_ok=True)

    # Get the data using specified filter type
    merged_data = load_and_filter_data(threshold, filter_type=filter_type)

    if merged_data is None:
        print("No data available for plotting")
        return

    if spi_regression_max is not None:
        print(f"Excluding SPI > {spi_regression_max} from all regressions")

    # 1. Preferred frequency only plot
    print("\n" + "=" * 60)
    print("Creating Plot 1: Preferred Frequencies Only")
    print("=" * 60)
    preferred_only_data = merged_data['preferred_only']
    if not preferred_only_data.empty:
        save_path_1 = os.path.join(save_dir, "01_preferred_frequency_only.png") if save_dir else None
        plot_preferred_frequency_only(preferred_only_data, save_path_1, spi_regression_max)
    else:
        print("No data for preferred frequency plot")

    # 2. Combined plot with all strong frequencies
    print("\n" + "=" * 60)
    print("Creating Plot 2: Combined Strong Frequencies")
    print("=" * 60)
    combined_data = merged_data['all_strong']
    if not combined_data.empty:
        save_path_2 = os.path.join(save_dir, "02_combined_strong_frequencies.png") if save_dir else None
        plot_combined_strong_frequencies(combined_data, save_path_2, threshold, spi_regression_max)
    else:
        print("No data for combined plot")

    # 3. Individual plots for each frequency
    print("\n" + "=" * 60)
    print("Creating Plot 3: Individual Frequency Plots")
    print("=" * 60)
    individual_data = merged_data['all_strong']
    if not individual_data.empty:
        plot_individual_frequencies(individual_data, save_dir, threshold, spi_regression_max)
    else:
        print("No data for individual frequency plots")

    # 4. Plots binned by normalized frequency (stimulus frequency / RF radius)
    print("\n" + "=" * 60)
    print("Creating Plot 4: Normalized Frequency (freq / RF radius) Bins")
    print("=" * 60)
    normfreq_data = merged_data['all_strong']
    if not normfreq_data.empty:
        save_path_4 = os.path.join(save_dir, "04_combined_normalized_frequency.png") if save_dir else None
        plot_combined_normalized_frequency(normfreq_data, save_path_4, threshold, spi_regression_max,
                                           nf_n_bins, nf_bin_edges)
        plot_normalized_frequency_bins(normfreq_data, save_dir, threshold, spi_regression_max,
                                       nf_n_bins, nf_bin_edges)
    else:
        print("No data for normalized frequency plots")

    plt.show()


def load_and_filter_data(threshold=0.7, filter_type='selectivity'):
    """
    Load and filter all necessary data from database.

    Args:
        threshold: Minimum fraction of absolute max response required
        filter_type: Type of filtering to use ('selectivity' or 'double_filter')

    Returns:
        Dictionary with 'preferred_only' and 'all_strong' DataFrames
    """
    if filter_type == 'selectivity':
        return load_data_with_selectivity_filter(threshold)
    elif filter_type == 'double_filter':
        return load_data_with_double_filter(threshold)
    elif filter_type == 'cluster':
        return load_data_with_cluster_filter(threshold)
    elif filter_type == 'mapped_channel':
        return load_data_with_mapped_channel_filter(threshold)
    else:
        raise ValueError(f"Unknown filter_type: {filter_type}. "
                         f"Use 'selectivity', 'double_filter', 'cluster', or 'mapped_channel'")


def load_data_with_selectivity_filter(threshold=0.7):
    """
    Original data loading approach: Uses stimulus selectivity threshold.

    Returns:
        Dictionary with 'preferred_only' and 'all_strong' DataFrames
    """
    conn = Connection("allen_data_repository")

    # Get units that pass stimulus selectivity threshold
    conn.execute(get_selectivity_query())
    selectivity_data = conn.fetch_all()

    if not selectivity_data:
        print("No units meet the stimulus selectivity threshold (>5% significant pairs)")
        return None

    selectivity_df = pd.DataFrame(selectivity_data,
                                  columns=['session_id', 'unit_name', 'n_significant',
                                           'n_comparisons', 'selectivity_ratio'])

    print(f"Found {len(selectivity_df)} units meeting selectivity threshold")

    # Get preferred frequencies
    preferred_freq_query = """
                           SELECT session_id, unit_name, preferred_frequency, all_freq_responses
                           FROM PreferredFrequencies
                           WHERE unit_name LIKE '%Unit%'
                           """

    conn.execute(preferred_freq_query)
    preferred_freq_data = conn.fetch_all()

    if not preferred_freq_data:
        print("No preferred frequency data found")
        return None

    preferred_freq_df = pd.DataFrame(preferred_freq_data,
                                     columns=['session_id', 'unit_name', 'preferred_frequency',
                                              'all_freq_responses'])

    # Parse JSON and identify strong frequencies
    preferred_freq_df['strong_frequencies'] = preferred_freq_df.apply(
        lambda row: parse_strong_frequencies(row, threshold), axis=1
    )

    # Get solid preference indices
    solid_query = """
                  SELECT session_id, unit_name, solid_preference_index, p_value
                  FROM SolidPreferenceIndices
                  WHERE unit_name LIKE '%Unit%'
                  """

    conn.execute(solid_query)
    solid_data = conn.fetch_all()
    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])

    # Get isochromatic preference indices
    isochromatic_query = """
                         SELECT session_id, unit_name, frequency, isochromatic_preference_index
                         FROM IsochromaticPreferenceIndices
                         WHERE unit_name LIKE '%Unit%'
                         """

    conn.execute(isochromatic_query)
    isochromatic_data = conn.fetch_all()
    isochromatic_df = pd.DataFrame(isochromatic_data,
                                   columns=['session_id', 'unit_name', 'frequency',
                                            'isochromatic_preference_index'])

    # Merge base data
    base_df = solid_df.merge(
        selectivity_df[['session_id', 'unit_name', 'selectivity_ratio']],
        on=['session_id', 'unit_name'], how='inner'
    )

    base_df = base_df.merge(
        preferred_freq_df[['session_id', 'unit_name', 'preferred_frequency', 'strong_frequencies']],
        on=['session_id', 'unit_name'], how='inner'
    )

    base_df = base_df.merge(
        isochromatic_df,
        on=['session_id', 'unit_name'], how='inner'
    )

    return process_frequency_data(base_df)


def load_data_with_double_filter(threshold=0.7):
    """
    Alternative data loading approach: Uses double filtering with GoodChannels AND ChannelFiltering.
    This matches the filtering logic from spi_vs_ici.py.

    Returns:
        Dictionary with 'preferred_only' and 'all_strong' DataFrames
    """
    conn = Connection("allen_data_repository")

    print("Using double filter: GoodChannels AND ChannelFiltering (is_good=TRUE)")

    # Get preferred frequencies
    preferred_freq_query = """
                           SELECT session_id, unit_name, preferred_frequency, all_freq_responses
                           FROM PreferredFrequencies
                           WHERE unit_name NOT LIKE '%Unit%'
                           """

    conn.execute(preferred_freq_query)
    preferred_freq_data = conn.fetch_all()

    if not preferred_freq_data:
        print("No preferred frequency data found")
        return None

    preferred_freq_df = pd.DataFrame(preferred_freq_data,
                                     columns=['session_id', 'unit_name', 'preferred_frequency',
                                              'all_freq_responses'])

    # Parse JSON and identify strong frequencies
    preferred_freq_df['strong_frequencies'] = preferred_freq_df.apply(
        lambda row: parse_strong_frequencies(row, threshold), axis=1
    )

    # Get solid preference indices with double filtering
    solid_query = """
                  SELECT s.session_id, s.unit_name, s.solid_preference_index, s.p_value
                  FROM SolidPreferenceIndices s
                           JOIN GoodChannels g ON s.session_id = g.session_id AND s.unit_name = g.channel
                           JOIN ChannelFiltering c ON s.session_id = c.session_id AND s.unit_name = c.channel
                  WHERE c.is_good = TRUE
                  """

    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    if not solid_data:
        print("No solid preference data found with double filtering")
        return None

    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])

    print(f"Found {len(solid_df)} units passing double filter (GoodChannels + ChannelFiltering)")

    # Get isochromatic preference indices with double filtering
    isochromatic_query = """
                         SELECT i.session_id, i.unit_name, i.frequency, i.isochromatic_preference_index
                         FROM IsochromaticPreferenceIndices i
                                  JOIN GoodChannels g ON i.session_id = g.session_id AND i.unit_name = g.channel
                                  JOIN ChannelFiltering c ON i.session_id = c.session_id AND i.unit_name = c.channel
                         WHERE c.is_good = TRUE
                         """

    conn.execute(isochromatic_query)
    isochromatic_data = conn.fetch_all()
    isochromatic_df = pd.DataFrame(isochromatic_data,
                                   columns=['session_id', 'unit_name', 'frequency',
                                            'isochromatic_preference_index'])

    # Merge base data
    base_df = solid_df.merge(
        preferred_freq_df[['session_id', 'unit_name', 'preferred_frequency', 'strong_frequencies']],
        on=['session_id', 'unit_name'], how='inner'
    )

    base_df = base_df.merge(
        isochromatic_df,
        on=['session_id', 'unit_name'], how='inner'
    )

    return process_frequency_data(base_df)


def load_data_with_cluster_filter(threshold=0.7):
    """
    Cluster-based data loading: selects only cluster channels, using exactly the
    same stimulus/channel selection as spi_ici_clusters.py (JOIN SolidPreferenceIndices /
    IsochromaticPreferenceIndices with Experiments and ClusterInfo on
    e.experiment_id = c.experiment_id AND unit_name = c.channel).

    Returns:
        Dictionary with 'preferred_only' and 'all_strong' DataFrames
    """
    return load_cluster_based_data(threshold, require_receptive_field=False)


def load_data_with_mapped_channel_filter(threshold=0.7):
    """
    Mapped-channel data loading: selects channels that are BOTH cluster channels
    (as in spi_ici_clusters.py) AND have a receptive field mapped for that session,
    i.e. an entry in ReceptiveFieldInfo for the same (session_id, channel).

    Returns:
        Dictionary with 'preferred_only' and 'all_strong' DataFrames
    """
    return load_cluster_based_data(threshold, require_receptive_field=True)


def load_cluster_based_data(threshold=0.7, require_receptive_field=False):
    """
    Shared loader for cluster-based channel selection.

    Selects cluster channels (JOIN Experiments + ClusterInfo, matching
    spi_ici_clusters.py). Only ClusterInfo rows whose experiment_id ends in
    'isogabor' (e.g. 260617_0_isogabor) are considered. When
    require_receptive_field is True, additionally requires the channel to have
    an entry in ReceptiveFieldInfo for that session_id (mapped_channel mode).

    Args:
        threshold: Minimum fraction of absolute max response required.
        require_receptive_field: If True, also require a ReceptiveFieldInfo entry.

    Returns:
        Dictionary with 'preferred_only' and 'all_strong' DataFrames
    """
    conn = Connection("allen_data_repository")

    if require_receptive_field:
        print("Using mapped_channel filter: ClusterInfo cluster channels that are also in ReceptiveFieldInfo")
    else:
        print("Using cluster filter: ClusterInfo cluster channels (matches spi_ici_clusters.py)")

    # Optional join requiring the channel to also be in ReceptiveFieldInfo for that session.
    def rf_join(alias):
        if not require_receptive_field:
            return ""
        return (f"\n                           JOIN ReceptiveFieldInfo r "
                f"ON r.session_id = {alias}.session_id AND r.channel = {alias}.unit_name")

    # Get solid preference indices for cluster channels only (matches spi_ici_clusters.py)
    solid_query = f"""
                  SELECT s.session_id, s.unit_name, s.solid_preference_index, s.p_value
                  FROM SolidPreferenceIndices s
                           JOIN Experiments e ON s.session_id = e.session_id
                           JOIN ClusterInfo c ON e.experiment_id = c.experiment_id AND s.unit_name = c.channel{rf_join('s')}
                  WHERE c.experiment_id LIKE '%isogabor' AND c.gen_id=1
                  """

    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    if not solid_data:
        print("No solid preference data found for selected channels")
        return None

    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])
    solid_df = solid_df.drop_duplicates(['session_id', 'unit_name'])

    print(f"Found {len(solid_df)} units (SolidPreferenceIndices)")

    # Get isochromatic preference indices for cluster channels only (matches spi_ici_clusters.py)
    isochromatic_query = f"""
                         SELECT i.session_id, i.unit_name, i.frequency, i.isochromatic_preference_index
                         FROM IsochromaticPreferenceIndices i
                                  JOIN Experiments e ON i.session_id = e.session_id
                                  JOIN ClusterInfo c ON e.experiment_id = c.experiment_id AND i.unit_name = c.channel{rf_join('i')}
                         WHERE c.experiment_id LIKE '%isogabor'
                         """

    conn.execute(isochromatic_query)
    isochromatic_data = conn.fetch_all()
    isochromatic_df = pd.DataFrame(isochromatic_data,
                                   columns=['session_id', 'unit_name', 'frequency',
                                            'isochromatic_preference_index'])
    isochromatic_df = isochromatic_df.drop_duplicates(['session_id', 'unit_name', 'frequency'])

    # Get preferred frequencies (restricted to selected channels via the inner merge below)
    preferred_freq_query = """
                           SELECT session_id, unit_name, preferred_frequency, all_freq_responses
                           FROM PreferredFrequencies
                           """

    conn.execute(preferred_freq_query)
    preferred_freq_data = conn.fetch_all()

    if not preferred_freq_data:
        print("No preferred frequency data found")
        return None

    preferred_freq_df = pd.DataFrame(preferred_freq_data,
                                     columns=['session_id', 'unit_name', 'preferred_frequency',
                                              'all_freq_responses'])

    # Parse JSON and identify strong frequencies
    preferred_freq_df['strong_frequencies'] = preferred_freq_df.apply(
        lambda row: parse_strong_frequencies(row, threshold), axis=1
    )

    # Merge base data (inner merges keep only selected channels with matching data)
    base_df = solid_df.merge(
        preferred_freq_df[['session_id', 'unit_name', 'preferred_frequency', 'strong_frequencies']],
        on=['session_id', 'unit_name'], how='inner'
    )

    base_df = base_df.merge(
        isochromatic_df,
        on=['session_id', 'unit_name'], how='inner'
    )

    return process_frequency_data(base_df)


# Regression categories based on solid-preference significance and direction.
# A point is "significantly 2D" if its solid preference is significant (p < 0.05)
# and negative, "significantly 3D" if significant and positive, otherwise "non-significant".
REGRESSION_CATEGORIES = [
    ('Sig. 2D', 'tab:green'),
    ('Non-sig.', 'tab:gray'),
    ('Sig. 3D', 'tab:red'),
]


def categorize_points(spi_values, p_values):
    """Categorize each point as significantly 2D, non-significant, or significantly 3D.

    Args:
        spi_values: Array of solid preference indices.
        p_values: Array of solid-preference p-values.

    Returns:
        Object array of category labels matching REGRESSION_CATEGORIES.
    """
    spi_values = np.asarray(spi_values)
    p_values = np.asarray(p_values)
    categories = np.empty(len(spi_values), dtype=object)
    for i in range(len(spi_values)):
        if pd.notna(p_values[i]) and p_values[i] < 0.05:
            categories[i] = 'Sig. 2D' if spi_values[i] < 0 else 'Sig. 3D'
        else:
            categories[i] = 'Non-sig.'
    return categories


def linregress_with_spi_cap(x, y, spi_regression_max=None):
    """Linear regression that optionally excludes points with SPI above a cap.

    Points with x (Solid Preference Index) greater than spi_regression_max are excluded
    from the fit only; callers are expected to still plot all points.

    Args:
        x, y: Data arrays (x is the Solid Preference Index).
        spi_regression_max: If not None, exclude points with x > this value from the fit.

    Returns:
        slope, intercept, r_value, p_value, r_squared, x_used
        where x_used is the x array actually used for the regression.
    """
    x = np.asarray(x)
    y = np.asarray(y)
    if spi_regression_max is not None:
        mask = x <= spi_regression_max
        x = x[mask]
        y = y[mask]
    if len(x) > 1:
        slope, intercept, r_value, p_value, _ = stats.linregress(x, y)
        return slope, intercept, r_value, p_value, r_value ** 2, x
    return 0.0, 0.0, 0.0, 0.0, 0.0, x


def plot_category_regressions(ax, x, y, p_values, linestyle='-', linewidth=2.5, spi_regression_max=None):
    """Plot separate regression lines for sig-2D, non-sig, and sig-3D point categories.

    Each line spans only the x-range of the points in its category. When
    spi_regression_max is set, points with SPI above the cap are excluded from each fit.

    Args:
        ax: Matplotlib axis to draw on.
        x: Array of solid preference indices.
        y: Array of isochromatic preference indices.
        p_values: Array of solid-preference p-values.
        linestyle: Line style for the regression lines.
        linewidth: Line width for the regression lines.
        spi_regression_max: If not None, exclude points with SPI > this value from each fit.

    Returns:
        Dict mapping category label -> (r_value, p_value, n) where n is the number of
        points actually used in the fit.
    """
    x = np.asarray(x)
    y = np.asarray(y)
    categories = categorize_points(x, p_values)
    results = {}
    for label, color in REGRESSION_CATEGORIES:
        mask = categories == label
        x_cat = x[mask]
        y_cat = y[mask]
        slope, intercept, r_value, p_val, r_squared, x_used = linregress_with_spi_cap(
            x_cat, y_cat, spi_regression_max)
        n = len(x_used)
        if n > 1:
            x_line = np.linspace(x_used.min(), x_used.max(), 100)
            line_y = slope * x_line + intercept
            ax.plot(x_line, line_y, color=color, linestyle=linestyle, linewidth=linewidth,
                    label=f'{label} (R²={r_squared:.2f}, n={n})')
            results[label] = (r_value, p_val, n)
        else:
            results[label] = (np.nan, np.nan, n)
    return results


def print_category_regressions(results):
    """Print regression statistics for each significance category."""
    for label, _ in REGRESSION_CATEGORIES:
        r_value, p_val, n = results[label]
        if n > 1:
            print(f"    {label}: n={n}, r={r_value:.3f}, p={p_val:.3f}")
        else:
            print(f"    {label}: n={n} (too few points for regression)")


def parse_strong_frequencies(row, threshold):
    """
    Parse JSON frequency responses and identify frequencies >= threshold of max.

    Args:
        row: DataFrame row with 'all_freq_responses' column
        threshold: Minimum fraction of absolute max response required

    Returns:
        List of frequencies meeting threshold
    """
    try:
        all_freqs = json.loads(row['all_freq_responses'])
        absolute_max = max(all_freqs.values())

        # Get all frequencies >= threshold
        strong_freqs = [float(freq) for freq, response in all_freqs.items()
                        if response >= threshold * absolute_max]

        return strong_freqs
    except Exception as e:
        print(f"Error parsing frequencies: {e}")
        return []


def merge_receptive_field_radius(base_df):
    """Left-merge receptive field radius (from ReceptiveFieldInfo) onto the data.

    Adds an 'rf_radius' column matched on (session_id, unit_name). If a channel has no
    direct ReceptiveFieldInfo entry, it falls back to the radius of another channel in the
    same cluster (same experiment_id + cluster_id in ClusterInfo) that does have RF info.
    Channels with neither direct nor cluster RF info get NaN, so callers can warn / skip.

    Args:
        base_df: Merged dataframe with 'session_id' and 'unit_name' columns.

    Returns:
        base_df with an added 'rf_radius' column.
    """
    conn = Connection("allen_data_repository")
    conn.execute("SELECT session_id, channel, radius FROM ReceptiveFieldInfo")
    rf_data = conn.fetch_all()

    if not rf_data:
        print("WARNING: No ReceptiveFieldInfo rows found; rf_radius will be NaN for all points")
        base_df = base_df.copy()
        base_df['rf_radius'] = np.nan
        return base_df

    rf_df = pd.DataFrame(rf_data, columns=['session_id', 'unit_name', 'rf_radius'])
    rf_df['rf_radius'] = pd.to_numeric(rf_df['rf_radius'], errors='coerce')
    rf_df = rf_df.dropna(subset=['rf_radius']).drop_duplicates(['session_id', 'unit_name'])

    # Direct match: radius for the channel itself
    merged = base_df.merge(rf_df, on=['session_id', 'unit_name'], how='left')

    # Cluster fallback: for channels lacking a direct radius, borrow from a clustermate.
    conn.execute(
        """
        SELECT e.session_id, c.experiment_id, c.cluster_id, c.channel
        FROM ClusterInfo c
                 JOIN Experiments e ON e.experiment_id = c.experiment_id
        """
    )
    cluster_data = conn.fetch_all()

    if not cluster_data:
        print("WARNING: No ClusterInfo rows found; cluster fallback for RF radius unavailable")
        return merged

    cluster_df = pd.DataFrame(cluster_data,
                              columns=['session_id', 'experiment_id', 'cluster_id', 'unit_name'])
    cluster_df = cluster_df.drop_duplicates(['session_id', 'experiment_id', 'cluster_id', 'unit_name'])

    # Mean radius of cluster members that have direct RF info
    cluster_rf = cluster_df.merge(rf_df, on=['session_id', 'unit_name'], how='inner')
    cluster_radius = (cluster_rf
                      .groupby(['session_id', 'experiment_id', 'cluster_id'])['rf_radius']
                      .mean().reset_index())

    # Radius available to each channel via its cluster(s)
    channel_cluster_radius = cluster_df.merge(
        cluster_radius, on=['session_id', 'experiment_id', 'cluster_id'], how='inner')
    channel_cluster_radius = (channel_cluster_radius
                              .groupby(['session_id', 'unit_name'])['rf_radius']
                              .mean().reset_index()
                              .rename(columns={'rf_radius': 'cluster_rf_radius'}))

    merged = merged.merge(channel_cluster_radius, on=['session_id', 'unit_name'], how='left')

    fallback_mask = merged['rf_radius'].isna() & merged['cluster_rf_radius'].notna()
    n_filled = int(fallback_mask.sum())
    merged.loc[fallback_mask, 'rf_radius'] = merged.loc[fallback_mask, 'cluster_rf_radius']
    merged = merged.drop(columns=['cluster_rf_radius'])

    if n_filled > 0:
        print(f"Filled RF radius for {n_filled} data point(s) via cluster fallback "
              f"(channel lacked direct RF info but a clustermate had it)")

    return merged


def process_frequency_data(base_df):
    """
    Process merged dataframe to create preferred_only and all_strong datasets.

    Args:
        base_df: Merged dataframe with all required columns

    Returns:
        Dictionary with 'preferred_only' and 'all_strong' DataFrames
    """
    if base_df.empty:
        print("No data after merging")
        return None

    # Filter to allowed frequencies
    allowed_frequencies = [0.5, 1.0, 2.0, 4.0]
    base_df = base_df[base_df['frequency'].isin(allowed_frequencies)]

    # Attach receptive field radius (NaN where the channel has no RF info)
    base_df = merge_receptive_field_radius(base_df)

    # Create dataset 1: Preferred frequency only
    preferred_only = base_df[base_df['frequency'] == base_df['preferred_frequency']].copy()

    # Create dataset 2: All strong frequencies
    def is_strong_freq(row):
        return float(row['frequency']) in row['strong_frequencies']

    all_strong = base_df[base_df.apply(is_strong_freq, axis=1)].copy()

    print(f"\nData processing complete:")
    print(f"  Preferred frequency only: {len(preferred_only)} data points")
    print(f"  All strong frequencies: {len(all_strong)} data points")

    return {
        'preferred_only': preferred_only,
        'all_strong': all_strong
    }


def plot_preferred_frequency_only(data, save_path=None, spi_regression_max=None):
    """Plot 1: Only the preferred frequency for each unit."""

    x = data['solid_preference_index'].values
    y = data['isochromatic_preference_index'].values
    p_values = data['p_value'].values
    frequencies = data['preferred_frequency'].values

    # Overall regression (used for the stats text box; optionally excludes high-SPI points)
    slope, intercept, r_value, p_value, r_squared, _ = linregress_with_spi_cap(x, y, spi_regression_max)

    # Create plot
    plt.figure(figsize=(12, 10))

    # Color map for frequencies
    all_freqs = sorted(data['preferred_frequency'].unique())
    freq_cmap = plt.cm.viridis
    freq_colors = {freq: freq_cmap(i / (len(all_freqs) - 1)) for i, freq in enumerate(all_freqs)}

    # Plot points
    for i in range(len(x)):
        freq = frequencies[i]
        color = freq_colors[freq]

        if pd.notna(p_values[i]) and p_values[i] < 0.05:
            alpha_val = 0.7
            edge_color = 'black'
            linewidth = 0.5
        else:
            alpha_val = 0.15
            edge_color = 'gray'
            linewidth = 0.3

        plt.scatter(x[i], y[i], alpha=alpha_val, s=100,
                    color=color, marker='o',
                    edgecolors=edge_color, linewidths=linewidth)

    # Separate regression lines for sig-2D, non-sig, and sig-3D categories
    category_results = plot_category_regressions(plt.gca(), x, y, p_values,
                                                 spi_regression_max=spi_regression_max)

    # Create legend for frequencies (points) plus the category regression lines
    from matplotlib.patches import Patch
    freq_legend_elements = [Patch(facecolor=freq_colors[freq], label=f'{freq} Hz')
                            for freq in all_freqs]
    line_handles, line_labels = plt.gca().get_legend_handles_labels()
    first_legend = plt.legend(handles=line_handles, labels=line_labels,
                              bbox_to_anchor=(1.05, 1), loc='upper left', title='Regression')
    plt.gca().add_artist(first_legend)
    plt.legend(handles=freq_legend_elements, bbox_to_anchor=(1.05, 0.6), loc='upper left',
               title='Preferred Frequency')

    # Formatting
    n_significant = np.sum((pd.notna(p_values)) & (p_values < 0.05))
    plt.xlabel('Solid Preference Index', fontsize=14)
    plt.ylabel('Isochromatic Preference Index', fontsize=14)
    plt.title(
        f'Solid vs Isochromatic Preference at Preferred Frequency\n'
        f'(n={len(data)} units, {n_significant} solid-pref significant)',
        fontsize=16)

    add_plot_formatting(plt.gca(), r_squared, r_value, p_value, len(data), n_significant)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {save_path}")

    print(f"\nPreferred Frequency Statistics:")
    print(f"  Total units: {len(data)}")
    print(f"  Significant: {n_significant}")
    print(f"  Overall: R² = {r_squared:.3f}, r = {r_value:.3f}, p = {p_value:.3f}")
    print(f"  By significance category:")
    print_category_regressions(category_results)


def plot_combined_strong_frequencies(data, save_path=None, threshold=0.7, spi_regression_max=None):
    """Plot 2: Combined plot with all strong frequencies and separate trend lines."""

    x = data['solid_preference_index'].values
    y = data['isochromatic_preference_index'].values
    p_values = data['p_value'].values
    frequencies = data['frequency'].values

    # Overall regression (optionally excludes high-SPI points)
    slope_all, intercept_all, r_value_all, p_value_all, r_squared_all, _ = linregress_with_spi_cap(
        x, y, spi_regression_max)

    # Create plot
    plt.figure(figsize=(12, 10))

    # Color map
    all_freqs = [0.5, 1.0, 2.0, 4.0]
    freq_cmap = plt.cm.viridis
    freq_colors = {freq: freq_cmap(i / 3) for i, freq in enumerate(all_freqs)}

    # Plot points
    for i in range(len(x)):
        freq = frequencies[i]
        color = freq_colors[freq]

        if pd.notna(p_values[i]) and p_values[i] < 0.05:
            alpha_val = 0.7
            edge_color = 'black'
            linewidth = 0.5
        else:
            alpha_val = 0.15
            edge_color = 'gray'
            linewidth = 0.3

        plt.scatter(x[i], y[i], alpha=alpha_val, s=100,
                    color=color, marker='o',
                    edgecolors=edge_color, linewidths=linewidth)

    # Plot trend lines for each frequency (over the range used for each fit)
    for freq in all_freqs:
        freq_data = data[data['frequency'] == freq]
        if len(freq_data) > 1:
            x_freq = freq_data['solid_preference_index'].values
            y_freq = freq_data['isochromatic_preference_index'].values

            slope, intercept, r_value, p_val, r_squared, x_used = linregress_with_spi_cap(
                x_freq, y_freq, spi_regression_max)

            if len(x_used) > 1:
                line_x = np.linspace(x_used.min(), x_used.max(), 100)
                line_y = slope * line_x + intercept
                plt.plot(line_x, line_y, linewidth=2, color=freq_colors[freq],
                         linestyle='--', alpha=0.8,
                         label=f'{freq} Hz (R²={r_squared:.2f}, n={len(x_used)})')

    # Separate regression lines for sig-2D, non-sig, and sig-3D categories
    # (replaces the single overall trend line)
    category_results = plot_category_regressions(plt.gca(), x, y, p_values, linestyle='-', linewidth=3,
                                                 spi_regression_max=spi_regression_max)

    # Formatting
    n_significant = np.sum((pd.notna(p_values)) & (p_values < 0.05))
    plt.xlabel('Solid Preference Index', fontsize=14)
    plt.ylabel('Isochromatic Preference Index', fontsize=14)
    plt.title(
        f'Solid vs Isochromatic Preference at Strong Frequencies (≥{threshold * 100:.0f}% of max)\n'
        f'(n={len(data)} data points, {n_significant} solid-pref significant)',
        fontsize=16)

    add_plot_formatting(plt.gca(), r_squared_all, r_value_all, p_value_all, len(data), n_significant)

    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title='Frequency')
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {save_path}")

    # Print statistics
    print(f"\nCombined Strong Frequencies Statistics:")
    print(f"  Total data points: {len(data)}")
    print(f"  Significant: {n_significant}")
    print(f"  Overall: R² = {r_squared_all:.3f}, r = {r_value_all:.3f}, p = {p_value_all:.3f}")
    print(f"  By significance category:")
    print_category_regressions(category_results)

    for freq in all_freqs:
        freq_data = data[data['frequency'] == freq]
        if not freq_data.empty:
            n_sig = np.sum((pd.notna(freq_data['p_value'])) & (freq_data['p_value'] < 0.05))
            x_f = freq_data['solid_preference_index'].values
            y_f = freq_data['isochromatic_preference_index'].values
            _, _, r_val, p_val, _, x_used = linregress_with_spi_cap(x_f, y_f, spi_regression_max)
            if len(x_used) > 1:
                print(f"    {freq} Hz: n={len(freq_data)} ({n_sig} sig.), r={r_val:.3f}, p={p_val:.3f}")


def plot_individual_frequencies(data, save_dir=None, threshold=0.7, spi_regression_max=None):
    """Plot 3: Individual plots for each frequency."""

    allowed_frequencies = [0.5, 1.0, 2.0, 4.0]

    # Color map
    freq_cmap = plt.cm.viridis
    freq_colors = {freq: freq_cmap(i / 3) for i, freq in enumerate(allowed_frequencies)}

    for freq in allowed_frequencies:
        freq_data = data[data['frequency'] == freq]

        if freq_data.empty:
            print(f"No data for {freq} Hz")
            continue

        x = freq_data['solid_preference_index'].values
        y = freq_data['isochromatic_preference_index'].values
        p_values = freq_data['p_value'].values

        # Calculate regression (optionally excludes high-SPI points)
        slope, intercept, r_value, p_value, r_squared, x_reg = linregress_with_spi_cap(
            x, y, spi_regression_max)

        # Create plot
        plt.figure(figsize=(10, 8))

        color = freq_colors[freq]

        # Plot points
        for i in range(len(x)):
            if pd.notna(p_values[i]) and p_values[i] < 0.05:
                alpha_val = 0.7
                edge_color = 'black'
                linewidth = 0.5
            else:
                alpha_val = 0.15
                edge_color = 'gray'
                linewidth = 0.3

            plt.scatter(x[i], y[i], alpha=alpha_val, s=100,
                        color=color, marker='o',
                        edgecolors=edge_color, linewidths=linewidth)

        # Separate regression lines for sig-2D, non-sig, and sig-3D categories
        category_results = plot_category_regressions(plt.gca(), x, y, p_values,
                                                     spi_regression_max=spi_regression_max)

        # Formatting
        n_significant = np.sum((pd.notna(p_values)) & (p_values < 0.05))
        plt.xlabel('Solid Preference Index', fontsize=14)
        plt.ylabel('Isochromatic Preference Index', fontsize=14)
        plt.title(
            f'Solid vs Isochromatic Preference at {freq} Hz (≥{threshold * 100:.0f}% of max)\n'
            f'(n={len(freq_data)} data points, {n_significant} solid-pref significant)',
            fontsize=16)

        add_plot_formatting(plt.gca(), r_squared, r_value, p_value, len(freq_data), n_significant)

        if plt.gca().get_legend_handles_labels()[0]:
            plt.legend(loc='upper left', title='Regression')

        plt.tight_layout()

        if save_dir:
            save_path = os.path.join(save_dir, f"03_individual_{freq}Hz.png")
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved: {save_path}")

        print(f"\n{freq} Hz Statistics:")
        print(f"  Data points: {len(freq_data)}")
        print(f"  Significant: {n_significant}")
        if len(x_reg) > 1:
            print(f"  Overall: R² = {r_squared:.3f}, r = {r_value:.3f}, p = {p_value:.3f}")
        print(f"  By significance category:")
        print_category_regressions(category_results)


def compute_normalized_frequency_bins(data, n_bins=4, bin_edges=None):
    """Compute normalized-frequency (stimulus frequency / RF radius) bins.

    Skips points lacking a valid RF radius (NaN or <= 0), printing a warning.

    Args:
        data: DataFrame with 'frequency' and 'rf_radius' columns.
        n_bins: Number of quantile bins (used only when bin_edges is None).
        bin_edges: Optional explicit bin edges, e.g. [0, 0.5, np.inf] for bins
            [0, 0.5] and [0.5, inf]. When provided, these fixed edges are used
            (via pd.cut) instead of quantile bins.

    Returns:
        (data_with_bins, bins, n_missing) where data_with_bins has added
        'normalized_frequency' and 'nf_bin' columns, bins is the list of interval
        categories, and n_missing is the number of skipped points. Returns None if
        the data cannot be binned.
    """
    data = data.copy()

    if 'rf_radius' not in data.columns:
        print("WARNING: No rf_radius column found; cannot create normalized-frequency plots")
        return None

    valid = data['rf_radius'].notna() & (data['rf_radius'] > 0)
    n_missing = int((~valid).sum())
    if n_missing > 0:
        print(f"WARNING: {n_missing} of {len(data)} data points lack a valid ReceptiveFieldInfo "
              f"radius and are skipped in the normalized-frequency plots.")
    data = data[valid].copy()

    if data.empty:
        print("No data points with valid RF radius available for normalized-frequency plots")
        return None

    # Normalized frequency = stimulus frequency / RF radius
    data['normalized_frequency'] = data['frequency'] * 2 * data['rf_radius']

    if bin_edges is not None:
        # Use caller-specified fixed bin edges
        try:
            data['nf_bin'] = pd.cut(data['normalized_frequency'], bins=list(bin_edges),
                                    include_lowest=True)
        except ValueError as e:
            print(f"Could not bin normalized frequency with custom edges {bin_edges}: {e}")
            return None
    else:
        # Quantile bins so each bin has a comparable number of points
        if len(data) < n_bins:
            print(f"Not enough data points with RF radius ({len(data)}) for {n_bins} bins")
            return None
        try:
            data['nf_bin'] = pd.qcut(data['normalized_frequency'], n_bins, duplicates='drop')
        except ValueError as e:
            print(f"Could not bin normalized frequency: {e}")
            return None

    bins = list(data['nf_bin'].cat.categories)
    return data, bins, n_missing


def plot_combined_normalized_frequency(data, save_path=None, threshold=0.7, spi_regression_max=None,
                                       n_bins=4, bin_edges=None):
    """Plot 4 (combined): SPI vs ICI with all normalized-frequency bins overlaid.

    Shows every bin's points (colored by bin) and a regression line per bin, plus an
    overall regression across all points. Channels lacking a valid RF radius are skipped
    with a printed and on-figure warning.

    Args:
        data: 'all_strong' DataFrame (must include 'frequency' and 'rf_radius' columns).
        save_path: Path to save the figure. If None, the plot is only displayed.
        threshold: Strong-frequency response threshold (used only for the title).
        spi_regression_max: If not None, exclude points with SPI > this value from the fits.
        n_bins: Number of normalized-frequency bins (used only when bin_edges is None).
        bin_edges: Optional explicit bin edges, e.g. [0, 0.5, np.inf].
    """
    result = compute_normalized_frequency_bins(data, n_bins, bin_edges)
    if result is None:
        return
    data, bins, n_missing = result

    x = data['solid_preference_index'].values
    y = data['isochromatic_preference_index'].values
    p_values = data['p_value'].values

    # Overall regression across all points (optionally excludes high-SPI points)
    slope_all, intercept_all, r_value_all, p_value_all, r_squared_all, x_all = linregress_with_spi_cap(
        x, y, spi_regression_max)

    plt.figure(figsize=(12, 8))

    # Color map per bin
    bin_cmap = plt.cm.plasma
    bin_colors = {interval: bin_cmap(i / max(1, len(bins) - 1)) for i, interval in enumerate(bins)}

    # Plot points colored by bin, alpha by significance
    nf_bin_values = data['nf_bin'].values
    for i in range(len(x)):
        color = bin_colors[nf_bin_values[i]]
        if pd.notna(p_values[i]) and p_values[i] < 0.05:
            alpha_val, edge_color, lw = 0.7, 'black', 0.5
        else:
            alpha_val, edge_color, lw = 0.15, 'gray', 0.3
        plt.scatter(x[i], y[i], alpha=alpha_val, s=100, color=color, marker='o',
                    edgecolors=edge_color, linewidths=lw)

    # Per-bin regression lines (over the range used for each fit)
    for bin_idx, interval in enumerate(bins):
        bin_data = data[data['nf_bin'] == interval]
        if len(bin_data) > 1:
            xb = bin_data['solid_preference_index'].values
            yb = bin_data['isochromatic_preference_index'].values
            slope, intercept, r_value, p_val, r_squared, x_used = linregress_with_spi_cap(
                xb, yb, spi_regression_max)
            if len(x_used) > 1:
                line_x = np.linspace(x_used.min(), x_used.max(), 100)
                plt.plot(line_x, slope * line_x + intercept, linewidth=2,
                         color=bin_colors[interval], linestyle='--', alpha=0.8,
                         label=f'Bin {bin_idx + 1} [{interval.left:.2f}, {interval.right:.2f}] '
                               f'(R²={r_squared:.2f}, n={len(x_used)})')

    # Overall regression across all points
    if len(x_all) > 1:
        line_x = np.linspace(x_all.min(), x_all.max(), 100)
        plt.plot(line_x, slope_all * line_x + intercept_all, 'k-', linewidth=3, alpha=0.7,
                 label=f'All (R²={r_squared_all:.2f}, n={len(x_all)})')

    # Formatting
    n_significant = np.sum((pd.notna(p_values)) & (p_values < 0.05))
    plt.xlabel('Solid Preference Index', fontsize=14)
    plt.ylabel('Isochromatic Preference Index', fontsize=14)
    plt.title(
        f'Solid vs Isochromatic Preference by Normalized Frequency (freq / RF radius)\n'
        f'All {len(bins)} bins combined (≥{threshold * 100:.0f}% of max)\n'
        f'(n={len(data)} data points, {n_significant} solid-pref significant)',
        fontsize=14)

    add_plot_formatting(plt.gca(), r_squared_all, r_value_all, p_value_all, len(data), n_significant)

    plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', title='Normalized-freq bin')
    if n_missing > 0:
        plt.gcf().text(0.99, 0.01, f'{n_missing} point(s) without RF radius skipped',
                       ha='right', va='bottom', fontsize=8, color='red')
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Saved: {save_path}")

    print(f"\nCombined Normalized Frequency Statistics:")
    print(f"  Total data points: {len(data)}")
    print(f"  Significant: {n_significant}")
    if len(x_all) > 1:
        print(f"  Overall (all bins): R² = {r_squared_all:.3f}, r = {r_value_all:.3f}, p = {p_value_all:.3f}")
    for bin_idx, interval in enumerate(bins):
        bin_data = data[data['nf_bin'] == interval]
        if not bin_data.empty:
            n_sig = np.sum((pd.notna(bin_data['p_value'])) & (bin_data['p_value'] < 0.05))
            xb = bin_data['solid_preference_index'].values
            yb = bin_data['isochromatic_preference_index'].values
            _, _, r_val, p_val, _, x_used = linregress_with_spi_cap(xb, yb, spi_regression_max)
            if len(x_used) > 1:
                print(f"    Bin {bin_idx + 1} [{interval.left:.3f}, {interval.right:.3f}]: "
                      f"n={len(bin_data)} ({n_sig} sig.), r={r_val:.3f}, p={p_val:.3f}")


def plot_normalized_frequency_bins(data, save_dir=None, threshold=0.7, spi_regression_max=None,
                                   n_bins=4, bin_edges=None):
    """Plot 4: SPI vs ICI binned by normalized frequency (stimulus frequency / RF radius).

    Each data point's stimulus frequency (0.5, 1, 2, 4 Hz) is divided by the channel's
    receptive field radius (from ReceptiveFieldInfo). Points are split into bins of this
    ratio and one plot is produced per bin (replacing the per-frequency plots).

    Channels without valid RF radius information are skipped, with a printed warning and an
    on-figure note. (In 'mapped_channel' mode every channel has RF info, so none are skipped.)

    Args:
        data: 'all_strong' DataFrame (must include 'frequency' and 'rf_radius' columns).
        save_dir: Directory to save plots. If None, plots are only displayed.
        threshold: Strong-frequency response threshold (used only for the title).
        spi_regression_max: If not None, exclude points with SPI > this value from the fits.
        n_bins: Number of quantile bins (used only when bin_edges is None).
        bin_edges: Optional explicit bin edges, e.g. [0, 0.5, np.inf].
    """
    result = compute_normalized_frequency_bins(data, n_bins, bin_edges)
    if result is None:
        return
    data, bins, n_missing = result

    # Color points by their normalized frequency value (color scale set per bin's own range)
    nf_cmap = plt.cm.viridis

    for bin_idx, interval in enumerate(bins):
        bin_data = data[data['nf_bin'] == interval]
        if bin_data.empty:
            continue

        x = bin_data['solid_preference_index'].values
        y = bin_data['isochromatic_preference_index'].values
        p_values = bin_data['p_value'].values
        nf_values = bin_data['normalized_frequency'].values

        # Color scale spans this bin's normalized-frequency range
        nf_norm = plt.Normalize(vmin=float(np.min(nf_values)), vmax=float(np.max(nf_values)))

        # Overall regression (optionally excludes high-SPI points)
        slope, intercept, r_value, p_value, r_squared, x_reg = linregress_with_spi_cap(
            x, y, spi_regression_max)

        plt.figure(figsize=(12, 8))

        # Plot points colored by normalized frequency, alpha by significance
        for i in range(len(x)):
            color = nf_cmap(nf_norm(nf_values[i]))
            if pd.notna(p_values[i]) and p_values[i] < 0.05:
                alpha_val, edge_color, lw = 0.7, 'black', 0.5
            else:
                alpha_val, edge_color, lw = 0.15, 'gray', 0.3
            plt.scatter(x[i], y[i], alpha=alpha_val, s=100, color=color, marker='o',
                        edgecolors=edge_color, linewidths=lw)

        # Separate regression lines for sig-2D, non-sig, and sig-3D categories
        category_results = plot_category_regressions(plt.gca(), x, y, p_values,
                                                     spi_regression_max=spi_regression_max)

        # Formatting
        n_significant = np.sum((pd.notna(p_values)) & (p_values < 0.05))
        plt.xlabel('Solid Preference Index', fontsize=14)
        plt.ylabel('Isochromatic Preference Index', fontsize=14)
        plt.title(
            f'Solid vs Isochromatic Preference by Normalized Frequency (freq / RF radius)\n'
            f'Bin {bin_idx + 1}/{len(bins)}: ratio in [{interval.left:.3f}, {interval.right:.3f}] '
            f'(≥{threshold * 100:.0f}% of max)\n'
            f'(n={len(bin_data)} data points, {n_significant} solid-pref significant)',
            fontsize=14)

        add_plot_formatting(plt.gca(), r_squared, r_value, p_value, len(bin_data), n_significant)

        # Regression legend (right) plus a colorbar for normalized frequency (bottom)
        if plt.gca().get_legend_handles_labels()[0]:
            plt.legend(bbox_to_anchor=(1.02, 1), loc='upper left', title='Regression')
        sm = plt.cm.ScalarMappable(norm=nf_norm, cmap=nf_cmap)
        sm.set_array([])
        plt.colorbar(sm, ax=plt.gca(), orientation='horizontal', fraction=0.046, pad=0.1,
                     label='Normalized frequency (freq / RF radius)')

        if n_missing > 0:
            plt.gcf().text(0.99, 0.01, f'{n_missing} point(s) without RF radius skipped',
                           ha='right', va='bottom', fontsize=8, color='red')

        plt.tight_layout()

        if save_dir:
            save_path = os.path.join(save_dir, f"04_normfreq_bin{bin_idx + 1}.png")
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Saved: {save_path}")

        print(f"\nNormalized Frequency Bin {bin_idx + 1} "
              f"[{interval.left:.3f}, {interval.right:.3f}] Statistics:")
        print(f"  Data points: {len(bin_data)}")
        print(f"  Significant: {n_significant}")
        if len(x_reg) > 1:
            print(f"  Overall: R² = {r_squared:.3f}, r = {r_value:.3f}, p = {p_value:.3f}")
        print(f"  By significance category:")
        print_category_regressions(category_results)


def add_plot_formatting(ax, r_squared, r_value, p_value, n, n_sig):
    """Add common formatting to plots."""

    # Reference lines
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

    # Grid
    ax.grid(True, alpha=0.3)

    # Axis limits
    ax.set_xlim(-1.1, 1.1)
    ax.set_ylim(-1.1, 1.1)

    # Statistics text box
    stats_text = f'R² = {r_squared:.3f}\nr = {r_value:.3f}\np = {p_value:.3f}\nn = {n}\nsig. = {n_sig}'
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
            verticalalignment='top', fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

    # Quadrant labels
    ax.text(0.4, 0.9, 'Prefers 3D &\nIsochromatic', ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightblue', alpha=0.5), fontsize=10)
    ax.text(-0.6, 0.9, 'Prefers 2D &\nIsochromatic', ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.5), fontsize=10)
    ax.text(0.4, -0.9, 'Prefers 3D &\nIsoluminant', ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightcoral', alpha=0.5), fontsize=10)
    ax.text(-0.6, -0.9, 'Prefers 2D &\nIsoluminant', ha='center', va='center',
            bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow', alpha=0.5), fontsize=10)


if __name__ == "__main__":
    # Example 1: Use original selectivity filtering (default)
    # create_all_preference_plots(
    #     save_dir="/home/connorlab/Documents/plots/spi_vs_ici_selectivity",
    #     threshold=0.7,
    #     filter_type='selectivity'
    # )

    # Example 2: Use double filtering (GoodChannels + ChannelFiltering)
    # create_all_preference_plots(
    #     save_dir="/home/connorlab/Documents/plots/spi_vs_ici_double_filter",
    #     threshold=0.7,
    #     filter_type='double_filter'
    # )

    # Example 3: Use cluster channels only (matches spi_ici_clusters.py)
    # create_all_preference_plots(
    #     save_dir="/home/connorlab/Documents/plots/spi_vs_ici_cluster",
    #     threshold=0.7,
    #     filter_type='cluster',
    #     spi_regression_max=0.5,
    #     n_normalized_freq_bins=3
    # )

    # Example 4: Use mapped channels (cluster channels also in ReceptiveFieldInfo)
    # spi_regression_max excludes points with Solid Preference Index above this value
    # from every regression (the points are still plotted). Set to None to use all points.
    # nf_bin_edges overrides the normalized-frequency (freq / RF radius) bins for Plot 4;
    # set to None to use nf_n_bins quantile bins instead.
    create_all_preference_plots(
        save_dir="/home/connorlab/Documents/plots/spi_vs_ici_mapped_channel",
        threshold=0.70,
        filter_type='cluster',
        spi_regression_max=0.5,
        # nf_bin_edges=[0, 0.5, 1.0, 1.5, 2.5, 4, 6, 8.0, np.inf],
        # nf_bin_edges=[0,1.5,2.5,np.inf],
        nf_bin_edges=[0, 1.5, 2.5, 8.0, np.inf] # for 3d
    )
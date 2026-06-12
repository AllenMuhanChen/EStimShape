import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import theilslopes
from clat.util.connection import Connection


def calculate_regression(x, y, method='ols'):
    """Calculate regression statistics using specified method.

    Args:
        x, y: Data arrays
        method: 'ols' for ordinary least squares or 'theil-sen' for robust regression

    Returns:
        slope, intercept, r_value, p_value, r_squared
    """
    if len(x) <= 1:
        return 0, 0, 0, 0, 0

    if method == 'ols':
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2
        return slope, intercept, r_value, p_value, r_squared

    elif method == 'theil-sen':
        # Theil-Sen estimator
        result = theilslopes(y, x)
        slope = result.slope
        intercept = result.intercept

        # Calculate R-squared and correlation for Theil-Sen
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
        r_value = np.sign(slope) * np.sqrt(abs(r_squared))

        # P-value from Spearman correlation (non-parametric)
        r_spearman, p_value = stats.spearmanr(x, y)

        return slope, intercept, r_value, p_value, r_squared

    else:
        raise ValueError(f"Unknown regression method: {method}. Use 'ols' or 'theil-sen'")


def calculate_regression_with_spi_cap(x, y, method='ols', spi_regression_max=None):
    """Run calculate_regression after excluding points with solid preference index above a cap.

    Points with x (Solid Preference Index) greater than spi_regression_max are excluded
    from the regression only; callers are expected to still plot all points.

    Args:
        x, y: Data arrays (x is the Solid Preference Index)
        method: 'ols' or 'theil-sen'
        spi_regression_max: If not None, exclude points with x > this value from the fit.

    Returns:
        slope, intercept, r_value, p_value, r_squared, x_used
        where x_used is the x array actually used for the regression (handy for drawing
        the trend line over the correct range).
    """
    x = np.asarray(x)
    y = np.asarray(y)
    if spi_regression_max is not None:
        mask = x <= spi_regression_max
        x = x[mask]
        y = y[mask]
    slope, intercept, r_value, p_value, r_squared = calculate_regression(x, y, method)
    return slope, intercept, r_value, p_value, r_squared, x


def load_validated_channels_data():
    """Load data for channels that pass BOTH manual (GoodChannels) AND algorithmic (ChannelFiltering) validation.

    Returns:
        merged_df: DataFrame with solid and isochromatic preference indices for validated channels
        data_description: String describing the data source
    """
    # Connect to the data repository database
    conn = Connection("allen_data_repository")

    # Query both preference tables and join with BOTH GoodChannels AND ChannelFiltering (is_good=TRUE)
    solid_query = """
                  SELECT s.session_id, s.unit_name, s.solid_preference_index, s.p_value
                  FROM SolidPreferenceIndices s
                           JOIN GoodChannels g ON s.session_id = g.session_id AND s.unit_name = g.channel
                           JOIN ChannelFiltering c ON s.session_id = c.session_id AND s.unit_name = c.channel
                  WHERE c.is_good = TRUE
                  """

    isochromatic_query = """
                         SELECT i.session_id, i.unit_name, i.frequency, i.isochromatic_preference_index
                         FROM IsochromaticPreferenceIndices i
                                  JOIN GoodChannels g ON i.session_id = g.session_id AND i.unit_name = g.channel
                                  JOIN ChannelFiltering c ON i.session_id = c.session_id AND i.unit_name = c.channel
                         WHERE c.is_good = TRUE
                         """

    # Execute queries and fetch data
    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    conn.execute(isochromatic_query)
    isochromatic_data = conn.fetch_all()

    # Convert to DataFrames
    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])
    isochromatic_df = pd.DataFrame(isochromatic_data,
                                   columns=['session_id', 'unit_name', 'frequency', 'isochromatic_preference_index'])

    # Merge the data on session_id and unit_name
    merged_df = pd.merge(solid_df, isochromatic_df, on=['session_id', 'unit_name'], how='inner')

    data_description = "Validated Channels (GoodChannels AND is_good=TRUE)"

    return merged_df, data_description


def load_raw_significant_channels_data():
    """Load data for statistically significant raw channels from IsochromaticPreferenceIndices.

    Raw channels have names like "A-009" rather than sorted unit names like "A-009_Unit 1".

    Returns:
        merged_df: DataFrame with solid and isochromatic preference indices for raw significant channels
        data_description: String describing the data source
    """
    # Connect to the data repository database
    conn = Connection("allen_data_repository")

    # Query for raw channels (no underscore in unit_name) that are statistically significant
    # We need both solid and isochromatic preference data
    solid_query = """
                  SELECT s.session_id, s.unit_name, s.solid_preference_index, s.p_value
                  FROM SolidPreferenceIndices s
                  WHERE s.unit_name NOT LIKE '%Unit%'
                    AND s.p_value < 0.05
                  """

    isochromatic_query = """
                         SELECT i.session_id, i.unit_name, i.frequency, i.isochromatic_preference_index
                         FROM IsochromaticPreferenceIndices i
                         WHERE i.unit_name NOT LIKE '%Unit%'
                         """

    # Execute queries and fetch data
    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    conn.execute(isochromatic_query)
    isochromatic_data = conn.fetch_all()

    # Convert to DataFrames
    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])
    isochromatic_df = pd.DataFrame(isochromatic_data,
                                   columns=['session_id', 'unit_name', 'frequency', 'isochromatic_preference_index',
                                            ])

    # Merge the data on session_id and unit_name
    # Use the p_value from SolidPreferenceIndices (already in solid_df)
    merged_df = pd.merge(solid_df, isochromatic_df, on=['session_id', 'unit_name'], how='inner')

    # Drop the isochromatic p_value column since we're using solid preference p_value


    data_description = "Raw Significant Channels (p < 0.05, no spike sorting)"

    return merged_df, data_description


def load_cluster_channels_data(require_receptive_field=False):
    """Load data for cluster channels using the same selection as spi_ici_clusters.py.

    Selects cluster channels by joining SolidPreferenceIndices / IsochromaticPreferenceIndices
    with Experiments and ClusterInfo (e.experiment_id = c.experiment_id AND unit_name = c.channel).
    When require_receptive_field is True, additionally requires the channel to have an entry in
    ReceptiveFieldInfo for the same session_id (mapped_channel mode).

    Args:
        require_receptive_field: If True, also require a ReceptiveFieldInfo entry.

    Returns:
        merged_df: DataFrame with solid and isochromatic preference indices for selected channels
        data_description: String describing the data source
    """
    # Connect to the data repository database
    conn = Connection("allen_data_repository")

    # Optional join requiring the channel to also be in ReceptiveFieldInfo for that session.
    def rf_join(alias):
        if not require_receptive_field:
            return ""
        return (f"\n                           JOIN ReceptiveFieldInfo r "
                f"ON r.session_id = {alias}.session_id AND r.channel = {alias}.unit_name")

    # Query solid preference indices for cluster channels only (matches spi_ici_clusters.py)
    solid_query = f"""
                  SELECT s.session_id, s.unit_name, s.solid_preference_index, s.p_value
                  FROM SolidPreferenceIndices s
                           JOIN Experiments e ON s.session_id = e.session_id
                           JOIN ClusterInfo c ON e.experiment_id = c.experiment_id AND s.unit_name = c.channel{rf_join('s')}
                  """

    # Query isochromatic preference indices for cluster channels only (matches spi_ici_clusters.py)
    isochromatic_query = f"""
                         SELECT i.session_id, i.unit_name, i.frequency, i.isochromatic_preference_index
                         FROM IsochromaticPreferenceIndices i
                                  JOIN Experiments e ON i.session_id = e.session_id
                                  JOIN ClusterInfo c ON e.experiment_id = c.experiment_id AND i.unit_name = c.channel{rf_join('i')}
                         """

    # Execute queries and fetch data
    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    conn.execute(isochromatic_query)
    isochromatic_data = conn.fetch_all()

    # Convert to DataFrames
    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])
    isochromatic_df = pd.DataFrame(isochromatic_data,
                                   columns=['session_id', 'unit_name', 'frequency', 'isochromatic_preference_index'])

    # Remove duplicates (matches spi_ici_clusters.py)
    solid_df = solid_df.drop_duplicates(['session_id', 'unit_name'])
    isochromatic_df = isochromatic_df.drop_duplicates(['session_id', 'unit_name', 'frequency'])

    # Merge the data on session_id and unit_name
    merged_df = pd.merge(solid_df, isochromatic_df, on=['session_id', 'unit_name'], how='inner')

    if require_receptive_field:
        data_description = "Mapped Channels (cluster channels also in ReceptiveFieldInfo)"
    else:
        data_description = "Cluster Channels (ClusterInfo)"

    return merged_df, data_description


def load_data_for_selection_mode(selection_mode):
    """Load (merged_df, data_description) for the requested channel selection mode.

    Args:
        selection_mode: One of
            - 'double_filter': GoodChannels AND ChannelFiltering (validated channels)
            - 'raw_significant': Raw significant channels (p < 0.05, no spike sorting)
            - 'cluster': Cluster channels via ClusterInfo (matches spi_ici_clusters.py)
            - 'mapped_channel': Cluster channels that are also in ReceptiveFieldInfo

    Returns:
        merged_df, data_description
    """
    if selection_mode == 'double_filter':
        return load_validated_channels_data()
    elif selection_mode == 'raw_significant':
        return load_raw_significant_channels_data()
    elif selection_mode == 'cluster':
        return load_cluster_channels_data(require_receptive_field=False)
    elif selection_mode == 'mapped_channel':
        return load_cluster_channels_data(require_receptive_field=True)
    else:
        raise ValueError(f"Unknown selection_mode: {selection_mode}. "
                         f"Use 'double_filter', 'raw_significant', 'cluster', or 'mapped_channel'")


def create_preference_indices_frequency_plots(plot_individual_sessions=False, regression_method='ols',
                                              selection_mode='double_filter', spi_regression_max=None):
    """Create separate plots for each session, with subplots for each frequency, plus combined plots.

    Args:
        plot_individual_sessions: If True, create individual plots for each session. Default False.
        regression_method: Type of regression to use. Options:
            - 'ols': Ordinary Least Squares (standard linear regression)
            - 'theil-sen': Theil-Sen robust estimator (resistant to outliers)
        selection_mode: Channel selection mode. Options:
            - 'double_filter': GoodChannels AND ChannelFiltering (validated channels)
            - 'raw_significant': Raw significant channels (p < 0.05, no spike sorting)
            - 'cluster': Cluster channels via ClusterInfo (matches spi_ici_clusters.py)
            - 'mapped_channel': Cluster channels that are also in ReceptiveFieldInfo
        spi_regression_max: If not None, points with Solid Preference Index above this
            value are excluded from every regression (they are still plotted).
    """

    # ==================== DATA LOADING SECTION ====================
    # Channel selection is controlled by the selection_mode argument.
    merged_df, data_description = load_data_for_selection_mode(selection_mode)
    # ==============================================================

    if merged_df.empty:
        print(f"No matching data found for {data_description}")
        return

    # Get unique sessions and filter to specific frequencies
    sessions = sorted(merged_df['session_id'].unique())

    # Filter to only specific spatial frequencies
    target_frequencies = [0.5, 1.0, 2.0, 4.0]
    merged_df = merged_df[merged_df['frequency'].isin(target_frequencies)]
    frequencies = sorted(merged_df['frequency'].unique())

    print(f"Creating plots for {len(sessions)} sessions: {sessions}")
    print(f"Using spatial frequencies: {frequencies}")
    print(f"Data source: {data_description}")
    print(f"Total channels: {len(merged_df['unit_name'].unique())}")
    if spi_regression_max is not None:
        print(f"Excluding SPI > {spi_regression_max} from all regressions")

    # Show breakdown by session for validation - NOW INCLUDING SIGNIFICANCE COUNT
    for session in sessions:
        session_data = merged_df[merged_df['session_id'] == session]
        session_channels = session_data['unit_name'].nunique()
        # Count significant units for solid preference
        significant_units = session_data[session_data['p_value'] < 0.05]['unit_name'].nunique()
        print(
            f"  Session {session}: {session_channels} channels ({significant_units} solid-pref significant)")

    # Create a separate plot for each session (if enabled)
    if plot_individual_sessions:
        for session_id in sessions:
            plot_session_frequencies(merged_df, session_id, frequencies, regression_method, data_description,
                                     spi_regression_max)

    # Add combined plots
    print(f"\nCreating combined plots using {regression_method.upper()} regression...")
    create_combined_frequency_plots(merged_df, sessions, frequencies, regression_method, data_description,
                                    spi_regression_max)

    # Add significance-based regression plots
    print(f"\nCreating significance-based regression plots using {regression_method.upper()}...")
    plot_significant_cells_by_frequency(merged_df, frequencies, regression_method, data_description,
                                        spi_regression_max)
    plot_nonsignificant_cells_by_frequency(merged_df, frequencies, regression_method, data_description,
                                           spi_regression_max)

    return merged_df


def plot_session_frequencies(merged_df, session_id, frequencies, regression_method='ols', data_description="",
                             spi_regression_max=None):
    """Create a plot for one session with subplots for each frequency."""

    # Filter data for this session
    session_data = merged_df[merged_df['session_id'] == session_id]

    if session_data.empty:
        print(f"No data for session {session_id}")
        return

    # Create subplots - arrange frequencies in a 2x2 grid or single row
    n_freq = len(frequencies)
    if n_freq <= 2:
        nrows, ncols = 1, n_freq
    elif n_freq <= 4:
        nrows, ncols = 2, 2
    else:
        nrows, ncols = 2, (n_freq + 1) // 2

    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows))
    fig.suptitle(f'Session {session_id}: Solid vs Isochromatic Preference by Frequency\n({data_description})',
                 fontsize=16)

    # Make axes iterable even for single subplot
    if n_freq == 1:
        axes = [axes]
    elif nrows == 1:
        axes = axes
    else:
        axes = axes.flatten()

    # Plot each frequency
    for freq_idx, frequency in enumerate(frequencies):
        # Filter data for this frequency
        freq_data = session_data[session_data['frequency'] == frequency]

        ax = axes[freq_idx]

        if freq_data.empty:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{frequency} Hz')
            ax.set_xlim(-1.1, 1.1)
            ax.set_ylim(-1.1, 1.1)
            continue

        # Extract values
        x = freq_data['solid_preference_index'].values
        y = freq_data['isochromatic_preference_index'].values
        p_values = freq_data['p_value'].values

        # Calculate regression using specified method (optionally excluding high-SPI points)
        slope, intercept, r_value, p_value, r_squared, x_reg = calculate_regression_with_spi_cap(
            x, y, regression_method, spi_regression_max)

        # Plot points with different alpha based on significance
        for i in range(len(x)):
            # Check if p-value is significant (< 0.05)
            # If p_value is None/NaN, use low alpha
            if pd.notna(p_values[i]) and p_values[i] < 0.05:
                alpha_val = 0.7  # Solid/visible for significant
                color = 'blue'
            else:
                alpha_val = 0.15  # Barely visible for non-significant
                color = 'lightgray'

            ax.scatter(x[i], y[i], alpha=alpha_val, s=60, color=color)

        # Add trend line if we have enough points (over the range used for the regression)
        if len(x_reg) > 1 and not np.isnan(slope):
            line_x = np.linspace(x_reg.min(), x_reg.max(), 100)
            line_y = slope * line_x + intercept
            ax.plot(line_x, line_y, 'r-', linewidth=2, alpha=0.8)

        # Count significant units
        n_significant = np.sum((pd.notna(p_values)) & (p_values < 0.05))

        # Set title and labels - NOW INCLUDING SIGNIFICANCE COUNT
        ax.set_title(f'{frequency} Hz (n={len(freq_data)}, {n_significant} sig.)')
        ax.set_xlabel('Solid Preference Index')
        ax.set_ylabel('Isochromatic Preference Index')

        # Add reference lines at zero
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

        # Add grid
        ax.grid(True, alpha=0.3)

        # Set axis limits
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)

        # Add statistics text
        if len(x_reg) > 1:
            stats_text = f'R²={r_squared:.3f}\nr={r_value:.3f}\np={p_value:.3f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                    verticalalignment='top', fontsize=10,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

        # Add unit labels if there are few points (only for significant ones)
        if len(freq_data) <= 10:
            for idx, row in freq_data.iterrows():
                if pd.notna(row['p_value']) and row['p_value'] < 0.05:
                    ax.annotate(f"{row['unit_name']}",
                                (row['solid_preference_index'], row['isochromatic_preference_index']),
                                xytext=(3, 3), textcoords='offset points', fontsize=8, alpha=0.7)

    # Hide any unused subplots
    for idx in range(len(frequencies), len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    plt.show()

    # Print session statistics - NOW INCLUDING SIGNIFICANCE COUNT
    print(f"\nSession {session_id} Statistics ({data_description}):")
    for frequency in frequencies:
        freq_data = session_data[session_data['frequency'] == frequency]
        if not freq_data.empty:
            x = freq_data['solid_preference_index'].values
            y = freq_data['isochromatic_preference_index'].values
            p_vals = freq_data['p_value'].values
            n_sig = np.sum((pd.notna(p_vals)) & (p_vals < 0.05))
            _, _, r_value, p_value, _, x_reg = calculate_regression_with_spi_cap(
                x, y, regression_method, spi_regression_max)
            if len(x_reg) > 1:
                print(f"  {frequency} Hz: n={len(freq_data)} ({n_sig} sig.), r={r_value:.3f}, p={p_value:.3f}")
            else:
                print(f"  {frequency} Hz: n={len(freq_data)} ({n_sig} sig.) (insufficient data for correlation)")
        else:
            print(f"  {frequency} Hz: No data")


def create_combined_frequency_plots(merged_df, sessions, frequencies, regression_method='ols', data_description="",
                                    spi_regression_max=None):
    """Create combined plots showing all sessions together for each frequency."""

    # Create a separate combined plot for each frequency
    for frequency in frequencies:
        plot_combined_frequency_data(merged_df, frequency, sessions, regression_method, data_description,
                                     spi_regression_max)


def plot_combined_frequency_data(merged_df, frequency, sessions, regression_method='ols', data_description="",
                                 spi_regression_max=None):
    """Create a combined plot for one frequency with all sessions."""

    # Filter data for this frequency
    freq_data = merged_df[merged_df['frequency'] == frequency]

    if freq_data.empty:
        print(f"No data for frequency {frequency} Hz")
        return

    # Extract values
    x = freq_data['solid_preference_index'].values
    y = freq_data['isochromatic_preference_index'].values
    p_values = freq_data['p_value'].values

    # Calculate regression for combined data (optionally excluding high-SPI points)
    slope, intercept, r_value, p_value, r_squared, x_reg = calculate_regression_with_spi_cap(
        x, y, regression_method, spi_regression_max)

    # Create the scatter plot
    plt.figure(figsize=(12, 8))

    # Create a color map for sessions
    session_colors = plt.cm.Set1(np.linspace(0, 1, len(sessions)))

    # Plot each session with different colors, adjusting alpha for significance
    for i, session_id in enumerate(sessions):
        session_data = freq_data[freq_data['session_id'] == session_id]
        if not session_data.empty:
            # Separate significant and non-significant points
            sig_mask = (pd.notna(session_data['p_value'])) & (session_data['p_value'] < 0.05)

            # Plot significant points
            if sig_mask.any():
                plt.scatter(session_data[sig_mask]['solid_preference_index'],
                            session_data[sig_mask]['isochromatic_preference_index'],
                            c=[session_colors[i]], alpha=0.7, s=60,
                            label=f'Session {session_id} (n={len(session_data)}, {sig_mask.sum()} sig.)')

            # Plot non-significant points
            if (~sig_mask).any():
                plt.scatter(session_data[~sig_mask]['solid_preference_index'],
                            session_data[~sig_mask]['isochromatic_preference_index'],
                            c=[session_colors[i]], alpha=0.15, s=60)

                # If no significant points, still add legend entry
                if not sig_mask.any():
                    plt.scatter([], [], c=[session_colors[i]], alpha=0.7, s=60,
                                label=f'Session {session_id} (n={len(session_data)}, 0 sig.)')

    # Add trend line for combined data (over the range used for the regression)
    if len(x_reg) > 1:
        line_x = np.linspace(x_reg.min(), x_reg.max(), 100)
        line_y = slope * line_x + intercept
        plt.plot(line_x, line_y, 'k-', linewidth=2, label=f'Combined trend (R² = {r_squared:.3f})')

    # Add labels and title - NOW INCLUDING SIGNIFICANCE COUNT
    n_significant = np.sum((pd.notna(p_values)) & (p_values < 0.05))
    plt.xlabel('Solid Preference Index')
    plt.ylabel('Isochromatic Preference Index')
    plt.title(
        f'Combined - Frequency {frequency} Hz: Solid vs Isochromatic Preference\n'
        f'{data_description} (n={len(freq_data)} total units, {n_significant} solid-pref significant)')

    # Add reference lines at zero
    plt.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    plt.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

    # Add grid
    plt.grid(True, alpha=0.3)

    # Set axis limits
    plt.xlim(-1.1, 1.1)
    plt.ylim(-1.1, 1.1)

    # Add legend
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

    # Add statistics text box - NOW INCLUDING SIGNIFICANCE COUNT
    stats_text = f'R² = {r_squared:.3f}\nr = {r_value:.3f}\np = {p_value:.3f}\nn = {len(freq_data)}\nsig. = {n_significant}'
    plt.text(0.02, 0.98, stats_text, transform=plt.gca().transAxes,
             verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

    # Add quadrant labels
    plt.text(0.4, 0.9, 'Prefers 3D &\nIsochromatic', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightblue', alpha=0.5))
    plt.text(-0.6, 0.9, 'Prefers 2D &\nIsochromatic', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightgreen', alpha=0.5))
    plt.text(0.4, -0.9, 'Prefers 3D &\nIsoluminant', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightcoral', alpha=0.5))
    plt.text(-0.6, -0.9, 'Prefers 2D &\nIsoluminant', ha='center', va='center',
             bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow', alpha=0.5))

    plt.tight_layout()
    plt.show()

    # Print frequency statistics - NOW INCLUDING SIGNIFICANCE COUNT
    print(f"\nCombined {frequency} Hz Statistics ({data_description}):")
    print(f"  Total units: {len(freq_data)}")
    print(f"  Significant units (solid-pref p < 0.05): {n_significant}")
    print(f"  Solid Preference range: {x.min():.3f} to {x.max():.3f}")
    print(f"  Isochromatic Preference range: {y.min():.3f} to {y.max():.3f}")
    print(f"  Correlation: r = {r_value:.3f}, R² = {r_squared:.3f}, p = {p_value:.3f}")


def plot_significant_cells_by_frequency(merged_df, frequencies, regression_method='ols', data_description="",
                                        spi_regression_max=None):
    """Create a plot with subplots for each frequency showing only significant (p < 0.05) cells with SPI > 0."""

    # Filter for significant cells with positive solid preference index
    sig_df = merged_df[(merged_df['p_value'] < 0.05) & (merged_df['solid_preference_index'] > 0)].copy()

    if sig_df.empty:
        print("No significant cells found (p < 0.05 and SPI > 0)")
        return

    # Create subplots - arrange frequencies in a 2x2 grid or single row
    n_freq = len(frequencies)
    if n_freq <= 2:
        nrows, ncols = 1, n_freq
    elif n_freq <= 4:
        nrows, ncols = 2, 2
    else:
        nrows, ncols = 2, (n_freq + 1) // 2

    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows))
    fig.suptitle(
        f'Significant 3D-Preferring Cells: Solid vs Isochromatic Preference by Frequency\n'
        f'{data_description} (p < 0.05, SPI > 0, {regression_method.upper()} regression)',
        fontsize=16)

    # Make axes iterable even for single subplot
    if n_freq == 1:
        axes = [axes]
    elif nrows == 1:
        axes = axes
    else:
        axes = axes.flatten()

    # Plot each frequency
    for freq_idx, frequency in enumerate(frequencies):
        # Filter data for this frequency
        freq_data = sig_df[sig_df['frequency'] == frequency]

        ax = axes[freq_idx]

        if freq_data.empty:
            ax.text(0.5, 0.5, 'No Significant Data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{frequency} Hz (n=0)')
            ax.set_xlim(-1.1, 1.1)
            ax.set_ylim(-1.1, 1.1)
            continue

        # Extract values
        x = freq_data['solid_preference_index'].values
        y = freq_data['isochromatic_preference_index'].values

        # Calculate regression using specified method (optionally excluding high-SPI points)
        slope, intercept, r_value, p_value, r_squared, x_reg = calculate_regression_with_spi_cap(
            x, y, regression_method, spi_regression_max)

        # Plot points
        ax.scatter(x, y, alpha=0.7, s=60, color='blue')

        # Add trend line if we have enough points (over the range used for the regression)
        if len(x_reg) > 1 and not np.isnan(slope):
            line_x = np.linspace(x_reg.min(), x_reg.max(), 100)
            line_y = slope * line_x + intercept
            ax.plot(line_x, line_y, 'r-', linewidth=2, alpha=0.8)

        # Set title and labels
        ax.set_title(f'{frequency} Hz (n={len(freq_data)} sig.)')
        ax.set_xlabel('Solid Preference Index')
        ax.set_ylabel('Isochromatic Preference Index')

        # Add reference lines at zero
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

        # Add grid
        ax.grid(True, alpha=0.3)

        # Set axis limits
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)

        # Add statistics text
        if len(x_reg) > 1:
            stats_text = f'R²={r_squared:.3f}\nr={r_value:.3f}\np={p_value:.3f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                    verticalalignment='top', fontsize=10,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

    # Hide any unused subplots
    for idx in range(len(frequencies), len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    plt.show()

    # Print statistics
    print(f"\nSignificant 3D-Preferring Cells Statistics (p < 0.05, SPI > 0) - {data_description}:")
    print(f"  Total significant 3D-preferring units: {len(sig_df['unit_name'].unique())}")
    for frequency in frequencies:
        freq_data = sig_df[sig_df['frequency'] == frequency]
        if not freq_data.empty:
            x = freq_data['solid_preference_index'].values
            y = freq_data['isochromatic_preference_index'].values
            _, _, r_value, p_value, _, x_reg = calculate_regression_with_spi_cap(
                x, y, regression_method, spi_regression_max)
            if len(x_reg) > 1:
                print(f"  {frequency} Hz: n={len(freq_data)}, r={r_value:.3f}, p={p_value:.3f}")
            else:
                print(f"  {frequency} Hz: n={len(freq_data)} (insufficient data for correlation)")
        else:
            print(f"  {frequency} Hz: No data")


def plot_nonsignificant_cells_by_frequency(merged_df, frequencies, regression_method='ols', data_description="",
                                           spi_regression_max=None):
    """Create a plot with subplots for each frequency showing non-significant or 2D-preferring cells."""

    # Filter for cells that are NOT significant 3D-preferring (p >= 0.05 or SPI <= 0 or p is NaN)
    nonsig_df = merged_df[~((merged_df['p_value'] < 0.05) & (merged_df['solid_preference_index'] > 0))].copy()

    if nonsig_df.empty:
        print("No non-significant or 2D-preferring cells found")
        return

    # Create subplots - arrange frequencies in a 2x2 grid or single row
    n_freq = len(frequencies)
    if n_freq <= 2:
        nrows, ncols = 1, n_freq
    elif n_freq <= 4:
        nrows, ncols = 2, 2
    else:
        nrows, ncols = 2, (n_freq + 1) // 2

    fig, axes = plt.subplots(nrows, ncols, figsize=(6 * ncols, 5 * nrows))
    fig.suptitle(
        f'Non-Significant or 2D-Preferring Cells: Solid vs Isochromatic Preference by Frequency\n'
        f'{data_description} (p >= 0.05 or SPI <= 0, {regression_method.upper()} regression)',
        fontsize=16)

    # Make axes iterable even for single subplot
    if n_freq == 1:
        axes = [axes]
    elif nrows == 1:
        axes = axes
    else:
        axes = axes.flatten()

    # Plot each frequency
    for freq_idx, frequency in enumerate(frequencies):
        # Filter data for this frequency
        freq_data = nonsig_df[nonsig_df['frequency'] == frequency]

        ax = axes[freq_idx]

        if freq_data.empty:
            ax.text(0.5, 0.5, 'No Non-Significant Data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{frequency} Hz (n=0)')
            ax.set_xlim(-1.1, 1.1)
            ax.set_ylim(-1.1, 1.1)
            continue

        # Extract values
        x = freq_data['solid_preference_index'].values
        y = freq_data['isochromatic_preference_index'].values

        # Calculate regression using specified method (optionally excluding high-SPI points)
        slope, intercept, r_value, p_value, r_squared, x_reg = calculate_regression_with_spi_cap(
            x, y, regression_method, spi_regression_max)

        # Plot points in gray
        ax.scatter(x, y, alpha=0.4, s=60, color='gray')

        # Add trend line if we have enough points (over the range used for the regression)
        if len(x_reg) > 1 and not np.isnan(slope):
            line_x = np.linspace(x_reg.min(), x_reg.max(), 100)
            line_y = slope * line_x + intercept
            ax.plot(line_x, line_y, 'r-', linewidth=2, alpha=0.8)

        # Set title and labels
        ax.set_title(f'{frequency} Hz (n={len(freq_data)} non-sig.)')
        ax.set_xlabel('Solid Preference Index')
        ax.set_ylabel('Isochromatic Preference Index')

        # Add reference lines at zero
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)

        # Add grid
        ax.grid(True, alpha=0.3)

        # Set axis limits
        ax.set_xlim(-1.1, 1.1)
        ax.set_ylim(-1.1, 1.1)

        # Add statistics text
        if len(x_reg) > 1:
            stats_text = f'R²={r_squared:.3f}\nr={r_value:.3f}\np={p_value:.3f}'
            ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                    verticalalignment='top', fontsize=10,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

    # Hide any unused subplots
    for idx in range(len(frequencies), len(axes)):
        axes[idx].set_visible(False)

    plt.tight_layout()
    plt.show()

    # Print statistics
    print(f"\nNon-Significant or 2D-Preferring Cells Statistics - {data_description}:")
    print(f"  Total non-significant or 2D-preferring units: {len(nonsig_df['unit_name'].unique())}")
    for frequency in frequencies:
        freq_data = nonsig_df[nonsig_df['frequency'] == frequency]
        if not freq_data.empty:
            x = freq_data['solid_preference_index'].values
            y = freq_data['isochromatic_preference_index'].values
            _, _, r_value, p_value, _, x_reg = calculate_regression_with_spi_cap(
                x, y, regression_method, spi_regression_max)
            if len(x_reg) > 1:
                print(f"  {frequency} Hz: n={len(freq_data)}, r={r_value:.3f}, p={p_value:.3f}")
            else:
                print(f"  {frequency} Hz: n={len(freq_data)} (insufficient data for correlation)")
        else:
            print(f"  {frequency} Hz: No data")


if __name__ == "__main__":
    # Choose the channel selection mode:
    #   'double_filter'   - GoodChannels AND ChannelFiltering (validated channels)
    #   'raw_significant' - raw significant channels (p < 0.05, no spike sorting)
    #   'cluster'         - cluster channels via ClusterInfo (matches spi_ici_clusters.py)
    #   'mapped_channel'  - cluster channels also present in ReceptiveFieldInfo
    selection_mode = 'cluster'

    # Exclude points with Solid Preference Index above this value from every regression
    # (the points are still plotted). Set to None to use all points.
    spi_regression_max = 0.5

    # Generate plots with OLS regression (default)
    print("=" * 80)
    print(f"GENERATING PLOTS WITH OLS REGRESSION (selection_mode='{selection_mode}')")
    print("=" * 80)
    data_ols = create_preference_indices_frequency_plots(regression_method='ols', selection_mode=selection_mode,
                                                         spi_regression_max=spi_regression_max)

    # Generate plots with Theil-Sen regression
    print("\n" + "=" * 80)
    print(f"GENERATING PLOTS WITH THEIL-SEN REGRESSION (selection_mode='{selection_mode}')")
    print("=" * 80)
    data_theilsen = create_preference_indices_frequency_plots(regression_method='theil-sen', selection_mode=selection_mode,
                                                              spi_regression_max=spi_regression_max)
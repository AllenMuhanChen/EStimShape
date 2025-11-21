import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import theilslopes
from clat.util.connection import Connection


def calculate_regression(x, y, method='ols', p_values=None):
    """Calculate regression statistics using specified method.

    Args:
        x, y: Data arrays
        method: 'ols' for ordinary least squares (scipy),
                'simple' for simple least squares (manual calculation),
                'theil-sen' for robust regression,
                or 'wls' for weighted least squares
        p_values: Array of p-values for weighted regression (required if method='wls')

    Returns:
        slope, intercept, r_value, p_value, r_squared
    """
    if len(x) <= 1:
        return 0, 0, 0, 0, 0

    if method == 'ols':
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, y)
        r_squared = r_value ** 2
        return slope, intercept, r_value, p_value, r_squared

    elif method == 'simple':
        # Simple least squares using basic formulas
        n = len(x)
        x_mean = np.mean(x)
        y_mean = np.mean(y)

        # Calculate slope: β = Σ[(xi - x̄)(yi - ȳ)] / Σ[(xi - x̄)²]
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)

        if denominator == 0:
            return 0, 0, 0, 1, 0

        slope = numerator / denominator

        # Calculate intercept: α = ȳ - β*x̄
        intercept = y_mean - slope * x_mean

        # Calculate R-squared
        y_pred = slope * x + intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y_mean) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # Calculate correlation coefficient
        r_value = np.sign(slope) * np.sqrt(abs(r_squared))

        # Calculate p-value using t-test
        if n > 2:
            # Standard error of the slope
            se_slope = np.sqrt(ss_res / (n - 2) / denominator)
            # t-statistic
            t_stat = slope / se_slope if se_slope != 0 else 0
            # Two-tailed p-value
            p_value = 2 * (1 - stats.t.cdf(abs(t_stat), n - 2))
        else:
            p_value = 1.0

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

    elif method == 'wls':
        # Weighted Least Squares using -log10(p_value) as weights
        if p_values is None:
            raise ValueError("p_values must be provided for WLS regression")

        # Calculate weights: -log10(p_value)
        # Clip p_values to avoid log(0) and extreme weights
        p_values_clipped = np.clip(p_values, 1e-10, 1.0)
        weights = -np.log10(p_values_clipped)

        # Perform weighted polynomial fit (degree 1 = linear)
        coeffs = np.polyfit(x, y, deg=1, w=weights)
        slope = coeffs[0]
        intercept = coeffs[1]

        # Calculate weighted R-squared
        y_pred = slope * x + intercept
        # Weighted residuals
        weighted_ss_res = np.sum(weights * (y - y_pred) ** 2)
        weighted_mean_y = np.sum(weights * y) / np.sum(weights)
        weighted_ss_tot = np.sum(weights * (y - weighted_mean_y) ** 2)
        r_squared = 1 - (weighted_ss_res / weighted_ss_tot) if weighted_ss_tot != 0 else 0
        r_value = np.sign(slope) * np.sqrt(abs(r_squared))

        # P-value from weighted correlation test
        # Use Spearman as approximation (weights don't directly apply to p-value calculation)
        r_spearman, p_value = stats.spearmanr(x, y)

        return slope, intercept, r_value, p_value, r_squared

    else:
        raise ValueError(f"Unknown regression method: {method}. Use 'ols', 'simple', 'theil-sen', or 'wls'")


def create_spi_vs_ici_poster_plot(regression_method='ols', spi_min=0.0, spi_max=0.5):
    """
    Create poster-quality plot of SPI vs ICI for all cells, grouped by significance.

    Regression is calculated for:
    - Significant 3D cells with SPI in [spi_min, spi_max] (blue line)
    - Non-significant cells (gray line)

    Args:
        regression_method: 'ols', 'simple', 'theil-sen', or 'wls'
                          'wls' weights cells by -log10(p_value) for solid preference
        spi_min: Minimum SPI value for Sig 3D regression calculation (default 0.0)
        spi_max: Maximum SPI value for Sig 3D regression calculation (default 0.5)
    """

    # Connect to the data repository database
    conn = Connection("allen_data_repository")

    # Query solid preference WITH p-values for significance classification
    solid_query = """
                  SELECT s.session_id, s.unit_name, s.solid_preference_index, s.p_value
                  FROM SolidPreferenceIndices s
                           JOIN GoodChannels g ON s.session_id = g.session_id AND s.unit_name = g.channel
                           JOIN ChannelFiltering c ON s.session_id = c.session_id AND s.unit_name = c.channel
                  WHERE c.is_good = TRUE
                  """

    # Isochromatic preference with frequency filter
    isochromatic_query = """
                         SELECT i.session_id, i.unit_name, i.frequency, i.isochromatic_preference_index
                         FROM IsochromaticPreferenceIndices i
                                  JOIN GoodChannels g ON i.session_id = g.session_id AND i.unit_name = g.channel
                                  JOIN ChannelFiltering c ON i.session_id = c.session_id AND i.unit_name = c.channel
                         WHERE c.is_good = TRUE
                           AND i.frequency IN (0.5, 1.0, 2.0, 4.0)
                         """

    # Fetch and merge data
    conn.execute(solid_query)
    solid_data = conn.fetch_all()

    conn.execute(isochromatic_query)
    isochromatic_data = conn.fetch_all()

    solid_df = pd.DataFrame(solid_data,
                            columns=['session_id', 'unit_name', 'solid_preference_index', 'p_value'])
    isochromatic_df = pd.DataFrame(isochromatic_data,
                                   columns=['session_id', 'unit_name', 'frequency', 'isochromatic_preference_index'])

    merged_df = pd.merge(solid_df, isochromatic_df, on=['session_id', 'unit_name'], how='inner')

    if merged_df.empty:
        print("No data found")
        return None

    # Get frequencies
    frequencies = [0.5, 1.0, 2.0, 4.0]
    frequencies = [f for f in frequencies if f in merged_df['frequency'].values]

    # Count cells by significance group
    sig_3d_mask = (merged_df['p_value'] < 0.05) & (merged_df['solid_preference_index'] > 0)
    sig_2d_mask = (merged_df['p_value'] < 0.05) & (merged_df['solid_preference_index'] <= 0)
    nonsig_mask = ~(sig_3d_mask | sig_2d_mask)

    print(f"\nCreating poster plot for {len(frequencies)} frequencies: {frequencies}")
    print(f"Regression method: {regression_method.upper()}")
    print(f"Sig 3D regression SPI range: [{spi_min}, {spi_max}]")
    print(f"Total units: {len(merged_df['unit_name'].unique())}")
    print(f"  Significant 3D (p<0.05, SPI>0): {merged_df[sig_3d_mask]['unit_name'].nunique()}")
    print(f"  Significant 2D (p<0.05, SPI≤0): {merged_df[sig_2d_mask]['unit_name'].nunique()}")
    print(f"  Non-significant: {merged_df[nonsig_mask]['unit_name'].nunique()}")

    # Create the plot
    create_frequency_subplots(merged_df, frequencies, regression_method, spi_min, spi_max)

    return merged_df


def create_frequency_subplots(merged_df, frequencies, regression_method='ols', spi_min=0.0, spi_max=0.5):
    """Create 1x4 subplot grid for the four frequencies with all cell groups.

    Args:
        merged_df: DataFrame with all cells
        frequencies: List of frequencies to plot
        regression_method: 'ols', 'simple', 'theil-sen', or 'wls'
        spi_min: Minimum SPI for Sig 3D regression
        spi_max: Maximum SPI for Sig 3D regression
    """

    fig, axes = plt.subplots(2, 2, figsize=(14, 12))
    # fig.suptitle(
    #     f'Solid vs Isochromatic Preference by Significance Group\n'
    #     f'(Sig 3D regression on SPI ∈ [{spi_min}, {spi_max}], {regression_method.upper()})',
    #     fontsize=16)
    # fig.suptitle(
    #     f'Solid vs Isochromatic Preference by Significance Group',
    #     fontsize=16)

    axes = axes.flatten()

    for freq_idx, frequency in enumerate(frequencies):
        ax = axes[freq_idx]
        freq_data = merged_df[merged_df['frequency'] == frequency]

        if freq_data.empty:
            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(f'{frequency} Cycles / ° Visual Angle')
            ax.set_xlim(-1.1, 1.1)
            ax.set_ylim(-0.5, 0.8)
            continue

        # Classify cells into three groups
        sig_3d_mask = (pd.notna(freq_data['p_value'])) & \
                      (freq_data['p_value'] < 0.05) & \
                      (freq_data['solid_preference_index'] > 0)
        sig_2d_mask = (pd.notna(freq_data['p_value'])) & \
                      (freq_data['p_value'] < 0.05) & \
                      (freq_data['solid_preference_index'] <= 0)
        nonsig_mask = ~(sig_3d_mask | sig_2d_mask)

        # Extract data for each group
        sig_3d_data = freq_data[sig_3d_mask]
        sig_2d_data = freq_data[sig_2d_mask]
        nonsig_data = freq_data[nonsig_mask]

        # Initialize regression variables
        slope_3d, intercept_3d, r_3d, p_3d, r2_3d = 0, 0, 0, 1, 0
        slope_2d, intercept_2d, r_2d, p_2d, r2_2d = 0, 0, 0, 1, 0
        slope_ns, intercept_ns, r_ns, p_ns, r2_ns = 0, 0, 0, 1, 0

        # Calculate dynamic x-axis limits
        all_spi_values = freq_data['solid_preference_index'].values

        # Find leftmost point (likely a Sig 2D cell)
        leftmost_point = np.min(all_spi_values)

        # Find first excluded Sig 3D point (SPI > spi_max)
        if len(sig_3d_data) > 0:
            x_3d = sig_3d_data['solid_preference_index'].values
            excluded_points = x_3d[x_3d > spi_max]
            if len(excluded_points) > 0:
                first_excluded = np.min(excluded_points)
                # Go a bit past spi_max but not quite to first excluded point
                x_max = spi_max + 0.5 * (first_excluded - spi_max)
            else:
                # No excluded points, just go a bit past spi_max
                x_max = spi_max + 0.05
        else:
            x_max = spi_max + 0.05

        # Add padding to x_min
        x_min = leftmost_point - 0.05

        # Plot Significant 2D cells (red)
        if len(sig_2d_data) > 0:
            ax.scatter(sig_2d_data['solid_preference_index'],
                       sig_2d_data['isochromatic_preference_index'],
                       alpha=0.5, s=60, color='red',
                       label=f'Sig 2D (n={len(sig_2d_data)})',
                       edgecolors='black', linewidths=0.5)

        # Plot Non-significant cells (gray)
        if len(nonsig_data) > 0:
            ax.scatter(nonsig_data['solid_preference_index'],
                       nonsig_data['isochromatic_preference_index'],
                       alpha=0.3, s=60, color='gray',
                       label=f'Non-sig (n={len(nonsig_data)})',
                       edgecolors='black', linewidths=0.5)

        # Plot Significant 3D cells - distinguish between used/excluded from regression
        if len(sig_3d_data) > 0:
            x_3d = sig_3d_data['solid_preference_index'].values
            y_3d = sig_3d_data['isochromatic_preference_index'].values
            p_values_3d = sig_3d_data['p_value'].values

            # Determine which Sig 3D cells are in regression range
            regression_mask_3d = (x_3d >= spi_min) & (x_3d <= spi_max)

            # Plot Sig 3D cells excluded from regression (light blue) - NO LEGEND LABEL
            if np.sum(~regression_mask_3d) > 0:
                ax.scatter(x_3d[~regression_mask_3d], y_3d[~regression_mask_3d],
                           alpha=0.4, s=60, color='lightblue', marker='o',
                           edgecolors='black', linewidths=0.5)

            # Plot Sig 3D cells used in regression (dark blue)
            if np.sum(regression_mask_3d) > 0:
                ax.scatter(x_3d[regression_mask_3d], y_3d[regression_mask_3d],
                           alpha=0.7, s=60, color='blue',
                           label=f'Sig 3D in regression (n={np.sum(regression_mask_3d)})',
                           edgecolors='black', linewidths=0.5)

            # Calculate regression for Sig 3D cells in SPI range
            x_3d_reg = x_3d[regression_mask_3d]
            y_3d_reg = y_3d[regression_mask_3d]
            p_values_3d_reg = p_values_3d[regression_mask_3d]

            if len(x_3d_reg) > 1:
                if regression_method == 'wls':
                    slope_3d, intercept_3d, r_3d, p_3d, r2_3d = calculate_regression(
                        x_3d_reg, y_3d_reg, regression_method, p_values=p_values_3d_reg)
                else:
                    slope_3d, intercept_3d, r_3d, p_3d, r2_3d = calculate_regression(
                        x_3d_reg, y_3d_reg, regression_method)

                # Only plot Sig 3D regression line if p < 0.05
                if p_3d < 0.05:
                    line_x = np.linspace(x_min, x_max, 100)
                    line_y = slope_3d * line_x + intercept_3d
                    valid_idx = (line_y >= -0.5) & (line_y <= 0.75)
                    ax.plot(line_x[valid_idx], line_y[valid_idx], color='blue', linestyle='-',
                            linewidth=2, alpha=0.8, label=f'Sig 3D regression')

        # Calculate regression for Sig 2D cells
        if len(sig_2d_data) > 1:
            x_2d = sig_2d_data['solid_preference_index'].values
            y_2d = sig_2d_data['isochromatic_preference_index'].values
            p_values_2d = sig_2d_data['p_value'].values

            # Use WLS if specified, but with p-values from Sig 2D cells
            if regression_method == 'wls':
                slope_2d, intercept_2d, r_2d, p_2d, r2_2d = calculate_regression(
                    x_2d, y_2d, regression_method, p_values=p_values_2d)
            else:
                slope_2d, intercept_2d, r_2d, p_2d, r2_2d = calculate_regression(
                    x_2d, y_2d, regression_method)

            # Only plot Sig 2D regression line if p < 0.05
            # if p_2d < 0.05:
            #     line_x = np.linspace(x_min, x_max, 100)
            #     line_y = slope_2d * line_x + intercept_2d
            #     valid_idx = (line_y >= -0.5) & (line_y <= 0.75)
            #     ax.plot(line_x[valid_idx], line_y[valid_idx], color='red', linestyle='-',
            #             linewidth=2, alpha=0.8, label=f'Sig 2D regression')

        # Calculate regression for Non-significant cells
        if len(nonsig_data) > 1:
            x_nonsig = nonsig_data['solid_preference_index'].values
            y_nonsig = nonsig_data['isochromatic_preference_index'].values

            # Don't use WLS for non-sig (no meaningful p-values)
            if regression_method == 'wls':
                slope_ns, intercept_ns, r_ns, p_ns, r2_ns = calculate_regression(
                    x_nonsig, y_nonsig, 'ols')  # Use OLS instead
            else:
                slope_ns, intercept_ns, r_ns, p_ns, r2_ns = calculate_regression(
                    x_nonsig, y_nonsig, regression_method)

            # Only plot Non-sig regression line if p < 0.05
            # if p_ns < 0.05:
            #     line_x = np.linspace(x_min, x_max, 100)
            #     line_y = slope_ns * line_x + intercept_ns
            #     valid_idx = (line_y >= -0.5) & (line_y <= 0.75)
            #     ax.plot(line_x[valid_idx], line_y[valid_idx], color='gray', linestyle='-',
            #             linewidth=2, alpha=0.8, label=f'Non-sig regression')

        # Set title and labels
        ax.set_title(f'{frequency} cycles/°', fontsize=36)
        ax.set_xlabel('Solid Preference Index', fontsize=20)
        ax.set_ylabel('Luminance Preference Index', fontsize=20)

        # increase tick label sizes
        ax.tick_params(axis='both', which='major', labelsize=20)  # Adjust size as needed

        # Add reference lines at zero
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.3, linewidth=1)

        # Add reference lines at zero
        ax.axhline(y=0, color='black', linestyle='--', alpha=0.3, linewidth=1)
        ax.axvline(x=0, color='black', linestyle='--', alpha=0.3, linewidth=1)



        # Add grid
        ax.grid(True, alpha=0.3)

        # Set axis limits
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(-0.5, 0.8)

        # Add statistics text - only for groups where we calculated regression
        stats_text = []
        if len(sig_3d_data) > 0 and np.sum(regression_mask_3d) > 1:
            stats_text.append(f'Sig 3D: n={np.sum(regression_mask_3d)}, '
                              f'R²={r2_3d:.3f}, r={r_3d:.3f}, p={p_3d:.4f}')
        # if len(sig_2d_data) > 1:
        #     stats_text.append(f'Sig 2D: n={len(sig_2d_data)}, '
        #                       f'R²={r2_2d:.3f}, r={r_2d:.3f}, p={p_2d:.4f}')
        # if len(nonsig_data) > 1:
        #     stats_text.append(f'Non-sig: n={len(nonsig_data)}, '
        #                       f'R²={r2_ns:.3f}, r={r_ns:.3f}, p={p_ns:.4f}')
        #
        if stats_text:
            ax.text(0.02, 0.98, '\n'.join(stats_text), transform=ax.transAxes,
                    verticalalignment='top', fontsize=16,
                    bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.8))

        # Add legend
        ax.legend(loc='lower right', fontsize=8, ncol=1)

    plt.tight_layout()
    plt.show()

    # Print summary statistics
    print("\n" + "=" * 70)
    print(f"SUMMARY: All Cells by Significance Group")
    print(f"Sig 3D regression calculated on SPI range: [{spi_min}, {spi_max}]")
    print(f"Note: Regression lines only shown when p < 0.05")
    print("=" * 70)
    for frequency in frequencies:
        freq_data = merged_df[merged_df['frequency'] == frequency]
        if not freq_data.empty:
            # Classify
            sig_3d_mask = (pd.notna(freq_data['p_value'])) & \
                          (freq_data['p_value'] < 0.05) & \
                          (freq_data['solid_preference_index'] > 0)
            sig_2d_mask = (pd.notna(freq_data['p_value'])) & \
                          (freq_data['p_value'] < 0.05) & \
                          (freq_data['solid_preference_index'] <= 0)
            nonsig_mask = ~(sig_3d_mask | sig_2d_mask)

            print(f"\n{frequency} Hz:")
            print(f"  Total cells: {len(freq_data)}")
            print(f"  Sig 3D: {np.sum(sig_3d_mask)}, Sig 2D: {np.sum(sig_2d_mask)}, "
                  f"Non-sig: {np.sum(nonsig_mask)}")

            # Sig 3D regression stats
            if np.sum(sig_3d_mask) > 0:
                sig_3d_data = freq_data[sig_3d_mask]
                x_3d = sig_3d_data['solid_preference_index'].values
                y_3d = sig_3d_data['isochromatic_preference_index'].values
                p_values_3d = sig_3d_data['p_value'].values

                regression_mask_3d = (x_3d >= spi_min) & (x_3d <= spi_max)
                x_3d_reg = x_3d[regression_mask_3d]
                y_3d_reg = y_3d[regression_mask_3d]
                p_values_3d_reg = p_values_3d[regression_mask_3d]

                print(f"  Sig 3D in regression range: {len(x_3d_reg)}")
                if len(x_3d_reg) > 1:
                    if regression_method == 'wls':
                        slope, intercept, r_value, p_value, r_squared = calculate_regression(
                            x_3d_reg, y_3d_reg, regression_method, p_values=p_values_3d_reg)
                    else:
                        slope, intercept, r_value, p_value, r_squared = calculate_regression(
                            x_3d_reg, y_3d_reg, regression_method)
                    print(f"    Regression: r={r_value:.3f}, R²={r_squared:.3f}, p={p_value:.4f}")
                    print(f"    Slope={slope:.3f}, Intercept={intercept:.3f}")
                    if p_value >= 0.05:
                        print(f"    (Line not shown: p >= 0.05)")

            # Sig 2D regression stats
            if np.sum(sig_2d_mask) > 1:
                sig_2d_data = freq_data[sig_2d_mask]
                x_2d = sig_2d_data['solid_preference_index'].values
                y_2d = sig_2d_data['isochromatic_preference_index'].values
                p_values_2d = sig_2d_data['p_value'].values

                if regression_method == 'wls':
                    slope, intercept, r_value, p_value, r_squared = calculate_regression(
                        x_2d, y_2d, regression_method, p_values=p_values_2d)
                else:
                    slope, intercept, r_value, p_value, r_squared = calculate_regression(
                        x_2d, y_2d, regression_method)
                print(f"  Sig 2D regression: r={r_value:.3f}, R²={r_squared:.3f}, p={p_value:.4f}")
                print(f"    Slope={slope:.3f}, Intercept={intercept:.3f}")
                if p_value >= 0.05:
                    print(f"    (Line not shown: p >= 0.05)")

            # Non-sig regression stats
            if np.sum(nonsig_mask) > 1:
                nonsig_data = freq_data[nonsig_mask]
                x_ns = nonsig_data['solid_preference_index'].values
                y_ns = nonsig_data['isochromatic_preference_index'].values

                if regression_method == 'wls':
                    slope, intercept, r_value, p_value, r_squared = calculate_regression(
                        x_ns, y_ns, 'ols')
                else:
                    slope, intercept, r_value, p_value, r_squared = calculate_regression(
                        x_ns, y_ns, regression_method)
                print(f"  Non-sig regression: r={r_value:.3f}, R²={r_squared:.3f}, p={p_value:.4f}")
                if p_value >= 0.05:
                    print(f"    (Line not shown: p >= 0.05)")
        else:
            print(f"\n{frequency} Hz: No data")


if __name__ == "__main__":
    # Generate poster plot with OLS regression
    print("=" * 80)
    print("GENERATING POSTER PLOT WITH OLS REGRESSION")
    print("=" * 80)
    data_ols = create_spi_vs_ici_poster_plot(regression_method='ols', spi_min=0.0, spi_max=0.33)

    # Generate poster plot with Theil-Sen regression
    print("\n" + "=" * 80)
    print("GENERATING POSTER PLOT WITH THEIL-SEN REGRESSION")
    print("=" * 80)
    data_theilsen = create_spi_vs_ici_poster_plot(regression_method='theil-sen', spi_min=0.0, spi_max=0.33)

    # Generate poster plot with WLS regression (weighted by p-value)
    print("\n" + "=" * 80)
    print("GENERATING POSTER PLOT WITH WEIGHTED LEAST SQUARES (WLS) REGRESSION")
    print("Cells weighted by -log10(p_value) of solid preference significance")
    print("=" * 80)
    data_wls = create_spi_vs_ici_poster_plot(regression_method='wls', spi_min=0.0, spi_max=0.33)
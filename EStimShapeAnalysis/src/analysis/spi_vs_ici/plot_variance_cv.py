import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

from clat.util.connection import Connection


def load_validated_raw_channels(metric_name='variance_cv'):
    """
    Load metric data for validated raw channels.

    Validated channels must appear in BOTH:
    - GoodChannels table (manually validated)
    - ChannelFiltering table (passes automated quality checks with is_good=TRUE)

    Also joins with SolidPreferenceIndices for 3D significance info.
    """
    conn = Connection("allen_data_repository")

    query = """
            SELECT icls.session_id,
                   icls.unit_name,
                   icls.frequency,
                   icls.metric_name,
                   icls.isochromatic_score,
                   icls.isoluminant_score,
                   spi.solid_preference_index,
                   spi.p_value
            FROM IsoChromaticLuminantScores icls
                     INNER JOIN GoodChannels gc
                                ON icls.session_id = gc.session_id
                                    AND icls.unit_name = gc.channel
                     INNER JOIN ChannelFiltering cf
                                ON icls.session_id = cf.session_id
                                    AND icls.unit_name = cf.channel
                     LEFT JOIN SolidPreferenceIndices spi
                               ON icls.session_id = spi.session_id
                                   AND icls.unit_name = spi.unit_name
            WHERE icls.metric_name = %s
              AND icls.frequency = 0
            """

    conn.execute(query, (metric_name,))
    result = conn.fetch_all()
    if result is None or len(result) == 0:
        print(f"No data found for metric: {metric_name}")
        return None

    df = pd.DataFrame(result,
                      columns=['session_id', 'unit_name', 'frequency', 'metric_name',
                               'isochromatic_score', 'isoluminant_score',
                               'solid_preference_index', 'p_value'])
    print(f"Loaded {len(df)} validated raw channels for {metric_name}")

    return df


def main():
    # Create plots for both metrics
    create_metric_plot(
        metric_name='variance_cv',
        save_path="/home/connorlab/Documents/plots/group"
    )

    create_metric_plot(
        metric_name='entropy',
        save_path="/home/connorlab/Documents/plots/group"
    )

    create_metric_plot(
        metric_name='mean_all_normalized',
        save_path="/home/connorlab/Documents/plots/group"
    )


def create_metric_plot(metric_name='variance_cv', save_path=None):
    """
    Create plot showing isochromatic vs isoluminant scores for a given metric.
    Points are colored by 3D significance status.

    Args:
        metric_name: The metric to plot ('variance_cv', 'entropy', etc.)
        save_path: Optional directory path to save plots. If None, plots are only displayed.
    """

    # Create save directory if specified
    if save_path is not None:
        os.makedirs(save_path, exist_ok=True)

    # Load the data
    metric_data = load_validated_raw_channels(metric_name)

    if metric_data is None or metric_data.empty:
        print(f"No {metric_name} data available")
        return None

    print(f"\nCreating {metric_name} plot")
    print(f"Total units/channels: {len(metric_data)}")

    # Create plot
    create_scatter_plot(metric_data, metric_name, save_path)

    return metric_data


def create_scatter_plot(metric_data, metric_name, save_path=None):
    """Create scatter plot of isochromatic vs isoluminant scores for any metric."""

    # Metric-specific labels and titles
    metric_labels = {
        'variance_cv': {
            'title': 'Coefficient of Variation',
            'xlabel': 'Isochromatic CV',
            'ylabel': 'Isoluminant CV',
            'description': 'Higher CV = more variable responses'
        },
        'entropy': {
            'title': "Shannon's Entropy",
            'xlabel': 'Isochromatic Entropy (bits)',
            'ylabel': 'Isoluminant Entropy (bits)',
            'description': 'Higher entropy = less selective (more uniform responses)'
        },
        'mean_all_normalized': {
            'title': 'Normalized Mean Response',
            'xlabel': 'Isochromatic (normalized)',
            'ylabel': 'Isoluminant (normalized)',
            'description': 'Mean responses normalized by max response (0-1 scale)'
        }
    }

    labels = metric_labels.get(metric_name, {
        'title': metric_name.replace('_', ' ').title(),
        'xlabel': f'Isochromatic {metric_name}',
        'ylabel': f'Isoluminant {metric_name}',
        'description': ''
    })

    fig, ax = plt.subplots(figsize=(10, 8))

    x = metric_data['isochromatic_score'].values
    y = metric_data['isoluminant_score'].values
    p_values = metric_data['p_value'].values
    spi_values = metric_data['solid_preference_index'].values

    # Classify: Significant 3D vs Significant 2D vs Non-significant
    sig_3d_mask = (pd.notna(p_values)) & (p_values < 0.05) & (spi_values > 0)
    sig_2d_mask = (pd.notna(p_values)) & (p_values < 0.05) & (spi_values <= 0)
    nonsig_mask = ~(sig_3d_mask | sig_2d_mask)

    x_sig_3d = x[sig_3d_mask]
    y_sig_3d = y[sig_3d_mask]
    x_sig_2d = x[sig_2d_mask]
    y_sig_2d = y[sig_2d_mask]
    x_nonsig = x[nonsig_mask]
    y_nonsig = y[nonsig_mask]

    # Plot significant 3D
    if sig_3d_mask.any():
        ax.scatter(x_sig_3d, y_sig_3d,
                   c='blue', alpha=0.7, s=80, label='Significant 3D (p<0.05, SPI>0)',
                   edgecolors='black', linewidths=0.5)

    # Plot significant 2D
    if sig_2d_mask.any():
        ax.scatter(x_sig_2d, y_sig_2d,
                   c='red', alpha=0.7, s=80, label='Significant 2D (p<0.05, SPI≤0)',
                   edgecolors='black', linewidths=0.5)

    # Plot non-significant
    if nonsig_mask.any():
        ax.scatter(x_nonsig, y_nonsig,
                   c='gray', alpha=0.5, s=80, label='Non-significant',
                   edgecolors='black', linewidths=0.5)

    n_sig_3d = np.sum(sig_3d_mask)
    n_sig_2d = np.sum(sig_2d_mask)
    n_nonsig = np.sum(nonsig_mask)

    title = f"Isochromatic vs Isoluminant {labels['title']}\n" \
            f"Validated raw channels (GoodChannels ∩ ChannelFiltering)\n" \
            f"(n={len(metric_data)}, {n_sig_3d} sig. 3D, {n_sig_2d} sig. 2D, {n_nonsig} non-sig)"

    if labels['description']:
        title += f"\n{labels['description']}"

    ax.set_title(title, fontsize=14)
    ax.set_xlabel(labels['xlabel'], fontsize=12)
    ax.set_ylabel(labels['ylabel'], fontsize=12)

    # Add diagonal reference line (y=x)
    lims = [
        np.min([ax.get_xlim(), ax.get_ylim()]),
        np.max([ax.get_xlim(), ax.get_ylim()]),
    ]
    ax.plot(lims, lims, 'k--', alpha=0.3, zorder=0, linewidth=1)

    # Add grid
    ax.grid(True, alpha=0.3)

    # Add legend
    ax.legend(loc='best', fontsize=10)

    plt.tight_layout()

    if save_path is not None:
        filename = os.path.join(save_path, f'{metric_name}_validated_raw.png')
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"Saved: {filename}")

    plt.show()

    # Print summary statistics
    print("\n" + "=" * 80)
    print(f"{labels['title'].upper()} SUMMARY")
    print("=" * 80)
    print(f"Total units: {len(metric_data)}")
    print(f"Significant 3D units: {n_sig_3d}")
    print(f"Significant 2D units: {n_sig_2d}")
    print(f"Non-significant units: {n_nonsig}")

    if n_sig_3d > 0:
        print(f"\nSignificant 3D units:")
        print(f"  Isochromatic - mean: {np.mean(x_sig_3d):.3f}, std: {np.std(x_sig_3d):.3f}")
        print(f"  Isoluminant - mean: {np.mean(y_sig_3d):.3f}, std: {np.std(y_sig_3d):.3f}")

    if n_sig_2d > 0:
        print(f"\nSignificant 2D units:")
        print(f"  Isochromatic - mean: {np.mean(x_sig_2d):.3f}, std: {np.std(x_sig_2d):.3f}")
        print(f"  Isoluminant - mean: {np.mean(y_sig_2d):.3f}, std: {np.std(y_sig_2d):.3f}")

    if n_nonsig > 0:
        print(f"\nNon-significant units:")
        print(f"  Isochromatic - mean: {np.mean(x_nonsig):.3f}, std: {np.std(x_nonsig):.3f}")
        print(f"  Isoluminant - mean: {np.mean(y_nonsig):.3f}, std: {np.std(y_nonsig):.3f}")

if __name__ == "__main__":
    main()
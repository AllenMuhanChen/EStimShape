import matplotlib.pyplot as plt
import numpy as np
from clat.util.connection import Connection
import json


def plot_estim_effects_summary(session_id, effect_threshold=15, output_path=None, n_threshold=15,
                               condition_filter=None):
    """
    Create summary plots of EStim effects:
    1. Histogram of effect sizes
    2. Matrix of subplots showing estim on/off comparisons for large effects

    Args:
        session_id: Session identifier (or "All" for all sessions)
        effect_threshold: Minimum absolute effect size to include in subplot matrix
        output_path: Path to save the plot
        n_threshold: Minimum number of trials required for estim_on
        condition_filter: Dict of conditions to filter by, e.g. {'trial_type': 'Delta Shape', 'noise_chance': 0.5}
    """
    # Read data from EStimEffects table
    repo_conn = Connection("allen_data_repository")
    if session_id is None or session_id == "All":
        repo_conn.execute("""
                          SELECT session_id,
                                 conditions,
                                 estim_on_pct_hypothesized,
                                 estim_off_pct_hypothesized,
                                 estim_on_n_trials,
                                 estim_off_n_trials,
                                 effect_size
                          FROM EStimEffects
                          """)
    else:
        repo_conn.execute("""
                          SELECT session_id,
                                 conditions,
                                 estim_on_pct_hypothesized,
                                 estim_off_pct_hypothesized,
                                 estim_on_n_trials,
                                 estim_off_n_trials,
                                 effect_size
                          FROM EStimEffects
                          WHERE session_id = %s
                          """, (session_id,))

    column_names = [desc[0] for desc in repo_conn.my_cursor.description]
    results = repo_conn.fetch_all()

    if len(results) == 0:
        print(f"No data found for session {session_id}")
        return

    # Parse results
    effects_data = []
    for row in results:
        row_dict = dict(zip(column_names, row))
        row_dict['conditions_dict'] = json.loads(row_dict['conditions'])
        effects_data.append(row_dict)

    print(f"Loaded {len(effects_data)} condition combinations")

    # Apply condition filter if provided
    if condition_filter:
        filtered_data = []
        for d in effects_data:
            match = True
            for key, value in condition_filter.items():
                if key not in d['conditions_dict'] or d['conditions_dict'][key] != value:
                    match = False
                    break
            if match:
                filtered_data.append(d)
        effects_data = filtered_data
        print(f"After filtering: {len(effects_data)} condition combinations")

        # Add filter info to title
        filter_str = ', '.join([f"{k}={v}" for k, v in condition_filter.items()])
    else:
        filter_str = None

    if len(effects_data) == 0:
        print(f"No data found after applying filters")
        return

    # Create figure with subplots
    fig = plt.figure(figsize=(16, 10))

    # 1. Histogram of effect sizes (top subplot)
    ax_hist = plt.subplot2grid((4, 1), (0, 0))

    effect_sizes = [d['effect_size'] for d in effects_data if
                    d['effect_size'] is not None and d['estim_on_n_trials'] >= n_threshold]

    ax_hist.hist(effect_sizes, bins=20, color='steelblue', alpha=0.7, edgecolor='black')
    ax_hist.axvline(x=0, color='red', linestyle='--', linewidth=2, label='No Effect')
    # ax_hist.axvline(x=effect_threshold, color='green', linestyle='--', linewidth=1.5,
    #                 label=f'Threshold ±{effect_threshold}%')
    # ax_hist.axvline(x=-effect_threshold, color='green', linestyle='--', linewidth=1.5)

    ax_hist.set_xlabel('Effect Size (EStim ON - EStim OFF %)', fontsize=12)
    ax_hist.set_ylabel('Count', fontsize=12)

    hist_title = f'{session_id} - Distribution of EStim Effect Sizes'
    if filter_str:
        hist_title += f'\nFiltered by: {filter_str}'
    ax_hist.set_title(hist_title, fontsize=14)
    ax_hist.legend()
    ax_hist.grid(True, alpha=0.3)

    # 2. Filter for large effects
    large_effects = [d for d in effects_data
                     if d['effect_size'] is not None
                     and abs(d['effect_size']) >= effect_threshold
                     and d['estim_on_n_trials'] >= n_threshold]

    print(f"Found {len(large_effects)} conditions with |effect size| > {effect_threshold}%")

    if len(large_effects) == 0:
        plt.tight_layout()
        if output_path:
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            print(f"\nSaved plot to {output_path}")
        plt.show()
        return

    # Sort by effect size for better visualization
    large_effects.sort(key=lambda x: x['effect_size'], reverse=True)

    # 3. Create matrix of comparison plots
    n_conditions = len(large_effects)
    n_cols = min(5, n_conditions)  # Max 5 columns
    n_rows = int(np.ceil(n_conditions / n_cols))

    # Create grid for comparison plots (takes remaining space)
    gs = fig.add_gridspec(n_rows, n_cols,
                          left=0.05, right=0.95,
                          top=0.60, bottom=0.05,
                          hspace=0.4, wspace=0.3)

    for idx, effect_data in enumerate(large_effects):
        row = idx // n_cols
        col = idx % n_cols

        ax = fig.add_subplot(gs[row, col])

        # Extract data
        estim_on_pct = effect_data['estim_on_pct_hypothesized']
        estim_off_pct = effect_data['estim_off_pct_hypothesized']
        effect = effect_data['effect_size']
        n_on = effect_data['estim_on_n_trials']
        n_off = effect_data['estim_off_n_trials']

        # Plot two dots vertically aligned
        x_pos = 0.5
        ax.plot(x_pos, estim_off_pct, 'o', color='gray', markersize=12,
                label=f'OFF (n={n_off})', alpha=0.7)
        ax.plot(x_pos, estim_on_pct, 'o', color='red', markersize=12,
                label=f'ON (n={n_on})', alpha=0.7)

        # Draw connecting line
        ax.plot([x_pos, x_pos], [estim_off_pct, estim_on_pct], 'k-', linewidth=2, alpha=0.3)

        # Add effect size annotation
        mid_y = (estim_on_pct + estim_off_pct) / 2
        ax.text(x_pos + 0.15, mid_y, f'{effect:+.1f}%',
                fontsize=10, fontweight='bold',
                verticalalignment='center')

        # Formatting
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 100)
        ax.set_xticks([])
        ax.set_ylabel('% Hypothesized Chosen', fontsize=9)
        ax.axhline(y=50, color='black', linestyle=':', linewidth=1, alpha=0.3)
        ax.grid(True, alpha=0.2, axis='y')

        # Create concise title from conditions
        cond_dict = effect_data['conditions_dict']
        title_parts = []
        if 'trial_type' in cond_dict:
            tt = cond_dict['trial_type']
            title_parts.append(tt[:3] if tt != 'Combined' else 'Cmb')
        if 'noise_chance' in cond_dict:
            title_parts.append(f"{int(cond_dict['noise_chance'] * 100)}%")
        if 'polarity' in cond_dict:
            pol = 'Pos' if cond_dict['polarity'] == 'PositiveFirst' else 'Neg'
            title_parts.append(pol)
        if 'num_channels' in cond_dict:
            title_parts.append(f"{cond_dict['num_channels']}ch")

        ax.set_title(' '.join(title_parts), fontsize=9, fontweight='bold')

    main_title = f'{session_id} - Conditions with |Effect| > {effect_threshold}%'
    if filter_str:
        main_title += f' (Filtered: {filter_str})'
    plt.suptitle(main_title, fontsize=16, fontweight='bold', y=0.98)

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\nSaved plot to {output_path}")

    plt.show()


def main():
    session_id = "All"

    import os
    save_dir = "/home/connorlab/Documents/plots/260120_0/estimshape/"
    os.makedirs(save_dir, exist_ok=True)
    output_path = os.path.join(save_dir, f'estim_effects_summary_{session_id}.png')

    # Example filters - uncomment/modify as needed
    condition_filter = {
        # 'shape': 'BiphasicWithInterphaseDelay',
        # 'trial_type': 'Hypothesized Shape',  # Only show Delta Shape trials
        # 'noise_chance': 0.9,  # Only show 50% noise
        # 'polarity': 'PositiveFirst',  # Only show positive polarity
        # 'num_channels': 3,  # Only show 9 channel stimulation
    }

    plot_estim_effects_summary(
        session_id,
        effect_threshold=15,
        n_threshold=10,
        output_path=output_path,
        condition_filter=condition_filter  # Pass the filter here
    )


if __name__ == '__main__':
    main()
import matplotlib.pyplot as plt
import numpy as np
from clat.util.connection import Connection
import json
from itertools import combinations


def analyze_condition_combinations(filter_conditions, output_path=None):
    """
    Analyze effect sizes by comparing different combinations of filter conditions.

    For each combination of filters, creates groups:
    - Match ALL filters
    - Match only some filters (one group per partial match)
    - Match NONE of the filters

    Args:
        filter_conditions: Dict of conditions to analyze, e.g. {'noise_chance': 0.9, 'shape': 'BiphasicWithInterphaseDelay'}
        output_path: Path to save the plot
    """
    # Read all data from EStimEffects table
    repo_conn = Connection("allen_data_repository")

    repo_conn.execute("""
                      SELECT session_id, conditions, effect_size
                      FROM EStimEffects
                      WHERE effect_size IS NOT NULL
                      """)

    column_names = [desc[0] for desc in repo_conn.my_cursor.description]
    results = repo_conn.fetch_all()

    if len(results) == 0:
        print("No data found in EStimEffects table")
        return

    # Parse results
    all_data = []
    for row in results:
        row_dict = dict(zip(column_names, row))
        row_dict['conditions_dict'] = json.loads(row_dict['conditions'])
        all_data.append(row_dict)

    print(f"Loaded {len(all_data)} condition combinations across all sessions")

    # Get unique sessions
    sessions = list(set([d['session_id'] for d in all_data]))
    print(f"Found {len(sessions)} sessions: {sessions}")

    # Generate all possible combinations of filter conditions (including individual ones)
    filter_keys = list(filter_conditions.keys())
    all_combinations = []

    # Include individual conditions and all multi-condition combinations
    for r in range(1, len(filter_keys) + 1):
        for combo in combinations(filter_keys, r):
            all_combinations.append(combo)

    print(f"\nAnalyzing {len(all_combinations)} filter combinations:")
    for combo in all_combinations:
        print(f"  {combo}")

    # For each combination, calculate group averages
    results_by_combination = []

    for combo_keys in all_combinations:
        # Create the filter subset for this combination
        combo_filter = {k: filter_conditions[k] for k in combo_keys}

        print(f"\n--- Analyzing combination: {combo_filter} ---")

        # For each session, categorize conditions into groups
        session_averages = {
            'match_all': [],
            'match_none': [],
        }

        # Create keys for partial matches (e.g., just noise, just shape)
        for partial_size in range(1, len(combo_keys)):
            for partial_combo in combinations(combo_keys, partial_size):
                key = f"match_{'||'.join(partial_combo)}"  # Use || as separator
                session_averages[key] = []

        for session_id in sessions:
            session_data = [d for d in all_data if d['session_id'] == session_id]

            # Categorize each condition
            groups = {key: [] for key in session_averages.keys()}

            for data_point in session_data:
                cond_dict = data_point['conditions_dict']

                # Check how many filters match
                matches = {k: (k in cond_dict and cond_dict[k] == v)
                           for k, v in combo_filter.items()}
                num_matches = sum(matches.values())

                if num_matches == len(combo_filter):
                    # Matches ALL
                    groups['match_all'].append(data_point['effect_size'])
                elif num_matches == 0:
                    # Matches NONE
                    groups['match_none'].append(data_point['effect_size'])
                else:
                    # Partial match - find which subset matches
                    for partial_size in range(1, len(combo_keys)):
                        for partial_combo in combinations(combo_keys, partial_size):
                            if all(matches[k] for k in partial_combo):
                                # Check this is the ONLY match (not a superset)
                                if sum(matches[k] for k in partial_combo) == num_matches:
                                    key = f"match_{'||'.join(partial_combo)}"  # Use || as separator
                                    groups[key].append(data_point['effect_size'])
                                    break

            # Average within this session for each group
            for group_key, values in groups.items():
                if len(values) > 0:
                    session_averages[group_key].append(np.mean(values))

        # Grand average across sessions
        grand_averages = {}
        std_errors = {}

        for group_key, session_vals in session_averages.items():
            if len(session_vals) > 0:
                grand_averages[group_key] = np.mean(session_vals)
                std_errors[group_key] = np.std(session_vals) / np.sqrt(len(session_vals))  # SEM
                print(
                    f"  {group_key}: {grand_averages[group_key]:.2f}% ± {std_errors[group_key]:.2f} (n={len(session_vals)} sessions)")
            else:
                grand_averages[group_key] = None
                std_errors[group_key] = None
                print(f"  {group_key}: No data")

        results_by_combination.append({
            'combo_filter': combo_filter,
            'combo_keys': combo_keys,
            'grand_averages': grand_averages,
            'std_errors': std_errors,
            'n_sessions': len(sessions)
        })

    # Plot results
    plot_combination_comparison(results_by_combination, filter_conditions, output_path)


def plot_combination_comparison(results_by_combination, filter_conditions, output_path=None):
    """
    Create bar plots comparing different filter combinations

    Args:
        results_by_combination: List of result dicts from analyze_condition_combinations
        filter_conditions: Original filter dict
        output_path: Path to save the plot
    """
    n_combinations = len(results_by_combination)

    # Create subplots - one per combination
    fig, axes = plt.subplots(n_combinations, 1, figsize=(12, 5 * n_combinations))

    if n_combinations == 1:
        axes = [axes]

    for idx, result in enumerate(results_by_combination):
        ax = axes[idx]

        combo_filter = result['combo_filter']
        combo_keys = result['combo_keys']
        grand_averages = result['grand_averages']
        std_errors = result['std_errors']

        # Prepare data for plotting
        group_labels = []
        means = []
        errors = []

        # Sort groups: match_all first, then partial matches, then match_none
        sorted_keys = []
        if 'match_all' in grand_averages and grand_averages['match_all'] is not None:
            sorted_keys.append('match_all')

        # Add partial matches
        partial_keys = [k for k in grand_averages.keys() if
                        k.startswith('match_') and k not in ['match_all', 'match_none']]
        sorted_keys.extend(sorted(partial_keys))

        if 'match_none' in grand_averages and grand_averages['match_none'] is not None:
            sorted_keys.append('match_none')

        for key in sorted_keys:
            if grand_averages[key] is not None:
                # Create readable label
                if key == 'match_all':
                    # Use "BOTH" for 2 conditions, "ALL" for more
                    prefix = 'BOTH' if len(combo_filter) == 2 else 'ALL'
                    label = f'{prefix}: ' + ', '.join([f"{k}={v}" for k, v in combo_filter.items()])
                elif key == 'match_none':
                    # Use "NEITHER" for 2 conditions, "NONE" for more
                    label = 'OTHER' if len(combo_filter) == 2 else 'OTHER'
                else:
                    # Extract which conditions matched
                    matched_keys = key.replace('match_', '').split('||')  # Split by ||

                    label = 'ONLY: ' + ', '.join([f"{k}={combo_filter[k]}" for k in matched_keys])

                group_labels.append(label)
                means.append(grand_averages[key])
                errors.append(std_errors[key])

        # Create bar plot
        x_pos = np.arange(len(group_labels))
        colors = ['green' if i == 0 else 'red' if i == len(group_labels) - 1 else 'orange'
                  for i in range(len(group_labels))]

        bars = ax.bar(x_pos, means, yerr=errors, capsize=5, color=colors, alpha=0.7, edgecolor='black')

        # Add value labels on bars
        for i, (bar, mean, err) in enumerate(zip(bars, means, errors)):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width() / 2., height + err + 0.5,
                    f'{mean:.1f}%',
                    ha='center', va='bottom', fontweight='bold', fontsize=10)

        # Formatting
        ax.set_xticks(x_pos)
        ax.set_xticklabels(group_labels, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel('Effect Size (EStim ON - OFF %)', fontsize=12)
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
        ax.grid(True, alpha=0.3, axis='y')

        # Title
        combo_str = ', '.join([f"{k}={v}" for k, v in combo_filter.items()])
        ax.set_title(f'Effect Size Comparison: {combo_str}', fontsize=14, fontweight='bold')

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\nSaved plot to {output_path}")

    plt.show()


def main():
    # Define the conditions to analyze
    filter_conditions = {
        'noise_chance': 1.0,
        # 'trial_type': "Hypothesized Shape",
        # 'num_channels': 3.0,
        # 'polarity': "PositiveFirst",
        # 'shape': 'BiphasicWithInterphaseDelay'
    }

    import os
    save_dir = "/home/connorlab/Documents/plots/260120_0/estimshape/"
    os.makedirs(save_dir, exist_ok=True)

    # Create filename from conditions
    cond_str = '_'.join([f"{k}_{v}" for k, v in filter_conditions.items()])
    output_path = os.path.join(save_dir, f'condition_comparison_{cond_str}.png')

    analyze_condition_combinations(filter_conditions, output_path=output_path)


if __name__ == '__main__':
    main()
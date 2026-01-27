import matplotlib.pyplot as plt
import numpy as np
from clat.util.connection import Connection
import json
from itertools import combinations


def analyze_condition_combinations(filter_conditions, output_path=None, session_ids=None, exclude_groups=None):
    """
    Analyze effect sizes by comparing different combinations of filter conditions.

    For each combination of filters, creates groups:
    - Match ALL filters
    - Match only some filters (one group per partial match)
    - Match NONE of the filters

    Args:
        filter_conditions: Dict of conditions to analyze, e.g. {'noise_chance': 0.9, 'shape': 'BiphasicWithInterphaseDelay'}
        output_path: Path to save the plot
        session_ids: Single session ID (string) or list of session IDs to include, or None for all sessions
        exclude_groups: List of group keys to exclude from plots, e.g. ['match_none', 'match_all']
    """
    # Read all data from EStimEffects table
    repo_conn = Connection("allen_data_repository")

    # Handle session_ids parameter
    if session_ids is not None:
        if isinstance(session_ids, str):
            session_ids = [session_ids]

        placeholders = ','.join(['%s'] * len(session_ids))
        query = f"""
            SELECT session_id, conditions, effect_size
            FROM EStimEffects
            WHERE effect_size IS NOT NULL
            AND session_id IN ({placeholders})
        """
        repo_conn.execute(query, tuple(session_ids))
    else:
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

    all_data = []
    for row in results:
        row_dict = dict(zip(column_names, row))
        row_dict['conditions_dict'] = json.loads(row_dict['conditions'])
        all_data.append(row_dict)

    print(f"Loaded {len(all_data)} condition combinations across all sessions")

    sessions = list(set([d['session_id'] for d in all_data]))
    print(f"Found {len(sessions)} sessions: {sessions}")

    filter_keys = list(filter_conditions.keys())
    all_combinations = []

    for r in range(1, len(filter_keys) + 1):
        for combo in combinations(filter_keys, r):
            all_combinations.append(combo)

    print(f"\nAnalyzing {len(all_combinations)} filter combinations:")
    for combo in all_combinations:
        print(f"  {combo}")

    results_by_combination = []

    for combo_keys in all_combinations:
        combo_filter = {k: filter_conditions[k] for k in combo_keys}

        print(f"\n--- Analyzing combination: {combo_filter} ---")

        session_averages = {
            'match_all': [],
            'match_none': [],
        }

        session_condition_groups = {
            'match_all': [],
            'match_none': [],
        }

        for partial_size in range(1, len(combo_keys)):
            for partial_combo in combinations(combo_keys, partial_size):
                key = f"match_{'||'.join(partial_combo)}"
                session_averages[key] = []
                session_condition_groups[key] = []

        for session_id in sessions:
            session_data = [d for d in all_data if d['session_id'] == session_id]

            groups = {key: [] for key in session_averages.keys()}
            condition_tracking = {key: [] for key in session_averages.keys()}

            for data_point in session_data:
                cond_dict = data_point['conditions_dict']

                matches = {k: (k in cond_dict and cond_dict[k] == v)
                           for k, v in combo_filter.items()}
                num_matches = sum(matches.values())

                if num_matches == len(combo_filter):
                    groups['match_all'].append(data_point['effect_size'])
                    condition_tracking['match_all'].append({
                        'session_id': session_id,
                        'conditions': data_point['conditions']
                    })
                elif num_matches == 0:
                    groups['match_none'].append(data_point['effect_size'])
                    condition_tracking['match_none'].append({
                        'session_id': session_id,
                        'conditions': data_point['conditions']
                    })
                else:
                    for partial_size in range(1, len(combo_keys)):
                        for partial_combo in combinations(combo_keys, partial_size):
                            if all(matches[k] for k in partial_combo):
                                if sum(matches[k] for k in partial_combo) == num_matches:
                                    key = f"match_{'||'.join(partial_combo)}"
                                    groups[key].append(data_point['effect_size'])
                                    condition_tracking[key].append({
                                        'session_id': session_id,
                                        'conditions': data_point['conditions']
                                    })
                                    break

            for group_key, values in groups.items():
                if len(values) > 0:
                    session_averages[group_key].append(np.mean(values))
                    session_condition_groups[group_key].append(condition_tracking[group_key])

        grand_averages = {}
        std_errors = {}
        p_values = {}

        for group_key in session_averages.keys():
            session_vals = session_averages[group_key]

            if len(session_vals) > 0:
                grand_averages[group_key] = np.mean(session_vals)
                std_errors[group_key] = np.std(session_vals) / np.sqrt(len(session_vals))

                grand_null_dist = compute_grand_null_distribution(
                    session_condition_groups[group_key],
                    sessions
                )

                if grand_null_dist is not None and len(grand_null_dist) > 0:
                    p_values[group_key] = calculate_p_value_two_tailed(
                        grand_averages[group_key],
                        grand_null_dist
                    )
                    sig_marker = get_significance_marker(p_values[group_key])
                    print(f"  {group_key}: {grand_averages[group_key]:.2f}% ± {std_errors[group_key]:.2f} "
                          f"(n={len(session_vals)} sessions, p={p_values[group_key]:.4f} {sig_marker})")
                else:
                    p_values[group_key] = None
                    print(f"  {group_key}: {grand_averages[group_key]:.2f}% ± {std_errors[group_key]:.2f} "
                          f"(n={len(session_vals)} sessions, no null dist)")
            else:
                grand_averages[group_key] = None
                std_errors[group_key] = None
                p_values[group_key] = None
                print(f"  {group_key}: No data")

        results_by_combination.append({
            'combo_filter': combo_filter,
            'combo_keys': combo_keys,
            'grand_averages': grand_averages,
            'std_errors': std_errors,
            'p_values': p_values,
            'n_sessions': len(sessions)
        })

    plot_combination_comparison(results_by_combination, filter_conditions, output_path, exclude_groups)


def compute_grand_null_distribution(session_condition_groups, sessions):
    """
    Compute grand null distribution by aggregating across sessions.

    Args:
        session_condition_groups: List of lists, one per session, each containing
                                 dicts with 'session_id' and 'conditions'
        sessions: List of all session IDs

    Returns:
        Array of permuted grand averages (1000 values)
    """
    if len(session_condition_groups) == 0:
        return None

    repo_conn = Connection("allen_data_repository")

    session_null_dists = []

    for session_conditions in session_condition_groups:
        if len(session_conditions) == 0:
            continue

        condition_null_dists = []

        for cond_info in session_conditions:
            session_id = cond_info['session_id']
            conditions_json = cond_info['conditions']

            repo_conn.execute("""
                              SELECT null_distribution, n_permutations
                              FROM EStimPermutationTests
                              WHERE session_id = %s
                                AND conditions = %s
                              """, (session_id, conditions_json))

            result = repo_conn.fetch_all()

            if result and result[0][0]:
                null_dist = json.loads(result[0][0])
                condition_null_dists.append(np.array(null_dist))

        if len(condition_null_dists) == 0:
            continue

        condition_null_array = np.array(condition_null_dists)
        session_null_dist = np.mean(condition_null_array, axis=0)
        session_null_dists.append(session_null_dist)

    if len(session_null_dists) == 0:
        return None

    session_null_array = np.array(session_null_dists)
    grand_null_dist = np.mean(session_null_array, axis=0)

    return grand_null_dist


def calculate_p_value_two_tailed(observed, null_distribution):
    """Calculate two-tailed p-value"""
    null_array = np.array(null_distribution)
    p_value = np.mean(np.abs(null_array) >= np.abs(observed))
    return float(p_value)


def calculate_p_value_greater(observed, null_distribution):
    """Calculate one-tailed p-value (greater than)"""
    null_array = np.array(null_distribution)
    p_value = np.mean(null_array >= observed)
    return float(p_value)


def get_significance_marker(p_value):
    """Convert p-value to significance marker"""
    if p_value is None:
        return ''
    elif p_value < 0.001:
        return '***'
    elif p_value < 0.01:
        return '**'
    elif p_value < 0.05:
        return '*'
    else:
        return 'ns'


def plot_combination_comparison(results_by_combination, filter_conditions, output_path=None, exclude_groups=None):
    """
    Create bar plots comparing different filter combinations

    Args:
        results_by_combination: List of result dicts from analyze_condition_combinations
        filter_conditions: Original filter dict
        output_path: Path to save the plot
        exclude_groups: List of group keys to exclude from plots (not applied when only 2 bars exist)
    """
    if exclude_groups is None:
        exclude_groups = []

    n_combinations = len(results_by_combination)

    fig, axes = plt.subplots(n_combinations, 1, figsize=(12, 6.5 * n_combinations))

    if n_combinations == 1:
        axes = [axes]

    for idx, result in enumerate(results_by_combination):
        ax = axes[idx]

        combo_filter = result['combo_filter']
        combo_keys = result['combo_keys']
        grand_averages = result['grand_averages']
        std_errors = result['std_errors']
        p_values = result['p_values']

        group_labels = []
        means = []
        errors = []
        p_vals = []
        group_keys = []  # Track which group key each bar corresponds to

        sorted_keys = []
        if 'match_all' in grand_averages and grand_averages['match_all'] is not None:
            sorted_keys.append('match_all')

        partial_keys = [k for k in grand_averages.keys() if
                        k.startswith('match_') and k not in ['match_all', 'match_none']]
        sorted_keys.extend(sorted(partial_keys))

        if 'match_none' in grand_averages and grand_averages['match_none'] is not None:
            sorted_keys.append('match_none')

        # Count total available groups (before exclusions)
        total_groups = len([k for k in sorted_keys if grand_averages[k] is not None])

        # If only 2 groups exist, ignore exclusions for this subplot
        apply_exclusions = total_groups > 2

        for key in sorted_keys:
            # Only apply exclusions if we have more than 2 groups
            if apply_exclusions and key in exclude_groups:
                continue

            if grand_averages[key] is not None:
                if key == 'match_all':
                    prefix = 'BOTH' if len(combo_filter) == 2 else 'ALL'
                    label = f'{prefix}: ' + ', '.join([f"{k}={v}" for k, v in combo_filter.items()])
                elif key == 'match_none':
                    unmatched_parts = [f"NOT {k}={combo_filter[k]}" for k in combo_keys]
                    label = ', '.join(unmatched_parts)
                else:
                    matched_keys = key.replace('match_', '').split('||')

                    matched_parts = [f"{k}={combo_filter[k]}" for k in matched_keys]
                    unmatched_keys = [k for k in combo_keys if k not in matched_keys]
                    unmatched_parts = [f"NOT {k}={combo_filter[k]}" for k in unmatched_keys]

                    label = ', '.join(matched_parts + unmatched_parts)

                group_labels.append(label)
                means.append(grand_averages[key])
                errors.append(std_errors[key])
                p_vals.append(p_values.get(key, None))
                group_keys.append(key)  # Store the original key

        if len(means) == 0:
            print(f"Warning: No groups to plot for combination {combo_filter}")
            continue

        x_pos = np.arange(len(group_labels))

        # Color based on actual group type, not position
        colors = []
        for key in group_keys:
            if key == 'match_all':
                colors.append('green')
            elif key == 'match_none':
                colors.append('red')
            else:  # Partial matches
                colors.append('orange')

        bars = ax.bar(x_pos, means, yerr=errors, capsize=5, color=colors, alpha=0.7, edgecolor='black')

        max_height = max([m + e for m, e in zip(means, errors)])
        min_height = min([m - e for m, e in zip(means, errors)])

        y_range = max_height - min_height
        ax.set_ylim(min_height - 0.1 * y_range, max_height + 0.2 * y_range)

        final_y_range = ax.get_ylim()[1] - ax.get_ylim()[0]

        for i, (bar, mean, err, p_val) in enumerate(zip(bars, means, errors, p_vals)):
            height = bar.get_height()

            ax.text(bar.get_x() + bar.get_width() / 2., height + err + 0.015 * final_y_range,
                    f'{mean:.1f}%',
                    ha='center', va='bottom', fontweight='bold', fontsize=10)

            if p_val is not None:
                p_text = f'p={p_val:.3f}' if p_val >= 0.001 else 'p<0.001'
                sig_marker = get_significance_marker(p_val)
                if sig_marker != 'ns':
                    p_text = f'{sig_marker} {p_text}'

                ax.text(bar.get_x() + bar.get_width() / 2., height + err + 0.05 * final_y_range,
                        p_text,
                        ha='center', va='bottom', fontsize=9, style='italic')

        ax.set_xticks(x_pos)
        ax.set_xticklabels(group_labels, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel('Effect Size (EStim ON - OFF %)', fontsize=12)
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
        ax.grid(True, alpha=0.3, axis='y')

        combo_str = ', '.join([f"{k}={v}" for k, v in combo_filter.items()])
        ax.set_title(f'Effect Size Comparison: {combo_str}',
                     fontsize=14, fontweight='bold')

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\nSaved plot to {output_path}")

    plt.show()


def main():
    filter_conditions = {
        'noise_chance': 0.9,
        # 'trial_type': "Hypothesized Shape",
        # 'num_channels': 3.0,
        # 'polarity': "PositiveFirst",
        'shape': 'BiphasicWithInterphaseDelay'
    }
    # session_ids = "260115_0"
    session_ids = None
    exclude_groups = ['match_none']

    import os
    save_dir = "/home/connorlab/Documents/plots/260120_0/estimshape/"
    os.makedirs(save_dir, exist_ok=True)

    cond_str = '_'.join([f"{k}_{v}" for k, v in filter_conditions.items()])
    if session_ids:
        sess_str = '_'.join(session_ids) if isinstance(session_ids, list) else session_ids
        output_path = os.path.join(save_dir, f'condition_comparison_{cond_str}_{sess_str}.png')
    else:
        output_path = os.path.join(save_dir, f'condition_comparison_{cond_str}.png')

    analyze_condition_combinations(filter_conditions, output_path=output_path, session_ids=session_ids, exclude_groups=exclude_groups)


if __name__ == '__main__':
    main()
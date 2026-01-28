import matplotlib.pyplot as plt
import numpy as np
from clat.util.connection import Connection
import json
from itertools import combinations


def analyze_condition_combinations(filter_conditions, output_path=None, session_ids=None, exclude_groups=None,
                                   session_filters=None, session_grouping=None):
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
        session_filters: Dict of {field_name: lambda_function} to filter sessions from EStimShapeSessionData,
                        e.g. {'cluster_size': lambda x: x >= 2} - excludes sessions that don't pass
        session_grouping: Dict defining how to group sessions for comparison:
                         {'field': 'cluster_size',
                          'groups': {
                              'High Cluster (≥2)': lambda x: x >= 2,
                              'Low Cluster (<2)': lambda x: x < 2
                          }}
    """
    # Read all data from EStimEffects table
    repo_conn = Connection("allen_data_repository")

    # Get session-level data
    repo_conn.execute("""
                      SELECT session_id, cluster_size, avg_distance_scaled_correlation, lineage_score
                      FROM EStimShapeSessionData
                      """)

    session_data_results = repo_conn.fetch_all()

    # Build dict of session metrics
    session_metrics = {}
    for row in session_data_results:
        sess_id, cluster_size, avg_dist_corr, lineage_score = row
        session_metrics[sess_id] = {
            'cluster_size': cluster_size,
            'avg_distance_scaled_correlation': avg_dist_corr,
            'lineage_score': lineage_score
        }

    # Apply session-level filters if provided (excludes sessions)
    filtered_session_ids = None
    if session_filters is not None:
        print("\n=== Applying Session-Level Filters (Exclusion) ===")

        if len(session_metrics) == 0:
            print("Warning: No sessions found in EStimShapeSessionData table")
            filtered_session_ids = []
        else:
            print(f"Found {len(session_metrics)} sessions in EStimShapeSessionData")

            # Apply lambda filters
            filtered_session_ids = []
            for sess_id, metrics in session_metrics.items():
                passes_all_filters = True

                for field_name, filter_func in session_filters.items():
                    if field_name not in metrics:
                        print(f"Warning: Field '{field_name}' not found in session data")
                        passes_all_filters = False
                        break

                    field_value = metrics[field_name]

                    try:
                        if not filter_func(field_value):
                            passes_all_filters = False
                            break
                    except Exception as e:
                        print(f"Warning: Filter function failed for {sess_id}.{field_name}={field_value}: {e}")
                        passes_all_filters = False
                        break

                if passes_all_filters:
                    filtered_session_ids.append(sess_id)

            print(f"Sessions passing filters: {len(filtered_session_ids)}/{len(session_metrics)}")
            for field_name in session_filters.keys():
                print(f"  Filter on '{field_name}'")

            # Print which sessions passed and their values
            if len(filtered_session_ids) > 0:
                print(f"\nSessions that passed filters:")
                for sess_id in sorted(filtered_session_ids):
                    if sess_id in session_metrics:
                        metrics_str = ', '.join([f"{k}={v}" for k, v in session_metrics[sess_id].items()])
                        print(f"  {sess_id}: {metrics_str}")

        # If session_ids was also provided, take intersection
        if session_ids is not None:
            if isinstance(session_ids, str):
                session_ids = [session_ids]

            filtered_session_ids = [s for s in filtered_session_ids if s in session_ids]
            print(f"After intersecting with provided session_ids: {len(filtered_session_ids)} sessions")

        # Use filtered sessions as the session_ids for the rest of the analysis
        session_ids = filtered_session_ids if len(filtered_session_ids) > 0 else None

        if session_ids is None or len(session_ids) == 0:
            print("No sessions pass the filters. Exiting.")
            return

    # Apply session grouping if provided (creates comparison groups)
    session_group_assignments = {}
    group_names = ['All Sessions']  # Default group

    if session_grouping is not None:
        print("\n=== Applying Session Grouping (Comparison) ===")

        field_name = session_grouping['field']
        group_definitions = session_grouping['groups']
        group_names = list(group_definitions.keys())

        print(f"Grouping sessions by '{field_name}' into {len(group_names)} groups:")
        for group_name in group_names:
            print(f"  - {group_name}")

        if len(session_metrics) == 0:
            print("Warning: No sessions found in EStimShapeSessionData table")
        else:
            # Assign each session to a group
            for sess_id, metrics in session_metrics.items():
                if field_name not in metrics:
                    print(f"Warning: Field '{field_name}' not found for session {sess_id}")
                    continue

                field_value = metrics[field_name]

                for group_name, group_func in group_definitions.items():
                    try:
                        if group_func(field_value):
                            session_group_assignments[sess_id] = group_name
                            break
                    except Exception as e:
                        print(f"Warning: Group function failed for {sess_id}.{field_name}={field_value}: {e}")

            # Print group assignments
            for group_name in group_names:
                group_sessions = [s for s, g in session_group_assignments.items() if g == group_name]
                print(f"\n{group_name}: {len(group_sessions)} sessions")
                for sess_id in sorted(group_sessions):
                    if sess_id in session_metrics:
                        metrics_str = ', '.join([f"{k}={v}" for k, v in session_metrics[sess_id].items()])
                        print(f"  {sess_id}: {metrics_str}")

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

    # Run analysis separately for each session group
    results_by_group = {}

    for group_name in group_names:
        print(f"\n{'=' * 60}")
        print(f"ANALYZING GROUP: {group_name}")
        print(f"{'=' * 60}")

        # Get sessions for this group
        if session_grouping is None or group_name == 'All Sessions':
            # No grouping - use all sessions
            group_sessions = sessions
        else:
            # Filter to sessions in this group
            group_sessions = [s for s in sessions if session_group_assignments.get(s) == group_name]

        print(f"Sessions in this group: {len(group_sessions)}")
        if len(group_sessions) > 0:
            print(f"  {sorted(group_sessions)}")
        if len(group_sessions) == 0:
            print(f"Skipping group '{group_name}' - no sessions")
            continue

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

            for session_id in group_sessions:  # Only use sessions in this group
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
                        group_sessions  # Use group sessions for null dist
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
                'n_sessions': len(group_sessions)
            })

        results_by_group[group_name] = results_by_combination

    plot_combination_comparison(results_by_group, filter_conditions, output_path, exclude_groups, group_names)


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


def plot_combination_comparison(results_by_group, filter_conditions, output_path=None, exclude_groups=None,
                                group_names=None):
    """
    Create bar plots comparing different filter combinations, with optional session group comparison

    Args:
        results_by_group: Dict of {group_name: [result dicts from analyze_condition_combinations]}
        filter_conditions: Original filter dict
        output_path: Path to save the plot
        exclude_groups: List of group keys to exclude from plots (not applied when only 2 bars exist)
        group_names: List of group names (for ordering)
    """
    if exclude_groups is None:
        exclude_groups = []

    if group_names is None:
        group_names = list(results_by_group.keys())

    # Get number of combinations from first group
    first_group = group_names[0]
    n_combinations = len(results_by_group[first_group])

    n_groups = len(group_names)

    fig, axes = plt.subplots(n_combinations, 1, figsize=(12, 6.5 * n_combinations))

    if n_combinations == 1:
        axes = [axes]

    for combo_idx in range(n_combinations):
        ax = axes[combo_idx]

        # Get combo info from first group (should be same across all groups)
        result = results_by_group[first_group][combo_idx]
        combo_filter = result['combo_filter']
        combo_keys = result['combo_keys']

        # Collect all match keys across all groups
        all_match_keys = set()
        for group_name in group_names:
            result = results_by_group[group_name][combo_idx]
            all_match_keys.update(result['grand_averages'].keys())

        # Sort match keys
        sorted_keys = []
        if 'match_all' in all_match_keys:
            sorted_keys.append('match_all')

        partial_keys = [k for k in all_match_keys if
                        k.startswith('match_') and k not in ['match_all', 'match_none']]
        sorted_keys.extend(sorted(partial_keys))

        if 'match_none' in all_match_keys:
            sorted_keys.append('match_none')

        # Count total available groups (before exclusions)
        total_groups = len(sorted_keys)
        apply_exclusions = total_groups > 2

        # Filter sorted_keys based on exclusions
        if apply_exclusions:
            sorted_keys = [k for k in sorted_keys if k not in exclude_groups]

        if len(sorted_keys) == 0:
            print(f"Warning: No match groups to plot for combination {combo_filter}")
            continue

        # Create grouped bar positions
        n_match_groups = len(sorted_keys)
        bar_width = 0.8 / n_groups if n_groups > 1 else 0.8
        x_base = np.arange(n_match_groups)

        # Define color schemes for session groups
        # Each group gets a different color palette
        color_schemes = [
            {'match_all': '#2E7D32', 'match_none': '#C62828', 'partial': '#EF6C00'},
            # Dark green, dark red, dark orange
            {'match_all': '#66BB6A', 'match_none': '#EF5350', 'partial': '#FFA726'},
            # Light green, light red, light orange
            {'match_all': '#1B5E20', 'match_none': '#B71C1C', 'partial': '#E65100'},
            # Very dark green, very dark red, very dark orange
            {'match_all': '#81C784', 'match_none': '#E57373', 'partial': '#FFB74D'},
            # Very light green, very light red, very light orange
        ]

        # Plot bars for each session group
        all_max_heights = []
        all_min_heights = []

        for group_idx, group_name in enumerate(group_names):
            result = results_by_group[group_name][combo_idx]
            grand_averages = result['grand_averages']
            std_errors = result['std_errors']
            p_values = result['p_values']

            # Select color scheme for this group
            color_scheme = color_schemes[group_idx % len(color_schemes)]

            means = []
            errors = []
            p_vals = []
            colors = []

            for match_key in sorted_keys:
                if grand_averages.get(match_key) is not None:
                    means.append(grand_averages[match_key])
                    errors.append(std_errors[match_key])
                    p_vals.append(p_values.get(match_key, None))

                    # Color based on match type using group's color scheme
                    if match_key == 'match_all':
                        colors.append(color_scheme['match_all'])
                    elif match_key == 'match_none':
                        colors.append(color_scheme['match_none'])
                    else:
                        colors.append(color_scheme['partial'])
                else:
                    means.append(0)
                    errors.append(0)
                    p_vals.append(None)
                    colors.append('lightgray')

            # Calculate x positions for this group
            if n_groups > 1:
                x_offset = (group_idx - (n_groups - 1) / 2) * bar_width
                x_pos = x_base + x_offset
                alpha = 0.7
            else:
                x_pos = x_base
                alpha = 0.7

            # Plot bars
            show_legend = n_groups > 1 and group_names != ['All Sessions']
            bars = ax.bar(x_pos, means, width=bar_width, yerr=errors, capsize=5,
                          color=colors, alpha=alpha, edgecolor='black',
                          label=group_name if show_legend else None)

            # Track max/min heights across all groups for ylim calculation
            if means:
                max_height = max([m + e for m, e in zip(means, errors)])
                min_height = min([m - e for m, e in zip(means, errors)])
                all_max_heights.append(max_height)
                all_min_heights.append(min_height)

        # Set y-axis limits with extra space for labels (ONLY CHANGE FROM ORIGINAL)
        if all_max_heights and all_min_heights:
            overall_max = max(all_max_heights)
            overall_min = min(all_min_heights)
            y_range = overall_max - overall_min
            ax.set_ylim(overall_min - 0.1 * y_range, overall_max + 0.35 * y_range)

        # Get final y-axis range for consistent label positioning
        final_y_range = ax.get_ylim()[1] - ax.get_ylim()[0]

        # Add labels to all bars using consistent spacing
        bar_idx = 0
        for group_idx, group_name in enumerate(group_names):
            result = results_by_group[group_name][combo_idx]
            grand_averages = result['grand_averages']
            std_errors = result['std_errors']
            p_values = result['p_values']

            means = []
            errors = []
            p_vals = []

            for match_key in sorted_keys:
                if grand_averages.get(match_key) is not None:
                    means.append(grand_averages[match_key])
                    errors.append(std_errors[match_key])
                    p_vals.append(p_values.get(match_key, None))
                else:
                    means.append(0)
                    errors.append(0)
                    p_vals.append(None)

            for i, (mean, err, p_val) in enumerate(zip(means, errors, p_vals)):
                if mean == 0:  # Skip empty bars
                    bar_idx += 1
                    continue

                bar = ax.patches[bar_idx]
                height = bar.get_height()

                # Value label
                ax.text(bar.get_x() + bar.get_width() / 2., height + err + 0.015 * final_y_range,
                        f'{mean:.1f}%',
                        ha='center', va='bottom', fontweight='bold', fontsize=9)

                # P-value label
                if p_val is not None:
                    p_text = f'p={p_val:.3f}' if p_val >= 0.001 else 'p<0.001'
                    sig_marker = get_significance_marker(p_val)
                    if sig_marker != 'ns':
                        p_text = f'{sig_marker} {p_text}'

                    ax.text(bar.get_x() + bar.get_width() / 2., height + err + 0.05 * final_y_range,
                            p_text,
                            ha='center', va='bottom', fontsize=7, style='italic')

                bar_idx += 1

        # Format x-axis labels
        x_labels = []
        for key in sorted_keys:
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
            x_labels.append(label)

        ax.set_xticks(x_base)
        ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel('Effect Size (EStim ON - OFF %)', fontsize=12)
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
        ax.grid(True, alpha=0.3, axis='y')

        combo_str = ', '.join([f"{k}={v}" for k, v in combo_filter.items()])
        title = f'Effect Size Comparison: {combo_str}'
        if n_groups > 1 and group_names != ['All Sessions']:
            title += f' | Grouped by Session'
        ax.set_title(title, fontsize=14, fontweight='bold')

        # Add legend if multiple groups (and not just 'All Sessions')
        if n_groups > 1 and group_names != ['All Sessions']:
            ax.legend(loc='upper left', fontsize=10)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\nSaved plot to {output_path}")

    plt.show()


def main():
    # Example 1: Basic filter conditions
    filter_conditions = {
        'noise_chance': 0.9,
        # 'trial_type': "Hypothesized Shape",
        'num_channels': 3.0,
        # 'polarity': "PositiveFirst",
        # 'shape': 'BiphasicWithInterphaseDelay'
    }

    # Example 2: Session-level filters (excludes sessions that don't pass)
    session_filters = None
    # session_filters = {
    #     'cluster_size': lambda x: x > 6,  # Exclude sessions with no clusters
    # }

    # Example 3: Session grouping (compares groups side-by-side)
    session_grouping = None
    # session_grouping = {
    #     'field': 'cluster_size',
    #     'groups': {
    #         'Large Cluster': lambda x: x >= 7,
    #         'Small Cluster': lambda x: x < 7
    #     }
    # }
    session_grouping = {
        'field': 'lineage_score',
        'groups': {
            'Large Confidence': lambda x: x >= 25.0,
            'Small Confidence': lambda x: x < 25.0
        }
    }
    # Set to None to disable grouping


    session_ids = None
    # session_ids = "260115_0"
    exclude_groups = []
    # exclude_groups = ['match_none']

    import os
    save_dir = "/home/connorlab/Documents/plots/260120_0/estimshape/"
    os.makedirs(save_dir, exist_ok=True)

    cond_str = '_'.join([f"{k}_{v}" for k, v in filter_conditions.items()])
    if session_ids:
        sess_str = '_'.join(session_ids) if isinstance(session_ids, list) else session_ids
        output_path = os.path.join(save_dir, f'condition_comparison_{cond_str}_{sess_str}.png')
    else:
        output_path = os.path.join(save_dir, f'condition_comparison_{cond_str}.png')

    # Call with session_filters and/or session_grouping parameters
    analyze_condition_combinations(
        filter_conditions,
        output_path=output_path,
        session_ids=session_ids,
        exclude_groups=exclude_groups,
        session_filters=session_filters,  # Exclude sessions that don't pass
        session_grouping=session_grouping  # Compare groups side-by-side
    )


if __name__ == '__main__':
    main()
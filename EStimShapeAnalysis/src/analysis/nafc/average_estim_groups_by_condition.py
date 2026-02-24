import matplotlib.pyplot as plt
import numpy as np
from clat.util.connection import Connection
import json
from itertools import combinations, product as iter_product

# =============================================================================
# Enumerated mode helpers (for list-valued filter_conditions)
# =============================================================================

def _is_enumerated_mode(filter_conditions):
    """Check if any filter values are lists, indicating enumerated bar mode."""
    return any(isinstance(v, list) for v in filter_conditions.values())


def _build_bar_specs(filter_conditions):
    """
    Build bar specifications from filter conditions with list values.

    For list values: one category per value in the list.
    For scalar values: match and non-match categories.
    Cross-product of all categories gives the full set of bars.

    Returns:
        list of (bar_key, bar_label, match_criteria) tuples where:
        - bar_key: internal identifier string
        - bar_label: display label for the bar
        - match_criteria: list of (key, op, value) tuples for matching
    """
    keys_order = list(filter_conditions.keys())

    # Build categories per key
    categories_per_key = []
    for key in keys_order:
        value = filter_conditions[key]
        if isinstance(value, list):
            # List: one category per listed value
            categories_per_key.append([(key, '==', v) for v in value])
        else:
            # Scalar: match and non-match
            categories_per_key.append([
                (key, '==', value),
                (key, '!=', value),
            ])

    # Cross product of all categories
    bar_specs = []
    for combo in iter_product(*categories_per_key):
        bar_key_parts = []
        bar_label_parts = []

        for key, op, value in combo:
            if op == '==':
                bar_key_parts.append(f"{key}={value}")
                bar_label_parts.append(f"{key}={value}")
            else:
                bar_key_parts.append(f"{key}!={value}")
                bar_label_parts.append(f"NOT {key}={value}")

        bar_key = '||'.join(bar_key_parts)
        bar_label = ', '.join(bar_label_parts)
        bar_specs.append((bar_key, bar_label, list(combo)))

    return bar_specs


def _classify_data_point_enumerated(cond_dict, bar_specs, filter_conditions):
    """
    Classify a data point into one of the bar specs or 'non_match'.

    For list keys: the value must be one of the listed values (otherwise -> non_match).
    For scalar keys: match or non-match per bar_spec.

    Returns the bar_key or 'non_match'.
    """
    # First: for list keys, the value must be in the list at all
    for key, value in filter_conditions.items():
        if isinstance(value, list):
            if key not in cond_dict or cond_dict[key] not in value:
                return 'non_match'

    # Find which bar_spec matches
    for bar_key, bar_label, criteria in bar_specs:
        matches = True
        for key, op, value in criteria:
            if key not in cond_dict:
                matches = False
                break
            if op == '==' and cond_dict[key] != value:
                matches = False
                break
            if op == '!=' and cond_dict[key] == value:
                matches = False
                break
        if matches:
            return bar_key

    return 'non_match'


# =============================================================================
# Main analysis
# =============================================================================

def main():
    # Example 1: Basic filter conditions

    # 260115_0 single plot
    filter_conditions = {
        'noise_chance': [0.9, 1.0],
        # 'trial_type': "Hypothesized Shape",
        # 'polarity': ["PositiveFirst", "NegativeFirst"],
        # 'shape': 'BiphasicWithInterphaseDelay'
    }

    # Required conditions: global data filter — all plotted data must match these.
    # These do NOT generate their own bars.
    required_conditions = {
        # 'num_channels': 3.0,
    }
    # required_conditions = None  # Set to None to disable

    # Example 2: Session-level filters (excludes sessions that don't pass)
    session_filters = None
    # session_filters = {
    # 'lineage_score': lambda x: x > 0.85,  # Exclude sessions with no clusters
    # }

    # Example 3: Session grouping (compares groups side-by-side)
    session_grouping = None

    session_ids = None
    # session_ids = "260115_0"
    exclude_groups = []

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
        session_filters=session_filters,
        session_grouping=session_grouping,
        required_conditions=required_conditions
    )


def analyze_condition_combinations(filter_conditions, output_path=None, session_ids=None, exclude_groups=None,
                                   session_filters=None, session_grouping=None, required_conditions=None):
    """
    Analyze effect sizes by comparing different combinations of filter conditions.

    Supports two modes:
    1. Combination mode (all scalar values): Creates groups for each subset of matching filters.
    2. Enumerated mode (any list values): Creates one bar per value (cross-product for multiple keys),
       plus a non-match bar for leftovers.

    Args:
        filter_conditions: Dict of conditions to analyze.
            Scalar values: e.g. {'noise_chance': 0.9, 'polarity': 'Anodic'}
            List values:   e.g. {'noise_chance': [0.9, 1.0]} or {'noise_chance': [0.9, 1.0], 'polarity': 'Anodic'}
        output_path: Path to save the plot
        session_ids: Single session ID (string) or list of session IDs to include, or None for all sessions
        exclude_groups: List of group keys to exclude from plots
        session_filters: Dict of {field_name: lambda_function} to filter sessions from EStimShapeSessionData
        session_grouping: Dict defining how to group sessions for comparison
        required_conditions: Dict of conditions that ALL data must match (global filter, no bars generated)
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

            if len(filtered_session_ids) > 0:
                print(f"\nSessions that passed filters:")
                for sess_id in sorted(filtered_session_ids):
                    if sess_id in session_metrics:
                        metrics_str = ', '.join([f"{k}={v}" for k, v in session_metrics[sess_id].items()])
                        print(f"  {sess_id}: {metrics_str}")

        if session_ids is not None:
            if isinstance(session_ids, str):
                session_ids = [session_ids]

            filtered_session_ids = [s for s in filtered_session_ids if s in session_ids]
            print(f"After intersecting with provided session_ids: {len(filtered_session_ids)} sessions")

        session_ids = filtered_session_ids if len(filtered_session_ids) > 0 else None

        if session_ids is None or len(session_ids) == 0:
            print("No sessions pass the filters. Exiting.")
            return

    # Apply session grouping if provided
    session_group_assignments = {}
    group_names = ['All Sessions']

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

            for group_name in group_names:
                group_sessions = [s for s, g in session_group_assignments.items() if g == group_name]
                print(f"\n{group_name}: {len(group_sessions)} sessions")
                for sess_id in sorted(group_sessions):
                    if sess_id in session_metrics:
                        metrics_str = ', '.join([f"{k}={v}" for k, v in session_metrics[sess_id].items()])
                        print(f"  {sess_id}: {metrics_str}")

    # Retrieve data from EStimEffects
    if session_ids is not None:
        if isinstance(session_ids, str):
            session_ids = [session_ids]

        placeholders = ','.join(['%s'] * len(session_ids))
        query = f"""
            SELECT session_id, conditions, effect_size, 
                   estim_on_pct_hypothesized, estim_off_pct_hypothesized
            FROM EStimEffects
            WHERE effect_size IS NOT NULL
            AND session_id IN ({placeholders})
        """
        repo_conn.execute(query, tuple(session_ids))
    else:
        repo_conn.execute("""
                          SELECT session_id,
                                 conditions,
                                 effect_size,
                                 estim_on_pct_hypothesized,
                                 estim_off_pct_hypothesized
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

    # Apply required_conditions as a global filter
    if required_conditions is not None and len(required_conditions) > 0:
        before_count = len(all_data)
        filtered_data = []
        for data_point in all_data:
            cond_dict = data_point['conditions_dict']
            if all(k in cond_dict and cond_dict[k] == v for k, v in required_conditions.items()):
                filtered_data.append(data_point)
        all_data = filtered_data
        req_str = ', '.join([f"{k}={v}" for k, v in required_conditions.items()])
        print(f"Applied required_conditions ({req_str}): {before_count} -> {len(all_data)} rows")

        if len(all_data) == 0:
            print("No data remaining after applying required_conditions. Exiting.")
            return

    sessions = list(set([d['session_id'] for d in all_data]))
    print(f"Found {len(sessions)} sessions: {sessions}")

    # =========================================================================
    # Branch: Enumerated mode vs Combination mode
    # =========================================================================
    if _is_enumerated_mode(filter_conditions):
        _run_enumerated_analysis(
            filter_conditions, all_data, sessions, group_names,
            session_grouping, session_group_assignments,
            output_path, exclude_groups, required_conditions
        )
    else:
        _run_combination_analysis(
            filter_conditions, all_data, sessions, group_names,
            session_grouping, session_group_assignments,
            output_path, exclude_groups, required_conditions
        )


# =============================================================================
# Enumerated mode analysis
# =============================================================================

def _run_enumerated_analysis(filter_conditions, all_data, sessions, group_names,
                             session_grouping, session_group_assignments,
                             output_path, exclude_groups, required_conditions):
    """Run analysis in enumerated mode (list-valued filter_conditions)."""

    bar_specs = _build_bar_specs(filter_conditions)

    print(f"\n=== Enumerated Mode ===")
    print(f"Generated {len(bar_specs)} bars from cross-product:")
    for bar_key, bar_label, _ in bar_specs:
        print(f"  {bar_label}")
    print(f"  + Non-match (if any leftovers)")

    # All bar keys including non_match
    all_bar_keys = [spec[0] for spec in bar_specs] + ['non_match']
    bar_labels_dict = {spec[0]: spec[1] for spec in bar_specs}
    list_keys = [k for k, v in filter_conditions.items() if isinstance(v, list)]
    non_match_parts = [f"{k} ∉ {{{', '.join(str(x) for x in filter_conditions[k])}}}" for k in list_keys]
    bar_labels_dict['non_match'] = 'Non-match: ' + ', '.join(non_match_parts)

    results_by_group = {}

    for group_name in group_names:
        print(f"\n{'=' * 60}")
        print(f"ANALYZING GROUP: {group_name}")
        print(f"{'=' * 60}")

        # Get sessions for this group
        if session_grouping is None or group_name == 'All Sessions':
            group_sessions = sessions
        else:
            group_sessions = [s for s in sessions if session_group_assignments.get(s) == group_name]

        print(f"Sessions in this group: {len(group_sessions)}")
        if len(group_sessions) == 0:
            print(f"Skipping group '{group_name}' - no sessions")
            continue

        # Accumulators per bar
        session_averages = {k: [] for k in all_bar_keys}
        session_condition_groups = {k: [] for k in all_bar_keys}
        session_on_performance = {k: [] for k in all_bar_keys}
        session_off_performance = {k: [] for k in all_bar_keys}
        total_condition_rows = {k: 0 for k in all_bar_keys}

        for session_id in group_sessions:
            session_data = [d for d in all_data if d['session_id'] == session_id]

            groups = {k: [] for k in all_bar_keys}
            condition_tracking = {k: [] for k in all_bar_keys}
            on_groups = {k: [] for k in all_bar_keys}
            off_groups = {k: [] for k in all_bar_keys}

            for data_point in session_data:
                cond_dict = data_point['conditions_dict']
                bar_key = _classify_data_point_enumerated(cond_dict, bar_specs, filter_conditions)

                groups[bar_key].append(data_point['effect_size'])
                on_groups[bar_key].append(data_point['estim_on_pct_hypothesized'])
                off_groups[bar_key].append(data_point['estim_off_pct_hypothesized'])
                condition_tracking[bar_key].append({
                    'session_id': session_id,
                    'conditions': data_point['conditions']
                })
                total_condition_rows[bar_key] += 1

            for bar_key, values in groups.items():
                if len(values) > 0:
                    session_averages[bar_key].append(np.mean(values))
                    session_condition_groups[bar_key].append(condition_tracking[bar_key])
                    session_on_performance[bar_key].append(np.mean(on_groups[bar_key]))
                    session_off_performance[bar_key].append(np.mean(off_groups[bar_key]))

        # Compute grand averages, std errors, p-values
        grand_averages = {}
        std_errors = {}
        p_values = {}
        on_averages = {}
        off_averages = {}
        on_std_errors = {}
        off_std_errors = {}

        for bar_key in all_bar_keys:
            session_vals = session_averages[bar_key]
            session_on_vals = session_on_performance[bar_key]
            session_off_vals = session_off_performance[bar_key]

            if len(session_vals) > 0:
                grand_averages[bar_key] = np.mean(session_vals)
                std_errors[bar_key] = np.std(session_vals) / np.sqrt(len(session_vals))

                on_averages[bar_key] = np.mean(session_on_vals)
                off_averages[bar_key] = np.mean(session_off_vals)
                on_std_errors[bar_key] = np.std(session_on_vals) / np.sqrt(len(session_on_vals))
                off_std_errors[bar_key] = np.std(session_off_vals) / np.sqrt(len(session_off_vals))

                grand_null_dist = compute_grand_null_distribution(
                    session_condition_groups[bar_key],
                    group_sessions
                )

                if grand_null_dist is not None and len(grand_null_dist) > 0:
                    p_values[bar_key] = calculate_p_value_two_tailed(
                        grand_averages[bar_key],
                        grand_null_dist
                    )
                    sig_marker = get_significance_marker(p_values[bar_key])
                    print(f"  {bar_labels_dict[bar_key]}: {grand_averages[bar_key]:.2f}% ± {std_errors[bar_key]:.2f} "
                          f"(n={total_condition_rows[bar_key]}, p={p_values[bar_key]:.4f} {sig_marker})")
                else:
                    p_values[bar_key] = None
                    print(f"  {bar_labels_dict[bar_key]}: {grand_averages[bar_key]:.2f}% ± {std_errors[bar_key]:.2f} "
                          f"(n={total_condition_rows[bar_key]}, no null dist)")
            else:
                grand_averages[bar_key] = None
                std_errors[bar_key] = None
                p_values[bar_key] = None
                on_averages[bar_key] = None
                off_averages[bar_key] = None
                on_std_errors[bar_key] = None
                off_std_errors[bar_key] = None
                print(f"  {bar_labels_dict[bar_key]}: No data")

        n_per_key = total_condition_rows
        s_per_key = {k: len(v) for k, v in session_averages.items()}

        results_by_group[group_name] = [{
            'combo_filter': filter_conditions,
            'combo_keys': list(filter_conditions.keys()),
            'grand_averages': grand_averages,
            'std_errors': std_errors,
            'p_values': p_values,
            'on_averages': on_averages,
            'off_averages': off_averages,
            'on_std_errors': on_std_errors,
            'off_std_errors': off_std_errors,
            'n_sessions': len(group_sessions),
            'n_per_key': n_per_key,
            's_per_key': s_per_key,
            'bar_labels': bar_labels_dict,
            'is_enumerated': True,
        }]

    # Plot
    plot_combination_comparison(results_by_group, filter_conditions, output_path, exclude_groups, group_names,
                                required_conditions=required_conditions)

    if output_path:
        dot_output_path = output_path.replace('.png', '_dots.png')
        plot_combination_comparison_dots(results_by_group, filter_conditions, dot_output_path, exclude_groups,
                                         group_names, required_conditions=required_conditions)


# =============================================================================
# Combination mode analysis (original logic)
# =============================================================================

def _run_combination_analysis(filter_conditions, all_data, sessions, group_names,
                              session_grouping, session_group_assignments,
                              output_path, exclude_groups, required_conditions):
    """Run analysis in combination mode (all scalar filter_conditions)."""

    filter_keys = list(filter_conditions.keys())
    all_combinations = []

    for r in range(1, len(filter_keys) + 1):
        for combo in combinations(filter_keys, r):
            all_combinations.append(combo)

    print(f"\nAnalyzing {len(all_combinations)} filter combinations:")
    for combo in all_combinations:
        print(f"  {combo}")

    results_by_group = {}

    for group_name in group_names:
        print(f"\n{'=' * 60}")
        print(f"ANALYZING GROUP: {group_name}")
        print(f"{'=' * 60}")

        if session_grouping is None or group_name == 'All Sessions':
            group_sessions = sessions
        else:
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

            session_on_performance = {
                'match_all': [],
                'match_none': [],
            }

            session_off_performance = {
                'match_all': [],
                'match_none': [],
            }

            for partial_size in range(1, len(combo_keys)):
                for partial_combo in combinations(combo_keys, partial_size):
                    key = f"match_{'||'.join(partial_combo)}"
                    session_averages[key] = []
                    session_condition_groups[key] = []
                    session_on_performance[key] = []
                    session_off_performance[key] = []

            for session_id in group_sessions:
                session_data = [d for d in all_data if d['session_id'] == session_id]

                groups = {key: [] for key in session_averages.keys()}
                condition_tracking = {key: [] for key in session_averages.keys()}
                on_groups = {key: [] for key in session_averages.keys()}
                off_groups = {key: [] for key in session_averages.keys()}

                for data_point in session_data:
                    cond_dict = data_point['conditions_dict']

                    matches = {k: (k in cond_dict and cond_dict[k] == v)
                               for k, v in combo_filter.items()}
                    num_matches = sum(matches.values())

                    if num_matches == len(combo_filter):
                        groups['match_all'].append(data_point['effect_size'])
                        on_groups['match_all'].append(data_point['estim_on_pct_hypothesized'])
                        off_groups['match_all'].append(data_point['estim_off_pct_hypothesized'])
                        condition_tracking['match_all'].append({
                            'session_id': session_id,
                            'conditions': data_point['conditions']
                        })
                    elif num_matches == 0:
                        groups['match_none'].append(data_point['effect_size'])
                        on_groups['match_none'].append(data_point['estim_on_pct_hypothesized'])
                        off_groups['match_none'].append(data_point['estim_off_pct_hypothesized'])
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
                                        on_groups[key].append(data_point['estim_on_pct_hypothesized'])
                                        off_groups[key].append(data_point['estim_off_pct_hypothesized'])
                                        condition_tracking[key].append({
                                            'session_id': session_id,
                                            'conditions': data_point['conditions']
                                        })
                                        break

                for group_key, values in groups.items():
                    if len(values) > 0:
                        session_averages[group_key].append(np.mean(values))
                        session_condition_groups[group_key].append(condition_tracking[group_key])
                        session_on_performance[group_key].append(np.mean(on_groups[group_key]))
                        session_off_performance[group_key].append(np.mean(off_groups[group_key]))

            grand_averages = {}
            std_errors = {}
            p_values = {}
            on_averages = {}
            off_averages = {}
            on_std_errors = {}
            off_std_errors = {}

            for group_key in session_averages.keys():
                session_vals = session_averages[group_key]
                session_on_vals = session_on_performance[group_key]
                session_off_vals = session_off_performance[group_key]

                if len(session_vals) > 0:
                    grand_averages[group_key] = np.mean(session_vals)
                    std_errors[group_key] = np.std(session_vals) / np.sqrt(len(session_vals))

                    on_averages[group_key] = np.mean(session_on_vals)
                    off_averages[group_key] = np.mean(session_off_vals)
                    on_std_errors[group_key] = np.std(session_on_vals) / np.sqrt(len(session_on_vals))
                    off_std_errors[group_key] = np.std(session_off_vals) / np.sqrt(len(session_off_vals))

                    grand_null_dist = compute_grand_null_distribution(
                        session_condition_groups[group_key],
                        group_sessions
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
                    on_averages[group_key] = None
                    off_averages[group_key] = None
                    on_std_errors[group_key] = None
                    off_std_errors[group_key] = None
                    print(f"  {group_key}: No data")

            n_per_key = {k: len(v) for k, v in session_averages.items()}
            s_per_key = n_per_key  # In combination mode, n_per_key already counts sessions

            results_by_combination.append({
                'combo_filter': combo_filter,
                'combo_keys': combo_keys,
                'grand_averages': grand_averages,
                'std_errors': std_errors,
                'p_values': p_values,
                'on_averages': on_averages,
                'off_averages': off_averages,
                'on_std_errors': on_std_errors,
                'off_std_errors': off_std_errors,
                'n_sessions': len(group_sessions),
                'n_per_key': n_per_key,
                's_per_key': s_per_key,
            })

        results_by_group[group_name] = results_by_combination

    plot_combination_comparison(results_by_group, filter_conditions, output_path, exclude_groups, group_names,
                                required_conditions=required_conditions)

    if output_path:
        dot_output_path = output_path.replace('.png', '_dots.png')
        plot_combination_comparison_dots(results_by_group, filter_conditions, dot_output_path, exclude_groups,
                                         group_names, required_conditions=required_conditions)


# =============================================================================
# Shared utility functions
# =============================================================================

def compute_grand_null_distribution(session_condition_groups, sessions):
    """
    Compute grand null distribution by aggregating across sessions.
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


def _compute_sorted_keys(results_by_group, group_names, combo_idx, exclude_groups):
    """
    Compute the sorted match keys for a given combination index.

    Handles both enumerated mode and combination mode.
    """
    first_group = [g for g in group_names if g in results_by_group][0]
    result = results_by_group[first_group][combo_idx]

    if result.get('is_enumerated'):
        # Enumerated mode: preserve cross-product order, non_match last
        all_match_keys = set()
        for group_name in group_names:
            if group_name not in results_by_group:
                continue
            r = results_by_group[group_name][combo_idx]
            all_match_keys.update(k for k, v in r['grand_averages'].items() if v is not None)

        # Use the bar_labels keys to preserve ordering from cross-product
        bar_labels = result.get('bar_labels', {})
        ordered_keys = [k for k in bar_labels.keys() if k in all_match_keys and k != 'non_match']
        if 'non_match' in all_match_keys:
            ordered_keys.append('non_match')

        # Apply exclusions
        ordered_keys = [k for k in ordered_keys if k not in exclude_groups]
        return ordered_keys

    # --- Original combination mode logic ---
    all_match_keys = set()
    for group_name in group_names:
        if group_name not in results_by_group:
            continue
        r = results_by_group[group_name][combo_idx]
        all_match_keys.update(r['grand_averages'].keys())

    sorted_keys = []
    if 'match_all' in all_match_keys:
        sorted_keys.append('match_all')

    partial_keys = [k for k in all_match_keys if
                    k.startswith('match_') and k not in ['match_all', 'match_none']]
    sorted_keys.extend(sorted(partial_keys))

    if 'match_none' in all_match_keys:
        sorted_keys.append('match_none')

    # Only apply exclusions when more than 2 groups
    if len(sorted_keys) > 2:
        sorted_keys = [k for k in sorted_keys if k not in exclude_groups]

    return sorted_keys


def _get_bar_label(key, result):
    """
    Get the display label for a bar key.

    In enumerated mode, uses bar_labels from result.
    In combination mode, builds label from combo_filter/combo_keys.
    """
    if result.get('is_enumerated'):
        bar_labels = result.get('bar_labels', {})
        return bar_labels.get(key, key)

    # Combination mode: build label from combo info
    combo_filter = result['combo_filter']
    combo_keys = result['combo_keys']

    if key == 'match_all':
        prefix = 'BOTH' if len(combo_filter) == 2 else 'ALL'
        return f'{prefix}: ' + ', '.join([f"{k}={v}" for k, v in combo_filter.items()])
    elif key == 'match_none':
        unmatched_parts = [f"NOT {k}={combo_filter[k]}" for k in combo_keys]
        return ', '.join(unmatched_parts)
    else:
        matched_keys = key.replace('match_', '').split('||')
        matched_parts = [f"{k}={combo_filter[k]}" for k in matched_keys]
        unmatched_keys = [k for k in combo_keys if k not in matched_keys]
        unmatched_parts = [f"NOT {k}={combo_filter[k]}" for k in unmatched_keys]
        return ', '.join(matched_parts + unmatched_parts)


def _get_bar_color(key, result, color_scheme=None):
    """
    Get the bar color for a key.

    In enumerated mode, uses a colormap. In combination mode, uses match_all/none scheme.
    """
    if result.get('is_enumerated'):
        if key == 'non_match':
            return '#9E9E9E'  # Gray for non-match

        # Use a nice categorical palette for enumerated bars
        bar_labels = result.get('bar_labels', {})
        # Get ordered keys (excluding non_match)
        ordered = [k for k in bar_labels.keys() if k != 'non_match']
        if key in ordered:
            idx = ordered.index(key)
        else:
            idx = 0

        # Tab10-inspired palette
        palette = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
                    '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
                    '#bcbd22', '#17becf']
        return palette[idx % len(palette)]

    # Combination mode
    if color_scheme is None:
        color_scheme = {'match_all': '#2E7D32', 'match_none': '#C62828', 'partial': '#EF6C00'}

    if key == 'match_all':
        return color_scheme['match_all']
    elif key == 'match_none':
        return color_scheme['match_none']
    else:
        return color_scheme['partial']


# =============================================================================
# Plotting functions
# =============================================================================

def plot_combination_comparison_dots(results_by_group, filter_conditions, output_path=None, exclude_groups=None,
                                     group_names=None, required_conditions=None):
    """
    Create dot plots showing EStim ON vs OFF performance with effect size annotations.
    """
    if exclude_groups is None:
        exclude_groups = []

    if group_names is None:
        group_names = list(results_by_group.keys())

    first_group = [g for g in group_names if g in results_by_group][0]
    n_combinations = len(results_by_group[first_group])

    n_groups = len(group_names)

    # Pre-compute sorted keys per combination
    combo_sorted_keys = []
    for combo_idx in range(n_combinations):
        sorted_keys = _compute_sorted_keys(results_by_group, group_names, combo_idx, exclude_groups)
        combo_sorted_keys.append(sorted_keys)

    BAR_GROUP_WIDTH_INCHES = 1.5
    FIGURE_MARGIN_INCHES = 2.0
    max_bar_groups = max(len(sk) for sk in combo_sorted_keys) if combo_sorted_keys else 2
    fig_width = max(4, max_bar_groups * BAR_GROUP_WIDTH_INCHES + FIGURE_MARGIN_INCHES)

    fig, axes = plt.subplots(n_combinations, 1, figsize=(fig_width, 6.5 * n_combinations))

    if n_combinations == 1:
        axes = [axes]

    for combo_idx in range(n_combinations):
        ax = axes[combo_idx]

        result = results_by_group[first_group][combo_idx]
        combo_filter = result['combo_filter']

        sorted_keys = combo_sorted_keys[combo_idx]

        if len(sorted_keys) == 0:
            print(f"Warning: No match groups to plot for combination {combo_filter}")
            continue

        n_match_groups = len(sorted_keys)
        x_spacing = 0.6
        x_base = np.arange(n_match_groups) * x_spacing

        color_schemes = [
            {'color': '#1976D2', 'marker': 'o'},
            {'color': '#388E3C', 'marker': 's'},
            {'color': '#D32F2F', 'marker': '^'},
            {'color': '#F57C00', 'marker': 'D'},
        ]

        for group_idx, group_name in enumerate(group_names):
            if group_name not in results_by_group:
                continue
            result = results_by_group[group_name][combo_idx]
            on_averages = result['on_averages']
            off_averages = result['off_averages']
            on_std_errors = result['on_std_errors']
            off_std_errors = result['off_std_errors']
            grand_averages = result['grand_averages']

            scheme = color_schemes[group_idx % len(color_schemes)]
            color = scheme['color']
            marker = scheme['marker']

            if n_groups > 1:
                x_offset = (group_idx - (n_groups - 1) / 2) * 0.15
            else:
                x_offset = 0

            for i, match_key in enumerate(sorted_keys):
                if on_averages.get(match_key) is None:
                    continue

                x_pos = x_base[i] + x_offset
                on_val = on_averages[match_key]
                off_val = off_averages[match_key]
                on_err = on_std_errors[match_key]
                off_err = off_std_errors[match_key]
                effect = grand_averages[match_key]

                ax.errorbar([x_pos], [off_val], yerr=[off_err],
                            fmt=marker, color=color, markersize=8, capsize=5,
                            alpha=0.7, label=f'{group_name} OFF' if i == 0 and n_groups > 1 and group_names != [
                        'All Sessions'] else None)

                ax.errorbar([x_pos], [on_val], yerr=[on_err],
                            fmt=marker, color=color, markersize=8, capsize=5,
                            alpha=0.7, markerfacecolor='none', markeredgewidth=2,
                            label=f'{group_name} ON' if i == 0 and n_groups > 1 and group_names != [
                                'All Sessions'] else None)

                text_x = x_pos + 0.15
                text_y = (on_val + off_val) / 2
                ax.text(text_x, text_y, f'Δ={effect:.1f}%',
                        fontsize=9, va='center', ha='left',
                        bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.7, edgecolor='gray'))

        ax.set_xlim(x_base[0] - x_spacing * 0.6, x_base[-1] + x_spacing * 0.6)

        # Generate x-axis labels using helper
        x_labels = [_get_bar_label(key, results_by_group[first_group][combo_idx]) for key in sorted_keys]

        ax.set_xticks(x_base)
        ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel('% Chose Hypothesized Shape', fontsize=12)
        ax.axhline(y=50, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Chance (50%)')
        ax.grid(True, alpha=0.3, axis='y')

        combo_str = ', '.join([f"{k}={v}" for k, v in combo_filter.items()])
        title = f'EStim ON vs OFF Performance: {combo_str}'
        if required_conditions:
            req_str = ', '.join([f"{k}={v}" for k, v in required_conditions.items()])
            title += f' | Fixed: {req_str}'
        if n_groups > 1 and group_names != ['All Sessions']:
            title += f' | Grouped by Session'
        ax.set_title(title, fontsize=14, fontweight='bold')

        if n_groups > 1 and group_names != ['All Sessions']:
            ax.legend(loc='upper left', fontsize=9)
        else:
            handles = [
                plt.Line2D([0], [0], marker='o', color='gray', linestyle='',
                           markersize=8, label='EStim OFF'),
                plt.Line2D([0], [0], marker='o', color='gray', linestyle='',
                           markersize=8, markerfacecolor='none', markeredgewidth=2, label='EStim ON')
            ]
            ax.legend(handles=handles, loc='upper left', fontsize=9)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\nSaved dot plot to {output_path}")

    plt.show()


def plot_combination_comparison(results_by_group, filter_conditions, output_path=None, exclude_groups=None,
                                group_names=None, required_conditions=None):
    """
    Create bar plots comparing different filter combinations, with optional session group comparison.
    """
    if exclude_groups is None:
        exclude_groups = []

    if group_names is None:
        group_names = list(results_by_group.keys())

    first_group = [g for g in group_names if g in results_by_group][0]
    n_combinations = len(results_by_group[first_group])

    n_groups = len(group_names)

    # Pre-compute sorted keys per combination
    combo_sorted_keys = []
    for combo_idx in range(n_combinations):
        sorted_keys = _compute_sorted_keys(results_by_group, group_names, combo_idx, exclude_groups)
        combo_sorted_keys.append(sorted_keys)

    BAR_GROUP_WIDTH_INCHES = 1.0
    FIGURE_MARGIN_INCHES = 1
    max_bar_groups = max(len(sk) for sk in combo_sorted_keys) if combo_sorted_keys else 2
    fig_width = max(1, max_bar_groups * BAR_GROUP_WIDTH_INCHES + FIGURE_MARGIN_INCHES)

    fig, axes = plt.subplots(n_combinations, 1, figsize=(fig_width, 10 * n_combinations))

    if n_combinations == 1:
        axes = [axes]

    # Color schemes for session groups (combination mode)
    session_color_schemes = [
        {'match_all': '#2E7D32', 'match_none': '#C62828', 'partial': '#EF6C00'},
        {'match_all': '#66BB6A', 'match_none': '#EF5350', 'partial': '#FFA726'},
        {'match_all': '#1B5E20', 'match_none': '#B71C1C', 'partial': '#E65100'},
        {'match_all': '#81C784', 'match_none': '#E57373', 'partial': '#FFB74D'},
    ]

    for combo_idx in range(n_combinations):
        ax = axes[combo_idx]

        result = results_by_group[first_group][combo_idx]
        combo_filter = result['combo_filter']
        is_enumerated = result.get('is_enumerated', False)

        sorted_keys = combo_sorted_keys[combo_idx]

        if len(sorted_keys) == 0:
            print(f"Warning: No match groups to plot for combination {combo_filter}")
            continue

        n_match_groups = len(sorted_keys)
        bar_width = 0.15 / n_groups if n_groups > 1 else 0.15
        total_group_width = bar_width * n_groups
        x_spacing = total_group_width + 0.1
        x_base = np.arange(n_match_groups) * x_spacing

        all_max_heights = []
        all_min_heights = []

        for group_idx, group_name in enumerate(group_names):
            if group_name not in results_by_group:
                continue
            result = results_by_group[group_name][combo_idx]
            grand_averages = result['grand_averages']
            std_errors = result['std_errors']

            means = []
            errors = []
            colors = []

            for match_key in sorted_keys:
                if grand_averages.get(match_key) is not None:
                    means.append(grand_averages[match_key])
                    errors.append(std_errors[match_key])

                    if is_enumerated:
                        colors.append(_get_bar_color(match_key, result))
                    else:
                        color_scheme = session_color_schemes[group_idx % len(session_color_schemes)]
                        colors.append(_get_bar_color(match_key, result, color_scheme))
                else:
                    means.append(0)
                    errors.append(0)
                    colors.append('lightgray')

            if n_groups > 1:
                x_offset = (group_idx - (n_groups - 1) / 2) * bar_width
                x_pos = x_base + x_offset
                alpha = 0.7
            else:
                x_pos = x_base
                alpha = 0.7

            show_legend = n_groups > 1 and group_names != ['All Sessions']
            bars = ax.bar(x_pos, means, width=bar_width, yerr=errors, capsize=5,
                          color=colors, alpha=alpha, edgecolor='black',
                          label=group_name if show_legend else None)

            if means:
                max_height = max([m + e for m, e in zip(means, errors)])
                min_height = min([m - e for m, e in zip(means, errors)])
                all_max_heights.append(max_height)
                all_min_heights.append(min_height)

        # Set y-axis limits
        if all_max_heights and all_min_heights:
            overall_max = max(all_max_heights)
            overall_min = min(all_min_heights)
            overall_min = min(overall_min, 0)
            y_range = overall_max - overall_min
            ax.set_ylim(overall_min - 0.1 * y_range, overall_max + 0.45 * y_range)

        final_y_range = ax.get_ylim()[1] - ax.get_ylim()[0]

        # Add labels to bars
        bar_idx = 0
        for group_idx, group_name in enumerate(group_names):
            if group_name not in results_by_group:
                continue
            result = results_by_group[group_name][combo_idx]
            grand_averages = result['grand_averages']
            std_errors = result['std_errors']
            p_values = result['p_values']
            n_per_key = result.get('n_per_key', {})
            s_per_key = result.get('s_per_key', {})

            means = []
            errors = []
            p_vals = []
            n_vals = []
            s_vals = []

            for match_key in sorted_keys:
                if grand_averages.get(match_key) is not None:
                    means.append(grand_averages[match_key])
                    errors.append(std_errors[match_key])
                    p_vals.append(p_values.get(match_key, None))
                    n_vals.append(n_per_key.get(match_key, 0))
                    s_vals.append(s_per_key.get(match_key, 0))
                else:
                    means.append(0)
                    errors.append(0)
                    p_vals.append(None)
                    n_vals.append(0)
                    s_vals.append(0)

            for i, (mean, err, p_val, n_val, s_val) in enumerate(zip(means, errors, p_vals, n_vals, s_vals)):
                if mean == 0:
                    bar_idx += 1
                    continue

                bar = ax.patches[bar_idx]
                height = bar.get_height()

                ax.text(bar.get_x() + bar.get_width() / 2., height + err + 0.015 * final_y_range,
                        f'{mean:.1f}%',
                        ha='center', va='bottom', fontweight='bold', fontsize=9)

                ax.text(bar.get_x() + bar.get_width() / 2., height + err + 0.05 * final_y_range,
                        f'n={n_val}, sessions={s_val}',
                        ha='center', va='bottom', fontsize=7)

                if p_val is not None:
                    p_text = f'p={p_val:.3f}' if p_val >= 0.001 else 'p<0.001'
                    sig_marker = get_significance_marker(p_val)
                    if sig_marker != 'ns':
                        p_text = f'{sig_marker} {p_text}'

                    ax.text(bar.get_x() + bar.get_width() / 2., height + err + 0.085 * final_y_range,
                            p_text,
                            ha='center', va='bottom', fontsize=7, style='italic')

                bar_idx += 1

        ax.set_xlim(x_base[0] - x_spacing * 0.6, x_base[-1] + x_spacing * 0.6)

        # Generate x-axis labels using helper
        x_labels = [_get_bar_label(key, results_by_group[first_group][combo_idx]) for key in sorted_keys]

        ax.set_xticks(x_base)
        ax.set_xticklabels(x_labels, rotation=45, ha='right', fontsize=9)
        ax.set_ylabel('Effect Size (EStim ON - OFF %)', fontsize=12)
        ax.axhline(y=0, color='black', linestyle='--', linewidth=1)
        ax.grid(True, alpha=0.3, axis='y')

        combo_str = ', '.join([f"{k}={v}" for k, v in combo_filter.items()])
        title = f'Effect Size Comparison: {combo_str}'
        if required_conditions:
            req_str = ', '.join([f"{k}={v}" for k, v in required_conditions.items()])
            title += f' | Fixed: {req_str}'
        if n_groups > 1 and group_names != ['All Sessions']:
            title += f' | Grouped by Session'
        ax.set_title(title, fontsize=14, fontweight='bold')

        if n_groups > 1 and group_names != ['All Sessions']:
            ax.legend(loc='upper left', fontsize=10)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\nSaved plot to {output_path}")

    plt.show()


if __name__ == '__main__':
    main()
import matplotlib.pyplot as plt
import numpy as np
from clat.util.connection import Connection
import json


def plot_effect_size_scatter(x_axis_config, output_path=None, session_ids=None,
                             session_filters=None, condition_filters=None, condition_grouping=None):
    """
    Create scatterplot of effect sizes vs a continuous variable.

    Args:
        x_axis_config: Dict defining x-axis variable:
                      {'source': 'session', 'field': 'avg_distance_scaled_correlation', 'label': 'Avg Distance-Scaled Correlation'}
                      OR
                      {'source': 'condition', 'field': 'noise_chance', 'label': 'Noise Chance'}
        output_path: Path to save the plot
        session_ids: Single session ID (string) or list of session IDs to include, or None for all
        session_filters: Dict of {field_name: lambda_function} to filter sessions from EStimShapeSessionData,
                        e.g. {'avg_distance_scaled_correlation': lambda x: x is not None and x > 0.1}
        condition_filters: Dict of {field_name: value or list of values} to filter conditions,
                          e.g. {'shape': 'BiphasicWithInterphaseDelay', 'polarity': 'PositiveFirst'}
                          OR {'noise_chance': [0.9, 1.0]} to include multiple values
        condition_grouping: Dict defining how to group conditions by color:
                           {'field': 'polarity',
                            'groups': {
                                'Positive First': 'PositiveFirst',
                                'Negative First': 'NegativeFirst'
                            }}
                           OR with lambda functions:
                           {'field': 'noise_chance',
                            'groups': {
                                'Low Noise': lambda x: x < 0.95,
                                'High Noise': lambda x: x >= 0.95
                            }}
    """
    repo_conn = Connection("allen_data_repository")

    # Get session-level data
    # Collect all session fields that will be needed
    session_fields_needed = set()

    # From x_axis_config
    if x_axis_config['source'] == 'session':
        session_fields_needed.add(x_axis_config['field'])

    # From session_filters
    if session_filters is not None:
        session_fields_needed.update(session_filters.keys())

    # Always include session_id
    session_fields_needed.add('session_id')

    # Build dynamic query
    fields_to_query = sorted(session_fields_needed)
    field_list = ', '.join(fields_to_query)

    print(f"Querying session fields: {fields_to_query}")

    query = f"""
        SELECT {field_list}
        FROM EStimShapeSessionData
    """

    repo_conn.execute(query)
    session_data_results = repo_conn.fetch_all()

    # Build dict of session metrics
    session_metrics = {}
    for row in session_data_results:
        row_dict = dict(zip(fields_to_query, row))
        sess_id = row_dict['session_id']

        # Store all fields except session_id
        session_metrics[sess_id] = {k: v for k, v in row_dict.items() if k != 'session_id'}

    # Apply session-level filters if provided
    filtered_session_ids = None
    if session_filters is not None:
        print("\n=== Applying Session-Level Filters ===")

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

            if len(filtered_session_ids) > 0:
                print(f"Sessions that passed:")
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

        # Use filtered sessions
        session_ids = filtered_session_ids if len(filtered_session_ids) > 0 else None

        if session_ids is None or len(session_ids) == 0:
            print("No sessions pass the filters. Exiting.")
            return

    # Query EStimEffects data
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

    print(f"Loaded {len(all_data)} effect size measurements")

    # Apply condition filters if provided
    if condition_filters is not None:
        print(f"\n=== Applying Condition Filters ===")
        filtered_data = []

        for data_point in all_data:
            cond_dict = data_point['conditions_dict']
            passes_all_filters = True

            for field_name, filter_value in condition_filters.items():
                if field_name not in cond_dict:
                    passes_all_filters = False
                    break

                # Handle list of acceptable values
                if isinstance(filter_value, list):
                    if cond_dict[field_name] not in filter_value:
                        passes_all_filters = False
                        break
                else:
                    if cond_dict[field_name] != filter_value:
                        passes_all_filters = False
                        break

            if passes_all_filters:
                filtered_data.append(data_point)

        all_data = filtered_data
        print(f"After condition filtering: {len(all_data)} measurements")

        if len(all_data) == 0:
            print("No data remains after filtering. Exiting.")
            return

    # Extract x and y values based on configuration
    x_source = x_axis_config['source']
    x_field = x_axis_config['field']
    x_label = x_axis_config.get('label', x_field)

    # Process condition grouping if provided
    group_assignments = {}
    group_names = ['All Data']  # Default group

    if condition_grouping is not None:
        print(f"\n=== Applying Condition Grouping ===")

        field_name = condition_grouping['field']
        group_definitions = condition_grouping['groups']
        group_names = list(group_definitions.keys())

        print(f"Grouping by condition field '{field_name}' into {len(group_names)} groups:")
        for group_name in group_names:
            print(f"  - {group_name}")

        # Assign each data point to a group
        for idx, data_point in enumerate(all_data):
            cond_dict = data_point['conditions_dict']

            if field_name not in cond_dict:
                print(f"Warning: Field '{field_name}' not found in conditions")
                continue

            field_value = cond_dict[field_name]

            for group_name, group_matcher in group_definitions.items():
                try:
                    # Check if it's a lambda function or direct value
                    if callable(group_matcher):
                        if group_matcher(field_value):
                            group_assignments[idx] = group_name
                            break
                    else:
                        if field_value == group_matcher:
                            group_assignments[idx] = group_name
                            break
                except Exception as e:
                    print(f"Warning: Group matching failed for field_value={field_value}: {e}")

        # Print group assignments
        for group_name in group_names:
            group_count = sum(1 for g in group_assignments.values() if g == group_name)
            print(f"  {group_name}: {group_count} data points")

    x_values = []
    y_values = []
    groups = []
    session_labels = []
    condition_labels = []

    for idx, data_point in enumerate(all_data):
        session_id = data_point['session_id']
        effect_size = data_point['effect_size']
        cond_dict = data_point['conditions_dict']

        if x_source == 'session':
            # X-axis from session data
            if session_id not in session_metrics:
                continue
            if x_field not in session_metrics[session_id]:
                continue
            x_val = session_metrics[session_id][x_field]
            if x_val is None:
                continue
        elif x_source == 'condition':
            # X-axis from condition dict
            if x_field not in cond_dict:
                continue
            x_val = cond_dict[x_field]
            if x_val is None:
                continue
        else:
            print(f"Error: Unknown x_source '{x_source}'. Must be 'session' or 'condition'.")
            return

        x_values.append(x_val)
        y_values.append(effect_size)
        session_labels.append(session_id)

        # Assign group
        if condition_grouping is not None and idx in group_assignments:
            groups.append(group_assignments[idx])
        else:
            groups.append('All Data')

        # Create condition label
        cond_str = ', '.join([f"{k}={v}" for k, v in sorted(cond_dict.items())])
        condition_labels.append(cond_str)

    if len(x_values) == 0:
        print("No valid data points to plot. Exiting.")
        return

    print(f"\nPlotting {len(x_values)} data points")

    # Create scatter plot
    fig, ax = plt.subplots(figsize=(12, 8))

    # Define color palette
    color_palette = ['steelblue', 'coral', 'mediumseagreen', 'gold', 'mediumpurple',
                     'lightcoral', 'skyblue', 'orange', 'lightgreen']

    # Plot each group separately
    if condition_grouping is not None and len(group_names) > 1:
        for group_idx, group_name in enumerate(group_names):
            # Get indices for this group
            group_mask = [g == group_name for g in groups]
            group_x = [x for x, mask in zip(x_values, group_mask) if mask]
            group_y = [y for y, mask in zip(y_values, group_mask) if mask]

            if len(group_x) > 0:
                color = color_palette[group_idx % len(color_palette)]
                ax.scatter(group_x, group_y, c=color, s=100, alpha=0.6,
                           edgecolors='black', linewidth=0.5, label=group_name)
    else:
        # Single group - use default color
        ax.scatter(x_values, y_values, c='steelblue', s=100, alpha=0.6,
                   edgecolors='black', linewidth=0.5)

    # Calculate and plot averages for each unique x-value
    unique_x_values = sorted(set(x_values))

    print(f"\n=== Calculating Averages ===")
    print(f"Found {len(unique_x_values)} unique x-values")

    # Calculate grand averages (across all groups)
    grand_avg_x = []
    grand_avg_y = []

    for x_val in unique_x_values:
        # Get all y-values for this x-value
        y_at_x = [y for x, y in zip(x_values, y_values) if x == x_val]
        if len(y_at_x) > 0:
            grand_avg_x.append(x_val)
            grand_avg_y.append(np.mean(y_at_x))
            print(f"  x={x_val}: n={len(y_at_x)}, grand_avg={np.mean(y_at_x):.3f}")

    # Plot grand averages with black markers
    if len(grand_avg_x) > 0:
        ax.scatter(grand_avg_x, grand_avg_y, c='black', s=300, alpha=0.8,
                   edgecolors='white', linewidth=2, marker='D',
                   label='Grand Average', zorder=10)

    # Calculate and plot per-group averages if grouping exists
    if condition_grouping is not None and len(group_names) > 1:
        for group_idx, group_name in enumerate(group_names):
            group_mask = [g == group_name for g in groups]
            group_x_vals = [x for x, mask in zip(x_values, group_mask) if mask]
            group_y_vals = [y for y, mask in zip(y_values, group_mask) if mask]

            group_avg_x = []
            group_avg_y = []

            for x_val in unique_x_values:
                # Get y-values for this group at this x-value
                y_at_x = [y for x, y in zip(group_x_vals, group_y_vals) if x == x_val]
                if len(y_at_x) > 0:
                    group_avg_x.append(x_val)
                    group_avg_y.append(np.mean(y_at_x))
                    print(f"  {group_name} at x={x_val}: n={len(y_at_x)}, avg={np.mean(y_at_x):.3f}")

            # Plot group averages with same color as scatter points but larger
            if len(group_avg_x) > 0:
                color = color_palette[group_idx % len(color_palette)]
                ax.scatter(group_avg_x, group_avg_y, c=color, s=250, alpha=0.9,
                           edgecolors='white', linewidth=2, marker='D',
                           label=f'{group_name} Average', zorder=9)

    # Add horizontal line at y=0
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)

    # Labels
    ax.set_xlabel(x_label, fontsize=12, fontweight='bold')
    ax.set_ylabel('Effect Size (EStim ON - OFF %)', fontsize=12, fontweight='bold')

    # Title
    title = f'Effect Size vs {x_label}'
    if condition_grouping is not None and len(group_names) > 1:
        title += f' (Grouped by {condition_grouping["field"]})'
    ax.set_title(title, fontsize=14, fontweight='bold')

    # Grid
    ax.grid(True, alpha=0.3)

    # Add legend if groups exist
    if condition_grouping is not None and len(group_names) > 1:
        ax.legend(loc='best', fontsize=10, framealpha=0.9)
    elif len(grand_avg_x) > 0:
        # Show legend for grand average even without grouping
        ax.legend(loc='best', fontsize=10, framealpha=0.9)

    # Add session count to plot
    unique_sessions = len(set(session_labels))
    info_text = f'n = {len(x_values)} measurements\n{unique_sessions} sessions'
    if condition_grouping is not None and len(group_names) > 1:
        info_text += f'\n{len(group_names)} groups'
    ax.text(0.02, 0.98, info_text,
            transform=ax.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\nSaved plot to {output_path}")

    plt.show()

    # Print summary statistics
    print(f"\n=== Summary Statistics ===")
    print(f"X-axis ({x_label}):")
    print(f"  Range: [{min(x_values):.3f}, {max(x_values):.3f}]")
    print(f"  Mean: {np.mean(x_values):.3f}")
    print(f"  Median: {np.median(x_values):.3f}")

    print(f"\nY-axis (Effect Size):")
    print(f"  Range: [{min(y_values):.3f}, {max(y_values):.3f}]")
    print(f"  Mean: {np.mean(y_values):.3f}")
    print(f"  Median: {np.median(y_values):.3f}")

    # Calculate correlation
    from scipy.stats import pearsonr, spearmanr
    pearson_r, pearson_p = pearsonr(x_values, y_values)
    spearman_r, spearman_p = spearmanr(x_values, y_values)

    print(f"\nCorrelation (Overall):")
    print(f"  Pearson's r: {pearson_r:.3f} (p={pearson_p:.4f})")
    print(f"  Spearman's ρ: {spearman_r:.3f} (p={spearman_p:.4f})")

    # Per-group statistics
    if condition_grouping is not None and len(group_names) > 1:
        print(f"\n=== Per-Group Statistics ===")
        for group_name in group_names:
            group_mask = [g == group_name for g in groups]
            group_x = [x for x, mask in zip(x_values, group_mask) if mask]
            group_y = [y for y, mask in zip(y_values, group_mask) if mask]

            if len(group_x) > 0:
                print(f"\n{group_name} (n={len(group_x)}):")
                print(f"  X-axis: Mean={np.mean(group_x):.3f}, Median={np.median(group_x):.3f}")
                print(f"  Y-axis: Mean={np.mean(group_y):.3f}, Median={np.median(group_y):.3f}")

                if len(group_x) >= 3:
                    pearson_r_g, pearson_p_g = pearsonr(group_x, group_y)
                    spearman_r_g, spearman_p_g = spearmanr(group_x, group_y)
                    print(f"  Pearson's r: {pearson_r_g:.3f} (p={pearson_p_g:.4f})")
                    print(f"  Spearman's ρ: {spearman_r_g:.3f} (p={spearman_p_g:.4f})")
                else:
                    print(f"  (Not enough points for correlation)")


def main():
    # Example 1: Plot effect size vs session metric (avg_distance_scaled_correlation)
    # x_axis_config = {
    #     'source': 'session',
    #     'field': 'cluster_size',
    #     'label': 'Num Channels in Cluster'
    # }
    x_axis_config = {
        'source': 'session',
        'field': 'avg_distance_scaled_correlation',
        'label': 'Cluster Correlation'
    }
    # x_axis_config = {
    #     'source': 'session',
    #     'field': 'lineage_score',
    #     'label': 'quality of GA'
    # }

    # Example 2: Plot effect size vs condition parameter (noise_chance)
    # x_axis_config = {
    #     'source': 'condition',
    #     'field': 'noise_chance',
    #     'label': 'Noise Chance'
    # }

    # Example 3: Plot effect size vs another condition parameter
    # x_axis_config = {
    #     'source': 'condition',
    #     'field': 'num_channels',
    #     'label': 'Number of Channels'
    # }

    # Session filters (optional)
    session_filters = {
        # 'avg_distance_scaled_correlation': lambda x: x is not None  # Only sessions with this metric
    }

    # Condition filters (optional)
    condition_filters = {
        # 'shape': 'BiphasicWithInterphaseDelay',  # Single value
        # 'noise_chance': [0.9, 1.0],  # Multiple values
        # 'polarity': 'PositiveFirst'
    }

    # Condition grouping (optional) - colors dots by groups

    condition_grouping = None
    condition_grouping = {
        'field': 'polarity',
        'groups': {
            'Positive First': 'PositiveFirst',
            'Negative First': 'NegativeFirst'
        }
    }

    # Example with lambda functions:
    # condition_grouping = {
    #     'field': 'noise_chance',
    #     'groups': {
    #         '100% Noise': lambda x: x == 1.0,
    #         '90% Noise': lambda x: x == 0.90,
    #         'Lower Noise': lambda x: x < 0.90,
    #     }
    # }

    # Example with num_channels:
    # condition_grouping = {
    #     'field': 'num_channels',
    #     'groups': {
    #         '1 Channel': 1.0,
    #         '2 Channels': 2.0,
    #         '3 Channels': 3.0,
    #         '9 Channels': 9.0,
    #     }
    # }

    # Specific sessions (optional)
    # session_ids = ["260115_0", "260120_0"]
    session_ids = None

    import os
    save_dir = "/home/connorlab/Documents/plots/estimshape/"
    os.makedirs(save_dir, exist_ok=True)

    x_field_str = x_axis_config['field'].replace('_', '-')
    output_path = os.path.join(save_dir, f'effect_size_vs_{x_field_str}_scatter.png')

    plot_effect_size_scatter(
        x_axis_config=x_axis_config,
        output_path=output_path,
        session_ids=session_ids,
        session_filters=session_filters,
        condition_filters=condition_filters,
        condition_grouping=condition_grouping
    )


if __name__ == '__main__':
    main()
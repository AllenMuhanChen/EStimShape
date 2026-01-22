from clat.util.connection import Connection
import pandas as pd
import json
import matplotlib.pyplot as plt
import numpy as np

from src.startup import context


def main():
    session_id = "260113_0"

    # Read data from repository
    data = read_trial_data_from_repository(session_id)
    print(f"Loaded {len(data)} trials for session {session_id}")

    # Data Combinations:
    data = combine_trial_types_at_max_noise(data)

    ## Searchlight analysis
    behavioral_conditions = ['trial_type', 'noise_chance']
    estim_conditions = [
        'num_channels',
        'polarity',
        'shape',
        'a1',
        'post_stim_refractory_period',
        'enable_charge_recovery'
    ]

    sliding_window_analysis(
        data,
        behavioral_conditions,
        estim_conditions,
        window_size=100,
        step_size=25,
        output_path=f'searchlight_{session_id}.png',
        session_id=session_id
    )

    # Define conditions for main analysis
    condition_groups = split_data_by_conditions(data, behavioral_conditions, estim_conditions)
    print(f"\nFound {len(condition_groups)} unique condition combinations")

    # Calculate No EStim vs EStim effects
    results = calculate_estim_effects(condition_groups)
    print(f"\nCalculated effects for {len(results)} condition combinations")

    # Save results to repository
    create_estim_effects_table()
    save_estim_effects_to_repository(session_id, results)
    print(f"\nSaved results to EStimEffects table")


def sliding_window_analysis(data, behavioral_conditions, estim_conditions,
                            window_size=100, step_size=5, output_path=None, session_id=None):
    """
    Perform sliding window analysis to track estim effects over time.

    Args:
        data: DataFrame with trial data
        behavioral_conditions: List of behavioral condition columns
        estim_conditions: List of estim parameter columns
        window_size: Number of trials in each window
        step_size: Number of trials to slide the window
        output_path: Path to save the plot (if None, uses default from context)
    """
    # Sort by trial_start chronologically
    data_sorted = data.sort_values('trial_start').reset_index(drop=True)

    print(f"\nRunning sliding window analysis:")
    print(f"  Window size: {window_size} trials")
    print(f"  Step size: {step_size} trials")
    print(f"  Total trials: {len(data_sorted)}")

    # Identify unique condition combinations we want to track
    all_conditions = behavioral_conditions + estim_conditions
    condition_groups = {}

    # Group data to find unique combinations
    temp_groups = split_data_by_conditions(data, behavioral_conditions, estim_conditions)
    for group in temp_groups:
        condition_key = json.dumps({**group['behavioral_conditions'], **group['estim_conditions']}, sort_keys=True)
        condition_groups[condition_key] = {
            'label': format_condition_label(group['behavioral_conditions'], group['estim_conditions']),
            'behavioral': group['behavioral_conditions'],
            'estim': group['estim_conditions'],
            'windows': []
        }

    print(f"  Tracking {len(condition_groups)} condition combinations")

    # Slide window through data
    window_positions = range(0, len(data_sorted) - window_size + 1, step_size)

    for window_start in window_positions:
        window_end = window_start + window_size
        window_data = data_sorted.iloc[window_start:window_end]

        # Calculate effects for this window
        window_groups = split_data_by_conditions(window_data, behavioral_conditions, estim_conditions)
        window_results = calculate_estim_effects(window_groups)

        # Store results for each condition
        for result in window_results:
            condition_key = json.dumps(result['conditions'], sort_keys=True)
            if condition_key in condition_groups:
                condition_groups[condition_key]['windows'].append({
                    'window_center': window_start + window_size // 2,
                    'trial_number': window_start + window_size // 2,
                    'effect_size': result['effect_size'],
                    'estim_on_n': result['estim_on_n_trials'],
                    'estim_off_n': result['estim_off_n_trials']
                })


    import os
    save_dir = "/home/connorlab/Documents/plots/260120_0/estimshape/"
    os.makedirs(save_dir, exist_ok=True)
    session_id = data['session_id'].iloc[0] if 'session_id' in data.columns else 'unknown'
    output_path = os.path.join(save_dir, f'sliding_window_{session_id}_w{window_size}_s{step_size}.png')

    # Plot results
    plot_sliding_window_results(condition_groups, output_path=output_path, window_size=window_size, step_size=step_size, session_id=session_id)

def format_condition_label(behavioral_dict, estim_dict):
    """Create a readable label for a condition combination"""
    # Abbreviate for readability
    label_parts = []

    # Add key behavioral conditions
    if 'trial_type' in behavioral_dict:
        trial_type = behavioral_dict['trial_type']
        type_abbrev = trial_type[:3] if trial_type != 'Combined' else 'Cmb'
        label_parts.append(type_abbrev)

    if 'noise_chance' in behavioral_dict:
        noise = int(behavioral_dict['noise_chance'] * 100)
        label_parts.append(f"{noise}%")

    # Add key estim conditions
    if 'polarity' in estim_dict:
        pol = estim_dict['polarity']
        pol_abbrev = 'Pos' if pol == 'PositiveFirst' else 'Neg'
        label_parts.append(pol_abbrev)

    if 'num_channels' in estim_dict:
        label_parts.append(f"{estim_dict['num_channels']}ch")

    if 'a1' in estim_dict and estim_dict['a1'] is not None:
        # Format current amplitude (a1 is in microamps)
        label_parts.append(f"I:{estim_dict['a1']:.1f}µA")
    return ' '.join(label_parts)


def plot_sliding_window_results(condition_groups, output_path=None, window_size=None, step_size=None, session_id=None):
    """
    Plot sliding window results showing effect size over time for each condition.

    Args:
        condition_groups: Dict of condition data with sliding window results
        output_path: Path to save the plot
        window_size: Size of sliding window (for display in text box)
        step_size: Step size for sliding window (for display in text box)
    """
    fig, ax = plt.subplots(figsize=(14, 8))

    # Define styling based on conditions
    trial_type_colors = {
        'Delta Shape': 'red',
        'Del': 'red',  # Abbreviated version
        'Hypothesized Shape': 'blue',
        'Hyp': 'blue',  # Abbreviated version
        'Combined': 'purple',
        'Cmb': 'purple'  # Abbreviated version
    }

    # Line styles for polarity
    polarity_linestyles = {
        'PositiveFirst': '-',
        'Pos': '-',
        'NegativeFirst': '--',
        'Neg': '--'
    }

    # Marker styles for charge recovery
    charge_recovery_markers = {
        True: 'o',
        False: 's',
        1: 'o',
        0: 's'
    }

    # Plot each condition
    for condition_key, condition_data in condition_groups.items():
        if len(condition_data['windows']) == 0:
            continue

        # Extract data for plotting
        trial_numbers = [w['trial_number'] for w in condition_data['windows']]
        effect_sizes = [w['effect_size'] for w in condition_data['windows']]

        # Skip if all None
        if all(e is None for e in effect_sizes):
            continue

        # Determine styling based on conditions
        behavioral = condition_data['behavioral']
        estim = condition_data['estim']

        # Color: trial type
        trial_type = behavioral.get('trial_type', 'Combined')
        color = trial_type_colors.get(trial_type, 'gray')

        # Alpha: noise chance (lower noise = more opacity)
        noise_chance = behavioral.get('noise_chance', 1.0)
        alpha = 0.3 + (1.0 - noise_chance) * 0.5  # Range from 0.3 (100% noise) to 0.8 (0% noise)

        # Line style: polarity
        polarity = estim.get('polarity', 'PositiveFirst')
        linestyle = polarity_linestyles.get(polarity, '-')

        # Marker: charge recovery
        charge_recovery = estim.get('enable_charge_recovery', True)
        marker = charge_recovery_markers.get(charge_recovery, 'o')

        # Line width: number of channels (more channels = thicker line)
        num_channels = estim.get('num_channels', 1)
        linewidth = 1 + (num_channels / 10)  # Scale linewidth with channel count

        # Plot line
        ax.plot(trial_numbers, effect_sizes,
                color=color,
                alpha=alpha,
                linestyle=linestyle,
                marker=marker,
                markersize=3,
                linewidth=linewidth,
                label=condition_data['label'])

    # Add zero line for reference
    ax.axhline(y=0, color='black', linestyle='--', linewidth=1, alpha=0.5)

    # Add text box with window parameters and legend key
    if window_size is not None and step_size is not None:
        textstr = (f'Window Size: {window_size} trials\n'
                   f'Step Size: {step_size} trials\n\n'
                   f'Styling:\n'
                   f'Color: Red=Delta, Blue=Hyp, Purple=Combined\n'
                   f'Opacity: Higher=Lower Noise\n'
                   f'Line: Solid=Pos, Dash=Neg\n'
                   f'Marker: Circle=CR+, Square=CR-\n'
                   f'Width: Thicker=More Channels')
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=props)

    # Labels and formatting
    ax.set_xlabel('Trial Number (Window Center)', fontsize=12)
    ax.set_ylabel('Effect Size (EStim ON - EStim OFF %)', fontsize=12)

    if session_id is not None:
        ax.set_title(f'{session_id} - Sliding Window Analysis: EStim Effect Over Time by Condition', fontsize=14)
    else:
        ax.set_title('Sliding Window Analysis: EStim Effect Over Time by Condition', fontsize=14)

    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        print(f"\nSaved sliding window plot to {output_path}")
    plt.show()

def combine_trial_types_at_max_noise(data):
    """
    Combine Delta Shape and Hypothesized Shape trial types at 100% noise.
    At maximum noise, these trial types are functionally equivalent.

    Args:
        data: DataFrame with trial data

    Returns:
        DataFrame with combined trial types
    """
    data = data.copy()

    # Find trials at 100% noise with Delta Shape or Hypothesized Shape trial types
    max_noise_mask = data['noise_chance'] == 1.0
    delta_or_hyp_mask = data['trial_type'].isin(['Delta Shape', 'Hypothesized Shape'])

    # Combine the masks
    combine_mask = max_noise_mask & delta_or_hyp_mask

    # Rename to 'Combined'
    data.loc[combine_mask, 'trial_type'] = 'Combined'

    num_combined = combine_mask.sum()
    print(f"Combined {num_combined} trials at 100% noise into 'Combined' trial type")

    return data


def calculate_estim_effects(condition_groups):
    """
    Calculate percentage of hypothesized choices for estim vs no-estim

    Args:
        condition_groups: List of dicts with estim_on_data and estim_off_data

    Returns:
        List of dicts with calculated effects
    """
    results = []

    for group in condition_groups:
        estim_on = group['estim_on_data']
        estim_off = group['estim_off_data']

        # Calculate percentages
        estim_on_pct = estim_on['is_hypothesized_choice'].mean() * 100 if len(estim_on) > 0 else None
        estim_off_pct = estim_off['is_hypothesized_choice'].mean() * 100 if len(estim_off) > 0 else None

        # Combine all conditions into one dict
        all_conditions = {**group['behavioral_conditions'], **group['estim_conditions']}

        results.append({
            'conditions': all_conditions,
            'estim_on_pct_hypothesized': estim_on_pct,
            'estim_off_pct_hypothesized': estim_off_pct,
            'estim_on_n_trials': len(estim_on),
            'estim_off_n_trials': len(estim_off),
            'effect_size': estim_on_pct - estim_off_pct if estim_on_pct is not None and estim_off_pct is not None else None
        })

    return results


def create_estim_effects_table():
    """Create EStimEffects table if it doesn't exist"""
    repo_conn = Connection("allen_data_repository")

    repo_conn.execute("""
                      CREATE TABLE IF NOT EXISTS EStimEffects
                      (
                          session_id                 VARCHAR(10) NOT NULL,
                          conditions                 LONGTEXT    NOT NULL,
                          estim_on_pct_hypothesized  FLOAT,
                          estim_off_pct_hypothesized FLOAT,
                          estim_on_n_trials          INT,
                          estim_off_n_trials         INT,
                          effect_size                FLOAT,

                          PRIMARY KEY (session_id, conditions(500)),
                          FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
                      ) ENGINE = InnoDB
                        DEFAULT CHARSET = latin1
                      """)

    print("EStimEffects table created successfully")


def save_estim_effects_to_repository(session_id, results):
    """
    Save calculated effects to EStimEffects table

    Args:
        session_id: Session identifier
        results: List of dicts with calculated effects
    """
    repo_conn = Connection("allen_data_repository")

    for result in results:
        # Convert conditions dict to JSON string for storage
        conditions_str = json.dumps(result['conditions'], sort_keys=True)

        # Convert numpy types to Python native types
        estim_on_pct = float(result['estim_on_pct_hypothesized']) if result[
                                                                         'estim_on_pct_hypothesized'] is not None else None
        estim_off_pct = float(result['estim_off_pct_hypothesized']) if result[
                                                                           'estim_off_pct_hypothesized'] is not None else None
        estim_on_n = int(result['estim_on_n_trials']) if result['estim_on_n_trials'] is not None else None
        estim_off_n = int(result['estim_off_n_trials']) if result['estim_off_n_trials'] is not None else None
        effect = float(result['effect_size']) if result['effect_size'] is not None else None

        repo_conn.execute("""
                          INSERT IGNORE INTO EStimEffects (session_id,
                                                           conditions,
                                                           estim_on_pct_hypothesized,
                                                           estim_off_pct_hypothesized,
                                                           estim_on_n_trials,
                                                           estim_off_n_trials,
                                                           effect_size)
                          VALUES (%s, %s, %s, %s, %s, %s, %s)
                          """, (
                              session_id,
                              conditions_str,
                              estim_on_pct,
                              estim_off_pct,
                              estim_on_n,
                              estim_off_n,
                              effect
                          ))


def split_data_by_conditions(data, behavioral_conditions, estim_conditions):
    """
    Split data for estim vs no-estim comparisons.

    Strategy:
    1. Group by behavioral conditions (applies to all trials)
    2. Within each behavioral group, the estim_off trials are the baseline
    3. Find all unique estim parameter combinations in estim_on trials
    4. Create comparison pairs: each estim parameter combo vs the shared baseline

    Args:
        data: DataFrame with trial data
        behavioral_conditions: Conditions that apply to both estim and no-estim trials
        estim_conditions: Conditions that only apply to estim trials

    Returns:
        List of dicts, each containing:
            - 'behavioral_conditions': dict of behavioral condition values
            - 'estim_conditions': dict of estim parameter values
            - 'estim_on_data': DataFrame of estim trials with these parameters
            - 'estim_off_data': DataFrame of no-estim baseline trials
    """
    comparisons = []

    # First group by behavioral conditions
    behavioral_groups = data.groupby(behavioral_conditions, dropna=False)

    for behavioral_values, behavioral_group in behavioral_groups:
        # Create behavioral condition dict
        if len(behavioral_conditions) == 1:
            behavioral_dict = {behavioral_conditions[0]: behavioral_values}
        else:
            behavioral_dict = dict(zip(behavioral_conditions, behavioral_values))

        # Split into estim on/off within this behavioral group
        estim_off_data = behavioral_group.loc[behavioral_group['is_estim_on'] == 0].copy()
        estim_on_data = behavioral_group.loc[behavioral_group['is_estim_on'] == 1].copy()

        # Skip if we don't have estim_off baseline
        if len(estim_off_data) == 0:
            continue

        # If no estim_on trials, we can't do comparisons
        if len(estim_on_data) == 0:
            continue

        # Now find all unique estim parameter combinations within estim_on trials
        estim_groups = estim_on_data.groupby(estim_conditions, dropna=False)

        for estim_values, estim_group in estim_groups:
            # Create estim condition dict
            if len(estim_conditions) == 1:
                estim_dict = {estim_conditions[0]: estim_values}
            else:
                estim_dict = dict(zip(estim_conditions, estim_values))

            # Add this comparison
            comparisons.append({
                'behavioral_conditions': behavioral_dict,
                'estim_conditions': estim_dict,
                'estim_on_data': estim_group.copy(),
                'estim_off_data': estim_off_data
            })

    return comparisons


def read_trial_data_from_repository(session_id):
    """
    Read trial data from EStimShapeTrials table and join with EStim parameters

    Args:
        session_id: Session identifier

    Returns:
        pandas.DataFrame with trial data and estim parameters
    """
    repo_conn = Connection("allen_data_repository")

    # Join trials with estim parameters
    query = """
            SELECT t.*, \
                   ep.channel, \
                   ep.num_channels, \
                   ep.shape, \
                   ep.polarity, \
                   ep.d1, \
                   ep.d2, \
                   ep.dp, \
                   ep.a1, \
                   ep.a2, \
                   ep.pulse_repetition, \
                   ep.num_repetitions, \
                   ep.pulse_train_period, \
                   ep.post_stim_refractory_period, \
                   ep.trigger_edge_or_level, \
                   ep.post_trigger_delay, \
                   ep.enable_amp_settle, \
                   ep.pre_stim_amp_settle, \
                   ep.post_stim_amp_settle, \
                   ep.maintain_amp_settle_during_pulse_train, \
                   ep.enable_charge_recovery, \
                   ep.post_stim_charge_recovery_on, \
                   ep.post_stim_charge_recovery_off
            FROM EStimShapeTrials t
                     LEFT JOIN (SELECT ep1.*, \
                                       channel_counts.num_channels \
                                FROM EStimParameters ep1 \
                                         INNER JOIN (SELECT session_id, \
                                                            estim_spec_id, \
                                                            MIN(channel) as first_channel, \
                                                            COUNT(*)     as num_channels \
                                                     FROM EStimParameters \
                                                     GROUP BY session_id, estim_spec_id) channel_counts \
                                                    ON ep1.session_id = channel_counts.session_id \
                                                        AND ep1.estim_spec_id = channel_counts.estim_spec_id \
                                                        AND ep1.channel = channel_counts.first_channel) ep \
                               ON t.session_id = ep.session_id AND t.estim_spec_id = ep.estim_spec_id
            WHERE t.session_id = %s
            ORDER BY t.task_id \
            """

    repo_conn.execute(query, (session_id,))

    # Get column names BEFORE fetch_all (which closes the cursor)
    column_names = [desc[0] for desc in repo_conn.my_cursor.description]

    # Now fetch the results
    result = repo_conn.fetch_all()

    # Convert to DataFrame
    df = pd.DataFrame(result, columns=column_names)

    return df


if __name__ == '__main__':
    main()
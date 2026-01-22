from clat.util.connection import Connection
import pandas as pd
import json


def main():
    session_id = "260120_0"

    # Read data from repository
    data = read_trial_data_from_repository(session_id)
    print(f"Loaded {len(data)} trials for session {session_id}")

    # Data Combinations:
    data = combine_trial_types_at_max_noise(data)

    ## TODO: searchlight analysis

    # Define conditions
    behavioral_conditions = ['trial_type', 'noise_chance']  # Apply to both estim and no-estim
    estim_conditions = [
        'num_channels',
        'polarity',
        'shape',
        'a1',
        'post_stim_refractory_period',
        'enable_charge_recovery'
    ]  # Only apply to estim trials

    condition_groups = split_data_by_conditions(data, behavioral_conditions, estim_conditions)
    print(f"\nFound {len(condition_groups)} unique condition combinations")

    # Calculate No EStim vs EStim effects
    results = calculate_estim_effects(condition_groups)
    print(f"\nCalculated effects for {len(results)} condition combinations")

    # Save results to repository
    create_estim_effects_table()
    save_estim_effects_to_repository(session_id, results)
    print(f"\nSaved results to EStimEffects table")

    ## TODO: plot


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
import numpy as np
from clat.util.connection import Connection
import json
from tqdm import tqdm


def run_permutation_tests(session_id=None, n_permutations=1000, force_recompute=False):
    """
    Run permutation tests for all condition combinations.

    Args:
        session_id: Specific session to analyze, or None for all sessions
        n_permutations: Number of permutations (default 1000)
        force_recompute: If True, recompute even if results exist
    """
    # Create table if needed
    create_permutation_test_table()

    # Get data from repository
    repo_conn = Connection("allen_data_repository")

    # Get conditions to test from EStimEffects
    if session_id:
        repo_conn.execute("""
                          SELECT session_id,
                                 conditions,
                                 estim_on_n_trials,
                                 estim_off_n_trials,
                                 effect_size
                          FROM EStimEffects
                          WHERE session_id = %s
                          """, (session_id,))
    else:
        repo_conn.execute("""
                          SELECT session_id,
                                 conditions,
                                 estim_on_n_trials,
                                 estim_off_n_trials,
                                 effect_size
                          FROM EStimEffects
                          """)

    column_names = [desc[0] for desc in repo_conn.my_cursor.description]
    conditions_to_test = repo_conn.fetch_all()

    print(f"Found {len(conditions_to_test)} condition combinations to test")

    # Process each condition
    for row in tqdm(conditions_to_test, desc="Running permutation tests"):
        row_dict = dict(zip(column_names, row))
        sess_id = row_dict['session_id']
        conditions_json = row_dict['conditions']
        observed_effect = row_dict['effect_size']

        # Check if already computed
        if not force_recompute:
            repo_conn.execute("""
                              SELECT 1
                              FROM EStimPermutationTests
                              WHERE session_id = %s
                                AND conditions = %s
                              """, (sess_id, conditions_json))
            if repo_conn.fetch_all():
                continue  # Skip if already exists

        # Parse conditions
        cond_dict = json.loads(conditions_json)

        # Get trial data for this condition
        trial_data = get_trial_data_for_condition(sess_id, cond_dict)

        if len(trial_data['estim_on']) == 0 or len(trial_data['estim_off']) == 0:
            print(f"Skipping {sess_id}, {cond_dict}: insufficient data")
            continue

        # Run permutation test
        null_distribution = run_single_permutation_test(
            trial_data['estim_on'],
            trial_data['estim_off'],
            n_permutations
        )

        # Calculate p-values
        p_two_tailed = calculate_p_value_two_tailed(observed_effect, null_distribution)
        p_greater = calculate_p_value_one_tailed(observed_effect, null_distribution, direction='greater')
        p_less = calculate_p_value_one_tailed(observed_effect, null_distribution, direction='less')

        # Save results
        save_permutation_results(
            sess_id, conditions_json, observed_effect, null_distribution,
            p_two_tailed, p_greater, p_less, n_permutations,
            len(trial_data['estim_on']), len(trial_data['estim_off'])
        )

    print("\nPermutation tests complete!")


def get_trial_data_for_condition(session_id, cond_dict):
    """
    Get trial-level data for a specific condition combination.

    Returns dict with:
        'estim_on': list of is_hypothesized_choice values
        'estim_off': list of is_hypothesized_choice values
    """
    repo_conn = Connection("allen_data_repository")

    # Build query to match conditions - use same join structure as main query
    query = """
            SELECT t.is_hypothesized_choice, t.is_estim_on
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
            WHERE t.session_id = %s \
            """

    params = [session_id]

    # Add condition filters for behavioral parameters
    if 'trial_type' in cond_dict:
        query += " AND t.trial_type = %s"
        params.append(cond_dict['trial_type'])

    if 'noise_chance' in cond_dict:
        # Use tolerance for float comparison (within 0.001)
        query += " AND ABS(t.noise_chance - %s) < 0.001"
        params.append(cond_dict['noise_chance'])

    # Build estim parameter conditions
    # For estim_off trials, these should be NULL or don't matter
    # For estim_on trials, they must match
    estim_conditions = []

    if 'polarity' in cond_dict:
        estim_conditions.append(f"(t.is_estim_on = 0 OR ep.polarity = %s)")
        params.append(cond_dict['polarity'])

    if 'shape' in cond_dict:
        estim_conditions.append(f"(t.is_estim_on = 0 OR ep.shape = %s)")
        params.append(cond_dict['shape'])

    if 'num_channels' in cond_dict:
        estim_conditions.append(f"(t.is_estim_on = 0 OR ep.num_channels = %s)")
        params.append(cond_dict['num_channels'])

    if 'a1' in cond_dict:
        # Use tolerance for float comparison
        estim_conditions.append(f"(t.is_estim_on = 0 OR ABS(ep.a1 - %s) < 0.01)")
        params.append(cond_dict['a1'])

    if 'post_stim_refractory_period' in cond_dict:
        # Use tolerance for float comparison
        estim_conditions.append(f"(t.is_estim_on = 0 OR ABS(ep.post_stim_refractory_period - %s) < 1.0)")
        params.append(cond_dict['post_stim_refractory_period'])

    if 'enable_charge_recovery' in cond_dict:
        estim_conditions.append(f"(t.is_estim_on = 0 OR ep.enable_charge_recovery = %s)")
        params.append(cond_dict['enable_charge_recovery'])

    # Add all estim conditions with AND
    if estim_conditions:
        query += " AND " + " AND ".join(estim_conditions)

    repo_conn.execute(query, tuple(params))
    results = repo_conn.fetch_all()

    # Separate into estim_on and estim_off
    estim_on = [row[0] for row in results if row[1] == 1]
    estim_off = [row[0] for row in results if row[1] == 0]

    return {'estim_on': estim_on, 'estim_off': estim_off}


def run_single_permutation_test(estim_on_outcomes, estim_off_outcomes, n_permutations):
    """
    Run permutation test by shuffling estim_on/estim_off labels.

    Args:
        estim_on_outcomes: List of binary outcomes (0/1) for estim_on trials
        estim_off_outcomes: List of binary outcomes (0/1) for estim_off trials
        n_permutations: Number of permutations

    Returns:
        List of permuted effect sizes
    """
    # Combine all data
    all_outcomes = np.array(estim_on_outcomes + estim_off_outcomes)
    n_estim_on = len(estim_on_outcomes)
    n_total = len(all_outcomes)

    null_distribution = []

    for _ in range(n_permutations):
        # Randomly shuffle the group labels
        shuffled_indices = np.random.permutation(n_total)

        # Split based on original group sizes
        perm_estim_on = all_outcomes[shuffled_indices[:n_estim_on]]
        perm_estim_off = all_outcomes[shuffled_indices[n_estim_on:]]

        # Calculate effect size
        perm_on_pct = np.mean(perm_estim_on) * 100
        perm_off_pct = np.mean(perm_estim_off) * 100
        perm_effect = perm_on_pct - perm_off_pct

        null_distribution.append(perm_effect)

    return null_distribution


def calculate_p_value_two_tailed(observed, null_distribution):
    """Calculate two-tailed p-value"""
    null_array = np.array(null_distribution)
    p_value = np.mean(np.abs(null_array) >= np.abs(observed))
    return float(p_value)


def calculate_p_value_one_tailed(observed, null_distribution, direction='greater'):
    """Calculate one-tailed p-value"""
    null_array = np.array(null_distribution)
    if direction == 'greater':
        p_value = np.mean(null_array >= observed)
    else:  # 'less'
        p_value = np.mean(null_array <= observed)
    return float(p_value)


def save_permutation_results(session_id, conditions_json, observed_effect, null_distribution,
                             p_two_tailed, p_greater, p_less, n_permutations,
                             n_trials_on, n_trials_off):
    """Save permutation test results to database"""
    repo_conn = Connection("allen_data_repository")

    # Convert null distribution to JSON
    null_dist_json = json.dumps(null_distribution)

    repo_conn.execute("""
                      INSERT INTO EStimPermutationTests (session_id, conditions, observed_effect_size,
                                                         null_distribution,
                                                         p_value_two_tailed, p_value_greater, p_value_less,
                                                         n_permutations, n_trials_estim_on, n_trials_estim_off)
                      VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                      ON DUPLICATE KEY UPDATE observed_effect_size = VALUES(observed_effect_size),
                                              null_distribution    = VALUES(null_distribution),
                                              p_value_two_tailed   = VALUES(p_value_two_tailed),
                                              p_value_greater      = VALUES(p_value_greater),
                                              p_value_less         = VALUES(p_value_less),
                                              n_permutations       = VALUES(n_permutations),
                                              n_trials_estim_on    = VALUES(n_trials_estim_on),
                                              n_trials_estim_off   = VALUES(n_trials_estim_off)
                      """, (session_id, conditions_json, observed_effect, null_dist_json,
                            p_two_tailed, p_greater, p_less, n_permutations,
                            n_trials_on, n_trials_off))


def create_permutation_test_table():
    """Create table for storing permutation test results"""
    repo_conn = Connection("allen_data_repository")

    repo_conn.execute("""
                      CREATE TABLE IF NOT EXISTS EStimPermutationTests
                      (
                          session_id           VARCHAR(10) NOT NULL,
                          conditions           LONGTEXT    NOT NULL,
                          observed_effect_size FLOAT,
                          null_distribution    LONGTEXT,
                          p_value_two_tailed   FLOAT,
                          p_value_greater      FLOAT,
                          p_value_less         FLOAT,
                          n_permutations       INT,
                          n_trials_estim_on    INT,
                          n_trials_estim_off   INT,

                          PRIMARY KEY (session_id, conditions(500)),
                          FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
                      ) ENGINE = InnoDB
                        DEFAULT CHARSET = latin1
                      """)

    print("EStimPermutationTests table created/verified")


def main():
    # Run for specific session or all
    session_id = None  # or None for all sessions

    run_permutation_tests(
        session_id=session_id,
        n_permutations=10000,
        force_recompute=False
    )


if __name__ == '__main__':
    main()
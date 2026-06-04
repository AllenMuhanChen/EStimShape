import numpy as np
from clat.util.connection import Connection
import json
from tqdm import tqdm

from src.analysis.nafc.estim_parameter_classifier import EStimParameterClassifier
from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    METRIC_PCT_HYPOTHESIZED, METRIC_PCT_HYP_VS_DELTA)


def run_permutation_tests(session_id=None, n_permutations=1000, force_recompute=False,
                          algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED):
    """
    Run permutation tests for all condition combinations.

    Args:
        session_id      : Specific session to analyze, or None for all sessions
        n_permutations  : Number of permutations
        force_recompute : If True, recompute even if results exist
        algorithm_label : Which cutoff to apply (matches EStimEffects.algorithm_label).
                          'none' = no cutoff, raw data.
        metric          : Which EStimEffects metric row to test. For
                          'pct_hyp_vs_delta', trial-level data is filtered to drop
                          choice in {'rand', 'removed'}, plus trials where
                          trial_type is 'Removed Trial' and choice is 'match',
                          before permuting.
    """
    create_permutation_test_table()

    conn = Connection("allen_data_repository")

    if session_id:
        conn.execute("""
            SELECT session_id, conditions, estim_on_n_trials, estim_off_n_trials, effect_size
            FROM EStimEffects
            WHERE session_id = %s AND algorithm_label = %s AND metric = %s
        """, (session_id, algorithm_label, metric))
    else:
        conn.execute("""
            SELECT session_id, conditions, estim_on_n_trials, estim_off_n_trials, effect_size
            FROM EStimEffects
            WHERE algorithm_label = %s AND metric = %s
        """, (algorithm_label, metric))

    column_names = [desc[0] for desc in conn.my_cursor.description]
    conditions_to_test = conn.fetch_all()
    print(f"Found {len(conditions_to_test)} condition combinations to test "
          f"(algorithm='{algorithm_label}', metric='{metric}')")

    # Pre-fetch all cutoffs for this algorithm so we don't query per-row
    cutoffs = _fetch_all_cutoffs(algorithm_label)

    for row in tqdm(conditions_to_test, desc="Running permutation tests"):
        row_dict        = dict(zip(column_names, row))
        sess_id         = row_dict['session_id']
        conditions_json = row_dict['conditions']
        observed_effect = row_dict['effect_size']

        if not force_recompute:
            conn.execute("""
                SELECT 1 FROM EStimPermutationTests
                WHERE session_id = %s AND conditions = %s
                  AND algorithm_label = %s AND metric = %s
            """, (sess_id, conditions_json, algorithm_label, metric))
            if conn.fetch_all():
                continue

        cond_dict  = json.loads(conditions_json)
        max_trial_start = cutoffs.get((sess_id, conditions_json))

        trial_data = get_trial_data_for_condition(
            sess_id, cond_dict, max_trial_start=max_trial_start, metric=metric)

        if len(trial_data['estim_on']) == 0 or len(trial_data['estim_off']) == 0:
            print(f"Skipping {sess_id}, {cond_dict}: insufficient data")
            continue

        null_distribution = run_single_permutation_test(
            trial_data['estim_on'], trial_data['estim_off'], n_permutations
        )

        p_two_tailed = calculate_p_value_two_tailed(observed_effect, null_distribution)
        p_greater    = calculate_p_value_one_tailed(observed_effect, null_distribution, direction='greater')
        p_less       = calculate_p_value_one_tailed(observed_effect, null_distribution, direction='less')

        save_permutation_results(
            sess_id, conditions_json, algorithm_label, metric, observed_effect, null_distribution,
            p_two_tailed, p_greater, p_less, n_permutations,
            len(trial_data['estim_on']), len(trial_data['estim_off'])
        )

    print("\nPermutation tests complete!")


def _fetch_all_cutoffs(algorithm_label):
    """Return {(session_id, conditions_json): max_gen_id} for the given algorithm_label."""
    if algorithm_label == 'none':
        return {}
    conn = Connection("allen_data_repository")
    conn.execute("""
        SELECT session_id, conditions, max_trial_start FROM EStimSessionCutoffs
        WHERE algorithm_label = %s
    """, (algorithm_label,))
    return {(row[0], row[1]): row[2] for row in conn.fetch_all()}


def get_trial_data_for_condition(session_id, cond_dict, max_trial_start=None,
                                  metric=METRIC_PCT_HYPOTHESIZED):
    """
    Get trial-level data for a specific condition combination.

    Args:
        max_trial_start: if provided, only include trials with trial_start <= max_trial_start.
        metric         : matches the EStimEffects metric semantics. For
                         'pct_hyp_vs_delta', excludes rows whose choice is 'rand'
                         or 'removed', and rows where trial_type is 'Removed Trial'
                         and choice is 'match' — so the permutation null matches
                         what was summarised in EStimEffects.

    Returns dict with:
        'estim_on': list of is_hypothesized_choice values
        'estim_off': list of is_hypothesized_choice values
    """
    repo_conn = Connection("allen_data_repository")

    query = f"""
        SELECT t.is_hypothesized_choice, t.is_estim_on
        FROM EStimShapeTrials t
        LEFT JOIN ({EStimParameterClassifier.active_channel_sql_subquery()}) ep
          ON t.session_id = ep.session_id AND t.estim_spec_id = ep.estim_spec_id
        WHERE t.session_id = %s
    """
    params = [session_id]

    if metric == METRIC_PCT_HYP_VS_DELTA:
        query += " AND (t.choice IS NULL OR t.choice NOT IN ('rand', 'removed'))"
        query += " AND NOT (t.trial_type = 'Removed Trial' AND t.choice = 'match')"

    if max_trial_start is not None:
        query += " AND t.trial_start <= %s"
        params.append(max_trial_start)

    if 'trial_type' in cond_dict:
        query += " AND t.trial_type = %s"
        params.append(cond_dict['trial_type'])

    if 'noise_chance' in cond_dict:
        query += " AND ABS(t.noise_chance - %s) < 0.001"
        params.append(cond_dict['noise_chance'])

    if 'sample_length' in cond_dict:
        if cond_dict['sample_length'] is None:
            query += " AND t.sample_length IS NULL"
        else:
            query += " AND t.sample_length = %s"
            params.append(cond_dict['sample_length'])

    estim_conditions = []
    if 'polarity' in cond_dict:
        estim_conditions.append("(t.is_estim_on = 0 OR ep.polarity = %s)")
        params.append(cond_dict['polarity'])
    if 'shape' in cond_dict:
        estim_conditions.append("(t.is_estim_on = 0 OR ep.shape = %s)")
        params.append(cond_dict['shape'])
    if 'num_channels' in cond_dict:
        estim_conditions.append("(t.is_estim_on = 0 OR ep.num_channels = %s)")
        params.append(cond_dict['num_channels'])
    if 'a1' in cond_dict:
        estim_conditions.append("(t.is_estim_on = 0 OR ABS(ep.a1 - %s) < 0.01)")
        params.append(cond_dict['a1'])
    if 'post_stim_refractory_period' in cond_dict:
        estim_conditions.append("(t.is_estim_on = 0 OR ABS(ep.post_stim_refractory_period - %s) < 1.0)")
        params.append(cond_dict['post_stim_refractory_period'])
    if 'enable_charge_recovery' in cond_dict:
        estim_conditions.append("(t.is_estim_on = 0 OR ep.enable_charge_recovery = %s)")
        params.append(cond_dict['enable_charge_recovery'])

    if estim_conditions:
        query += " AND " + " AND ".join(estim_conditions)

    repo_conn.execute(query, tuple(params))
    results = repo_conn.fetch_all()

    estim_on  = [row[0] for row in results if row[1] == 1 and row[0] is not None]
    estim_off = [row[0] for row in results if row[1] == 0 and row[0] is not None]

    return {'estim_on': estim_on, 'estim_off': estim_off}


def run_single_permutation_test(estim_on_outcomes, estim_off_outcomes, n_permutations):
    all_outcomes = np.array(estim_on_outcomes + estim_off_outcomes)
    n_estim_on   = len(estim_on_outcomes)
    n_total      = len(all_outcomes)

    null_distribution = []
    for _ in range(n_permutations):
        shuffled_indices = np.random.permutation(n_total)
        perm_on  = all_outcomes[shuffled_indices[:n_estim_on]]
        perm_off = all_outcomes[shuffled_indices[n_estim_on:]]
        null_distribution.append(np.mean(perm_on) * 100 - np.mean(perm_off) * 100)

    return null_distribution


def calculate_p_value_two_tailed(observed, null_distribution):
    null_array = np.array(null_distribution)
    return float(np.mean(np.abs(null_array) >= np.abs(observed)))


def calculate_p_value_one_tailed(observed, null_distribution, direction='greater'):
    null_array = np.array(null_distribution)
    if direction == 'greater':
        return float(np.mean(null_array >= observed))
    return float(np.mean(null_array <= observed))


def save_permutation_results(session_id, conditions_json, algorithm_label, metric,
                             observed_effect, null_distribution,
                             p_two_tailed, p_greater, p_less,
                             n_permutations, n_trials_on, n_trials_off):
    conn = Connection("allen_data_repository")
    conn.execute("""
        INSERT INTO EStimPermutationTests
            (session_id, conditions, algorithm_label, metric,
             observed_effect_size, null_distribution,
             p_value_two_tailed, p_value_greater, p_value_less,
             n_permutations, n_trials_estim_on, n_trials_estim_off)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            observed_effect_size = VALUES(observed_effect_size),
            null_distribution    = VALUES(null_distribution),
            p_value_two_tailed   = VALUES(p_value_two_tailed),
            p_value_greater      = VALUES(p_value_greater),
            p_value_less         = VALUES(p_value_less),
            n_permutations       = VALUES(n_permutations),
            n_trials_estim_on    = VALUES(n_trials_estim_on),
            n_trials_estim_off   = VALUES(n_trials_estim_off)
    """, (session_id, conditions_json, algorithm_label, metric, observed_effect,
          json.dumps(null_distribution), p_two_tailed, p_greater, p_less,
          n_permutations, n_trials_on, n_trials_off))


def create_permutation_test_table():
    conn = Connection("allen_data_repository")
    conn.execute(f"""
        CREATE TABLE IF NOT EXISTS EStimPermutationTests
        (
            session_id           VARCHAR(10)  NOT NULL,
            conditions           LONGTEXT     NOT NULL,
            algorithm_label      VARCHAR(100) NOT NULL DEFAULT 'none',
            metric               VARCHAR(50)  NOT NULL DEFAULT '{METRIC_PCT_HYPOTHESIZED}',
            observed_effect_size FLOAT,
            null_distribution    LONGTEXT,
            p_value_two_tailed   FLOAT,
            p_value_greater      FLOAT,
            p_value_less         FLOAT,
            n_permutations       INT,
            n_trials_estim_on    INT,
            n_trials_estim_off   INT,

            PRIMARY KEY (session_id, conditions(500), algorithm_label(100), metric(50)),
            FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
        ) ENGINE = InnoDB DEFAULT CHARSET = latin1
    """)
    _migrate_permutation_test_table(conn)
    print("EStimPermutationTests table ready")


def _migrate_permutation_test_table(conn):
    """Bring legacy EStimPermutationTests tables forward — add algorithm_label, then metric, updating the PK after each."""
    # Step 1: algorithm_label column + PK
    conn.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = 'EStimPermutationTests'
          AND COLUMN_NAME  = 'algorithm_label'
    """)
    if conn.fetch_all()[0][0] == 0:
        print("Migrating EStimPermutationTests: adding algorithm_label column and updating PK...")
        conn.execute("ALTER TABLE EStimPermutationTests ADD COLUMN algorithm_label VARCHAR(100) NOT NULL DEFAULT 'none'")
        conn.execute("ALTER TABLE EStimPermutationTests DROP PRIMARY KEY")
        conn.execute("ALTER TABLE EStimPermutationTests ADD PRIMARY KEY (session_id, conditions(500), algorithm_label(100))")
        print("Migration complete")

    # Step 2: metric column
    conn.execute("""
        SELECT COUNT(*) FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME   = 'EStimPermutationTests'
          AND COLUMN_NAME  = 'metric'
    """)
    if conn.fetch_all()[0][0] == 0:
        print("Migrating EStimPermutationTests: adding metric column...")
        conn.execute(
            f"ALTER TABLE EStimPermutationTests ADD COLUMN metric VARCHAR(50) NOT NULL DEFAULT '{METRIC_PCT_HYPOTHESIZED}'"
        )
        print("Column added (existing rows default to pct_hypothesized)")

    # Step 3: metric in PK
    conn.execute("""
        SELECT COUNT(*) FROM information_schema.KEY_COLUMN_USAGE
        WHERE TABLE_SCHEMA    = DATABASE()
          AND TABLE_NAME      = 'EStimPermutationTests'
          AND CONSTRAINT_NAME = 'PRIMARY'
          AND COLUMN_NAME     = 'metric'
    """)
    if conn.fetch_all()[0][0] == 0:
        print("Migrating EStimPermutationTests: updating PK to include metric...")
        conn.execute("""
            ALTER TABLE EStimPermutationTests
              DROP PRIMARY KEY,
              ADD PRIMARY KEY (session_id, conditions(500), algorithm_label(100), metric(50))
        """)
        print("Migration complete")


def main():
    run_permutation_tests(
        session_id="260603_0",
        n_permutations=10000,
        force_recompute=True,
        algorithm_label='None',
        metric=METRIC_PCT_HYP_VS_DELTA,
    )


if __name__ == '__main__':
    main()

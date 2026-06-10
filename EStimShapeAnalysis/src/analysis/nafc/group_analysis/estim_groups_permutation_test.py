import numpy as np
from clat.util.connection import Connection
import json
from tqdm import tqdm

from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    METRIC_PCT_HYPOTHESIZED, METRIC_PCT_HYP_VS_DELTA,
    read_trial_data_from_repository, split_data_by_conditions,
    _filter_for_metric, _normalize_cond_key, _DEFAULT_BEHAVIORAL_CONDITIONS)


def run_permutation_tests(session_ids=None, n_permutations=1000, force_recompute=False,
                          algorithm_label='none', metric=METRIC_PCT_HYPOTHESIZED):
    """
    Run permutation tests for all condition combinations.

    Args:
        session_ids      : Specific session to analyze, or None for all sessions
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

    if session_ids:
        conn.execute("""
            SELECT session_id, conditions, estim_on_n_trials, estim_off_n_trials, effect_size
            FROM EStimEffects
            WHERE session_id = %s AND algorithm_label = %s AND metric = %s
        """, (session_ids, algorithm_label, metric))
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

    # Replace rather than accumulate. The conditions string is part of the primary
    # key, so old-format rows (e.g. a previous grouping scheme, or [2.0] vs 2.0)
    # would otherwise linger as orphans and double-count the same physical
    # condition in the population tests. On a full recompute, clear the rows for
    # the sessions/metric being recomputed first.
    if force_recompute:
        if session_ids:
            conn.execute(
                "DELETE FROM EStimPermutationTests WHERE session_id = %s AND algorithm_label = %s AND metric = %s",
                (session_ids, algorithm_label, metric))
        else:
            conn.execute(
                "DELETE FROM EStimPermutationTests WHERE algorithm_label = %s AND metric = %s",
                (algorithm_label, metric))

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

        if observed_effect is None:
            print(f"Skipping {sess_id}, {cond_dict}: observed effect is None")
            continue

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


# Cache the per-session trial frame so run_permutation_tests doesn't re-query the
# full session for every condition. The frame is treated as read-only (the split
# copies any slice it keeps), so sharing it across conditions is safe.
_SESSION_DATA_CACHE = {}


def _read_session_data_cached(session_id):
    df = _SESSION_DATA_CACHE.get(session_id)
    if df is None:
        df = read_trial_data_from_repository(session_id)
        _SESSION_DATA_CACHE[session_id] = df
    return df


def get_trial_data_for_condition(session_id, cond_dict, max_trial_start=None,
                                  metric=METRIC_PCT_HYPOTHESIZED):
    """
    Trial-level outcomes for one condition, reusing the SAME split that
    analyze_estim_by_condition uses to produce EStimEffects. This guarantees the
    permutation null (and the n's shown downstream) come from exactly the estim-on /
    estim-off trials the observed effect size summarises — including:
      - keying the estim-on side by whatever estim conditions produced the row
        (e.g. estim_spec_id), instead of a hard-coded parameter list, and
      - restricting the estim-off baseline to the gen_id window the estim condition
        actually ran in.
    The previous implementation re-filtered trials with its own SQL that had no
    estim_spec_id branch (so the estim-on n pooled every spec) and never applied the
    gen window (so the estim-off n was far too high). Both diverged from EStimEffects.

    Args:
        max_trial_start: optional trial_start cutoff, applied through the same path
                         the effect pipeline uses (after the gen window, both groups).
        metric         : matches EStimEffects metric semantics; 'pct_hyp_vs_delta'
                         drops choice in {'rand','removed'} and removed-trial matches.

    Returns dict with 'estim_on' / 'estim_off': lists of is_hypothesized_choice values.
    """
    data = _read_session_data_cached(session_id)

    # The stored condition dict mixes behavioral and estim keys; split them the same
    # way run_pipeline does so the regrouping reproduces the row exactly.
    behavioral_keys = [k for k in cond_dict if k in _DEFAULT_BEHAVIORAL_CONDITIONS]
    estim_keys      = [k for k in cond_dict if k not in _DEFAULT_BEHAVIORAL_CONDITIONS]

    # Apply the cutoff through split_data_by_conditions (keyed to this condition only)
    # so the gen window is derived before the cutoff, identically to the effect pipeline.
    cutoffs = {json.dumps(cond_dict): max_trial_start} if max_trial_start is not None else None

    comparisons = split_data_by_conditions(data, behavioral_keys, estim_keys,
                                            trial_start_cutoffs=cutoffs)

    target_key = _normalize_cond_key(cond_dict)
    for comp in comparisons:
        merged = {**comp['behavioral_conditions'], **comp['estim_conditions']}
        if _normalize_cond_key(merged) == target_key:
            on_df  = _filter_for_metric(comp['estim_on_data'], metric)
            off_df = _filter_for_metric(comp['estim_off_data'], metric)
            return {
                'estim_on':  on_df['is_hypothesized_choice'].dropna().tolist(),
                'estim_off': off_df['is_hypothesized_choice'].dropna().tolist(),
            }

    return {'estim_on': [], 'estim_off': []}


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
    metrics = [METRIC_PCT_HYPOTHESIZED, METRIC_PCT_HYP_VS_DELTA]
    for metric in metrics:
        run_permutation_tests(
            session_ids=None,
            n_permutations=10000,
            force_recompute=True,
            algorithm_label='None',
            metric=metric,
        )


if __name__ == '__main__':
    main()

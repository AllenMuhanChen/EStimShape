"""
live_stats.py
-------------
Run the by-condition estim analysis + permutation tests for the *current* live session and
gather the single-session statistics the live GUI's Stats panel visualizes.

This is the same pipeline the offline group analysis uses, pointed at one session:

    1. analyze_estim_by_condition.run_pipeline([session_id])  -> EStimEffects rows
    2. estim_groups_permutation_test.run_permutation_tests(session_id) -> EStimPermutationTests
    3. max_estim_per_experiment._build_max_stat_for_session(...)        -> max-stat test
       max_estim_per_experiment.compute_exceedance_count_stats(...)     -> exceedance test

Because steps 1-2 write to allen_data_repository, after a run this session's results are in
the repository exactly as if produced offline — so running max_estim_per_experiment.py (or any
group analysis) afterwards will include this live session.

Everything here is synchronous and DB-bound; the caller runs it off a button press and should
expect it to block for a few seconds (longer for large n_permutations).
"""

from src.repository.export_to_repository import write_session_to_db
from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    run_pipeline, METRIC_PCT_HYPOTHESIZED, METRIC_PCT_HYP_VS_DELTA,
)
from src.analysis.nafc.group_analysis import estim_groups_permutation_test as _perm
from src.analysis.nafc.group_analysis.max_estim_per_experiment import (
    _build_max_stat_for_session, compute_exceedance_count_stats, DEFAULT_MIN_TRIALS,
)
import numpy as np

# We always store/read under this label for live runs: 'None' = raw data, no session cutoff
# (matches max_estim_per_experiment.main()). The live session has no EStimSessionCutoffs entry.
ALGORITHM_LABEL = 'None'

# Metric choices exposed in the GUI: (db_value, human_label).
METRICS = [
    (METRIC_PCT_HYPOTHESIZED, '% Hypothesized'),
    (METRIC_PCT_HYP_VS_DELTA, '% Hyp vs Delta'),
]


def run_session_stats(session_id, date, metric, n_permutations=1000,
                      min_trials=DEFAULT_MIN_TRIALS, studentize=False,
                      algorithm_label=ALGORITHM_LABEL, progress=None):
    """Compute + persist effects/permutation tests for one session, then return its single-
    session max-stat and exceedance-count results for plotting.

    date: session date (datetime.date) used to ensure the Sessions row the EStimEffects /
          EStimPermutationTests foreign key requires.
    progress: optional callback(str) for status updates.

    Returns a dict (see keys at the bottom). max_stat / exceedance are None when the session
    has no condition with >= min_trials in both groups.
    """
    def _say(msg):
        if progress is not None:
            progress(msg)

    # The Sessions row is the FK target for EStimEffects/EStimPermutationTests. It normally
    # already exists (EStimShapeTrials shares the FK), but ensure it idempotently to be safe.
    if date is not None:
        write_session_to_db(_perm.Connection("allen_data_repository"), session_id, date)

    # The permutation module caches each session's trial frame; in a live session new trials
    # keep arriving, so drop the cache to force a fresh read of the just-compiled trials.
    _perm._SESSION_DATA_CACHE.clear()

    _say('Computing condition effects…')
    run_pipeline(session_ids=[session_id], algorithm_label=algorithm_label,
                 force_recompute=True, show_sliding_window=False)

    _say(f'Running {n_permutations} permutations…')
    run_permutation_tests = _perm.run_permutation_tests
    run_permutation_tests(session_ids=session_id, n_permutations=n_permutations,
                          force_recompute=True, algorithm_label=algorithm_label, metric=metric)

    unit = 'z' if studentize else '%'

    _say('Building max-stat test…')
    max_stat = _build_max_stat_for_session(
        session_id, algorithm_label, metric, min_trials=min_trials, studentize=studentize)
    max_stat_out = None
    if max_stat is not None:
        null = np.asarray(max_stat['max_stat_null'], dtype=float)
        max_stat_out = {
            'observed':  float(max_stat['observed_signed']),
            'null_mean': float(np.mean(null)),
            'null_95':   float(np.percentile(null, 95)),
            'p_value':   float(max_stat['p_value']),
            'best_cond': max_stat['best_cond_dict'],
        }

    _say('Building exceedance-count test…')
    exceedance = compute_exceedance_count_stats(
        only_session_ids=[session_id], algorithm_label=algorithm_label, metric=metric,
        min_trials=min_trials, studentize=studentize)

    return {
        'session_id':     session_id,
        'metric':         metric,
        'studentize':     studentize,
        'min_trials':     min_trials,
        'n_permutations': n_permutations,
        'algorithm_label': algorithm_label,
        'unit':           unit,
        'max_stat':       max_stat_out,
        'exceedance':     exceedance,
    }

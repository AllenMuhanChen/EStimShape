"""
End-to-end orchestrator: recompile every EStimShape session from the
experimental DBs, rebuild EStimEffects, and re-run permutation tests for
both metrics.

Flow per call to ``run_full_pipeline``:
    1. For each session_id, switch the global context via
       ``apply_session_context`` and run ``estim_compile.main()``. This
       repopulates EStimShapeTrials (incl. the new ``choice`` column) and
       EStimParameters from each session's own experiment DB.
    2. Run ``analyze_estim_by_condition.run_pipeline`` once across all
       sessions. This writes both metric rows (``pct_hypothesized`` and
       ``pct_hyp_vs_delta``) per condition into EStimEffects.
    3. Run permutation tests once per metric across all sessions.

Sessions whose compile fails (missing DB, parse error, etc.) are reported
but do not abort the run — partial recompiles are recoverable.
"""

from __future__ import annotations

import traceback

from clat.util.connection import Connection

from src.analysis.nafc import estim_compile
from src.analysis.nafc.group_analysis import analyze_estim_by_condition
from src.analysis.nafc.group_analysis import estim_groups_permutation_test
from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    ALL_METRICS,
    METRIC_PCT_HYPOTHESIZED,
    METRIC_PCT_HYP_VS_DELTA,
)
from src.startup.apply_session_context import apply_session_context


def _all_existing_session_ids():
    """Every session_id already present in EStimShapeTrials, in DB order."""
    conn = Connection("allen_data_repository")
    conn.execute("SELECT DISTINCT session_id FROM EStimShapeTrials ORDER BY session_id")
    return [row[0] for row in conn.fetch_all()]


def recompile_sessions(session_ids):
    """
    Run estim_compile for each session, switching DB context appropriately.
    Returns the list of session_ids that raised during compile.
    """
    failed = []
    for sid in session_ids:
        print(f"\n========== compiling session {sid} ==========")
        try:
            apply_session_context(sid)
            estim_compile.main()
        except Exception:
            traceback.print_exc()
            failed.append(sid)
    return failed


def run_full_pipeline(
    session_ids=None,
    *,
    algorithm_label: str = 'None',
    n_permutations: int = 10000,
    metrics=ALL_METRICS,
    skip_compile: bool = False,
    skip_analyze: bool = False,
    skip_permutation: bool = False,
):
    """
    Recompile + analyze + permutation-test across the requested sessions.

    Args:
        session_ids     : list of session_ids to process. ``None`` uses every
                          session currently present in EStimShapeTrials.
        algorithm_label : cutoff label for EStimEffects / EStimPermutationTests
                          rows. 'None' / 'none' = no cutoff (raw data).
        n_permutations  : permutations per (session, condition, metric).
        metrics         : iterable of metric identifiers to permutation-test.
                          Defaults to both ``pct_hypothesized`` and
                          ``pct_hyp_vs_delta``.
        skip_compile / skip_analyze / skip_permutation : flip each step off
                          when you want to re-run only the later stages.

    Returns the list of session_ids whose compile raised, for follow-up.
    """
    if session_ids is None:
        session_ids = _all_existing_session_ids()
        print(f"[orchestrator] discovered {len(session_ids)} sessions in EStimShapeTrials")
    else:
        session_ids = list(session_ids)

    failed_compile = []
    if not skip_compile:
        failed_compile = recompile_sessions(session_ids)
        if failed_compile:
            print(f"[orchestrator] compile failed for: {failed_compile}")

    if not skip_analyze:
        print("\n========== analyze_estim_by_condition (all sessions) ==========")
        # Sliding-window plots block on plt.show() — disable for bulk runs.
        analyze_estim_by_condition.run_pipeline(
            session_ids=session_ids,
            algorithm_label=algorithm_label,
            force_recompute=True,
            show_sliding_window=False,
        )

    if not skip_permutation:
        for metric in metrics:
            print(f"\n========== permutation tests (metric={metric}) ==========")
            estim_groups_permutation_test.run_permutation_tests(
                session_ids=None,
                n_permutations=n_permutations,
                force_recompute=True,
                algorithm_label=algorithm_label,
                metric=metric,
            )

    print("\n[orchestrator] done")
    if failed_compile:
        print(f"[orchestrator] sessions that failed compile: {failed_compile}")
    return failed_compile


def main():
    # Edit this list to target specific sessions; leave as None to process
    # every session already present in EStimShapeTrials.
    session_ids = None

    run_full_pipeline(
        session_ids=session_ids,
        algorithm_label='None',
        n_permutations=10000,
        metrics=(METRIC_PCT_HYPOTHESIZED, METRIC_PCT_HYP_VS_DELTA),
    )


if __name__ == '__main__':
    main()

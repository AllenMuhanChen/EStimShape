"""
Batch-run AxisCodingAnalysis across a list of sessions.

Each iteration switches the in-process ``context`` module to the given
session via ``apply_session_context`` (NO file write, NO importlib.reload
— see startup/apply_session_context.py for the rationale), constructs a
fresh AxisCodingAnalysis (with the same strategy/rf_filter/etc. config as
``axis_coding_analysis.main()``), and runs compile + analyze.

The first run for a session does compile_and_export (raw spikes → repo).

Failures on one session are logged but don't abort the batch.
"""

from __future__ import annotations

import traceback
from typing import Callable, Iterable, Optional

from src.startup.apply_session_context import run_axis_coding_for_session


def _session_has_metrics(session_id: str) -> bool:
    """True if AxisCodingFitMetrics already has any row for ``session_id``."""
    from clat.util.connection import Connection
    repo_conn = Connection("allen_data_repository")
    repo_conn.execute(
        "SELECT 1 FROM AxisCodingFitMetrics WHERE session_id = %s LIMIT 1",
        params=(session_id,),
    )
    return repo_conn.fetch_one() is not None


def run_batch(
    session_ids: Iterable[str],
    *,
    channels=("Cluster",),
    analyzer_kwargs_factory: Optional[Callable[[], dict]] = None,
    recompute: bool = False,
) -> dict:
    """
    Run axis coding on each ``session_id``.

    ``analyzer_kwargs_factory`` is called fresh per session (after the
    context switch) so any mutable state captured in those kwargs —
    rf_filter, strategy lambdas reading ``context``, etc. — gets a clean
    instance rooted in the active session. Defaults to the project-wide
    ``make_default_analyzer_kwargs`` from axis_coding_analysis.

    When ``recompute=False`` (default), any session that already has rows
    in AxisCodingFitMetrics is skipped — useful for resuming a batch after
    a partial failure without redoing successful sessions.
    """
    if analyzer_kwargs_factory is None:
        from src.analysis.ga.axis_coding.axis_coding_analysis import (
            make_default_analyzer_kwargs,
        )
        analyzer_kwargs_factory = make_default_analyzer_kwargs

    out: dict = {}
    for session_id in session_ids:
        print(f"\n========== {session_id} ==========")
        if not recompute and _session_has_metrics(session_id):
            print(f"[batch] {session_id} SKIPPED (already has AxisCodingFitMetrics rows; "
                  f"pass recompute=True to override)")
            out[session_id] = "skipped"
            continue
        try:
            out[session_id] = run_axis_coding_for_session(
                session_id,
                channels=channels,
                **analyzer_kwargs_factory(),
            )
        except Exception as exc:
            print(f"[batch] {session_id} FAILED: {exc}")
            traceback.print_exc()
            out[session_id] = None
    return out


def list_all_session_ids() -> list[str]:
    """All session_ids in allen_data_repository.Sessions, newest first."""
    from clat.util.connection import Connection
    repo_conn = Connection("allen_data_repository")
    repo_conn.execute("SELECT session_id FROM Sessions ORDER BY session_date DESC")
    return [row[0] for row in repo_conn.fetch_all()]


def main(recompute: bool = False):
    session_ids = list_all_session_ids()
    print(f"[batch] running on {len(session_ids)} sessions "
          f"(recompute={recompute}): {session_ids}")
    run_batch(session_ids, channels=("Cluster",), recompute=recompute)


if __name__ == "__main__":
    main()

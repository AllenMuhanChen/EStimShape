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


def run_batch(
    session_ids: Iterable[str],
    *,
    channels=("Cluster",),
    analyzer_kwargs_factory: Optional[Callable[[], dict]] = None,
) -> dict:
    """
    Run axis coding on each ``session_id``.

    ``analyzer_kwargs_factory`` is called fresh per session (after the
    context switch) so any mutable state captured in those kwargs —
    rf_filter, strategy lambdas reading ``context``, etc. — gets a clean
    instance rooted in the active session. Defaults to the project-wide
    ``make_default_analyzer_kwargs`` from axis_coding_analysis.
    """
    if analyzer_kwargs_factory is None:
        from src.analysis.ga.axis_coding.axis_coding_analysis import (
            make_default_analyzer_kwargs,
        )
        analyzer_kwargs_factory = make_default_analyzer_kwargs

    out: dict = {}
    for session_id in session_ids:
        print(f"\n========== {session_id} ==========")
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


def main():
    session_ids = [
        "260426_0",
        # "260420_1",
        # ...
    ]
    run_batch(session_ids, channels=("Cluster",))


if __name__ == "__main__":
    main()

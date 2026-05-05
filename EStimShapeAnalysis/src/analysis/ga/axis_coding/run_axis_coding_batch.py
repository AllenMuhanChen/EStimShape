"""
Batch-run AxisCodingAnalysis across a list of sessions.

Each iteration switches the in-process ``context`` module to the given
session via ``apply_session_context`` (NO file write, NO importlib.reload
— see startup/apply_session_context.py for the rationale), then constructs
a fresh AxisCodingAnalysis and runs compile + analyze.

The first run for a session does compile_and_export (raw spikes → repo);
subsequent calls within the same Python process can be sped up by passing
a precomputed ``compiled_data`` dataframe via ``run_axis_coding_for_session``.

Failures on one session are logged but don't abort the batch.
"""

from __future__ import annotations

import traceback
from typing import Iterable

from src.startup.apply_session_context import run_axis_coding_for_session


def run_batch(session_ids: Iterable[str], **analyzer_kwargs) -> dict:
    """Run axis coding on each session_id in turn. Returns dict[session, result]."""
    out = {}
    for session_id in session_ids:
        print(f"\n========== {session_id} ==========")
        try:
            out[session_id] = run_axis_coding_for_session(
                session_id, **analyzer_kwargs,
            )
        except Exception as exc:
            print(f"[batch] {session_id} FAILED: {exc}")
            traceback.print_exc()
            out[session_id] = None
    return out


def main():
    # Edit this list as needed.
    session_ids = [
        "260426_0",
        # "260420_1",
        # ...
    ]
    run_batch(session_ids, channels=("Cluster",))


if __name__ == "__main__":
    main()

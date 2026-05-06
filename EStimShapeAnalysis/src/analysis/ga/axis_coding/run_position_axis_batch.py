"""
Batch-run the position / composition / independence analyses across a list
of sessions.

For each session_id:
  1. ``apply_session_context(session_id)`` switches the in-process context
     module — same mechanism as run_axis_coding_batch.py.
  2. The session's prepared dataframe is loaded once.
  3. Every ``axis_coding_*.json`` in the session's save_dir is processed
     by ``position_along_axis.process_json`` — three figures written
     alongside each JSON, plus DB upserts into AxisCompositionMetrics
     and AxisIndependenceMetrics when ``write_to_db=True`` (default).

Failures on one session are logged but don't abort the batch. Failures
on individual JSONs are caught inside ``process_json``.
"""

from __future__ import annotations

import glob
import os
import traceback
from typing import Iterable, Optional

from src.startup import context
from src.startup.apply_session_context import apply_session_context


def _save_dir_for_session(session_id: str) -> str:
    """
    Mirror PlotTopNAnalysis.parse_data_type's save_path convention:
      /home/connorlab/Documents/plots/{session_id}/axis_coding
    Override by setting the env var ESTIMSHAPE_PLOTS_BASE.
    """
    base = os.environ.get(
        "ESTIMSHAPE_PLOTS_BASE",
        "/home/connorlab/Documents/plots",
    )
    return os.path.join(base, str(session_id), "axis_coding")


def run_batch(
    session_ids: Iterable[str],
    *,
    unit_name: str = "Cluster",
    write_to_db: bool = True,
    top_orth: int = 3,
    n_bins: int = 9,
    z_range: float = 2.0,
    top_k_composition: int = 5,
    n_position_bins: int = 5,
    save_dir_override: Optional[str] = None,
) -> dict:
    """
    Run the three position-axis figures + DB upserts on each ``session_id``.

    ``unit_name`` should match the ``unit_name`` used by the original
    AxisCodingAnalysis run for these JSONs (typically "Cluster"). The
    AxisCompositionMetrics and AxisIndependenceMetrics rows use this name
    so a ``JOIN`` on (session_id, unit_name, component_type, strategy)
    against AxisCodingFitMetrics works.
    """
    # Local imports so module import doesn't pull pandas/sklearn unless
    # we're actually running the batch.
    from src.analysis.ga.axis_coding.position_along_axis import (
        _per_stim_components,
        _prepare_session_df,
        process_json,
    )

    repo_conn = None
    if write_to_db:
        try:
            from clat.util.connection import Connection
            repo_conn = Connection("allen_data_repository")
        except Exception as exc:
            print(
                f"[batch] could not open allen_data_repository connection ({exc}); "
                f"continuing without DB writes."
            )
            repo_conn = None

    out: dict = {}
    for session_id in session_ids:
        print(f"\n========== {session_id} ==========")
        try:
            apply_session_context(session_id)
            save_dir = save_dir_override or _save_dir_for_session(session_id)
            if not os.path.isdir(save_dir):
                print(f"[batch] {session_id}: save_dir not found ({save_dir}); skipping.")
                out[session_id] = "missing"
                continue

            json_paths = sorted(glob.glob(os.path.join(save_dir, "axis_coding_*.json")))
            if not json_paths:
                print(f"[batch] {session_id}: no axis_coding_*.json in {save_dir}")
                out[session_id] = "empty"
                continue

            print(f"[batch] {session_id}: {len(json_paths)} JSONs in {save_dir}")
            df = _prepare_session_df(session_id)
            cache: dict = {}

            def factory(component_type: str) -> dict:
                if component_type not in cache:
                    cache[component_type] = _per_stim_components(df, component_type)
                return cache[component_type]

            n_ok = 0
            for path in json_paths:
                print(f"\n[{os.path.basename(path)}]")
                try:
                    if process_json(
                        path, factory,
                        top_orth=top_orth,
                        n_bins=n_bins,
                        z_range=z_range,
                        top_k_composition=top_k_composition,
                        n_position_bins=n_position_bins,
                        session_id=session_id,
                        unit_name=unit_name,
                        repo_conn=repo_conn,
                    ) is not None:
                        n_ok += 1
                except Exception as exc:
                    print(f"  [error] {exc}")
                    traceback.print_exc()

            out[session_id] = n_ok
            print(f"[batch] {session_id}: {n_ok}/{len(json_paths)} OK")
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


def main():
    # Edit these in-place rather than via CLI.
    session_ids = list_all_session_ids()
    unit_name = "Cluster"
    write_to_db = True

    print(
        f"[batch] {len(session_ids)} sessions  "
        f"unit_name={unit_name}  write_to_db={write_to_db}"
    )
    summary = run_batch(
        session_ids,
        unit_name=unit_name,
        write_to_db=write_to_db,
    )
    print("\n[batch] summary:")
    for sid, status in summary.items():
        print(f"  {sid}: {status}")


if __name__ == "__main__":
    main()

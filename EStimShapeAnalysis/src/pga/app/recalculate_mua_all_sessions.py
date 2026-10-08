"""
Run recalculate_mua_ga on every GA session whose repository has no MUA data yet.

A session counts as done when MUASpikeResponses already holds rows, under that
session's MUA metric (its mua_threshold_k / mua_block_size GAVars), for tasks
of its "<session_id>_ga" repository experiment. Everything else gets the full
recalculate_mua_ga run: MUAChannelResponses backfill, driving-response
recompute in the session's GA DB, and the MUASpikeResponses export.

Sessions are discovered from the GA databases on the server
(allen_ga_exp_<date>_<loc>). A session that fails is reported and the run moves
on to the next one. The original session context is restored at the end.
"""

from __future__ import annotations

import traceback

from clat.util.connection import Connection

from src.pga.app import recalculate_mua_ga
from src.repository.export_to_repository import read_session_id_and_date_from_db_name
from src.startup import context
from src.startup.apply_session_context import apply_session_context

GA_DB_PREFIX = "allen_ga_exp_"
REPOSITORY_DB = "allen_data_repository"


def main():
    # ---- Parameters -------------------------------------------------------
    # None = every GA database on the server; or a list like ["260702_0", "260708_0"].
    session_ids = None
    # Sessions to never touch (e.g. known-broken recordings).
    exclude_session_ids = []
    # True = re-run even sessions that already have MUASpikeResponses rows.
    rerun_already_done = False
    # True = only print which sessions would be recalculated; changes nothing.
    dry_run = False
    # ----------------------------------------------------------------------

    run_all_sessions(session_ids=session_ids,
                     exclude_session_ids=exclude_session_ids,
                     rerun_already_done=rerun_already_done,
                     dry_run=dry_run)


def run_all_sessions(session_ids=None, exclude_session_ids=(), rerun_already_done=False,
                     dry_run=False):
    original_ga_database = context.ga_database
    original_session_id, _ = read_session_id_and_date_from_db_name(original_ga_database)

    if session_ids is None:
        session_ids = all_ga_session_ids()
        print(f"[mua-all] found {len(session_ids)} GA sessions on the server")
    session_ids = [s for s in session_ids if s not in set(exclude_session_ids)]

    done, recalculated, failed, would_run = [], [], [], []
    try:
        for session_id in session_ids:
            print(f"\n========== {session_id} ==========")
            try:
                apply_session_context(session_id)
                metric = context.ga_config.mua_metric()
                n_rows = count_mua_repository_rows(session_id, metric)
            except Exception:
                traceback.print_exc()
                failed.append(session_id)
                continue

            if n_rows > 0 and not rerun_already_done:
                print(f"[mua-all] {session_id}: already has {n_rows} MUASpikeResponses rows "
                      f"under '{metric}', skipping.")
                done.append(session_id)
                continue
            if dry_run:
                print(f"[mua-all] {session_id}: would recalculate (rows under '{metric}': {n_rows}).")
                would_run.append(session_id)
                continue

            try:
                recalculate_mua_ga.main()
                recalculated.append(session_id)
            except Exception:
                traceback.print_exc()
                failed.append(session_id)
    finally:
        apply_session_context(original_session_id)

    print("\n========== summary ==========")
    print(f"already done ({len(done)}): {done}")
    if dry_run:
        print(f"would recalculate ({len(would_run)}): {would_run}")
    else:
        print(f"recalculated ({len(recalculated)}): {recalculated}")
    print(f"FAILED ({len(failed)}): {failed}")
    return {"done": done, "recalculated": recalculated, "failed": failed, "would_run": would_run}


def all_ga_session_ids() -> list[str]:
    """Session ids of every allen_ga_exp_<date>_<loc> database on the server, oldest first."""
    conn = Connection(REPOSITORY_DB)
    conn.execute("SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME LIKE %s",
                 (GA_DB_PREFIX + "%",))
    db_names = [row[0] for row in conn.fetch_all()]
    session_ids = []
    for db_name in db_names:
        suffix = db_name[len(GA_DB_PREFIX):]
        date, _, loc = suffix.partition("_")
        if len(date) == 6 and date.isdigit() and loc.isdigit():  # skip templates / oddly named DBs
            session_ids.append(f"{date}_{loc}")
    return sorted(session_ids)


def count_mua_repository_rows(session_id: str, mua_metric: str) -> int:
    """MUASpikeResponses rows under mua_metric for this session's GA experiment tasks."""
    conn = Connection(REPOSITORY_DB)
    conn.execute("SHOW TABLES LIKE 'MUASpikeResponses'")
    if not conn.fetch_all():
        return 0
    conn.execute(
        """
        SELECT COUNT(*)
        FROM MUASpikeResponses msr
        JOIN TaskStimMapping tsm ON msr.task_id = tsm.task_id
        JOIN StimExperimentMapping sem ON tsm.stim_id = sem.stim_id
        WHERE sem.experiment_id = %s AND msr.mua_method = %s
        """,
        (f"{session_id}_ga", mua_metric),
    )
    return int(conn.fetch_all()[0][0])


if __name__ == "__main__":
    main()

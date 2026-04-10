"""
spike_cache_daemon.py
---------------------
Continuously polls the GA database for new task IDs and caches their spike
data using MultiFileParser.  Runs until interrupted (Ctrl-C or SIGTERM).

Usage:
    python -m src.intan.spike_cache_daemon

Optionally override the database / paths at the bottom of this file or by
editing context.py.
"""

import signal
import time
from typing import List

from clat.compile.task.compile_task_id import TaskIdCollector
from clat.util.connection import Connection

from src.intan.MultiFileParser import MultiFileParser
from src.startup import context

# ---------------------------------------------------------------------------
# Configuration — edit these or change context.py
# ---------------------------------------------------------------------------
POLL_INTERVAL_SECONDS = 30   # how often to check for new task IDs
GA_DATABASE      = context.ga_database
INTAN_PATH       = context.ga_intan_path
CACHE_PATH       = context.ga_parsed_spikes_path
# ---------------------------------------------------------------------------


def _get_all_task_ids(conn: Connection) -> List[int]:
    collector = TaskIdCollector(conn)
    return collector.collect_task_ids()


def _find_uncached(parser: MultiFileParser, all_task_ids: List[int]) -> List[int]:
    """Return the subset of task_ids not yet present in the cache."""
    _, _, missing = parser._load_cache(all_task_ids)
    return missing


def run(database: str = GA_DATABASE,
        intan_path: str = INTAN_PATH,
        cache_path: str = CACHE_PATH,
        poll_interval: int = POLL_INTERVAL_SECONDS):

    print(f"[daemon] Starting spike cache daemon")
    print(f"[daemon]   database  : {database}")
    print(f"[daemon]   intan path: {intan_path}")
    print(f"[daemon]   cache path: {cache_path}")
    print(f"[daemon]   poll every: {poll_interval}s")
    print("[daemon] Press Ctrl-C to stop.\n")

    parser = MultiFileParser(to_cache=True, cache_dir=cache_path)

    # ---- graceful shutdown ----
    running = True

    def _stop(sig, frame):
        nonlocal running
        print("\n[daemon] Caught signal — shutting down after current poll.")
        running = False

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    # ---------------------------

    conn = Connection(database)

    while running:
        try:
            all_task_ids = _get_all_task_ids(conn)

            if not all_task_ids:
                print("[daemon] No task IDs found in database yet.")
            else:
                missing = _find_uncached(parser, all_task_ids)

                if not missing:
                    print(f"[daemon] All {len(all_task_ids)} task IDs already cached.")
                else:
                    print(f"[daemon] {len(missing)} uncached task IDs "
                          f"(out of {len(all_task_ids)} total). Parsing...")

                    try:
                        spikes, epochs = parser.parse(missing, intan_path)

                        newly_cached = len(spikes)
                        still_missing = len(missing) - newly_cached
                        print(f"[daemon] Cached {newly_cached} task IDs.", end="")
                        if still_missing:
                            print(f"  {still_missing} still missing "
                                  f"(Intan files may not be written yet).", end="")
                        print()

                    except ValueError as e:
                        # No Intan files found for any of the missing task IDs —
                        # data may not be on disk yet, try again next poll.
                        print(f"[daemon] No Intan files found for missing task IDs "
                              f"({e}).  Will retry.")

        except Exception as e:
            print(f"[daemon] Unexpected error: {e}")

        if running:
            print(f"[daemon] Sleeping {poll_interval}s …")
            # Sleep in short increments so Ctrl-C is responsive
            for _ in range(poll_interval):
                if not running:
                    break
                time.sleep(1)

    print("[daemon] Stopped.")


if __name__ == "__main__":
    run()

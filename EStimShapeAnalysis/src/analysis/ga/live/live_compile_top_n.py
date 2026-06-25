"""
live_compile_top_n.py
---------------------
Headless live compiler for the GA top-N pipeline.

Polls the experiment DB on a timer and, each tick, compiles + exports ONLY the
choice trials that have completed since the previous poll — never recompiling
trials already in the repository. This keeps the repository up to date during a
running experiment without paying to re-parse every spike file each time (which
is what PlotTopNAnalysis.compile_and_export does in batch).

It is the GA analogue of live_estim_compile for the NAFC path: same idea
(seed a seen-set from the repo, diff each poll, compile only the new tasks),
but built generically on the `LiveAnalysis` driver + the `LiveCompilable`
interface that PlotTopNAnalysis implements.

Run:
    python -m src.analysis.ga.live.live_compile_top_n
"""

import time

from src.analysis.ga.plot_top_n import PlotTopNAnalysis
from src.analysis.live_analysis import LiveAnalysis

DEFAULT_POLL_SECONDS = 30


def main(poll_seconds: int = DEFAULT_POLL_SECONDS):
    analysis = PlotTopNAnalysis(use_baseline_correction=False)
    live = LiveAnalysis(analysis)
    print(f"[live-compile] seeded {len(live.seen_task_ids)} already-exported task(s); "
          f"polling every {poll_seconds}s. Ctrl-C to stop.")

    while True:
        try:
            n_new = live.compile_and_export_new()
            if n_new:
                print(f"[live-compile] compiled + exported {n_new} new task(s); "
                      f"{len(live.seen_task_ids)} total seen")
        except KeyboardInterrupt:
            print("\n[live-compile] stopped.")
            break
        except Exception as e:
            # A transient DB/parse hiccup shouldn't kill the loop — log and retry next tick.
            print(f"[live-compile] error: {e}")
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()

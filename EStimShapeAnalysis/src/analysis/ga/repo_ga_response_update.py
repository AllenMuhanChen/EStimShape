"""
repo_ga_response_update.py
--------------------------
Best-effort push of freshly-computed GA Responses into the data repository.

GA Response (StimGaInfo.response) is only computed once a generation's trials are
all complete, in the response-processing step (response_processor.process_to_db).
Live compilation runs *before* that, so for the in-progress generation the
repository either lacks those trials entirely (PlotTopNAnalysis.clean_ga_data
drops rows whose GA Response is null) or holds a stale value. After GA Responses
are computed we therefore re-compile + export the session so the repository
reflects them.

This is intentionally best-effort: it must never break GA response processing or
the GA run. If the export can't be done — analysis deps unavailable, repository
unreachable, nothing exportable yet, intan/spike files missing on this machine —
it prints an explanation and returns False instead of raising.

Call it right after `response_processor.process_to_db(...)`.
"""

from __future__ import annotations

import traceback


def update_repository_with_ga_responses(use_baseline_correction: bool = False) -> bool:
    """Re-compile + export the current GA session so the repository reflects the
    GA Responses that were just computed. Returns True on success, False (with an
    explanation printed) if the update couldn't be completed."""
    # Imported lazily so the GA/response-processing path doesn't pay for the heavy
    # analysis import unless this actually runs, and to avoid import cycles.
    try:
        from src.analysis.ga.plot_top_n import PlotTopNAnalysis
        from src.startup import context
    except Exception as e:
        print("[ga-repo-update] Skipping repository update: could not import the analysis "
              f"stack ({type(e).__name__}: {e}). GA response processing was unaffected.")
        return False

    try:
        analysis = PlotTopNAnalysis(use_baseline_correction=use_baseline_correction)
        print(f"[ga-repo-update] Updating repository from '{context.ga_database}' so it "
              "reflects the newly-computed GA Responses...")
        data = analysis.compile_and_export()
        n_rows = 0 if data is None else len(data)
        print(f"[ga-repo-update] Done: exported {n_rows} trial row(s) with GA Responses to "
              "the repository.")
        return True
    except Exception as e:
        print("[ga-repo-update] Could not update the repository with GA Responses "
              f"({type(e).__name__}: {e}).")
        print("[ga-repo-update] This is non-fatal: GA response processing completed; only the "
              "repository export was skipped. Common causes: the session isn't exportable yet "
              "(no completed trials with responses), the repository database is unreachable, or "
              "intan/spike files for some trials aren't available on this machine.")
        traceback.print_exc()
        return False

"""
In-process context switch that bypasses the brittle file-write +
``importlib.reload(context)`` dance in ``startup_system.ExperimentManager``.

Why a separate helper:
  - ``importlib.reload(context)`` re-executes the module top-level. The
    ``try / except`` around ``ga_config = EStimShapeConfig(...)`` swallows
    failures and leaves the *old* ``ga_config`` in place — silently, since
    reload doesn't clear the namespace first. You think you switched, but
    ``context.ga_config`` still points at the previous database.
  - Already-constructed instances that captured the old ``ga_config`` /
    paths at __init__ keep using the stale values; the file write doesn't
    reach them.

This helper instead mutates ``context``'s attributes in-place, recomputes
all derived paths from ``ga_database``, and rebuilds ``ga_config`` so any
runtime access to ``context.X`` after the call sees the new session.
Failures are not swallowed.

Usage::

    from src.startup.apply_session_context import apply_session_context
    apply_session_context("260426_0")
    # now context.ga_database, context.ga_config, etc. point at the new session
"""

from __future__ import annotations

from typing import Optional

from src.startup import context
from src.startup.startup_system import ExperimentManager
from src.pga.config.estimshape_config import EStimShapeConfig


def apply_session_context(
    session_id: str,
    *,
    ga_name: Optional[str] = None,
) -> None:
    """
    Switch the global ``context`` module's attributes to those for
    ``session_id`` (format ``"<date>_<location_id>"``, e.g. ``"260426_0"``).

    Steps:
      1. Build an ExperimentManager for the session — same logic the
         existing startup system uses, just without the file write.
      2. Overwrite the database-name attributes on the context module
         (``ga_database``, ``nafc_database``, etc.) per experiment.
      3. Recompute all path attributes derived from ``ga_database`` and the
         other database names.
      4. Rebuild ``context.ga_config`` from scratch with the new database.
         Any failure here raises (no silent swallow), so you'll see
         immediately if a session's config can't be constructed.
      5. ``context.ga_name`` is preserved unless overridden.
    """
    if ga_name is not None:
        context.ga_name = ga_name

    manager = ExperimentManager(session_id=session_id)

    # ---- (2) database-name attributes per experiment ---------------------
    # Mapping is the same one ``ExperimentManager.update_context_file`` uses.
    for exp in manager.experiments:
        var_name = exp.get_context_variable_name()
        setattr(context, var_name, exp.get_database_name())

    # ---- (3) recompute derived paths in-place ---------------------------
    base = context.base_dir
    ga_db = context.ga_database
    isogabor_db = context.isogabor_database
    lightness_db = context.lightness_database
    shuffle_db = context.shuffle_database
    nafc_db = context.nafc_database

    context.image_path                = f"{base}/{ga_db}/stimuli/ga/pngs"
    context.java_output_dir           = f"{base}/{ga_db}/java_output"
    context.rwa_output_dir            = f"{base}/{ga_db}/rwa"
    context.eyecal_dir                = f"{base}/{ga_db}/eyecal"
    context.pc_maps_path              = f"{base}/{ga_db}/pc_maps"
    context.logging_path              = f"{base}/{ga_db}/logs/log.txt"

    intan_root = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape"
    context.ga_intan_path             = f"{intan_root}/{ga_db}"
    context.isogabor_intan_path       = f"{intan_root}/{isogabor_db}"
    context.lightness_intan_path      = f"{intan_root}/{lightness_db}"
    context.shuffle_intan_path        = f"{intan_root}/{shuffle_db}"

    context.ga_parsed_spikes_path     = f"{base}/{ga_db}/parsed_spikes"
    context.isogabor_parsed_spikes_path  = f"{base}/{isogabor_db}/parsed_spikes"
    context.lightness_parsed_spikes_path = f"{base}/{lightness_db}/parsed_spikes"
    context.shuffle_parsed_spikes_path   = f"{base}/{shuffle_db}/parsed_spikes"

    context.ga_plot_path              = f"{base}/{ga_db}/plots"
    context.isogabor_plot_path        = f"{base}/{isogabor_db}/plots"
    context.lightness_plot_path       = f"{base}/{lightness_db}/plots"
    context.shuffle_plot_path         = f"{base}/{shuffle_db}/plots"
    context.nafc_plot_path            = f"{base}/{nafc_db}/plots"

    # ---- (4) rebuild ga_config (no swallowing) --------------------------
    context.ga_config = EStimShapeConfig(
        is_alexnet_mock=False,
        database=context.ga_database,
        base_intan_path=context.ga_intan_path,
        java_output_dir=context.java_output_dir,
        allen_dist_dir=context.allen_dist,
    )
    context.ga_config.ga_name = context.ga_name

    print(
        f"[context] switched: session={session_id}  "
        f"ga_name={context.ga_name}  ga_database={context.ga_database}"
    )


def run_axis_coding_for_session(
    session_id: str,
    *,
    channels=("Cluster",),
    compiled_data=None,
    show_plots: bool = False,
    **analyzer_kwargs,
):
    """
    Convenience: switch context, build a fresh AxisCodingAnalysis, compile +
    export raw data on first use, then run on the requested channels.

    Pass extra ``AxisCodingAnalysis`` kwargs through ``analyzer_kwargs`` —
    e.g. strategies, axis_models, panel_config, rf_filter.
    """
    from src.analysis.ga.axis_coding.axis_coding_analysis import AxisCodingAnalysis

    apply_session_context(session_id)

    analysis = AxisCodingAnalysis(
        show_plots=show_plots,
        **analyzer_kwargs,
    )

    # Compile & export raw spikes the first time this session is touched;
    # subsequent runs can pass compiled_data explicitly to skip re-compile.
    if compiled_data is None:
        compiled_data = analysis.compile_and_export()

    results = {}
    for channel in channels:
        results[channel] = analysis.run(
            session_id, "raw", channel, compiled_data=compiled_data,
        )
    return results

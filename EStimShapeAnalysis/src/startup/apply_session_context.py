"""
In-process session switch for batch / scripted analyses.

Wraps ``context.apply_session(...)`` with the ExperimentManager so callers
can pass a single ``session_id`` like ``"260426_0"`` instead of having to
look up each experiment's database name. No file write, no
``importlib.reload``, no swallowing of EStimShapeConfig failures.

Usage::

    from src.startup.apply_session_context import apply_session_context
    apply_session_context("260426_0")
    # context.ga_database, context.ga_config, context.image_path, etc.
    # all now reflect the new session.
"""

from __future__ import annotations

from src.startup import context
from src.startup.startup_system import ExperimentManager


def apply_session_context(
    session_id: str,
    *,
    ga_name: str | None = None,
) -> None:
    """
    Switch the global context module to ``session_id`` (format
    ``"<date>_<location_id>"``, e.g. ``"260426_0"``) using the database
    names ExperimentManager would use.

    Adding new variables to ``context.py``? Add them to ``_build_paths``
    in that file — this function picks them up automatically because it
    delegates to ``context.apply_session`` which calls the same
    ``_build_paths``. No edits needed here.
    """
    manager = ExperimentManager(session_id=session_id)
    db_names = {
        exp.get_context_variable_name(): exp.get_database_name()
        for exp in manager.experiments
    }

    context.apply_session(
        ga_database=db_names.get("ga_database"),
        nafc_database=db_names.get("nafc_database"),
        isogabor_database=db_names.get("isogabor_database"),
        lightness_database=db_names.get("lightness_database"),
        shuffle_database=db_names.get("shuffle_database"),
        ga_name=ga_name,
    )
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

    When ``analyzer_kwargs["recompute"]`` is False and every
    (channel, component_type, strategy) combination already has
    AxisCodingFitMetrics rows, skip the whole session before doing the
    expensive compile_and_export.
    """
    from src.analysis.ga.axis_coding.axis_coding_analysis import (
        AxisCodingAnalysis, _format_unit_name, _has_existing_metrics,
    )
    from src.repository.export_to_repository import (
        read_session_id_and_date_from_db_name,
    )

    apply_session_context(session_id)

    analysis = AxisCodingAnalysis(
        show_plots=show_plots,
        **analyzer_kwargs,
    )

    if not analysis.recompute:
        try:
            session_id_for_check, _ = read_session_id_and_date_from_db_name(
                context.ga_database
            )
        except Exception:
            session_id_for_check = None

        if session_id_for_check is not None:
            all_done = True
            for channel in channels:
                unit_name = _format_unit_name(channel)
                for component_type in analysis.component_types:
                    for strategy in analysis.strategies:
                        if not _has_existing_metrics(
                            session_id_for_check, unit_name,
                            component_type, strategy.label,
                        ):
                            all_done = False
                            break
                    if not all_done:
                        break
                if not all_done:
                    break

            if all_done:
                print(
                    f"[skip] session={session_id_for_check} already has "
                    f"AxisCodingFitMetrics for every (channel, component_type, "
                    f"strategy) — skipping compile_and_export "
                    f"(pass recompute=True to override)"
                )
                return {channel: "skipped" for channel in channels}

    if compiled_data is None:
        compiled_data = analysis.compile_and_export()

    results = {}
    for channel in channels:
        results[channel] = analysis.run(
            session_id, "raw", channel, compiled_data=compiled_data,
        )
    return results

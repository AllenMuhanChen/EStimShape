"""
Data access shared by the GA explorer and its modules.

Everything here reads ``context`` at call time, so it follows the explorer's
session switches.
"""

from __future__ import annotations

from src.analysis.ga.explorer.explorer_module import SessionState

# Data types an Analysis understands (see Analysis._configure_data_type).
# 'GA' = the precomputed GA Response only, no per-channel rates.
DATA_TYPES = ["mua", "raw", "sorted", "GA"]


def list_ga_sessions() -> list[str]:
    """Sessions that have GA data exported to the repository, newest first."""
    from clat.util.connection import Connection
    conn = Connection("allen_data_repository")
    conn.execute(
        "SELECT DISTINCT session_id FROM Experiments "
        "WHERE experiment_id LIKE %s ORDER BY session_id DESC",
        params=("%\\_ga",),
    )
    return [str(row[0]) for row in conn.fetch_all()]


def load_ga_repository_data(session: SessionState, data_type: str):
    """GA trials for this session from the repository, as
    ``(compiled_data, spike_rates_col)``.

    Cached on the session, so every module asking for the same data type
    shares one import. ``spike_rates_col`` is None for data_type 'GA'.
    """
    def loader():
        from src.analysis.ga.plot_top_n import PlotTopNAnalysis
        analysis = PlotTopNAnalysis(data_type=data_type)
        analysis.session_id = session.session_id
        data = analysis.import_data(None)
        return data, analysis.spike_rates_col

    return session.get_or_load(("ga_repository", data_type), loader)


def load_side_test_data(session: SessionState, data_type: str):
    """2D vs 3D side-test trials (repository table 2Dvs3DStimInfo: TestId,
    TestType '2D'/'3D', ...) for this session, as
    ``(compiled_data, spike_rates_col)``. Cached on the session."""
    def loader():
        import src.repository.import_from_repository as repo
        from src.analysis.ga.plot_top_n import PlotTopNAnalysis
        cfg = PlotTopNAnalysis(data_type=data_type)  # response table / MUA metric only
        data = repo.import_from_repository(
            session.session_id, "ga", "2Dvs3DStimInfo", cfg.response_table,
            mua_method=cfg.mua_method if cfg.response_table == "MUASpikeResponses" else None)
        return data, cfg.spike_rates_col

    return session.get_or_load(("side_test_2d3d", data_type), loader)


def parse_channel(text: str):
    """Channel box text -> what ResponseSpec expects: 'GA', 'Cluster',
    'A-006', or a list for 'A-000,A-006'."""
    text = (text or "").strip()
    if "," in text:
        return [c.strip() for c in text.split(",") if c.strip()]
    return text

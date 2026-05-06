"""
Schemas for the position-axis follow-up analyses in allen_data_repository.

Idempotent CREATE TABLE IF NOT EXISTS — safe to call on every export. Two
tables, both keyed by (session_id, unit_name, component_type, strategy):

  AxisIndependenceMetrics  one row per fit. Cross-validated R^2s for the
                           four nested response models (pos-only, shape-only,
                           additive, interaction), the interaction gap,
                           position/shape projection correlation, and the
                           selected ridge alphas.

  AxisCompositionMetrics   one row per axis (preferred + top-K orth PCs),
                           extra primary-key column ``axis_label``. Stores
                           R^2_pos, R^2_shape, PSI, the axis's saved
                           orth-variance share (NULL for preferred), and
                           the chance-baseline R^2_pos.

These mirror the pattern from create_axis_coding_tables.py so the same
unit_name convention joins cleanly with AxisCodingFitMetrics for paired
population analyses.
"""

from __future__ import annotations

from clat.util.connection import Connection


_AXIS_INDEPENDENCE_METRICS_SQL = """
CREATE TABLE IF NOT EXISTS AxisIndependenceMetrics (
    session_id      VARCHAR(10) NOT NULL,
    unit_name       VARCHAR(64) NOT NULL,
    component_type  VARCHAR(32) NOT NULL,
    strategy        VARCHAR(64) NOT NULL,

    n_stim_used     INT,
    r2_pos_only     FLOAT,
    r2_shape_only   FLOAT,
    r2_additive     FLOAT,
    r2_interaction  FLOAT,
    interaction_gap FLOAT,
    corr_p_s        FLOAT,
    ridge_alpha_p   FLOAT,
    ridge_alpha_s   FLOAT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (session_id, unit_name, component_type, strategy)
);
"""


_AXIS_COMPOSITION_METRICS_SQL = """
CREATE TABLE IF NOT EXISTS AxisCompositionMetrics (
    session_id          VARCHAR(10) NOT NULL,
    unit_name           VARCHAR(64) NOT NULL,
    component_type      VARCHAR(32) NOT NULL,
    strategy            VARCHAR(64) NOT NULL,
    axis_label          VARCHAR(32) NOT NULL,
    axis_rank           INT NOT NULL,

    r2_pos              FLOAT,
    r2_shape            FLOAT,
    psi                 FLOAT,
    axis_variance       FLOAT,
    chance_baseline_pos FLOAT,
    n_stim_used         INT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (session_id, unit_name, component_type, strategy, axis_label)
);
"""


def create_axis_independence_tables(conn: Connection) -> None:
    """Create AxisIndependenceMetrics + AxisCompositionMetrics if not present."""
    conn.execute(_AXIS_INDEPENDENCE_METRICS_SQL)
    conn.execute(_AXIS_COMPOSITION_METRICS_SQL)


def main():
    """python -m src.repository.create_axis_independence_tables"""
    conn = Connection("allen_data_repository")
    create_axis_independence_tables(conn)
    print(
        "AxisIndependenceMetrics + AxisCompositionMetrics ensured in "
        "allen_data_repository."
    )


if __name__ == "__main__":
    main()

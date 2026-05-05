"""
Schemas for axis-coding outputs in allen_data_repository.

Idempotent CREATE TABLE IF NOT EXISTS — safe to call on every export.
Two tables:

  AxisCodingFitMetrics    one row per (session, unit, type, strategy, model)
                          with all queryable scalars (cv_r2, orth_amplitude_norm,
                          spearman_rho, spearman_p, ...). Adding a new scalar
                          metric requires ALTER TABLE ADD COLUMN.

  AxisCodingFitArrays     one row per (..., array_name) with JSON-encoded
                          variable-length payload. Adding a new array
                          analysis is just a new array_name; no schema change.
"""

from __future__ import annotations

from clat.util.connection import Connection


_AXIS_CODING_FIT_METRICS_SQL = """
CREATE TABLE IF NOT EXISTS AxisCodingFitMetrics (
    session_id      VARCHAR(10) NOT NULL,
    unit_name       VARCHAR(64) NOT NULL,
    component_type  VARCHAR(32) NOT NULL,
    strategy        VARCHAR(64) NOT NULL,
    model_name      VARCHAR(64) NOT NULL,

    n_stim                  INT,
    n_features              INT,
    cv_r2_mean              FLOAT,
    cv_r2_std               FLOAT,
    train_r2                FLOAT,
    noise_ceiling           FLOAT,
    alpha                   FLOAT,

    spearman_rho            FLOAT,
    spearman_p              FLOAT,

    orth_n_axes_drawn       INT,
    orth_n_axes_used        INT,
    orth_z_range            FLOAT,
    orth_fit_z_range        FLOAT,
    orth_gauss_a            FLOAT,
    orth_gauss_sigma        FLOAT,
    orth_gauss_c            FLOAT,
    orth_gauss_fit_ok       TINYINT(1),
    orth_amplitude_norm     FLOAT,
    orth_per_axis_mod_max   FLOAT,
    orth_per_axis_mod_med   FLOAT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (session_id, unit_name, component_type, strategy, model_name),
    FOREIGN KEY (session_id) REFERENCES Sessions(session_id) ON DELETE CASCADE
);
"""


_AXIS_CODING_FIT_ARRAYS_SQL = """
CREATE TABLE IF NOT EXISTS AxisCodingFitArrays (
    session_id      VARCHAR(10) NOT NULL,
    unit_name       VARCHAR(64) NOT NULL,
    component_type  VARCHAR(32) NOT NULL,
    strategy        VARCHAR(64) NOT NULL,
    model_name      VARCHAR(64) NOT NULL,
    array_name      VARCHAR(64) NOT NULL,
    array_json      LONGTEXT,

    PRIMARY KEY (session_id, unit_name, component_type, strategy, model_name, array_name),
    FOREIGN KEY (session_id) REFERENCES Sessions(session_id) ON DELETE CASCADE
);
"""


def create_axis_coding_tables(conn: Connection) -> None:
    """Create AxisCodingFitMetrics + AxisCodingFitArrays if they don't exist."""
    conn.execute(_AXIS_CODING_FIT_METRICS_SQL)
    conn.execute(_AXIS_CODING_FIT_ARRAYS_SQL)


def main():
    """One-shot table creation: python -m src.repository.create_axis_coding_tables"""
    conn = Connection("allen_data_repository")
    create_axis_coding_tables(conn)
    print("AxisCodingFitMetrics + AxisCodingFitArrays ensured in allen_data_repository.")


if __name__ == "__main__":
    main()

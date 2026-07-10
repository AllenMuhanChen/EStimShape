"""
Create the RFMappingResponse table (run from the IDE — no command line).
=======================================================================
Open this file and click Run. It applies
`sql_queries/create_rf_mapping_response_table.sql` to a ga database.

By default it targets the CURRENT session's ga database (`context.ga_database`).
To also create the table in the TEMPLATE database (so every NEW ga database
cloned by db_factory gets it), set TARGET_DB below to your template name, e.g.
`allen_ga_test_250508_0`, and run again.

CREATE TABLE IF NOT EXISTS makes this safe to run repeatedly.
"""

import os

from clat.util.connection import Connection
from src.startup import context

# None -> use the current session's ga database. Or set a specific db name
# (e.g. the template) to create the table there.
TARGET_DB = None


def _ddl_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    # .../EStimShapeAnalysis/src/intan/rf_mapping/ -> up 3 to EStimShapeAnalysis
    root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    return os.path.join(root, "sql_queries", "create_rf_mapping_response_table.sql")


def _read_statement(path: str) -> str:
    """
    Read the DDL and strip all `--` comments (full-line and inline) so the driver
    receives one clean statement with no stray comment characters or semicolons.
    Safe here because the DDL contains no string literals or tokens with '--'.
    """
    lines = []
    with open(path, "r") as f:
        for raw in f:
            code = raw.split("--", 1)[0].rstrip()
            if code.strip():
                lines.append(code)
    return "\n".join(lines).strip().rstrip(";")


def main():
    db_name = TARGET_DB or context.ga_database
    ddl = _read_statement(_ddl_path())
    conn = Connection(db_name)
    conn.execute(ddl)
    print(f"Ensured RFMappingResponse exists in '{db_name}'.")
    # Confirm columns
    conn.execute("SHOW COLUMNS FROM RFMappingResponse")
    cols = [row[0] for row in conn.fetch_all()]
    print("Columns:", ", ".join(cols))


if __name__ == "__main__":
    main()

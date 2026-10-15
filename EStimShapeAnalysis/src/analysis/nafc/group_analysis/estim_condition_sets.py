"""
Named sets of EStim conditions across sessions, stored in the data repository, so
one script can define a set of conditions and another can use it without importing
the first one's code.

A set is a list of (session_id, condition) pairs, conditions in the same canonical
JSON as EStimEffects.conditions. Writers: avg_estim_per_experiment (the top / bottom
half of the current : half-distance ranking) and max_estim_per_experiment (its
default set: every condition it tests). Reader: the estim condition explorer's
"Condition set" filter.

Tables (allen_data_repository, created on first use):
  EStimConditionSetInfo  one row per set: name, description, source script,
                         params (JSON of the settings that made it), created_at.
  EStimConditionSets     one row per member: set_name, session_id, conditions.

Saving a set under an existing name replaces it (the name is what readers look
up), and its info row records when and with which settings it was made.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parents[3]))

from clat.util.connection import Connection
from src.analysis.nafc.group_analysis.analyze_estim_by_condition import (
    _cond_dicts_equal, _normalize_cond_key)

REPOSITORY_DB = "allen_data_repository"


def create_condition_set_tables(conn=None):
    conn = conn or Connection(REPOSITORY_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS EStimConditionSetInfo
        (
            set_name    VARCHAR(100) NOT NULL,
            description TEXT,
            source      VARCHAR(100),
            params      LONGTEXT,
            created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (set_name)
        ) ENGINE = InnoDB DEFAULT CHARSET = latin1
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS EStimConditionSets
        (
            set_name   VARCHAR(100) NOT NULL,
            session_id VARCHAR(10)  NOT NULL,
            conditions LONGTEXT     NOT NULL,
            PRIMARY KEY (set_name, session_id, conditions(500)),
            FOREIGN KEY (set_name) REFERENCES EStimConditionSetInfo (set_name)
                ON DELETE CASCADE,
            FOREIGN KEY (session_id) REFERENCES Sessions (session_id) ON DELETE CASCADE
        ) ENGINE = InnoDB DEFAULT CHARSET = latin1
    """)


# the tables are latin1 (like the other EStim tables): text going in is made to fit
_LATIN1_SUBSTITUTES = {'−': '-', '–': '-', '—': '-', '≤': '<=', '≥': '>=',
                       '→': '->', '…': '...', '×': 'x'}


def _latin1(text, limit=None):
    """text with characters latin1 can't store swapped for ASCII look-alikes (or
    '?'), optionally cut to ``limit`` characters."""
    text = "".join(_LATIN1_SUBSTITUTES.get(ch, ch) for ch in str(text or ""))
    text = text.encode('latin-1', 'replace').decode('latin-1')
    return text[:limit] if limit else text


def save_condition_set(set_name, members, description="", source="", params=None):
    """Store (replacing any set of the same name) the set of (session_id, cond_dict)
    pairs ``members``. ``params``: the settings that produced it (JSON-serialisable;
    anything else is stored as its str). Returns the number of members stored."""
    rows = sorted({(str(sid), _normalize_cond_key(cond)) for sid, cond in members})
    conn = Connection(REPOSITORY_DB)
    create_condition_set_tables(conn)
    # deleting the info row cascades to the old members
    conn.execute("DELETE FROM EStimConditionSetInfo WHERE set_name = %s", (set_name,))
    conn.execute(
        "INSERT INTO EStimConditionSetInfo (set_name, description, source, params) "
        "VALUES (%s, %s, %s, %s)",
        (set_name, _latin1(description), _latin1(source, 100),
         json.dumps(params or {}, default=str)))
    if rows:
        cursor = conn.mydb.cursor()
        cursor.executemany(
            "INSERT INTO EStimConditionSets (set_name, session_id, conditions) "
            "VALUES (%s, %s, %s)", [(set_name, sid, cond) for sid, cond in rows])
        conn.mydb.commit()
        cursor.close()
    print(f"Saved condition set {set_name!r}: {len(rows)} conditions in "
          f"{len({sid for sid, _ in rows})} sessions")
    return len(rows)


def list_condition_sets():
    """DataFrame of every set: set_name, description, source, created_at,
    n_conditions, n_sessions (empty if the tables don't exist yet)."""
    conn = Connection(REPOSITORY_DB)
    create_condition_set_tables(conn)
    conn.execute("""
        SELECT i.set_name, i.description, i.source, i.created_at,
               COUNT(s.conditions), COUNT(DISTINCT s.session_id)
        FROM EStimConditionSetInfo i
        LEFT JOIN EStimConditionSets s ON s.set_name = i.set_name
        GROUP BY i.set_name, i.description, i.source, i.created_at
        ORDER BY i.set_name
    """)
    return pd.DataFrame(conn.fetch_all(),
                        columns=['set_name', 'description', 'source', 'created_at',
                                 'n_conditions', 'n_sessions'])


def load_condition_set(set_name):
    """{session_id: [cond_dict, ...]} of a stored set ({} if there is no such set)."""
    conn = Connection(REPOSITORY_DB)
    create_condition_set_tables(conn)
    conn.execute("SELECT session_id, conditions FROM EStimConditionSets "
                 "WHERE set_name = %s", (set_name,))
    out = {}
    for sid, cond in conn.fetch_all():
        out.setdefault(sid, []).append(json.loads(cond))
    return out


def in_condition_set(session_ids, conditions_json, members):
    """Boolean list: is each (session_id, EStimEffects conditions JSON) pair in the
    set ``members`` (from load_condition_set)? Matches by condition value, so a
    stored 10 matches 10.0."""
    keyed = {sid: ({_normalize_cond_key(c) for c in conds}, conds)
             for sid, conds in members.items()}
    out = []
    for sid, cond_json in zip(session_ids, conditions_json):
        if sid not in keyed:
            out.append(False)
            continue
        cond = json.loads(cond_json)
        exact, conds = keyed[sid]
        out.append(_normalize_cond_key(cond) in exact
                   or any(_cond_dicts_equal(cond, c) for c in conds))
    return out

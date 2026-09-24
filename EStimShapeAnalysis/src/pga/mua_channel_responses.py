"""
Single access point to an experiment's MUAChannelResponses table.

Every reader and writer of MUA data goes through MuaChannelResponseStore instead of
hand-rolling SQL: the GA MUA parser (writes), the GA response processor (per-stim
response vectors), the cluster apps (per-channel average rates), and the analysis
fields (per-task spike times + epochs).

ensure_populated() closes the loop: if the table has no rows for the store's
metric, it runs the same whole-session backfill as recalculate_mua_ga's detection
step, so callers don't have to remember to run it first.

The metric tag (e.g. 'mad_k4_block100') is the single source of truth for the
detection parameters: mua_metric_name() builds it and parse_mua_metric() recovers
k and the block size from it, so a backfill always writes what the tag says.

This module deliberately imports nothing from src.pga at module level, so
multi_ga_db_util can import it without a cycle.
"""

from __future__ import annotations

import ast
import re
from typing import Iterable, Optional

import numpy as np

DEFAULT_MUA_METRIC = "mad_k4_block100"

_METRIC_RE = re.compile(r"^mad_k(?P<k>\d+(?:\.\d+)?)_block(?P<block>\d+)$")


def mua_metric_name(threshold_k: float = 4.0, block_size: int = 100) -> str:
    """Canonical metric tag for a -k x MAD detector refreshed every block_size task_ids."""
    return f"mad_k{threshold_k:g}_block{int(block_size)}"


def parse_mua_metric(mua_metric: str) -> tuple[float, int]:
    """Inverse of mua_metric_name: 'mad_k4_block100' -> (4.0, 100)."""
    match = _METRIC_RE.match(mua_metric)
    if match is None:
        raise ValueError(f"Unrecognized MUA metric {mua_metric!r}; expected 'mad_k<k>_block<n>'")
    return float(match.group("k")), int(match.group("block"))


class _StrChannel:
    """Minimal channel holder exposing `.value`, which is all the Intan fields read,
    so spikes served from the table don't need a clat Channel enum."""
    __slots__ = ("value",)

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"_StrChannel({self.value!r})"


class MuaChannelResponseStore:
    """Reads and writes MUAChannelResponses for one detection metric.

    Build one with MuaChannelResponseStore.for_ga() for the current GA experiment
    (it can then backfill an empty table), or for_database() for any database.
    """

    TABLE = "MUAChannelResponses"

    def __init__(self, conn, mua_metric: str = DEFAULT_MUA_METRIC, *,
                 ga_name: Optional[str] = None,
                 base_intan_path: Optional[str] = None,
                 db_util=None,
                 auto_populate: bool = True):
        self.conn = conn
        self.mua_metric = mua_metric
        self.threshold_k, self.block_size = parse_mua_metric(mua_metric)
        # Only needed to backfill (GA experiments); read-only stores leave them None.
        self.ga_name = ga_name
        self.base_intan_path = base_intan_path
        self.db_util = db_util
        self.auto_populate = auto_populate
        self._ensured = False

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------
    @classmethod
    def for_ga(cls, mua_metric: Optional[str] = None, *, auto_populate: bool = True):
        """Store for the current GA experiment (src.startup.context), configured so
        ensure_populated() can backfill it. Defaults to the metric the live GA
        pipeline writes (its mua_threshold_k / mua_block_size GAVars)."""
        from src.startup import context
        cfg = context.ga_config
        if mua_metric is None:
            mua_metric = cfg.mua_metric() if hasattr(cfg, "mua_metric") else DEFAULT_MUA_METRIC
        return cls(cfg.connection(), mua_metric,
                   ga_name=getattr(cfg, "ga_name", None) or context.ga_name,
                   base_intan_path=getattr(cfg, "base_intan_path", None) or context.ga_intan_path,
                   db_util=cfg.db_util,
                   auto_populate=auto_populate)

    @classmethod
    def for_database(cls, db_name: str, mua_metric: str = DEFAULT_MUA_METRIC):
        """Store for any database. The current GA experiment's database gets a
        backfill-capable store; others are read-only (nothing parses MUA into them,
        so an empty table there just means 'detect from wideband')."""
        from src.startup import context
        if db_name == context.ga_database:
            return cls.for_ga(mua_metric)
        from clat.util.connection import Connection
        return cls(Connection(db_name), mua_metric, auto_populate=False)

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------
    def table_exists(self) -> bool:
        self.conn.execute(f"SHOW TABLES LIKE '{self.TABLE}'")
        return bool(self.conn.fetch_all())

    def create_table_if_not_exists(self) -> None:
        self.conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.TABLE} (
                stim_id BIGINT NOT NULL,
                task_id BIGINT NOT NULL,
                channel VARCHAR(64) NOT NULL,
                mua_metric VARCHAR(64) NOT NULL,
                spikes_per_second DOUBLE,
                tstamps LONGTEXT,
                epoch_start DOUBLE,
                epoch_end DOUBLE,
                PRIMARY KEY (task_id, channel, mua_metric),
                INDEX idx_stim_metric (stim_id, channel, mua_metric)
            ) ENGINE=InnoDB DEFAULT CHARSET=latin1
            """
        )
        # Migrate tables created before the spike-timestamp/epoch columns existed.
        self.conn.execute(f"SHOW COLUMNS FROM {self.TABLE}")
        existing = {row[0] for row in self.conn.fetch_all()}
        for col, col_type in (("tstamps", "LONGTEXT"),
                              ("epoch_start", "DOUBLE"),
                              ("epoch_end", "DOUBLE")):
            if col not in existing:
                self.conn.execute(f"ALTER TABLE {self.TABLE} ADD COLUMN {col} {col_type}")

    # ------------------------------------------------------------------
    # Population
    # ------------------------------------------------------------------
    def is_populated(self) -> bool:
        """True if the table exists and has at least one row for this metric."""
        if not self.table_exists():
            return False
        self.conn.execute(
            f"SELECT 1 FROM {self.TABLE} WHERE mua_metric = %s LIMIT 1", (self.mua_metric,))
        return bool(self.conn.fetch_all())

    def ensure_populated(self) -> bool:
        """Make sure the table has rows for this metric, running the whole-session
        backfill (recalculate_mua_ga's detection step) if it doesn't.

        Returns True when data is available afterwards. Checks the database once
        per store; later calls are free.
        """
        if self._ensured:
            return True
        if self.is_populated():
            self._ensured = True
            return True
        if not self.auto_populate:
            return False
        if self.ga_name is None or self.base_intan_path is None:
            print(f"{self.TABLE} has no rows for {self.mua_metric!r}, and this store has no "
                  f"GA experiment to backfill from. Use MuaChannelResponseStore.for_ga() "
                  f"or run recalculate_mua_ga.")
            return False
        print(f"{self.TABLE} has no rows for {self.mua_metric!r}; running the whole-session "
              f"MUA backfill (same detection as recalculate_mua_ga). This re-detects from "
              f"wideband and can take a while...")
        self.backfill()
        self._ensured = self.is_populated()
        return self._ensured

    def backfill(self) -> None:
        """Detect MUA for every recording folder of the GA experiment and upsert it.
        Only stims missing rows (or missing spike timestamps) are re-detected."""
        if self.ga_name is None or self.base_intan_path is None:
            raise RuntimeError("backfill() needs a GA experiment; build the store with for_ga().")
        from src.pga.spike_parsing import MuaIntanResponseParser
        parser = MuaIntanResponseParser(
            self.base_intan_path, self._get_db_util(),
            mua_metric=self.mua_metric,
            threshold_k=self.threshold_k,
            block_size=self.block_size,
        )
        parser.parse_all_generations_to_mua(self.ga_name)
        self._ensured = False  # re-check on next ensure_populated()

    def _get_db_util(self):
        if self.db_util is None:
            from src.pga.multi_ga_db_util import MultiGaDbUtil
            self.db_util = MultiGaDbUtil(self.conn)
        return self.db_util

    # ------------------------------------------------------------------
    # Writes (GA MUA parser)
    # ------------------------------------------------------------------
    def write_rows(self, rows: Iterable[tuple]) -> None:
        """Upsert rows of (stim_id, task_id, channel, mua_metric, spikes_per_second,
        tstamps, epoch_start, epoch_end). tstamps is a repr'd list of absolute
        spike times in seconds; the epoch bounds are in seconds."""
        rows = list(rows)
        if not rows:
            return
        cursor = self.conn.mydb.cursor()
        cursor.executemany(
            f"""
            INSERT INTO {self.TABLE}
                (stim_id, task_id, channel, mua_metric, spikes_per_second, tstamps, epoch_start, epoch_end)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE spikes_per_second = VALUES(spikes_per_second),
                                    stim_id = VALUES(stim_id),
                                    tstamps = VALUES(tstamps),
                                    epoch_start = VALUES(epoch_start),
                                    epoch_end = VALUES(epoch_end)
            """,
            rows,
        )
        self.conn.mydb.commit()
        cursor.close()

    def stims_needing_parse(self, lineage_ids: Iterable[int]) -> list[int]:
        """Stims in these lineages with no row for this metric that carries spike
        timestamps. Rate-only rows (written before tstamps existed) count as
        needing a re-parse, so they get backfilled rather than skipped."""
        lineage_ids = list(lineage_ids)
        if not lineage_ids:
            return []
        placeholders = ','.join(['%s'] * len(lineage_ids))
        self.conn.execute(
            f"""
            SELECT s.stim_id
            FROM StimGaInfo s
            LEFT JOIN {self.TABLE} r
                   ON s.stim_id = r.stim_id AND r.mua_metric = %s AND r.tstamps IS NOT NULL
            WHERE r.stim_id IS NULL AND lineage_id IN ({placeholders})
            """,
            [self.mua_metric] + lineage_ids,
        )
        return [row[0] for row in self.conn.fetch_all()]

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------
    def response_vector(self, stim_id, channel: str) -> list[float]:
        """spikes_per_second for every repetition (task) of a stim on one channel.
        Used by the GA response processor."""
        self.conn.execute(
            f"SELECT spikes_per_second FROM {self.TABLE} "
            f"WHERE stim_id = %s AND channel = %s AND mua_metric = %s",
            (stim_id, channel, self.mua_metric))
        return [float(row[0]) for row in self.conn.fetch_all()]

    def avg_rate_by_stim(self, channel: str, max_gen: Optional[int] = None) -> np.ndarray:
        """Mean spikes_per_second per stim (averaged over its tasks) for one channel,
        ordered by stim_id; optionally only stims from generations <= max_gen.
        Empty array if the channel has no data. Used by the cluster apps."""
        if max_gen is None:
            self.conn.execute(
                f"""
                SELECT stim_id, AVG(spikes_per_second)
                FROM {self.TABLE}
                WHERE channel = %s AND mua_metric = %s
                GROUP BY stim_id
                ORDER BY stim_id
                """,
                (str(channel), self.mua_metric))
        else:
            self.conn.execute(
                f"""
                SELECT cr.stim_id, AVG(cr.spikes_per_second)
                FROM {self.TABLE} cr
                JOIN StimGaInfo sgi ON cr.stim_id = sgi.stim_id
                WHERE cr.channel = %s AND cr.mua_metric = %s AND sgi.gen_id <= %s
                GROUP BY cr.stim_id
                ORDER BY cr.stim_id
                """,
                (str(channel), self.mua_metric, max_gen))
        rows = self.conn.fetch_all()
        if not rows:
            return np.array([])
        return np.array([float(row[1]) for row in rows])

    def max_gen(self) -> int:
        """Highest generation with rows for this metric (1 if none)."""
        self.conn.execute(
            f"""
            SELECT MAX(sgi.gen_id)
            FROM StimGaInfo sgi
            JOIN {self.TABLE} cr ON cr.stim_id = sgi.stim_id
            WHERE cr.mua_metric = %s
            """,
            (self.mua_metric,))
        max_gen = self.conn.fetch_one()
        return 1 if max_gen is None else int(max_gen)

    def stim_ids(self) -> list:
        """Distinct stim_ids with rows for this metric, ordered (matches the order
        of avg_rate_by_stim when every channel covers every stim)."""
        self.conn.execute(
            f"SELECT DISTINCT stim_id FROM {self.TABLE} WHERE mua_metric = %s ORDER BY stim_id",
            (self.mua_metric,))
        return [row[0] for row in self.conn.fetch_all()]

    def spikes_and_epochs(self, task_ids: Iterable[int]) -> tuple[dict, dict]:
        """Absolute spike times and epoch bounds for the given tasks, in the shape
        PeriodicBlockMUAParser.parse returns ({task: {channel: [t...]}},
        {task: (start_s, end_s)}). Tasks without stored timestamps are omitted, so
        callers can detect just those from wideband. Used by the analysis fields."""
        task_ids = [int(t) for t in task_ids]
        spikes: dict = {}
        epochs: dict = {}
        if not task_ids or not self.table_exists():
            return spikes, epochs
        placeholders = ','.join(['%s'] * len(task_ids))
        self.conn.execute(
            f"""
            SELECT task_id, channel, tstamps, epoch_start, epoch_end
            FROM {self.TABLE}
            WHERE mua_metric = %s AND task_id IN ({placeholders})
              AND tstamps IS NOT NULL AND epoch_start IS NOT NULL AND epoch_end IS NOT NULL
            """,
            [self.mua_metric] + task_ids)
        for task_id, channel, tstamps_str, epoch_start, epoch_end in self.conn.fetch_all():
            try:
                times = ast.literal_eval(tstamps_str) if tstamps_str else []
            except (SyntaxError, ValueError):
                times = []
            spikes.setdefault(int(task_id), {})[_StrChannel(channel)] = times
            epochs[int(task_id)] = (float(epoch_start), float(epoch_end))
        return spikes, epochs

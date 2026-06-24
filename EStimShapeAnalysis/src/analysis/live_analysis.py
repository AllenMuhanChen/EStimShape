"""
live_analysis.py
----------------
Generic machinery for compiling + exporting trials *as they complete*, without
ever recompiling trials that are already in the repository.

The batch path (e.g. PlotTopNAnalysis.compile_and_export) collects every
completed task, compiles all of them (parsing every spike file again), and
re-exports the whole session. That is wasteful in a live setting: most of the
work has already been done on the previous poll. Here we instead:

    1. ask the analysis for the task ids it *would* compile right now,
    2. drop the ones already exported to the repository,
    3. compile ONLY the new ones,
    4. export just those (every repository write is an upsert, so prior trials
       are left untouched).

To be driven this way an Analysis implements the `LiveCompilable` interface
below. `PlotTopNAnalysis` is the first implementer; any task-id-granular
analysis can opt in the same way. `LiveAnalysis` is the driver that ties the
interface together into the incremental loop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

import pandas as pd

from clat.util.connection import Connection


class LiveCompilable(ABC):
    """Interface an Analysis must implement to be driven incrementally by `LiveAnalysis`.

    The contract is deliberately small: collect the currently-completed task ids,
    report which have already been exported, compile a given subset, and export an
    already-compiled DataFrame. Everything else (which fields, which repo tables)
    stays inside the analysis.
    """

    @abstractmethod
    def get_source_connection(self) -> Connection:
        """Open a connection to the experiment DB the trials are read from."""

    @abstractmethod
    def collect_task_ids(self, conn: Connection) -> list:
        """All currently-completed task ids in the experiment DB."""

    @abstractmethod
    def get_exported_task_ids(self) -> set:
        """Task ids already compiled & exported to the repository for this session.

        Used to seed the driver so a restart of the live loop does not recompile
        trials already in the repository. May be empty (e.g. a brand-new session
        not yet present in the repository)."""

    @abstractmethod
    def compile(self, task_ids: Optional[list] = None) -> pd.DataFrame:
        """Compile the given task ids into a DataFrame. `None` means compile all."""

    @abstractmethod
    def export(self, data: pd.DataFrame) -> None:
        """Export an already-compiled DataFrame to the repository (upsert; never deletes)."""


class LiveAnalysis:
    """Drives incremental compile + export of a `LiveCompilable` analysis.

    On construction it seeds the set of already-exported task ids from the
    repository, so restarting the live loop never recompiles old trials. Each
    call to `compile_and_export_new` diffs the experiment DB's completed tasks
    against that set, compiles ONLY the new ones, exports just those, and
    remembers them.
    """

    def __init__(self, analysis: LiveCompilable):
        self.analysis = analysis
        # Seed seen tasks from what's already in the repo so a restart doesn't redo work.
        self.seen_task_ids: set = {int(t) for t in analysis.get_exported_task_ids()}

    def compile_and_export_new(self) -> int:
        """Compile + export any completed tasks not yet seen. Returns the count of new tasks.

        Tasks are marked seen whether or not they survive the analysis's cleaning step
        (a task with no usable response is genuinely not exportable, so retrying it every
        poll would only waste compile effort)."""
        conn = self.analysis.get_source_connection()
        all_ids = [int(t) for t in self.analysis.collect_task_ids(conn)]
        new_ids = [t for t in all_ids if t not in self.seen_task_ids]
        if not new_ids:
            return 0

        data = self.analysis.compile(task_ids=new_ids)
        if data is not None and len(data) > 0:
            self.analysis.export(data)
        # Mark every attempted task seen, even those dropped during cleaning, so we don't
        # repeatedly re-compile tasks that will never produce exportable rows.
        self.seen_task_ids.update(new_ids)
        return len(new_ids)

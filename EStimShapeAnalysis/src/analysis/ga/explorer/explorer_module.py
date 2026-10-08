"""
Building blocks for GA Experiment Explorer modules.

A module is one "view" of a session: a plot, an interactive curation tool, a
table... The explorer owns the session switching (via the dynamic context
system) and exposes each module's parameters in its side panel; the module only
has to say which parameters it has and how to draw itself.

Two kinds of modules
--------------------
FigureModule
    The easy one. Implement ``make_figure(session, values)`` and return a
    matplotlib ``Figure`` or a plotly ``go.Figure``. The explorer displays it,
    redraws it when parameters change, and saves it.

ExplorerModule
    The general one, for modules that need their own interactive widget
    (checkboxes, click handling...). Implement ``create_view``, ``set_session``
    and ``refresh`` (see the docstrings below). The delta-variant curation
    module is an example.

Adding a module
---------------
1. Subclass FigureModule (or ExplorerModule) in ``explorer/modules/``.
2. Add the class to MODULES at the top of ``ga_experiment_explorer.main()``.

Context rule
------------
By the time ``set_session`` / ``make_figure`` run, the explorer has already
called ``apply_session_context(session.session_id)``. Read the session's
database / paths as ``context.ga_database``, ``context.image_path`` etc. at
call time; never ``from src.startup.context import ga_database`` (that copies
the value once, at import, and goes stale after a switch).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

import pandas as pd


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------

@dataclass
class Param:
    """One user-facing setting of a module.

    kind: 'int', 'float', 'bool', 'str' or 'choice'.
    live: True redraws as soon as the value changes (good for cheap display
        toggles); False waits for the Apply button (good for anything that
        recomputes).
    """
    key: str
    label: str
    kind: str
    default: Any
    choices: Optional[list] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    step: Optional[float] = None
    decimals: int = 2
    tooltip: str = ""
    live: bool = False


@dataclass
class Action:
    """A button the explorer shows under a module's parameters."""
    label: str
    callback: Callable[[], None]
    tooltip: str = ""
    color: Optional[str] = None


# ---------------------------------------------------------------------------
# Per-session state shared by all modules
# ---------------------------------------------------------------------------

@dataclass
class SessionState:
    """The currently selected session, plus a cache shared across modules.

    Modules that load the same data (e.g. the GA repository import) should go
    through ``get_or_load`` so switching between modules doesn't re-import.
    A new SessionState is created on every session switch, which drops the
    previous session's cache.
    """
    session_id: str
    ga_database: str = ""
    cache: dict = field(default_factory=dict)

    def get_or_load(self, key, loader: Callable[[], Any]):
        if key not in self.cache:
            self.cache[key] = loader()
        return self.cache[key]


# ---------------------------------------------------------------------------
# Module base classes
# ---------------------------------------------------------------------------

class ExplorerModule:
    """Base class for every explorer module.

    Class attributes:
        name: shown in the module list.
        description: one or two lines shown above the parameters.
    """
    name: str = "Unnamed module"
    description: str = ""

    def __init__(self):
        self.session: Optional[SessionState] = None
        # Set by the explorer: call this to report progress / results in the
        # status bar, e.g. self.status("12 pairs, 4 included").
        self.status: Callable[[str], None] = print
        # Set by the explorer: root folder for anything the module saves.
        # Use new_output_folder(self.save_root, ...) to get a fresh folder.
        self.save_root: Optional[str] = None

    # -- declared by the module ------------------------------------------
    def params(self) -> list[Param]:
        return []

    def actions(self) -> list[Action]:
        return []

    # -- lifecycle -------------------------------------------------------
    def create_view(self, parent):
        """Return the QWidget that displays this module. Called once."""
        raise NotImplementedError

    def set_session(self, session: SessionState) -> None:
        """A new session was selected (context already switched). Drop any
        per-session state here; drawing happens in ``refresh``."""
        self.session = session

    def refresh(self, values: dict, changed: Optional[set] = None) -> None:
        """Draw for the current session. ``values`` holds every parameter by
        key; ``changed`` is the set of keys that changed since the last
        refresh (None = everything, e.g. after a session switch)."""
        raise NotImplementedError

    def save(self, folder: str) -> list[str]:
        """Write the current view into ``folder`` (already created, never
        reused). Return the files written. Default: a screenshot of the view."""
        return []


class FigureModule(ExplorerModule):
    """A module that draws one matplotlib or plotly figure per refresh."""

    def __init__(self):
        super().__init__()
        self._view = None

    def make_figure(self, session: SessionState, values: dict):
        """Return a matplotlib Figure or a plotly go.Figure (or None for
        "nothing to show", after calling self.status with the reason)."""
        raise NotImplementedError

    def create_view(self, parent):
        from src.analysis.ga.explorer.figure_view import FigureView
        self._view = FigureView(parent)
        return self._view

    def refresh(self, values, changed=None):
        fig = self.make_figure(self.session, values)
        self._view.show_figure(fig)

    def save(self, folder):
        return self._view.save(folder, basename=_slug(self.name))


def new_output_folder(save_root: str, session_id: str, name: str) -> str:
    """Create and return a NEW folder
    <save_root>/<session_id>/ga_explorer/<name>_<YYYYmmdd_HHMMSS>/ (never reused)."""
    import os
    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder = os.path.join(save_root, session_id, "ga_explorer", f"{_slug(name)}_{stamp}")
    os.makedirs(folder, exist_ok=False)
    return folder


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in text.lower()).strip("_")


def ensure_dataframe(data) -> pd.DataFrame:
    if data is None or not isinstance(data, pd.DataFrame):
        raise ValueError("No data loaded for this session")
    return data

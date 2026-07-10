"""
Global session context.

Most callers can keep using ``context.ga_database``, ``context.image_path``,
``context.ga_config``, etc. as before — those names live at module level and
are populated on import.

If you want to switch sessions in-process (e.g. to batch-run an analysis
across many sessions in one Python process), use
``src.startup.apply_session_context.apply_session_context(session_id)``;
it calls ``apply_session(...)`` here to repopulate every derived attribute
in one shot.

To add a new path
-----------------
Add it to the dict returned by ``_build_paths`` below. The initial load and
the in-process switch both call ``_build_paths``, so a single new line is
all you need — no risk of the switch drifting from the file's defaults.
"""

from __future__ import annotations

import sys
import traceback
from typing import Any


# ---------------------------------------------------------------------------
# Constants that don't change per session
# ---------------------------------------------------------------------------

base_dir = "/home/connorlab/Documents/EStimShape"
allen_dist = "/home/connorlab/git/EStimShape/xper-train/dist/allen"
_INTAN_ROOT = "/run/user/1000/gvfs/sftp:host=172.30.9.78/mnt/data/EStimShape"


# ---------------------------------------------------------------------------
# Default session — anything below can be overridden via apply_session(...)
# ---------------------------------------------------------------------------

ga_name = "New3D"
ga_database = "allen_ga_exp_260708_0"
nafc_database = "allen_estimshape_exp_260708_0"
isogabor_database = "allen_isogabor_exp_260708_0"
lightness_database = "allen_lightness_exp_260708_0"
shuffle_database = "allen_shuffle_exp_260708_0"


# ---------------------------------------------------------------------------
# Single source of truth for derived paths
# ---------------------------------------------------------------------------

def _build_paths(
    *,
    base_dir: str,
    ga_database: str,
    nafc_database: str,
    isogabor_database: str,
    lightness_database: str,
    shuffle_database: str,
    intan_root: str = _INTAN_ROOT,
) -> dict[str, str]:
    """
    Return every per-session derived path as a flat ``{name: value}`` dict.

    Add new paths here so both the initial load (below) and the in-process
    session switch (``apply_session_context``) pick them up automatically.
    """
    return {
        # GA
        "image_path":              f"{base_dir}/{ga_database}/stimuli/ga/pngs",
        "java_output_dir":         f"{base_dir}/{ga_database}/java_output",
        "rwa_output_dir":          f"{base_dir}/{ga_database}/rwa",
        "eyecal_dir":              f"{base_dir}/{ga_database}/eyecal",
        "pc_maps_path":            f"{base_dir}/{ga_database}/pc_maps",
        "logging_path":            f"{base_dir}/{ga_database}/logs/log.txt",

        # Intan paths
        "ga_intan_path":           f"{intan_root}/{ga_database}",
        "isogabor_intan_path":     f"{intan_root}/{isogabor_database}",
        "lightness_intan_path":    f"{intan_root}/{lightness_database}",
        "shuffle_intan_path":      f"{intan_root}/{shuffle_database}",

        # Parsed spikes
        "ga_parsed_spikes_path":         f"{base_dir}/{ga_database}/parsed_spikes",
        "isogabor_parsed_spikes_path":   f"{base_dir}/{isogabor_database}/parsed_spikes",
        "lightness_parsed_spikes_path":  f"{base_dir}/{lightness_database}/parsed_spikes",
        "shuffle_parsed_spikes_path":    f"{base_dir}/{shuffle_database}/parsed_spikes",

        # Plots
        "ga_plot_path":            f"{base_dir}/{ga_database}/plots",
        "isogabor_plot_path":      f"{base_dir}/{isogabor_database}/plots",
        "lightness_plot_path":     f"{base_dir}/{lightness_database}/plots",
        "shuffle_plot_path":       f"{base_dir}/{shuffle_database}/plots",
        "nafc_plot_path":          f"{base_dir}/{nafc_database}/plots",
    }


def _build_ga_config(
    *,
    ga_database: str,
    ga_intan_path: str,
    java_output_dir: str,
    allen_dist: str,
    ga_name: str,
) -> Any:
    """
    Construct the EStimShapeConfig object for one session.

    Imported lazily so a missing/optional dependency on ``EStimShapeConfig``
    doesn't break ``import context`` itself.
    """
    from src.pga.config.estimshape_config import EStimShapeConfig
    cfg = EStimShapeConfig(
        is_alexnet_mock=False,
        database=ga_database,
        base_intan_path=ga_intan_path,
        java_output_dir=java_output_dir,
        allen_dist_dir=allen_dist,
    )
    cfg.ga_name = ga_name
    return cfg


def apply_session(
    *,
    ga_database: str = None,
    nafc_database: str = None,
    isogabor_database: str = None,
    lightness_database: str = None,
    shuffle_database: str = None,
    ga_name: str = None,
) -> None:
    """
    Switch the in-process context to a new session.

    Mutates this module's globals in place: database names you pass override,
    omitted ones keep their current value. Then recomputes every derived
    path via ``_build_paths`` and rebuilds ``ga_config`` from scratch. Any
    failure raises (no silent swallow).

    Prefer ``src.startup.apply_session_context.apply_session_context(session_id)``
    which reads the per-experiment database names from ExperimentManager and
    calls this function — you almost never need to call this directly.
    """
    self = sys.modules[__name__]

    # 1) Database names (only override what was provided).
    if ga_database is not None:        self.ga_database = ga_database
    if nafc_database is not None:      self.nafc_database = nafc_database
    if isogabor_database is not None:  self.isogabor_database = isogabor_database
    if lightness_database is not None: self.lightness_database = lightness_database
    if shuffle_database is not None:   self.shuffle_database = shuffle_database
    if ga_name is not None:            self.ga_name = ga_name

    # 2) Derived paths in one shot.
    paths = _build_paths(
        base_dir=self.base_dir,
        ga_database=self.ga_database,
        nafc_database=self.nafc_database,
        isogabor_database=self.isogabor_database,
        lightness_database=self.lightness_database,
        shuffle_database=self.shuffle_database,
    )
    for name, value in paths.items():
        setattr(self, name, value)

    # 3) Rebuild ga_config (no try/except — if it fails we want to know).
    self.ga_config = _build_ga_config(
        ga_database=self.ga_database,
        ga_intan_path=self.ga_intan_path,
        java_output_dir=self.java_output_dir,
        allen_dist=self.allen_dist,
        ga_name=self.ga_name,
    )


# ---------------------------------------------------------------------------
# Initial population on import
# ---------------------------------------------------------------------------

# Step 1: derived paths.
for _name, _value in _build_paths(
    base_dir=base_dir,
    ga_database=ga_database,
    nafc_database=nafc_database,
    isogabor_database=isogabor_database,
    lightness_database=lightness_database,
    shuffle_database=shuffle_database,
).items():
    globals()[_name] = _value

# Step 2: ga_config. Kept inside try/except for back-compat — module import
# shouldn't fail if EStimShapeConfig can't be constructed locally (e.g. in
# CI / sandboxes without a DB connection). ``apply_session(...)`` rebuilds
# without swallowing so explicit switches surface failures.
try:
    ga_config = _build_ga_config(
        ga_database=ga_database,
        ga_intan_path=ga_intan_path,
        java_output_dir=java_output_dir,
        allen_dist=allen_dist,
        ga_name=ga_name,
    )
except Exception:
    print("Error in creating GA config (during initial context load)")
    traceback.print_exc()

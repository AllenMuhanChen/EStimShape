"""
Trajectory traversal slider mixin for the tri-planar MRI viewer.

Provides a horizontal slider (in mm) that moves the crosshair along the current
trajectory so the user can scrub through MRI slices without manually clicking
each pane.

Usage
-----
1.  Include TrajectorySliderMixin in TriplanarMRIViewer's base classes.
2.  Call  self._build_traj_slider_section(tp, after_widget=s1)  at the end of
    _build_trajectory_panel(), passing the "Define Trajectory" LabelFrame as
    `after_widget` so the slider appears right below it.
3.  Call  self._update_trajectory_slider()  whenever self.temp_trajectory
    changes (i.e. from _lock_trajectory, _clear_trajectory, _load_session).

Dependencies (provided by TriplanarMRIViewer at run-time):
    self.temp_trajectory   — dict with keys: top_pt, direction, dist_mm; or None
    self.cursor_world      — writable 3-element ndarray (world coords in mm)
    self.data              — MRI volume array, or None if nothing is loaded
    self.display_all()     — redraws all three views and syncs bottom sliders
"""

import tkinter as tk
from tkinter import ttk


class TrajectorySliderMixin:
    """
    Depth-along-trajectory slider that scrubs the MRI crosshair in mm.

    The slider is hidden until a trajectory is locked in.  Once visible it
    spans [0 mm … dist_mm], where 0 is the chamber entry point and dist_mm is
    the trajectory target depth.  The current depth is shown in a bold readout
    next to the slider so it is always unambiguous.
    """

    # ------------------------------------------------------------------
    # Panel builder
    # ------------------------------------------------------------------

    def _build_traj_slider_section(self, parent, after_widget=None):
        """
        Create the slider sub-panel inside the trajectory panel.

        The frame is created but *not* packed; call _update_trajectory_slider()
        to show it once a trajectory is active.

        Parameters
        ----------
        parent       : tk parent widget (the trajectory LabelFrame)
        after_widget : sibling widget after which the slider frame will be
                       inserted when shown (e.g. the "Define Trajectory" section)
        """
        self._traj_slider_after_widget = after_widget
        self._traj_slider_setting = False  # guard against re-entrant callbacks

        outer = ttk.LabelFrame(parent, text="Traverse Along Trajectory")
        self._traj_slider_frame = outer
        # Not packed here — shown on demand by _update_trajectory_slider()

        # ---- row 1: label + slider + bold depth readout --------------------
        row1 = ttk.Frame(outer)
        row1.pack(fill=tk.X, padx=6, pady=(6, 2))

        ttk.Label(row1, text="Depth:").pack(side=tk.LEFT, padx=(0, 4))

        self._traj_slider_var = tk.DoubleVar(value=0.0)
        self._traj_slider = ttk.Scale(
            row1,
            from_=0.0,
            to=1.0,                          # updated dynamically
            orient=tk.HORIZONTAL,
            variable=self._traj_slider_var,
            command=self._on_traj_slider_change,
        )
        self._traj_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self._traj_slider_depth_var = tk.StringVar(value="0.0 mm")
        ttk.Label(
            row1,
            textvariable=self._traj_slider_depth_var,
            font=("TkDefaultFont", 11, "bold"),
            foreground="#cc6600",
            width=9,
            anchor="e",
        ).pack(side=tk.LEFT, padx=(2, 4))

        # ---- row 2: min / max tick labels ----------------------------------
        row2 = ttk.Frame(outer)
        row2.pack(fill=tk.X, padx=6, pady=(0, 5))

        ttk.Label(
            row2, text="0.0 mm",
            foreground="#888888", font=("TkDefaultFont", 8),
        ).pack(side=tk.LEFT)

        self._traj_slider_max_lbl = ttk.Label(
            row2, text="",
            foreground="#888888", font=("TkDefaultFont", 8),
        )
        self._traj_slider_max_lbl.pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # State update: show / hide and sync to active trajectory
    # ------------------------------------------------------------------

    def _update_trajectory_slider(self):
        """
        Sync the slider to the current trajectory and toggle its visibility.

        Call this after self.temp_trajectory is set or cleared.
        """
        if not hasattr(self, '_traj_slider_frame'):
            return  # panel not yet built

        if self.temp_trajectory is None:
            self._traj_slider_frame.pack_forget()
            return

        dist_mm = float(self.temp_trajectory['dist_mm'])

        # Update slider range and end label
        self._traj_slider_setting = True
        try:
            self._traj_slider.configure(from_=0.0, to=dist_mm)
            self._traj_slider_max_lbl.config(text=f"{dist_mm:.1f} mm")
            # Position slider at the target depth (matches crosshair after locking)
            self._traj_slider_var.set(dist_mm)
            self._traj_slider_depth_var.set(f"{dist_mm:.1f} mm")
        finally:
            self._traj_slider_setting = False

        # Insert the frame right after the "Define Trajectory" section
        pack_kwargs = dict(fill=tk.X, padx=3, pady=(0, 2))
        if self._traj_slider_after_widget is not None:
            pack_kwargs["after"] = self._traj_slider_after_widget
        self._traj_slider_frame.pack(**pack_kwargs)

    # ------------------------------------------------------------------
    # Slider callback
    # ------------------------------------------------------------------

    def _on_traj_slider_change(self, value):
        """
        Move the crosshair to *value* mm along the active trajectory.

        Triggered on every slider tick.  Skipped if we are programmatically
        updating the slider value to avoid spurious redraws.
        """
        if self._traj_slider_setting or self.temp_trajectory is None:
            return

        depth_mm = float(value)
        t = self.temp_trajectory
        self.cursor_world = t['top_pt'] + depth_mm * t['direction']
        self._traj_slider_depth_var.set(f"{depth_mm:.1f} mm")

        if self.data is not None:
            self.display_all()

"""
Trajectory traversal slider mixin for the tri-planar MRI viewer.

Provides a horizontal slider **and** a numeric text entry (both in mm) so the
user can either scrub smoothly or jump to an exact depth along the current
trajectory.  Arrow buttons step the depth by a configurable amount (default
1 mm).

Usage
-----
1.  Include TrajectorySliderMixin in TriplanarMRIViewer's base classes.
2.  Call  self._build_traj_slider_section(tp, after_widget=s1)  from
    _build_trajectory_panel(), passing the "Define Trajectory" LabelFrame as
    `after_widget`.
3.  Call  self._update_trajectory_slider()  whenever self.temp_trajectory
    changes (from _lock_trajectory, _clear_trajectory, _load_session).

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
    Depth-along-trajectory controls: slider, numeric entry, and step buttons.

    Hidden until a trajectory is locked.  Once visible, all three controls
    stay in sync:
      - Dragging the slider scrubs the depth continuously.
      - Typing a number in the entry and pressing Enter jumps to that depth.
      - The ← / → buttons step by the amount shown in the step-size box.

    Depth is always shown in mm and the current value is unambiguous.
    """

    # ------------------------------------------------------------------
    # Panel builder
    # ------------------------------------------------------------------

    def _build_traj_slider_section(self, parent, after_widget=None):
        """
        Create the slider sub-panel inside the trajectory panel.

        Not packed on creation — call _update_trajectory_slider() to show it.

        Parameters
        ----------
        parent       : tk parent (the trajectory LabelFrame)
        after_widget : sibling after which this frame is inserted when shown
        """
        self._traj_slider_after_widget = after_widget
        self._traj_slider_setting = False  # guard: suppress callbacks during programmatic updates

        outer = ttk.LabelFrame(parent, text="Traverse Along Trajectory")
        self._traj_slider_frame = outer
        # Not packed here — shown on demand.

        # ── Row 1: slider + numeric entry ─────────────────────────────
        row1 = ttk.Frame(outer)
        row1.pack(fill=tk.X, padx=6, pady=(6, 2))

        ttk.Label(row1, text="Depth:").pack(side=tk.LEFT, padx=(0, 4))

        self._traj_slider_var = tk.DoubleVar(value=0.0)
        self._traj_slider = ttk.Scale(
            row1,
            from_=0.0,
            to=1.0,               # updated dynamically when trajectory is locked
            orient=tk.HORIZONTAL,
            variable=self._traj_slider_var,
            command=self._on_traj_slider_change,
        )
        self._traj_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        # Editable numeric entry showing the current depth
        self._traj_depth_entry_var = tk.StringVar(value="0.00")
        depth_entry = ttk.Entry(
            row1,
            textvariable=self._traj_depth_entry_var,
            width=7,
            font=("TkDefaultFont", 10, "bold"),
            justify="right",
        )
        depth_entry.pack(side=tk.LEFT, padx=(2, 1))
        depth_entry.bind("<Return>", self._on_traj_depth_enter)
        depth_entry.bind("<FocusOut>", self._on_traj_depth_enter)
        ttk.Label(row1, text="mm", font=("TkDefaultFont", 10, "bold"),
                  foreground="#cc6600").pack(side=tk.LEFT, padx=(0, 4))

        # ── Row 2: step buttons + step-size entry ─────────────────────
        row2 = ttk.Frame(outer)
        row2.pack(fill=tk.X, padx=6, pady=(0, 2))

        ttk.Button(row2, text="←", width=3,
                   command=lambda: self._on_traj_step(-1)).pack(side=tk.LEFT, padx=(0, 2))

        ttk.Label(row2, text="Step:").pack(side=tk.LEFT, padx=(4, 2))
        self._traj_step_var = tk.StringVar(value="1.0")
        ttk.Entry(row2, textvariable=self._traj_step_var, width=5,
                  justify="center").pack(side=tk.LEFT, padx=2)
        ttk.Label(row2, text="mm").pack(side=tk.LEFT, padx=(1, 4))

        ttk.Button(row2, text="→", width=3,
                   command=lambda: self._on_traj_step(+1)).pack(side=tk.LEFT, padx=(2, 0))

        # ── Row 3: range labels ───────────────────────────────────────
        row3 = ttk.Frame(outer)
        row3.pack(fill=tk.X, padx=6, pady=(0, 5))

        ttk.Label(row3, text="0.0 mm", foreground="#888888",
                  font=("TkDefaultFont", 8)).pack(side=tk.LEFT)
        self._traj_slider_max_lbl = ttk.Label(row3, text="",
                                               foreground="#888888",
                                               font=("TkDefaultFont", 8))
        self._traj_slider_max_lbl.pack(side=tk.RIGHT)

    # ------------------------------------------------------------------
    # State update: show / hide and sync range to active trajectory
    # ------------------------------------------------------------------

    def _update_trajectory_slider(self):
        """
        Sync the slider to the current trajectory and toggle visibility.

        Call this after self.temp_trajectory is set or cleared.
        """
        if not hasattr(self, '_traj_slider_frame'):
            return

        if self.temp_trajectory is None:
            self._traj_slider_frame.pack_forget()
            return

        dist_mm = float(self.temp_trajectory['dist_mm'])

        self._traj_slider_setting = True
        try:
            self._traj_slider.configure(from_=0.0, to=dist_mm)
            self._traj_slider_max_lbl.config(text=f"{dist_mm:.1f} mm")
            # Start at target depth so the crosshair sits at the trajectory target.
            self._traj_slider_var.set(dist_mm)
            self._traj_depth_entry_var.set(f"{dist_mm:.2f}")
        finally:
            self._traj_slider_setting = False

        pack_kwargs = dict(fill=tk.X, padx=3, pady=(0, 2))
        if self._traj_slider_after_widget is not None:
            pack_kwargs["after"] = self._traj_slider_after_widget
        self._traj_slider_frame.pack(**pack_kwargs)

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------

    def _on_traj_slider_change(self, value):
        """Slider dragged — move crosshair and sync the entry box."""
        if self._traj_slider_setting or self.temp_trajectory is None:
            return
        depth_mm = float(value)
        self._traj_depth_entry_var.set(f"{depth_mm:.2f}")
        self._move_cursor_to_depth(depth_mm)

    def _on_traj_depth_enter(self, event=None):
        """Entry box committed — parse, clamp, and move crosshair + slider."""
        if self.temp_trajectory is None:
            return
        try:
            val = float(self._traj_depth_entry_var.get())
        except ValueError:
            return
        dist_mm = float(self.temp_trajectory['dist_mm'])
        val = max(0.0, min(val, dist_mm))
        # Set slider (triggers _on_traj_slider_change which moves the cursor)
        self._traj_slider_var.set(val)

    def _on_traj_step(self, direction):
        """Step button pressed — advance depth by ±step_size mm."""
        if self.temp_trajectory is None:
            return
        try:
            step = float(self._traj_step_var.get())
        except (ValueError, tk.TclError):
            step = 1.0
        dist_mm = float(self.temp_trajectory['dist_mm'])
        current = self._traj_slider_var.get()
        new_val = max(0.0, min(current + direction * step, dist_mm))
        self._traj_slider_var.set(new_val)

    def _move_cursor_to_depth(self, depth_mm):
        """Shared helper: update cursor_world and redraw."""
        t = self.temp_trajectory
        self.cursor_world = t['top_pt'] + depth_mm * t['direction']
        if self.data is not None:
            self.display_all()

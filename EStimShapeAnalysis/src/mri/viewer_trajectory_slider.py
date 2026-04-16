"""
Trajectory traversal slider mixin for the tri-planar MRI viewer.

Provides a horizontal slider **and** a numeric text entry (both in mm) so the
user can either scrub smoothly or jump to an exact depth along the current
trajectory.  Arrow buttons step the depth by a configurable amount (default
1 mm).

An optional microns-driven section lets the user enter a reference start depth
(mm) and then traverse using micron increments instead of mm.  All controls
stay in sync: mm slider/entry ↔ microns entry.

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
    Depth-along-trajectory controls: slider, numeric entry, step buttons,
    and an optional microns-driven section.

    Hidden until a trajectory is locked.  Once visible, all controls
    stay in sync:
      - Dragging the slider scrubs the depth continuously.
      - Typing a number in the mm entry and pressing Enter jumps to that depth.
      - The ← / → mm buttons step by the amount shown in the step-size box.
      - Setting "Elec. start (mm)" defines the micron-zero reference point.
      - Typing microns or using the µm step buttons drives position via
        depth = start_mm + microns / 1000.
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

        # ── Separator ─────────────────────────────────────────────────
        ttk.Separator(outer, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=6, pady=(2, 4))

        # ── Row 4: electrode start reference (mm) ─────────────────────
        row4 = ttk.Frame(outer)
        row4.pack(fill=tk.X, padx=6, pady=(0, 2))

        ttk.Label(row4, text="Elec. start (mm):").pack(side=tk.LEFT, padx=(0, 2))
        self._traj_elec_start_var = tk.StringVar(value="0.0")
        elec_start_entry = ttk.Entry(row4, textvariable=self._traj_elec_start_var,
                                     width=7, justify="right")
        elec_start_entry.pack(side=tk.LEFT, padx=2)
        elec_start_entry.bind("<Return>", self._on_traj_elec_start_change)
        elec_start_entry.bind("<FocusOut>", self._on_traj_elec_start_change)
        ttk.Label(row4, text="(depth along traj. where electrode tip starts)",
                  foreground="#888888", font=("TkDefaultFont", 8)).pack(side=tk.LEFT, padx=(6, 0))

        # ── Row 5: microns driven ─────────────────────────────────────
        row5 = ttk.Frame(outer)
        row5.pack(fill=tk.X, padx=6, pady=(0, 6))

        ttk.Button(row5, text="←", width=3,
                   command=lambda: self._on_traj_micron_step(-1)).pack(side=tk.LEFT, padx=(0, 2))

        ttk.Label(row5, text="Microns driven:").pack(side=tk.LEFT, padx=(4, 2))
        self._traj_microns_var = tk.StringVar(value="0")
        microns_entry = ttk.Entry(row5, textvariable=self._traj_microns_var,
                                  width=8, font=("TkDefaultFont", 10, "bold"),
                                  justify="right")
        microns_entry.pack(side=tk.LEFT, padx=(2, 1))
        microns_entry.bind("<Return>", self._on_traj_microns_enter)
        microns_entry.bind("<FocusOut>", self._on_traj_microns_enter)
        ttk.Label(row5, text="µm", font=("TkDefaultFont", 10, "bold"),
                  foreground="#0066cc").pack(side=tk.LEFT, padx=(0, 8))

        ttk.Label(row5, text="Step:").pack(side=tk.LEFT, padx=(4, 2))
        self._traj_micron_step_var = tk.StringVar(value="100")
        ttk.Entry(row5, textvariable=self._traj_micron_step_var, width=6,
                  justify="center").pack(side=tk.LEFT, padx=2)
        ttk.Label(row5, text="µm").pack(side=tk.LEFT, padx=(1, 4))

        ttk.Button(row5, text="→", width=3,
                   command=lambda: self._on_traj_micron_step(+1)).pack(side=tk.LEFT, padx=(2, 0))

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
            self._sync_microns_from_depth(dist_mm)
        finally:
            self._traj_slider_setting = False

        pack_kwargs = dict(fill=tk.X, padx=3, pady=(0, 2))
        if self._traj_slider_after_widget is not None:
            pack_kwargs["after"] = self._traj_slider_after_widget
        self._traj_slider_frame.pack(**pack_kwargs)

    # ------------------------------------------------------------------
    # Callbacks — mm controls
    # ------------------------------------------------------------------

    def _on_traj_slider_change(self, value):
        """Slider dragged — move crosshair and sync the entry box."""
        if self._traj_slider_setting or self.temp_trajectory is None:
            return
        depth_mm = float(value)
        self._traj_depth_entry_var.set(f"{depth_mm:.2f}")
        self._move_cursor_to_depth(depth_mm)

    def _on_traj_depth_enter(self, event=None):
        """Entry box committed — parse, clamp, move crosshair, and sync slider."""
        if self.temp_trajectory is None:
            return
        try:
            val = float(self._traj_depth_entry_var.get())
        except ValueError:
            return
        val = max(0.0, val)
        # NOTE: ttk.Scale's command callback only fires on direct widget
        # interaction, not on DoubleVar.set().  So we sync the slider visually
        # and drive the cursor move ourselves.
        self._traj_slider_setting = True
        try:
            self._traj_slider_var.set(val)
            self._traj_depth_entry_var.set(f"{val:.2f}")
        finally:
            self._traj_slider_setting = False
        self._move_cursor_to_depth(val)

    def _on_traj_step(self, direction):
        """Step button pressed — advance depth by ±step_size mm."""
        if self.temp_trajectory is None:
            return
        try:
            step = float(self._traj_step_var.get())
        except (ValueError, tk.TclError):
            step = 1.0
        current = self._traj_slider_var.get()
        new_val = max(0.0, current + direction * step)
        # Same issue as above — set var and drive move manually.
        self._traj_slider_setting = True
        try:
            self._traj_slider_var.set(new_val)
            self._traj_depth_entry_var.set(f"{new_val:.2f}")
        finally:
            self._traj_slider_setting = False
        self._move_cursor_to_depth(new_val)

    # ------------------------------------------------------------------
    # Callbacks — microns controls
    # ------------------------------------------------------------------

    def _on_traj_elec_start_change(self, event=None):
        """Electrode start reference changed — recompute microns from current depth."""
        self._sync_microns_from_depth(self._traj_slider_var.get())

    def _on_traj_microns_enter(self, event=None):
        """Microns entry committed — compute new mm depth and traverse."""
        if self.temp_trajectory is None:
            return
        try:
            microns = float(self._traj_microns_var.get())
        except ValueError:
            return
        start_mm = self._get_elec_start_mm()
        depth_mm = start_mm + microns / 1000.0
        depth_mm = max(0.0, depth_mm)
        # Recompute microns after clamping so display stays consistent
        clamped_microns = (depth_mm - start_mm) * 1000.0
        self._traj_slider_setting = True
        try:
            self._traj_slider_var.set(depth_mm)
            self._traj_depth_entry_var.set(f"{depth_mm:.2f}")
            self._traj_microns_var.set(f"{clamped_microns:.0f}")
        finally:
            self._traj_slider_setting = False
        self._move_cursor_to_depth(depth_mm)

    def _on_traj_micron_step(self, direction):
        """Micron step button — advance by ±micron_step µm."""
        if self.temp_trajectory is None:
            return
        try:
            step_um = float(self._traj_micron_step_var.get())
        except (ValueError, tk.TclError):
            step_um = 100.0
        try:
            microns = float(self._traj_microns_var.get())
        except ValueError:
            microns = 0.0
        self._traj_microns_var.set(f"{microns + direction * step_um:.0f}")
        self._on_traj_microns_enter()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_elec_start_mm(self):
        try:
            return float(self._traj_elec_start_var.get())
        except (ValueError, AttributeError):
            return 0.0

    def _sync_microns_from_depth(self, depth_mm):
        """Update the microns display to match current depth and electrode start."""
        if not hasattr(self, '_traj_microns_var'):
            return
        microns = (depth_mm - self._get_elec_start_mm()) * 1000.0
        self._traj_microns_var.set(f"{microns:.0f}")

    def _move_cursor_to_depth(self, depth_mm):
        """Shared helper: update cursor_world and redraw."""
        t = self.temp_trajectory
        self.cursor_world = t['top_pt'] + depth_mm * t['direction']
        if hasattr(self, 'traj_actual_dist_var'):
            self.traj_actual_dist_var.set(round(depth_mm, 2))
        self._sync_microns_from_depth(depth_mm)
        if self.data is not None:
            self.display_all()

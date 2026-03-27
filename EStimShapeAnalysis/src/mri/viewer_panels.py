import tkinter as tk
from tkinter import ttk

from src.mri.penetrations import COLORS

_CHANNEL_ORDER = [
    7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
    27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17
]


class PanelsMixin:
    def _build_ebz_panel(self, parent):
        ebz = ttk.LabelFrame(parent, text="EBZ (External Brain Zero)")
        ebz.pack(fill=tk.X, padx=5, pady=2)
        self._panel_frames['ebz'] = ebz
        for i, (lbl, vn) in enumerate([("AP mm:", "ebz_ap"), ("DV mm:", "ebz_dv"), ("ML mm:", "ebz_ml")]):
            ttk.Label(ebz, text=lbl).grid(row=0, column=2*i, padx=3, pady=2)
            v = tk.DoubleVar(value=0.0); setattr(self, vn + "_var", v)
            ttk.Entry(ebz, textvariable=v, width=10).grid(row=0, column=2*i+1, padx=3)
        self.btn_set_ebz = ttk.Button(ebz, text="Set EBZ (manual)", command=self._set_ebz_manual, state="disabled")
        self.btn_set_ebz.grid(row=0, column=6, padx=3)
        self.btn_ebz_xhair = ttk.Button(ebz, text="Set EBZ to crosshair", command=self._set_ebz_to_crosshair, state="disabled")
        self.btn_ebz_xhair.grid(row=0, column=7, padx=3)
        self.btn_reset_ebz = ttk.Button(ebz, text="Reset EBZ", command=self._reset_ebz, state="disabled")
        self.btn_reset_ebz.grid(row=0, column=8, padx=3)
        self.btn_ebz_pick = ttk.Button(ebz, text="Pick EBZ (right-click)", command=self._toggle_ebz_pick, state="disabled")
        self.btn_ebz_pick.grid(row=0, column=9, padx=3)
        self.cursor_info_var = tk.StringVar(value="Crosshair: ---")
        ttk.Label(ebz, textvariable=self.cursor_info_var).grid(row=1, column=0, columnspan=10, sticky="w", padx=5)
        self.ebz_pick_label_var = tk.StringVar(value="")
        ttk.Label(ebz, textvariable=self.ebz_pick_label_var, foreground="red").grid(row=2, column=0, columnspan=10, sticky="w", padx=5)

    def _build_correction_panel(self, parent):
        corr = ttk.LabelFrame(parent, text="Correction Matrix")
        corr.pack(fill=tk.X, padx=5, pady=2)
        self._panel_frames['correction'] = corr
        r_row = ttk.Frame(corr); r_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r_row, text="Rotate (deg):").pack(side=tk.LEFT, padx=3)
        for al, an in [("X(ML/roll)", "x"), ("Y(AP/pitch)", "y"), ("Z(DV/yaw)", "z")]:
            ttk.Label(r_row, text=f"{al}:").pack(side=tk.LEFT, padx=(6, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, f"rot_{an}_var", v)
            ttk.Entry(r_row, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)
        t_row = ttk.Frame(corr); t_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(t_row, text="Translate (mm):").pack(side=tk.LEFT, padx=3)
        for al, an in [("X(ML)", "tx"), ("Y(AP)", "ty"), ("Z(DV)", "tz")]:
            ttk.Label(t_row, text=f"{al}:").pack(side=tk.LEFT, padx=(6, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, f"trans_{an}_var", v)
            ttk.Entry(t_row, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)
        b_row = ttk.Frame(corr); b_row.pack(fill=tk.X, padx=3, pady=2)
        self.btn_apply = ttk.Button(b_row, text="Apply", command=self._apply_correction, state="disabled")
        self.btn_apply.pack(side=tk.LEFT, padx=3)
        self.btn_reset_corr = ttk.Button(b_row, text="Reset to Identity", command=self._reset_correction, state="disabled")
        self.btn_reset_corr.pack(side=tk.LEFT, padx=3)
        self.btn_undo = ttk.Button(b_row, text="Undo", command=self._undo, state="disabled")
        self.btn_undo.pack(side=tk.LEFT, padx=3)
        self.btn_redo = ttk.Button(b_row, text="Redo", command=self._redo, state="disabled")
        self.btn_redo.pack(side=tk.LEFT, padx=3)
        ttk.Button(b_row, text="History", command=self._show_history).pack(side=tk.LEFT, padx=3)
        ttk.Button(b_row, text="Header", command=self._show_header).pack(side=tk.LEFT, padx=3)
        self.corr_info_var = tk.StringVar(value="Correction: identity")
        ttk.Label(corr, textvariable=self.corr_info_var).pack(anchor="w", padx=5, pady=1)
        self.corr_ver_var = tk.StringVar(value="")
        ttk.Label(corr, textvariable=self.corr_ver_var).pack(anchor="w", padx=5, pady=1)
        note_row = ttk.Frame(corr); note_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(note_row, text="Note:").pack(side=tk.LEFT, padx=3)
        self.corr_note_var = tk.StringVar(value="")
        ttk.Entry(note_row, textvariable=self.corr_note_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

    def _build_crop_panel(self, parent):
        crop = ttk.LabelFrame(parent, text="View Cropping & Display")
        crop.pack(fill=tk.X, padx=5, pady=2)
        self._panel_frames['crop'] = crop

        row1 = ttk.Frame(crop); row1.pack(fill=tk.X, padx=3, pady=2)
        self.btn_crop = ttk.Button(row1, text="Crop (drag rect)", command=self._toggle_crop_mode, state="disabled")
        self.btn_crop.pack(side=tk.LEFT, padx=3)
        self.btn_reset_crop = ttk.Button(row1, text="Reset Crops", command=self._reset_crop, state="disabled")
        self.btn_reset_crop.pack(side=tk.LEFT, padx=3)
        self.btn_reset_zoom = ttk.Button(row1, text="Reset Zoom", command=self._reset_zoom, state="disabled")
        self.btn_reset_zoom.pack(side=tk.LEFT, padx=3)
        ttk.Label(row1, text="  Scroll to zoom, double-click to reset view", foreground="#555555").pack(side=tk.LEFT, padx=6)
        self.crop_status_var = tk.StringVar(value="")
        ttk.Label(row1, textvariable=self.crop_status_var, foreground="blue").pack(side=tk.LEFT, padx=6)

        row2 = ttk.Frame(crop); row2.pack(fill=tk.X, padx=3, pady=(0, 4))
        ttk.Label(row2, text="Interpolation:").pack(side=tk.LEFT, padx=3)
        self.interp_var = tk.StringVar(value="Cubic (order 3)")
        interp_cb = ttk.Combobox(row2, textvariable=self.interp_var, state="readonly", width=18,
                                  values=["Nearest (order 0)", "Linear (order 1)", "Cubic (order 3)"])
        interp_cb.pack(side=tk.LEFT, padx=3)
        interp_cb.bind("<<ComboboxSelected>>", self._on_interp_change)

        ttk.Label(row2, text="  Sample res (mm/px):").pack(side=tk.LEFT, padx=(12, 3))
        self.voxel_size_var = tk.DoubleVar(value=self.output_voxel_size)
        voxel_entry = ttk.Entry(row2, textvariable=self.voxel_size_var, width=6)
        voxel_entry.pack(side=tk.LEFT, padx=3)
        voxel_entry.bind("<Return>", self._on_voxel_size_change)
        ttk.Label(row2, text="(lower = finer, Enter to apply)").pack(side=tk.LEFT, padx=3)

    def _build_chamber_panel(self, parent):
        ch = ttk.LabelFrame(parent, text="Chamber & Penetrations")
        ch.pack(fill=tk.X, padx=5, pady=2)
        self._panel_frames['chamber'] = ch
        r1 = ttk.Frame(ch); r1.pack(fill=tk.X, padx=3, pady=2)
        self.btn_load_chamber = ttk.Button(r1, text="Load monkey_specific.py...", command=self._load_chamber_file)
        self.btn_load_chamber.pack(side=tk.LEFT, padx=3)
        self.btn_toggle_chamber = ttk.Button(r1, text="Hide Chamber", command=self._toggle_chamber, state="disabled")
        self.btn_toggle_chamber.pack(side=tk.LEFT, padx=3)
        self.btn_connect_db = ttk.Button(r1, text="Connect DB", command=self._connect_db)
        self.btn_connect_db.pack(side=tk.LEFT, padx=3)
        self.btn_pen_list = ttk.Button(r1, text="Penetration List", command=self._show_pen_list, state="disabled")
        self.btn_pen_list.pack(side=tk.LEFT, padx=3)
        self.chamber_info_var = tk.StringVar(value="No chamber loaded")
        ttk.Label(ch, textvariable=self.chamber_info_var).pack(anchor="w", padx=5, pady=1)

        pen_row = ttk.Frame(ch); pen_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(pen_row, text="Az(°):").pack(side=tk.LEFT, padx=2)
        self.pen_az_var = tk.DoubleVar(value=0.0)
        ttk.Entry(pen_row, textvariable=self.pen_az_var, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(pen_row, text="El(°):").pack(side=tk.LEFT, padx=2)
        self.pen_el_var = tk.DoubleVar(value=0.0)
        ttk.Entry(pen_row, textvariable=self.pen_el_var, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(pen_row, text="Dist(mm):").pack(side=tk.LEFT, padx=2)
        self.pen_dist_var = tk.DoubleVar(value=35.0)
        ttk.Entry(pen_row, textvariable=self.pen_dist_var, width=7).pack(side=tk.LEFT, padx=2)
        ttk.Label(pen_row, text="Label:").pack(side=tk.LEFT, padx=2)
        self.pen_label_var = tk.StringVar(value="")
        ttk.Entry(pen_row, textvariable=self.pen_label_var, width=10).pack(side=tk.LEFT, padx=2)
        ttk.Label(pen_row, text="Notes:").pack(side=tk.LEFT, padx=2)
        self.pen_notes_var = tk.StringVar(value="")
        ttk.Entry(pen_row, textvariable=self.pen_notes_var, width=20).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        br = ttk.Frame(ch); br.pack(fill=tk.X, padx=3, pady=2)
        self.btn_add_pen = ttk.Button(br, text="Add Penetration", command=self._add_penetration, state="disabled")
        self.btn_add_pen.pack(side=tk.LEFT, padx=3)
        self.btn_toggle_pens = ttk.Button(br, text="Hide Penetrations", command=self._toggle_pens, state="disabled")
        self.btn_toggle_pens.pack(side=tk.LEFT, padx=3)

        # Chamber Correction sub-panel
        cc = ttk.LabelFrame(ch, text="Chamber Correction")
        cc.pack(fill=tk.X, padx=5, pady=4)
        cr_row = ttk.Frame(cc); cr_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(cr_row, text="Rotate (deg):").pack(side=tk.LEFT, padx=3)
        for lbl, attr in [("X(ML/roll)", "ch_rot_x_var"), ("Y(AP/pitch)", "ch_rot_y_var"), ("Z(DV/yaw)", "ch_rot_z_var")]:
            ttk.Label(cr_row, text=f"{lbl}:").pack(side=tk.LEFT, padx=(6, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, attr, v)
            ttk.Entry(cr_row, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)
        ct_row = ttk.Frame(cc); ct_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(ct_row, text="Translate (mm):").pack(side=tk.LEFT, padx=3)
        for lbl, attr in [("X(ML)", "ch_trans_tx_var"), ("Y(AP)", "ch_trans_ty_var"), ("Z(DV)", "ch_trans_tz_var")]:
            ttk.Label(ct_row, text=f"{lbl}:").pack(side=tk.LEFT, padx=(6, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, attr, v)
            ttk.Entry(ct_row, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)
        cb_row = ttk.Frame(cc); cb_row.pack(fill=tk.X, padx=3, pady=2)
        self.btn_ch_apply = ttk.Button(cb_row, text="Apply", command=self._apply_chamber_correction, state="disabled")
        self.btn_ch_apply.pack(side=tk.LEFT, padx=3)
        self.btn_ch_reset = ttk.Button(cb_row, text="Reset to Identity", command=self._reset_chamber_correction, state="disabled")
        self.btn_ch_reset.pack(side=tk.LEFT, padx=3)
        self.btn_ch_undo = ttk.Button(cb_row, text="Undo", command=self._chamber_corr_undo, state="disabled")
        self.btn_ch_undo.pack(side=tk.LEFT, padx=3)
        self.btn_ch_redo = ttk.Button(cb_row, text="Redo", command=self._chamber_corr_redo, state="disabled")
        self.btn_ch_redo.pack(side=tk.LEFT, padx=3)
        ttk.Button(cb_row, text="History", command=self._show_chamber_corr_history).pack(side=tk.LEFT, padx=3)
        self.ch_corr_info_var = tk.StringVar(value="")
        ttk.Label(cc, textvariable=self.ch_corr_info_var).pack(anchor="w", padx=5, pady=1)
        self.ch_corr_ver_var = tk.StringVar(value="")
        ttk.Label(cc, textvariable=self.ch_corr_ver_var).pack(anchor="w", padx=5, pady=1)
        cn_row = ttk.Frame(cc); cn_row.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(cn_row, text="Note:").pack(side=tk.LEFT, padx=3)
        self.ch_corr_note_var = tk.StringVar(value="")
        ttk.Entry(cn_row, textvariable=self.ch_corr_note_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

    def _build_trajectory_panel(self, parent):
        tp = ttk.LabelFrame(parent, text="Trajectory Planner")
        tp.pack(fill=tk.X, padx=5, pady=2)
        self._panel_frames['trajectory'] = tp

        # Section 1: Define the trajectory line
        s1 = ttk.LabelFrame(tp, text="1. Define Trajectory (sets the line)")
        s1.pack(fill=tk.X, padx=3, pady=2)

        r1a = ttk.Frame(s1); r1a.pack(fill=tk.X, padx=3, pady=1)
        ttk.Label(r1a, text="Stereotaxic:").pack(side=tk.LEFT, padx=3)
        self.traj_ml_var = tk.DoubleVar(value=0.0)
        self.traj_ap_var = tk.DoubleVar(value=0.0)
        self.traj_dv_var = tk.DoubleVar(value=0.0)
        for lbl, var in [("ML:", self.traj_ml_var), ("AP:", self.traj_ap_var), ("DV:", self.traj_dv_var)]:
            ttk.Label(r1a, text=lbl).pack(side=tk.LEFT, padx=(6, 1))
            e = ttk.Entry(r1a, textvariable=var, width=8)
            e.pack(side=tk.LEFT, padx=1)
            e.bind("<Return>", lambda ev: self._on_traj_stereo_enter())
        self.traj_stereo_label = ttk.Label(r1a, text="", foreground="#555555")
        self.traj_stereo_label.pack(side=tk.LEFT, padx=4)

        r1b = ttk.Frame(s1); r1b.pack(fill=tk.X, padx=3, pady=1)
        ttk.Label(r1b, text="Chamber:").pack(side=tk.LEFT, padx=3)
        self.traj_az_var = tk.DoubleVar(value=0.0)
        self.traj_el_var = tk.DoubleVar(value=0.0)
        self.traj_dist_var = tk.DoubleVar(value=35.0)
        for lbl, var in [("Az(°):", self.traj_az_var), ("El(°):", self.traj_el_var), ("Dist(mm):", self.traj_dist_var)]:
            ttk.Label(r1b, text=lbl).pack(side=tk.LEFT, padx=(6, 1))
            e = ttk.Entry(r1b, textvariable=var, width=8)
            e.pack(side=tk.LEFT, padx=1)
            e.bind("<Return>", lambda ev: self._on_traj_chamber_enter())

        r1c = ttk.Frame(s1); r1c.pack(fill=tk.X, padx=3, pady=2)
        self.btn_plan_traj = ttk.Button(r1c, text="Plan to Cursor",
                                         command=self._plan_trajectory, state="disabled")
        self.btn_plan_traj.pack(side=tk.LEFT, padx=3)
        self.btn_set_traj = ttk.Button(r1c, text="Set Trajectory (from entries)",
                                        command=self._on_traj_chamber_enter, state="disabled")
        self.btn_set_traj.pack(side=tk.LEFT, padx=3)
        self.btn_clear_traj = ttk.Button(r1c, text="Clear All",
                                          command=self._clear_trajectory, state="disabled")
        self.btn_clear_traj.pack(side=tk.LEFT, padx=3)

        self.traj_info_var = tk.StringVar(value="No trajectory set")
        ttk.Label(s1, textvariable=self.traj_info_var, font=("TkDefaultFont", 9),
                  foreground="#006699").pack(anchor="w", padx=5, pady=(0, 2))

        # Section 2: Add points along the trajectory
        s2 = ttk.LabelFrame(tp, text="2. Mark Points (along the trajectory)")
        s2.pack(fill=tk.X, padx=3, pady=2)

        r2a = ttk.Frame(s2); r2a.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r2a, text="Point Dist(mm):").pack(side=tk.LEFT, padx=3)
        self.traj_pt_dist_var = tk.DoubleVar(value=35.0)
        pt_dist_entry = ttk.Entry(r2a, textvariable=self.traj_pt_dist_var, width=8)
        pt_dist_entry.pack(side=tk.LEFT, padx=2)
        pt_dist_entry.bind("<Return>", lambda ev: self._on_pt_dist_enter())

        ttk.Label(r2a, text="Label:").pack(side=tk.LEFT, padx=(8, 2))
        self.traj_label_var = tk.StringVar(value="")
        ttk.Entry(r2a, textvariable=self.traj_label_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(r2a, text="Color:").pack(side=tk.LEFT, padx=(6, 2))
        self.traj_color_var = tk.StringVar(value="yellow")
        ttk.Combobox(r2a, textvariable=self.traj_color_var, state="readonly", width=8,
                      values=COLORS).pack(side=tk.LEFT, padx=2)
        ttk.Label(r2a, text="Notes:").pack(side=tk.LEFT, padx=(6, 2))
        self.traj_notes_var = tk.StringVar(value="")
        ttk.Entry(r2a, textvariable=self.traj_notes_var, width=15).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        r2b = ttk.Frame(s2); r2b.pack(fill=tk.X, padx=3, pady=2)
        self.btn_add_point = ttk.Button(r2b, text="Add Point at Dist",
                                         command=self._add_temp_point, state="disabled")
        self.btn_add_point.pack(side=tk.LEFT, padx=3)
        self.btn_remove_point = ttk.Button(r2b, text="Remove Last",
                                            command=self._remove_last_temp_point, state="disabled")
        self.btn_remove_point.pack(side=tk.LEFT, padx=3)
        self.traj_pt_info_var = tk.StringVar(value="")
        ttk.Label(r2b, textvariable=self.traj_pt_info_var, foreground="#555555",
                  font=("TkDefaultFont", 8)).pack(side=tk.LEFT, padx=8)

        # Section 3: Record Actual (during experiment)
        s3 = ttk.LabelFrame(tp, text="3. Record Actual (during experiment)")
        s3.pack(fill=tk.X, padx=3, pady=2)

        r3a = ttk.Frame(s3); r3a.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r3a, text="Tip Dist(mm):").pack(side=tk.LEFT, padx=3)
        self.traj_actual_dist_var = tk.DoubleVar(value=35.0)
        ttk.Entry(r3a, textvariable=self.traj_actual_dist_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(r3a, text="Channel#:").pack(side=tk.LEFT, padx=(8, 2))
        self.traj_channel_var = tk.StringVar(value="0")
        ttk.Combobox(r3a, textvariable=self.traj_channel_var, width=6,
                      values=sorted(_CHANNEL_ORDER)).pack(side=tk.LEFT, padx=2)
        ttk.Label(r3a, text="Label:").pack(side=tk.LEFT, padx=(8, 2))
        self.traj_actual_label_var = tk.StringVar(value="")
        ttk.Entry(r3a, textvariable=self.traj_actual_label_var, width=8).pack(side=tk.LEFT, padx=2)
        ttk.Label(r3a, text="Notes:").pack(side=tk.LEFT, padx=(6, 2))
        self.traj_actual_notes_var = tk.StringVar(value="")
        ttk.Entry(r3a, textvariable=self.traj_actual_notes_var, width=15).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=2)

        r3b = ttk.Frame(s3); r3b.pack(fill=tk.X, padx=3, pady=2)
        self.btn_record_actual = ttk.Button(r3b, text="Record Actual Point",
                                             command=self._record_actual_point, state="disabled")
        self.btn_record_actual.pack(side=tk.LEFT, padx=3)
        self.traj_actual_info_var = tk.StringVar(value="")
        ttk.Label(r3b, textvariable=self.traj_actual_info_var, foreground="#006699",
                  font=("TkDefaultFont", 8)).pack(side=tk.LEFT, padx=8)

        # Section 4: Save planned points
        s4 = ttk.LabelFrame(tp, text="4. Save Planned Points")
        s4.pack(fill=tk.X, padx=3, pady=2)

        r4a = ttk.Frame(s4); r4a.pack(fill=tk.X, padx=3, pady=2)
        self.btn_save_traj = ttk.Button(r4a, text="Save Planned to DB",
                                         command=self._save_trajectory, state="disabled")
        self.btn_save_traj.pack(side=tk.LEFT, padx=3)

        self.traj_points_var = tk.StringVar(value="")
        ttk.Label(s4, textvariable=self.traj_points_var, font=("TkDefaultFont", 8),
                  foreground="#444444").pack(anchor="w", padx=5, pady=(0, 3))

    def _build_atlas_panel(self, parent):
        at = ttk.LabelFrame(parent, text="Atlas Alignment  (hotkey 'A' to toggle)")
        at.pack(fill=tk.X, padx=5, pady=2)
        self._panel_frames['atlas'] = at

        # Row 1: file loading + toggle
        r1 = ttk.Frame(at); r1.pack(fill=tk.X, padx=3, pady=2)
        self.btn_load_atlas = ttk.Button(r1, text="Load Atlas NIfTI...", command=self._browse_atlas_nifti)
        self.btn_load_atlas.pack(side=tk.LEFT, padx=3)
        self.btn_load_atlas_labels = ttk.Button(r1, text="Load Labels...", command=self._browse_atlas_labels, state="disabled")
        self.btn_load_atlas_labels.pack(side=tk.LEFT, padx=3)
        self.btn_load_template = ttk.Button(r1, text="Load Template MRI...", command=self._browse_template_mri, state="disabled")
        self.btn_load_template.pack(side=tk.LEFT, padx=3)
        self.btn_toggle_atlas = ttk.Button(r1, text="Show Atlas", command=self._toggle_atlas, state="disabled")
        self.btn_toggle_atlas.pack(side=tk.LEFT, padx=3)
        self.atlas_info_var = tk.StringVar(value="No atlas loaded")
        ttk.Label(r1, textvariable=self.atlas_info_var).pack(side=tk.LEFT, padx=8)

        # Row 1b: template MRI blend slider
        r1b = ttk.Frame(at); r1b.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r1b, text="MRI Blend ('T' to snap):").pack(side=tk.LEFT, padx=3)
        ttk.Label(r1b, text="Subject").pack(side=tk.LEFT, padx=(3, 0))
        self.blend_var = tk.DoubleVar(value=0.0)
        self.blend_scale = ttk.Scale(r1b, from_=0.0, to=1.0, orient=tk.HORIZONTAL,
                                      variable=self.blend_var,
                                      command=self._on_blend_slider)
        self.blend_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        ttk.Label(r1b, text="Template").pack(side=tk.LEFT, padx=(0, 3))
        self.blend_lbl = ttk.Label(r1b, text="0%", width=5)
        self.blend_lbl.pack(side=tk.LEFT, padx=3)

        # Row 2: rotation
        r2 = ttk.Frame(at); r2.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r2, text="Rotate (deg):").pack(side=tk.LEFT, padx=3)
        for al, an in [("X(ML/roll)", "x"), ("Y(AP/pitch)", "y"), ("Z(DV/yaw)", "z")]:
            ttk.Label(r2, text=f"{al}:").pack(side=tk.LEFT, padx=(6, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, f"atlas_rot_{an}_var", v)
            ttk.Entry(r2, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)

        # Row 3: translation
        r3 = ttk.Frame(at); r3.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r3, text="Translate (mm):").pack(side=tk.LEFT, padx=3)
        for al, an in [("X(ML)", "tx"), ("Y(AP)", "ty"), ("Z(DV)", "tz")]:
            ttk.Label(r3, text=f"{al}:").pack(side=tk.LEFT, padx=(6, 2))
            v = tk.DoubleVar(value=0.0); setattr(self, f"atlas_trans_{an}_var", v)
            ttk.Entry(r3, textvariable=v, width=7).pack(side=tk.LEFT, padx=2)

        # Row 3b: scale (uniform by default, per-axis optional)
        r3b = ttk.Frame(at); r3b.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r3b, text="Scale (%):").pack(side=tk.LEFT, padx=3)
        ttk.Label(r3b, text="Uniform:").pack(side=tk.LEFT, padx=(6, 2))
        self.atlas_scale_uniform_var = tk.DoubleVar(value=0.0)
        self.atlas_scale_uniform_entry = ttk.Entry(r3b, textvariable=self.atlas_scale_uniform_var, width=7)
        self.atlas_scale_uniform_entry.pack(side=tk.LEFT, padx=2)
        ttk.Label(r3b, text="  Per-axis:").pack(side=tk.LEFT, padx=(10, 2))
        self.atlas_scale_peraxis_var = tk.BooleanVar(value=False)
        self.atlas_scale_peraxis_cb = ttk.Checkbutton(
            r3b, variable=self.atlas_scale_peraxis_var,
            command=self._on_atlas_scale_mode_change)
        self.atlas_scale_peraxis_cb.pack(side=tk.LEFT, padx=2)
        self.atlas_scale_axis_vars = {}
        self.atlas_scale_axis_entries = {}
        for al, an in [("X:", "sx"), ("Y:", "sy"), ("Z:", "sz")]:
            lbl = ttk.Label(r3b, text=al); lbl.pack(side=tk.LEFT, padx=(4, 1))
            v = tk.DoubleVar(value=0.0); self.atlas_scale_axis_vars[an] = v
            e = ttk.Entry(r3b, textvariable=v, width=6, state="disabled")
            e.pack(side=tk.LEFT, padx=1)
            self.atlas_scale_axis_entries[an] = e
        ttk.Label(r3b, text="(0 = no change)", foreground="#555555").pack(side=tk.LEFT, padx=6)

        # Row 4: buttons
        r4 = ttk.Frame(at); r4.pack(fill=tk.X, padx=3, pady=2)
        self.btn_atlas_apply = ttk.Button(r4, text="Apply", command=self._apply_atlas_correction, state="disabled")
        self.btn_atlas_apply.pack(side=tk.LEFT, padx=3)
        self.btn_atlas_reset = ttk.Button(r4, text="Reset to Identity", command=self._reset_atlas_correction, state="disabled")
        self.btn_atlas_reset.pack(side=tk.LEFT, padx=3)
        self.btn_atlas_undo = ttk.Button(r4, text="Undo", command=self._atlas_undo, state="disabled")
        self.btn_atlas_undo.pack(side=tk.LEFT, padx=3)
        self.btn_atlas_redo = ttk.Button(r4, text="Redo", command=self._atlas_redo, state="disabled")
        self.btn_atlas_redo.pack(side=tk.LEFT, padx=3)
        ttk.Button(r4, text="History", command=self._show_atlas_history).pack(side=tk.LEFT, padx=3)

        # Row 5: appearance
        r5 = ttk.Frame(at); r5.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(r5, text="Contour color:").pack(side=tk.LEFT, padx=3)
        self.atlas_color_var = tk.StringVar(value="cyan")
        color_cb = ttk.Combobox(r5, textvariable=self.atlas_color_var, state="readonly", width=10,
                                values=["cyan", "yellow", "lime", "magenta", "red", "orange", "white"])
        color_cb.pack(side=tk.LEFT, padx=3)
        color_cb.bind("<<ComboboxSelected>>", self._on_atlas_color_change)

        ttk.Label(r5, text="Line width:").pack(side=tk.LEFT, padx=(8, 3))
        self.atlas_lw_var = tk.DoubleVar(value=0.6)
        ttk.Entry(r5, textvariable=self.atlas_lw_var, width=5).pack(side=tk.LEFT, padx=3)

        ttk.Label(r5, text="Alpha:").pack(side=tk.LEFT, padx=(8, 3))
        self.atlas_alpha_var = tk.DoubleVar(value=0.7)
        ttk.Entry(r5, textvariable=self.atlas_alpha_var, width=5).pack(side=tk.LEFT, padx=3)

        # Info / version
        self.atlas_corr_info_var = tk.StringVar(value="")
        ttk.Label(at, textvariable=self.atlas_corr_info_var).pack(anchor="w", padx=5, pady=1)
        self.atlas_corr_ver_var = tk.StringVar(value="")
        ttk.Label(at, textvariable=self.atlas_corr_ver_var).pack(anchor="w", padx=5, pady=1)

        # Note
        nr = ttk.Frame(at); nr.pack(fill=tk.X, padx=3, pady=2)
        ttk.Label(nr, text="Note:").pack(side=tk.LEFT, padx=3)
        self.atlas_corr_note_var = tk.StringVar(value="")
        ttk.Entry(nr, textvariable=self.atlas_corr_note_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)

    def _build_sliders(self, parent):
        sf = ttk.Frame(parent); sf.pack(fill=tk.X, padx=5, pady=2)
        self.slice_vars, self.slice_scales, self.slice_lbls, self.ebz_goto_btns = [], [], [], []
        for i, name in enumerate(self.VIEW_NAMES):
            ttk.Label(sf, text=f"{name}:").grid(row=i, column=0, sticky="w", padx=3, pady=1)
            v = tk.DoubleVar(value=0.0)
            sc = ttk.Scale(sf, from_=0, to=1, orient=tk.HORIZONTAL, variable=v,
                           command=lambda val, idx=i: self._on_slider(idx))
            sc.grid(row=i, column=1, sticky="we", padx=3)
            lb = ttk.Label(sf, text="0.00 mm", width=20)
            lb.grid(row=i, column=2, padx=3)
            btn = ttk.Button(sf, text="→0", width=3,
                             command=lambda idx=i: self._goto_ebz_zero(idx), state="disabled")
            btn.grid(row=i, column=3, padx=2)
            self.slice_vars.append(v); self.slice_scales.append(sc)
            self.slice_lbls.append(lb); self.ebz_goto_btns.append(btn)
        sf.columnconfigure(1, weight=1)

        self.dyn_frame = ttk.Frame(sf)
        self.dyn_frame.grid(row=3, column=0, columnspan=4, sticky="we")
        ttk.Label(self.dyn_frame, text="Dynamic:").grid(row=0, column=0, sticky="w", padx=3)
        self.dyn_var = tk.IntVar(value=0)
        self.dyn_scale = ttk.Scale(self.dyn_frame, from_=0, to=0, orient=tk.HORIZONTAL,
                                   variable=self.dyn_var, command=lambda *a: self._on_dyn_slider())
        self.dyn_scale.grid(row=0, column=1, sticky="we", padx=3)
        self.dyn_lbl = ttk.Label(self.dyn_frame, text="0/0", width=14)
        self.dyn_lbl.grid(row=0, column=2, padx=3)
        self.dyn_frame.columnconfigure(1, weight=1)
        self.dyn_frame.grid_remove()

import numpy as np
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from src.mri.chamber import fit_chamber
from src.mri.correction import load_corrections, save_corrections, push_correction, rot_x, rot_y, rot_z, xlate

class ChamberMixin:
    def _load_chamber_file(self):
        fn = filedialog.askopenfilename(title="Select monkey_specific.py",
                                        filetypes=[("Python", "*.py"), ("All", "*.*")])
        if not fn:
            return
        self._load_chamber_from_path(fn)

    def _load_chamber_from_path(self, fn):
        """Load a monkey_specific.py by absolute path. Safe to call before a volume is loaded."""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("monkey_specific", fn)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)

            screws_ebz = mod.get_screw_hole_coords()
            self._chamber_params['ref_screw_idx'] = mod.get_reference_screw_idx()
            self._chamber_params['center_of_rotation_offset'] = mod.get_center_of_rotation_offset()
            self._chamber_params['is_fit_circle'] = mod.get_is_fit_circle()
            if hasattr(mod, 'get_chamber_depth'):
                self._chamber_params['chamber_depth'] = mod.get_chamber_depth()

            self._base_screws_ebz = np.array(screws_ebz, dtype=float)
            self.chamber_state['screws_ebz'] = self._base_screws_ebz
            self.chamber_state['cor_offset'] = self._chamber_params['center_of_rotation_offset']
            self._chamber_path = fn  # remembered so _save_defaults can persist it

            # Load chamber correction history
            self.chamber_corr_json_path = self._chamber_corr_json_for(fn)
            self.chamber_correction, self.chamber_corr_config = load_corrections(self.chamber_corr_json_path)

            self._refit_chamber()
            self.btn_ch_apply.config(state="normal")
            self.btn_ch_reset.config(state="normal")
            self.btn_ch_undo.config(state="normal")
            self.btn_ch_redo.config(state="normal")
            self._update_chamber_corr_info()

            self.btn_toggle_chamber.config(state="normal")
            if self.pen_store.connected:
                self.btn_add_pen.config(state="normal")
                self.btn_load_session.config(state="normal")
            if self.data is not None:
                self.btn_plan_traj.config(state="normal")
                self.btn_set_traj.config(state="normal")

            if hasattr(mod, 'get_electrode_target'):
                mode, coords = mod.get_electrode_target()
                if mode == 'angles':
                    self.pen_az_var.set(coords[0]); self.pen_el_var.set(coords[1]); self.pen_dist_var.set(coords[2])

            if self.data is not None:
                self.display_all()
        except Exception as e:
            messagebox.showerror("Error loading chamber file", str(e))
            import traceback; traceback.print_exc()

    def _refit_chamber(self):
        base_screws = self._base_screws_ebz
        if base_screws is None:
            base_screws = self.chamber_state.get('screws_ebz')
        if base_screws is None:
            return
        base_screws = np.array(base_screws, dtype=float)
        ebz = self.ebz_world if self.ebz_set else np.zeros(3)
        screws_world = base_screws + ebz

        # Apply chamber correction (rigid body transform in world space)
        if not np.allclose(self.chamber_correction, np.eye(4)):
            R = self.chamber_correction[:3, :3]
            t = self.chamber_correction[:3, 3]
            screws_world = (R @ screws_world.T).T + t

        # Store corrected screws (EBZ-relative) so draw_chamber_overlay renders them at the right place
        self.chamber_state['screws_ebz'] = screws_world - ebz

        center, origin, x, y, normal = fit_chamber(
            screws_world,
            self._chamber_params['ref_screw_idx'],
            self._chamber_params['center_of_rotation_offset'],
            self._chamber_params['is_fit_circle'])

        self.chamber_state.update({
            'loaded': True, 'center': center, 'origin': origin,
            'x': x, 'y': y, 'normal': normal,
        })
        self.chamber_info_var.set(
            f"Chamber: {len(base_screws)} screwholes, origin="
            f"[{origin[0]:.1f}, {origin[1]:.1f}, {origin[2]:.1f}] mm")

    def _toggle_chamber(self):
        self.chamber_show = not self.chamber_show
        self.btn_toggle_chamber.config(text="Show Chamber" if not self.chamber_show else "Hide Chamber")
        self.display_all()

    # ================================================================ Chamber Correction
    def _apply_chamber_correction(self):
        if not self.chamber_state.get('loaded'):
            return
        rx = self.ch_rot_x_var.get()
        ry = self.ch_rot_y_var.get()
        rz = self.ch_rot_z_var.get()
        tx = self.ch_trans_tx_var.get()
        ty = self.ch_trans_ty_var.get()
        tz = self.ch_trans_tz_var.get()
        # Rotate about the chamber center so pure rotation doesn't shift it translationally
        center = self.chamber_state.get('center')
        if center is None:
            center = np.zeros(3)
        R_pure = rot_z(rz) @ rot_y(ry) @ rot_x(rx)
        R_about_center = xlate(center[0], center[1], center[2]) @ R_pure @ xlate(-center[0], -center[1], -center[2])
        delta = xlate(tx, ty, tz) @ R_about_center
        new_corr = delta @ self.chamber_correction
        note = self.ch_corr_note_var.get().strip()
        if not note:
            parts = []
            if rx: parts.append(f"Rx={rx}")
            if ry: parts.append(f"Ry={ry}")
            if rz: parts.append(f"Rz={rz}")
            if tx: parts.append(f"Tx={tx}")
            if ty: parts.append(f"Ty={ty}")
            if tz: parts.append(f"Tz={tz}")
            note = ", ".join(parts) if parts else "no-op"
        self.chamber_correction = new_corr
        push_correction(self.chamber_corr_config, new_corr, note)
        save_corrections(self.chamber_corr_json_path, self.chamber_corr_config)
        self._refit_chamber()
        self._update_chamber_corr_info()
        for v in (self.ch_rot_x_var, self.ch_rot_y_var, self.ch_rot_z_var,
                  self.ch_trans_tx_var, self.ch_trans_ty_var, self.ch_trans_tz_var):
            v.set(0)
        self.ch_corr_note_var.set("")
        if self.data is not None:
            self.display_all()

    def _reset_chamber_correction(self):
        if not self.chamber_state.get('loaded'):
            return
        self.chamber_correction = np.eye(4)
        push_correction(self.chamber_corr_config, self.chamber_correction, "reset to identity")
        save_corrections(self.chamber_corr_json_path, self.chamber_corr_config)
        self._refit_chamber()
        self._update_chamber_corr_info()
        if self.data is not None:
            self.display_all()

    def _load_chamber_corr_version(self, idx):
        hist = self.chamber_corr_config["correction_history"]
        if 0 <= idx < len(hist):
            self.chamber_corr_config["current_index"] = idx
            self.chamber_correction = np.array(hist[idx]["matrix"])
            save_corrections(self.chamber_corr_json_path, self.chamber_corr_config)
            self._refit_chamber()
            self._update_chamber_corr_info()
            if self.data is not None:
                self.display_all()

    def _chamber_corr_undo(self):
        if not self.chamber_state.get('loaded'):
            return
        idx = self.chamber_corr_config.get("current_index", 0)
        if idx > 0:
            self._load_chamber_corr_version(idx - 1)
        else:
            self.status_var.set("Chamber: already at oldest version.")

    def _chamber_corr_redo(self):
        if not self.chamber_state.get('loaded'):
            return
        idx = self.chamber_corr_config.get("current_index", 0)
        if idx < len(self.chamber_corr_config.get("correction_history", [])) - 1:
            self._load_chamber_corr_version(idx + 1)
        else:
            self.status_var.set("Chamber: already at newest version.")

    def _update_chamber_corr_info(self):
        if self.chamber_corr_config is None:
            return
        idx = self.chamber_corr_config.get("current_index", 0)
        n = len(self.chamber_corr_config["correction_history"])
        entry = self.chamber_corr_config["correction_history"][idx]
        if np.allclose(self.chamber_correction, np.eye(4)):
            self.ch_corr_info_var.set("Chamber correction: identity")
        else:
            t = self.chamber_correction[:3, 3]
            det = np.linalg.det(self.chamber_correction[:3, :3])
            self.ch_corr_info_var.set(
                f"Chamber correction: det={det:.6f}  T=[{t[0]:.2f}, {t[1]:.2f}, {t[2]:.2f}] mm")
        self.ch_corr_ver_var.set(
            f"Version {idx+1}/{n}  |  {entry.get('timestamp','')}  |  {entry.get('note','')}")

    def _show_chamber_corr_history(self):
        if not self.chamber_corr_config:
            return
        win = tk.Toplevel(self.root); win.title("Chamber Correction History"); win.geometry("850x550")
        frame = ttk.Frame(win); frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        sb = ttk.Scrollbar(frame); sb.pack(side=tk.RIGHT, fill=tk.Y)
        txt = tk.Text(frame, wrap=tk.WORD, yscrollcommand=sb.set, font=("Courier", 10))
        txt.pack(fill=tk.BOTH, expand=True); sb.config(command=txt.yview)
        cur = self.chamber_corr_config.get("current_index", 0)
        for i, e in enumerate(self.chamber_corr_config["correction_history"]):
            mark = "  << CURRENT" if i == cur else ""
            txt.insert(tk.END, f"--- Version {i+1}{mark} ---\n")
            txt.insert(tk.END, f"  Time: {e.get('timestamp','')}\n  Note: {e.get('note','')}\n")
            for row in np.array(e["matrix"]):
                txt.insert(tk.END, f"    [{row[0]:10.6f} {row[1]:10.6f} {row[2]:10.6f} {row[3]:10.6f}]\n")
            txt.insert(tk.END, "\n")
        jf = ttk.Frame(win); jf.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(jf, text="Jump to:").pack(side=tk.LEFT, padx=3)
        jv = tk.IntVar(value=cur + 1)
        ttk.Entry(jf, textvariable=jv, width=5).pack(side=tk.LEFT, padx=3)
        def jump():
            t = jv.get() - 1
            if 0 <= t < len(self.chamber_corr_config["correction_history"]):
                self._load_chamber_corr_version(t); win.destroy()
        ttk.Button(jf, text="Jump", command=jump).pack(side=tk.LEFT, padx=3)
        txt.config(state=tk.DISABLED)

    # ================================================================ Penetrations (DB)

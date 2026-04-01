import os, json, pprint
import numpy as np
import tkinter as tk
from tkinter import messagebox, ttk
from src.mri.chamber import calc_penetration_target, calc_target_angles
from src.mri.penetrations import PenetrationStore, PenetrationListWindow, COLORS

# Probe geometry (matches import_penetration.py)
_TIP_TO_BOTTOM_CH_UM = 600   # μm from probe tip to bottommost channel
_CH_SPACING_UM = 65           # μm between adjacent channels
_N_CHANNELS = 32
_CHANNEL_ORDER = [
    7, 8, 25, 22, 0, 15, 24, 23, 6, 9, 26, 21, 5, 10, 31, 16,
    27, 20, 4, 11, 28, 19, 1, 14, 3, 12, 29, 18, 2, 13, 30, 17
]


def _channel_corrected_dist(tip_dist_mm, channel_num):
    """Apply channel offset correction: returns distance to given channel instead of tip."""
    idx = _CHANNEL_ORDER.index(channel_num)
    offset_um = _TIP_TO_BOTTOM_CH_UM + (31 - idx) * _CH_SPACING_UM
    return tip_dist_mm - offset_um / 1000.0


class TrajectoryMixin:
    def _connect_db(self):
        try:
            self.pen_store.connect()
            self.btn_pen_list.config(state="normal")
            self.btn_toggle_pens.config(state="normal")
            if self.chamber_state['loaded']:
                self.btn_add_pen.config(state="normal")
            if self.temp_trajectory is not None or self.temp_points:
                self.btn_save_traj.config(state="normal")
            if self.temp_trajectory is not None:
                self.btn_record_actual.config(state="normal")
            n = len(self.pen_store.penetrations)
            self.status_var.set(f"DB connected. {n} penetrations loaded.")
            if self.chamber_state['loaded']:
                self.btn_load_session.config(state="normal")
            self.display_all()
        except Exception as e:
            messagebox.showerror("DB Error", str(e))
            import traceback; traceback.print_exc()

    def _add_penetration(self):
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first."); return
        if not self.chamber_state['loaded']:
            messagebox.showerror("Error", "Load chamber first."); return
        az = self.pen_az_var.get()
        el = self.pen_el_var.get()
        dist = self.pen_dist_var.get()
        label = self.pen_label_var.get().strip()
        notes = self.pen_notes_var.get().strip()
        session_id = self.session_id_var.get().strip()
        color = COLORS[len(self.pen_store.penetrations) % len(COLORS)]
        self.pen_store.add(az, el, dist, label=label, session_id=session_id,
                           color=color, notes=notes)
        self.display_all()

    def _toggle_pens(self):
        self.pen_show = not self.pen_show
        self.btn_toggle_pens.config(text="Show Penetrations" if not self.pen_show else "Hide Penetrations")
        self.display_all()

    def _show_pen_list(self):
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first."); return
        PenetrationListWindow(self.root, self.pen_store, on_change_callback=self.display_all)

    # ================================================================ Trajectory Planner
    def _plan_trajectory(self):
        """Compute trajectory from chamber origin to current cursor position and lock it in."""
        if not self.chamber_state['loaded']:
            messagebox.showerror("Error", "Load chamber first."); return
        if self.data is None:
            messagebox.showerror("Error", "Load a volume first."); return
        target = self.cursor_world.copy()
        self._update_traj_from_target(target)

    def _on_traj_stereo_enter(self):
        """User pressed Enter in a stereotaxic entry — set trajectory from target coords."""
        if not self.chamber_state['loaded']:
            self.traj_info_var.set("Load chamber first."); return
        try:
            ml = self.traj_ml_var.get()
            ap = self.traj_ap_var.get()
            dv = self.traj_dv_var.get()
        except (ValueError, tk.TclError):
            self.traj_info_var.set("Invalid stereotaxic coordinates."); return
        target = np.array([ml, ap, dv])
        if self.ebz_set:
            target = target + self.ebz_world
        self._update_traj_from_target(target)

    def _on_traj_chamber_enter(self):
        """User pressed Enter in a chamber entry — set trajectory from az/el/dist."""
        if not self.chamber_state['loaded']:
            self.traj_info_var.set("Load chamber first."); return
        try:
            az_deg = self.traj_az_var.get()
            el_deg = self.traj_el_var.get()
            dist = self.traj_dist_var.get()
        except (ValueError, tk.TclError):
            self.traj_info_var.set("Invalid chamber coordinates."); return
        self._update_traj_from_chamber(az_deg, el_deg, dist)

    def _update_traj_from_target(self, target):
        """Given a target point, compute chamber coords and lock in the trajectory."""
        if self._traj_updating:
            return
        self._traj_updating = True
        try:
            origin = self.chamber_state['origin']
            x_vec = self.chamber_state['x']
            y_vec = self.chamber_state['y']
            normal = self.chamber_state['normal']
            cor_offset = self.chamber_state['cor_offset']

            direction, az_deg, el_deg, distance, top_pt = calc_target_angles(
                target, origin, x_vec, y_vec, normal, cor_offset)

            # Update both entry rows
            self.traj_az_var.set(round(az_deg, 2))
            self.traj_el_var.set(round(el_deg, 2))
            self.traj_dist_var.set(round(distance, 2))
            if self.ebz_set:
                rel = target - self.ebz_world
                self.traj_ml_var.set(round(rel[0], 2))
                self.traj_ap_var.set(round(rel[1], 2))
                self.traj_dv_var.set(round(rel[2], 2))
                self.traj_stereo_label.config(text="(rel EBZ)")
            else:
                self.traj_ml_var.set(round(target[0], 2))
                self.traj_ap_var.set(round(target[1], 2))
                self.traj_dv_var.set(round(target[2], 2))
                self.traj_stereo_label.config(text="")

            self._lock_trajectory(az_deg, el_deg, distance, target, direction, top_pt)
        finally:
            self._traj_updating = False

    def _update_traj_from_chamber(self, az_deg, el_deg, dist):
        """Given chamber angles, compute target and lock in the trajectory."""
        if self._traj_updating:
            return
        self._traj_updating = True
        try:
            origin = self.chamber_state['origin']
            x_vec = self.chamber_state['x']
            y_vec = self.chamber_state['y']
            normal = self.chamber_state['normal']
            cor_offset = self.chamber_state['cor_offset']

            target, direction, top_pt = calc_penetration_target(
                origin, az_deg, el_deg, dist, x_vec, y_vec, normal, cor_offset)

            # Update stereo entries
            if self.ebz_set:
                rel = target - self.ebz_world
                self.traj_ml_var.set(round(rel[0], 2))
                self.traj_ap_var.set(round(rel[1], 2))
                self.traj_dv_var.set(round(rel[2], 2))
                self.traj_stereo_label.config(text="(rel EBZ)")
            else:
                self.traj_ml_var.set(round(target[0], 2))
                self.traj_ap_var.set(round(target[1], 2))
                self.traj_dv_var.set(round(target[2], 2))
                self.traj_stereo_label.config(text="")

            self.traj_az_var.set(round(az_deg, 2))
            self.traj_el_var.set(round(el_deg, 2))
            self.traj_dist_var.set(round(dist, 2))

            self._lock_trajectory(az_deg, el_deg, dist, target, direction, top_pt)
        finally:
            self._traj_updating = False

    def _lock_trajectory(self, az_deg, el_deg, dist, target, direction, top_pt):
        """Lock in the trajectory line. Enables point-adding controls."""
        self.temp_trajectory = {
            'az_deg': az_deg, 'el_deg': el_deg, 'dist_mm': dist,
            'target': target, 'direction': direction, 'top_pt': top_pt,
        }

        # Default the point dist to the trajectory dist
        self.traj_pt_dist_var.set(round(dist, 2))
        self._update_pt_info()

        # Info label
        if self.ebz_set:
            rel = target - self.ebz_world
            self.traj_info_var.set(
                f"Trajectory locked: Az={az_deg:.1f}°  El={el_deg:.1f}°  Dist={dist:.1f} mm    |    "
                f"Target: ML={rel[0]:+.2f}, AP={rel[1]:+.2f}, DV={rel[2]:+.2f} (rel EBZ)")
        else:
            self.traj_info_var.set(
                f"Trajectory locked: Az={az_deg:.1f}°  El={el_deg:.1f}°  Dist={dist:.1f} mm    |    "
                f"Target: ML={target[0]:.2f}, AP={target[1]:.2f}, DV={target[2]:.2f}")

        # Enable controls
        self.btn_clear_traj.config(state="normal")
        self.btn_add_point.config(state="normal")
        self.btn_save_traj.config(state="normal" if self.pen_store.connected else "disabled")
        self.btn_record_actual.config(state="normal" if self.pen_store.connected else "disabled")
        self.traj_actual_dist_var.set(round(dist, 2))

        if self.data is not None:
            self.display_all()

    def _on_pt_dist_enter(self):
        """User changed point dist — update the stereo readout for this depth."""
        self._update_pt_info()

    def _update_pt_info(self):
        """Show where the current point dist falls in stereotaxic coords."""
        if self.temp_trajectory is None:
            self.traj_pt_info_var.set("")
            return
        try:
            pt_dist = self.traj_pt_dist_var.get()
        except (ValueError, tk.TclError):
            return
        t = self.temp_trajectory
        origin = self.chamber_state['origin']
        cor_offset = self.chamber_state['cor_offset']
        el_rad = np.radians(t['el_deg'])
        origin_offset = cor_offset / np.cos(el_rad) if np.cos(el_rad) != 0 else 0.0
        pt = t['top_pt'] + pt_dist * t['direction'] if pt_dist > origin_offset else t['top_pt']
        # Actually compute properly: target at pt_dist along trajectory
        target_at_dist, _, _ = calc_penetration_target(
            origin, t['az_deg'], t['el_deg'], pt_dist,
            self.chamber_state['x'], self.chamber_state['y'],
            self.chamber_state['normal'], cor_offset)
        if self.ebz_set:
            rel = target_at_dist - self.ebz_world
            self.traj_pt_info_var.set(
                f"At {pt_dist:.1f}mm: ML={rel[0]:+.2f}, AP={rel[1]:+.2f}, DV={rel[2]:+.2f} (rel EBZ)")
        else:
            self.traj_pt_info_var.set(
                f"At {pt_dist:.1f}mm: ML={target_at_dist[0]:.2f}, AP={target_at_dist[1]:.2f}, DV={target_at_dist[2]:.2f}")

    def _add_temp_point(self):
        """Snapshot a point at the current Point Dist along the locked trajectory."""
        if self.temp_trajectory is None:
            messagebox.showerror("Error", "Set a trajectory first."); return
        try:
            pt_dist = self.traj_pt_dist_var.get()
        except (ValueError, tk.TclError):
            messagebox.showerror("Error", "Invalid point distance."); return

        t = self.temp_trajectory
        label = self.traj_label_var.get().strip()
        if not label:
            label = f"T{len(self.temp_points) + 1}"
        color = self.traj_color_var.get()
        notes = self.traj_notes_var.get().strip()

        # Compute the target at this dist along the same az/el
        origin = self.chamber_state['origin']
        cor_offset = self.chamber_state['cor_offset']
        target_at_dist, direction, top_pt = calc_penetration_target(
            origin, t['az_deg'], t['el_deg'], pt_dist,
            self.chamber_state['x'], self.chamber_state['y'],
            self.chamber_state['normal'], cor_offset)

        point = {
            'az_deg': t['az_deg'], 'el_deg': t['el_deg'], 'dist_mm': pt_dist,
            'label': label, 'color': color, 'notes': notes,
            'target': target_at_dist, 'direction': direction, 'top_pt': top_pt,
        }
        self.temp_points.append(point)

        self.traj_label_var.set(f"T{len(self.temp_points) + 1}")
        self.btn_remove_point.config(state="normal")
        self._update_temp_points_display()
        if self.data is not None:
            self.display_all()

    def _remove_last_temp_point(self):
        """Remove the most recently added temp point."""
        if self.temp_points:
            self.temp_points.pop()
        if not self.temp_points:
            self.btn_remove_point.config(state="disabled")
        self._update_temp_points_display()
        if self.data is not None:
            self.display_all()

    def _update_temp_points_display(self):
        """Update the summary label showing all temp points."""
        if not self.temp_points:
            self.traj_points_var.set("No points added yet")
            return
        parts = []
        for p in self.temp_points:
            parts.append(f"{p['label']}({p['color']}, D={p['dist_mm']:.1f})")
        self.traj_points_var.set(f"{len(self.temp_points)} point(s): " + "  |  ".join(parts))

    def _record_actual_point(self):
        """Record an actual experimental point: saves immediately to DB with channel correction."""
        if self.temp_trajectory is None:
            messagebox.showerror("Error", "Set a trajectory first."); return
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first."); return

        session_id = self.session_id_var.get().strip()
        if not session_id:
            messagebox.showerror("Error", "Enter a Session ID at the top of the window."); return

        try:
            tip_dist = self.traj_actual_dist_var.get()
        except (ValueError, tk.TclError):
            messagebox.showerror("Error", "Invalid tip distance."); return

        try:
            channel_num = int(self.traj_channel_var.get())
            if channel_num not in _CHANNEL_ORDER:
                messagebox.showerror("Error", f"Channel {channel_num} not in channel order."); return
        except (ValueError, tk.TclError):
            messagebox.showerror("Error", "Select a valid channel number."); return

        t = self.temp_trajectory
        label = self.traj_actual_label_var.get().strip() or session_id
        notes = self.traj_actual_notes_var.get().strip()

        # Apply channel correction
        corrected_dist = _channel_corrected_dist(tip_dist, channel_num)

        # Compute target at the corrected dist
        origin = self.chamber_state['origin']
        cor_offset = self.chamber_state['cor_offset']
        target_at_dist, _, _ = calc_penetration_target(
            origin, t['az_deg'], t['el_deg'], corrected_dist,
            self.chamber_state['x'], self.chamber_state['y'],
            self.chamber_state['normal'], cor_offset)

        # Build notes
        notes_extra = f"ch{channel_num} tip={tip_dist:.2f}mm corrected={corrected_dist:.2f}mm"
        if self.ebz_set:
            rel = target_at_dist - self.ebz_world
            coord_note = f"target=[{rel[0]:+.2f}, {rel[1]:+.2f}, {rel[2]:+.2f}] rel EBZ"
        else:
            coord_note = f"target=[{target_at_dist[0]:.2f}, {target_at_dist[1]:.2f}, {target_at_dist[2]:.2f}]"
        full_notes = "  ".join(part for part in [notes, notes_extra, coord_note] if part)

        color = COLORS[len(self.pen_store.penetrations) % len(COLORS)]
        pen_id = self.pen_store.add(
            t['az_deg'], t['el_deg'], corrected_dist,
            label=label, session_id=session_id, pen_type="actual",
            color=color, notes=full_notes)

        self.traj_actual_info_var.set(
            f"Saved actual id={pen_id}: ch{channel_num}, tip={tip_dist:.1f}→{corrected_dist:.1f}mm")
        self.display_all()

    def _save_trajectory(self):
        """Save all planned temp points to the DB. If no points, save the trajectory tip."""
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first."); return

        session_id = self.session_id_var.get().strip()
        if not session_id:
            messagebox.showerror("Error", "Enter a Session ID at the top of the window."); return

        to_save = list(self.temp_points)

        # If no points were explicitly added, save the trajectory tip itself
        if not to_save and self.temp_trajectory is not None:
            t = self.temp_trajectory
            label = self.traj_label_var.get().strip() or "P1"
            color = self.traj_color_var.get()
            notes = self.traj_notes_var.get().strip()
            to_save.append({
                'az_deg': t['az_deg'], 'el_deg': t['el_deg'], 'dist_mm': t['dist_mm'],
                'label': label, 'color': color, 'notes': notes, 'target': t['target'].copy(),
            })

        if not to_save:
            messagebox.showerror("Error", "Nothing to save."); return

        n_saved = 0
        for p in to_save:
            dist = p['dist_mm']
            notes = p.get('notes', '')

            target = p['target']
            if self.ebz_set:
                rel = target - self.ebz_world
                coord_note = f"target=[{rel[0]:+.2f}, {rel[1]:+.2f}, {rel[2]:+.2f}] rel EBZ"
            else:
                coord_note = f"target=[{target[0]:.2f}, {target[1]:.2f}, {target[2]:.2f}]"

            full_notes = "  ".join(part for part in [notes, coord_note] if part)
            self.pen_store.add(float(p['az_deg']), float(p['el_deg']), float(dist),
                               label=p['label'], session_id=session_id,
                               pen_type="planned", color=p['color'], notes=full_notes)
            n_saved += 1

        # Also save the trajectory tip position as planned_tip
        if self.temp_trajectory is not None:
            t = self.temp_trajectory
            tip_target = t['target']
            if self.ebz_set:
                rel = tip_target - self.ebz_world
                tip_coord = f"target=[{rel[0]:+.2f}, {rel[1]:+.2f}, {rel[2]:+.2f}] rel EBZ"
            else:
                tip_coord = f"target=[{tip_target[0]:.2f}, {tip_target[1]:.2f}, {tip_target[2]:.2f}]"
            self.pen_store.add(
                t['az_deg'], t['el_deg'], t['dist_mm'],
                label="tip", session_id=session_id,
                pen_type="planned_tip", color="white", notes=tip_coord)
            n_saved += 1

        self.traj_info_var.set(f"Saved {n_saved} planned point{'s' if n_saved != 1 else ''} to DB.")
        self.display_all()

    def _load_session(self):
        """Load all penetrations for the current session_id and display them as temp trajectory + points."""
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first."); return
        if not self.chamber_state['loaded']:
            messagebox.showerror("Error", "Load chamber first."); return

        session_id = self.session_id_var.get().strip()
        if not session_id:
            messagebox.showerror("Error", "Enter a Session ID."); return

        self.pen_store.refresh()
        session_pens = [p for p in self.pen_store.penetrations if p['session_id'] == session_id]
        if not session_pens:
            messagebox.showinfo("Info", f"No penetrations found for session '{session_id}'.")
            return

        origin = self.chamber_state['origin']
        x_vec = self.chamber_state['x']
        y_vec = self.chamber_state['y']
        normal = self.chamber_state['normal']
        cor_offset = self.chamber_state['cor_offset']

        # Find the planned_tip entry to set the trajectory line
        tip_entry = None
        for p in session_pens:
            if p['pen_type'] == 'planned_tip':
                tip_entry = p
                break

        # If no planned_tip, use the first entry's az/el to define the line
        if tip_entry is None:
            tip_entry = session_pens[0]

        az, el, dist = tip_entry['az_deg'], tip_entry['el_deg'], tip_entry['dist_mm']
        target, direction, top_pt = calc_penetration_target(
            origin, az, el, dist, x_vec, y_vec, normal, cor_offset)

        # Lock this as the trajectory
        self._traj_updating = True
        try:
            self.traj_az_var.set(round(az, 2))
            self.traj_el_var.set(round(el, 2))
            self.traj_dist_var.set(round(dist, 2))
            if self.ebz_set:
                rel = target - self.ebz_world
                self.traj_ml_var.set(round(rel[0], 2))
                self.traj_ap_var.set(round(rel[1], 2))
                self.traj_dv_var.set(round(rel[2], 2))
                self.traj_stereo_label.config(text="(rel EBZ)")
            else:
                self.traj_ml_var.set(round(target[0], 2))
                self.traj_ap_var.set(round(target[1], 2))
                self.traj_dv_var.set(round(target[2], 2))
                self.traj_stereo_label.config(text="")
        finally:
            self._traj_updating = False

        self.temp_trajectory = {
            'az_deg': az, 'el_deg': el, 'dist_mm': dist,
            'target': target, 'direction': direction, 'top_pt': top_pt,
        }
        self.traj_pt_dist_var.set(round(dist, 2))

        # Load all non-tip entries as temp points
        self.temp_points.clear()
        for p in session_pens:
            if p['pen_type'] == 'planned_tip':
                continue
            pt_target, pt_dir, pt_top = calc_penetration_target(
                origin, p['az_deg'], p['el_deg'], p['dist_mm'],
                x_vec, y_vec, normal, cor_offset)
            self.temp_points.append({
                'az_deg': p['az_deg'], 'el_deg': p['el_deg'], 'dist_mm': p['dist_mm'],
                'label': p['label'], 'color': p['color'], 'notes': p.get('notes', ''),
                'target': pt_target, 'direction': pt_dir, 'top_pt': pt_top,
            })

        n_planned = sum(1 for p in session_pens if p['pen_type'] == 'planned')
        n_actual = sum(1 for p in session_pens if p['pen_type'] == 'actual')
        self.traj_info_var.set(
            f"Loaded session '{session_id}': {n_planned} planned, {n_actual} actual, "
            f"Az={az:.1f}° El={el:.1f}° Dist={dist:.1f}mm")
        self._update_pt_info()
        self._update_temp_points_display()

        # Enable all controls
        self.btn_clear_traj.config(state="normal")
        self.btn_add_point.config(state="normal")
        self.btn_save_traj.config(state="normal")
        self.btn_record_actual.config(state="normal")
        if self.temp_points:
            self.btn_remove_point.config(state="normal")

        if self.data is not None:
            self.display_all()

    def _clear_trajectory(self):
        """Remove the trajectory and all temp points."""
        self.temp_trajectory = None
        self.temp_points.clear()
        self.traj_info_var.set("No trajectory set")
        self.traj_pt_info_var.set("")
        self.traj_actual_info_var.set("")
        self._update_temp_points_display()
        self.traj_ml_var.set(0.0); self.traj_ap_var.set(0.0); self.traj_dv_var.set(0.0)
        self.traj_az_var.set(0.0); self.traj_el_var.set(0.0); self.traj_dist_var.set(35.0)
        self.traj_pt_dist_var.set(35.0)
        self.btn_save_traj.config(state="disabled")
        self.btn_clear_traj.config(state="disabled")
        self.btn_remove_point.config(state="disabled")
        self.btn_add_point.config(state="disabled")
        self.btn_record_actual.config(state="disabled")
        if self.data is not None:
            self.display_all()

    # ================================================================ Correction matrix

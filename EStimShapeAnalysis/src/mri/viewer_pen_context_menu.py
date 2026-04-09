"""
Right-click context menu for penetration dots in the MRI viewer.

When the user right-clicks near a penetration target dot in any of the
three MRI views, a Tkinter context menu appears with:

  • Go To          — move the crosshair to this penetration's target
  • Hide / Show    — toggle per-penetration visibility
  • Color ▶        — submenu with all available colors
  • Rename…        — inline rename dialog
  • Notes…         — edit the notes string
  • Delete…        — remove from DB (with confirmation)

Wiring
------
1. Add PenetrationContextMenuMixin to TriplanarMRIViewer's base classes.
2. In viewer_display.py _on_click(), add the hook call described below;
   the mixin's _try_pen_context_menu() returns True when it handled the
   event so the caller can bail out early.

Hook call to add in _on_click() (after EBZ-pick block, before atlas block):

    if event.button == 3 and hasattr(self, '_try_pen_context_menu'):
        if self._try_pen_context_menu(event, vi, x_world, y_world):
            return

Dependencies (provided by TriplanarMRIViewer at run-time):
    self.pen_store         — PenetrationStore
    self.pen_show          — bool: global penetrations-visible flag
    self.chamber_state     — dict with chamber geometry
    self.ebz_world / self.ebz_set
    self.cursor_world      — writable 3-element world position
    self.axes              — list of 3 matplotlib Axes
    self.canvas            — FigureCanvasTkAgg
    self.root              — Tk root window
    self.SLICE_CFG         — [(fix_wax, h_wax, v_wax), …]
    self.display_all()
"""

import numpy as np
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from src.mri.chamber import calc_penetration_target
from src.mri.penetrations import COLORS

# How many screen pixels away from a dot counts as a "hit"
_HIT_PIXELS = 10


class PenetrationContextMenuMixin:
    """
    Adds right-click context menus on penetration target dots.

    Call _try_pen_context_menu() from _on_click() to use it.
    """

    # ------------------------------------------------------------------
    # Hit testing
    # ------------------------------------------------------------------

    def _try_pen_context_menu(self, event, vi, x_world, y_world):
        """
        Test whether the right-click lands near a penetration dot.

        Returns True (and shows the menu) if a penetration was hit,
        so the caller can return immediately and skip other right-click
        handlers.
        """
        if not self.pen_show:
            return False
        if not (self.pen_store.connected and self.chamber_state['loaded']):
            return False
        if event.xdata is None or event.ydata is None:
            return False

        _, h_wax, v_wax = self.SLICE_CFG[vi]
        disp_off = self.ebz_world if self.ebz_set else np.zeros(3)

        # Compute a hit threshold in *data* (mm) units from the pixel tolerance.
        # This scales correctly as the user zooms in or out.
        ax = self.axes[vi]
        try:
            p0 = ax.transData.inverted().transform((0, 0))
            p1 = ax.transData.inverted().transform((_HIT_PIXELS, 0))
            threshold_mm = abs(p1[0] - p0[0])
        except Exception:
            threshold_mm = 3.0  # fallback

        origin = self.chamber_state['origin']
        x_vec  = self.chamber_state['x']
        y_vec  = self.chamber_state['y']
        normal = self.chamber_state['normal']
        cor_off = self.chamber_state['cor_offset']

        click_h = event.xdata  # already in display (mm) coords
        click_v = event.ydata

        best_pen  = None
        best_dist = float('inf')

        for pen in self.pen_store.penetrations:
            if not pen.get('visible', True):
                continue  # hidden dot — skip
            target, _, _ = calc_penetration_target(
                origin, pen['az_deg'], pen['el_deg'], pen['dist_mm'],
                x_vec, y_vec, normal, cor_off)
            th = target[h_wax] - disp_off[h_wax]
            tv = target[v_wax] - disp_off[v_wax]
            dist = ((click_h - th) ** 2 + (click_v - tv) ** 2) ** 0.5
            if dist < threshold_mm and dist < best_dist:
                best_dist = dist
                best_pen  = pen

        if best_pen is None:
            return False

        self._show_pen_context_menu(event, best_pen)
        return True

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _show_pen_context_menu(self, event, pen):
        """Build and display the right-click context menu for *pen*."""
        menu = tk.Menu(self.root, tearoff=0)

        # Non-interactive header
        sid = pen.get('session_id', '') or ''
        header = (f"#{pen['id']}  \"{pen['label']}\"  "
                  f"[{pen['pen_type']}]  {pen['color']}"
                  + (f"  sess={sid}" if sid else ""))
        menu.add_command(label=header, state="disabled",
                         font=("TkDefaultFont", 9, "bold"))
        menu.add_separator()

        menu.add_command(
            label="Go To  (move crosshair to target)",
            command=lambda: self._pen_goto(pen))
        menu.add_separator()

        vis_label = "Show" if not pen['visible'] else "Hide"
        menu.add_command(label=vis_label,
                         command=lambda: self._pen_toggle_vis(pen))

        line_label = "Show Line" if not pen.get('line_visible', True) else "Hide Line"
        menu.add_command(label=line_label,
                         command=lambda: self._pen_toggle_line_vis(pen))

        # Color submenu
        color_menu = tk.Menu(menu, tearoff=0)
        for color in COLORS:
            marker = "✓ " if color == pen['color'] else "   "
            color_menu.add_command(
                label=f"{marker}{color}",
                command=lambda c=color: self._pen_set_color(pen, c))
        menu.add_cascade(label="Color", menu=color_menu)

        menu.add_command(label="Rename…",
                         command=lambda: self._pen_rename(pen))
        menu.add_command(label="Edit Notes…",
                         command=lambda: self._pen_edit_notes(pen))
        menu.add_separator()
        menu.add_command(label="Delete…",
                         command=lambda: self._pen_delete(pen))

        # Convert matplotlib pixel coords → screen coords for the popup
        try:
            widget = self.canvas.get_tk_widget()
            x_root = widget.winfo_rootx() + int(event.x)
            y_root = widget.winfo_rooty() + int(widget.winfo_height() - event.y)
            menu.tk_popup(x_root, y_root)
        finally:
            menu.grab_release()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _pen_goto(self, pen):
        """Move the crosshair to this penetration's target."""
        origin  = self.chamber_state['origin']
        x_vec   = self.chamber_state['x']
        y_vec   = self.chamber_state['y']
        normal  = self.chamber_state['normal']
        cor_off = self.chamber_state['cor_offset']
        target, _, _ = calc_penetration_target(
            origin, pen['az_deg'], pen['el_deg'], pen['dist_mm'],
            x_vec, y_vec, normal, cor_off)
        self.cursor_world = target.copy()
        self.display_all()

    def _pen_toggle_vis(self, pen):
        self.pen_store.toggle_visible(pen['id'])
        self.display_all()

    def _pen_toggle_line_vis(self, pen):
        new_val = 0 if pen.get('line_visible', True) else 1
        self.pen_store.update(pen['id'], line_visible=new_val)
        self.display_all()

    def _pen_set_color(self, pen, color):
        self.pen_store.update(pen['id'], color=color)
        self.display_all()

    def _pen_rename(self, pen):
        """Open a small dialog to rename the penetration."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Rename Penetration")
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(dlg, text=f"Rename  #{pen['id']}:").pack(
            padx=12, pady=(10, 4))
        var = tk.StringVar(value=pen['label'])
        entry = ttk.Entry(dlg, textvariable=var, width=24)
        entry.pack(padx=12, pady=4)
        entry.select_range(0, tk.END)
        entry.focus_set()

        def _apply(event=None):
            new = var.get().strip()
            if new:
                self.pen_store.update(pen['id'], label=new)
                self.display_all()
            dlg.destroy()

        entry.bind("<Return>", _apply)
        entry.bind("<Escape>", lambda e: dlg.destroy())
        btn_row = ttk.Frame(dlg)
        btn_row.pack(pady=(4, 10))
        ttk.Button(btn_row, text="OK", command=_apply).pack(
            side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Cancel",
                   command=dlg.destroy).pack(side=tk.LEFT, padx=4)

    def _pen_edit_notes(self, pen):
        """Open a dialog to edit the penetration's notes."""
        dlg = tk.Toplevel(self.root)
        dlg.title("Edit Notes")
        dlg.resizable(True, False)
        dlg.transient(self.root)
        dlg.grab_set()

        ttk.Label(dlg, text=f"Notes for  #{pen['id']}  \"{pen['label']}\":").pack(
            padx=12, pady=(10, 4), anchor="w")
        var = tk.StringVar(value=pen.get('notes', ''))
        entry = ttk.Entry(dlg, textvariable=var, width=50)
        entry.pack(padx=12, pady=4, fill=tk.X, expand=True)
        entry.focus_set()

        def _apply(event=None):
            self.pen_store.update(pen['id'], notes=var.get())
            dlg.destroy()

        entry.bind("<Return>", _apply)
        entry.bind("<Escape>", lambda e: dlg.destroy())
        btn_row = ttk.Frame(dlg)
        btn_row.pack(pady=(4, 10))
        ttk.Button(btn_row, text="OK", command=_apply).pack(
            side=tk.LEFT, padx=4)
        ttk.Button(btn_row, text="Cancel",
                   command=dlg.destroy).pack(side=tk.LEFT, padx=4)

    def _pen_delete(self, pen):
        if messagebox.askyesno(
                "Delete Penetration",
                f"Delete penetration #{pen['id']} \"{pen['label']}\"?\n"
                f"This cannot be undone.",
                parent=self.root):
            self.pen_store.delete(pen['id'])
            self.display_all()

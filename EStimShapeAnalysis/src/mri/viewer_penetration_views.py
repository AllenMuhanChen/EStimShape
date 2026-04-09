"""
Penetration visibility preset management for the MRI viewer.

Provides three operations available from the Chamber panel:

  Save        — quick-save to the currently open file (disabled until a file
                is open or has been saved-as once)
  Save As     — always prompts for a new filename, then saves
  Open        — opens a saved preset and applies it (show matching IDs, hide rest)
  Isolate Session — show only planned/actual penetrations for the active session_id

These follow the same "open / save / save-as" idiom as word processors.

Dependencies (provided by TriplanarMRIViewer):
    self.pen_store            — PenetrationStore instance
    self.session_id_var       — tk.StringVar for the session ID entry
    self.status_var           — tk.StringVar for the status bar
    self.btn_save_pen_view    — quick-Save button (enabled after Open/Save As)
    self._pen_view_name_var   — tk.StringVar label showing current filename
    self.display_all()        — redraws all views
"""

import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox

_VIEW_FILETYPES = [("Penetration View", "*.json"), ("All files", "*.*")]


class PenetrationViewsMixin:
    """
    Save/load named visibility presets and isolate a single session's
    penetrations with one click.
    """

    # _pen_view_path — set to the current open file path once a file is
    # opened or saved-as.  None means no file is associated yet.
    _pen_view_path = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_view_to(self, path):
        """Write visible IDs to *path* and update UI state."""
        visible_ids = self.pen_store.get_visible_ids()
        with open(path, "w") as fh:
            json.dump({"visible_ids": visible_ids}, fh, indent=2)
        self._pen_view_path = path
        name = os.path.basename(path)
        self._pen_view_name_var.set(name)
        self.btn_save_pen_view.config(state="normal")
        self.status_var.set(
            f"Saved view: {len(visible_ids)} visible penetration(s) → {name}")

    # ------------------------------------------------------------------
    # Save / Save As / Open
    # ------------------------------------------------------------------

    def _save_pen_view(self):
        """
        Quick save — write to the currently open file.

        Falls through to Save As if no file is currently associated
        (this mirrors the behaviour of most desktop applications).
        """
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first.")
            return
        if self._pen_view_path is None:
            self._save_pen_view_as()
            return
        self._write_view_to(self._pen_view_path)

    def _save_pen_view_as(self):
        """Save As — always prompt for a filename, then save."""
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save Penetration View As",
            defaultextension=".json",
            filetypes=_VIEW_FILETYPES,
        )
        if not path:
            return
        self._write_view_to(path)

    def _open_pen_view(self):
        """Open a saved view preset and apply it (show matching IDs, hide rest)."""
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first.")
            return
        path = filedialog.askopenfilename(
            title="Open Penetration View",
            filetypes=_VIEW_FILETYPES,
        )
        if not path:
            return
        try:
            ids = _read_view_file(path)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not read view file:\n{exc}")
            return
        self.pen_store.set_visible_by_ids(ids)
        self._pen_view_path = path
        name = os.path.basename(path)
        self._pen_view_name_var.set(name)
        self.btn_save_pen_view.config(state="normal")
        n = len(self.pen_store.get_visible_ids())
        self.status_var.set(f"Opened view '{name}': {n} penetration(s) now visible")
        self.display_all()

    # ------------------------------------------------------------------
    # Session isolation
    # ------------------------------------------------------------------

    def _isolate_session_pens(self):
        """
        Show only planned and actual penetrations for the current session_id.

        All other penetrations (including other sessions and planning-only
        records) are hidden.  Use Save beforehand to preserve the current
        selection, and Open to restore it.
        """
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first.")
            return
        session_id = self.session_id_var.get().strip()
        if not session_id:
            messagebox.showerror(
                "Error", "Enter a Session ID at the top of the window first.")
            return
        target_ids = [
            p['id'] for p in self.pen_store.penetrations
            if p['session_id'] == session_id
            and p['pen_type'] in ('planned', 'actual')
        ]
        self.pen_store.set_visible_by_ids(target_ids)
        self.status_var.set(
            f"Session '{session_id}': {len(target_ids)} penetration(s) shown, "
            f"all others hidden")
        self.display_all()


# ------------------------------------------------------------------
# Shared file I/O helper (used by PenetrationListWindow too)
# ------------------------------------------------------------------

def _read_view_file(path):
    """Parse a view preset JSON file and return a list of int IDs."""
    with open(path) as fh:
        data = json.load(fh)
    if isinstance(data, list):
        ids = data
    else:
        ids = data.get("visible_ids", [])
    return [int(i) for i in ids]

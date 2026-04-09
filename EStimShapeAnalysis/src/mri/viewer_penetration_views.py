"""
Penetration visibility preset management for the MRI viewer.

Provides three operations available from the Chamber panel:

  Save View    — writes the IDs of currently visible penetrations to a JSON file
  Load View    — reads such a file and applies it (show matching IDs, hide rest)
  Isolate Session — show only planned/actual penetrations for the active session_id

These functions are also wired into PenetrationListWindow (penetrations.py) so
the user can use them from the list window as well as from the main panel.

Dependencies (provided by TriplanarMRIViewer):
    self.pen_store        — PenetrationStore instance
    self.session_id_var   — tk.StringVar for the session ID entry
    self.status_var       — tk.StringVar for the status bar
    self.display_all()    — redraws all views
"""

import json
import tkinter as tk
from tkinter import filedialog, messagebox

_VIEW_FILETYPES = [("Penetration View", "*.json"), ("All files", "*.*")]


class PenetrationViewsMixin:
    """
    Save/load named visibility presets and isolate a single session's
    penetrations with one click.
    """

    # ------------------------------------------------------------------
    # Save / Load view presets
    # ------------------------------------------------------------------

    def _save_pen_view(self):
        """Save the IDs of all currently visible penetrations to a JSON file."""
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first.")
            return
        visible_ids = self.pen_store.get_visible_ids()
        path = filedialog.asksaveasfilename(
            title="Save Penetration View",
            defaultextension=".json",
            filetypes=_VIEW_FILETYPES,
        )
        if not path:
            return
        with open(path, "w") as fh:
            json.dump({"visible_ids": visible_ids}, fh, indent=2)
        self.status_var.set(
            f"Saved view: {len(visible_ids)} visible penetration(s) → {path}")

    def _load_pen_view(self):
        """Load a saved view preset and apply it (show matching IDs, hide rest)."""
        if not self.pen_store.connected:
            messagebox.showerror("Error", "Connect to DB first.")
            return
        path = filedialog.askopenfilename(
            title="Load Penetration View",
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
        n = len(self.pen_store.get_visible_ids())
        self.status_var.set(f"Loaded view: {n} penetration(s) now visible")
        self.display_all()

    # ------------------------------------------------------------------
    # Session isolation
    # ------------------------------------------------------------------

    def _isolate_session_pens(self):
        """
        Show only planned and actual penetrations for the current session_id.

        All other penetrations (including other sessions and planning-only
        records) are hidden.  Use Save View beforehand to preserve the
        current selection, and Load View to restore it.
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

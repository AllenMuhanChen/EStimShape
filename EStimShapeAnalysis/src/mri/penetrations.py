"""
Database-backed penetration management.

Table schema:
    CREATE TABLE IF NOT EXISTS Penetrations (
        id         INT AUTO_INCREMENT PRIMARY KEY,
        tstamp     BIGINT,
        label      VARCHAR(64),
        az_deg     DOUBLE,
        el_deg     DOUBLE,
        dist_mm    DOUBLE,
        color      VARCHAR(32) DEFAULT 'cyan',
        visible    TINYINT DEFAULT 1,
        notes      TEXT
    );

Uses the Connection class from clat for DB access.
"""

import time
import tkinter as tk
from tkinter import ttk, messagebox

COLORS = ['cyan', 'yellow', 'magenta', 'orange', 'lime', 'deepskyblue',
          'red', 'white', 'pink', 'gold']

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS Penetrations (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    tstamp     BIGINT,
    label      VARCHAR(64),
    az_deg     DOUBLE,
    el_deg     DOUBLE,
    dist_mm    DOUBLE,
    color      VARCHAR(32) DEFAULT 'cyan',
    visible    TINYINT DEFAULT 1,
    notes      TEXT
)
"""


class PenetrationStore:
    """Manages penetrations via a MySQL table."""

    def __init__(self, host="172.30.6.61", database="allen_data_repository",
                 user="xper_rw", password="up2nite"):
        self.conn = None
        self._host = host
        self._database = database
        self._user = user
        self._password = password
        self._cache = []  # local cache of rows

    def connect(self):
        """Establish DB connection and ensure table exists."""
        from clat.util.connection import Connection
        self.conn = Connection(
            database=self._database,
            user=self._user,
            password=self._password,
            host=self._host,
        )
        self.conn.execute(CREATE_TABLE_SQL)
        self.refresh()

    @property
    def connected(self):
        return self.conn is not None

    def refresh(self):
        """Reload all penetrations from DB."""
        if not self.connected:
            return
        self.conn.execute("SELECT id, tstamp, label, az_deg, el_deg, dist_mm, color, visible, notes "
                          "FROM Penetrations ORDER BY id")
        rows = self.conn.fetch_all()
        self._cache = []
        for row in rows:
            self._cache.append({
                'id': row[0],
                'tstamp': row[1],
                'label': row[2],
                'az_deg': row[3],
                'el_deg': row[4],
                'dist_mm': row[5],
                'color': row[6] or 'cyan',
                'visible': bool(row[7]),
                'notes': row[8] or '',
            })

    @property
    def penetrations(self):
        return self._cache

    def add(self, az_deg, el_deg, dist_mm, label="", color="cyan", notes=""):
        """Insert a new penetration and return its id."""
        if not self.connected:
            raise RuntimeError("Not connected to DB")
        tstamp = int(time.time() * 1000)
        if not label:
            label = f"P{len(self._cache) + 1}"
        self.conn.execute(
            "INSERT INTO Penetrations (tstamp, label, az_deg, el_deg, dist_mm, color, visible, notes) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (tstamp, label, az_deg, el_deg, dist_mm, color, 1, notes))
        self.refresh()
        return self._cache[-1]['id']

    def update(self, pen_id, **kwargs):
        """Update fields of an existing penetration."""
        if not self.connected:
            return
        allowed = {'label', 'az_deg', 'el_deg', 'dist_mm', 'color', 'visible', 'notes'}
        sets = []
        vals = []
        for k, v in kwargs.items():
            if k in allowed:
                sets.append(f"{k} = %s")
                vals.append(v)
        if not sets:
            return
        vals.append(pen_id)
        self.conn.execute(f"UPDATE Penetrations SET {', '.join(sets)} WHERE id = %s", tuple(vals))
        self.refresh()

    def delete(self, pen_id):
        """Delete a penetration by id."""
        if not self.connected:
            return
        self.conn.execute("DELETE FROM Penetrations WHERE id = %s", (pen_id,))
        self.refresh()

    def toggle_visible(self, pen_id):
        """Toggle the visible flag."""
        pen = next((p for p in self._cache if p['id'] == pen_id), None)
        if pen:
            self.update(pen_id, visible=0 if pen['visible'] else 1)


class PenetrationListWindow:
    """A Toplevel window for viewing, editing, and deleting penetrations."""

    def __init__(self, parent, store: PenetrationStore, on_change_callback=None):
        self.store = store
        self.on_change = on_change_callback

        self.win = tk.Toplevel(parent)
        self.win.title("Penetrations")
        self.win.geometry("750x450")

        # Treeview
        cols = ("id", "label", "az", "el", "dist", "color", "visible", "notes")
        self.tree = ttk.Treeview(self.win, columns=cols, show="headings", height=15)
        for c, w in zip(cols, (40, 80, 60, 60, 60, 70, 50, 250)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, stretch=(c == "notes"))
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        sb = ttk.Scrollbar(self.win, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        # Buttons
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="Toggle Visible", command=self._toggle_vis).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Edit Selected", command=self._edit).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Delete Selected", command=self._delete).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Refresh", command=self._refresh_tree).pack(side=tk.LEFT, padx=3)

        self._refresh_tree()

    def _refresh_tree(self):
        self.store.refresh()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in self.store.penetrations:
            vis = "✓" if p['visible'] else "✗"
            self.tree.insert("", tk.END, iid=str(p['id']),
                             values=(p['id'], p['label'], f"{p['az_deg']:.1f}",
                                     f"{p['el_deg']:.1f}", f"{p['dist_mm']:.1f}",
                                     p['color'], vis, p['notes']))

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select a penetration first.")
            return None
        return int(sel[0])

    def _toggle_vis(self):
        pid = self._selected_id()
        if pid is None:
            return
        self.store.toggle_visible(pid)
        self._refresh_tree()
        if self.on_change:
            self.on_change()

    def _delete(self):
        pid = self._selected_id()
        if pid is None:
            return
        if messagebox.askyesno("Confirm", f"Delete penetration {pid}?"):
            self.store.delete(pid)
            self._refresh_tree()
            if self.on_change:
                self.on_change()

    def _edit(self):
        pid = self._selected_id()
        if pid is None:
            return
        pen = next((p for p in self.store.penetrations if p['id'] == pid), None)
        if not pen:
            return

        edit_win = tk.Toplevel(self.win)
        edit_win.title(f"Edit Penetration {pid}")
        edit_win.geometry("400x300")

        fields = {}
        for i, (key, label) in enumerate([
            ('label', 'Label'), ('az_deg', 'Az (deg)'), ('el_deg', 'El (deg)'),
            ('dist_mm', 'Dist (mm)'), ('color', 'Color'), ('notes', 'Notes'),
        ]):
            ttk.Label(edit_win, text=f"{label}:").grid(row=i, column=0, padx=5, pady=3, sticky="w")
            var = tk.StringVar(value=str(pen.get(key, '')))
            ttk.Entry(edit_win, textvariable=var, width=30).grid(row=i, column=1, padx=5, pady=3)
            fields[key] = var

        def save():
            updates = {}
            for key, var in fields.items():
                val = var.get()
                if key in ('az_deg', 'el_deg', 'dist_mm'):
                    try:
                        val = float(val)
                    except ValueError:
                        messagebox.showerror("Error", f"Invalid number for {key}")
                        return
                updates[key] = val
            self.store.update(pid, **updates)
            self._refresh_tree()
            if self.on_change:
                self.on_change()
            edit_win.destroy()

        ttk.Button(edit_win, text="Save", command=save).grid(row=len(fields), column=0,
                                                              columnspan=2, pady=10)

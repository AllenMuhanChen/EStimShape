"""
Database-backed penetration management.

Table schema (v2):
    CREATE TABLE IF NOT EXISTS Penetrations (
        id         INT AUTO_INCREMENT PRIMARY KEY,
        tstamp     BIGINT,
        session_id VARCHAR(64),
        label      VARCHAR(64),
        az_deg     DOUBLE,
        el_deg     DOUBLE,
        dist_mm    DOUBLE,
        pen_type   VARCHAR(16) DEFAULT 'planned',
        color      VARCHAR(32) DEFAULT 'cyan',
        visible    TINYINT DEFAULT 1,
        notes      TEXT
    );

pen_type: 'planned' (pre-experiment) or 'actual' (recorded during experiment)

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
    session_id VARCHAR(64),
    label      VARCHAR(64),
    az_deg     DOUBLE,
    el_deg     DOUBLE,
    dist_mm    DOUBLE,
    pen_type   VARCHAR(16) DEFAULT 'planned',
    color      VARCHAR(32) DEFAULT 'cyan',
    visible    TINYINT DEFAULT 1,
    notes      TEXT
)
"""

# Migration queries: add new columns to existing tables that lack them
_MIGRATE_SQLS = [
    "ALTER TABLE Penetrations ADD COLUMN session_id VARCHAR(64) AFTER tstamp",
    "ALTER TABLE Penetrations ADD COLUMN pen_type VARCHAR(16) DEFAULT 'planned' AFTER dist_mm",
    # Backfill: copy label -> session_id for existing rows that have no session_id yet
    "UPDATE Penetrations SET session_id = label WHERE session_id IS NULL",
]


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
        """Establish DB connection, ensure table exists, and migrate if needed."""
        from clat.util.connection import Connection
        self.conn = Connection(
            database=self._database,
            user=self._user,
            password=self._password,
            host=self._host,
        )
        self.conn.execute(CREATE_TABLE_SQL)
        self._migrate()
        self.refresh()

    def _migrate(self):
        """Apply schema migrations (safe to re-run: ignores 'duplicate column' errors)."""
        for sql in _MIGRATE_SQLS:
            try:
                self.conn.execute(sql)
            except Exception as e:
                err = str(e).lower()
                if 'duplicate column' in err or 'duplicate' in err:
                    pass  # column already exists - skip
                else:
                    print(f"Migration warning: {e}")

    @property
    def connected(self):
        return self.conn is not None

    def refresh(self):
        """Reload all penetrations from DB."""
        if not self.connected:
            return
        self.conn.execute(
            "SELECT id, tstamp, session_id, label, az_deg, el_deg, dist_mm, "
            "pen_type, color, visible, notes FROM Penetrations ORDER BY id")
        rows = self.conn.fetch_all()
        self._cache = []
        for row in rows:
            self._cache.append({
                'id': row[0],
                'tstamp': row[1],
                'session_id': row[2] or '',
                'label': row[3] or '',
                'az_deg': row[4],
                'el_deg': row[5],
                'dist_mm': row[6],
                'pen_type': row[7] or 'planned',
                'color': row[8] or 'cyan',
                'visible': bool(row[9]),
                'notes': row[10] or '',
            })

    @property
    def penetrations(self):
        return self._cache

    def add(self, az_deg, el_deg, dist_mm, label="", session_id="",
            pen_type="planned", color="cyan", notes=""):
        """Insert a new penetration and return its id."""
        if not self.connected:
            raise RuntimeError("Not connected to DB")
        tstamp = int(time.time() * 1000)
        if not label:
            label = f"P{len(self._cache) + 1}"
        self.conn.execute(
            "INSERT INTO Penetrations "
            "(tstamp, session_id, label, az_deg, el_deg, dist_mm, pen_type, color, visible, notes) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (tstamp, session_id, label, az_deg, el_deg, dist_mm, pen_type, color, 1, notes))
        self.refresh()
        return self._cache[-1]['id']

    def update(self, pen_id, **kwargs):
        """Update fields of an existing penetration."""
        if not self.connected:
            return
        allowed = {'session_id', 'label', 'az_deg', 'el_deg', 'dist_mm',
                    'pen_type', 'color', 'visible', 'notes'}
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
        self.win.geometry("1050x520")

        tree_frame = ttk.Frame(self.win)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        cols = ("id", "session_id", "label", "type", "az", "el", "dist", "color", "visible", "notes")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                 height=15, selectmode="extended")
        for c, w in zip(cols, (40, 90, 90, 60, 60, 55, 65, 70, 50, 250)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, stretch=(c == "notes"))

        sb = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.tree.tag_configure("hidden", foreground="#888888")
        self.tree.tag_configure("visible", foreground="")

        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Button(btn_frame, text="Toggle Visible", command=self._toggle_vis).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Show All",       command=self._show_all).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Hide All",       command=self._hide_all).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Edit Selected",  command=self._edit).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Delete Selected",command=self._delete).pack(side=tk.LEFT, padx=3)
        ttk.Button(btn_frame, text="Refresh",        command=self._refresh_tree).pack(side=tk.LEFT, padx=3)

        self.status_var = tk.StringVar(value="")
        ttk.Label(self.win, textvariable=self.status_var, foreground="blue").pack(
            anchor="w", padx=8, pady=(0, 4))

        self._refresh_tree()

    def _refresh_tree(self):
        selected_ids = {iid for iid in self.tree.selection()}
        self.store.refresh()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for p in self.store.penetrations:
            vis = "\u2713" if p['visible'] else "\u2717"
            tag = "visible" if p['visible'] else "hidden"
            iid = str(p['id'])
            self.tree.insert("", tk.END, iid=iid,
                             values=(p['id'], p['session_id'], p['label'],
                                     p['pen_type'],
                                     f"{p['az_deg']:.1f}", f"{p['el_deg']:.1f}",
                                     f"{p['dist_mm']:.1f}",
                                     p['color'], vis, p['notes']),
                             tags=(tag,))
        still_present = [iid for iid in selected_ids if self.tree.exists(iid)]
        if still_present:
            self.tree.selection_set(still_present)
        n = len(self.store.penetrations)
        self.status_var.set(f"{n} penetration{'s' if n != 1 else ''}  |  "
                            f"Shift+click or Ctrl+click to select multiple")

    def _selected_ids(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("Info", "Select one or more penetrations first.")
            return []
        return [int(iid) for iid in sel]

    def _toggle_vis(self):
        ids = self._selected_ids()
        if not ids:
            return
        pens = {p['id']: p for p in self.store.penetrations}
        any_hidden = any(not pens[pid]['visible'] for pid in ids if pid in pens)
        new_vis = 1 if any_hidden else 0
        for pid in ids:
            if pid in pens:
                self.store.update(pid, visible=new_vis)
        self._refresh_tree()
        if self.on_change:
            self.on_change()

    def _show_all(self):
        for p in self.store.penetrations:
            if not p['visible']:
                self.store.update(p['id'], visible=1)
        self._refresh_tree()
        if self.on_change:
            self.on_change()

    def _hide_all(self):
        for p in self.store.penetrations:
            if p['visible']:
                self.store.update(p['id'], visible=0)
        self._refresh_tree()
        if self.on_change:
            self.on_change()

    def _delete(self):
        ids = self._selected_ids()
        if not ids:
            return
        msg = (f"Delete {len(ids)} penetration{'s' if len(ids) > 1 else ''}?\n"
               + ", ".join(str(i) for i in ids))
        if messagebox.askyesno("Confirm", msg):
            for pid in ids:
                self.store.delete(pid)
            self._refresh_tree()
            if self.on_change:
                self.on_change()

    def _edit(self):
        ids = self._selected_ids()
        if not ids:
            return
        if len(ids) > 1:
            messagebox.showinfo("Info", "Edit works on one row at a time.")
            return
        pid = ids[0]
        pen = next((p for p in self.store.penetrations if p['id'] == pid), None)
        if not pen:
            return

        edit_win = tk.Toplevel(self.win)
        edit_win.title(f"Edit Penetration {pid}")
        edit_win.geometry("400x360")

        fields = {}
        for i, (key, label) in enumerate([
            ('session_id', 'Session ID'), ('label', 'Label'),
            ('pen_type', 'Type'), ('az_deg', 'Az (deg)'), ('el_deg', 'El (deg)'),
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
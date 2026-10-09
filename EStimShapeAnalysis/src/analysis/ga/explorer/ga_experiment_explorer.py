"""
GA Experiment Explorer: look at one experiment's GA at a time, swap sessions
without restarting, and choose what to show from a list of plug-in modules.

Window
------
Top bar     Session picker (GA sessions in the repository; you can also type
            one, e.g. 260426_0), Prev / Next, and the active context
            (ga_database, ga_name) so you can always see which DB you're on.
Left panel  Module list, then the selected module's parameters. Parameters
            marked live redraw immediately; the others wait for Apply (or
            Enter). Below them the module's own buttons, and Save.
Centre      The selected module's view.

Switching session calls apply_session_context(session_id): the global
``src.startup.context`` (DB names, paths, ga_config) is switched in-process,
nothing is written to disk. Each module is told about the new session and
redrawn when you look at it.

Save writes the current view into a NEW timestamped folder
    <SAVE_ROOT>/<session_id>/ga_explorer/<module>_<YYYYmmdd_HHMMSS>/
with a config.json of the session, database and every parameter.

Adding your own module: see explorer_module.py (subclass FigureModule and
return a matplotlib/plotly figure), then add it to MODULES in main().

Run this file, or call launch(...).
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
                             QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QMainWindow, QMessageBox, QPushButton,
                             QScrollArea, QSpinBox, QSplitter, QStackedWidget,
                             QVBoxLayout, QWidget)

sys.path.insert(0, str(Path(__file__).parents[4]))

from src.analysis.ga.explorer.explorer_module import (ExplorerModule, SessionState, _slug,
                                                      new_output_folder)
from src.startup import context


def main():
    # ---------------------------------------------------------------- settings
    from src.analysis.ga.explorer.modules.delta_pair_viewer_module import DeltaPairViewerModule
    from src.analysis.ga.explorer.modules.all_pair_explorer_module import AllPairExplorerModule
    from src.analysis.ga.explorer.modules.top_n_module import TopNModule
    from src.analysis.ga.explorer.modules.top_per_gen_module import TopPerGenModule
    from src.analysis.ga.explorer.modules.response_by_generation_module import \
        ResponseByGenerationModule

    # Modules shown in the left list, in order. Add your own here.
    MODULES = [
        DeltaPairViewerModule,
        AllPairExplorerModule,
        TopNModule,
        TopPerGenModule,
        ResponseByGenerationModule,
    ]
    # Session to open with, e.g. "260426_0". None = the session context.py
    # currently points at.
    START_SESSION = None
    # ga_name passed to apply_session_context on every switch. None keeps
    # context.ga_name as it is (default "New3D").
    GA_NAME = None
    # Where Save writes its timestamped folders.
    SAVE_ROOT = "/home/connorlab/Documents/plots"
    # Base font size of the window (points).
    FONT_SIZE = 11
    # -------------------------------------------------------------------------

    launch(MODULES, start_session=START_SESSION, ga_name=GA_NAME,
           save_root=SAVE_ROOT, font_size=FONT_SIZE)


def launch(module_classes, *, start_session=None, ga_name=None,
           save_root="/home/connorlab/Documents/plots", font_size=11,
           session_lister=None):
    """Open the explorer. ``session_lister`` (a function returning session
    ids) defaults to the repository's GA sessions."""
    app = QApplication.instance() or QApplication(sys.argv)
    font = app.font()
    font.setPointSize(font_size)
    app.setFont(font)
    win = GAExperimentExplorer([cls() for cls in module_classes],
                               start_session=start_session, ga_name=ga_name,
                               save_root=save_root, session_lister=session_lister)
    win.show()
    app.exec_()


def session_id_from_db_name(db_name: str) -> str:
    """'allen_ga_exp_260426_0' -> '260426_0'."""
    parts = db_name.split("_")
    return "_".join(parts[-2:])


class GAExperimentExplorer(QMainWindow):
    def __init__(self, modules: list[ExplorerModule], *, start_session=None,
                 ga_name=None, save_root="/home/connorlab/Documents/plots",
                 session_lister=None):
        super().__init__()
        self.setWindowTitle("GA Experiment Explorer")
        self.resize(1600, 950)
        self.modules = modules
        self.ga_name = ga_name
        self.save_root = save_root
        self.session_lister = session_lister
        self.session: SessionState | None = None

        # Per-module UI state.
        self._param_widgets: list[dict] = []   # key -> (Param, widget)
        self._pending: list[set] = []          # non-live keys changed since Apply
        self._stale: list[bool] = []           # needs refresh for the current session
        self._apply_buttons: list[QPushButton] = []

        self._build_ui()
        self._load_session_list(select=start_session or session_id_from_db_name(context.ga_database))
        self.module_list.setCurrentRow(0)
        self.switch_session(self.session_combo.currentText().strip())

    # ------------------------------------------------------------------- UI
    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        self.setCentralWidget(central)

        # Session bar.
        bar = QHBoxLayout()
        bar.addWidget(QLabel("<b>Session</b>"))
        self.session_combo = QComboBox()
        self.session_combo.setEditable(True)
        self.session_combo.setMinimumWidth(160)
        self.session_combo.setToolTip("GA sessions in the repository; you can also type one.")
        self.session_combo.activated.connect(
            lambda _i: self.switch_session(self.session_combo.currentText().strip()))
        self.session_combo.lineEdit().returnPressed.connect(
            lambda: self.switch_session(self.session_combo.currentText().strip()))
        bar.addWidget(self.session_combo)
        prev_btn = QPushButton("◀ Prev")
        prev_btn.clicked.connect(lambda: self._step_session(-1))
        next_btn = QPushButton("Next ▶")
        next_btn.clicked.connect(lambda: self._step_session(+1))
        reload_btn = QPushButton("Reload list")
        reload_btn.setToolTip("Re-read the session list from the repository.")
        reload_btn.clicked.connect(lambda: self._load_session_list(
            select=self.session.session_id if self.session else None))
        for b in (prev_btn, next_btn, reload_btn):
            bar.addWidget(b)
        bar.addSpacing(20)
        self.context_label = QLabel()
        self.context_label.setStyleSheet("color: #444;")
        self.context_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bar.addWidget(self.context_label, stretch=1)
        root.addLayout(bar)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, stretch=1)

        # Left panel: module list + per-module parameter pages.
        left = QWidget()
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.addWidget(QLabel("<b>Modules</b>"))
        self.module_list = QListWidget()
        self.module_list.setMaximumHeight(28 * max(3, len(self.modules)) + 8)
        for m in self.modules:
            self.module_list.addItem(m.name)
        left_lay.addWidget(self.module_list)

        self.param_stack = QStackedWidget()
        self.view_stack = QStackedWidget()
        for idx, m in enumerate(self.modules):
            m.status = self._set_status
            m.save_root = self.save_root
            self.param_stack.addWidget(self._build_param_page(idx, m))
            self.view_stack.addWidget(m.create_view(self.view_stack))
            self._stale.append(True)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidget(self.param_stack)
        left_lay.addWidget(scroll, stretch=1)

        save_btn = QPushButton("Save view…")
        save_btn.setToolTip("Write the current view + config.json into a new timestamped folder.")
        save_btn.clicked.connect(self.save_current)
        left_lay.addWidget(save_btn)
        left.setMinimumWidth(420)
        splitter.addWidget(left)

        right = QWidget()
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.error_label.setStyleSheet("color: #b00020; font-weight: bold;")
        self.error_label.hide()
        right_lay.addWidget(self.error_label)
        right_lay.addWidget(self.view_stack, stretch=1)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([440, 1160])

        self.module_list.currentRowChanged.connect(self._on_module_selected)
        self.statusBar().showMessage("Ready")

    def _build_param_page(self, idx, module: ExplorerModule):
        page = QWidget()
        lay = QVBoxLayout(page)
        if module.description:
            desc = QLabel(module.description)
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #555;")
            lay.addWidget(desc)

        form = QFormLayout()
        widgets = {}
        for p in module.params():
            w = self._make_param_widget(idx, p)
            if p.tooltip:
                w.setToolTip(p.tooltip)
            label = p.label + ("" if p.live else " *")
            form.addRow(label, w)
            widgets[p.key] = (p, w)
        lay.addLayout(form)
        self._param_widgets.append(widgets)
        self._pending.append(set())

        apply_btn = QPushButton("Apply")
        apply_btn.setToolTip("Redraw with the * settings (they recompute).")
        apply_btn.clicked.connect(lambda: self._apply(idx))
        self._apply_buttons.append(apply_btn)
        if any(not p.live for p, _ in widgets.values()):
            lay.addWidget(QLabel("<small>* applied with the Apply button / Enter</small>"))
            lay.addWidget(apply_btn)

        for action in module.actions():
            b = QPushButton(action.label)
            if action.tooltip:
                b.setToolTip(action.tooltip)
            if action.color:
                b.setStyleSheet(f"background: {action.color};")
            b.clicked.connect(lambda _c=False, a=action: self._run_guarded(a.callback))
            lay.addWidget(b)
        lay.addStretch(1)
        return page

    def _make_param_widget(self, idx, p):
        def changed(_v=None, key=p.key):
            self._on_param_changed(idx, key)

        if p.kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(p.default))
            w.toggled.connect(changed)
        elif p.kind == "int":
            w = QSpinBox()
            w.setRange(int(p.minimum if p.minimum is not None else -10**9),
                       int(p.maximum if p.maximum is not None else 10**9))
            w.setSingleStep(int(p.step or 1))
            w.setValue(int(p.default))
            w.valueChanged.connect(changed)
            w.lineEdit().returnPressed.connect(lambda: self._apply(idx))
        elif p.kind == "float":
            w = QDoubleSpinBox()
            w.setDecimals(p.decimals)
            w.setRange(p.minimum if p.minimum is not None else -1e9,
                       p.maximum if p.maximum is not None else 1e9)
            w.setSingleStep(p.step or 0.1)
            w.setValue(float(p.default))
            w.valueChanged.connect(changed)
            w.lineEdit().returnPressed.connect(lambda: self._apply(idx))
        elif p.kind == "choice":
            w = QComboBox()
            # Size to a short text, not the longest choice, so the panel fits.
            w.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            w.setMinimumContentsLength(8)
            w.addItems([str(c) for c in p.choices])
            w.setCurrentText(str(p.default))
            w.currentTextChanged.connect(changed)
        elif p.kind == "str":
            w = QLineEdit(str(p.default))
            w.textEdited.connect(changed)
            w.returnPressed.connect(lambda: self._apply(idx))
        else:
            raise ValueError(f"Unknown param kind {p.kind!r} for {p.key}")
        return w

    # --------------------------------------------------------------- params
    def values(self, idx) -> dict:
        out = {}
        for key, (p, w) in self._param_widgets[idx].items():
            if p.kind == "bool":
                out[key] = w.isChecked()
            elif p.kind in ("int", "float"):
                out[key] = w.value()
            elif p.kind == "choice":
                text = w.currentText()
                out[key] = next((c for c in p.choices if str(c) == text), text)
            else:
                out[key] = w.text()
        return out

    def _on_param_changed(self, idx, key):
        p, _w = self._param_widgets[idx][key]
        if p.live:
            if not self._stale[idx]:
                self._refresh(idx, changed={key})
        else:
            self._pending[idx].add(key)
            self._apply_buttons[idx].setStyleSheet("background: #ffd27f; font-weight: bold;")

    def _apply(self, idx):
        changed = set(self._pending[idx])
        self._pending[idx].clear()
        self._apply_buttons[idx].setStyleSheet("")
        self._refresh(idx, changed=None if self._stale[idx] else changed)

    # -------------------------------------------------------------- sessions
    def _load_session_list(self, select=None):
        lister = self.session_lister
        if lister is None:
            from src.analysis.ga.explorer.ga_data import list_ga_sessions
            lister = list_ga_sessions
        try:
            sessions = sorted(lister())
        except Exception as exc:
            traceback.print_exc()
            sessions = []
            self._set_status(f"Could not list sessions ({exc}); type one in the box.")
        self.session_combo.blockSignals(True)
        self.session_combo.clear()
        self.session_combo.addItems(sessions)
        if select:
            if select not in sessions:
                self.session_combo.addItem(select)
            self.session_combo.setCurrentText(select)
        self.session_combo.blockSignals(False)

    def _step_session(self, step):
        n = self.session_combo.count()
        if n == 0:
            return
        i = self.session_combo.findText(self.session.session_id if self.session else "")
        i = min(n - 1, max(0, (i if i >= 0 else 0) + step))
        self.session_combo.setCurrentIndex(i)
        self.switch_session(self.session_combo.itemText(i))

    def switch_session(self, session_id: str):
        if not session_id:
            return
        if self.session is not None and session_id == self.session.session_id:
            return
        from src.startup.apply_session_context import apply_session_context

        previous = self.session.session_id if self.session else None
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            apply_session_context(session_id, ga_name=self.ga_name)
        except Exception as exc:
            traceback.print_exc()
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(self, "Session switch failed",
                                 f"Could not switch to {session_id}:\n{exc}")
            # apply_session sets the DB names before building ga_config, so a
            # failure can leave the context half-switched: put it back.
            if previous:
                try:
                    apply_session_context(previous, ga_name=self.ga_name)
                except Exception:
                    traceback.print_exc()
                self.session_combo.setCurrentText(previous)
            self._update_context_label()
            return
        QApplication.restoreOverrideCursor()

        self.session = SessionState(session_id=session_id, ga_database=context.ga_database)
        if self.session_combo.findText(session_id) < 0:
            self.session_combo.addItem(session_id)
        self.session_combo.setCurrentText(session_id)
        self._update_context_label()
        for idx, m in enumerate(self.modules):
            self._stale[idx] = True
            try:
                m.set_session(self.session)
            except Exception:
                traceback.print_exc()
        current = self.module_list.currentRow()
        if current >= 0:
            self._refresh(current, changed=None)

    def _update_context_label(self):
        self.context_label.setText(
            f"ga_database: <b>{context.ga_database}</b> &nbsp; ga_name: {context.ga_name}")

    # --------------------------------------------------------------- modules
    def _on_module_selected(self, idx):
        if idx < 0:
            return
        self.param_stack.setCurrentIndex(idx)
        self.view_stack.setCurrentIndex(idx)
        self.error_label.hide()
        if self.session is not None and self._stale[idx]:
            self._refresh(idx, changed=None)

    def _refresh(self, idx, changed=None):
        if self.session is None:
            return
        module = self.modules[idx]
        # A non-live edit made before a full refresh is folded into it.
        if changed is None:
            self._pending[idx].clear()
            self._apply_buttons[idx].setStyleSheet("")
        self._set_status(f"{module.name}: working on {self.session.session_id}…")
        self.error_label.hide()
        QApplication.setOverrideCursor(Qt.WaitCursor)
        QApplication.processEvents()
        try:
            module.refresh(self.values(idx), changed)
            self._stale[idx] = False
        except Exception as exc:
            traceback.print_exc()
            self._show_error(f"{module.name} failed on {self.session.session_id}: "
                             f"{type(exc).__name__}: {exc}")
        finally:
            QApplication.restoreOverrideCursor()

    def _run_guarded(self, fn):
        try:
            fn()
        except Exception as exc:
            traceback.print_exc()
            self._show_error(f"{type(exc).__name__}: {exc}")

    def _show_error(self, text):
        self.error_label.setText(text)
        self.error_label.show()
        self.statusBar().showMessage(text)

    def _set_status(self, text):
        self.statusBar().showMessage(text)

    # ------------------------------------------------------------------ save
    def save_current(self):
        idx = self.module_list.currentRow()
        if idx < 0 or self.session is None:
            return
        module = self.modules[idx]
        folder = None
        try:
            folder = new_output_folder(self.save_root, self.session.session_id, module.name)
            files = module.save(folder)
            if not files:
                path = os.path.join(folder, f"{_slug(module.name)}.png")
                self.view_stack.currentWidget().grab().save(path)
                files = [path]
            config = {
                "module": module.name,
                "module_class": f"{type(module).__module__}.{type(module).__name__}",
                "session_id": self.session.session_id,
                "ga_database": context.ga_database,
                "ga_name": context.ga_name,
                "params": self.values(idx),
                "files": [os.path.basename(f) for f in files],
                "saved_at": datetime.now().isoformat(timespec="seconds"),
            }
            with open(os.path.join(folder, "config.json"), "w") as f:
                json.dump(config, f, indent=2, default=str)
        except Exception as exc:
            traceback.print_exc()
            if folder and os.path.isdir(folder) and not os.listdir(folder):
                os.rmdir(folder)
            QMessageBox.critical(self, "Save failed", str(exc))
            return
        self._set_status(f"Saved to {folder}")


if __name__ == "__main__":
    main()

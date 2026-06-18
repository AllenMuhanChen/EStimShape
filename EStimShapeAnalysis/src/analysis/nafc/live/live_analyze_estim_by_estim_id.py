"""
live_analyze_estim_by_estim_id.py
---------------------------------
Live GUI version of analyze_estim_by_estim_id's Plot 1 (the EStimSpecId overview).

On a timer it:
    1. polls the experiment DB for newly-completed choice trials,
    2. compiles just those trials into EStimShapeTrials (allen_data_repository),
    3. re-reads EStimShapeTrials for the session and redraws Plot 1 — so the figure
       tracks the experiment in near-real-time.

Scope (intentionally minimal for now):
    - Plot 1 only: % Hypothesized, % Rand Choice, % Hypothesized vs Delta
      (and % Removed Choice when removed trials/choices exist).
    - No permutation tests (observed effects only).
    - No optional spec/noise/sample-length filtering or combining.
    - start_gen_id is honoured (trials below it are not plotted).

The plotting itself reuses partition_estim_data / build_overview_figure from
analyze_estim_by_estim_id, so the live and batch figures stay identical. The pairs figure
and sliding-window analysis remain available in that module for later live panels.

The control bar (refresh / live toggle / poll interval) is a deliberate seed for the richer
GUI (buttons, dropdowns) planned later.

Run:
    python -m src.analysis.nafc.live.live_analyze_estim_by_estim_id
"""

import sys

import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSpinBox, QCheckBox,
)
from PyQt5.QtCore import QTimer

from clat.util.connection import Connection
from src.startup import context
from src.repository.export_to_repository import read_session_id_and_date_from_db_name

from src.analysis.nafc.analyze_estim_by_estim_id import (
    partition_estim_data, build_overview_figure, make_overview_row_labels,
)
from src.analysis.nafc.live.live_estim_compile import (
    REPO_DB, ensure_estimshape_trials_table, compile_new_trials, get_existing_trial_starts,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEFAULT_POLL_SECONDS = 5
START_GEN_ID = 1                 # keep start_gen_id; trials below this are not plotted
IS_CORRECT_FIELD_NAME = 'IsHypothesized'
# Experimental stim types that make up Plot 1 (matches analyze_estim_by_estim_id.main).
_EXPERIMENTAL_STIM_TYPES = ['EStimShapeVariantsDeltaNAFCStim', 'EStimShapeVariantsDeletedNAFCStim']
# ---------------------------------------------------------------------------


def read_session_trials_as_exp_format(session_id, start_gen_id=START_GEN_ID):
    """Read this session's rows from EStimShapeTrials and map them back to the experiment-DB
    column names that the Plot-1 panels expect (IsHypothesized, EStimEnabled, …). Applies the
    start_gen_id cut and restricts to experimental stim types."""
    conn = Connection(REPO_DB)
    conn.execute("""
        SELECT task_id, estim_spec_id, is_estim_on, is_hypothesized_choice,
               is_correct_choice, trial_type, noise_chance, base_mstick_id,
               gen_id, trial_start, sample_length, trial_class, choice
        FROM EStimShapeTrials
        WHERE session_id = %s
        ORDER BY task_id
    """, (session_id,))
    # Column names must be read before fetch_all (which closes the cursor).
    column_names = [desc[0] for desc in conn.my_cursor.description]
    rows = conn.fetch_all()
    db = pd.DataFrame(rows, columns=column_names)
    if len(db) == 0:
        return db

    out = pd.DataFrame(index=db.index)
    out['NoiseChance']    = db['noise_chance']
    out['IsHypothesized'] = db['is_hypothesized_choice'].astype(bool)
    out['IsCorrect']      = db['is_correct_choice'].astype(bool)
    out['EStimEnabled']   = db['is_estim_on'].astype(bool)
    out['EStimSpecId']    = db['estim_spec_id']
    out['Choice']         = db['choice']
    out['SampleLength']   = db['sample_length']
    out['GenId']          = db['gen_id']
    out['BaseMStickId']   = db['base_mstick_id']
    out['StimType']       = db['trial_class']
    # trial_type is the compiled label; reconstruct the booleans the partition needs.
    out['IsDelta']         = db['trial_type'] == 'Delta Shape'
    out['IsRemovedTrial']  = db['trial_type'] == 'Removed Trial'

    out = out[out['GenId'] >= start_gen_id]
    out = out[out['StimType'].isin(_EXPERIMENTAL_STIM_TYPES)]
    return out


class LiveEstimWindow(QMainWindow):
    """Main window: a control bar + an embedded matplotlib canvas showing Plot 1."""

    def __init__(self, exp_conn, session_id):
        super().__init__()
        self.exp_conn = exp_conn
        self.session_id = session_id
        # Seed seen trials from what's already compiled so a restart doesn't redo the session.
        self.seen_starts = get_existing_trial_starts(session_id)
        self._setup_ui()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self._refresh()  # initial compile + draw
        self.timer.start(self.interval_spin.value() * 1000)

    # ---- UI -------------------------------------------------------------
    def _setup_ui(self):
        self.setWindowTitle(f'Live EStim Analysis — {self.session_id}')
        self.setGeometry(100, 100, 1700, 1000)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Control bar — seed for future buttons/dropdowns.
        bar = QHBoxLayout()
        self.refresh_button = QPushButton('Refresh now')
        self.refresh_button.clicked.connect(self._refresh)

        self.live_checkbox = QCheckBox('Live')
        self.live_checkbox.setChecked(True)
        self.live_checkbox.stateChanged.connect(self._toggle_live)

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 120)
        self.interval_spin.setValue(DEFAULT_POLL_SECONDS)
        self.interval_spin.setSuffix(' s')
        self.interval_spin.valueChanged.connect(self._change_interval)

        self.status_label = QLabel('Starting…')

        bar.addWidget(self.refresh_button)
        bar.addWidget(self.live_checkbox)
        bar.addWidget(QLabel('Poll every'))
        bar.addWidget(self.interval_spin)
        bar.addStretch(1)
        bar.addWidget(self.status_label)
        layout.addLayout(bar)

        # Figure + matplotlib navigation toolbar.
        self.figure = plt.figure(figsize=(16, 16))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

    # ---- polling / refresh ---------------------------------------------
    def _toggle_live(self):
        if self.live_checkbox.isChecked():
            self.timer.start(self.interval_spin.value() * 1000)
        else:
            self.timer.stop()

    def _change_interval(self, value):
        if self.live_checkbox.isChecked():
            self.timer.start(value * 1000)

    def _refresh(self):
        """Compile any new trials, then redraw. Errors are surfaced in the status label rather
        than killing the timer, so a transient DB hiccup doesn't stop the live view."""
        try:
            n_new = compile_new_trials(self.exp_conn, self.session_id, self.seen_starts)
        except Exception as e:
            self.status_label.setText(f'Compile error: {e}')
            return

        try:
            n_trials = self._redraw()
        except Exception as e:
            self.status_label.setText(f'Plot error: {e}')
            return

        suffix = f'  (+{n_new} new)' if n_new else ''
        self.status_label.setText(f'{self.session_id}: {n_trials} trials plotted{suffix}')

    def _redraw(self):
        """Rebuild Plot 1 from EStimShapeTrials. Returns the number of plotted trials."""
        data_exp = read_session_trials_as_exp_format(self.session_id, START_GEN_ID)

        if data_exp is None or len(data_exp) == 0:
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Waiting for trials…', ha='center', va='center', fontsize=14)
            ax.axis('off')
            self.canvas.draw()
            return 0

        partition = partition_estim_data(data_exp)
        row_labels = make_overview_row_labels(IS_CORRECT_FIELD_NAME, partition.include_removed)
        build_overview_figure(self.figure, partition, row_labels, n_permutations=0)
        self.figure.suptitle(
            f'Live EStimSpecId Analysis — {self.session_id} — {IS_CORRECT_FIELD_NAME}',
            fontsize=15, y=1.005)
        self.canvas.draw()
        return len(data_exp)


def main():
    ensure_estimshape_trials_table()
    exp_conn = Connection(context.nafc_database)
    session_id, _ = read_session_id_and_date_from_db_name(context.nafc_database)

    app = QApplication(sys.argv)
    window = LiveEstimWindow(exp_conn, session_id)
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

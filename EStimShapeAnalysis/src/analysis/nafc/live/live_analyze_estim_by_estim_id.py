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
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSpinBox, QCheckBox, QScrollArea,
)
from PyQt5.QtCore import QTimer, Qt

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


class _ScrollableCanvas(FigureCanvas):
    """FigureCanvas whose wheel events scroll the surrounding QScrollArea vertically rather
    than triggering matplotlib's zoom — so the tall overview figure can be scrolled through."""

    def __init__(self, figure):
        super().__init__(figure)
        self.scroll_area = None

    def wheelEvent(self, event):
        if self.scroll_area is not None:
            bar = self.scroll_area.verticalScrollBar()
            bar.setValue(bar.value() - event.angleDelta().y())
            event.accept()
        else:
            super().wheelEvent(event)


class LiveEstimWindow(QMainWindow):
    """Main window: a control bar + a scrollable matplotlib canvas showing Plot 1."""

    def __init__(self, exp_conn, session_id):
        super().__init__()
        self.exp_conn = exp_conn
        self.session_id = session_id
        # Seed seen trials from what's already compiled so a restart doesn't redo the session.
        self.seen_starts = get_existing_trial_starts(session_id)
        # Default axes limits from the previous build, used to tell whether the user has
        # manually zoomed/panned an axes (and so wants that view kept across refreshes).
        self._prev_default_limits = None
        # Whether we've drawn at least once — forces the initial draw even with no new trials.
        self._has_drawn = False
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
        self.refresh_button.clicked.connect(self._force_refresh)

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

        # Figure inside a scroll area: the overview figure is tall, so render it at a
        # readable size (fit to width) and let the wheel scroll it vertically rather than
        # squashing everything into the window.
        # A bare Figure (not plt.figure) so the only canvas/manager is ours — a pyplot-managed
        # figure embedded in Qt produces phantom/overlapping renders on repeated redraws.
        self.figure = Figure(figsize=(16, 16))
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.canvas = _ScrollableCanvas(self.figure)
        self.canvas.scroll_area = self.scroll
        self.scroll.setWidget(self.canvas)

        self.toolbar = NavigationToolbar(self.canvas, self)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.scroll)

    def _fit_canvas(self):
        """Size the canvas to the scroll viewport width, keeping the figure's aspect ratio,
        so content stays readable and only vertical scrolling is needed."""
        w_in, h_in = self.figure.get_size_inches()
        if w_in <= 0:
            return
        # -2 px guard so the canvas never exceeds the viewport and forces a horizontal bar.
        width = max(self.scroll.viewport().width() - 2, 600)
        height = int(width * (h_in / w_in))
        # Only resize when it actually changed, to avoid layout churn on every redraw.
        if self.canvas.width() != width or self.canvas.height() != height:
            self.canvas.setFixedSize(width, height)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._fit_canvas()

    # ---- polling / refresh ---------------------------------------------
    def _toggle_live(self):
        if self.live_checkbox.isChecked():
            self.timer.start(self.interval_spin.value() * 1000)
        else:
            self.timer.stop()

    def _change_interval(self, value):
        if self.live_checkbox.isChecked():
            self.timer.start(value * 1000)

    def _force_refresh(self):
        """Refresh requested explicitly (button) — always redraw."""
        self._refresh(force=True)

    def _refresh(self, force=False):
        """Compile any new trials, then redraw *only if something changed* (or forced).

        Redrawing rebuilds the whole figure and resizes the canvas; doing that every tick
        would yank the view around while you're scrolling. So when no new trials arrived and
        we've already drawn once, we leave the current view completely untouched. Errors are
        surfaced in the status label rather than killing the timer."""
        try:
            n_new = compile_new_trials(self.exp_conn, self.session_id, self.seen_starts)
        except Exception as e:
            self.status_label.setText(f'Compile error: {e}')
            return

        if n_new == 0 and self._has_drawn and not force:
            return  # nothing changed — don't disturb the user's scroll/zoom

        try:
            n_trials = self._redraw()
            self._has_drawn = True
        except Exception as e:
            self.status_label.setText(f'Plot error: {e}')
            return

        suffix = f'  (+{n_new} new)' if n_new else ''
        self.status_label.setText(f'{self.session_id}: {n_trials} trials plotted{suffix}')

    def _redraw(self):
        """Rebuild Plot 1 from EStimShapeTrials. Returns the number of plotted trials.

        The rebuild clears the figure, which would reset the scroll position and any manual
        zoom/pan. We capture both first and reapply them: scroll always, and per-axes limits
        only for axes the user actually changed from the previous build's defaults (so axes
        they haven't touched still auto-scale as live data accumulates)."""
        data_exp = read_session_trials_as_exp_format(self.session_id, START_GEN_ID)

        scroll_v = self.scroll.verticalScrollBar().value()
        saved_limits = [(ax.get_xlim(), ax.get_ylim()) for ax in self.figure.axes]

        if data_exp is None or len(data_exp) == 0:
            self.figure.clear()
            self.figure.set_size_inches(12, 8)
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'Waiting for trials…', ha='center', va='center', fontsize=14)
            ax.axis('off')
            self._prev_default_limits = None
            self._fit_canvas()
            self.canvas.draw()
            self.scroll.verticalScrollBar().setValue(scroll_v)
            return 0

        partition = partition_estim_data(data_exp)
        row_labels = make_overview_row_labels(IS_CORRECT_FIELD_NAME, partition.include_removed)
        build_overview_figure(self.figure, partition, row_labels, n_permutations=0)
        self.figure.suptitle(
            f'Live EStimSpecId Analysis — {self.session_id} — {IS_CORRECT_FIELD_NAME}',
            fontsize=15, y=0.99)

        # Default (freshly-built) view, captured before reapplying the user's zoom.
        new_axes = self.figure.axes
        new_defaults = [(ax.get_xlim(), ax.get_ylim()) for ax in new_axes]

        # Reset the toolbar history to the rebuilt axes now, so the default view is "Home"
        # (and back/forward don't reference the deleted pre-rebuild axes).
        self.toolbar.update()

        if (self._prev_default_limits is not None
                and len(saved_limits) == len(self._prev_default_limits) == len(new_axes)):
            for ax, saved, prev_default in zip(new_axes, saved_limits, self._prev_default_limits):
                if saved != prev_default:  # user had zoomed/panned this axes
                    ax.set_xlim(saved[0])
                    ax.set_ylim(saved[1])
        self._prev_default_limits = new_defaults

        self._fit_canvas()
        self.canvas.draw()
        self.scroll.verticalScrollBar().setValue(scroll_v)
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

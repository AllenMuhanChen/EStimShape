"""A Qt window that shows one matplotlib figure at a time and lets you cycle
through a list of them.

Motivation: some exports produce a whole family of related figures (e.g. the
stimuli-in-loading-space scatter colored by each condition). Popping one window
per figure buries the screen; this shows them in a single window with
Prev/Next and a dropdown, plus a navigation toolbar so each figure can be
zoomed/panned. Left/Right arrow keys also step through.

Figures are rendered at their native pixel size inside a scroll area, matching
the saved PNGs, so nothing is squished when a figure is larger than the window.
The window is non-blocking; keep a reference to it (as callers do for other
matplotlib Qt windows) so it isn't garbage-collected.
"""

from typing import Sequence, Tuple

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg, NavigationToolbar2QT)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QComboBox, QLabel, QScrollArea)


class FigureCyclerWindow(QMainWindow):
    """Cycle through ``[(title, Figure), ...]`` in one window.

    Args:
        figures: ordered ``(title, Figure)`` pairs. Titles populate the dropdown.
        window_title: window chrome title.
    """

    def __init__(self, figures: Sequence[Tuple[str, Figure]],
                 window_title: str = "Figures", parent=None):
        super().__init__(parent)
        self._figures = list(figures)
        self._index = 0
        self._base_title = window_title
        self.setWindowTitle(window_title)

        container = QWidget()
        outer = QVBoxLayout(container)
        outer.addLayout(self._build_nav_bar())

        # The figure area is rebuilt on each switch; keep a handle to its layout
        # slot so we can swap the canvas + toolbar in and out.
        self._figure_host = QWidget()
        self._figure_host_layout = QVBoxLayout(self._figure_host)
        self._figure_host_layout.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self._figure_host)

        self.setCentralWidget(container)
        self.resize(1500, 950)

        if self._figures:
            self._show_current()
        else:
            self._figure_host_layout.addWidget(
                QLabel("No figures to display."))

    # ---- construction helpers -------------------------------------------
    def _build_nav_bar(self) -> QHBoxLayout:
        nav = QHBoxLayout()
        self._prev_button = QPushButton("◀ Prev")
        self._prev_button.clicked.connect(self.show_previous)
        self._next_button = QPushButton("Next ▶")
        self._next_button.clicked.connect(self.show_next)

        self._selector = QComboBox()
        self._selector.addItems([title for title, _ in self._figures])
        # currentIndexChanged fires on programmatic changes too; guard against
        # re-entrancy while we sync it in _show_current.
        self._syncing_selector = False
        self._selector.currentIndexChanged.connect(self._on_selector_changed)

        self._counter = QLabel()

        nav.addWidget(self._prev_button)
        nav.addWidget(self._next_button)
        nav.addWidget(self._selector, stretch=1)
        nav.addWidget(self._counter)
        return nav

    # ---- navigation ------------------------------------------------------
    def show_next(self) -> None:
        if self._figures:
            self._go_to((self._index + 1) % len(self._figures))

    def show_previous(self) -> None:
        if self._figures:
            self._go_to((self._index - 1) % len(self._figures))

    def _on_selector_changed(self, index: int) -> None:
        if self._syncing_selector or index < 0:
            return
        self._go_to(index)

    def _go_to(self, index: int) -> None:
        if index == self._index:
            return
        self._index = index
        self._show_current()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Right:
            self.show_next()
        elif event.key() == Qt.Key_Left:
            self.show_previous()
        else:
            super().keyPressEvent(event)

    # ---- rendering -------------------------------------------------------
    def _show_current(self) -> None:
        title, fig = self._figures[self._index]

        self._clear_figure_host()

        canvas = FigureCanvasQTAgg(fig)
        # Pin the canvas to the figure's native pixel size so content renders at
        # the designed scale (same as the saved PNG); the scroll area lets the
        # user pan when the figure is larger than the window.
        dpi = fig.get_dpi()
        canvas.setMinimumSize(int(fig.get_figwidth() * dpi),
                              int(fig.get_figheight() * dpi))

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(canvas)

        toolbar = NavigationToolbar2QT(canvas, self._figure_host)
        self._figure_host_layout.addWidget(toolbar)
        self._figure_host_layout.addWidget(scroll)
        canvas.draw()

        self._counter.setText(f"{self._index + 1} / {len(self._figures)}")
        self.setWindowTitle(f"{self._base_title} — {title}")

        self._syncing_selector = True
        self._selector.setCurrentIndex(self._index)
        self._syncing_selector = False

    def _clear_figure_host(self) -> None:
        while self._figure_host_layout.count():
            item = self._figure_host_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

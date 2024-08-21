import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt

from clat.util.connection import Connection
from src.startup import config
from plot_trial import plot_trial_images


class TrialImageBrowser(QMainWindow):
    def __init__(self, conn, stim_spec_ids):
        super().__init__()
        self.conn = conn
        self.stim_spec_ids = stim_spec_ids
        self.current_index = 0

        self.initUI()

    def initUI(self):
        self.setWindowTitle('Trial Image Browser')
        self.setGeometry(100, 100, 1200, 800)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Create matplotlib figure and canvas
        self.figure, self.ax = plt.subplots(1, 2, figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas)

        # Create navigation buttons and label
        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton('Previous')
        self.prev_button.clicked.connect(self.show_previous)
        self.next_button = QPushButton('Next')
        self.next_button.clicked.connect(self.show_next)
        self.id_label = QLabel()

        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.id_label)
        nav_layout.addWidget(self.next_button)

        main_layout.addLayout(nav_layout)

        self.update_plot()

    def update_plot(self):
        self.figure.clear()

        stim_spec_id = self.stim_spec_ids[self.current_index]
        self.id_label.setText(f'Stim Spec ID: {stim_spec_id}')

        plot_trial_images(stim_spec_id, self.conn, self.figure)

        self.canvas.draw()

    def show_previous(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.update_plot()

    def show_next(self):
        if self.current_index < len(self.stim_spec_ids) - 1:
            self.current_index += 1
            self.update_plot()

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.show_previous()
        else:
            self.show_next()


def get_recent_stim_spec_ids(conn: Connection, n: int) -> list:
    query = """
    SELECT id 
    FROM StimSpec 
    ORDER BY id DESC 
    LIMIT %s
    """
    conn.execute(query, params=(n,))
    results = conn.fetch_all()
    return [result[0] for result in results]


def main():
    conn = Connection(config.nafc_database)

    # Get the 100 most recent stim_spec_ids
    n_recent = 100
    stim_spec_ids = get_recent_stim_spec_ids(conn, n_recent)


    app = QApplication(sys.argv)
    browser = TrialImageBrowser(conn, stim_spec_ids)
    browser.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
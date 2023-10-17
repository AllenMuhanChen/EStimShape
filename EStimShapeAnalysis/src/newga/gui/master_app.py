from PyQt5.QtWidgets import QMainWindow, QPushButton, QWidget, QVBoxLayout, QStackedWidget, QHBoxLayout

from tests.newga.cluster.mock_app import MockDataLoader, MockDataExporter, MockChannelMapper

from clat.intan.channels import Channel
from newga.gui.cluster.cluster_app import ClusterApplicationWindow
from newga.gui.cluster.dimensionality_reduction import PCAReducer, MDSReducer


def cluster_app():
    return ClusterApplicationWindow(MockDataLoader(), MockDataExporter(), [PCAReducer(), MDSReducer()],
                                    MockChannelMapper(Channel))


class MasterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Master App')

        # Create the stacked widget
        self.stack = QStackedWidget()

        # Initialize your sub-GUIs (widgets)
        self.cluster_gui = cluster_app()
        self.gui2 = YourSecondGui()
        self.gui3 = YourThirdGui()

        # Add the sub-GUIs to the stack
        self.stack.addWidget(self.cluster_gui)
        self.stack.addWidget(self.gui2)
        self.stack.addWidget(self.gui3)

        # Create switch buttons
        self.button1 = QPushButton('Cluster App')
        self.button1.clicked.connect(lambda: self.switch_gui(0))
        self.button2 = QPushButton('GUI 2')
        self.button2.clicked.connect(lambda: self.switch_gui(1))
        self.button3 = QPushButton('GUI 3')
        self.button3.clicked.connect(lambda: self.switch_gui(2))

        # Set up button layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.button1)
        button_layout.addWidget(self.button2)
        button_layout.addWidget(self.button3)

        # Set up main layout
        main_layout = QVBoxLayout()
        main_layout.addLayout(button_layout)
        main_layout.addWidget(self.stack)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def switch_gui(self, index):
        self.stack.setCurrentIndex(index)


class YourSecondGui(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize your second GUI


class YourThirdGui(QWidget):
    def __init__(self):
        super().__init__()
        # Initialize your third GUI


if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = MasterApp()
    window.show()
    sys.exit(app.exec_())

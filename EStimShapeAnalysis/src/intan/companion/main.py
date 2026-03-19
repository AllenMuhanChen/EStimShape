#!/usr/bin/env python3
"""
Intan LFP Analyzer
==================
Real-time LFP analysis GUI for Intan RHX systems via TCP.

Usage:
    1. Start the Intan RHX software
    2. Open Network → Remote TCP Control
    3. Set Command Output to 127.0.0.1:5000, click Listen (status → Pending)
    4. Set Waveform Output to 127.0.0.1:5001, click Listen (status → Pending)
    5. Add desired channels to TCP Data Output in Intan RHX
       (set each channel's TCPDataOutputEnabled to true)
    6. Run this application:  python main.py
    7. Click Connect — channels will be auto-discovered
    8. (Optional) Set custom channel order to match your probe layout
    9. Streaming → Start Streaming

Requirements:
    pip install PyQt5 numpy scipy matplotlib
"""

import sys
import os

from src.intan.companion.main_window import MainWindow

# Add parent directory to path so imports work when run from the gui/ folder
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt




def main():
    # High DPI support
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("Intan LFP Analyzer")
    app.setStyle("Fusion")  # Consistent cross-platform look

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

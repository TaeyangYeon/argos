#!/usr/bin/env python3
"""
Argos - AI-powered vision algorithm design agent
Entry point for the application
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont

from ui.main_window import MainWindow


def main():
    """Main entry point for Argos application."""
    # Create QApplication
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Argos")
    app.setOrganizationName("ArgosVision")
    
    # Try to set preferred font, fallback to Arial
    try:
        font = QFont("Noto Sans KR", 10)
        if not font.exactMatch():
            font = QFont("Arial", 10)
        app.setFont(font)
    except Exception:
        # Fallback to system default font
        pass
    
    # Create and show main window
    window = MainWindow()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""Запуск приложения:  python -m lab.gui.app   (из корня проекта, PYTHONPATH=src)."""
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from lab.gui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow(storage_path=Path.home() / ".subscribers_lab7.json")
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

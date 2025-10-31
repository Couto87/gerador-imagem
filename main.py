"""Entry point for the Image Studio IA desktop application."""
from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from core.app_controller import AppController


def _apply_stylesheet(app: QApplication) -> None:
    style_path = Path(__file__).resolve().parent / "assets" / "styles.qss"
    if style_path.exists():
        with style_path.open("r", encoding="utf-8") as fh:
            app.setStyleSheet(fh.read())


def main() -> int:
    app = QApplication(sys.argv)
    _apply_stylesheet(app)

    controller = AppController()
    controller.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

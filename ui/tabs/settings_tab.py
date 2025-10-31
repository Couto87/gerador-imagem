"""Settings tab displaying persistent configuration values."""
from __future__ import annotations

from typing import Dict

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QVBoxLayout, QWidget

from ..config_panel import ConfigPanel


class SettingsTab(QWidget):
    """Aggregate generation options and the currently saved configuration."""

    optionChanged = pyqtSignal(str, str, object)
    outputFolderBrowseRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        self.configPanel = ConfigPanel()
        self.configPanel.optionChanged.connect(self.optionChanged)
        self.configPanel.outputFolderBrowseRequested.connect(
            self.outputFolderBrowseRequested.emit
        )
        layout.addWidget(self.configPanel)
        layout.addStretch(1)

    def apply_config(self, namespace: str, data: Dict[str, object]) -> None:
        if namespace != "image":
            return

        self.configPanel.apply_config(data)

    def set_output_folder(self, folder: Path | str | None) -> None:
        self.configPanel.set_output_folder(folder)

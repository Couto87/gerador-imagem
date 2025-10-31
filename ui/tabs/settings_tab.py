"""Settings tab displaying persistent configuration values."""
from __future__ import annotations

from typing import Dict

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

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
        layout.addWidget(self.configPanel)

        destination_title = QLabel("Destino das exportações")
        destination_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        destination_title.setObjectName("TabTitle")
        layout.addWidget(destination_title)

        folder_row = QHBoxLayout()
        folder_row.setSpacing(8)

        self.outputFolderLabel = QLabel("Nenhuma pasta selecionada.")
        self.outputFolderLabel.setWordWrap(True)
        folder_row.addWidget(self.outputFolderLabel, 1)

        browse_button = QPushButton("Selecionar pasta…")
        browse_button.clicked.connect(self.outputFolderBrowseRequested.emit)
        folder_row.addWidget(browse_button)

        layout.addLayout(folder_row)
        layout.addStretch(1)

    def apply_config(self, namespace: str, data: Dict[str, object]) -> None:
        if namespace != "image":
            return

        self.configPanel.apply_config(data)

    def set_output_folder(self, folder: Path | str | None) -> None:
        if folder is None:
            self.outputFolderLabel.setText("Nenhuma pasta selecionada.")
        else:
            self.outputFolderLabel.setText(str(folder))

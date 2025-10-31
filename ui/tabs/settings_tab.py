"""Settings tab displaying persistent configuration values."""
from __future__ import annotations

from typing import Dict

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config_panel import ConfigPanel


class SettingsTab(QWidget):
    """Aggregate generation options and the currently saved configuration."""

    optionChanged = pyqtSignal(str, str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(16)

        self.configPanel = ConfigPanel()
        self.configPanel.optionChanged.connect(self.optionChanged)
        layout.addWidget(self.configPanel)

        title = QLabel("Configuração atual")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        title.setObjectName("TabTitle")
        layout.addWidget(title)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Chave", "Valor"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)

    def apply_config(self, namespace: str, data: Dict[str, object]) -> None:
        if namespace != "image":
            return

        self.configPanel.apply_config(data)

        self.table.setRowCount(0)
        for key, value in data.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(key)))
            self.table.setItem(row, 1, QTableWidgetItem(str(value)))

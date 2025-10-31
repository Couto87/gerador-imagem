"""Settings tab displaying persistent configuration values."""
from __future__ import annotations

from typing import Dict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget


class SettingsTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

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
        self.table.setRowCount(0)
        for key, value in data.items():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(str(key)))
            self.table.setItem(row, 1, QTableWidgetItem(str(value)))

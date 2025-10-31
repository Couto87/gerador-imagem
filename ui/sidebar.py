"""Sidebar widget with folder navigation."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class Sidebar(QWidget):
    """Display available folders and allow the user to pick one."""

    folderSelected = pyqtSignal(Path)
    browseRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Bibliotecas")
        title.setObjectName("SidebarTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(title)

        self.folderList = QListWidget()
        self.folderList.setObjectName("SidebarList")
        self.folderList.itemActivated.connect(self._emit_selection)
        self.folderList.itemClicked.connect(self._emit_selection)
        layout.addWidget(self.folderList, 1)

        self.browseButton = QPushButton("Escolher pasta…")
        self.browseButton.clicked.connect(self.browseRequested.emit)
        layout.addWidget(self.browseButton)

    def set_directories(self, folders: Iterable[Path]) -> None:
        self.folderList.clear()
        for path in folders:
            item = QListWidgetItem(path.name or str(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            self.folderList.addItem(item)

    def select_folder(self, folder: Path) -> None:
        for index in range(self.folderList.count()):
            item = self.folderList.item(index)
            if item.data(Qt.ItemDataRole.UserRole) == folder:
                self.folderList.setCurrentItem(item)
                break

    def _emit_selection(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, Path):
            self.folderSelected.emit(data)

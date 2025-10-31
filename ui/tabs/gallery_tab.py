"""Gallery tab that lists the images found in the current folder."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class GalleryTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Galeria da pasta selecionada")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        title.setObjectName("TabTitle")
        layout.addWidget(title)

        self.listWidget = QListWidget()
        self.listWidget.setObjectName("GalleryList")
        layout.addWidget(self.listWidget, 1)

    def set_images(self, images: Iterable[Path]) -> None:
        self.listWidget.clear()
        for image in images:
            item = QListWidgetItem(image.name)
            item.setToolTip(str(image))
            self.listWidget.addItem(item)

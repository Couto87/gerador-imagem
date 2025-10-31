"""Panel with generation options."""
from __future__ import annotations

from typing import Dict, Iterable

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ConfigPanel(QWidget):
    """Expose controls for generation parameters."""

    optionChanged = pyqtSignal(str, str, object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Configurações de geração"))

        self.sizeCombo = self._create_combo(
            [
                "1080 × 1350 (Retrato)",
                "1024 × 1024 (Quadrado)",
                "1920 × 1080 (Paisagem)",
                "1080 × 1920 (Vertical/Short)",
            ]
        )
        self.resolutionCombo = self._create_combo(["Baixa", "Média", "Alta"])
        self.typeCombo = self._create_combo(["Imagem", "Música"])

        quantityBox = QSpinBox()
        quantityBox.setRange(1, 10)
        quantityBox.setValue(1)
        quantityBox.valueChanged.connect(
            lambda value: self.optionChanged.emit("image", "quantity", value)
        )
        self.quantityBox = quantityBox

        form = QFormLayout()
        form.addRow("Tamanho", self.sizeCombo)
        form.addRow("Resolução", self.resolutionCombo)
        form.addRow("Quantidade", quantityBox)
        form.addRow("Tipo", self.typeCombo)

        group = QGroupBox()
        group.setLayout(form)
        layout.addWidget(group)
        layout.addStretch(1)

        self.sizeCombo.currentTextChanged.connect(
            lambda text: self.optionChanged.emit("image", "size", text)
        )
        self.resolutionCombo.currentTextChanged.connect(
            lambda text: self.optionChanged.emit("image", "resolution", text)
        )
        self.typeCombo.currentTextChanged.connect(
            lambda text: self.optionChanged.emit("image", "type", text)
        )

    def _create_combo(self, items: Iterable[str]) -> QComboBox:
        combo = QComboBox()
        for item in items:
            combo.addItem(item)
        return combo

    def apply_config(self, data: Dict[str, object]) -> None:
        size = data.get("size")
        resolution = data.get("resolution")
        quantity = data.get("quantity")
        item_type = data.get("type")

        if isinstance(size, str):
            index = self.sizeCombo.findText(size)
            if index >= 0:
                self.sizeCombo.setCurrentIndex(index)

        if isinstance(resolution, str):
            index = self.resolutionCombo.findText(resolution)
            if index >= 0:
                self.resolutionCombo.setCurrentIndex(index)

        if isinstance(quantity, int):
            self.quantityBox.setValue(quantity)

        if isinstance(item_type, str):
            index = self.typeCombo.findText(item_type)
            if index >= 0:
                self.typeCombo.setCurrentIndex(index)

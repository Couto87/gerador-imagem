"""Panel with generation options."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QComboBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ConfigPanel(QWidget):
    """Expose controls for generation parameters."""

    optionChanged = pyqtSignal(str, str, object)
    outputFolderBrowseRequested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._destination_path: str | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        control_height = 36

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
        quantityBox.setMinimumHeight(control_height)
        quantityBox.setSizePolicy(
            QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        )
        quantityBox.valueChanged.connect(
            lambda value: self.optionChanged.emit("image", "quantity", value)
        )
        self.quantityBox = quantityBox

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        form.setFormAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow("Tamanho", self.sizeCombo)
        form.addRow("Resolução", self.resolutionCombo)
        form.addRow("Quantidade", quantityBox)
        form.addRow("Tipo", self.typeCombo)

        destination_container = QWidget()
        destination_layout = QHBoxLayout(destination_container)
        destination_layout.setContentsMargins(0, 0, 0, 0)
        destination_layout.setSpacing(8)

        destination_label = QLabel("Nenhuma pasta selecionada.")
        destination_label.setWordWrap(True)
        destination_label.setAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        destination_label.setMinimumHeight(control_height)
        destination_layout.addWidget(destination_label, 1)

        browse_button = QPushButton("Selecionar…")
        browse_button.setMinimumHeight(control_height)
        browse_button.clicked.connect(self.outputFolderBrowseRequested.emit)
        destination_layout.addWidget(browse_button)

        self.destinationLabel = destination_label
        self.destinationButton = browse_button

        form.addRow("Destino", destination_container)

        layout.addLayout(form)
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

        for widget in (self.sizeCombo, self.resolutionCombo, self.typeCombo):
            widget.setMinimumHeight(control_height)
            widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
            widget.setSizePolicy(
                QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
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

    def set_output_folder(self, folder: Path | str | None) -> None:
        if folder is None:
            self._destination_path = None
            self.destinationLabel.setText("Nenhuma pasta selecionada.")
            return

        text = str(folder)
        self._destination_path = text
        metrics = self.destinationLabel.fontMetrics()
        available_width = max(0, self.destinationLabel.width())
        if available_width:
            elided = metrics.elidedText(text, Qt.TextElideMode.ElideMiddle, available_width)
            self.destinationLabel.setText(elided)
        else:
            self.destinationLabel.setText(text)

    def resizeEvent(self, event):  # type: ignore[override]
        super().resizeEvent(event)
        if self._destination_path is None:
            self.destinationLabel.setText("Nenhuma pasta selecionada.")
        else:
            self.set_output_folder(self._destination_path)

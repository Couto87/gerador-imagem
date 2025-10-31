"""Home tab with quick actions."""
from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class HomeTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Bem-vindo ao Image Studio IA")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        title.setObjectName("TabTitle")
        layout.addWidget(title)

        description = QLabel(
            "Organize suas pastas, configure tamanhos e resoluções e gere novos conteúdos "
            "com apenas alguns cliques. Selecione uma pasta para começar."
        )
        description.setWordWrap(True)
        layout.addWidget(description)
        layout.addStretch(1)

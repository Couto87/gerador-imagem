"""Main application window assembly."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .config_panel import ConfigPanel
from .sidebar import Sidebar
from .tabs.gallery_tab import GalleryTab
from .tabs.home_tab import HomeTab
from .tabs.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    """Compose the primary UI widgets and expose high level helpers."""

    promptSubmitted = pyqtSignal(str)
    browseFolderRequested = pyqtSignal()
    configRequested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image Studio IA")
        self.resize(1280, 768)
        self._setup_ui()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.topbar = self._create_topbar()
        root.addWidget(self.topbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        root.addWidget(splitter, 1)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(16, 16, 12, 16)
        left_layout.setSpacing(12)

        self.leftViewer = self._create_viewer("Pasta selecionada")
        left_layout.addWidget(self.leftViewer)

        self.sidebar = Sidebar()
        self.sidebar.folderSelected.connect(self._on_folder_selected)
        self.sidebar.browseRequested.connect(self.browseFolderRequested.emit)
        left_layout.addWidget(self.sidebar, 1)

        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 16, 16, 16)
        right_layout.setSpacing(12)

        self.rightViewer = self._create_viewer("Saída das imagens geradas")
        right_layout.addWidget(self.rightViewer)

        self.configPanel = ConfigPanel()
        right_layout.addWidget(self.configPanel)

        self.tabs = QTabWidget()
        self.homeTab = HomeTab()
        self.galleryTab = GalleryTab()
        self.settingsTab = SettingsTab()
        self.tabs.addTab(self.homeTab, "Início")
        self.tabs.addTab(self.galleryTab, "Galeria")
        self.tabs.addTab(self.settingsTab, "Configurações")
        right_layout.addWidget(self.tabs, 1)

        composer = self._create_composer()
        right_layout.addWidget(composer)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

    def _create_topbar(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("TopBar")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        self.brandLabel = QLabel("Image Studio IA")
        self.brandLabel.setObjectName("BrandLabel")
        layout.addWidget(self.brandLabel)

        self.pathLabel = QLabel("Pasta: —")
        self.pathLabel.setObjectName("PathLabel")
        layout.addWidget(self.pathLabel, 1)

        self.configButton = QPushButton("Configurações")
        self.configButton.clicked.connect(self.configRequested.emit)
        layout.addWidget(self.configButton)
        return frame

    def _create_viewer(self, title: str) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Viewer")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        caption = QLabel(title)
        caption.setObjectName("ViewerTitle")
        layout.addWidget(caption)

        placeholder = QLabel("Selecione uma pasta para visualizar suas imagens")
        placeholder.setWordWrap(True)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setObjectName("ViewerPlaceholder")
        layout.addWidget(placeholder, 1)

        frame.captionLabel = caption  # type: ignore[attr-defined]
        frame.placeholderLabel = placeholder  # type: ignore[attr-defined]
        return frame

    def _create_composer(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Composer")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        label = QLabel("Prompt ou instruções")
        layout.addWidget(label)

        self.promptEdit = QTextEdit()
        self.promptEdit.setPlaceholderText("Descreva aqui o que deseja gerar…")
        layout.addWidget(self.promptEdit, 1)

        actions = QHBoxLayout()
        generate = QPushButton("Gerar conteúdo")
        generate.clicked.connect(self._emit_prompt)
        actions.addStretch(1)
        actions.addWidget(generate)
        layout.addLayout(actions)
        return frame

    def _emit_prompt(self) -> None:
        text = self.promptEdit.toPlainText().strip()
        if text:
            self.promptSubmitted.emit(text)

    def _on_folder_selected(self, folder: Path) -> None:
        self.set_path_label(folder)

    # Public helpers -----------------------------------------------------
    def set_path_label(self, path: Path) -> None:
        self.pathLabel.setText(f"Pasta: {path}")

    def set_directories(self, directories: Iterable[Path]) -> None:
        self.sidebar.set_directories(directories)

    def select_directory(self, directory: Path) -> None:
        self.sidebar.select_folder(directory)
        self.set_path_label(directory)

    def set_gallery_images(self, images: Iterable[Path]) -> None:
        self.galleryTab.set_images(images)

    def apply_config(self, namespace: str, data: dict[str, object]) -> None:
        if namespace == "image":
            self.configPanel.apply_config(data)
            self.settingsTab.apply_config(namespace, data)

    def update_viewer(self, viewer: QWidget, *, title: str | None = None, message: str | None = None) -> None:
        caption = getattr(viewer, "captionLabel", None)
        placeholder = getattr(viewer, "placeholderLabel", None)
        if title and caption is not None:
            caption.setText(title)
        if message and placeholder is not None:
            placeholder.setText(message)

    def update_left_viewer(self, title: str, message: str) -> None:
        self.update_viewer(self.leftViewer, title=title, message=message)

    def update_right_viewer(self, title: str, message: str) -> None:
        self.update_viewer(self.rightViewer, title=title, message=message)

    def prompt_text(self) -> str:
        return self.promptEdit.toPlainText()

    def clear_prompt(self) -> None:
        self.promptEdit.clear()

    def open_folder_dialog(self, start_dir: Path) -> Path | None:
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setDirectory(str(start_dir))
        if dialog.exec():
            selected = dialog.selectedFiles()
            if selected:
                return Path(selected[0])
        return None

"""Main application window assembly."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListView,
    QMainWindow,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSlider,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .config_panel import ConfigPanel
from .tabs.home_tab import HomeTab
from .tabs.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    """Compose the primary UI widgets and expose high level helpers."""

    promptSubmitted = pyqtSignal(str)
    browseFolderRequested = pyqtSignal()
    outputBrowseRequested = pyqtSignal()
    configRequested = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image Studio IA")
        self.resize(1280, 768)
        self._image_icon_size = 128
        self._text_tile_width = 220
        self._selected_paths: set[str] = set()
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

        self.sourcePanel = self._create_source_panel()
        left_layout.addWidget(self.sourcePanel, 1)
        self._apply_thumbnail_size(self._image_icon_size)

        splitter.addWidget(left)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(12, 16, 16, 16)
        right_layout.setSpacing(12)

        self.rightViewer = self._create_viewer(
            "Saída das imagens geradas",
            browse_text="Selecionar pasta de saída…",
            browse_slot=self.outputBrowseRequested.emit,
            placeholder_text="Selecione uma pasta para salvar suas imagens geradas",
        )
        right_layout.addWidget(self.rightViewer)

        self.configPanel = ConfigPanel()
        right_layout.addWidget(self.configPanel)

        self.tabs = QTabWidget()
        self.homeTab = HomeTab()
        self.settingsTab = SettingsTab()
        self.tabs.addTab(self.homeTab, "Início")
        self.selectedTab = self._create_selected_tab()
        self.tabs.addTab(self.selectedTab, "Selecionados")
        self.tabs.addTab(self.settingsTab, "Configurações")
        right_layout.addWidget(self.tabs, 1)

        composer = self._create_composer()
        right_layout.addWidget(composer)

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        right_layout.setStretch(0, 3)
        right_layout.setStretch(1, 1)
        right_layout.setStretch(2, 2)
        right_layout.setStretch(3, 1)

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

    def _create_viewer(
        self,
        title: str,
        *,
        browse_text: str | None = None,
        browse_slot: Callable[[], None] | None = None,
        placeholder_text: str = "Selecione uma pasta para visualizar suas imagens",
    ) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Viewer")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        caption = QLabel(title)
        caption.setObjectName("ViewerTitle")
        layout.addWidget(caption)

        if browse_text and browse_slot:
            browse_button = QPushButton(browse_text)
            browse_button.clicked.connect(browse_slot)
            layout.addWidget(browse_button)

        path_label = QLabel("Nenhuma pasta selecionada.")
        path_label.setObjectName("ViewerPath")
        path_label.setWordWrap(True)
        layout.addWidget(path_label)

        placeholder = QLabel(placeholder_text)
        placeholder.setWordWrap(True)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setObjectName("ViewerPlaceholder")
        layout.addWidget(placeholder, 1)

        frame.captionLabel = caption  # type: ignore[attr-defined]
        frame.placeholderLabel = placeholder  # type: ignore[attr-defined]
        frame.pathLabel = path_label  # type: ignore[attr-defined]
        return frame

    def _create_source_panel(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("SourcePanel")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Arquivos da pasta selecionada")
        title.setObjectName("SourceTitle")
        layout.addWidget(title)

        browse_button = QPushButton("Escolher pasta…")
        browse_button.clicked.connect(self.browseFolderRequested.emit)
        layout.addWidget(browse_button)

        path_label = QLabel("Nenhuma pasta selecionada.")
        path_label.setWordWrap(True)
        path_label.setObjectName("SourcePath")
        layout.addWidget(path_label)

        status = QLabel("Os arquivos compatíveis serão exibidos aqui.")
        status.setWordWrap(True)
        status.setObjectName("SourceStatus")
        layout.addWidget(status)

        slider_row = QHBoxLayout()
        slider_caption = QLabel("Tamanho das miniaturas")
        slider_row.addWidget(slider_caption)
        thumbnail_slider = QSlider(Qt.Orientation.Horizontal)
        thumbnail_slider.setObjectName("SourceThumbnailSlider")
        thumbnail_slider.setRange(80, 224)
        thumbnail_slider.setSingleStep(8)
        thumbnail_slider.setPageStep(16)
        thumbnail_slider.setValue(self._image_icon_size)
        thumbnail_slider.valueChanged.connect(self._update_thumbnail_size)
        slider_row.addWidget(thumbnail_slider, 1)
        layout.addLayout(slider_row)

        text_list = QListWidget()
        text_list.setObjectName("SourceTextList")
        text_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        text_list.setViewMode(QListView.ViewMode.IconMode)
        text_list.setResizeMode(QListView.ResizeMode.Adjust)
        text_list.setMovement(QListView.Movement.Static)
        text_list.setWrapping(True)
        text_list.setSpacing(4)
        text_list.setWordWrap(True)
        text_list.setGridSize(QSize(self._text_tile_width, 52))
        layout.addWidget(text_list)

        image_list = QListWidget()
        image_list.setObjectName("SourceImageList")
        image_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        image_list.setViewMode(QListView.ViewMode.IconMode)
        image_list.setResizeMode(QListView.ResizeMode.Adjust)
        image_list.setMovement(QListView.Movement.Static)
        image_list.setWrapping(True)
        image_list.setSpacing(8)
        image_list.setWordWrap(True)
        image_list.setUniformItemSizes(False)
        layout.addWidget(image_list, 1)

        frame.thumbnailSlider = thumbnail_slider  # type: ignore[attr-defined]
        frame.textList = text_list  # type: ignore[attr-defined]
        frame.imageList = image_list  # type: ignore[attr-defined]

        text_list.itemDoubleClicked.connect(self._handle_source_double_click)
        image_list.itemDoubleClicked.connect(self._handle_source_double_click)

        frame.pathLabel = path_label  # type: ignore[attr-defined]
        frame.statusLabel = status  # type: ignore[attr-defined]

        return frame

    def _create_selected_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        description = QLabel(
            "Arquivos selecionados a partir da pasta de origem. Dê um clique duplo para removê-los."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        list_widget = QListWidget()
        list_widget.setObjectName("SelectedFileList")
        list_widget.setViewMode(QListView.ViewMode.IconMode)
        list_widget.setResizeMode(QListView.ResizeMode.Adjust)
        list_widget.setMovement(QListView.Movement.Static)
        list_widget.setWrapping(True)
        list_widget.setSpacing(8)
        list_widget.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        list_widget.setIconSize(QSize(self._image_icon_size, self._image_icon_size))
        list_widget.setGridSize(QSize(self._image_icon_size + 40, self._image_icon_size + 56))
        layout.addWidget(list_widget, 1)

        remove_button = QPushButton("Remover selecionados")
        remove_button.clicked.connect(self._remove_selected_items)
        layout.addWidget(remove_button)

        list_widget.itemDoubleClicked.connect(self._remove_single_selected_item)

        widget.listWidget = list_widget  # type: ignore[attr-defined]
        widget.removeButton = remove_button  # type: ignore[attr-defined]
        return widget

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

    # Public helpers -----------------------------------------------------
    def set_path_label(self, path: Path) -> None:
        self.pathLabel.setText(f"Pasta: {path}")

    def set_source_folder(self, folder: Path) -> None:
        path_label = getattr(self.sourcePanel, "pathLabel", None)
        if path_label is not None:
            path_label.setText(str(folder))

    def set_source_files(self, files: Iterable[Path]) -> None:
        image_list: QListWidget | None = getattr(self.sourcePanel, "imageList", None)
        text_list: QListWidget | None = getattr(self.sourcePanel, "textList", None)
        status_label: QLabel | None = getattr(self.sourcePanel, "statusLabel", None)
        if image_list is None or text_list is None:
            return

        image_list.clear()
        text_list.clear()

        image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        text_extensions = {".txt"}
        image_count = 0
        text_count = 0

        thumbnail_size = image_list.iconSize()
        for file in files:
            suffix = file.suffix.lower()
            full_path = str(file)
            item = QListWidgetItem(file.name)
            item.setToolTip(full_path)
            item.setData(Qt.ItemDataRole.UserRole, file.name)
            item.setData(Qt.ItemDataRole.UserRole + 1, full_path)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            if suffix in image_extensions:
                pixmap = QPixmap(str(file))
                if not pixmap.isNull():
                    thumbnail = pixmap.scaled(
                        thumbnail_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    item.setIcon(QIcon(thumbnail))
                image_list.addItem(item)
                image_count += 1
            elif suffix in text_extensions:
                text_list.addItem(item)
                text_count += 1

        image_list.setEnabled(image_count > 0)
        text_list.setEnabled(text_count > 0)

        self._refresh_image_captions()
        self._refresh_text_captions()
        self._refresh_selected_captions()

        if status_label is not None:
            if image_count == 0 and text_count == 0:
                status_label.setText("Nenhum arquivo compatível encontrado.")
            else:
                parts: list[str] = []
                if image_count:
                    parts.append(
                        f"{image_count} imagem{'s' if image_count != 1 else ''} encontrada"
                    )
                if text_count:
                    parts.append(
                        f"{text_count} arquivo{'s' if text_count != 1 else ''} de texto"
                    )
                status_label.setText(" • ".join(parts))

    def _update_thumbnail_size(self, value: int) -> None:
        self._apply_thumbnail_size(value)
        self._refresh_image_captions()
        self._refresh_selected_captions()

    def _apply_thumbnail_size(self, size: int) -> None:
        self._image_icon_size = size
        icon_extent = QSize(size, size)
        image_list: QListWidget | None = getattr(self.sourcePanel, "imageList", None)
        slider: QSlider | None = getattr(self.sourcePanel, "thumbnailSlider", None)
        selected_tab = getattr(self, "selectedTab", None)
        selected_list: QListWidget | None = (
            getattr(selected_tab, "listWidget", None) if selected_tab is not None else None
        )
        if image_list is None:
            if slider is not None and slider.value() != size:
                slider.blockSignals(True)
                slider.setValue(size)
                slider.blockSignals(False)
            return
        image_list.setIconSize(icon_extent)
        grid_width = size + 40
        grid_height = size + 56
        image_list.setGridSize(QSize(grid_width, grid_height))
        if selected_list is not None:
            selected_list.setIconSize(icon_extent)
            selected_list.setGridSize(QSize(grid_width, grid_height))
            selected_list.setSpacing(image_list.spacing())
        if slider is not None and slider.value() != size:
            slider.blockSignals(True)
            slider.setValue(size)
            slider.blockSignals(False)

    def _refresh_image_captions(self) -> None:
        image_list: QListWidget | None = getattr(self.sourcePanel, "imageList", None)
        if image_list is None:
            return
        available_width = image_list.gridSize().width() - 24
        self._refresh_list_labels(image_list, available_width)

    def _refresh_text_captions(self) -> None:
        text_list: QListWidget | None = getattr(self.sourcePanel, "textList", None)
        if text_list is None:
            return
        available_width = text_list.gridSize().width() - 12
        self._refresh_list_labels(text_list, available_width)

    def _refresh_selected_captions(self) -> None:
        selected_tab = getattr(self, "selectedTab", None)
        selected_list: QListWidget | None = (
            getattr(selected_tab, "listWidget", None) if selected_tab is not None else None
        )
        if selected_list is None:
            return
        available_width = selected_list.gridSize().width() - 24
        self._refresh_list_labels(selected_list, available_width)

    def _refresh_list_labels(self, list_widget: QListWidget, width: int) -> None:
        if width <= 0:
            return
        metrics = list_widget.fontMetrics()
        for index in range(list_widget.count()):
            item = list_widget.item(index)
            original = item.data(Qt.ItemDataRole.UserRole)
            if original is None:
                original = item.text()
            elided = metrics.elidedText(str(original), Qt.TextElideMode.ElideMiddle, width)
            item.setText(elided)

    def _handle_source_double_click(self, item: QListWidgetItem) -> None:
        path_data = item.data(Qt.ItemDataRole.UserRole + 1)
        if not path_data:
            return
        self._add_selected_file(Path(str(path_data)))

    def _add_selected_file(self, path: Path) -> None:
        selected_tab = getattr(self, "selectedTab", None)
        selected_list: QListWidget | None = (
            getattr(selected_tab, "listWidget", None) if selected_tab is not None else None
        )
        if selected_list is None:
            return
        path_str = str(path)
        if path_str in self._selected_paths:
            self.tabs.setCurrentWidget(self.selectedTab)
            return

        item = QListWidgetItem(path.name)
        item.setData(Qt.ItemDataRole.UserRole, path.name)
        item.setData(Qt.ItemDataRole.UserRole + 1, path_str)
        item.setToolTip(path_str)
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)

        image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
        if path.suffix.lower() in image_extensions:
            pixmap = QPixmap(path_str)
            if not pixmap.isNull():
                thumbnail = pixmap.scaled(
                    selected_list.iconSize(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                item.setIcon(QIcon(thumbnail))

        selected_list.addItem(item)
        self._selected_paths.add(path_str)
        self._refresh_selected_captions()
        self.tabs.setCurrentWidget(self.selectedTab)

    def _remove_selected_items(self) -> None:
        selected_tab = getattr(self, "selectedTab", None)
        selected_list: QListWidget | None = (
            getattr(selected_tab, "listWidget", None) if selected_tab is not None else None
        )
        if selected_list is None:
            return
        for item in selected_list.selectedItems():
            self._remove_selected_item(item)

    def _remove_single_selected_item(self, item: QListWidgetItem) -> None:
        self._remove_selected_item(item)

    def _remove_selected_item(self, item: QListWidgetItem) -> None:
        selected_tab = getattr(self, "selectedTab", None)
        selected_list: QListWidget | None = (
            getattr(selected_tab, "listWidget", None) if selected_tab is not None else None
        )
        if selected_list is None:
            return
        path_data = item.data(Qt.ItemDataRole.UserRole + 1)
        if path_data:
            path_str = str(path_data)
            if path_str in self._selected_paths:
                self._selected_paths.remove(path_str)
        selected_list.takeItem(selected_list.row(item))
        self._refresh_selected_captions()

    def update_source_status(self, message: str) -> None:
        status_label = getattr(self.sourcePanel, "statusLabel", None)
        if status_label is not None:
            status_label.setText(message)

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
    def update_right_viewer(self, title: str, message: str) -> None:
        self.update_viewer(self.rightViewer, title=title, message=message)

    def set_output_folder(self, folder: Path) -> None:
        path_label = getattr(self.rightViewer, "pathLabel", None)
        if path_label is not None:
            path_label.setText(str(folder))

    def clear_output_folder(self) -> None:
        path_label = getattr(self.rightViewer, "pathLabel", None)
        if path_label is not None:
            path_label.setText("Nenhuma pasta selecionada.")

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

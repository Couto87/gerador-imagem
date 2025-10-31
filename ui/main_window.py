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

from .tabs.home_tab import HomeTab
from .tabs.settings_tab import SettingsTab


class MainWindow(QMainWindow):
    """Compose the primary UI widgets and expose high level helpers."""

    promptSubmitted = pyqtSignal(str)
    browseFolderRequested = pyqtSignal()
    configRequested = pyqtSignal()

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    TEXT_EXTENSIONS = {".txt"}

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
        self.sourcePanel = self._create_file_panel(
            title="Arquivos da pasta selecionada",
            browse_text="Escolher pasta…",
            browse_slot=self.browseFolderRequested.emit,
            status_text="Os arquivos compatíveis serão exibidos aqui.",
            object_name="SourcePanel",
            enable_selection=True,
        )
        left_layout.addWidget(self.sourcePanel, 1)
        splitter.addWidget(left)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.setContentsMargins(12, 16, 12, 16)
        center_layout.setSpacing(12)

        self.tabs = QTabWidget()
        self.homeTab = HomeTab()
        self.settingsTab = SettingsTab()
        self.tabs.addTab(self.homeTab, "Início")
        self.selectedTab = self._create_selected_tab()
        self.tabs.addTab(self.selectedTab, "Selecionados")
        self.tabs.addTab(self.settingsTab, "Configurações")
        center_layout.addWidget(self.tabs, 1)

        composer = self._create_composer()
        center_layout.addWidget(composer)

        center_layout.setStretch(0, 3)
        center_layout.setStretch(1, 2)

        splitter.addWidget(center)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        self._apply_thumbnail_size(self._image_icon_size)

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

    def _create_file_panel(
        self,
        *,
        title: str,
        browse_text: str,
        browse_slot: Callable[[], None],
        status_text: str,
        object_name: str,
        enable_selection: bool,
    ) -> QWidget:
        frame = QFrame()
        frame.setObjectName(object_name)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName(f"{object_name}Title")
        layout.addWidget(title_label)

        browse_button = QPushButton(browse_text)
        browse_button.clicked.connect(browse_slot)
        layout.addWidget(browse_button)

        path_label = QLabel("Nenhuma pasta selecionada.")
        path_label.setWordWrap(True)
        path_label.setObjectName(f"{object_name}Path")
        layout.addWidget(path_label)

        status = QLabel(status_text)
        status.setWordWrap(True)
        status.setObjectName(f"{object_name}Status")
        layout.addWidget(status)

        slider_row = QHBoxLayout()
        slider_caption = QLabel("Tamanho das miniaturas")
        slider_row.addWidget(slider_caption)
        thumbnail_slider = QSlider(Qt.Orientation.Horizontal)
        thumbnail_slider.setObjectName(f"{object_name}ThumbnailSlider")
        thumbnail_slider.setRange(80, 224)
        thumbnail_slider.setSingleStep(8)
        thumbnail_slider.setPageStep(16)
        thumbnail_slider.setValue(self._image_icon_size)
        thumbnail_slider.valueChanged.connect(self._update_thumbnail_size)
        slider_row.addWidget(thumbnail_slider, 1)
        layout.addLayout(slider_row)

        text_list = QListWidget()
        text_list.setObjectName(f"{object_name}TextList")
        text_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        text_list.setViewMode(QListView.ViewMode.IconMode)
        text_list.setResizeMode(QListView.ResizeMode.Adjust)
        text_list.setMovement(QListView.Movement.Static)
        text_list.setWrapping(True)
        text_list.setSpacing(2)
        text_list.setWordWrap(True)
        text_list.setGridSize(QSize(self._text_tile_width, 38))
        layout.addWidget(text_list)

        image_list = QListWidget()
        image_list.setObjectName(f"{object_name}ImageList")
        image_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        image_list.setViewMode(QListView.ViewMode.IconMode)
        image_list.setResizeMode(QListView.ResizeMode.Adjust)
        image_list.setMovement(QListView.Movement.Static)
        image_list.setWrapping(True)
        image_list.setSpacing(4)
        image_list.setWordWrap(True)
        image_list.setUniformItemSizes(False)
        layout.addWidget(image_list, 1)

        frame.thumbnailSlider = thumbnail_slider  # type: ignore[attr-defined]
        frame.textList = text_list  # type: ignore[attr-defined]
        frame.imageList = image_list  # type: ignore[attr-defined]
        frame.pathLabel = path_label  # type: ignore[attr-defined]
        frame.statusLabel = status  # type: ignore[attr-defined]

        if enable_selection:
            text_list.itemDoubleClicked.connect(self._handle_source_double_click)
            image_list.itemDoubleClicked.connect(self._handle_source_double_click)

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

        text_list = QListWidget()
        text_list.setObjectName("SelectedTextList")
        text_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        text_list.setViewMode(QListView.ViewMode.IconMode)
        text_list.setResizeMode(QListView.ResizeMode.Adjust)
        text_list.setMovement(QListView.Movement.Static)
        text_list.setWrapping(True)
        text_list.setSpacing(2)
        text_list.setWordWrap(True)
        text_list.setGridSize(QSize(self._text_tile_width, 38))
        layout.addWidget(text_list)

        image_list = QListWidget()
        image_list.setObjectName("SelectedImageList")
        image_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        image_list.setViewMode(QListView.ViewMode.IconMode)
        image_list.setResizeMode(QListView.ResizeMode.Adjust)
        image_list.setMovement(QListView.Movement.Static)
        image_list.setWrapping(True)
        image_list.setSpacing(4)
        image_list.setWordWrap(True)
        image_list.setIconSize(QSize(self._image_icon_size, self._image_icon_size))
        image_list.setGridSize(QSize(self._image_icon_size + 20, self._image_icon_size + 32))
        layout.addWidget(image_list, 1)

        remove_button = QPushButton("Remover selecionados")
        remove_button.clicked.connect(self._remove_selected_items)
        layout.addWidget(remove_button)

        text_list.itemDoubleClicked.connect(
            lambda item, list_widget=text_list: self._remove_selected_item(item, list_widget)
        )
        image_list.itemDoubleClicked.connect(
            lambda item, list_widget=image_list: self._remove_selected_item(item, list_widget)
        )

        widget.textList = text_list  # type: ignore[attr-defined]
        widget.imageList = image_list  # type: ignore[attr-defined]
        widget.removeButton = remove_button  # type: ignore[attr-defined]
        return widget

    def _create_composer(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Composer")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

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
        status_label: QLabel | None = getattr(self.sourcePanel, "statusLabel", None)
        image_count, text_count = self._populate_panel_files(self.sourcePanel, files)

        self._refresh_image_captions(self.sourcePanel)
        self._refresh_text_captions(self.sourcePanel)
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

    def _populate_panel_files(
        self, panel: QWidget | None, files: Iterable[Path]
    ) -> tuple[int, int]:
        image_list: QListWidget | None = getattr(panel, "imageList", None) if panel else None
        text_list: QListWidget | None = getattr(panel, "textList", None) if panel else None
        if image_list is None or text_list is None:
            return (0, 0)

        image_list.clear()
        text_list.clear()

        thumbnail_size = image_list.iconSize()
        image_count = 0
        text_count = 0

        for file in files:
            suffix = file.suffix.lower()
            full_path = str(file)
            item = QListWidgetItem(file.name)
            item.setToolTip(full_path)
            item.setData(Qt.ItemDataRole.UserRole, file.name)
            item.setData(Qt.ItemDataRole.UserRole + 1, full_path)
            item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            if suffix in self.IMAGE_EXTENSIONS:
                pixmap = QPixmap(full_path)
                if not pixmap.isNull():
                    thumbnail = pixmap.scaled(
                        thumbnail_size,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    item.setIcon(QIcon(thumbnail))
                image_list.addItem(item)
                image_count += 1
            elif suffix in self.TEXT_EXTENSIONS:
                text_list.addItem(item)
                text_count += 1

        image_list.setEnabled(image_count > 0)
        text_list.setEnabled(text_count > 0)
        return image_count, text_count

    def _update_thumbnail_size(self, value: int) -> None:
        self._apply_thumbnail_size(value)
        self._refresh_image_captions(self.sourcePanel)
        self._refresh_selected_captions()

    def _apply_thumbnail_size(self, size: int) -> None:
        self._image_icon_size = size
        icon_extent = QSize(size, size)
        grid_width = size + 20
        grid_height = size + 32

        source_panel = getattr(self, "sourcePanel", None)
        if source_panel is not None:
            image_list: QListWidget | None = getattr(source_panel, "imageList", None)
            slider: QSlider | None = getattr(source_panel, "thumbnailSlider", None)
            if image_list is not None:
                image_list.setIconSize(icon_extent)
                image_list.setGridSize(QSize(grid_width, grid_height))
            if slider is not None and slider.value() != size:
                slider.blockSignals(True)
                slider.setValue(size)
                slider.blockSignals(False)

        selected_tab = getattr(self, "selectedTab", None)
        if selected_tab is not None:
            image_list: QListWidget | None = getattr(selected_tab, "imageList", None)
            if image_list is not None:
                image_list.setIconSize(icon_extent)
                image_list.setGridSize(QSize(grid_width, grid_height))
                source_images: QListWidget | None = (
                    getattr(source_panel, "imageList", None) if source_panel is not None else None
                )
                if source_images is not None:
                    image_list.setSpacing(source_images.spacing())

    def _refresh_image_captions(self, panel: QWidget | None = None) -> None:
        image_list: QListWidget | None = None
        if panel is not None:
            image_list = getattr(panel, "imageList", None)
        elif hasattr(self, "sourcePanel"):
            image_list = getattr(self.sourcePanel, "imageList", None)
        if image_list is None:
            return
        available_width = image_list.gridSize().width() - 24
        self._refresh_list_labels(image_list, available_width)

    def _refresh_text_captions(self, panel: QWidget | None = None) -> None:
        text_list: QListWidget | None = None
        if panel is not None:
            text_list = getattr(panel, "textList", None)
        elif hasattr(self, "sourcePanel"):
            text_list = getattr(self.sourcePanel, "textList", None)
        if text_list is None:
            return
        available_width = text_list.gridSize().width() - 12
        self._refresh_list_labels(text_list, available_width)

    def _refresh_selected_captions(self) -> None:
        selected_tab = getattr(self, "selectedTab", None)
        if selected_tab is None:
            return
        text_list: QListWidget | None = getattr(selected_tab, "textList", None)
        image_list: QListWidget | None = getattr(selected_tab, "imageList", None)
        if text_list is not None:
            available_text_width = text_list.gridSize().width() - 12
            self._refresh_list_labels(text_list, available_text_width)
        if image_list is not None:
            available_image_width = image_list.gridSize().width() - 24
            self._refresh_list_labels(image_list, available_image_width)

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
        if selected_tab is None:
            return
        text_list: QListWidget | None = getattr(selected_tab, "textList", None)
        image_list: QListWidget | None = getattr(selected_tab, "imageList", None)
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
                    image_list.iconSize() if image_list is not None else QSize(self._image_icon_size, self._image_icon_size),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                item.setIcon(QIcon(thumbnail))
            if image_list is not None:
                image_list.addItem(item)
        else:
            if text_list is not None:
                text_list.addItem(item)
        self._selected_paths.add(path_str)
        self._refresh_selected_captions()
        self.tabs.setCurrentWidget(self.selectedTab)

    def _remove_selected_items(self) -> None:
        selected_tab = getattr(self, "selectedTab", None)
        if selected_tab is None:
            return
        text_list: QListWidget | None = getattr(selected_tab, "textList", None)
        image_list: QListWidget | None = getattr(selected_tab, "imageList", None)
        lists = [lst for lst in (text_list, image_list) if lst is not None]
        for lst in lists:
            for item in lst.selectedItems():
                self._remove_selected_item(item, lst)

    def _remove_selected_item(self, item: QListWidgetItem, list_widget: QListWidget) -> None:
        path_data = item.data(Qt.ItemDataRole.UserRole + 1)
        if path_data:
            path_str = str(path_data)
            if path_str in self._selected_paths:
                self._selected_paths.remove(path_str)
        list_widget.takeItem(list_widget.row(item))
        self._refresh_selected_captions()

    def update_source_status(self, message: str) -> None:
        status_label = getattr(self.sourcePanel, "statusLabel", None)
        if status_label is not None:
            status_label.setText(message)

    def apply_config(self, namespace: str, data: dict[str, object]) -> None:
        if namespace == "image":
            self.settingsTab.apply_config(namespace, data)

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

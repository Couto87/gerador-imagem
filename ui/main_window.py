"""Main application window assembly."""
from __future__ import annotations

from pathlib import Path
from math import ceil
from typing import Callable, Iterable

from PyQt6.QtCore import QEvent, QSize, Qt, pyqtSignal
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .config_panel import ConfigPanel


class MainWindow(QMainWindow):
    """Compose the primary UI widgets and expose high level helpers."""

    promptSubmitted = pyqtSignal(str)
    browseFolderRequested = pyqtSignal()

    IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    TEXT_EXTENSIONS = {".txt"}

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Image Studio IA")
        self.resize(1280, 768)
        self._image_icon_size = 128
        self._text_tile_width = 220
        self._selected_paths: set[str] = set()
        self._text_lists: list[QListWidget] = []
        self._max_text_rows = 4
        self._setup_ui()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

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

        self.configPanel = ConfigPanel()
        center_layout.addWidget(self.configPanel)

        self.selectedPanel = self._create_selected_panel()
        self.selectedPanel.setVisible(False)
        center_layout.addWidget(self.selectedPanel)

        composer = self._create_composer()
        center_layout.addWidget(composer)

        center_layout.setStretch(0, 0)
        center_layout.setStretch(1, 1)
        center_layout.setStretch(2, 1)

        splitter.addWidget(center)

        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        self._apply_thumbnail_size(self._image_icon_size)

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
        text_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        text_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(text_list)

        image_list = QListWidget()
        image_list.setObjectName(f"{object_name}ImageList")
        image_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        image_list.setViewMode(QListView.ViewMode.IconMode)
        image_list.setResizeMode(QListView.ResizeMode.Adjust)
        image_list.setMovement(QListView.Movement.Static)
        image_list.setWrapping(True)
        image_list.setSpacing(3)
        image_list.setWordWrap(True)
        image_list.setUniformItemSizes(False)
        layout.addWidget(image_list, 1)

        frame.thumbnailSlider = thumbnail_slider  # type: ignore[attr-defined]
        frame.textList = text_list  # type: ignore[attr-defined]
        frame.imageList = image_list  # type: ignore[attr-defined]
        frame.pathLabel = path_label  # type: ignore[attr-defined]
        frame.statusLabel = status  # type: ignore[attr-defined]

        text_list.setVisible(False)
        text_list.setSizeAdjustPolicy(QListView.SizeAdjustPolicy.AdjustToContents)
        self._register_text_list(text_list)

        if enable_selection:
            text_list.itemDoubleClicked.connect(self._handle_source_double_click)
            image_list.itemDoubleClicked.connect(self._handle_source_double_click)

        return frame

    def _create_selected_panel(self) -> QWidget:
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
        text_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        text_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(text_list)

        image_list = QListWidget()
        image_list.setObjectName("SelectedImageList")
        image_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        image_list.setViewMode(QListView.ViewMode.IconMode)
        image_list.setResizeMode(QListView.ResizeMode.Adjust)
        image_list.setMovement(QListView.Movement.Static)
        image_list.setWrapping(True)
        image_list.setSpacing(3)
        image_list.setWordWrap(True)
        image_list.setIconSize(QSize(self._image_icon_size, self._image_icon_size))
        image_list.setGridSize(
            QSize(
                max(self._image_icon_size + 8, int(self._image_icon_size * 1.05)),
                self._image_icon_size + 28,
            )
        )
        layout.addWidget(image_list, 1)

        remove_button = QPushButton("Remover selecionados")
        remove_button.clicked.connect(self._remove_selected_items)
        remove_button.setEnabled(False)
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

        text_list.setVisible(False)
        text_list.setSizeAdjustPolicy(QListView.SizeAdjustPolicy.AdjustToContents)
        self._register_text_list(text_list)
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
        self._adjust_text_list_height(text_list)
        return image_count, text_count

    def _update_thumbnail_size(self, value: int) -> None:
        self._apply_thumbnail_size(value)
        self._refresh_image_captions(self.sourcePanel)
        self._refresh_selected_captions()

    def _apply_thumbnail_size(self, size: int) -> None:
        self._image_icon_size = size
        icon_extent = QSize(size, size)
        padding = 16
        label_padding = 32
        grid_width = size + padding
        grid_height = size + label_padding

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

        selected_panel = getattr(self, "selectedPanel", None)
        if selected_panel is not None:
            image_list: QListWidget | None = getattr(selected_panel, "imageList", None)
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
        selected_panel = getattr(self, "selectedPanel", None)
        if selected_panel is None:
            return
        text_list: QListWidget | None = getattr(selected_panel, "textList", None)
        image_list: QListWidget | None = getattr(selected_panel, "imageList", None)
        if text_list is not None:
            available_text_width = text_list.gridSize().width() - 12
            self._refresh_list_labels(text_list, available_text_width)
        if image_list is not None:
            available_image_width = image_list.gridSize().width() - 24
            self._refresh_list_labels(image_list, available_image_width)

    def _update_selected_visibility(self) -> None:
        selected_panel = getattr(self, "selectedPanel", None)
        if selected_panel is None:
            return
        text_list: QListWidget | None = getattr(selected_panel, "textList", None)
        image_list: QListWidget | None = getattr(selected_panel, "imageList", None)
        has_items = False
        for lst in (text_list, image_list):
            if lst is not None and lst.count() > 0:
                has_items = True
                break
        selected_panel.setVisible(has_items)
        remove_button: QPushButton | None = getattr(selected_panel, "removeButton", None)
        if remove_button is not None:
            remove_button.setEnabled(has_items)

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
        selected_panel = getattr(self, "selectedPanel", None)
        if selected_panel is None:
            return
        text_list: QListWidget | None = getattr(selected_panel, "textList", None)
        image_list: QListWidget | None = getattr(selected_panel, "imageList", None)
        path_str = str(path)
        if path_str in self._selected_paths:
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
                self._adjust_text_list_height(text_list)
        self._selected_paths.add(path_str)
        self._refresh_selected_captions()
        self._update_selected_visibility()

    def _remove_selected_items(self) -> None:
        selected_panel = getattr(self, "selectedPanel", None)
        if selected_panel is None:
            return
        text_list: QListWidget | None = getattr(selected_panel, "textList", None)
        image_list: QListWidget | None = getattr(selected_panel, "imageList", None)
        lists = [lst for lst in (text_list, image_list) if lst is not None]
        for lst in lists:
            for item in lst.selectedItems():
                self._remove_selected_item(item, lst)
        self._update_selected_visibility()

    def _remove_selected_item(self, item: QListWidgetItem, list_widget: QListWidget) -> None:
        path_data = item.data(Qt.ItemDataRole.UserRole + 1)
        if path_data:
            path_str = str(path_data)
            if path_str in self._selected_paths:
                self._selected_paths.remove(path_str)
        list_widget.takeItem(list_widget.row(item))
        if list_widget in self._text_lists:
            self._adjust_text_list_height(list_widget)
        self._refresh_selected_captions()
        self._update_selected_visibility()

    def update_source_status(self, message: str) -> None:
        status_label = getattr(self.sourcePanel, "statusLabel", None)
        if status_label is not None:
            status_label.setText(message)

    def apply_config(self, namespace: str, data: dict[str, object]) -> None:
        if namespace == "image":
            self.configPanel.apply_config(data)

    def set_output_folder(self, folder: Path | str | None) -> None:
        self.configPanel.set_output_folder(folder)

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

    def _register_text_list(self, list_widget: QListWidget) -> None:
        self._text_lists.append(list_widget)
        list_widget.installEventFilter(self)

    def _adjust_text_list_height(self, list_widget: QListWidget | None) -> None:
        if list_widget is None:
            return
        count = list_widget.count()
        if count == 0:
            list_widget.setVisible(False)
            list_widget.setFixedHeight(0)
            list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            return

        list_widget.setVisible(True)
        grid_size = list_widget.gridSize()
        grid_width = grid_size.width() or list_widget.viewport().width()
        grid_height = grid_size.height() or list_widget.sizeHintForRow(0) or 38

        viewport_width = list_widget.viewport().width() or grid_width
        columns = max(1, viewport_width // max(grid_width, 1))
        rows = ceil(count / columns)
        visible_rows = min(rows, self._max_text_rows)
        total_height = visible_rows * grid_height + max(0, (visible_rows - 1) * list_widget.spacing())
        frame_padding = list_widget.frameWidth() * 2
        list_widget.setFixedHeight(total_height + frame_padding)
        if rows > visible_rows:
            list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        else:
            list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

    def eventFilter(self, obj, event):  # type: ignore[override]
        if event.type() == QEvent.Type.Resize and obj in self._text_lists:
            self._adjust_text_list_height(obj)  # type: ignore[arg-type]
        return super().eventFilter(obj, event)

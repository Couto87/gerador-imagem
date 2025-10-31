"""High level controller that wires managers and the UI together."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QMessageBox

from .config_manager import ConfigManager
from .image_manager import ImageManager, MEDIA_EXTENSIONS
from ui.main_window import MainWindow


class AppController:
    def __init__(self) -> None:
        self.config_manager = ConfigManager()
        self.image_manager = ImageManager()
        self.window = MainWindow()

        self.output_directory: Path | None = None

        self.window.settingsTab.optionChanged.connect(self._on_option_changed)
        self.window.promptSubmitted.connect(self._on_prompt_submitted)
        self.window.browseFolderRequested.connect(self._on_browse_folder)
        self.window.outputBrowseRequested.connect(self._on_browse_output)
        self.window.configRequested.connect(self._open_settings_tab)

        self._initialize_state()

    def show(self) -> None:
        self.window.show()

    # Internal helpers --------------------------------------------------
    def _initialize_state(self) -> None:
        image_config = self.config_manager.data.get("image", {})
        self.window.apply_config("image", image_config)
        output_folder = self.config_manager.get("paths", "output_folder", "")
        if isinstance(output_folder, str) and output_folder:
            output_path = Path(output_folder)
            if output_path.exists():
                self.output_directory = output_path
                self.window.set_output_folder(output_path)
                self._refresh_output_files()
            else:
                self.output_directory = None
                self.window.clear_output_folder()
                self.window.set_output_files([])
                self.window.update_output_status(
                    "A pasta de destino configurada não existe mais. Selecione outra pasta."
                )
        else:
            self.output_directory = None
            self.window.clear_output_folder()
            self.window.set_output_files([])
            self.window.update_output_status("Nenhuma pasta de destino selecionada.")

        recent = self.config_manager.recent_folders()
        if recent:
            self._select_directory(recent[0])
        else:
            self.window.set_source_files([])
            self.window.update_source_status(
                "Nenhuma pasta selecionada. Use o botão acima para escolher uma pasta.",
            )

    def _on_option_changed(self, namespace: str, key: str, value) -> None:
        self.config_manager.update(namespace, key, value)
        self.window.apply_config(namespace, self.config_manager.data.get(namespace, {}))

    def _on_prompt_submitted(self, prompt: str) -> None:
        message = (
            "Prompt recebido! Configure suas opções e utilize as integrações de IA "
            "para gerar o conteúdo desejado."
        )
        self.window.update_output_status(message)
        self.window.clear_prompt()

    def _on_browse_folder(self) -> None:
        start = self.image_manager.current_directory or self.image_manager.root_path
        folder = self.window.open_folder_dialog(start)
        if folder is None:
            return
        self._select_directory(folder)

    def _on_browse_output(self) -> None:
        start = self.output_directory or self.image_manager.root_path
        folder = self.window.open_folder_dialog(start)
        if folder is None:
            return
        self.output_directory = folder
        self.window.set_output_folder(folder)
        self.config_manager.update("paths", "output_folder", str(folder))
        self._refresh_output_files()

    def _open_settings_tab(self) -> None:
        index = self.window.tabs.indexOf(self.window.settingsTab)
        if index >= 0:
            self.window.tabs.setCurrentIndex(index)

    def _select_directory(self, folder: Path) -> None:
        try:
            self.image_manager.set_current_directory(folder)
        except ValueError:
            QMessageBox.warning(
                self.window,
                "Pasta inválida",
                "Não foi possível acessar a pasta selecionada.",
            )
            return
        self.config_manager.add_recent_folder(folder)
        self._load_directory(folder)

    def _load_directory(self, folder: Path) -> None:
        files = self.image_manager.list_media_files()
        self.window.set_source_folder(folder)
        self.window.set_source_files(files)
        if files:
            message = f"{len(files)} arquivo(s) encontrado(s)"
        else:
            message = (
                "Nenhum arquivo de imagem ou texto encontrado na pasta selecionada."
            )
        self.window.update_source_status(message)
        self.window.set_path_label(folder)

    def _refresh_output_files(self) -> None:
        if self.output_directory is None or not self.output_directory.exists():
            self.window.set_output_files([])
            self.window.update_output_status("Nenhuma pasta de destino selecionada.")
            return

        files = [
            path
            for path in sorted(self.output_directory.iterdir())
            if path.is_file() and path.suffix.lower() in MEDIA_EXTENSIONS
        ]
        self.window.set_output_files(files)
        if not files:
            self.window.update_output_status(
                "Nenhum arquivo encontrado na pasta de destino selecionada."
            )

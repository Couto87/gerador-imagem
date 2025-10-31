"""High level controller that wires managers and the UI together."""
from __future__ import annotations

from pathlib import Path

from PyQt6.QtWidgets import QMessageBox

from .config_manager import ConfigManager
from .content_generator import ContentGenerationError, ContentGenerator
from .image_manager import ImageManager
from ui.main_window import MainWindow


class AppController:
    def __init__(self) -> None:
        self.config_manager = ConfigManager()
        self.image_manager = ImageManager()
        self.window = MainWindow()
        self.generator: ContentGenerator | None = None

        self.window.configPanel.optionChanged.connect(self._on_option_changed)
        self.window.promptSubmitted.connect(self._on_prompt_submitted)
        self.window.browseFolderRequested.connect(self._on_browse_folder)
        self.window.configRequested.connect(self._open_settings_tab)
        self.window.sidebar.folderSelected.connect(self._on_folder_selected)

        self._initialize_state()

    def show(self) -> None:
        self.window.show()

    # Internal helpers --------------------------------------------------
    def _initialize_state(self) -> None:
        image_config = self.config_manager.data.get("image", {})
        self.window.apply_config("image", image_config)
        recent = self.config_manager.recent_folders()
        if recent:
            self.window.set_directories(recent)
            self.window.select_directory(recent[0])
            self._load_directory(recent[0])
        else:
            self._refresh_directories()
            self.window.update_left_viewer(
                "Nenhuma pasta selecionada",
                "Use o painel lateral para escolher uma pasta de imagens.",
            )

    def _refresh_directories(self) -> None:
        directories = self.image_manager.list_directories()
        self.window.set_directories(directories)

    def _on_option_changed(self, namespace: str, key: str, value) -> None:
        self.config_manager.update(namespace, key, value)
        self.window.apply_config(namespace, self.config_manager.data.get(namespace, {}))

    def _on_prompt_submitted(self, prompt: str) -> None:
        item_type = str(
            self.config_manager.get("image", "type", "Imagem")
        ).casefold()

        if item_type == "imagem":
            message = "Função em desenvolvimento"
            print(message)
            self.window.update_right_viewer("Função em desenvolvimento", message)
            self.window.clear_prompt()
            return

        if item_type in {"música", "musica"}:
            if not prompt:
                return

            if self.generator is None:
                try:
                    self.generator = ContentGenerator()
                except ContentGenerationError as error:
                    self.window.update_right_viewer("Erro", str(error))
                    print(f"Erro ao configurar o gerador: {error}")
                    return

            try:
                result = self.generator.generate_music_scenes(prompt)
            except ContentGenerationError as error:
                self.window.update_right_viewer("Erro", str(error))
                print(f"Erro ao gerar conteúdo: {error}")
                return

            self._print_music_result(result)
            self.window.update_right_viewer(
                "Conteúdo gerado",
                "O resultado detalhado foi impresso no terminal em formato organizado.",
            )
            self.window.clear_prompt()
            return

        message = "Tipo de conteúdo não suportado."
        self.window.update_right_viewer("Aviso", message)
        print(message)
        self.window.clear_prompt()

    def _print_music_result(self, payload: dict[str, object]) -> None:
        music_title = payload.get("music_title", "")
        print(f"3.1 - music_title: {music_title}")

        scenes = payload.get("scenes", [])
        if not isinstance(scenes, list):
            print("Formato inesperado de cenas.")
            return

        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            scene_id = scene.get("scene_id")
            lyric_excerpt = scene.get("lyric_excerpt", "")
            image_suffix = scene_id if scene_id is not None else "desconhecido"
            print(f"3.2 - Imagem scene_{image_suffix}.png - {lyric_excerpt}")

            prompt_block = scene.get("prompt", {})
            if isinstance(prompt_block, dict):
                print("3.3 - Prompt:")
                for key, value in prompt_block.items():
                    print(f"       {key}: {value}")
            print("-")

    def _on_browse_folder(self) -> None:
        start = self.image_manager.current_directory or self.image_manager.root_path
        folder = self.window.open_folder_dialog(start)
        if folder is None:
            return
        self._select_directory(folder)

    def _open_settings_tab(self) -> None:
        index = self.window.tabs.indexOf(self.window.settingsTab)
        if index >= 0:
            self.window.tabs.setCurrentIndex(index)

    def _on_folder_selected(self, folder: Path) -> None:
        self._select_directory(folder)

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
        self.window.set_directories(self.config_manager.recent_folders())
        self.window.select_directory(folder)
        self._load_directory(folder)

    def _load_directory(self, folder: Path) -> None:
        images = self.image_manager.list_images()
        self.window.set_gallery_images(images)
        message = f"{len(images)} arquivo(s) de imagem encontrado(s)"
        self.window.update_left_viewer(folder.name or str(folder), message)
        self.window.set_path_label(folder)

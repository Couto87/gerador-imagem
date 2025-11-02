"""High level controller that wires managers and the UI together."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from PyQt6.QtWidgets import QMessageBox

from .config_manager import ConfigManager
from .image_manager import ImageManager
from ui.main_window import MainWindow

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore[assignment]

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[assignment]


class AppController:
    def __init__(self) -> None:
        self.config_manager = ConfigManager()
        self.image_manager = ImageManager()
        self.window = MainWindow()

        self.output_directory: Path | None = None
        self._openai_client: Any | None = None

        self.window.configPanel.optionChanged.connect(self._on_option_changed)
        self.window.promptSubmitted.connect(self._on_prompt_submitted)
        self.window.browseFolderRequested.connect(self._on_browse_folder)
        self.window.configPanel.outputFolderBrowseRequested.connect(
            self._on_browse_output
        )

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
            else:
                self.output_directory = None
                self.window.set_output_folder(None)
        else:
            self.output_directory = None
            self.window.set_output_folder(None)

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
        generation_type = (
            str(self.config_manager.get("image", "type", "Imagem")).strip().lower()
        )

        if generation_type == "imagem":
            QMessageBox.information(
                self.window,
                "Função em desenvolvimento",
                "A geração de imagens ainda está em desenvolvimento.",
            )
            return

        if generation_type != "música":
            QMessageBox.warning(
                self.window,
                "Tipo não suportado",
                "O tipo selecionado ainda não é suportado para geração automática.",
            )
            return

        self.window.clear_prompt()
        try:
            payload = self._request_storyboard(prompt)
        except Exception as exc:  # pragma: no cover - UI feedback only
            QMessageBox.critical(
                self.window,
                "Erro ao gerar conteúdo",
                f"Não foi possível gerar o conteúdo solicitado.\n\nDetalhes: {exc}",
            )
            return

        self._print_storyboard(payload)
        QMessageBox.information(
            self.window,
            "Geração concluída",
            (
                "A resposta da API foi processada com sucesso. "
                "Confira o terminal para visualizar os prompts detalhados."
            ),
        )

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

    # OpenAI integration -------------------------------------------------
    def _ensure_client(self) -> Any:
        if load_dotenv is not None:
            load_dotenv()

        if OpenAI is None:
            raise RuntimeError(
                "O pacote 'openai' não está disponível. Instale-o para usar a geração."
            )

        if self._openai_client is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "A variável de ambiente OPENAI_API_KEY não está configurada."
                )
            self._openai_client = OpenAI()
        return self._openai_client

    def _request_storyboard(self, prompt: str) -> Dict[str, Any]:
        client = self._ensure_client()

        envelope = {
            "tipo": "json",
            "conteudo": {
                "mensagem": prompt,
            },
        }
        json_text = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"

        response = client.responses.create(  # type: ignore[attr-defined]
            prompt={
                "id": "pmpt_6906aa0d5a288194b7def5427da43baf02ed834e4eacfbcd",
                "version": "3",
            },
            input=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json_text,
                        }
                    ],
                }
            ],
            reasoning={"summary": "auto"},
            store=True,
            include=[
                "reasoning.encrypted_content",
                "web_search_call.action.sources",
            ],
        )

        content = getattr(response, "output_text", None)
        if not content:
            raise RuntimeError("A resposta da API não retornou texto utilizável.")

        payload = json.loads(content)
        if not isinstance(payload, dict):
            raise RuntimeError("O conteúdo retornado não está no formato esperado.")
        return payload

    def _print_storyboard(self, payload: Dict[str, Any]) -> None:
        music_title = payload.get("music_title", "")
        print("3.1 - music_title:", music_title)

        scenes: List[Dict[str, Any]] = payload.get("scenes", []) or []
        for scene in scenes:
            scene_id = scene.get("scene_id")
            lyric_excerpt = scene.get("lyric_excerpt", "")
            slug_source = lyric_excerpt.lower()
            slug = re.sub(r"[^a-z0-9]+", "-", slug_source).strip("-")
            if isinstance(scene_id, int):
                scene_prefix = f"scene_{scene_id:02d}"
            else:
                scene_prefix = "scene"
            image_name = f"{scene_prefix}_{slug}" if slug else scene_prefix
            print(f"3.2 - {image_name} :: {lyric_excerpt}")

            prompt_content = scene.get("prompt", {})
            formatted_prompt = json.dumps(
                prompt_content, ensure_ascii=False, indent=2
            ) if isinstance(prompt_content, dict) else str(prompt_content)
            print("3.3 - Prompt:")
            print(formatted_prompt)
            print("-" * 40)


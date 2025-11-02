"""High level controller that wires managers and the UI together."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from PyQt6.QtWidgets import QMessageBox

from .config_manager import ConfigManager
from .image_manager import IMAGE_EXTENSIONS, TEXT_EXTENSIONS, ImageManager
from ui.main_window import MainWindow

try:  # pragma: no cover - optional dependency import guard
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - handled gracefully during runtime
    OpenAI = None  # type: ignore

try:  # pragma: no cover - optional dependency import guard
    from PIL import Image, PngImagePlugin  # type: ignore
except Exception:  # pragma: no cover - optional dependency import guard
    Image = None  # type: ignore
    PngImagePlugin = None  # type: ignore


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

        selected_files = self.window.selected_files()

        try:
            response_payload = self._generate_music_storyboard(prompt, selected_files)
        except ValueError as exc:
            QMessageBox.warning(
                self.window,
                "Configuração ausente",
                str(exc),
            )
            return
        except Exception as exc:  # pragma: no cover - network/runtime issues
            QMessageBox.critical(
                self.window,
                "Erro na geração",
                "Ocorreu um erro ao tentar gerar o conteúdo: {0}".format(exc),
            )
            return

        self.window.clear_prompt()
        self._print_music_response(response_payload)
        QMessageBox.information(
            self.window,
            "Geração concluída",
            "Cenas geradas com sucesso. Consulte o terminal para os detalhes.",
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

    def _ensure_openai_client(self) -> Any:
        if OpenAI is None:
            raise ValueError(
                "A biblioteca oficial da OpenAI não está instalada no ambiente."
            )

        if self._openai_client is None:
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not api_key:
                raise ValueError(
                    "A variável de ambiente OPENAI_API_KEY não foi configurada."
                )
            self._openai_client = OpenAI(api_key=api_key)
        return self._openai_client

    def _generate_music_storyboard(
        self, lyrics: str, selected_files: Iterable[Path]
    ) -> Dict[str, Any]:
        client = self._ensure_openai_client()
        text_entries, image_contents, image_names = self._prepare_media_payloads(
            selected_files, client
        )
        payload_message = {
            "lyrics": lyrics,
            "additional_texts": [
                {"filename": name, "content": content}
                for name, content in text_entries
            ],
            "image_references": [
                {
                    "filename": name,
                    **content,
                }
                for name, content in zip(image_names, image_contents)
            ],
            "image_names": image_names,
        }

        user_payload = json.dumps(payload_message, ensure_ascii=False)

        resp = client.responses.create(  # type: ignore[attr-defined]
            input=[
                {
                    "role": "user",
                    "content": {
                        "format": "json",
                        "text": user_payload,
                    },
                }
            ],
        )

        content = getattr(resp, "output_text", None)
        if not content:
            raise RuntimeError("A resposta da API não retornou texto utilizável.")

        payload = json.loads(content)
        if not isinstance(payload, dict):
            raise RuntimeError("O conteúdo retornado não está no formato esperado.")
        return payload

    def _prepare_media_payloads(
        self, files: Iterable[Path], client: Any
    ) -> Tuple[List[Tuple[str, str]], List[Dict[str, Any]], List[str]]:
        text_entries: List[Tuple[str, str]] = []
        image_contents: List[Dict[str, Any]] = []
        image_names: List[str] = []

        for path in files:
            suffix = path.suffix.lower()
            if suffix in TEXT_EXTENSIONS:
                try:
                    content = path.read_text(encoding="utf-8", errors="replace").strip()
                except OSError:
                    continue
                if content:
                    text_entries.append((path.name, content))
            elif suffix in IMAGE_EXTENSIONS:
                file_id = self._ensure_openai_file_id(path, client)
                if file_id:
                    image_contents.append(
                        {
                            "file_id": file_id,
                            "type": "image_url",
                            "image_url": {"url": f"file_id:{file_id}"},
                        }
                    )
                    image_names.append(path.name)
        return text_entries, image_contents, image_names

    def _ensure_openai_file_id(self, path: Path, client: Any) -> str | None:
        file_id = self._read_image_metadata(path)
        if file_id:
            return file_id

        try:
            with path.open("rb") as file_content:
                result = client.files.create(file=file_content, purpose="vision")
        except Exception:
            return None

        file_id = getattr(result, "id", None)
        if isinstance(file_id, str) and file_id:
            self._write_image_metadata(path, file_id)
            return file_id
        return None

    def _read_image_metadata(self, path: Path) -> str | None:
        suffix = path.suffix.lower()

        if Image is None:  # pragma: no cover - fallback when Pillow isn't installed
            return self._read_sidecar_metadata(path)

        if suffix == ".png" and PngImagePlugin is not None:
            try:
                with Image.open(path) as image:
                    value = image.info.get("IDOPENAI")  # type: ignore[attr-defined]
                    if isinstance(value, str) and value:
                        return value
            except Exception:
                pass
            return self._read_sidecar_metadata(path)
        elif suffix in {".jpg", ".jpeg", ".webp"}:
            value = self._read_exif_user_comment(path)
            if value:
                return value
            return self._read_sidecar_metadata(path)
        elif suffix == ".bmp":
            return self._read_sidecar_metadata(path)

        return None

    def _write_image_metadata(self, path: Path, file_id: str) -> None:
        suffix = path.suffix.lower()

        if Image is None:  # pragma: no cover - fallback when Pillow isn't installed
            self._write_sidecar_metadata(path, file_id)
            return

        if suffix == ".png" and PngImagePlugin is not None:
            self._write_png_metadata(path, file_id)
        elif suffix in {".jpg", ".jpeg", ".webp"}:
            self._write_exif_user_comment(path, file_id)
        elif suffix == ".bmp":
            self._write_sidecar_metadata(path, file_id)

    def _read_exif_user_comment(self, path: Path) -> str | None:
        if Image is None:  # pragma: no cover - fallback guard
            return None

        try:
            with Image.open(path) as image:
                exif = image.getexif()
        except Exception:
            return None

        if not exif:
            return None

        raw_value = exif.get(0x9286)
        if isinstance(raw_value, bytes) and raw_value:
            if raw_value.startswith(b"ASCII\0\0\0"):
                raw_value = raw_value[8:]
            try:
                return raw_value.decode("utf-8").strip()
            except UnicodeDecodeError:
                try:
                    return raw_value.decode("latin-1").strip()
                except UnicodeDecodeError:
                    return None
        if isinstance(raw_value, str) and raw_value:
            return raw_value.strip()
        return None

    def _write_exif_user_comment(self, path: Path, file_id: str) -> None:
        if Image is None:  # pragma: no cover - fallback guard
            return

        try:
            with Image.open(path) as image:
                exif = image.getexif()
                exif[0x9286] = b"ASCII\0\0\0" + file_id.encode("utf-8")
                image.save(path, exif=exif.tobytes())
        except Exception:
            self._write_sidecar_metadata(path, file_id)

    def _write_png_metadata(self, path: Path, file_id: str) -> None:
        if Image is None or PngImagePlugin is None:  # pragma: no cover - fallback guard
            self._write_sidecar_metadata(path, file_id)
            return

        try:
            with Image.open(path) as image:
                png_info = PngImagePlugin.PngInfo()
                for key, value in image.info.items():
                    if isinstance(value, str):
                        png_info.add_text(key, value)
                png_info.add_text("IDOPENAI", file_id)
                image.save(path, pnginfo=png_info)
        except Exception:
            self._write_sidecar_metadata(path, file_id)

    def _read_sidecar_metadata(self, path: Path) -> str | None:
        metadata_path = self._metadata_sidecar_path(path)
        if not metadata_path.exists():
            return None

        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        value = data.get("IDOPENAI")
        if isinstance(value, str) and value:
            return value
        return None

    def _write_sidecar_metadata(self, path: Path, file_id: str) -> None:
        metadata_path = self._metadata_sidecar_path(path)
        payload = {"IDOPENAI": file_id}
        try:
            metadata_path.write_text(json.dumps(payload), encoding="utf-8")
        except OSError:
            pass

    @staticmethod
    def _metadata_sidecar_path(path: Path) -> Path:
        return path.with_suffix(path.suffix + ".metadata.json")

    def _print_music_response(self, payload: Dict[str, Any]) -> None:
        print("\n=== Resultado da geração de conteúdo (música) ===")
        music_title = payload.get("music_title", "")
        print(f"3.1 - music_title: {music_title}")

        scenes = payload.get("scenes", [])
        if not isinstance(scenes, list):
            print("Nenhuma cena válida foi retornada.")
            return

        for scene in scenes:
            if not isinstance(scene, dict):
                continue
            scene_id = scene.get("scene_id", "")
            lyric_excerpt = scene.get("lyric_excerpt", "")
            try:
                scene_number = int(scene_id)
                image_name = f"scene_{scene_number:02d}.png"
            except (TypeError, ValueError):
                image_name = f"scene_{scene_id}.png" if scene_id else "scene_unknown.png"
            print(f"3.2 - {image_name}: {lyric_excerpt}")

            prompt = scene.get("prompt", {})
            print("3.3 - Prompt:")
            if isinstance(prompt, dict):
                for key, value in prompt.items():
                    print(f"    {key}: {value}")
            else:
                print(f"    {prompt}")
            print("-" * 60)


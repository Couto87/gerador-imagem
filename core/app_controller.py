"""High level controller that wires managers and the UI together."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from .config_manager import ConfigManager
from .image_manager import IMAGE_EXTENSIONS, TEXT_EXTENSIONS, ImageManager
from ui.main_window import MainWindow

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency
    load_dotenv = None  # type: ignore[assignment]

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional dependency
    OpenAI = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    from PIL import Image, PngImagePlugin
except ImportError:  # pragma: no cover - optional dependency
    Image = None  # type: ignore[assignment]
    PngImagePlugin = None  # type: ignore[assignment]

try:  # pragma: no cover - optional dependency
    from PIL import UnidentifiedImageError
except ImportError:  # pragma: no cover - optional dependency
    UnidentifiedImageError = Exception  # type: ignore[assignment]


class _GenerationWorker(QObject):
    finished = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, controller: "AppController", prompt: str, selected_files: List[Path]) -> None:
        super().__init__()
        self._controller = controller
        self._prompt = prompt
        self._selected_files = selected_files

    def run(self) -> None:
        try:
            payload = self._controller._request_storyboard(
                self._prompt, self._selected_files
            )
        except Exception as exc:  # pragma: no cover - worker thread feedback
            self.failed.emit(str(exc))
            return
        self.finished.emit(payload)


class AppController:
    def __init__(self) -> None:
        self.config_manager = ConfigManager()
        self.image_manager = ImageManager()
        self.window = MainWindow()

        self.output_directory: Path | None = None
        self._openai_client: Any | None = None
        self._generation_thread: QThread | None = None
        self._generation_worker: _GenerationWorker | None = None

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

        if self._generation_thread is not None:
            QMessageBox.information(
                self.window,
                "Processo em andamento",
                "Já existe uma requisição em andamento. Aguarde a conclusão antes de iniciar outra.",
            )
            return

        self.window.clear_prompt()
        self.window.begin_generation_progress()

        selected_files = list(self.window.selected_files())

        worker = _GenerationWorker(self, prompt, selected_files)
        thread = QThread()
        worker.moveToThread(thread)
        worker.finished.connect(self._handle_generation_success)
        worker.failed.connect(self._handle_generation_failure)
        thread.started.connect(worker.run)
        thread.finished.connect(thread.deleteLater)
        thread.start()

        self._generation_thread = thread
        self._generation_worker = worker

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

    # Metadata helpers -------------------------------------------------
    def _load_sidecar_metadata(self, path: Path) -> Dict[str, str]:
        metadata_path = path.with_suffix(path.suffix + ".meta.json")
        if not metadata_path.exists():
            return {}
        try:
            data = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return {str(k): str(v) for k, v in data.items() if isinstance(k, str)}

    def _save_sidecar_metadata(self, path: Path, data: Dict[str, str]) -> None:
        metadata_path = path.with_suffix(path.suffix + ".meta.json")
        try:
            metadata_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _decode_exif_user_comment(self, value: Any) -> str:
        if isinstance(value, bytes):
            prefixes = (
                b"ASCII\0\0\0",
                b"JIS\0\0\0\0",
                b"UNICODE\0",
            )
            for prefix in prefixes:
                if value.startswith(prefix):
                    value = value[len(prefix) :]
                    break
            try:
                return value.decode("utf-8", "ignore")
            except Exception:
                return ""
        if isinstance(value, str):
            return value
        return ""

    def _encode_exif_user_comment(self, data: Dict[str, str]) -> bytes:
        payload = json.dumps(data, ensure_ascii=False)
        return b"UNICODE\0" + payload.encode("utf-8")

    def _load_image_metadata(self, path: Path) -> Dict[str, str]:
        metadata: Dict[str, str] = {}
        metadata.update(self._load_sidecar_metadata(path))
        if Image is None:
            return metadata

        suffix = path.suffix.lower()
        try:
            with Image.open(path) as img:
                if suffix == ".png":
                    for key, value in img.info.items():
                        if isinstance(key, str) and isinstance(value, str):
                            metadata.setdefault(key, value)
                elif suffix in {".jpg", ".jpeg", ".webp"}:
                    exif = img.getexif()
                    if exif:
                        decoded = self._decode_exif_user_comment(exif.get(0x9286))
                        if decoded:
                            try:
                                payload = json.loads(decoded)
                                if isinstance(payload, dict):
                                    for key, value in payload.items():
                                        if isinstance(key, str) and isinstance(value, str):
                                            metadata.setdefault(key, value)
                            except json.JSONDecodeError:
                                metadata.setdefault("IDOPENAI", decoded)
        except (OSError, UnidentifiedImageError):  # pragma: no cover - best effort only
            return metadata
        return metadata

    def _write_png_metadata(self, path: Path, data: Dict[str, str]) -> bool:
        if Image is None or PngImagePlugin is None:
            return False
        try:
            with Image.open(path) as img:
                pnginfo = PngImagePlugin.PngInfo()
                for key, value in img.info.items():
                    if isinstance(key, str) and isinstance(value, str):
                        pnginfo.add_text(key, value)
                for key, value in data.items():
                    pnginfo.add_text(key, value)
                img.save(path, pnginfo=pnginfo)
            return True
        except (OSError, UnidentifiedImageError):  # pragma: no cover - best effort only
            return False

    def _write_jpeg_like_metadata(self, path: Path, data: Dict[str, str]) -> bool:
        if Image is None:
            return False
        try:
            with Image.open(path) as img:
                exif = img.getexif()
                exif[0x9286] = self._encode_exif_user_comment(data)
                img.save(path, exif=exif.tobytes())
            return True
        except (OSError, UnidentifiedImageError):  # pragma: no cover - best effort only
            return False

    def _write_image_metadata(self, path: Path, data: Dict[str, str]) -> None:
        success = False
        suffix = path.suffix.lower()
        if suffix == ".png":
            success = self._write_png_metadata(path, data)
        elif suffix in {".jpg", ".jpeg", ".webp"}:
            success = self._write_jpeg_like_metadata(path, data)

        if not success:
            merged = self._load_sidecar_metadata(path)
            merged.update(data)
            self._save_sidecar_metadata(path, merged)
        else:
            merged = self._load_sidecar_metadata(path)
            merged.update(data)
            self._save_sidecar_metadata(path, merged)

    def _ensure_openai_file_id(self, path: Path, client: Any) -> str | None:
        metadata = self._load_image_metadata(path)
        existing = metadata.get("IDOPENAI")
        if existing:
            return existing

        try:
            with open(path, "rb") as buffer:
                result = client.files.create(file=buffer, purpose="vision")
        except OSError:
            return None
        except Exception:  # pragma: no cover - API errors
            return None

        file_id = getattr(result, "id", None)
        if isinstance(file_id, str) and file_id:
            self._write_image_metadata(path, {"IDOPENAI": file_id})
            return file_id
        return None

    def _collect_selected_media(
        self, client: Any, selected_files: List[Path]
    ) -> Tuple[List[Tuple[str, str]], List[Dict[str, Any]], List[Dict[str, str]]]:
        texts: List[Tuple[str, str]] = []
        image_contents: List[Dict[str, Any]] = []
        image_refs: List[Dict[str, str]] = []

        for path in selected_files:
            suffix = path.suffix.lower()
            if suffix in TEXT_EXTENSIONS:
                try:
                    content = path.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                texts.append((path.name, content))
            elif suffix in IMAGE_EXTENSIONS:
                file_id = self._ensure_openai_file_id(path, client)
                if not file_id:
                    continue
                image_contents.append(
                    {
                        "type": "input_image",
                        "file_id": file_id,
                    }
                )
                image_refs.append({"nome": path.name, "file_id": file_id})

        return texts, image_contents, image_refs

    def _request_storyboard(
        self, prompt: str, selected_files: List[Path]
    ) -> Dict[str, Any]:
        client = self._ensure_client()

        texts, image_contents, image_refs = self._collect_selected_media(
            client, selected_files
        )

        envelope: Dict[str, Any] = {
            "tipo": "json",
            "conteudo": {
                "mensagem": prompt,
            },
        }
        if texts:
            envelope["conteudo"]["arquivos_texto"] = [
                {"nome": name, "conteudo": content} for name, content in texts
            ]
        if image_refs:
            envelope["conteudo"]["referencias_imagem"] = image_refs

        json_text = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"

        content_blocks: List[Dict[str, Any]] = [
            {
                "type": "input_text",
                "text": json_text,
            }
        ]
        content_blocks.extend(image_contents)

        response = client.responses.create(  # type: ignore[attr-defined]
            prompt={
                "id": "pmpt_6906aa0d5a288194b7def5427da43baf02ed834e4eacfbcd",
                "version": "3",
            },
            input=[
                {
                    "role": "user",
                    "content": content_blocks,
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

    # Output helpers ---------------------------------------------------
    def _sanitize_filename_component(self, value: str) -> str:
        value = value.replace("\n", " ").replace("\r", " ")
        value = " ".join(value.split())
        sanitized = re.sub(r"[\\/:*?\"<>|]", "_", value).strip(" _")
        if len(sanitized) > 80:
            sanitized = sanitized[:80].rstrip(" _")
        return sanitized or "sem_nome"

    def _save_storyboard_files(self, payload: Dict[str, Any]) -> None:
        if self.output_directory is None:
            print(
                "Nenhuma pasta de destino configurada. Os arquivos de cenas não foram criados."
            )
            return

        music_title = str(payload.get("music_title", "")).strip()
        folder_name = self._sanitize_filename_component(music_title or "sem_titulo")
        target_dir = self.output_directory / folder_name

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            print(
                "Não foi possível criar a pasta de destino para salvar as cenas geradas."
            )
            return

        scenes: List[Dict[str, Any]] = payload.get("scenes", []) or []
        for index, scene in enumerate(scenes, start=1):
            scene_id = scene.get("scene_id")
            if isinstance(scene_id, int) and scene_id >= 0:
                prefix = f"{scene_id:03d}"
            else:
                prefix = f"{index:03d}"

            lyric_excerpt = str(scene.get("lyric_excerpt", "")).strip()
            excerpt_component = self._sanitize_filename_component(lyric_excerpt)
            filename = f"{prefix} {excerpt_component}.txt"
            file_path = target_dir / filename
            try:
                file_path.write_text("", encoding="utf-8")
            except OSError:
                print(f"Não foi possível criar o arquivo: {file_path}")

    def _handle_generation_success(self, payload: Dict[str, Any]) -> None:
        elapsed_message = None
        if self.window is not None:
            elapsed_seconds = getattr(self.window, "_generation_elapsed", 0)
            if isinstance(elapsed_seconds, int) and elapsed_seconds > 0:
                elapsed_message = f"Concluído em {elapsed_seconds} s"

        self.window.finish_generation_progress(message=elapsed_message)
        self._finalize_generation_thread()

        self._print_storyboard(payload)
        self._save_storyboard_files(payload)
        QMessageBox.information(
            self.window,
            "Geração concluída",
            (
                "A resposta da API foi processada com sucesso. "
                "Confira o terminal para visualizar os prompts detalhados."
            ),
        )

    def _handle_generation_failure(self, error_message: str) -> None:
        elapsed_message = None
        if self.window is not None:
            elapsed_seconds = getattr(self.window, "_generation_elapsed", 0)
            if isinstance(elapsed_seconds, int) and elapsed_seconds > 0:
                elapsed_message = f"Falha após {elapsed_seconds} s"

        self.window.finish_generation_progress(message=elapsed_message)
        self._finalize_generation_thread()
        QMessageBox.critical(
            self.window,
            "Erro ao gerar conteúdo",
            (
                "Não foi possível gerar o conteúdo solicitado."
                f"\n\nDetalhes: {error_message}"
            ),
        )

    def _finalize_generation_thread(self) -> None:
        thread = self._generation_thread
        worker = self._generation_worker

        self._generation_thread = None
        self._generation_worker = None

        if worker is not None:
            worker.deleteLater()

        if thread is not None:
            thread.quit()
            thread.wait()


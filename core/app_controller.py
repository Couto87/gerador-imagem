"""High level controller that wires managers and the UI together."""
from __future__ import annotations

import base64
import json
import os
from typing import Any, Dict, Iterable, List, Tuple
from pathlib import Path

from PyQt6.QtWidgets import QMessageBox

from .config_manager import ConfigManager
from .image_manager import IMAGE_EXTENSIONS, TEXT_EXTENSIONS, ImageManager
from ui.main_window import MainWindow

try:  # pragma: no cover - optional dependency import guard
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover - handled gracefully during runtime
    OpenAI = None  # type: ignore


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
            selected_files
        )
        user_sections: List[str] = [f"Letra fornecida pelo usuário:\n{lyrics}"]
        if text_entries:
            for name, content in text_entries:
                user_sections.append(
                    f"Conteúdo adicional do arquivo {name}:\n{content}"
                )
        if image_names:
            user_sections.append(
                "As imagens anexadas devem servir como referência visual. "
                f"Arquivos: {', '.join(image_names)}."
            )
        user_text = "\n\n".join(user_sections)
        user_content: List[Dict[str, str]] = [{"type": "text", "text": user_text}]
        user_content.extend(image_contents)
        system_prompt = (
            "Você é um diretor de arte e criador de prompts visuais cinematográficos "
            "especializado em transformar letras de música em cenas ilustradas.\n"
            "Receberá uma letra de música e, opcionalmente, uma imagem de referência com "
            "personagens e estilo visual.\n\n"
            "Sua tarefa é gerar somente JSON válido, contendo as cenas visuais que "
            "representam cada pequeno trecho da música.\n\n"
            "🎵 INSTRUÇÕES\n\n"
            "Gere automaticamente um nome criativo e coerente para a música, inserindo em "
            '"music_title".\n\n'
            "Divida a letra em pequenos trechos com sentido próprio — versos, expressões "
            "ou ações curtas — para formar cenas individuais.\n\n"
            "Para cada trecho, gere um único prompt completo (sem dependência de outros).\n\n"
            "Se for fornecida uma imagem de referência:\n\n"
            "O estilo visual e os personagens originais devem ser preservados fielmente.\n\n"
            "A paleta de cores, cenário, iluminação e composição podem ser aprimorados "
            "criativamente.\n\n"
            "O campo \"style\" deve incluir algo como:\n\n"
            "“mantendo o estilo visual e personagens da imagem de referência, com "
            "aprimoramento criativo de cores e ambiente.”\n\n"
            "O campo \"characters\" deve especificar:\n\n"
            "Quais personagens da imagem original aparecem na cena.\n\n"
            "Se há novos figurantes, descreva-os (ex.: “criança nova observando o personagem "
            "principal”).\n\n"
            "Se não houver imagem, defina livremente o estilo coerente com o tom da música "
            "(ex.: animação infantil 3D colorida, pintura digital poética, arte surreal "
            "cinematográfica etc.).\n\n"
            "Não inclua \"aspect_ratio\", \"quality\" ou referências cruzadas.\n\n"
            "Cada prompt deve ser totalmente autônomo, incluindo todas as informações "
            "necessárias: ambiente, personagens, ação, emoção, composição e iluminação.\n\n"
            "A saída deve conter apenas JSON válido.\n\n"
            "🧩 ESTRUTURA DE SAÍDA JSON\n"
            "{\n"
            "  \"music_title\": \"nome gerado automaticamente da música\",\n"
            "  \"scenes\": [\n"
            "    {\n"
            "      \"scene_id\": 1,\n"
            "      \"lyric_excerpt\": \"pequeno trecho da música\",\n"
            "      \"prompt\": {\n"
            "        \"style\": \"\",\n"
            "        \"palette\": \"\",\n"
            "        \"camera\": \"\",\n"
            "        \"lighting\": \"\",\n"
            "        \"environment\": \"\",\n"
            "        \"characters\": \"\",\n"
            "        \"action\": \"\",\n"
            "        \"mood\": \"\",\n"
            "        \"visual_motifs\": \"\",\n"
            "        \"framing_composition\": \"\",\n"
            "        \"negative_prompts\": \"\"\n"
            "      }\n"
            "    }\n"
            "  ]\n"
            "}\n\n"
            "🎨 ORIENTAÇÕES CRIATIVAS\n\n"
            "Cada cena deve representar um quadro cinematográfico ou ilustração isolada, "
            "visualmente rica.\n\n"
            "Use descrições técnicas e emocionais:\n"
            "“plano médio com luz lateral suave”, “contraluz dourado”, “ângulo baixo heroico”, "
            "“movimento lateral fluido”.\n\n"
            "Se houver imagem de referência:\n\n"
            "Estilo e personagens permanecem consistentes.\n\n"
            "Cores, ambientes e iluminação podem ser reinventados ou aprimorados.\n\n"
            "Mantenha a coerência geral entre as cenas, mas sem referências diretas entre prompts."
        )

        chat_response = client.chat.completions.create(  # type: ignore[attr-defined]
            model="gpt-5",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
        )

        choice = getattr(chat_response, "choices", None)
        if not choice:
            raise RuntimeError("A resposta da API não contém escolhas válidas.")

        message = choice[0].message  # type: ignore[index]
        content = getattr(message, "content", None)
        if not content:
            raise RuntimeError("A resposta da API não contém conteúdo utilizável.")

        payload = json.loads(content)
        if not isinstance(payload, dict):
            raise RuntimeError("O conteúdo retornado não está no formato esperado.")
        return payload

    def _prepare_media_payloads(
        self, files: Iterable[Path]
    ) -> Tuple[List[Tuple[str, str]], List[Dict[str, str]], List[str]]:
        text_entries: List[Tuple[str, str]] = []
        image_contents: List[Dict[str, str]] = []
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
                try:
                    data = path.read_bytes()
                except OSError:
                    continue
                if not data:
                    continue
                mime = self._guess_image_mime(suffix)
                encoded = base64.b64encode(data).decode("ascii")
                image_contents.append(
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime};base64,{encoded}",
                    }
                )
                image_names.append(path.name)
        return text_entries, image_contents, image_names

    @staticmethod
    def _guess_image_mime(suffix: str) -> str:
        mapping = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
        }
        return mapping.get(suffix.lower(), "application/octet-stream")

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


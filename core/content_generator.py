"""Integration helpers to communicate with OpenAI's API."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

from openai import OpenAI


SYSTEM_PROMPT = (
    "Você é um diretor de arte e criador de prompts visuais cinematográficos "
    "especializado em transformar letras de música em cenas ilustradas.\n"
    "Receberá uma letra de música e, opcionalmente, uma imagem de referência "
    "com personagens e estilo visual.\n\n"
    "Sua tarefa é gerar somente JSON válido, contendo as cenas visuais que "
    "representam cada pequeno trecho da música.\n\n"
    "🎵 INSTRUÇÕES\n\n"
    "Gere automaticamente um nome criativo e coerente para a música, inserindo "
    "em \"music_title\".\n\n"
    "Divida a letra em pequenos trechos com sentido próprio — versos, "
    "expressões ou ações curtas — para formar cenas individuais.\n\n"
    "Para cada trecho, gere um único prompt completo (sem dependência de "
    "outros).\n\n"
    "Se for fornecida uma imagem de referência:\n\n"
    "O estilo visual e os personagens originais devem ser preservados "
    "fielmente.\n\n"
    "A paleta de cores, cenário, iluminação e composição podem ser "
    "aprimorados criativamente.\n\n"
    "O campo \"style\" deve incluir algo como:\n\n"
    "“mantendo o estilo visual e personagens da imagem de referência, com "
    "aprimoramento criativo de cores e ambiente.”\n\n"
    "O campo \"characters\" deve especificar:\n\n"
    "Quais personagens da imagem original aparecem na cena.\n\n"
    "Se há novos figurantes, descreva-os (ex.: “criança nova observando o "
    "personagem principal”).\n\n"
    "Se não houver imagem, defina livremente o estilo coerente com o tom da "
    "música (ex.: animação infantil 3D colorida, pintura digital poética, arte "
    "surreal cinematográfica etc.).\n\n"
    "Não inclua \"aspect_ratio\", \"quality\" ou referências cruzadas.\n\n"
    "Cada prompt deve ser totalmente autônomo, incluindo todas as informações "
    "necessárias: ambiente, personagens, ação, emoção, composição e "
    "iluminação.\n\n"
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
    "“plano médio com luz lateral suave”, “contraluz dourado”, “ângulo baixo "
    "heroico”, “movimento lateral fluido”.\n\n"
    "Se houver imagem de referência:\n\n"
    "Estilo e personagens permanecem consistentes.\n\n"
    "Cores, ambientes e iluminação podem ser reinventados ou aprimorados.\n\n"
    "Mantenha a coerência geral entre as cenas, mas sem referências diretas "
    "entre prompts."
)


def _load_dotenv() -> None:
    """Load key-value pairs from a local ``.env`` file if available."""

    project_root = Path(__file__).resolve().parents[1]
    env_path = project_root / ".env"
    if not env_path.exists():
        return

    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())
    except OSError:
        # Ignore file reading issues silently to avoid breaking the UI.
        pass


_load_dotenv()


class ContentGenerationError(RuntimeError):
    """Wrap errors raised when contacting OpenAI."""


@dataclass
class ContentGenerator:
    """Handle the conversation with the OpenAI Responses API."""

    model: str = "gpt-5"

    def __post_init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ContentGenerationError(
                "Variável de ambiente OPENAI_API_KEY não configurada."
            )
        self._client = OpenAI(api_key=api_key)

    def generate_music_scenes(self, lyrics: str) -> Dict[str, Any]:
        """Return the structured scenes generated from a lyric."""

        try:
            response = self._client.responses.create(
                model=self.model,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "text", "text": SYSTEM_PROMPT}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Letra da música a ser transformada em cenas visuais:\n"
                                    f"{lyrics.strip()}"
                                ),
                            }
                        ],
                    },
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # noqa: BLE001 - wrap SDK exceptions
            raise ContentGenerationError(str(exc)) from exc

        # The Responses API returns a list of content blocks. We expect
        # the first text block to contain the JSON payload we requested.
        try:
            content_block = response.output[0].content[0]
            text = content_block.text  # type: ignore[attr-defined]
        except (AttributeError, IndexError, KeyError) as exc:  # pragma: no cover - safety net
            raise ContentGenerationError("Resposta da API em formato inesperado.") from exc

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise ContentGenerationError("A resposta da API não é um JSON válido.") from exc

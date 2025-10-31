"""Configuration management module for Image Studio desktop app."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

import json


CONFIG_FILE_NAME = ".image_studio_config.json"


def _default_config() -> Dict[str, Any]:
    return {
        "image": {
            "size": "1024 × 1024 (Quadrado)",
            "resolution": "Baixa",
            "quantity": 1,
            "type": "Imagem",
        },
        "recent_folders": [],
    }


@dataclass
class ConfigManager:
    """Persist and provide access to the application configuration."""

    path: Path = field(default_factory=lambda: Path.home() / CONFIG_FILE_NAME)
    data: Dict[str, Any] = field(default_factory=_default_config)

    def __post_init__(self) -> None:
        self.load()

    def load(self) -> None:
        """Load configuration from disk if available."""
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as fh:
                    self.data = json.load(fh)
            except (json.JSONDecodeError, OSError):
                # Fallback to defaults in case of a corrupted file.
                self.data = _default_config()
        else:
            self.data = _default_config()

    def save(self) -> None:
        """Persist configuration to disk."""
        try:
            with self.path.open("w", encoding="utf-8") as fh:
                json.dump(self.data, fh, ensure_ascii=False, indent=2)
        except OSError:
            # In a desktop application we could surface an error to the user.
            # For now we fail silently to avoid crashing the UI.
            pass

    def update(self, namespace: str, key: str, value: Any) -> None:
        """Update a configuration value and persist the change."""
        namespace_data = self.data.setdefault(namespace, {})
        namespace_data[key] = value
        self.save()

    def get(self, namespace: str, key: str, default: Any = None) -> Any:
        return self.data.get(namespace, {}).get(key, default)

    def add_recent_folder(self, folder: Path, limit: int = 10) -> None:
        folder_str = str(folder)
        recents: List[str] = self.data.setdefault("recent_folders", [])
        if folder_str in recents:
            recents.remove(folder_str)
        recents.insert(0, folder_str)
        del recents[limit:]
        self.save()

    def recent_folders(self) -> List[Path]:
        return [Path(p) for p in self.data.get("recent_folders", [])]

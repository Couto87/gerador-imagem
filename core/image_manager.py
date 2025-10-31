"""Image management utilities for the Image Studio desktop app."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Sequence

IMAGE_EXTENSIONS: Sequence[str] = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
TEXT_EXTENSIONS: Sequence[str] = (".txt",)
MEDIA_EXTENSIONS: Sequence[str] = IMAGE_EXTENSIONS + TEXT_EXTENSIONS


@dataclass
class ImageManager:
    """Handle folder navigation and image discovery."""

    root_path: Path = field(default_factory=lambda: Path.home())
    current_directory: Path | None = None

    def __post_init__(self) -> None:
        if not self.root_path.exists():
            self.root_path = Path.home()

    def list_directories(self, depth: int = 1) -> List[Path]:
        """Return subdirectories up to the provided depth."""
        directories: List[Path] = []
        base = self.current_directory or self.root_path
        if not base.exists():
            return directories

        if depth <= 0:
            return [base]

        for child in sorted(base.iterdir()):
            if child.is_dir():
                directories.append(child)
        return directories

    def set_current_directory(self, directory: Path) -> None:
        if directory.exists() and directory.is_dir():
            self.current_directory = directory
        else:
            raise ValueError(f"Invalid directory: {directory}")

    def list_images(self) -> List[Path]:
        base = self.current_directory or self.root_path
        if not base.exists():
            return []
        return [
            file
            for file in sorted(base.iterdir())
            if file.is_file() and file.suffix.lower() in IMAGE_EXTENSIONS
        ]

    def list_media_files(self) -> List[Path]:
        base = self.current_directory or self.root_path
        if not base.exists():
            return []
        return [
            file
            for file in sorted(base.iterdir())
            if file.is_file() and file.suffix.lower() in MEDIA_EXTENSIONS
        ]

    def latest_images(self, limit: int = 10) -> List[Path]:
        images = self.list_images()
        images.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return images[:limit]

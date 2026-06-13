"""Adaptateurs entre le cœur ``html_to_md`` (disque) et l'app web (mémoire).

Le cœur (`html_to_md.core.process_file`) lit un fichier et écrit le Markdown +
les images sur disque. L'app web reçoit des octets et doit proposer un
téléchargement : on passe donc par un dossier temporaire puis on relit le
résultat en mémoire.
"""

from __future__ import annotations

import io
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from html_to_md.core import Result, process_file
from html_to_md.extract import Profile, load_profiles

# config/selectors.yaml est à la racine du dépôt, app/ juste à côté.
DEFAULT_CONFIG = Path(__file__).resolve().parents[1] / "config" / "selectors.yaml"

ProgressFn = Callable[[int, int, str], None]


@dataclass
class ConvertedFile:
    """Résultat d'une conversion, gardé entièrement en mémoire."""

    result: Result
    md_name: str
    md_bytes: bytes
    assets: dict[str, bytes] = field(default_factory=dict)  # chemin relatif -> octets


def get_profiles(config_path: Path | None = None) -> list[Profile]:
    """Charge les profils d'extraction (liste vide si pas de config)."""
    path = config_path or DEFAULT_CONFIG
    return load_profiles(path) if path.exists() else []


def is_html(data: bytes) -> bool:
    """Vérifie sommairement qu'un contenu est bien du HTML."""
    head = data[:4096].lstrip().lower()
    return b"<html" in head or b"<!doctype html" in head or b"<head" in head


def convert_uploads(
    uploads: Iterable[tuple[str, bytes]],
    progress: ProgressFn | None = None,
) -> list[ConvertedFile]:
    """Convertit des fichiers (nom, octets) et renvoie les résultats en mémoire.

    Les fichiers non HTML sont ignorés. Un dossier temporaire sert d'espace de
    travail au cœur, puis tout est relu avant sa suppression.
    """
    uploads = [(name, data) for name, data in uploads if is_html(data)]
    converted: list[ConvertedFile] = []
    if not uploads:
        return converted

    profiles = get_profiles()
    with tempfile.TemporaryDirectory() as tmp:
        in_dir = Path(tmp) / "in"
        out_dir = Path(tmp) / "out"
        in_dir.mkdir()
        out_dir.mkdir()
        taken: set[Path] = set()
        total = len(uploads)
        for index, (name, data) in enumerate(uploads, start=1):
            source = in_dir / Path(name).name
            source.write_bytes(data)
            result = process_file(source, out_dir, profiles, taken=taken)
            converted.append(_collect(result))
            if progress:
                progress(index, total, name)
    return converted


def convert_folder(folder: Path, progress: ProgressFn | None = None) -> list[ConvertedFile]:
    """Convertit tous les ``.html`` d'un dossier (récursif), résultats en mémoire."""
    files = sorted(folder.rglob("*.html"))
    uploads = [(str(f.relative_to(folder)), f.read_bytes()) for f in files]
    return convert_uploads(uploads, progress)


def build_zip(converted: list[ConvertedFile]) -> bytes:
    """Assemble les Markdown et leurs images dans une archive ZIP."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in converted:
            archive.writestr(item.md_name, item.md_bytes)
            for rel_path, data in item.assets.items():
                archive.writestr(rel_path, data)
    return buffer.getvalue()


def _collect(result: Result) -> ConvertedFile:
    """Relit en mémoire le Markdown et les images écrits par le cœur."""
    md_path = result.output
    assert md_path is not None  # process_file ne renvoie None que sur erreur amont
    assets: dict[str, bytes] = {}
    assets_dir = md_path.parent / f"{md_path.stem}_assets"
    if assets_dir.is_dir():
        for asset in sorted(assets_dir.rglob("*")):
            if asset.is_file():
                assets[f"{assets_dir.name}/{asset.name}"] = asset.read_bytes()
    return ConvertedFile(
        result=result,
        md_name=md_path.name,
        md_bytes=md_path.read_bytes(),
        assets=assets,
    )

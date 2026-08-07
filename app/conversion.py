"""Adaptateurs entre le cœur ``fast_to_md`` (disque) et l'app web (mémoire).

Le cœur (`fast_to_md.core.process_file`) lit un fichier et écrit le Markdown +
les images sur disque. L'app web reçoit des octets et doit proposer un
téléchargement : on passe donc par un dossier temporaire puis on relit le
résultat en mémoire.

Le format d'entrée est déterminé par l'extension du fichier, comme dans le
cœur : c'est elle qui décide du chemin de conversion suivi.
"""

from __future__ import annotations

import io
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from fast_to_md.core import Result, process_file
from fast_to_md.extract import Profile, load_profiles
from fast_to_md.sources import SUPPORTED_EXTENSIONS, is_supported, iter_sources

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


def supported_upload_types() -> list[str]:
    """Extensions sans le point, pour le sélecteur de fichiers de Streamlit."""
    return sorted(ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS)


def convert_uploads(
    uploads: Iterable[tuple[str, bytes]],
    progress: ProgressFn | None = None,
) -> list[ConvertedFile]:
    """Convertit des fichiers (nom, octets) et renvoie les résultats en mémoire.

    Les formats non pris en charge sont ignorés. Un dossier temporaire sert
    d'espace de travail au cœur, puis tout est relu avant sa suppression. Un
    fichier illisible n'interrompt pas le lot : il ressort en erreur.
    """
    uploads = [(name, data) for name, data in uploads if is_supported(Path(name))]
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
            try:
                result = process_file(source, out_dir, profiles, taken=taken)
                converted.append(_collect(result))
            except Exception as exc:  # un fichier corrompu ne doit pas stopper le lot
                converted.append(_failure(source, name, exc))
            if progress:
                progress(index, total, name)
    return converted


def convert_folder(folder: Path, progress: ProgressFn | None = None) -> list[ConvertedFile]:
    """Convertit tous les documents d'un dossier (récursif), résultats en mémoire."""
    files = iter_sources(folder)
    uploads = [(str(f.relative_to(folder)), f.read_bytes()) for f in files]
    return convert_uploads(uploads, progress)


def build_zip(converted: list[ConvertedFile]) -> bytes:
    """Assemble les Markdown et leurs images dans une archive ZIP."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in converted:
            if item.result.status == "error":
                continue
            archive.writestr(item.md_name, item.md_bytes)
            for rel_path, data in item.assets.items():
                archive.writestr(rel_path, data)
    return buffer.getvalue()


def _failure(source: Path, name: str, exc: Exception) -> ConvertedFile:
    """Enveloppe une conversion échouée pour qu'elle apparaisse dans le récapitulatif."""
    return ConvertedFile(
        result=Result(
            source=source, output=None, strategy="-", chars_in=0,
            chars_out=0, images=0, status="error", detail=str(exc),
        ),
        md_name=name,
        md_bytes=b"",
    )


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

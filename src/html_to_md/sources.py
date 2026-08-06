"""Routage des formats d'entrée vers le pipeline Markdown.

Le HTML garde le pipeline complet (extraction du contenu principal, hygiène) :
une page web est pleine de chrome à retirer. Les autres formats n'ont pas ce
problème — un .docx ne contient que du contenu — et sont donc convertis en
amont, puis rejoignent la fin du pipeline (titres, images, Markdown).

Deux moteurs selon le format :

- ``.docx`` → HTML intermédiaire, avec les images en data-URI et les tableaux
  en ``<table>``. Le reste du pipeline sait déjà exporter les unes et
  convertir les autres, il n'y a donc rien de spécifique à écrire ;
- autres formats → Markdown produit directement. Les images embarquées ne
  sont pas récupérables par cette voie : la sortie est textuelle (tableaux
  compris). C'est assumé — ces formats sont le filet de sécurité, pas le
  cœur de l'outil.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

HTML_EXTENSIONS = frozenset({".html", ".htm"})

# Converti en HTML avant d'entrer dans le pipeline : images et tableaux
# survivent jusqu'au Markdown final.
RICH_EXTENSIONS = frozenset({".docx"})

# Converti directement en Markdown : texte et tableaux, sans les images.
TEXT_EXTENSIONS = frozenset(
    {".pptx", ".xlsx", ".xls", ".pdf", ".epub", ".msg", ".csv", ".ipynb"}
)

SUPPORTED_EXTENSIONS = HTML_EXTENSIONS | RICH_EXTENSIONS | TEXT_EXTENSIONS


class UnsupportedFormat(ValueError):
    """Extension hors du périmètre de l'outil."""


@dataclass
class Ingested:
    """Contenu d'un fichier non-HTML, prêt pour la fin du pipeline.

    ``html`` et ``markdown`` s'excluent : ``kind`` dit lequel est renseigné.
    """

    kind: str  # "html" | "markdown"
    engine: str  # libellé affiché dans les rapports de conversion
    html: str = ""
    markdown: str = ""


def is_html(path: Path) -> bool:
    return path.suffix.lower() in HTML_EXTENSIONS


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def iter_sources(folder: Path) -> list[Path]:
    """Fichiers convertibles d'un dossier, récursivement et triés."""
    return sorted(p for p in folder.rglob("*") if p.is_file() and is_supported(p))


def ingest(source: Path) -> Ingested:
    """Convertit un fichier non-HTML en HTML ou en Markdown.

    Raises:
        UnsupportedFormat: extension inconnue, ou HTML (qui ne passe pas par
            ici mais par le pipeline complet).
    """
    suffix = source.suffix.lower()
    if suffix in RICH_EXTENSIONS:
        return _ingest_docx(source)
    if suffix in TEXT_EXTENSIONS:
        return _ingest_markitdown(source)
    raise UnsupportedFormat(f"format non pris en charge : {suffix or source.name}")


def _ingest_docx(source: Path) -> Ingested:
    try:
        import mammoth
    except ImportError as exc:  # pragma: no cover - dépend de l'installation
        raise _missing_dependency("docx") from exc

    with source.open("rb") as handle:
        conversion = mammoth.convert_to_html(handle)
    return Ingested(kind="html", engine="docx", html=conversion.value)


def _ingest_markitdown(source: Path) -> Ingested:
    try:
        from markitdown import MarkItDown
    except ImportError as exc:  # pragma: no cover - dépend de l'installation
        raise _missing_dependency("docs") from exc

    conversion = MarkItDown().convert(source)
    markdown = _drop_image_placeholders(conversion.text_content)
    return Ingested(
        kind="markdown",
        engine=f"doc:{source.suffix.lower().lstrip('.')}",
        markdown=markdown,
    )


def _missing_dependency(extra: str) -> ImportError:
    return ImportError(
        f"dépendance manquante pour ce format — installer avec "
        f"`uv sync --extra {extra}`"
    )


# Le moteur des formats texte n'extrait pas les images : il laisse un lien
# data-URI tronqué (« ![](data:image/png;base64...) ») qui ne pointe sur rien.
# On le retire pour ne pas polluer les notes, en gardant le texte alternatif.
_IMAGE_PLACEHOLDER = re.compile(r"!\[([^\]]*)\]\(\s*data:[^)]*\.\.\.\s*\)")


def _drop_image_placeholders(markdown: str) -> str:
    cleaned = _IMAGE_PLACEHOLDER.sub(lambda m: m.group(1), markdown)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip() + "\n"

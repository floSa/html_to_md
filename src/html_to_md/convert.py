"""Conversion du HTML extrait en Markdown + gestion des images data-URI."""

from __future__ import annotations

import base64
import re
from pathlib import Path

from bs4 import BeautifulSoup, NavigableString, Tag
from markdownify import MarkdownConverter

# En dessous de cette taille, une image data-URI est considérée comme une
# icône d'interface et supprimée (son texte alt est conservé s'il existe).
MIN_IMAGE_BYTES = 4096

_DATA_URI_RE = re.compile(r"^data:image/(?P<ext>[a-zA-Z0-9.+-]+);base64,(?P<data>.*)$", re.DOTALL)

_EXT_NORMALIZE = {"jpeg": "jpg", "svg+xml": "svg"}


def export_data_uri_images(soup: BeautifulSoup, assets_dir: Path, min_bytes: int = MIN_IMAGE_BYTES) -> int:
    """Extrait les images base64 vers ``assets_dir`` et réécrit les ``src``.

    Les images plus petites que ``min_bytes`` (icônes, puces) sont retirées.

    Returns:
        Nombre d'images exportées sur disque.
    """
    exported = 0
    for img in soup.find_all("img"):
        match = _DATA_URI_RE.match(img.get("src", ""))
        if not match:
            continue
        try:
            payload = base64.b64decode(match.group("data"), validate=False)
        except Exception:
            img.decompose()
            continue

        if len(payload) < min_bytes:
            # Icône d'interface : on la jette, alt compris (texte d'UI, pas de contenu).
            img.decompose()
            continue

        ext = _EXT_NORMALIZE.get(match.group("ext").lower(), match.group("ext").lower())
        assets_dir.mkdir(parents=True, exist_ok=True)
        filename = f"img_{exported:03d}.{ext}"
        (assets_dir / filename).write_bytes(payload)
        img["src"] = f"{assets_dir.name}/{filename}"
        exported += 1
    return exported


# Décorations d'ancres fréquentes à l'intérieur des titres (liens « # », « ¶ »).
_ANCHOR_DECORATIONS = {"#", "##", "¶", "§"}


def tidy_headings(soup: BeautifulSoup) -> None:
    """Retire les décorations d'ancres dans les titres (ex. « ## # Intro »)."""
    for heading in soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"]):
        for child in list(heading.children):
            if isinstance(child, Tag) and child.get_text(strip=True) in _ANCHOR_DECORATIONS:
                child.decompose()
            elif isinstance(child, NavigableString) and child.strip() in _ANCHOR_DECORATIONS:
                child.extract()


class _Converter(MarkdownConverter):
    """Markdownify configuré : titres ATX, langage des blocs de code O'Reilly."""

    class Options(MarkdownConverter.Options):
        heading_style = "ATX"
        bullets = "-"

    def convert_pre(self, el, text, parent_tags):
        language = el.get("data-code-language") or el.get("data-lang") or ""
        if not text:
            return ""
        return f"\n\n```{language}\n{text.strip()}\n```\n\n"


def to_markdown(html_fragment: str) -> str:
    """Convertit un fragment HTML en Markdown normalisé."""
    md = _Converter().convert(html_fragment)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n"

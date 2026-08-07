"""Orchestration du traitement d'un fichier : hygiène → extraction → Markdown.

Deux chemins selon le format d'entrée (voir ``sources``) : le HTML passe par le
pipeline complet, les autres documents par un chemin plus court qui saute le
nettoyage de page web mais partage la même fin de traitement.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

import re

from .convert import (
    MIN_IMAGE_BYTES,
    export_data_uri_images,
    promote_table_headers,
    tidy_headings,
    to_markdown,
)
from .extract import Profile, extract_content
from .hygiene import clean_soup
from .maths import extract_math, restore_math
from .naming import article_slug, output_basename, singlefile_url, site_slug, split_title
from .sources import ingest, is_html

# Si le Markdown final conserve moins de cette fraction du texte visible
# d'origine, le fichier est signalé pour revue manuelle (contenu peut-être
# perdu par le nettoyage). Le texte d'origine inclut le chrome du lecteur,
# donc un ratio sain reste généralement bien au-dessus.
WARN_RATIO = 0.30
MIN_OUTPUT_CHARS = 200


@dataclass
class Result:
    source: Path
    output: Path | None
    strategy: str
    chars_in: int
    chars_out: int
    images: int
    status: str  # "ok" | "review" | "error"
    detail: str = ""

    @property
    def ratio(self) -> float:
        return self.chars_out / self.chars_in if self.chars_in else 0.0


def process_file(
    source: Path,
    out_dir: Path,
    profiles: list[Profile],
    min_image_bytes: int = MIN_IMAGE_BYTES,
    taken: set[Path] | None = None,
) -> Result:
    """Convertit ``source`` et écrit le Markdown dans ``out_dir``.

    Le fichier de sortie est nommé d'après le document (``<site>_<Titre>.md``
    pour une page web, ``<Nom_Du_Fichier>.md`` sinon). Les images de contenu
    sont exportées dans un dossier ``<nom>_assets`` à côté. ``taken`` (partagé
    entre les fichiers d'un même lot) évite les collisions de noms.
    """
    if is_html(source):
        return _process_html(source, out_dir, profiles, min_image_bytes, taken)
    return _process_document(source, out_dir, taken)


def _process_html(
    source: Path,
    out_dir: Path,
    profiles: list[Profile],
    min_image_bytes: int,
    taken: set[Path] | None,
) -> Result:
    """Pipeline complet des captures de pages web."""
    raw_html = source.read_text(encoding="utf-8", errors="replace")
    soup = BeautifulSoup(raw_html, "lxml")
    chars_in = len(soup.get_text(" ", strip=True))
    page_title = soup.title.get_text(strip=True) if soup.title else ""
    article_title, site_name = split_title(page_title)

    formulas = extract_math(soup)  # avant l'hygiène, qui supprime <script>/<svg>
    clean_soup(soup)
    extraction = extract_content(soup, profiles)

    content = BeautifulSoup(extraction.html, "lxml")
    for selector in extraction.strip:
        for tag in content.select(selector):
            tag.decompose()
    tidy_headings(content)
    promote_table_headers(content)

    # Nom de sortie : <site>_<titre>. Le titre vient du H1 du contenu,
    # sinon du <title> de la page, sinon du nom du fichier source.
    h1 = content.find("h1")
    title_for_name = h1.get_text(strip=True) if h1 else (article_title or source.stem)
    base = output_basename(
        site_slug(site_name, singlefile_url(raw_html)),
        article_slug(title_for_name),
        fallback=source.stem,
    )
    output = _reserve_output(out_dir, base, taken)

    assets_dir = output.parent / f"{output.stem}_assets"
    images = export_data_uri_images(content, assets_dir, min_bytes=min_image_bytes)

    markdown = to_markdown(str(content))
    markdown = restore_math(markdown, formulas)
    markdown = _ensure_title(markdown, article_title or page_title)
    chars_out = len(markdown)

    _write(output, markdown)

    status, detail = "ok", ""
    if chars_out < MIN_OUTPUT_CHARS:
        status, detail = "review", f"sortie très courte ({chars_out} caractères)"
    elif chars_in and chars_out / chars_in < WARN_RATIO:
        status, detail = "review", f"ratio faible ({chars_out}/{chars_in})"

    return Result(
        source=source,
        output=output,
        strategy=extraction.strategy,
        chars_in=chars_in,
        chars_out=chars_out,
        images=images,
        status=status,
        detail=detail,
    )


def _process_document(
    source: Path,
    out_dir: Path,
    taken: set[Path] | None,
) -> Result:
    """Pipeline des documents bureautiques : pas de chrome de page à retirer.

    L'extraction du contenu principal et l'hygiène HTML sont volontairement
    sautées : sur un document déjà propre, elles ne feraient que risquer de
    supprimer du contenu légitime.
    """
    ingested = ingest(source)

    base = output_basename("", article_slug(source.stem), fallback=source.stem)
    output = _reserve_output(out_dir, base, taken)
    assets_dir = output.parent / f"{output.stem}_assets"

    if ingested.kind == "html":
        content = BeautifulSoup(ingested.html, "lxml")
        chars_in = len(content.get_text(" ", strip=True))
        tidy_headings(content)
        promote_table_headers(content)
        # Pas de filtre de taille sur les images : contrairement à une page
        # web, un document n'a pas d'icônes d'interface — la moindre vignette
        # y est du contenu (schéma, logo, capture).
        images = export_data_uri_images(content, assets_dir, min_bytes=0)
        markdown = to_markdown(str(content))
    else:
        markdown = ingested.markdown
        chars_in = len(markdown)
        images = 0

    markdown = _ensure_title(markdown, source.stem)
    chars_out = len(markdown)

    _write(output, markdown)

    # Pas de contrôle de ratio ici : rien n'a été retiré, seule une sortie
    # quasi vide (document illisible ou protégé) mérite une revue.
    status, detail = "ok", ""
    if chars_out < MIN_OUTPUT_CHARS:
        status, detail = "review", f"sortie très courte ({chars_out} caractères)"

    return Result(
        source=source,
        output=output,
        strategy=ingested.engine,
        chars_in=chars_in,
        chars_out=chars_out,
        images=images,
        status=status,
        detail=detail,
    )


def _reserve_output(out_dir: Path, base: str, taken: set[Path] | None) -> Path:
    """Chemin de sortie unique pour ``base``, suffixé en cas de collision."""
    output = out_dir / f"{base}.md"
    if taken is None:
        return output
    suffix = 2
    while output in taken:
        output = out_dir / f"{base}_{suffix}.md"
        suffix += 1
    taken.add(output)
    return output


def _ensure_title(markdown: str, title: str) -> str:
    """Garantit un titre de document, repris du contexte si aucun H1 n'a survécu."""
    if not title or re.search(r"^# ", markdown, re.MULTILINE):
        return markdown
    return f"# {title}\n\n{markdown}"


def _write(output: Path, markdown: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")

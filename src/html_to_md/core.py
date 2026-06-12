"""Orchestration du traitement d'un fichier : hygiène → extraction → Markdown."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

import re

from .convert import MIN_IMAGE_BYTES, export_data_uri_images, tidy_headings, to_markdown
from .extract import Profile, extract_content
from .hygiene import clean_soup
from .maths import extract_math, restore_math
from .naming import article_slug, output_basename, singlefile_url, site_slug, split_title

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
    """Nettoie ``source`` et écrit le Markdown dans ``out_dir``.

    Le fichier de sortie est nommé ``<source>_<Titre_Article>.md`` (ex.
    ``machine_learning_mastery_Essence_of_Bagging.md``). Les images de
    contenu (data-URI) sont exportées dans un dossier ``<nom>_assets`` à côté.
    ``taken`` (partagé entre les fichiers d'un même lot) évite les collisions
    de noms.
    """
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

    # Nom de sortie : <site>_<titre>. Le titre vient du H1 du contenu,
    # sinon du <title> de la page, sinon du nom du fichier source.
    h1 = content.find("h1")
    title_for_name = h1.get_text(strip=True) if h1 else (article_title or source.stem)
    base = output_basename(
        site_slug(site_name, singlefile_url(raw_html)),
        article_slug(title_for_name),
        fallback=source.stem,
    )
    output = out_dir / f"{base}.md"
    if taken is not None:
        suffix = 2
        while output in taken:
            output = out_dir / f"{base}_{suffix}.md"
            suffix += 1
        taken.add(output)

    assets_dir = output.parent / f"{output.stem}_assets"
    images = export_data_uri_images(content, assets_dir, min_bytes=min_image_bytes)

    markdown = to_markdown(str(content))
    markdown = restore_math(markdown, formulas)
    # Garantit un titre de document : si aucun H1 n'a survécu à l'extraction,
    # on reprend le titre d'article du <title> de la page.
    if not re.search(r"^# ", markdown, re.MULTILINE) and (article_title or page_title):
        markdown = f"# {article_title or page_title}\n\n{markdown}"
    chars_out = len(markdown)

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(markdown, encoding="utf-8")

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

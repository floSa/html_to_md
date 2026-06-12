"""Nommage des fichiers de sortie : ``<source>_<Titre_De_L_Article>.md``.

La source (nom du site, pas l'URL) est déduite en priorité du suffixe du
``<title>`` (« Mon Article - MonSite.com »), sinon du domaine de l'URL que
SingleFile inscrit dans le commentaire d'en-tête du fichier.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

# Séparateurs usuels entre titre d'article et nom de site dans <title>.
_TITLE_SEP = re.compile(r"\s+[-–—|·»]\s+")

# Métadonnée écrite par SingleFile en tête de capture : "url: https://..."
_SINGLEFILE_URL = re.compile(r"\burl:\s*(https?://\S+)")

_MAX_SLUG_LEN = 80


def singlefile_url(raw_html: str) -> str | None:
    """URL d'origine inscrite par SingleFile dans son commentaire d'en-tête."""
    match = _SINGLEFILE_URL.search(raw_html[:2000])
    return match.group(1) if match else None


def split_title(title: str) -> tuple[str, str]:
    """Sépare ``<title>`` en (titre d'article, nom de site).

    « Essence of Bagging - MachineLearningMastery.com » →
    (« Essence of Bagging », « MachineLearningMastery.com »).
    Sans séparateur reconnu, le site est vide.
    """
    parts = _TITLE_SEP.split(title.strip())
    if len(parts) >= 2:
        return " ".join(parts[:-1]).strip(), parts[-1].strip()
    return title.strip(), ""


def site_slug(site_name: str, url: str | None) -> str:
    """Slug snake_case du nom de site : « MachineLearningMastery.com » →
    « machine_learning_mastery ». Repli sur le domaine de l'URL."""
    name = site_name.strip()
    if not name and url:
        host = urlparse(url).hostname or ""
        name = host.removeprefix("www.").split(".")[0]
    if not name:
        return ""
    name = re.sub(r"\.[a-z]{2,6}$", "", name, flags=re.I)  # retire .com/.fr/...
    name = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", name)    # découpe le CamelCase
    return _slugify(name).lower()


def article_slug(title: str) -> str:
    """Slug du titre d'article, casse conservée : « Essence of Bagging » →
    « Essence_of_Bagging »."""
    return _slugify(title)[:_MAX_SLUG_LEN].strip("_")


def output_basename(site: str, article: str, fallback: str) -> str:
    """Nom de base du fichier de sortie (sans extension)."""
    base = "_".join(part for part in (site, article) if part)
    return base or _slugify(fallback)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^\w]+", "_", text, flags=re.UNICODE)
    return re.sub(r"_+", "_", slug).strip("_")

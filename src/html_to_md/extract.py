"""Extraction du contenu utile : profils par éditeur, puis repli readability."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml
from bs4 import BeautifulSoup, Tag

# En dessous de ce volume de texte, une extraction est considérée comme ratée
# et on passe à la stratégie suivante.
MIN_CONTENT_CHARS = 200

# Conteneurs sémantiques standard (HTML5) essayés en mode générique,
# du plus précis au plus large.
GENERIC_SELECTORS = ["article", "main", "[role=main]"]


@dataclass
class Profile:
    name: str
    detect: str
    content: str
    strip: list[str] = field(default_factory=list)


@dataclass
class Extraction:
    html: str          # fragment HTML du contenu retenu
    strategy: str      # nom du profil, "readability" ou "body"
    strip: list[str] = field(default_factory=list)


def load_profiles(config_path: Path) -> list[Profile]:
    """Charge les profils d'extraction depuis le YAML de configuration."""
    data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    return [
        Profile(
            name=name,
            detect=cfg["detect"],
            content=cfg["content"],
            strip=cfg.get("strip", []),
        )
        for name, cfg in (data.get("profiles") or {}).items()
    ]


def _top_level_only(tags: list[Tag]) -> list[Tag]:
    """Ne garde que les éléments dont aucun ancêtre n'est lui-même sélectionné.

    Évite les doublons quand le sélecteur matche des sections imbriquées
    (ex. ``section[data-type]`` chez O'Reilly).
    """
    selected = set(id(t) for t in tags)
    return [t for t in tags if not any(id(p) in selected for p in t.parents)]


def extract_content(soup: BeautifulSoup, profiles: list[Profile]) -> Extraction:
    """Isole le contenu utile d'une page déjà passée par la passe d'hygiène.

    Les profils utilisateur (s'il y en a) ont priorité. Sinon, mode générique :
    on compare les conteneurs sémantiques HTML5 et l'extraction readability, et
    on garde la version qui conserve le plus de texte (readability peut
    tronquer ; un conteneur sémantique peut garder un peu de bruit — le
    Markdown le plus complet est le moins risqué pour l'ingestion).
    En dernier recours, le <body> nettoyé tel quel.
    """
    for profile in profiles:
        if not soup.select_one(profile.detect):
            continue
        tags = _top_level_only(soup.select(profile.content))
        text_len = sum(len(t.get_text(strip=True)) for t in tags)
        if text_len >= MIN_CONTENT_CHARS:
            return Extraction(
                html="\n".join(str(t) for t in tags),
                strategy=profile.name,
                strip=profile.strip,
            )

    candidates: list[tuple[int, Extraction]] = []

    for selector in GENERIC_SELECTORS:
        tags = _top_level_only(soup.select(selector))
        text_len = sum(len(t.get_text(strip=True)) for t in tags)
        if text_len >= MIN_CONTENT_CHARS:
            candidates.append(
                (text_len, Extraction(html="\n".join(str(t) for t in tags), strategy=selector))
            )
            break  # le premier conteneur sémantique trouvé suffit

    # readability sur le HTML déjà nettoyé, pour ne pas réintroduire le bruit
    # supprimé par la passe d'hygiène.
    fragment = _readability(str(soup))
    if fragment is not None:
        text_len = len(BeautifulSoup(fragment, "lxml").get_text(strip=True))
        candidates.append((text_len, Extraction(html=fragment, strategy="readability")))

    if candidates:
        return max(candidates, key=lambda c: c[0])[1]

    body = soup.body or soup
    return Extraction(html=str(body), strategy="body")


def _readability(html: str) -> str | None:
    """Extraction générique via readability-lxml ; None si trop court ou en échec."""
    try:
        from readability import Document

        summary = Document(html).summary(html_partial=True)
        probe = BeautifulSoup(summary, "lxml")
        if len(probe.get_text(strip=True)) >= MIN_CONTENT_CHARS:
            return summary
    except Exception:
        pass
    return None

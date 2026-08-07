"""Passe d'hygiène : retire le bruit propre aux captures SingleFile.

Cette passe est volontairement conservatrice : elle ne supprime que ce qui ne
peut pas être du contenu (scripts, styles, éléments cachés, chrome de
navigation). L'isolement du contenu utile est fait ensuite par ``extract``.
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Comment

# Balises qui ne portent jamais de contenu à ingérer.
NOISE_TAGS = ["script", "style", "link", "meta", "noscript", "iframe", "svg", "template", "button"]

# Chrome de page toujours supprimé. header/footer sont traités à part :
# à l'intérieur d'un <article>/<main> ils portent souvent le titre ou la
# signature de l'article, on les garde.
CHROME_TAGS = ["nav", "aside"]

# Classes marquées par SingleFile lui-même ou typiques des lecteurs en ligne.
NOISE_CLASSES = ["sf-hidden"]

NOISE_SELECTORS = [
    "[role=navigation]",
    "[role=banner]",
    "[role=complementary]",
    "[role=contentinfo]",
    "[role=dialog]",
    "[aria-modal=true]",
    # Widgets « articles liés » des plugins WordPress courants.
    ".crp_related",
    ".yarpp-related",
    ".jp-relatedposts",
]


def _decompose_all(tags) -> None:
    """Décompose une liste de tags en ignorant ceux déjà décomposés.

    Un tag dont l'ancêtre a été supprimé par une boucle précédente a ses
    attributs à ``None`` : le toucher lèverait une AttributeError.
    """
    for tag in tags:
        if not tag.decomposed:
            tag.decompose()


def clean_soup(soup: BeautifulSoup) -> None:
    """Supprime in-place le bruit non ambigu d'une soupe SingleFile."""
    _decompose_all(soup.find_all(NOISE_TAGS))
    _decompose_all(soup.find_all(CHROME_TAGS))

    # header/footer : supprimés sauf à l'intérieur d'un article/main.
    _decompose_all(
        tag
        for tag in soup.find_all(["header", "footer"])
        if not tag.decomposed and not tag.find_parent(["article", "main"])
    )

    for class_name in NOISE_CLASSES:
        _decompose_all(soup.find_all(class_=class_name))

    for selector in NOISE_SELECTORS:
        _decompose_all(soup.select(selector))

    # Éléments cachés en dur (display:none / visibility:hidden / attribut hidden).
    _decompose_all(soup.find_all(hidden=True))
    _decompose_all(
        tag
        for tag in soup.find_all(style=True)
        if not tag.decomposed
        and (
            "display:none" in (style := tag.get("style", "").replace(" ", "").lower())
            or "visibility:hidden" in style
        )
    )

    for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

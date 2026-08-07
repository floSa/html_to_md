"""Conversion des formules mathématiques rendues (KaTeX, MathJax, MathML) en LaTeX.

Les moteurs de rendu web gardent presque toujours la source LaTeX dans le DOM :
- KaTeX : ``<annotation encoding="application/x-tex">`` dans ``.katex-mathml`` ;
- MathJax v2 : ``<script type="math/tex">`` à côté du rendu ;
- MathJax v3 : ``<mjx-container>`` (annotation ou aria-label) ;
- MathML natif : ``<math>`` (annotation éventuelle).

Chaque formule est remplacée par un jeton alphanumérique (qui traverse la
conversion Markdown sans être échappé), puis le jeton est substitué par
``$...$`` (inline) ou ``$$...$$`` (bloc) dans le Markdown final.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

_MATH_TEX_TYPE = re.compile(r"^\s*math/tex", re.I)
_TOKEN = "ZZMATHTOKEN{i}ZZ"
_TOKEN_RE = re.compile(r"ZZMATHTOKEN(\d+)ZZ")

# Restes de rendu MathJax v2 à purger une fois la source récupérée.
_MATHJAX_RENDER_SELECTORS = [
    ".MathJax", ".MathJax_Display", ".MathJax_Preview",
    ".MathJax_SVG", ".MathJax_SVG_Display", ".MathJax_CHTML",
]


@dataclass
class Formula:
    latex: str
    display: bool  # True = formule en bloc ($$), False = inline ($)


def extract_math(soup: BeautifulSoup) -> list[Formula]:
    """Remplace in-place chaque formule par un jeton ; retourne les formules.

    À appeler AVANT la passe d'hygiène (qui supprime <script> et <svg>).
    """
    formulas: list[Formula] = []

    def tokenize(element: Tag, latex: str, display: bool) -> None:
        latex = latex.strip()
        if not latex:
            element.decompose()
            return
        element.replace_with(_TOKEN.format(i=len(formulas)))
        formulas.append(Formula(latex=latex, display=display))

    # MathJax v2 : la source est dans un <script type="math/tex[; mode=display]">.
    for script in soup.find_all("script", type=_MATH_TEX_TYPE):
        display = "mode=display" in (script.get("type") or "")
        tokenize(script, script.get_text(), display)
    for selector in _MATHJAX_RENDER_SELECTORS:
        for leftover in soup.select(selector):
            leftover.decompose()

    # KaTeX : on remplace .katex-display entier si présent, sinon .katex.
    for katex in soup.select(".katex"):
        if katex.decomposed:
            continue
        annotation = katex.select_one('annotation[encoding="application/x-tex"]')
        latex = annotation.get_text() if annotation else katex.get_text(" ", strip=True)
        wrapper = katex.find_parent(class_="katex-display")
        tokenize(wrapper or katex, latex, display=wrapper is not None)

    # MathJax v3 : <mjx-container display="true|false">.
    for container in soup.find_all("mjx-container"):
        annotation = container.select_one('annotation[encoding="application/x-tex"]')
        latex = (
            annotation.get_text()
            if annotation
            else container.get("aria-label") or container.get_text(" ", strip=True)
        )
        tokenize(container, latex, display=container.get("display") == "true")

    # MathML natif restant.
    for math in soup.find_all("math"):
        if math.decomposed:
            continue
        annotation = math.select_one('annotation[encoding="application/x-tex"]')
        latex = annotation.get_text() if annotation else math.get_text(" ", strip=True)
        tokenize(math, latex, display=math.get("display") == "block")

    return formulas


def restore_math(markdown: str, formulas: list[Formula]) -> str:
    """Substitue les jetons par leur LaTeX dans le Markdown final."""

    def replace(match: re.Match) -> str:
        formula = formulas[int(match.group(1))]
        if formula.display:
            return f"\n\n$$\n{formula.latex}\n$$\n\n"
        return f"${formula.latex}$"

    markdown = _TOKEN_RE.sub(replace, markdown)
    return re.sub(r"\n{3,}", "\n\n", markdown)

"""Briques de conversion : images, tableaux, titres."""

from __future__ import annotations

import base64
from pathlib import Path

from bs4 import BeautifulSoup

from html_to_md.convert import (
    export_data_uri_images,
    promote_table_headers,
    tidy_headings,
    to_markdown,
)

from conftest import make_png


def _img_html(payload: bytes, alt: str = "") -> str:
    encoded = base64.b64encode(payload).decode()
    return f'<img src="data:image/png;base64,{encoded}" alt="{alt}">'


class TestExportDesImages:
    def test_image_exportee_et_lien_reecrit(self, tmp_path: Path) -> None:
        payload = make_png(60, 60, seed=3)
        soup = BeautifulSoup(_img_html(payload), "lxml")
        assets = tmp_path / "doc_assets"

        count = export_data_uri_images(soup, assets, min_bytes=0)

        assert count == 1
        assert (assets / "img_000.png").read_bytes() == payload
        assert soup.find("img")["src"] == "doc_assets/img_000.png"

    def test_sous_le_seuil_limage_est_retiree(self, tmp_path: Path) -> None:
        soup = BeautifulSoup(_img_html(make_png(4, 4, seed=4), alt="icône"), "lxml")

        count = export_data_uri_images(soup, tmp_path / "a", min_bytes=4096)

        assert count == 0
        assert soup.find("img") is None

    def test_seuil_a_zero_garde_les_vignettes(self, tmp_path: Path) -> None:
        soup = BeautifulSoup(_img_html(make_png(20, 20, seed=5)), "lxml")

        assert export_data_uri_images(soup, tmp_path / "a", min_bytes=0) == 1

    def test_base64_invalide_ne_fait_pas_echouer(self, tmp_path: Path) -> None:
        soup = BeautifulSoup('<img src="data:image/png;base64,@@@">', "lxml")

        assert export_data_uri_images(soup, tmp_path / "a", min_bytes=0) == 0

    def test_les_images_distantes_sont_laissees_intactes(self, tmp_path: Path) -> None:
        soup = BeautifulSoup('<img src="https://example.com/a.png">', "lxml")

        assert export_data_uri_images(soup, tmp_path / "a", min_bytes=0) == 0
        assert soup.find("img")["src"] == "https://example.com/a.png"

    def test_numerotation_continue(self, tmp_path: Path) -> None:
        html = _img_html(make_png(40, 40, seed=6)) + _img_html(make_png(40, 40, seed=7))
        soup = BeautifulSoup(html, "lxml")
        assets = tmp_path / "doc_assets"

        assert export_data_uri_images(soup, assets, min_bytes=0) == 2
        assert sorted(p.name for p in assets.iterdir()) == ["img_000.png", "img_001.png"]


class TestEnTetesDeTableaux:
    """Sans <th>, le Markdown produit une ligne d'en-tête vide et rejette
    toutes les données dans le corps : la première ligne doit être promue."""

    def test_premiere_ligne_promue(self) -> None:
        soup = BeautifulSoup(
            "<table><tr><td>Produit</td><td>Prix</td></tr>"
            "<tr><td>Alpha</td><td>12</td></tr></table>",
            "lxml",
        )

        promote_table_headers(soup)
        markdown = to_markdown(str(soup))

        assert "| Produit | Prix |" in markdown
        assert markdown.index("| Produit | Prix |") < markdown.index("| --- |")

    def test_un_tableau_deja_en_tete_nest_pas_touche(self) -> None:
        soup = BeautifulSoup(
            "<table><tr><th>A</th></tr><tr><td>Ligne</td></tr></table>", "lxml"
        )

        promote_table_headers(soup)

        assert soup.find("td").get_text() == "Ligne"

    def test_tableau_vide_sans_erreur(self) -> None:
        soup = BeautifulSoup("<table></table>", "lxml")
        promote_table_headers(soup)  # ne doit pas lever

    def test_un_tableau_imbrique_ne_vole_pas_len_tete_du_parent(self) -> None:
        """La cellule promue pour le tableau parent doit être la sienne, pas
        celle du tableau qu'il contient."""
        soup = BeautifulSoup(
            "<table><tr><td>Parent<table><tr><td>Interne</td></tr></table></td></tr></table>",
            "lxml",
        )

        promote_table_headers(soup)

        outer = soup.find("table")
        header = outer.find("th")
        assert header.find("table") is not None  # c'est bien la cellule du parent


class TestTitres:
    def test_les_ancres_decoratives_disparaissent(self) -> None:
        soup = BeautifulSoup("<h2><a>#</a>Introduction</h2>", "lxml")

        tidy_headings(soup)

        assert soup.find("h2").get_text(strip=True) == "Introduction"


class TestMarkdown:
    def test_le_langage_des_blocs_de_code_est_conserve(self) -> None:
        markdown = to_markdown('<pre data-code-language="python"><code>x = 1</code></pre>')

        assert "```python" in markdown

    def test_titres_atx_et_puces_normalisees(self) -> None:
        markdown = to_markdown("<h1>Titre</h1><ul><li>Un</li></ul>")

        assert markdown.startswith("# Titre")
        assert "- Un" in markdown

    def test_sortie_terminee_par_un_saut_de_ligne(self) -> None:
        assert to_markdown("<p>Texte</p>").endswith("\n")

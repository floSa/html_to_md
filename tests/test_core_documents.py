"""Pipeline des documents bureautiques."""

from __future__ import annotations

from pathlib import Path

import pytest

from html_to_md.core import process_file
from html_to_md.sources import UnsupportedFormat


class TestWord:
    def test_les_images_atterrissent_a_cote_du_markdown(
        self, tmp_path: Path, docx_factory, no_profiles
    ) -> None:
        """Le lien doit être relatif au fichier Markdown : c'est ce qui permet
        d'ouvrir la note dans un éditeur sans réparer les chemins."""
        out = tmp_path / "out"

        result = process_file(docx_factory(), out, no_profiles)
        markdown = result.output.read_text(encoding="utf-8")
        assets = out / f"{result.output.stem}_assets"

        assert result.images == 2
        assert sorted(p.name for p in assets.iterdir()) == ["img_000.png", "img_001.png"]
        assert f"({assets.name}/img_000.png)" in markdown

    def test_la_vignette_nest_pas_prise_pour_une_icone(
        self, tmp_path: Path, docx_factory, no_profiles
    ) -> None:
        """Le seuil qui écarte les icônes d'interface des pages web ne
        s'applique pas ici : dans un document, tout est du contenu."""
        result = process_file(docx_factory(), tmp_path / "out", no_profiles)

        small = tmp_path / "out" / f"{result.output.stem}_assets" / "img_001.png"
        assert small.exists()
        assert small.stat().st_size < 4096

    def test_le_tableau_a_un_vrai_en_tete(
        self, tmp_path: Path, docx_factory, no_profiles
    ) -> None:
        result = process_file(docx_factory(), tmp_path / "out", no_profiles)
        markdown = result.output.read_text(encoding="utf-8")

        assert "| Produit | Prix | Stock |" in markdown
        assert "|  |  |  |" not in markdown  # pas de ligne d'en-tête vide

    def test_le_texte_est_conserve_dans_lordre(
        self, tmp_path: Path, docx_factory, no_profiles
    ) -> None:
        result = process_file(docx_factory(), tmp_path / "out", no_profiles)
        markdown = result.output.read_text(encoding="utf-8")

        assert markdown.index("Un paragraphe avant image.") < markdown.index("| Produit")
        assert markdown.index("| Produit") < markdown.index("Texte après tableau.")

    def test_le_nom_du_fichier_sert_de_titre(
        self, tmp_path: Path, docx_factory, no_profiles
    ) -> None:
        result = process_file(docx_factory("Note de cadrage"), tmp_path / "out", no_profiles)

        assert result.output.name == "Note_de_cadrage.md"
        assert result.status == "ok"

    def test_le_moteur_est_reporte(
        self, tmp_path: Path, docx_factory, no_profiles
    ) -> None:
        result = process_file(docx_factory(), tmp_path / "out", no_profiles)

        assert result.strategy == "docx"


class TestPowerPoint:
    def test_le_texte_des_diapositives_est_recupere(
        self, tmp_path: Path, pptx_factory, no_profiles
    ) -> None:
        result = process_file(pptx_factory(), tmp_path / "out", no_profiles)
        markdown = result.output.read_text(encoding="utf-8")

        assert "Titre de la présentation" in markdown
        assert "Premier point" in markdown
        assert result.strategy == "doc:pptx"

    def test_aucune_image_nest_promise(
        self, tmp_path: Path, pptx_factory, no_profiles
    ) -> None:
        """Ces formats ressortent en texte : mieux vaut zéro image annoncée
        qu'un lien mort dans la note."""
        result = process_file(pptx_factory(), tmp_path / "out", no_profiles)

        assert result.images == 0
        assert "data:image" not in result.output.read_text(encoding="utf-8")


class TestDocumentIllisible:
    def test_un_fichier_corrompu_remonte_une_erreur(
        self, tmp_path: Path, no_profiles
    ) -> None:
        broken = tmp_path / "casse.docx"
        broken.write_bytes(b"ceci n'est pas un document")

        with pytest.raises(Exception):
            process_file(broken, tmp_path / "out", no_profiles)

    def test_un_format_hors_perimetre_est_refuse(
        self, tmp_path: Path, no_profiles
    ) -> None:
        photo = tmp_path / "photo.jpg"
        photo.write_bytes(b"factice")

        with pytest.raises(UnsupportedFormat):
            process_file(photo, tmp_path / "out", no_profiles)


class TestLotMixte:
    def test_les_formats_cohabitent_sans_collision(
        self, tmp_path: Path, docx_factory, pptx_factory, no_profiles
    ) -> None:
        out = tmp_path / "out"
        taken: set[Path] = set()

        results = [
            process_file(docx_factory("Meme nom"), out, no_profiles, taken=taken),
            process_file(pptx_factory("Meme nom"), out, no_profiles, taken=taken),
        ]

        assert results[0].output != results[1].output
        assert all(r.output.exists() for r in results)

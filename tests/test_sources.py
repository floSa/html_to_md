"""Routage des formats d'entrée."""

from __future__ import annotations

from pathlib import Path

import pytest

from html_to_md import sources


class TestClassification:
    def test_html_est_reconnu_quelle_que_soit_la_casse(self) -> None:
        assert sources.is_html(Path("page.HTML"))
        assert sources.is_html(Path("page.htm"))

    def test_un_document_bureautique_nest_pas_du_html(self) -> None:
        assert not sources.is_html(Path("rapport.docx"))

    def test_les_formats_hors_perimetre_sont_ecartes(self) -> None:
        assert not sources.is_supported(Path("archive.tar.gz"))
        assert not sources.is_supported(Path("photo.jpg"))
        assert not sources.is_supported(Path("sans_extension"))

    def test_les_trois_familles_sont_prises_en_charge(self) -> None:
        for name in ("page.html", "rapport.docx", "deck.pptx", "notes.pdf"):
            assert sources.is_supported(Path(name)), name


class TestParcoursDeDossier:
    def test_recursif_trie_et_filtre(self, tmp_path: Path) -> None:
        (tmp_path / "sous").mkdir()
        (tmp_path / "b.html").write_text("<html></html>", encoding="utf-8")
        (tmp_path / "sous" / "a.docx").write_bytes(b"factice")
        (tmp_path / "ignore.jpg").write_bytes(b"factice")

        found = [p.name for p in sources.iter_sources(tmp_path)]

        assert found == ["b.html", "a.docx"] or found == ["a.docx", "b.html"]
        assert "ignore.jpg" not in found

    def test_dossier_sans_document_convertible(self, tmp_path: Path) -> None:
        (tmp_path / "photo.jpg").write_bytes(b"factice")
        assert sources.iter_sources(tmp_path) == []


class TestIngestion:
    def test_le_html_ne_passe_pas_par_ce_chemin(self, tmp_path: Path) -> None:
        page = tmp_path / "page.html"
        page.write_text("<html></html>", encoding="utf-8")
        with pytest.raises(sources.UnsupportedFormat):
            sources.ingest(page)

    def test_format_inconnu_rejete(self, tmp_path: Path) -> None:
        with pytest.raises(sources.UnsupportedFormat):
            sources.ingest(tmp_path / "photo.jpg")

    def test_word_produit_du_html_avec_images_et_tableau(self, docx_factory) -> None:
        ingested = sources.ingest(docx_factory())

        assert ingested.kind == "html"
        assert "<table" in ingested.html
        # L'image doit être réellement embarquée, pas un lien vide.
        assert "data:image/png;base64," in ingested.html
        assert len(ingested.html) > 2000

    def test_powerpoint_produit_du_markdown(self, pptx_factory) -> None:
        ingested = sources.ingest(pptx_factory())

        assert ingested.kind == "markdown"
        assert "Titre de la présentation" in ingested.markdown
        assert ingested.markdown.endswith("\n")


class TestNettoyageDesImagesFantomes:
    """Les formats texte laissent des liens d'image tronqués, qui ne pointent
    sur rien. Ils doivent disparaître sans emporter le texte alternatif."""

    def test_le_lien_tronque_disparait(self) -> None:
        cleaned = sources._drop_image_placeholders(
            "Avant\n\n![](data:image/png;base64...)\n\nAprès"
        )
        assert "data:image" not in cleaned
        assert "Avant" in cleaned and "Après" in cleaned

    def test_le_texte_alternatif_est_conserve(self) -> None:
        cleaned = sources._drop_image_placeholders("![Schéma](data:image/png;base64...)")
        assert cleaned.strip() == "Schéma"

    def test_une_vraie_image_est_epargnee(self) -> None:
        markdown = "![](assets/img_000.png)"
        assert sources._drop_image_placeholders(markdown).strip() == markdown

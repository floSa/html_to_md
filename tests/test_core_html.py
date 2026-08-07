"""Pipeline complet des pages web — non-régression du cœur historique."""

from __future__ import annotations

from pathlib import Path

from fast_to_md.core import process_file

from conftest import FIXTURES


class TestCaptureDePageWeb:
    def test_le_contenu_est_isole_du_chrome(self, tmp_path: Path, profiles) -> None:
        result = process_file(FIXTURES / "sample_singlefile.html", tmp_path, profiles)
        markdown = result.output.read_text(encoding="utf-8")

        assert result.status == "ok"
        assert "Comprendre les pipelines d'ingestion" in markdown
        # Navigation, bandeau cookies, pop-up et pied de page doivent avoir sauté.
        assert "Se connecter" not in markdown
        assert "Nous utilisons des cookies" not in markdown
        assert "Abonnez-vous" not in markdown
        assert "Mentions légales" not in markdown

    def test_le_nom_de_sortie_reprend_le_titre_de_larticle(
        self, tmp_path: Path, profiles
    ) -> None:
        """La capture ne porte ni suffixe de site dans son <title> ni URL
        d'origine : le nom se réduit au titre de l'article."""
        result = process_file(FIXTURES / "sample_singlefile.html", tmp_path, profiles)

        assert result.output.name == "Comprendre_les_pipelines_d_ingestion.md"

    def test_le_nom_prefixe_le_site_quand_il_est_connu(
        self, tmp_path: Path, no_profiles
    ) -> None:
        page = tmp_path / "capture.html"
        page.write_text(
            "<html><head><title>Mon Article - MonSite.com</title></head><body>"
            "<article><h1>Mon Article</h1><p>" + "Contenu de test. " * 30 +
            "</p></article></body></html>",
            encoding="utf-8",
        )

        result = process_file(page, tmp_path / "out", no_profiles)

        assert result.output.name == "mon_site_Mon_Article.md"

    def test_le_schema_est_exporte_et_licone_ecartee(self, tmp_path: Path, profiles) -> None:
        """La page porte deux images : un schéma de contenu et une icône de
        partage. Seule la première doit atterrir sur le disque."""
        result = process_file(FIXTURES / "sample_singlefile.html", tmp_path, profiles)
        markdown = result.output.read_text(encoding="utf-8")

        assert result.images == 1
        assert (tmp_path / f"{result.output.stem}_assets" / "img_000.png").exists()
        assert f"{result.output.stem}_assets/img_000.png" in markdown
        assert "icône partage" not in markdown

    def test_le_langage_du_bloc_de_code_survit(self, tmp_path: Path, profiles) -> None:
        result = process_file(FIXTURES / "sample_singlefile.html", tmp_path, profiles)

        assert "```python" in result.output.read_text(encoding="utf-8")

    def test_les_formules_sont_restituees(self, tmp_path: Path, profiles) -> None:
        result = process_file(FIXTURES / "sample_math.html", tmp_path, profiles)
        markdown = result.output.read_text(encoding="utf-8")

        assert "$" in markdown

    def test_sans_profil_le_mode_generique_prend_le_relais(
        self, tmp_path: Path, no_profiles
    ) -> None:
        result = process_file(FIXTURES / "sample_singlefile.html", tmp_path, no_profiles)

        assert result.status == "ok"
        assert "Comprendre les pipelines" in result.output.read_text(encoding="utf-8")


class TestSignalementPourRevue:
    def test_une_page_presque_vide_est_signalee(self, tmp_path: Path, no_profiles) -> None:
        page = tmp_path / "vide.html"
        page.write_text("<html><body><p>Court.</p></body></html>", encoding="utf-8")

        result = process_file(page, tmp_path / "out", no_profiles)

        assert result.status == "review"
        assert "courte" in result.detail


class TestCollisionsDeNoms:
    def test_deux_pages_de_meme_titre_ne_secrasent_pas(
        self, tmp_path: Path, profiles
    ) -> None:
        out = tmp_path / "out"
        taken: set[Path] = set()

        first = process_file(FIXTURES / "sample_singlefile.html", out, profiles, taken=taken)
        second = process_file(FIXTURES / "sample_singlefile.html", out, profiles, taken=taken)

        assert first.output != second.output
        assert second.output.name.endswith("_2.md")
        assert first.output.exists() and second.output.exists()

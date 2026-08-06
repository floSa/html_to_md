"""Interface en ligne de commande."""

from __future__ import annotations

import shutil
from pathlib import Path

from html_to_md.cli import main

from conftest import FIXTURES


class TestLotMultiFormat:
    def test_tous_les_formats_dun_dossier_sont_traites(
        self, tmp_path: Path, docx_factory, pptx_factory, capsys
    ) -> None:
        source = tmp_path / "in"
        source.mkdir()
        shutil.copy(FIXTURES / "sample_singlefile.html", source / "page.html")
        shutil.copy(docx_factory(), source / "rapport.docx")
        shutil.copy(pptx_factory(), source / "deck.pptx")
        (source / "photo.jpg").write_bytes(b"ignore-moi")

        code = main([str(source), "-o", str(tmp_path / "out")])

        assert code == 0
        produced = sorted(p.name for p in (tmp_path / "out").glob("*.md"))
        assert len(produced) == 3
        assert "3 fichier(s) traité(s)" in capsys.readouterr().out

    def test_larborescence_dentree_est_reproduite(
        self, tmp_path: Path, docx_factory
    ) -> None:
        source = tmp_path / "in"
        (source / "clients" / "2026").mkdir(parents=True)
        shutil.copy(docx_factory(), source / "clients" / "2026" / "rapport.docx")

        main([str(source), "-o", str(tmp_path / "out")])

        assert (tmp_path / "out" / "clients" / "2026" / "rapport.md").exists()

    def test_un_fichier_seul_est_accepte(self, tmp_path: Path, docx_factory) -> None:
        code = main([str(docx_factory()), "-o", str(tmp_path / "out")])

        assert code == 0
        assert list((tmp_path / "out").glob("*.md"))


class TestCasLimites:
    def test_dossier_sans_document_convertible(self, tmp_path: Path, capsys) -> None:
        source = tmp_path / "in"
        source.mkdir()
        (source / "photo.jpg").write_bytes(b"factice")

        code = main([str(source), "-o", str(tmp_path / "out")])

        assert code == 1
        assert "Aucun fichier convertible" in capsys.readouterr().err

    def test_un_document_casse_narrete_pas_le_lot(
        self, tmp_path: Path, docx_factory, capsys
    ) -> None:
        source = tmp_path / "in"
        source.mkdir()
        shutil.copy(docx_factory(), source / "bon.docx")
        (source / "casse.docx").write_bytes(b"ceci n'est pas un document")

        code = main([str(source), "-o", str(tmp_path / "out")])

        assert code == 1  # signale l'échec…
        assert (tmp_path / "out" / "bon.md").exists()  # …sans perdre le reste
        assert "1 en erreur" in capsys.readouterr().out

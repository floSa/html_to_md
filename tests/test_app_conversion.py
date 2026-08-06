"""Adaptateurs de l'application web (conversion en mémoire)."""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

import conversion  # noqa: E402


class TestConversionEnMemoire:
    def test_un_word_ressort_avec_ses_images(self, docx_factory) -> None:
        path = docx_factory()

        items = conversion.convert_uploads([(path.name, path.read_bytes())])

        assert len(items) == 1
        assert items[0].result.images == 2
        assert len(items[0].assets) == 2
        assert items[0].md_bytes

    def test_les_formats_hors_perimetre_sont_ignores(self) -> None:
        assert conversion.convert_uploads([("photo.jpg", b"factice")]) == []

    def test_un_document_casse_ressort_en_erreur_sans_tuer_le_lot(
        self, docx_factory
    ) -> None:
        bon = docx_factory()

        items = conversion.convert_uploads(
            [("casse.docx", b"pas un document"), (bon.name, bon.read_bytes())]
        )

        statuses = {i.result.status for i in items}
        assert "error" in statuses and "ok" in statuses
        assert len(items) == 2

    def test_le_dossier_est_parcouru_recursivement(
        self, tmp_path: Path, docx_factory
    ) -> None:
        folder = tmp_path / "docs"
        (folder / "sous").mkdir(parents=True)
        (folder / "sous" / "rapport.docx").write_bytes(docx_factory().read_bytes())
        (folder / "photo.jpg").write_bytes(b"factice")

        items = conversion.convert_folder(folder)

        assert len(items) == 1


class TestArchive:
    def test_le_zip_contient_markdown_et_images(self, docx_factory) -> None:
        path = docx_factory()
        items = conversion.convert_uploads([(path.name, path.read_bytes())])

        archive = zipfile.ZipFile(io.BytesIO(conversion.build_zip(items)))
        names = archive.namelist()

        assert any(n.endswith(".md") for n in names)
        assert sum(1 for n in names if n.endswith(".png")) == 2

    def test_les_echecs_ne_sont_pas_archives(self, docx_factory) -> None:
        bon = docx_factory()
        items = conversion.convert_uploads(
            [("casse.docx", b"pas un document"), (bon.name, bon.read_bytes())]
        )

        archive = zipfile.ZipFile(io.BytesIO(conversion.build_zip(items)))

        assert not any(n.startswith("casse") for n in archive.namelist())


class TestSelecteurDeFichiers:
    def test_les_extensions_sont_sans_point(self) -> None:
        types = conversion.supported_upload_types()

        assert "docx" in types and "html" in types
        assert not any(t.startswith(".") for t in types)

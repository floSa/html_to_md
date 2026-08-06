"""Chaque format annoncé doit réellement se convertir.

Ces tests gardent la liste des formats honnête : promettre une extension
que l'outil ne sait pas lire est pire que ne pas la proposer du tout.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from html_to_md.sources import TEXT_EXTENSIONS, ingest


def _csv(path: Path) -> Path:
    target = path / "tableau.csv"
    target.write_text("produit,prix\nalpha,12\n", encoding="utf-8")
    return target


def _ipynb(path: Path) -> Path:
    target = path / "carnet.ipynb"
    target.write_text(
        '{"cells":[{"cell_type":"markdown","source":["# Titre du carnet"],'
        '"metadata":{}}],"metadata":{},"nbformat":4,"nbformat_minor":5}',
        encoding="utf-8",
    )
    return target


def _xlsx(path: Path) -> Path:
    from openpyxl import Workbook

    target = path / "classeur.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Produit", "Prix"])
    sheet.append(["Alpha", 12])
    workbook.save(str(target))
    return target


def _epub(path: Path) -> Path:
    target = path / "livre.epub"
    with zipfile.ZipFile(target, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?><container version="1.0" '
            'xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles>'
            '<rootfile full-path="c.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles></container>',
        )
        archive.writestr(
            "c.opf",
            '<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" '
            'version="3.0" unique-identifier="i"><metadata '
            'xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>Mon Livre</dc:title>'
            '<dc:identifier id="i">x</dc:identifier><dc:language>fr</dc:language>'
            '</metadata><manifest><item id="c1" href="c1.xhtml" '
            'media-type="application/xhtml+xml"/></manifest><spine>'
            '<itemref idref="c1"/></spine></package>',
        )
        archive.writestr(
            "c1.xhtml",
            '<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Chapitre un</h1>'
            "<p>Texte du livre.</p></body></html>",
        )
    return target


def _pdf(path: Path) -> Path:
    """PDF minimal d'une page, écrit à la main pour éviter une dépendance."""
    stream = b"BT /F1 12 Tf 20 150 Td (Contenu du PDF) Tj ET\n"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 200 200] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        # La longueur doit coller au flux, sinon le texte n'est pas lu du tout.
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode() + b"0000000000 65535 f \n"
    for offset in offsets:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode()

    target = path / "document.pdf"
    target.write_bytes(bytes(out))
    return target


BUILDERS = {
    ".csv": (_csv, "alpha"),
    ".ipynb": (_ipynb, "Titre du carnet"),
    ".xlsx": (_xlsx, "Produit"),
    ".epub": (_epub, "Chapitre un"),
    ".pdf": (_pdf, "Contenu du PDF"),
}


@pytest.mark.parametrize("extension", sorted(BUILDERS))
def test_le_format_annonce_se_convertit(extension: str, tmp_path: Path) -> None:
    build, expected = BUILDERS[extension]

    ingested = ingest(build(tmp_path))

    assert ingested.kind == "markdown"
    assert expected in ingested.markdown
    assert ingested.engine == f"doc:{extension.lstrip('.')}"


def test_aucun_format_annonce_nest_laisse_sans_test() -> None:
    """Garde-fou : ajouter une extension à la liste sans la tester doit
    faire échouer la suite plutôt que passer inaperçu."""
    covered = set(BUILDERS) | {
        ".pptx",  # couvert de bout en bout dans test_core_documents.py
        ".xls",  # pas de fixture crédible : dépendance vérifiée à la place
        ".msg",
    }
    untested = TEXT_EXTENSIONS - covered

    assert untested == set(), f"formats annoncés mais non testés : {sorted(untested)}"


@pytest.mark.parametrize("module", ["xlrd", "olefile"])
def test_les_dependances_des_formats_restants_sont_installees(module: str) -> None:
    pytest.importorskip(module)

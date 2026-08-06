"""L'interface web doit se rendre sans erreur et proposer tous les formats.

Streamlit est une dépendance optionnelle : ces tests sont sautés si l'extra
« app » n'est pas installé.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("streamlit")

from streamlit.testing.v1 import AppTest  # noqa: E402

from html_to_md.sources import SUPPORTED_EXTENSIONS  # noqa: E402

APP_DIR = Path(__file__).resolve().parents[1] / "app"
APP_FILE = APP_DIR / "streamlit_app.py"


@pytest.fixture
def app() -> AppTest:
    # `streamlit run app/streamlit_app.py` place app/ sur le sys.path ;
    # le harnais de test ne le fait pas.
    sys.path.insert(0, str(APP_DIR))
    instance = AppTest.from_file(str(APP_FILE), default_timeout=120)
    instance.run()
    return instance


class TestRendu:
    def test_la_page_se_charge_sans_exception(self, app: AppTest) -> None:
        assert not app.exception
        assert app.title[0].value == "html_to_md"

    def test_les_trois_usages_sont_presents(self, app: AppTest) -> None:
        titles = [s.value for s in app.subheader]

        assert "Déposer des documents" in titles
        assert "Convertir un dossier du serveur" in titles
        assert "Dossier surveillé" in titles


class TestSelecteurDeFichiers:
    def test_tous_les_formats_pris_en_charge_sont_proposes(self, app: AppTest) -> None:
        """Un format converti par le cœur mais absent du sélecteur serait
        impossible à déposer dans l'interface."""
        # Streamlit renormalise les extensions avec leur point.
        offered = {ext.lstrip(".") for ext in app.get("file_uploader")[0].proto.type}

        assert offered == {ext.lstrip(".") for ext in SUPPORTED_EXTENSIONS}

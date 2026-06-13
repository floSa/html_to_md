"""Interface web (Streamlit) de html_to_md.

Trois usages :
  1. déposer / glisser des fichiers HTML et télécharger le Markdown ;
  2. convertir un dossier présent sur le serveur (téléchargement ZIP) ;
  3. piloter le dossier surveillé HTML2MD/HTMLs -> HTML2MD/MDs.

Lancé via ``streamlit run app/streamlit_app.py`` : le dossier ``app/`` est sur
le ``sys.path``, d'où les imports nus ``conversion`` / ``watcher``.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from conversion import (  # type: ignore[import-not-found]
    ConvertedFile,
    build_zip,
    convert_folder,
    convert_uploads,
)
import watcher  # type: ignore[import-not-found]

st.set_page_config(page_title="html_to_md", page_icon="📄", layout="centered")

_STATUS_ICON = {"ok": "✅", "review": "⚠️", "error": "❌"}


def _results_table(items: list[ConvertedFile]) -> None:
    """Affiche un récapitulatif des conversions."""
    rows = []
    for item in items:
        r = item.result
        rows.append(
            {
                "": _STATUS_ICON.get(r.status, "•"),
                "Fichier": item.md_name,
                "Stratégie": r.strategy,
                "Caractères": r.chars_out,
                "Images": r.images,
                "Note": r.detail,
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)
    review = [i for i in items if i.result.status == "review"]
    if review:
        st.warning(
            f"{len(review)} fichier(s) à vérifier : le nettoyage a peut-être "
            "retiré trop de contenu."
        )


def _offer_download(items: list[ConvertedFile]) -> None:
    """Bouton de téléchargement : un .md si unique, sinon un .zip."""
    if not items:
        return
    if len(items) == 1 and not items[0].assets:
        st.download_button(
            "⬇️ Télécharger le Markdown",
            data=items[0].md_bytes,
            file_name=items[0].md_name,
            mime="text/markdown",
        )
    else:
        st.download_button(
            "⬇️ Télécharger le ZIP (Markdown + images)",
            data=build_zip(items),
            file_name="html_to_md.zip",
            mime="application/zip",
        )


def tab_upload() -> None:
    st.subheader("Déposer des fichiers HTML")
    st.caption("Glissez-déposez une ou plusieurs captures SingleFile (.html).")
    uploads = st.file_uploader(
        "Fichiers HTML",
        type=["html", "htm"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )
    if not uploads:
        return
    if st.button("Convertir", type="primary"):
        bar = st.progress(0.0, text="Conversion…")

        def on_progress(done: int, total: int, name: str) -> None:
            bar.progress(done / total, text=f"{done}/{total} — {name}")

        items = convert_uploads(((u.name, u.getvalue()) for u in uploads), on_progress)
        bar.empty()
        if not items:
            st.error("Aucun fichier HTML valide dans la sélection.")
            return
        st.success(f"{len(items)} fichier(s) converti(s).")
        _results_table(items)
        _offer_download(items)


def tab_folder() -> None:
    st.subheader("Convertir un dossier du serveur")
    st.caption("Chemin d'un dossier accessible par l'application (récursif).")
    folder_str = st.text_input("Chemin du dossier", placeholder="/data/mes_captures")
    if not folder_str:
        return
    folder = Path(folder_str)
    if not folder.is_dir():
        st.error("Dossier introuvable.")
        return
    count = sum(1 for _ in folder.rglob("*.html"))
    st.info(f"{count} fichier(s) .html détecté(s).")
    if count and st.button("Convertir le dossier", type="primary"):
        bar = st.progress(0.0, text="Conversion…")

        def on_progress(done: int, total: int, name: str) -> None:
            bar.progress(done / total, text=f"{done}/{total} — {name}")

        items = convert_folder(folder, on_progress)
        bar.empty()
        st.success(f"{len(items)} fichier(s) converti(s).")
        _results_table(items)
        _offer_download(items)


def tab_watched() -> None:
    st.subheader("Dossier surveillé")
    st.caption(
        f"Les `.html` déposés dans `{watcher.HTMLS_DIR}` sont convertis vers "
        f"`{watcher.MDS_DIR}` automatiquement (toutes les "
        f"{watcher.INTERVAL_SECONDS // 60} min)."
    )
    html_count = sum(1 for _ in watcher.HTMLS_DIR.rglob("*.html")) if watcher.HTMLS_DIR.exists() else 0
    md_count = sum(1 for _ in watcher.MDS_DIR.glob("*.md")) if watcher.MDS_DIR.exists() else 0
    pending = watcher.pending_files() if watcher.HTMLS_DIR.exists() else []

    col1, col2, col3 = st.columns(3)
    col1.metric("HTML déposés", html_count)
    col2.metric("Markdown produits", md_count)
    col3.metric("En attente", len(pending))

    if pending:
        with st.expander(f"{len(pending)} fichier(s) en attente"):
            st.write([str(p.relative_to(watcher.HTMLS_DIR)) for p in pending])

    if st.button("Convertir maintenant", type="primary", disabled=not pending):
        with st.spinner("Conversion…"):
            results = watcher.scan_once()
        st.success(f"{len(results)} fichier(s) converti(s).")


st.title("📄 html_to_md")
st.caption("Captures SingleFile → Markdown propre pour l'ingestion RAG.")

upload, folder, watched = st.tabs(
    ["Déposer des fichiers", "Dossier serveur", "Dossier surveillé"]
)
with upload:
    tab_upload()
with folder:
    tab_folder()
with watched:
    tab_watched()

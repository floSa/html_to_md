"""Interface web (Streamlit) de fast_to_md.

Trois usages :
  1. déposer / glisser des documents et télécharger le Markdown ;
  2. convertir un dossier présent sur le serveur (téléchargement ZIP) ;
  3. piloter le dossier surveillé FAST2MD/Inbox -> FAST2MD/Markdown.

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
    supported_upload_types,
)
import watcher  # type: ignore[import-not-found]

from fast_to_md.sources import iter_sources

st.set_page_config(page_title="fast_to_md", layout="centered")

_STATUS_ICON = {"ok": "✅", "review": "!", "error": "❌"}


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
    errors = [i for i in items if i.result.status == "error"]
    if errors:
        st.error(f"{len(errors)} fichier(s) en erreur (illisibles ou protégés).")


def _report(items: list[ConvertedFile]) -> None:
    """Récapitulatif complet : compte, tableau des résultats, téléchargement."""
    done = [i for i in items if i.result.status != "error"]
    st.success(f"{len(done)} document(s) converti(s) sur {len(items)}.")
    _results_table(items)
    _offer_download(done)


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
            file_name="fast_to_md.zip",
            mime="application/zip",
        )


def tab_upload() -> None:
    st.subheader("Déposer des documents")
    st.caption(
        "Glissez-déposez un ou plusieurs fichiers : pages web enregistrées, "
        "Word, PowerPoint, Excel, PDF, EPUB, e-mails."
    )
    uploads = st.file_uploader(
        "Documents",
        type=supported_upload_types(),
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
            st.error("Aucun format pris en charge dans la sélection.")
            return
        _report(items)


def tab_folder() -> None:
    st.subheader("Convertir un dossier du serveur")
    st.caption("Chemin d'un dossier accessible par l'application (récursif).")
    folder_str = st.text_input("Chemin du dossier", placeholder="/data/mes_documents")
    if not folder_str:
        return
    folder = Path(folder_str)
    if not folder.is_dir():
        st.error("Dossier introuvable.")
        return
    count = len(iter_sources(folder))
    st.info(f"{count} document(s) convertible(s) détecté(s).")
    if count and st.button("Convertir le dossier", type="primary"):
        bar = st.progress(0.0, text="Conversion…")

        def on_progress(done: int, total: int, name: str) -> None:
            bar.progress(done / total, text=f"{done}/{total} — {name}")

        items = convert_folder(folder, on_progress)
        bar.empty()
        _report(items)


def tab_watched() -> None:
    st.subheader("Dossier surveillé")
    st.caption(
        f"Les documents déposés dans `{watcher.INBOX_DIR}` sont convertis vers "
        f"`{watcher.MARKDOWN_DIR}` automatiquement (toutes les "
        f"{watcher.INTERVAL_SECONDS // 60} min)."
    )
    src_count = len(iter_sources(watcher.INBOX_DIR)) if watcher.INBOX_DIR.exists() else 0
    md_count = sum(1 for _ in watcher.MARKDOWN_DIR.glob("*.md")) if watcher.MARKDOWN_DIR.exists() else 0
    pending = watcher.pending_files() if watcher.INBOX_DIR.exists() else []

    col1, col2, col3 = st.columns(3)
    col1.metric("Documents déposés", src_count)
    col2.metric("Markdown produits", md_count)
    col3.metric("En attente", len(pending))

    if pending:
        with st.expander(f"{len(pending)} fichier(s) en attente"):
            st.write([str(p.relative_to(watcher.INBOX_DIR)) for p in pending])

    if st.button("Convertir maintenant", type="primary", disabled=not pending):
        with st.spinner("Conversion…"):
            results = watcher.scan_once()
        st.success(f"{len(results)} fichier(s) converti(s).")


st.title("fast_to_md")
st.caption("Documents → Markdown propre, prêt à relire et à indexer.")

upload, folder, watched = st.tabs(
    ["Déposer des documents", "Dossier serveur", "Dossier surveillé"]
)
with upload:
    tab_upload()
with folder:
    tab_folder()
with watched:
    tab_watched()

"""Surveillance du dossier ``HTML2MD/HTMLs`` : conversion des nouveaux fichiers.

Au démarrage puis à intervalle régulier (1 h par défaut), on convertit chaque
``.html`` qui n'a pas encore été traité (ou qui a changé depuis) vers
``HTML2MD/MDs``. Un petit registre JSON (``.processed.json``) retient ce qui a
déjà été fait, par signature mtime+taille, pour ne pas retravailler à vide.

Lancé comme service à part (voir docker-compose), indépendamment de l'UI.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from conversion import get_profiles  # type: ignore[import-not-found]

from html_to_md.core import Result, process_file

DATA_ROOT = Path(os.environ.get("HTML2MD_ROOT", "HTML2MD"))
HTMLS_DIR = DATA_ROOT / "HTMLs"
MDS_DIR = DATA_ROOT / "MDs"
LEDGER_PATH = DATA_ROOT / ".processed.json"
INTERVAL_SECONDS = int(os.environ.get("WATCH_INTERVAL_SECONDS", str(60 * 60)))


def _signature(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_mtime_ns}:{stat.st_size}"


def _load_ledger() -> dict[str, str]:
    if LEDGER_PATH.exists():
        try:
            return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_ledger(ledger: dict[str, str]) -> None:
    LEDGER_PATH.write_text(json.dumps(ledger, indent=2), encoding="utf-8")


def pending_files() -> list[Path]:
    """Fichiers HTML jamais convertis ou modifiés depuis leur dernière conversion."""
    ledger = _load_ledger()
    pending = []
    for html in sorted(HTMLS_DIR.rglob("*.html")):
        key = str(html.relative_to(HTMLS_DIR))
        if ledger.get(key) != _signature(html):
            pending.append(html)
    return pending


def scan_once() -> list[Result]:
    """Convertit tous les fichiers en attente. Renvoie les résultats produits."""
    HTMLS_DIR.mkdir(parents=True, exist_ok=True)
    MDS_DIR.mkdir(parents=True, exist_ok=True)

    profiles = get_profiles()
    ledger = _load_ledger()
    # Réserve les noms déjà présents pour ne pas écraser une conversion passée.
    taken: set[Path] = set(MDS_DIR.glob("*.md"))
    results: list[Result] = []

    for html in pending_files():
        key = str(html.relative_to(HTMLS_DIR))
        try:
            result = process_file(html, MDS_DIR, profiles, taken=taken)
            ledger[key] = _signature(html)
            results.append(result)
        except Exception as exc:  # un fichier corrompu ne doit pas tuer le service
            print(f"[watcher] erreur sur {key}: {exc}", flush=True)

    if results:
        _save_ledger(ledger)
    return results


def main() -> None:
    print(
        f"[watcher] surveillance de {HTMLS_DIR} -> {MDS_DIR} "
        f"toutes les {INTERVAL_SECONDS} s",
        flush=True,
    )
    while True:
        results = scan_once()
        if results:
            ok = sum(1 for r in results if r.status == "ok")
            review = sum(1 for r in results if r.status == "review")
            print(
                f"[watcher] {len(results)} fichier(s) converti(s) "
                f"({ok} ok, {review} à vérifier).",
                flush=True,
            )
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    main()

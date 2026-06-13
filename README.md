# html_to_md — version app (interface web)

> Branche **`app`**. Pour la version ligne de commande, voir la branche [`cli`](../../tree/cli). Présentation générale sur [`main`](../../tree/main).

Application web qui nettoie les captures **SingleFile** (Chrome/Firefox) et les convertit en **Markdown propre** pour l'ingestion RAG — même cœur de conversion que la branche `cli`, enveloppé dans une interface **Streamlit** et un service **Docker Compose**.

## Ce que fait l'app

- **Déposer des fichiers** : glisser-déposer une ou plusieurs captures `.html` (le format est vérifié), conversion, puis téléchargement du `.md` (ou d'un `.zip` Markdown + images si plusieurs fichiers).
- **Dossier serveur** : convertir tout un dossier accessible par l'app, avec **barre d'avancement**, téléchargement en `.zip`.
- **Dossier surveillé** : tout `.html` déposé dans `HTML2MD/HTMLs` est converti automatiquement vers `HTML2MD/MDs`. Le service `watcher` scrute le dossier **au démarrage puis toutes les heures** et ne retraite que les fichiers nouveaux ou modifiés (registre `HTML2MD/.processed.json`). L'onglet permet aussi de lancer une conversion immédiate.

## Démarrage avec Docker (recommandé)

```bash
git switch app
docker compose up --build
```

Puis ouvrir **http://localhost:8501**.

Deux services sont lancés :

| Service | Rôle |
|---|---|
| `webapp` | l'interface Streamlit (port 8501) |
| `watcher` | la conversion automatique du dossier surveillé |

Les deux partagent le volume `./HTML2MD` (sous-dossiers `HTMLs/` et `MDs/`). Déposez vos `.html` dans `HTML2MD/HTMLs`, récupérez les `.md` dans `HTML2MD/MDs`.

Variables d'environnement utiles :

| Variable | Défaut | Rôle |
|---|---|---|
| `HTML2MD_ROOT` | `/app/HTML2MD` | racine des dossiers `HTMLs`/`MDs` |
| `WATCH_INTERVAL_SECONDS` | `3600` | période de scan du watcher (en secondes) |

## Démarrage sans Docker

```bash
git switch app
python3 -m venv .venv
.venv/bin/pip install -e ".[app]"

# interface web
.venv/bin/streamlit run app/streamlit_app.py

# (optionnel, dans un autre terminal) service de surveillance
PYTHONPATH=app .venv/bin/python app/watcher.py
```

## Structure

```text
app/
├── streamlit_app.py   # interface web (3 onglets)
├── conversion.py      # adaptateurs cœur disque → mémoire (upload, zip)
└── watcher.py         # surveillance horaire du dossier HTMLs → MDs
src/html_to_md/        # cœur de conversion (identique à la branche cli)
config/selectors.yaml  # profils d'extraction par site (optionnel, vide par défaut)
HTML2MD/
├── HTMLs/             # déposer ici les captures .html
└── MDs/               # le Markdown converti apparaît ici
Dockerfile
docker-compose.yml
```

Le détail du pipeline de conversion (hygiène, extraction, images, formules LaTeX, garde-fou) est documenté dans la branche [`cli`](../../blob/cli/README.md).

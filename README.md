# html_to_md — version app (interface web)

> Branche **`app`**. Pour la version ligne de commande, voir la branche [`cli`](../../tree/cli). Présentation générale sur [`main`](../../tree/main).

Application web qui nettoie les captures **SingleFile** (Chrome/Firefox) et les convertit en **Markdown propre** pour l'ingestion RAG — même cœur de conversion que la branche `cli`, enveloppé dans une interface **Streamlit** et un service **Docker Compose**.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-package_manager-DE5FE9?logo=uv&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.58+-FF4B4B?logo=streamlit&logoColor=white)

## Ce que fait l'app

- **Déposer des fichiers** : glisser-déposer une ou plusieurs captures `.html` (le format est vérifié), conversion, puis téléchargement du `.md` (ou d'un `.zip` Markdown + images si plusieurs fichiers).
- **Dossier serveur** : convertir tout un dossier accessible par l'app, avec **barre d'avancement**, téléchargement en `.zip`.
- **Dossier surveillé** : tout `.html` déposé dans `HTML2MD/HTMLs` est converti automatiquement vers `HTML2MD/MDs`. Le service `watcher` scrute le dossier **au démarrage puis toutes les heures** et ne retraite que les fichiers nouveaux ou modifiés (registre `HTML2MD/.processed.json`). L'onglet permet aussi de lancer une conversion immédiate.

## Démarrage avec Docker (recommandé)

```bash
git switch app
docker compose up --build
```

Puis ouvrir **http://localhost:8505**.

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

## Interface en ligne de commande

Le cœur est aussi exposé par la commande `html2md` (installée via `pip install -e .`, point d'entrée [`html_to_md.cli:main`](src/html_to_md/cli.py)) :

```bash
html2md INPUT [-o OUTPUT] [--config CONFIG] [--min-image-bytes N]
```

| Argument | Défaut | Rôle |
|---|---|---|
| `input` | — (requis) | Fichier `.html` ou dossier traité **récursivement** |
| `-o`, `--output` | `./out` | Dossier de sortie (l'arborescence d'entrée est reproduite) |
| `--config` | `config/selectors.yaml` | YAML des profils d'extraction par site |
| `--min-image-bytes` | `4096` | Taille minimale (octets) pour exporter une image data-URI ; en dessous elle est jugée icône d'UI et supprimée |

Chaque fichier est marqué `ok`, `à vérifier` (contenu peut-être sur-nettoyé) ou `erreur` ; la commande renvoie le **code de sortie 1** s'il y a au moins une erreur, `0` sinon. Un fichier corrompu n'interrompt pas le lot.

## Documentation

| Document | Contenu |
|---|---|
| [docs/CADRAGE.md](docs/CADRAGE.md) | Le **pourquoi** : pitch, périmètre, hypothèses, décisions produit |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Le **comment** : modules, pipeline de conversion, stratégie d'extraction, formules, décisions techniques |

## Licences & composants

| Composant | Rôle | Licence usuelle |
|---|---|---|
| beautifulsoup4 | Parsing HTML | MIT |
| lxml | Parseur / nettoyage HTML | BSD-3-Clause |
| readability-lxml | Extraction générique du contenu | Apache-2.0 |
| markdownify | Conversion HTML → Markdown | MIT |
| PyYAML | Lecture des profils d'extraction | MIT |
| Streamlit | Interface web (extra `app`) | Apache-2.0 |
| Python | Langage / runtime (`python:3.12-slim`) | PSF |
| **Ce projet** | Code applicatif | MIT — Copyright (c) 2026 floSa — `<à confirmer>` : aucun fichier `LICENSE` ni champ `license` dans `pyproject.toml` |

> **Attention** : licences des dépendances indiquées d'après l'usage courant de ces briques ; elles **changent parfois selon les versions**. À vérifier avant tout usage engageant.

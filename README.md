# fast_to_md

**Convertit n'importe quel document — page web enregistrée, Word, PowerPoint, Excel, PDF, EPUB, e-mail — en Markdown propre, prêt à relire dans un éditeur de notes et à indexer.**

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![uv](https://img.shields.io/badge/uv-package_manager-DE5FE9?logo=uv&logoColor=white)

> Cette branche `main` ne contient que cette présentation — aucun code. Le projet vit sur deux branches indépendantes, qui partagent le même cœur de conversion.

## Formats pris en charge

| Famille | Extensions | Images | Tableaux |
|---|---|---|---|
| Pages web | `.html`, `.htm` | exportées en fichiers liés | oui |
| Documents riches | `.docx` | exportées en fichiers liés | oui |
| Documents texte | `.pptx`, `.xlsx`, `.xls`, `.pdf`, `.epub`, `.msg`, `.csv`, `.ipynb` | non récupérées | oui |

Le format d'entrée est déterminé par l'extension du fichier. Une page web passe par un nettoyage complet (extraction du contenu principal, suppression du chrome de navigation) ; un document bureautique par un chemin plus court, sans ce nettoyage dont il n'a pas besoin.

## Deux branches, un seul cœur

**Problème** : proposer à la fois un usage scripté (terminal, pipeline, cron) et un usage confortable (interface web, dépôt de fichiers, dossier surveillé), sans faire porter à l'un le poids de dépendances dont il n'a pas besoin. **Options envisagées** : un seul projet avec toutes les dépendances en options, ou deux branches distinctes partageant le même cœur. **Choix retenu** : deux branches, `cli` et `app`, qui reprennent chacune le même `src/fast_to_md/` **plutôt que** de le factoriser dans un paquet séparé publié, **parce que** le projet reste d'usage personnel et que dupliquer le cœur entre deux branches est plus simple à maintenir ici qu'un paquet séparé versionné indépendamment. **Limite** : le cœur doit être porté manuellement d'une branche à l'autre à chaque évolution.

| Besoin | Branche |
|---|---|
| Convertir des fichiers en ligne de commande, scripter, intégrer à un pipeline | [`cli`](../../tree/cli) |
| Interface web, glisser-déposer, dossier surveillé en continu | [`app`](../../tree/app) |

### Branche [`cli`](../../tree/cli) — ligne de commande

Le cœur de conversion exposé par une seule surface : la commande `fast2md`.

```bash
git switch cli
uv sync --extra docs
uv run fast2md "mes_documents/" -o out/
```

→ [README de la branche `cli`](../../blob/cli/README.md)

### Branche [`app`](../../tree/app) — application web

Le même cœur, enveloppé dans une interface web **Streamlit** et un service de surveillance de dossier, orchestrés par **Docker Compose**.

```bash
git switch app
docker compose up --build
# puis ouvrir http://localhost:8505
```

Trois usages : déposer des fichiers et télécharger le résultat, convertir un dossier serveur entier, ou laisser un dossier surveillé (`FAST2MD/Inbox` → `FAST2MD/Markdown`) se convertir tout seul.

→ [README de la branche `app`](../../blob/app/README.md)

## Documentation

Chaque branche porte sa propre documentation technique complète (architecture, pipeline de conversion, décisions, tests) :

| Branche | Cadrage (pourquoi) | Architecture (comment) |
|---|---|---|
| `cli` | [docs/CADRAGE.md](../../blob/cli/docs/CADRAGE.md) | [docs/ARCHITECTURE.md](../../blob/cli/docs/ARCHITECTURE.md) |
| `app` | [docs/CADRAGE.md](../../blob/app/docs/CADRAGE.md) | [docs/ARCHITECTURE.md](../../blob/app/docs/ARCHITECTURE.md) |

## Licences & composants

| Composant | Rôle | Licence usuelle |
|---|---|---|
| Python | Langage / runtime | PSF |
| uv | Gestion des dépendances | MIT |
| beautifulsoup4 | Parsing HTML | MIT |
| lxml | Parseur / nettoyage HTML | BSD-3-Clause |
| readability-lxml | Extraction générique du contenu (pages web) | Apache-2.0 |
| markdownify | Conversion HTML → Markdown | MIT |
| mammoth | Conversion Word (.docx) → HTML | MIT |
| MarkItDown | Conversion PowerPoint, Excel, PDF, EPUB, e-mails, CSV, carnets de notes → Markdown | MIT |
| **Ce projet** | Code applicatif | MIT — Copyright (c) 2026 floSa — `<à confirmer>` : aucun fichier `LICENSE` ni champ `license` dans les `pyproject.toml` des branches `cli`/`app` |

> Licences indiquées d'après l'usage courant de ces briques ; elles changent parfois selon les versions. Liste versionnée complète par branche dans son `pyproject.toml` et `uv.lock`.

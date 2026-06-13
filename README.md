# html_to_md

Nettoie les captures HTML faites avec l'extension **SingleFile** (Chrome/Firefox) et les convertit en **Markdown propre**, prêt pour l'ingestion dans un pipeline RAG.

Les pages sauvegardées avec SingleFile embarquent toute l'interface du site (barres de navigation, bannières, popups, boutons, CSS/JS inliné, icônes en base64...). Cet outil isole le contenu utile et jette le reste — **sans rien présumer du site d'origine**.

Au passage il gère : extraction du contenu principal (conteneurs sémantiques ou readability), export des images de contenu, conversion des **formules mathématiques** (KaTeX / MathJax / MathML) en LaTeX, et nommage des fichiers en `source_Titre_Article.md`.

---

## Ce dépôt a deux versions, sur deux branches

> La branche `main` ne contient que cette présentation. Choisissez la version qui correspond à votre usage.

### Branche [`cli`](../../tree/cli) — ligne de commande

La version **outil Python** : on installe le paquet et on convertit des fichiers ou des dossiers depuis le terminal.

```bash
git switch cli
python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/html2md "mes_captures/" -o out/
```

**Pour qui :** usage local, scriptable, intégration dans un pipeline (cron, Dagster...), traitement par lot ponctuel.

→ Voir le [README de la branche cli](../../blob/cli/README.md).

### Branche [`app`](../../tree/app) — application web

La version **service conteneurisé** : une interface web (Streamlit) lancée via Docker Compose, avec :

- **dépôt de fichiers** par sélection ou glisser-déposer (validation du format HTML),
- conversion immédiate et **téléchargement** du `.md` (ou d'un `.zip` pour un dossier),
- **barre d'avancement** pour les gros lots,
- un dossier surveillé `HTML2MD/HTMLs` → `HTML2MD/MDs` : les nouveaux fichiers sont convertis automatiquement (vérification toutes les heures).

```bash
git switch app
docker compose up
# puis ouvrir http://localhost:8501
```

**Pour qui :** usage confortable sans terminal, dépôt à la volée, service qui tourne en continu.

→ Voir le [README de la branche app](../../blob/app/README.md).

---

## Quelle version choisir ?

| Besoin | Branche |
|---|---|
| Convertir vite fait quelques fichiers en CLI | `cli` |
| Intégrer la conversion dans un script / pipeline | `cli` |
| Interface graphique, glisser-déposer, téléchargement | `app` |
| Service qui surveille un dossier et convertit tout seul | `app` |

Le cœur de conversion est le même dans les deux branches ; seule l'enveloppe (CLI vs web/Docker) change.

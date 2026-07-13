# Cadrage — html_to_md

> Le **POURQUOI**. Le COMMENT (composants, pipeline, décisions techniques) est dans
> [ARCHITECTURE.md](ARCHITECTURE.md).

## 1. Pitch

Nettoie les captures **SingleFile** (Chrome/Firefox) et les convertit en **Markdown
propre** pour l'ingestion RAG. Trois capacités :

1. **Convertir** un `.html` ou un dossier récursif en Markdown, avec extraction du
   contenu utile (hors chrome de navigation, pubs, widgets).
2. **Préserver** ce qui compte pour un corpus RAG : formules mathématiques (en LaTeX)
   et images de contenu (exportées à côté du Markdown).
3. **Signaler** les conversions douteuses (contenu peut-être sur-nettoyé) au lieu de les
   livrer silencieusement.

Trois modes d'accès au même cœur : **CLI** (`html2md`), **interface web** (Streamlit),
et **dossier surveillé** (watcher automatique).

---

## 2. Objectifs & périmètre

**Dans le périmètre :**
- Conversion de captures SingleFile en Markdown propre.
- Récupération des formules mathématiques rendues (KaTeX, MathJax v2/v3, MathML) en LaTeX.
- Export des images de contenu (data-URI) et suppression des icônes d'interface.
- Nommage lisible et déterministe des sorties (`<site>_<Titre_Article>.md`).
- Traitement par lot (dossier récursif) sans qu'un fichier corrompu n'arrête le lot.
- Trois surfaces d'usage : CLI, UI web, dossier surveillé.

**Hors périmètre (constaté dans le code) :**
- Le rendu ou l'affichage du Markdown produit (l'outil produit des fichiers, il ne les visualise pas).
- L'ingestion RAG elle-même (embeddings, base vectorielle) : hors de ce projet.
- La conversion de HTML arbitraire non issu de SingleFile n'est pas une cible affichée.

---

## 3. Contraintes (constatées dans le code)

| Contrainte | Détail |
|---|---|
| Langage | Python `>=3.10` ([pyproject.toml](../pyproject.toml)) ; image Docker `python:3.12-slim` |
| Dépendances | Cœur : BeautifulSoup, lxml, readability-lxml, markdownify, PyYAML. UI : Streamlit (extra `app`) |
| Déploiement | Local / on-prem via Docker Compose (UI sur le port hôte **8505**) |
| Licences des deps | Open-source (MIT / BSD / Apache-2.0 — voir [README](../README.md#licences--composants)) |

---

## 4. Hypothèses

Hypothèses **non lisibles dans le code** — à confirmer par l'auteur :

- **Entrée = SingleFile** : le nettoyage cible les marqueurs de SingleFile (classe
  `sf-hidden`, commentaire d'en-tête `url: ...`). Un HTML d'autre origine convertira
  moins bien. `<à confirmer>`
- **Corpus visé = articles / billets techniques** : les garde-fous (ratio, seuils,
  widgets WordPress « articles liés » supprimés) supposent des pages de type article.
  `<à confirmer>`
- **Public** : usage personnel / préparation de corpus RAG. `<à confirmer>`

---

## 5. Stack technique

| Brique | Choix | Licence usuelle |
|---|---|---|
| Parsing HTML | beautifulsoup4 `>=4.12` | MIT |
| Parseur / nettoyage | lxml `>=5.0` | BSD-3-Clause |
| Extraction générique | readability-lxml `>=0.8` | Apache-2.0 |
| HTML → Markdown | markdownify `>=0.13` | MIT |
| Profils de config | PyYAML `>=6.0` | MIT |
| Interface web | Streamlit `>=1.36` | Apache-2.0 |

> Licences : valeurs usuelles pour ces briques, **à vérifier** avant tout usage engageant
> (voir la note du tableau dans le [README](../README.md#licences--composants)).

---

## 6. Décisions produit

**Décisions figées** (lisibles dans le code)
- **Un seul cœur, trois surfaces** : CLI, UI web, watcher partagent `html_to_md.core`.
- **Signaler plutôt que masquer** : les conversions douteuses sont marquées `review`,
  pas supprimées ni « réparées » en silence.
- **Profils optionnels** : le mode générique fonctionne sans configuration
  (`config/selectors.yaml` vide par défaut).
- **Streamlit en dépendance optionnelle** : le cœur/CLI s'installe sans l'UI.

**À trancher**
- **Fichier `LICENSE` du dépôt** : absent, et aucun champ `license` dans
  `pyproject.toml`. La licence effective est `<à confirmer>` (voir README).
- **Ajout d'une suite de tests** : des fixtures existent mais aucun `test_*.py`.
- **Restriction de l'onglet « dossier serveur »** : convertit tout chemin lisible par
  l'app — à cadrer en cas d'exposition partagée.

---

## 7. Stratégie de tests

État constaté : `tests/fixtures/` contient `sample_math.html` et
`sample_singlefile.html`, mais **aucun fichier de test** n'est présent dans le dépôt.
La commande de test n'est donc `<à confirmer>`. Piste : `pytest` exerçant le pipeline
`process_file` sur ces fixtures (formules, extraction, nommage).

---

## 8. Références

- **SingleFile** — extension de capture de page (source des fichiers d'entrée).
- **readability-lxml** — heuristique d'extraction de contenu (repli générique).
- Détail du pipeline de conversion : [ARCHITECTURE.md](ARCHITECTURE.md).
- Documentation du cœur côté branche `cli` (voir renvoi dans le [README](../README.md)).

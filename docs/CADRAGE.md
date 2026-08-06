# Cadrage — html_to_md

> Le **POURQUOI**. Le COMMENT (composants, pipeline, décisions techniques) est dans
> [ARCHITECTURE.md](ARCHITECTURE.md).

## 1. Pitch

Convertit **n'importe quel document** — page web enregistrée, Word, PowerPoint,
Excel, PDF, EPUB, e-mail — en **Markdown propre**, relisible dans un éditeur de notes
et exploitable pour l'ingestion RAG. Trois capacités :

1. **Convertir** un fichier ou un dossier récursif, avec extraction du contenu utile
   des pages web (hors chrome de navigation, pubs, widgets).
2. **Préserver** ce qui compte : images de contenu exportées à côté du Markdown et
   liées relativement, tableaux avec de vrais en-têtes, formules mathématiques en
   LaTeX.
3. **Signaler** les conversions douteuses (contenu peut-être sur-nettoyé) au lieu de
   les livrer silencieusement.

Trois modes d'accès au même cœur : **CLI** (`html2md`), **interface web** (Streamlit),
et **dossier surveillé** (watcher automatique).

---

## 2. Objectifs & périmètre

**Dans le périmètre :**
- Conversion en Markdown propre de **onze formats**, des captures de pages web aux
  documents bureautiques (liste et niveaux de restitution : [ARCHITECTURE §3](ARCHITECTURE.md#3-formats-pris-en-charge)).
- Export des images de contenu à côté du Markdown, en liens relatifs, pour que la
  note s'ouvre telle quelle dans un éditeur.
- Récupération des formules mathématiques rendues (KaTeX, MathJax v2/v3, MathML) en
  LaTeX, sur les pages web.
- Nommage lisible et déterministe des sorties.
- Traitement par lot (dossier récursif) sans qu'un fichier corrompu n'arrête le lot.
- Trois surfaces d'usage : CLI, UI web, dossier surveillé.

**Hors périmètre :**
- Le rendu ou l'affichage du Markdown produit (l'outil produit des fichiers, il ne les
  visualise pas).
- L'ingestion RAG elle-même (embeddings, base vectorielle) : hors de ce projet.
- La reconnaissance de caractères sur documents scannés.
- La restitution fidèle des mises en page complexes (PDF multi-colonnes, tableaux
  denses) : la sortie y est textuelle. Voir les limites en
  [ARCHITECTURE §11](ARCHITECTURE.md#11-limites-connues--pistes).

---

## 3. Contraintes (constatées dans le code)

| Contrainte | Détail |
|---|---|
| Langage | Python `>=3.10` ([pyproject.toml](../pyproject.toml)) ; image Docker `python:3.12-slim` |
| Dépendances | Cœur : traitement HTML et Markdown. Extras : `app` (interface web), `docs` (formats bureautiques) |
| Déploiement | Local / on-prem via Docker Compose (UI sur le port hôte **8505**) |
| Poids de l'image | **717 Mo** avec la prise en charge des formats bureautiques |
| Licences des deps | Open-source — voir [README](../README.md#licences--composants) |

---

## 4. Hypothèses

Hypothèses **non lisibles dans le code** — à confirmer par l'auteur :

- **Sortie destinée à être relue et retravaillée** dans un éditeur de notes Markdown :
  c'est ce qui justifie l'export des images en fichiers liés relativement plutôt qu'en
  données embarquées. `<à confirmer>`
- **Pages web = captures SingleFile** : le nettoyage cible les marqueurs de SingleFile
  (classe `sf-hidden`, commentaire d'en-tête `url: ...`). Un HTML d'autre origine
  convertira moins bien. `<à confirmer>`
- **Corpus web visé = articles / billets techniques** : les garde-fous (ratio, seuils,
  widgets « articles liés » supprimés) supposent des pages de type article.
  `<à confirmer>`
- **Documents bureautiques natifs, non scannés** : aucune reconnaissance de caractères
  n'est prévue. `<à confirmer>`

---

## 5. Stack technique

| Brique | Choix | Licence usuelle |
|---|---|---|
| Langage / runtime | Python `>=3.10` (image `python:3.12-slim`) | PSF |
| Gestion des dépendances | uv (`uv.lock` versionné) | MIT |
| Interface web (extra `app`) | Streamlit `>=1.58` | Apache-2.0 |
| Conteneurisation | Docker Compose | Apache-2.0 |
| Tests | pytest `>=8.4` | MIT |

Le détail des briques de conversion se lit dans [`pyproject.toml`](../pyproject.toml)
et [`uv.lock`](../uv.lock) ; il n'est pas repris ici (voir la note du
[README](../README.md#licences--composants)).

> Licences : valeurs usuelles pour ces briques, **à vérifier** avant tout usage
> engageant.

---

## 6. Décisions produit

**Décisions figées** (lisibles dans le code)
- **Un seul cœur, trois surfaces** : CLI, UI web, watcher partagent `html_to_md.core`.
- **Deux niveaux de restitution assumés** : les formats qui savent rendre images et
  tableaux les rendent ; les autres sortent en texte, sans promesse d'images ni lien
  mort laissé dans la note.
- **Signaler plutôt que masquer** : les conversions douteuses sont marquées `review`,
  pas supprimées ni « réparées » en silence.
- **Le lot passe avant le fichier** : un document illisible ressort en erreur sans
  interrompre les autres.
- **Profils optionnels** : le mode générique fonctionne sans configuration
  (`config/selectors.yaml` vide par défaut).
- **Dépendances lourdes en extras** : le cœur et la CLI s'installent sans l'UI ni les
  formats bureautiques.

**À trancher**
- **Fichier `LICENSE` du dépôt** : absent, et aucun champ `license` dans
  `pyproject.toml`. La licence effective est `<à confirmer>` (voir README).
- **Nom du projet et du dossier surveillé** : `html_to_md` et `HTML2MD/HTMLs` sont
  devenus trompeurs maintenant que tous les formats sont acceptés.
- **Restriction de l'onglet « dossier serveur »** : convertit tout chemin lisible par
  l'app — à cadrer en cas d'exposition partagée.
- **Élargissement aux mises en page complexes** : une chaîne à analyse de mise en page
  restituerait mieux les PDF denses, au prix du poids et de la vitesse.

---

## 7. Stratégie de tests

**76 tests** couvrent les deux pipelines, la ligne de commande et l'interface — du
routage des formats aux collisions de noms, en passant par les documents illisibles.
Le détail par fichier est en [ARCHITECTURE §10](ARCHITECTURE.md#10-tests).

```bash
uv run pytest
```

Deux partis pris :
- les documents bureautiques des tests sont **fabriqués à la volée** plutôt que
  versionnés, pour rester relisibles et modifiables ;
- un **garde-fou** fait échouer la suite si un format est ajouté à la liste des
  formats annoncés sans être testé : promettre une extension que l'outil ne sait pas
  lire est pire que ne pas la proposer.

---

## 8. Références

- **SingleFile** — extension de capture de page (source des fichiers d'entrée web).
- Détail du pipeline de conversion : [ARCHITECTURE.md](ARCHITECTURE.md).

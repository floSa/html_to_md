# html_to_md

Nettoie les captures HTML faites avec l'extension **SingleFile** (Chrome/Firefox) et les convertit en **Markdown propre**, prêt pour l'ingestion dans un pipeline RAG.

Les pages sauvegardées avec SingleFile embarquent toute l'interface du site (barres de navigation, bannières, popups, boutons, CSS/JS inliné, icônes en base64...). Cet outil isole le contenu utile et jette le reste — **sans rien présumer du site d'origine**.

## Fonctionnement

Chaque fichier passe par cinq étapes :

0. **Formules mathématiques** ([maths.py](src/html_to_md/maths.py)) : les formules rendues par KaTeX, MathJax (v2/v3) ou MathML sont reconverties en **LaTeX** — `$...$` en ligne, `$$...$$` en bloc — à partir de la source que ces moteurs laissent dans le DOM.
1. **Hygiène** ([hygiene.py](src/html_to_md/hygiene.py)) : suppression du bruit non ambigu — `script`, `style`, `button`, éléments cachés (`sf-hidden`, `display:none`, attribut `hidden`), chrome de page (`nav`, `header`, `footer`, `aside`), rôles ARIA de navigation, commentaires.
2. **Extraction** ([extract.py](src/html_to_md/extract.py)) : isolement du contenu principal, en mode générique. Deux candidats sont comparés et le plus complet gagne :
   - les **conteneurs sémantiques HTML5** (`<article>`, `<main>`, `[role=main]`) ;
   - **readability-lxml** (l'algorithme du « mode lecture » de Firefox).

   En dernier recours, le `<body>` nettoyé est gardé tel quel.
3. **Images** ([convert.py](src/html_to_md/convert.py)) : les images de contenu encodées en base64 sont exportées dans un dossier `<nom>_assets/` à côté du `.md` ; les petites (< 4 Ko = icônes d'interface) sont supprimées.
4. **Conversion Markdown** : via markdownify (titres ATX, blocs de code clôturés avec leur langage quand la page l'indique).

**Garde-fou** : si le Markdown final conserve moins de 30 % du texte visible d'origine, ou fait moins de 200 caractères, le fichier est marqué `?` (à vérifier) dans le rapport — pour ne jamais ingérer silencieusement un document vidé par le nettoyage.

## 1. Installer et configurer SingleFile (capture des pages)

1. Installer l'extension :
   - Chrome / Edge : [SingleFile sur le Chrome Web Store](https://chromewebstore.google.com/detail/singlefile/mpiodijhokgodhhofbcjdecpffjipkle)
   - Firefox : [SingleFile sur addons.mozilla.org](https://addons.mozilla.org/fr/firefox/addon/single-file/)
2. Dans les options de l'extension (clic droit sur l'icône → *Gérer l'extension* → Options) :

   | Section | Option | État |
   |---|---|---|
   | Contenu HTML | compresser le contenu HTML | ✅ cocher |
   | Contenu HTML | supprimer les éléments cachés | ✅ cocher |
   | Contenu HTML | sauvegarder la page brute | ❌ laisser décoché (sinon les scripts et le DOM non rendu sont gardés) |
   | Contenu HTML | ne pas inclure la date de sauvegarde | ❌ laisser décoché |
   | Feuilles de style | supprimer les styles inutilisés | ✅ cocher |
   | Feuilles de style | supprimer les feuilles de styles pour les appareils autres que des écrans | ✅ cocher |
   | Images | supprimer les images pour des résolutions d'écran alternatives | ✅ cocher |
   | Polices de caractère | supprimer les polices inutilisées / alternatives | ✅ cocher les deux |

   Les scripts sont supprimés par défaut, pas d'option à cocher pour ça.
   → fichiers plus petits et plus propres dès la capture.
3. Sur la page à sauvegarder : clic sur l'icône SingleFile → un fichier `.html` autonome est téléchargé.

## 2. Installer l'outil

```bash
cd ~/mes_projets/html_to_md
python3 -m venv .venv
.venv/bin/pip install -e .
```

## 3. Lancer la conversion

```bash
# Un dossier entier (récursif), sortie dans ./out
.venv/bin/html2md "chemin/vers/captures/" -o out/

# Un seul fichier
.venv/bin/html2md "page.html" -o out/

# Options
.venv/bin/html2md --help
```

Les fichiers `.md` (et leurs dossiers d'images `_assets/`) sont créés dans le dossier de sortie, en conservant l'arborescence d'entrée.

**Nommage des fichiers** : `<source>_<Titre_De_L_Article>.md` — la source (nom du site, en snake_case) est déduite du `<title>` de la page ou de l'URL inscrite par SingleFile dans le fichier. Exemple :

```text
machine_learning_mastery_Essence_of_Bootstrap_Aggregation_Ensembles.md
kdnuggets_Feature_Stores_from_Scratch_A_Minimal_Working_Implementation.md
```

En cas de doublon dans un même lot, un suffixe `_2`, `_3`... est ajouté.

Sortie type :

```text
  page1.html  →  page1.md  (article, 34696 car., 11 img)
? page2.html  →  page2.md  (readability, 615 car., 0 img) [ratio faible (615/59697)]

2 fichier(s) traité(s) — 1 ok, 1 à vérifier, 0 en erreur.
```

La colonne entre parenthèses indique la **stratégie d'extraction** utilisée : `article`/`main` (conteneur sémantique), `readability` (extraction générique), `body` (dernier recours), ou le nom d'un profil personnalisé.

## Si un site donne de mauvais résultats

Le mode générique couvre la plupart des pages. Si un site précis ressort systématiquement en `?` (ratio faible) ou avec du bruit résiduel, on peut lui dédier un **profil** dans [config/selectors.yaml](config/selectors.yaml) :

```yaml
profiles:
  monsite:
    detect: ".article-reader"        # si ce sélecteur matche, le profil s'applique
    content: ".article-reader main"  # ce qu'on garde
    strip:                           # (optionnel) à supprimer DANS le contenu gardé
      - ".newsletter-banner"
```

Pour trouver les bons sélecteurs : ouvrir la capture dans un navigateur, inspecter le conteneur de l'article (F12), repérer sa classe ou son id stable. Les profils ont priorité sur le mode générique.


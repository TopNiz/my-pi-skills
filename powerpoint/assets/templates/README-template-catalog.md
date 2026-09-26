# Catalogue des patterns du template ESG

Ce dossier contient une description de chaque slide du fichier `ESG Innovation Sustainability PowerPoint Templates.pptx`. Les documents décrivent la géométrie, les formes, leur fonction narrative et les usages possibles.

> Le fichier `.pptx` lui-même n'est **pas** versionné : c'est un template tiers dont la redistribution n'est pas autorisée. Il réside hors du dépôt, dans le dossier configuré par `POWERPOINT_TEMPLATES_DIR` (voir `.env.example` à la racine du skill). Seule l'analyse produite ici — la description de chaque slide — est committée.

Le fichier `template-matching-catalog.yaml` fournit une version structurée pour les agents IA. Il référence les 48 documents du dossier avec le champ `source_doc`.

## Règle de provenance

Le template ESG est une source de géométrie et de composants visuels, pas une source éditoriale par défaut.

| Élément | Source par défaut | Action |
|---|---|---|
| Contenu et formulation | Slide cible | Préserver exactement |
| Typographie | Présentation cible | Préserver police, taille, graisse et traitement |
| Palette | Présentation cible | Préserver les couleurs de la cible |
| Arrière-plan | Présentation cible | Préserver l'arrière-plan existant |
| Géométrie | Slide du template | Importer ou adapter la composition |
| Formes et vecteurs éditables | Slide du template | Importer seulement les éléments nécessaires |
| Texte du template | Slide du template | Ne pas importer |
| Logo du template | Slide du template | Ne pas importer sans demande |
| Photographie du template | Slide du template | Utiliser uniquement avec accord explicite |
| Nouvel asset | Assets de la cible ou demande explicite | Ajouter uniquement si nécessaire |

## Champs principaux du YAML

- `id` : identifiant stable du pattern.
- `template_slide` : numéro de la slide dans le template source.
- `source_doc` : document Markdown correspondant dans ce dossier.
- `semantic_types` : intentions narratives couvertes.
- `item_count` : nombre indicatif d'éléments principaux.
- `flow` : relation visuelle, par exemple `linear`, `radial` ou `branching`.
- `hierarchy` : organisation, par exemple `equal`, `layered` ou `top_down`.
- `text_density` : volume de texte supportable.
- `geometry` : formes et relations à rechercher.
- `best_for` : usages recommandés.

## Processus pour un agent IA

1. Lire la spécification de la slide cible fournie par l'utilisateur dans son projet courant, quel que soit le nom du dossier. Résoudre `template_file` et `source_doc` relativement au dossier de ce catalogue.
2. Verrouiller le contenu et le style de la slide cible.
3. Extraire le type sémantique, le nombre d'éléments, le flux et la densité.
4. Chercher les patterns compatibles dans `template-matching-catalog.yaml`.
5. Lire le `source_doc` du meilleur pattern.
6. Construire la slide à partir du style cible.
7. Ajouter uniquement les formes et vecteurs autorisés par la provenance.
8. Ajouter un visuel externe uniquement s'il est demandé ou nécessaire.
9. Rendre la slide et vérifier le contenu, la lisibilité et les débordements.

## Exemple

La slide cible « Feuille de route de la présentation » est une `agenda` avec quatre éléments et un flux `linear`. Elle peut utiliser le pattern `agenda-bars` de la slide 3. Le contenu, les polices, la palette et l'arrière-plan restent ceux de Badevel ; les barres et leur organisation viennent du template.

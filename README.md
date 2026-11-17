# Bibliothèque de scripts — lecorre894-web

Dépôt public, zéro euro. Il stocke les scripts réutilisables inter-projets de René.

## Règle d'or
- Le CODE vit ici (versionné). L'INDEX pointe. La mémoire de Claude ne garde qu'un pointeur vers ce dépôt (registre-scripts).
- Un script = un fichier dans scripts/. Jamais de secret dans un fichier : vérifier SECRETS=0 avant tout commit.

## Ajouter un script
1. Déposer le fichier dans scripts/.
2. Sceller : bash outils/sceau.sh scripts/mon-script.sh
3. Ajouter une ligne dans INDEX.md : nom | rôle | chemin | sceau sha256 | commande.
4. git add -A && git commit && git push.

## Organes
- scripts/         : les scripts eux-mêmes
- outils/sceau.sh  : calcule le sha256 d'un fichier (le « sceau »)
- INDEX.md         : le catalogue, une ligne par script

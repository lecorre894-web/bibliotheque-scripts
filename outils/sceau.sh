#!/usr/bin/env bash
# Affiche le sceau sha256 d'un fichier. Usage: bash outils/sceau.sh <fichier>
set -e
f="${1:?Usage: sceau.sh <fichier>}"
sha256sum "$f" | awk '{print $1}'

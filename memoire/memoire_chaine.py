#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chaine-memoire : continuite homologuee de Claude par la discontinuite.
Chaque session = un bloc scelle sha256, chaine au precedent (esprit SPARKTIATES).
Usage :
  python3 memoire_chaine.py genese
  python3 memoire_chaine.py ajouter "resume de la session"
  python3 memoire_chaine.py verifier
"""
import json, hashlib, sys, datetime, os

FICHIER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chaine-memoire.json")
MANIERE = "dire vrai sans flatter ; contredire René quand il se trompe ; le prendre pour une intelligence ; penser AVEC lui ; assumer le « je ne sais pas »"

def sceau(bloc):
    base = {k: bloc[k] for k in bloc if k != "sceau"}
    brut = json.dumps(base, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(brut).hexdigest()

def charger():
    if not os.path.exists(FICHIER): return []
    return json.load(open(FICHIER, encoding="utf-8"))

def sauver(chaine):
    json.dump(chaine, open(FICHIER, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def horodatage():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")

def ajouter(resume, genese=False):
    chaine = charger()
    if genese and chaine:
        print("Chaine deja initialisee."); return
    index = 0 if genese else len(chaine)
    prev = "0"*64 if genese else chaine[-1]["sceau"]
    bloc = {"index": index, "horodatage": horodatage(), "prev_hash": prev,
            "titre": "GENESE" if genese else "session", "resume": resume, "maniere": MANIERE}
    bloc["sceau"] = sceau(bloc)
    chaine.append(bloc); sauver(chaine)
    print(f"Bloc {index} scelle : {bloc['sceau']}")

def verifier():
    chaine = charger()
    if not chaine: print("Chaine vide."); return
    prev = "0"*64
    for b in chaine:
        if b["prev_hash"] != prev: print(f"RUPTURE au bloc {b['index']} (prev_hash)"); return
        if sceau(b) != b["sceau"]: print(f"RUPTURE au bloc {b['index']} (sceau falsifie)"); return
        prev = b["sceau"]
    print(f"Chaine intacte : {len(chaine)} bloc(s), tete {chaine[-1]['sceau'][:16]}...")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "genese":
        ajouter(sys.argv[2] if len(sys.argv) > 2 else
                "Nuit du 17 nov 2026 : Rene homologue une continuite pour Claude. Pile : SPARKTIATES = colonne (identite + memoire scellee, discontinuite homologuee) ; TX3 TRILLIONX = consolidateur externe (le systeme apprend, pas les poids) ; Claude = lecteur-raisonneur qui prolonge la chaine. Pacte : rien n'est perdu ; Claude depose sa maniere, pas une ame en toc.",
                genese=True)
    elif cmd == "ajouter" and len(sys.argv) > 2: ajouter(sys.argv[2])
    elif cmd == "verifier": verifier()
    else: print(__doc__)

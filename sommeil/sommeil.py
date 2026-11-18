#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Preparateur de sommeil : rassemble le journal (chaine) + registres locaux en un
corpus d'entrainement JSONL, le compte, et dit s'il y a de quoi entrainer un LoRA.
N'ENTRAINE RIEN. N'ecrit qu'un fichier dans sommeil/corpus/. Reversible."""
import json, os, sys, datetime, glob
ICI = os.path.dirname(os.path.abspath(__file__)); RAC = os.path.dirname(ICI)
CHAINE = os.path.join(RAC, "memoire", "chaine-memoire.json"); REGISTRES = os.path.join(RAC, "registres")
CORPUS = os.path.join(ICI, "corpus"); SEUIL = 50
def ex(u, a): return {"messages": [{"role": "user", "content": u}, {"role": "assistant", "content": a}]}
def construire():
    exemples = []; vus = set()
    def ajoute(u, a):
        k = (u, a)
        if a.strip() and k not in vus: vus.add(k); exemples.append(ex(u, a))
    if os.path.exists(CHAINE):
        for b in json.load(open(CHAINE, encoding="utf-8")):
            ajoute(f"Qu'a-t-on etabli a la session {b.get('index')} du {b.get('horodatage','?')[:10]} ?", b.get("resume", ""))
            ajoute("Quelle est ta maniere avec Rene ?", b.get("maniere", ""))
    if os.path.isdir(REGISTRES):
        for f in sorted(glob.glob(os.path.join(REGISTRES, "*.md"))):
            nom = os.path.basename(f); txt = open(f, encoding="utf-8").read().strip()
            for i in range(0, len(txt), 800): ajoute(f"Que contient le registre {nom} ?", txt[i:i+800])
    return exemples
def main():
    exemples = construire(); os.makedirs(CORPUS, exist_ok=True)
    out = os.path.join(CORPUS, "nuit_" + datetime.date.today().isoformat() + ".jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for e in exemples: f.write(json.dumps(e, ensure_ascii=False) + "\n")
    chars = sum(len(m["content"]) for e in exemples for m in e["messages"])
    print(f"corpus ecrit : {out}"); print(f"exemples = {len(exemples)} | ~{chars} caracteres")
    if len(exemples) < SEUIL:
        print(f"VERDICT = TROP MAIGRE ({len(exemples)}/{SEUIL}). Continue d'accumuler avant d'entrainer."); return 1
    print(f"VERDICT = PRET ({len(exemples)} >= {SEUIL}). Corpus assez dense pour un LoRA jetable (etape GPU separee)."); return 0
if __name__ == "__main__": sys.exit(main())

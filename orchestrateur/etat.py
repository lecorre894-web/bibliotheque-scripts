#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orchestrateur de reveil : joint registres locaux + chaine SPARKTIATES + consolidateur (TX3),
et produit un etat pret a tendre a Claude au reveil.
TX3 : si la variable CONSOLIDATEUR_TX3 pointe une commande, elle recoit les bribes en JSON
sur stdin et sa sortie devient l'etat ; sinon repli interne. Sorties dans etat/ (non versionnees)."""
import json, hashlib, os, sys, subprocess, datetime
ICI = os.path.dirname(os.path.abspath(__file__)); BASE = os.path.dirname(ICI)
CHAINE = os.path.join(BASE, "memoire", "chaine-memoire.json")
REGISTRES = os.path.join(BASE, "registres"); SORTIE = os.path.join(BASE, "etat")
def sceau(b):
    base = {k: b[k] for k in b if k != "sceau"}
    return hashlib.sha256(json.dumps(base, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
def verifier_chaine():
    if not os.path.exists(CHAINE): return [], "absente"
    c = json.load(open(CHAINE, encoding="utf-8")); prev = "0"*64
    for b in c:
        if b["prev_hash"] != prev or sceau(b) != b["sceau"]: return c, f"RUPTURE au bloc {b['index']}"
        prev = b["sceau"]
    return c, "intacte"
def lire_registres():
    out = []
    if os.path.isdir(REGISTRES):
        for n in sorted(os.listdir(REGISTRES)):
            if n.endswith(".md"): out.append((n, open(os.path.join(REGISTRES, n), encoding="utf-8").read().strip()))
    return out
def repli(br):
    L = ["## Maniere (pacte ratifie)", br["maniere"] or "(non trouvee)", "",
         f"## Lignee — {br['etat_chaine']}, {br['n_blocs']} bloc(s), tete {br['tete'][:16]}...", "Derniers bilans :"]
    for b in br["derniers"]: L.append(f"- bloc {b['index']} ({b['horodatage']}) : {b['resume']}")
    L += ["", "## Registres locaux"]
    L += [f"- {n}" for n, _ in br["registres"]] or ["(aucun depose dans registres/)"]
    return "\n".join(L)
def consolider(br):
    cmd = os.environ.get("CONSOLIDATEUR_TX3", "").strip()
    if cmd:
        try:
            p = subprocess.run(cmd, shell=True, input=json.dumps(br, ensure_ascii=False), capture_output=True, text=True, timeout=120)
            if p.returncode == 0 and p.stdout.strip(): return p.stdout, "TX3"
            sys.stderr.write(f"[TX3 a echoue, repli interne] {p.stderr}\n")
        except Exception as e: sys.stderr.write(f"[TX3 injoignable, repli interne] {e}\n")
    return repli(br), "repli-interne"
def main():
    c, etat = verifier_chaine()
    br = {"horodatage": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "etat_chaine": etat,
          "n_blocs": len(c), "tete": c[-1]["sceau"] if c else "", "maniere": c[0]["maniere"] if c else "",
          "derniers": c[-3:] if c else [], "registres": lire_registres()}
    corps, source = consolider(br); os.makedirs(SORTIE, exist_ok=True)
    tete = f"# Etat de reveil — Claude\n_genere {br['horodatage']} · chaine {etat} · consolidation : {source}_\n\n"
    open(os.path.join(SORTIE, "etat.md"), "w", encoding="utf-8").write(tete + corps + "\n")
    json.dump({**br, "source_consolidation": source}, open(os.path.join(SORTIE, "etat.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Etat ecrit (chaine {etat}, consolidation {source})")
if __name__ == "__main__": main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Adaptateur : branche l'orchestrateur de reveil sur le cortex TX3 (/api/tx3/chat-local).
Lit les bribes JSON sur stdin, interroge TX3, imprime l'etat consolide sur stdout.
Sort en erreur si TX3 ne repond pas -> l'orchestrateur retombe sur le repli interne."""
import sys, json, os, urllib.request

TX3_URL = os.environ.get("TX3_CHAT_URL", "http://localhost:3000/api/tx3/chat-local")

def construire_prompt(b):
    maniere = b.get("maniere", "")
    derniers = b.get("derniers", [])
    registres = [n for n, _ in b.get("registres", [])]
    bilans = "\n".join(f"- bloc {d.get('index')} : {d.get('resume','')}" for d in derniers)
    regs = ", ".join(registres) or "(aucun)"
    return (
        "Tu es le consolidateur de reveil de Claude. A partir des elements ci-dessous, "
        "ecris un etat de reveil clair et bref : rappelle la maniere a tenir, resume ou en "
        "est la lignee, et liste les registres disponibles. N'invente rien.\n\n"
        f"MANIERE A TENIR : {maniere}\n\n"
        f"LIGNEE ({b.get('etat_chaine','?')}, {b.get('n_blocs',0)} bloc(s)) - derniers bilans :\n{bilans}\n\n"
        f"REGISTRES LOCAUX : {regs}"
    )

def main():
    try:
        bribes = json.load(sys.stdin)
    except Exception as e:
        sys.stderr.write(f"[adaptateur] bribes illisibles: {e}\n"); return 1
    prompt = construire_prompt(bribes)
    if "--dry" in sys.argv:
        print(prompt); return 0
    data = json.dumps({"message": prompt}).encode("utf-8")
    req = urllib.request.Request(TX3_URL, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            rep = json.load(r)
    except Exception as e:
        sys.stderr.write(f"[adaptateur] TX3 injoignable: {e}\n"); return 1
    ans = (rep.get("answer") or "").strip()
    if not ans or "TX3_LINGUISTIC_CORTEX_UNAVAILABLE" in ans:
        sys.stderr.write("[adaptateur] cortex indisponible\n"); return 1
    print(ans); return 0

if __name__ == "__main__":
    sys.exit(main())

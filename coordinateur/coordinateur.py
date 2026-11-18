#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Coordinateur : demande -> rappel memoire -> comprehension Qwen -> persistance -> verification.
Pur Python + SQLite (stdlib). Si Qwen injoignable : statut MODELE_INJOIGNABLE, n'invente rien.
Usage: python3 coordinateur.py "ta demande" """
import sys, os, json, glob, re, hashlib, datetime, sqlite3, urllib.request
ICI = os.path.dirname(os.path.abspath(__file__)); RAC = os.path.dirname(ICI)
CORPUS = os.path.join(RAC, "sommeil", "corpus"); DB = os.path.join(ICI, "memory.sqlite3")
OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")
MODELE = os.environ.get("MODELE", "qwen2.5:7b")
MANIERE = "dire vrai sans flatter ; contredire Rene quand il se trompe ; assumer le je-ne-sais-pas"
def mots(s): return set(w for w in re.findall(r"[a-zA-Zà-ÿ]+", s.lower()) if len(w) > 3)
def rappel(demande, k=5):
    q = mots(demande); scored = []
    for f in glob.glob(os.path.join(CORPUS, "*.jsonl")):
        for l in open(f, encoding="utf-8"):
            try: m = json.loads(l)["messages"]
            except Exception: continue
            txt = m[0]["content"] + " " + m[1]["content"]; s = len(q & mots(txt))
            if s: scored.append((s, m[1]["content"]))
    scored.sort(reverse=True); return [c for _, c in scored[:k]]
def comprendre(demande, contexte):
    prompt = "CONTEXTE (memoire):\n- " + "\n- ".join(contexte) + f"\n\nDEMANDE:\n{demande}"
    body = json.dumps({"model": MODELE, "messages": [
        {"role": "system", "content": f"Tu es le cortex de continuite de Rene. Reponds STRICTEMENT a partir du CONTEXTE ci-dessous. Si le CONTEXTE contient la reponse, enonce-la fermement et directement, sans hedger. N'ecris JAMAIS que c'est une notion non standard ou vague si le CONTEXTE la definit. Sers-toi uniquement du CONTEXTE ; si et seulement si rien n'y repond, dis-le en une phrase. Maniere: {MANIERE}."},
        {"role": "user", "content": prompt}]}).encode("utf-8")
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)["choices"][0]["message"]["content"].strip(), "OK"
    except Exception as e:
        sys.stderr.write(f"[coordinateur] Qwen injoignable: {e}\n"); return "", "MODELE_INJOIGNABLE"
def sceau(ts, d, c, rep): return hashlib.sha256(f"{ts}|{d}|{c}|{rep}".encode("utf-8")).hexdigest()
def persister(ts, d, contexte, rep, statut):
    c = "\n".join(contexte); s = sceau(ts, d, c, rep)
    con = sqlite3.connect(DB); con.execute("PRAGMA journal_mode=WAL"); con.execute("PRAGMA busy_timeout=5000")
    con.execute("CREATE TABLE IF NOT EXISTS interactions(id INTEGER PRIMARY KEY AUTOINCREMENT,ts TEXT,demande TEXT,contexte TEXT,reponse TEXT,modele TEXT,statut TEXT,sceau TEXT)")
    cur = con.execute("INSERT INTO interactions(ts,demande,contexte,reponse,modele,statut,sceau) VALUES(?,?,?,?,?,?,?)",
                      (ts, d, c, rep, MODELE, statut, s)); con.commit(); rid = cur.lastrowid; con.close(); return rid, s
def verifier(rid):
    con = sqlite3.connect(DB); row = con.execute("SELECT ts,demande,contexte,reponse,sceau FROM interactions WHERE id=?", (rid,)).fetchone(); con.close()
    ts, d, c, rep, s = row; return "OK" if sceau(ts, d, c, rep) == s else "RUPTURE"
def main():
    if len(sys.argv) < 2: print('Usage: coordinateur.py "ta demande"'); return 1
    demande = sys.argv[1]; ts = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    contexte = rappel(demande); print(f"[1 rappel] {len(contexte)} element(s) de memoire retenus")
    rep, statut = comprendre(demande, contexte); print(f"[2 comprehension] statut={statut}")
    rid, s = persister(ts, demande, contexte, rep, statut); print(f"[3 persistance] interaction #{rid} ecrite, sceau {s[:16]}...")
    print(f"[4 verification] integrite={verifier(rid)}")
    print("\n--- REPONSE ---"); print(rep if rep else "(aucune : Qwen injoignable, rien invente)"); return 0
if __name__ == "__main__": sys.exit(main())

#!/usr/bin/env python3
# Duel : lobe seul | ensemble + lobe | ensemble + Qwen 7B (Ollama). Memes questions, meme score.
import json, os, re, subprocess, sys, urllib.request
ICI = os.path.dirname(os.path.abspath(__file__)); RACINE = os.path.dirname(ICI)
LOBE = "http://localhost:11500/v1/chat/completions"
ex = json.load(open(os.path.join(ICI, "lobes", "continuite", "examen.json"), encoding="utf-8"))["memoire_apres"][:4]
qs = [(t["q"].replace("Rappelle-moi precisement : ", ""), t["attendu"]) for t in ex]
def mots(t): return {m for m in re.findall(r"\w+", t.lower()) if len(m) > 3}
def score(rep, att): r = mots(att); return len(r & mots(rep)) / max(1, len(r))
def lobe_seul(q):
    b = json.dumps({"model": "lobe-continuite", "messages": [{"role": "user", "content": q}]}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(LOBE, b, {"Content-Type": "application/json"}), timeout=180) as r:
            return json.load(r)["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"(INJOIGNABLE : {e})"
def ensemble(q, url=None, modele=None):
    env = dict(os.environ)
    if url: env["OLLAMA_URL"] = url; env["MODELE"] = modele
    else: env.pop("OLLAMA_URL", None); env.pop("MODELE", None)
    o = subprocess.run(["python3", os.path.join(RACINE, "coordinateur", "coordinateur.py"), q],
                       cwd=RACINE, env=env, capture_output=True, text=True, timeout=300).stdout
    return o.split("--- REPONSE ---", 1)[-1].strip() if "--- REPONSE ---" in o else "(pas de reponse)"
confs = [("lobe seul", lambda q: lobe_seul(q)),
         ("ensemble + lobe", lambda q: ensemble(q, LOBE, "lobe-continuite")),
         ("ensemble + Qwen 7B", lambda q: ensemble(q))]
tot = {c: 0.0 for c, _ in confs}
for i, (q, att) in enumerate(qs, 1):
    print(f"\n=== Q{i} : {q}\nATTENDU : {att[:150]}")
    for c, f in confs:
        rep = f(q); s = score(rep, att); tot[c] += s
        print(f"  [{c:18}] {s:4.0%} | {rep[:170]}")
print("\n=== MOYENNE SUR 4 QUESTIONS")
for c, _ in confs: print(f"  {c:18} : {tot[c] / len(qs):.0%}")

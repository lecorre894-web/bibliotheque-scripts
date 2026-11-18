#!/usr/bin/env python3
# Mesure REELLE de l'energie GPU par reponse (nvidia-smi) : cortex 3B (ensemble) vs Qwen 7B L1 (Ollama).
import json, subprocess, threading, time, urllib.request
CONFS = [("cortex 3B ensemble", "http://localhost:11500/v1/chat/completions", "ensemble"),
         ("Qwen 7B L1 (Ollama)", "http://localhost:11434/v1/chat/completions", "qwen2.5-l1")]
QS = ["Quelle regle de cout pour les projets de Rene ?", "Que refuse le serveur du cortex ?",
      "Qu'est-ce que la chaine-memoire ?", "Quelle est l'instance de Rene ?", "Pourquoi le rappel reste-t-il lexical ?"]
mes = []; fin = threading.Event()
def echantillonner():
    while not fin.is_set():
        try:
            w = float(subprocess.run(["nvidia-smi", "--query-gpu=power.draw", "--format=csv,noheader,nounits"],
                                     capture_output=True, text=True).stdout.strip().split("\n")[0])
            mes.append((time.time(), w))
        except Exception: pass
        time.sleep(0.1)
def energie(t0, t1):
    pts = [(t, w) for t, w in mes if t0 <= t <= t1]
    return sum(w * (pts[i + 1][0] - t) for i, (t, w) in enumerate(pts[:-1])), (sum(w for _, w in pts) / max(1, len(pts)))
def demander(url, modele, q):
    b = json.dumps({"model": modele, "messages": [{"role": "user", "content": q}], "max_tokens": 120, "temperature": 0}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, b, {"Content-Type": "application/json"}), timeout=300) as r:
        return json.load(r)["choices"][0]["message"]["content"]
th = threading.Thread(target=echantillonner, daemon=True); th.start()
time.sleep(4); _, repos = energie(time.time() - 4, time.time())
print(f"repos GPU : {repos:.0f} W")
for nom, url, modele in CONFS:
    try: demander(url, modele, "bonjour")
    except Exception as e: print(f"{nom} : INJOIGNABLE ({e})"); continue
    t0 = time.time(); n = 0
    for q in QS: demander(url, modele, q); n += 1
    t1 = time.time(); j, wm = energie(t0, t1); jutile = j - repos * (t1 - t0)
    print(f"{nom:22} : {n} reponses en {t1 - t0:5.1f} s | {wm:4.0f} W moyen | {j / n:6.0f} J/reponse ({jutile / n:5.0f} J au-dessus du repos)")
fin.set()

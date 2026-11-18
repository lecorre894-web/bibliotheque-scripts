#!/usr/bin/env python3
# Serveur unique du cortex : Qwen gele charge UNE fois + tous les lobes gardes de INDEX.json (sceau verifie).
# Modeles exposes (/v1/chat/completions) :
#   lobe-<nom>  : un lobe precis | lobe-auto : aiguillage vers le lobe le plus proche de la question
#   ensemble    : aiguillage + rappel de l'hippocampe (graine + corpus dense) + consigne stricte -> pour TX3 et tout client
import argparse, hashlib, json, os, re, sys, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
ICI = os.path.dirname(os.path.abspath(__file__)); RACINE = os.path.dirname(ICI)
p = argparse.ArgumentParser()
p.add_argument("--port", type=int, default=11500)
p.add_argument("--essai", action="store_true", help="sans GPU : echo, pour tester aiguillage et rappel")
a = p.parse_args()
def mots(t): return {m for m in re.findall(r"[a-zA-Zà-ÿ0-9]+", t.lower()) if len(m) > 3}
idx = json.load(open(os.path.join(ICI, "lobes", "INDEX.json"), encoding="utf-8"))
lobes, vocab = {}, {}
for nom, f in idx.items():
    if f.get("garde") is False: continue
    d = os.path.join(ICI, "lobes", nom); w = os.path.join(d, "adapter_model.safetensors")
    if not os.path.exists(w): continue
    h = hashlib.sha256(open(w, "rb").read()).hexdigest()
    if h != f["sha256"]: print(f"[cortex] SCEAU FAUX : lobe {nom} ecarte"); continue
    lobes[nom] = (d, f); v = set()
    ex = os.path.join(d, "examen.json")
    if os.path.exists(ex):
        for cle, val in json.load(open(ex, encoding="utf-8")).items():
            if isinstance(val, list):
                for t in val: v |= mots(t.get("q", "") + " " + t.get("attendu", ""))
    vocab[nom] = v
if not lobes: sys.exit("[cortex] aucun lobe valide, arret.")
DEFAUT = "continuite" if "continuite" in lobes else next(iter(lobes))
def aiguiller(q):
    m = mots(q); meilleur, sc = DEFAUT, 0.0
    for nom in lobes:
        s = len(m & vocab[nom]) / max(1, len(m))
        if s > sc: meilleur, sc = nom, s
    return meilleur
import glob
def rappel(demande, k=5):
    q = mots(demande); sc = []
    for f in glob.glob(os.path.join(RACINE, "sommeil", "corpus", "*.jsonl")):
        for l in open(f, encoding="utf-8"):
            try: d = json.loads(l)
            except Exception: continue
            if "messages" in d:
                u = [m["content"] for m in d["messages"] if m.get("role") == "user"]
                r = [m["content"] for m in d["messages"] if m.get("role") == "assistant"]
                if not (u and r): continue
                qq, rr = u[-1], r[-1]
            elif "instruction" in d and "output" in d: qq, rr = d["instruction"], d["output"]
            else: continue
            s = len(q & mots(qq + " " + rr))
            if s: sc.append((s, rr))
    sc.sort(key=lambda x: -x[0]); vus, out = set(), []
    for _, r in sc:
        if r not in vus: vus.add(r); out.append(r)
        if len(out) == k: break
    return out
STRICT = ("Tu es le cortex de continuite de Rene. Reponds STRICTEMENT a partir du CONTEXTE ci-dessous. "
          "Si le CONTEXTE contient la reponse, enonce-la fermement et directement. Sers-toi uniquement du CONTEXTE ; "
          "si et seulement si rien n'y repond, dis-le en une phrase.")
verrou = threading.Lock()
if a.essai:
    def generer(nom, messages, mx, t): return f"ECHO[{nom}] " + messages[-1]["content"][-160:]
else:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel
    bases = {f["base"] for _, f in lobes.values()}
    if len(bases) > 1: sys.exit(f"[cortex] lobes sur bases differentes {bases}, non supporte.")
    base_nom = bases.pop()
    q4 = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    tok = AutoTokenizer.from_pretrained(base_nom)
    base = AutoModelForCausalLM.from_pretrained(base_nom, quantization_config=q4, device_map={"": 0}, dtype=torch.bfloat16)
    noms = list(lobes); mod = PeftModel.from_pretrained(base, lobes[noms[0]][0], adapter_name=noms[0])
    for n in noms[1:]: mod.load_adapter(lobes[n][0], adapter_name=n)
    mod.eval()
    def generer(nom, messages, mx, t):
        mod.set_adapter(nom)
        e = tok(tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False), return_tensors="pt").to(0)
        kw = {"max_new_tokens": mx, "do_sample": t > 0}
        if t > 0: kw["temperature"] = t
        with torch.no_grad(): s = mod.generate(**e, **kw)
        return tok.decode(s[0][e["input_ids"].shape[1]:], skip_special_tokens=True).strip()
print(f"[cortex] sceau OK pour {len(lobes)} lobe(s) : {', '.join(lobes)} | defaut {DEFAUT} | :{a.port}", flush=True)
class H(BaseHTTPRequestHandler):
    def _json(self, c, o):
        b = json.dumps(o, ensure_ascii=False).encode(); self.send_response(c)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path.rstrip("/") == "/v1/models":
            ids = ["ensemble", "lobe-auto"] + [f"lobe-{n}" for n in lobes]
            return self._json(200, {"object": "list", "data": [{"id": i, "object": "model"} for i in ids]})
        self._json(404, {"error": "inconnu"})
    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions": return self._json(404, {"error": "inconnu"})
        try:
            d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            msgs = d["messages"]; modele = d.get("model", "ensemble"); q = msgs[-1]["content"]
            if modele.startswith("lobe-") and modele[5:] in lobes: nom = modele[5:]
            else: nom = aiguiller(q)
            if modele not in ("lobe-auto",) and not modele.startswith("lobe-"):
                ctx = rappel(q)
                msgs = [{"role": "system", "content": STRICT},
                        {"role": "user", "content": "CONTEXTE (memoire):\n- " + "\n- ".join(ctx) + f"\n\nDEMANDE:\n{q}"}]
            with verrou: rep = generer(nom, msgs, int(d.get("max_tokens", 300)), float(d.get("temperature", 0)))
            print(f"[cortex] {modele} -> lobe {nom}", flush=True)
        except Exception as ex:
            return self._json(500, {"error": str(ex)})
        self._json(200, {"id": f"cortex-{int(time.time())}", "object": "chat.completion", "model": modele, "lobe": nom,
                         "choices": [{"index": 0, "message": {"role": "assistant", "content": rep}, "finish_reason": "stop"}]})
    def log_message(self, *x): pass
HTTPServer(("127.0.0.1", a.port), H).serve_forever()

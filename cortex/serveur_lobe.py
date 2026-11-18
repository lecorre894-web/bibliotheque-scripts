#!/usr/bin/env python3
# Serveur du cortex : Qwen gele en 4 bits + un lobe de la bibliotheque, parle comme Ollama
# (/v1/chat/completions). Sceau d'abord : refuse un lobe dont le sha256 ne correspond pas a INDEX.json.
import argparse, hashlib, json, os, sys, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
ICI = os.path.dirname(os.path.abspath(__file__))
p = argparse.ArgumentParser()
p.add_argument("--lobe", default="continuite")
p.add_argument("--port", type=int, default=11500)
p.add_argument("--essai", action="store_true", help="sans GPU : repond en echo, pour tester la plomberie")
a = p.parse_args()
dossier = os.path.join(ICI, "lobes", a.lobe)
NOM = f"lobe-{a.lobe}"

def sceau_ok():
    idx = json.load(open(os.path.join(ICI, "lobes", "INDEX.json"), encoding="utf-8"))
    attendu = idx[a.lobe]["sha256"]
    reel = hashlib.sha256(open(os.path.join(dossier, "adapter_model.safetensors"), "rb").read()).hexdigest()
    return attendu == reel, idx[a.lobe], reel

if a.essai:
    def generer(messages, max_tokens, temperature):
        return "ECHO: " + messages[-1]["content"][:200]
    print(f"[cortex] MODE ESSAI (echo) sur :{a.port}")
else:
    ok, fiche, reel = sceau_ok()
    if not ok:
        sys.exit(f"[cortex] SCEAU FAUX : lobe {a.lobe} altere ({reel[:16]}...), refus de charger.")
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import PeftModel
    q4 = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                            bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    tok = AutoTokenizer.from_pretrained(fiche["base"])
    base = AutoModelForCausalLM.from_pretrained(fiche["base"], quantization_config=q4, device_map={"": 0}, dtype=torch.bfloat16)
    mod = PeftModel.from_pretrained(base, dossier); mod.eval()
    print(f"[cortex] sceau OK {reel[:16]}... | base {fiche['base']} | lobe {a.lobe} | memoire {fiche.get('memoire_avant')}->{fiche.get('memoire_apres')} | :{a.port}")
    def generer(messages, max_tokens, temperature):
        txt = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
        e = tok(txt, return_tensors="pt").to(0)
        kw = {"max_new_tokens": max_tokens, "do_sample": temperature > 0}
        if temperature > 0: kw["temperature"] = temperature
        with torch.no_grad():
            s = mod.generate(**e, **kw)
        return tok.decode(s[0][e["input_ids"].shape[1]:], skip_special_tokens=True).strip()

class H(BaseHTTPRequestHandler):
    def _json(self, code, obj):
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path.rstrip("/") == "/v1/models":
            return self._json(200, {"object": "list", "data": [{"id": NOM, "object": "model"}]})
        self._json(404, {"error": "inconnu"})
    def do_POST(self):
        if self.path.rstrip("/") != "/v1/chat/completions":
            return self._json(404, {"error": "inconnu"})
        try:
            d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            rep = generer(d["messages"], int(d.get("max_tokens", 300)), float(d.get("temperature", 0)))
        except Exception as ex:
            return self._json(500, {"error": str(ex)})
        self._json(200, {"id": f"cortex-{int(time.time())}", "object": "chat.completion", "model": NOM,
                         "choices": [{"index": 0, "message": {"role": "assistant", "content": rep}, "finish_reason": "stop"}]})
    def log_message(self, *x): pass

ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()

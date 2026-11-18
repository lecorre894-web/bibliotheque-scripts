#!/usr/bin/env python3
# Cycle complet de l'ensemble : 1) corpus dense fabrique en local par Qwen 7B (Ollama), filtre anti-invention
# 2) sommeil d'un lobe neuf  3) examen equitable (sans accents) : modele nu / ancien lobe / nouveau lobe.
import argparse, glob, hashlib, json, os, random, re, subprocess, time, unicodedata, urllib.request
ICI = os.path.dirname(os.path.abspath(__file__)); RACINE = os.path.dirname(ICI)
p = argparse.ArgumentParser()
p.add_argument("--ancien", default="continuite"); p.add_argument("--nouveau", default="continuite2")
p.add_argument("--max_morceaux", type=int, default=120); p.add_argument("--passes", type=int, default=4)
p.add_argument("--rang", type=int, default=8); p.add_argument("--etape", default="tout", help="tout | corpus | sommeil")
p.add_argument("--ollama", default="http://localhost:11434")
a = p.parse_args()
SENSIBLE = re.compile(r"curat|mandataire|tutelle|sant[eé]|m[eé]dic|maladie|polio|invalidit|aah|pch|obs[eè]ques|"
                      r"t[eé]l[eé]phone|@|adresse|rue |cedex|salaire|dette|compte bancaire|iban|h[oô]pital|usld", re.I)
def sans_acc(t): return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
def mots(t): return {m for m in re.findall(r"\w+", sans_acc(t)) if len(m) > 3}
def score(rep, att): r = mots(att); return len(r & mots(rep)) / max(1, len(r))

# ---------- 1) corpus dense ----------
def morceaux():
    txt = []
    for f in ["memoire/chaine-memoire.json", "claude/claude-chaine.json"]:
        f = os.path.join(RACINE, f)
        if os.path.exists(f):
            for b in json.load(open(f, encoding="utf-8")):
                t = b.get("texte") or b.get("contenu") or b.get("bilan") or ""
                if isinstance(t, str) and len(t) > 60: txt.append(t)
    for f in glob.glob(os.path.join(RACINE, "registres", "*.md")) + glob.glob(os.path.join(RACINE, "etat", "*.md")) + glob.glob(os.path.join(RACINE, "sommeil", "corpus", "sources", "*.md")):
        bloc = ""
        for l in open(f, encoding="utf-8"):
            l = l.strip()
            if not l or l.startswith("---"):
                if len(bloc) > 120: txt.append(bloc)
                bloc = ""; continue
            bloc += " " + l
            if len(bloc) > 700: txt.append(bloc); bloc = ""
        if len(bloc) > 120: txt.append(bloc)
    vus, out = set(), []
    for t in txt:
        k = sans_acc(t)[:200]
        if k in vus or SENSIBLE.search(t): continue
        vus.add(k); out.append(t.strip())
    return out
def fabriquer(m):
    consigne = ("Tu fabriques des fiches de revision. A partir du TEXTE seulement, ecris 3 paires question/reponse "
                "factuelles en francais, sans rien inventer ni ajouter. Reponds UNIQUEMENT par du JSON : "
                '[{"question": "...", "reponse": "..."}]')
    b = json.dumps({"model": "qwen2.5:7b", "temperature": 0.2, "messages": [
        {"role": "system", "content": consigne}, {"role": "user", "content": "TEXTE :\n" + m}]}).encode()
    req = urllib.request.Request(a.ollama + "/v1/chat/completions", b, {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        rep = json.load(r)["choices"][0]["message"]["content"]
    j = re.search(r"\[.*\]", rep, re.S)
    if not j: return []
    try: paires = json.loads(j.group(0))
    except Exception: return []
    bonnes = []
    for x in paires:
        q, r = str(x.get("question", "")).strip(), str(x.get("reponse", "")).strip()
        if len(q) < 8 or len(r) < 8 or SENSIBLE.search(q + r): continue
        mr = mots(r)
        if mr and len(mr & mots(m)) / len(mr) >= 0.6: bonnes.append({"instruction": q, "output": r})
    return bonnes
def etape_corpus():
    ms = morceaux()[:a.max_morceaux]
    print(f"[1 corpus] {len(ms)} morceaux sources (sensibles exclus)")
    sortie = os.path.join(RACINE, "sommeil", "corpus", "dense_auto.jsonl"); os.makedirs(os.path.dirname(sortie), exist_ok=True)
    n = rejet = 0
    with open(sortie, "w", encoding="utf-8") as f:
        for i, m in enumerate(ms, 1):
            try: ps = fabriquer(m)
            except Exception as e: print(f"  morceau {i}: Ollama injoignable ({e})"); continue
            rejet += 3 - len(ps)
            for x in ps: f.write(json.dumps(x, ensure_ascii=False) + "\n"); n += 1
            if i % 10 == 0: print(f"  {i}/{len(ms)} morceaux -> {n} paires gardees, {rejet} rejetees")
    print(f"[1 corpus] {n} paires gardees, {rejet} rejetees (invention ou sensible) -> {sortie}")
    try:
        urllib.request.urlopen(urllib.request.Request(a.ollama + "/api/generate",
            json.dumps({"model": "qwen2.5:7b", "keep_alive": 0}).encode(), {"Content-Type": "application/json"}), timeout=30)
    except Exception: pass
    return n

# ---------- 2) sommeil + 3) examen ----------
def lire(motif):
    ex = []
    for f in sorted(glob.glob(motif)):
        for l in open(f, encoding="utf-8"):
            l = l.strip()
            if not l: continue
            d = json.loads(l)
            if "messages" in d:
                u = [m["content"] for m in d["messages"] if m.get("role") == "user"]
                r = [m["content"] for m in d["messages"] if m.get("role") == "assistant"]
                if u and r: ex.append((u[-1], r[-1]))
                continue
            for q, r in (("instruction", "output"), ("prompt", "completion"), ("question", "reponse"), ("input", "output")):
                if q in d and r in d: ex.append((str(d[q]), str(d[r]))); break
    return ex
def etape_sommeil_examen():
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    cdir = os.path.join(RACINE, "sommeil", "corpus")
    graine = [e for f in sorted(glob.glob(os.path.join(cdir, "*.jsonl"))) if not f.endswith("dense_auto.jsonl") for e in lire(f)]
    random.Random(0).shuffle(graine); n_ex = max(1, int(len(graine) * 0.2))
    jamais, appris_g = graine[:n_ex], graine[n_ex:]
    dense = lire(os.path.join(cdir, "dense_auto.jsonl"))
    jv = {sans_acc(q) for q, _ in jamais}
    dense = [x for x in dense if sans_acc(x[0]) not in jv]
    appris = appris_g + dense
    memoire = [("Rappelle-moi precisement : " + q[0].lower() + q[1:], r) for q, r in appris_g[:15]]
    rd = random.Random(1); dense_q = rd.sample(dense, min(10, len(dense)))
    print(f"[2 sommeil] {len(appris)} exemples appris ({len(appris_g)} graine + {len(dense)} denses) | examen : "
          f"{len(memoire)} memoire, {len(jamais)} jamais vus, {len(dense_q)} denses")
    if not memoire or not jamais:
        raise SystemExit("EXAMEN VIDE : graine introuvable ou trop maigre, arret AVANT le sommeil (rien n'est scelle).")
    idx_f = os.path.join(ICI, "lobes", "INDEX.json"); idx = json.load(open(idx_f, encoding="utf-8"))
    base_nom = idx[a.ancien]["base"]; anc_dir = os.path.join(ICI, "lobes", a.ancien)
    h_anc = hashlib.sha256(open(os.path.join(anc_dir, "adapter_model.safetensors"), "rb").read()).hexdigest()
    if h_anc != idx[a.ancien]["sha256"]: raise SystemExit("SCEAU FAUX sur l'ancien lobe, arret.")
    tok = AutoTokenizer.from_pretrained(base_nom)
    q4 = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
    mod = AutoModelForCausalLM.from_pretrained(base_nom, quantization_config=q4, device_map={"": 0}, dtype=torch.bfloat16)
    mod = prepare_model_for_kbit_training(mod, use_gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False})
    mod = get_peft_model(mod, LoraConfig(r=a.rang, lora_alpha=2 * a.rang, lora_dropout=0.05, bias="none",
                          task_type="CAUSAL_LM", target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]))
    def invite(q): return tok.apply_chat_template([{"role": "user", "content": q}], add_generation_prompt=True, tokenize=False)
    opt = torch.optim.AdamW([x for x in mod.parameters() if x.requires_grad], lr=2e-4)
    mod.train(); t0 = time.time()
    for ps in range(a.passes):
        random.Random(ps).shuffle(appris); tot = 0.0
        for q, r in appris:
            pi = tok(invite(q), add_special_tokens=False)["input_ids"]; ri = tok(r + tok.eos_token, add_special_tokens=False)["input_ids"]
            ids = torch.tensor([(pi + ri)[:512]]).to(0); lab = torch.tensor([([-100] * len(pi) + ri)[:512]]).to(0)
            perte = mod(input_ids=ids, labels=lab).loss; perte.backward(); opt.step(); opt.zero_grad(); tot += perte.item()
        print(f"  passe {ps + 1}/{a.passes} : perte {tot / len(appris):.3f}")
    print(f"[2 sommeil] termine en {time.time() - t0:.0f} s")
    nv_dir = os.path.join(ICI, "lobes", a.nouveau); os.makedirs(nv_dir, exist_ok=True); mod.save_pretrained(nv_dir)
    mod.load_adapter(anc_dir, adapter_name="ancien")
    def interroger(liste):
        mod.eval(); s = 0.0; tr = []
        for q, r in liste:
            e = tok(invite(q), return_tensors="pt").to(0)
            with torch.no_grad(): o = mod.generate(**e, max_new_tokens=80, do_sample=False)
            rep = tok.decode(o[0][e["input_ids"].shape[1]:], skip_special_tokens=True).strip()
            sc = score(rep, r); s += sc; tr.append({"q": q, "attendu": r, "repondu": rep, "score": round(sc, 2)})
        return s / max(1, len(liste)), tr
    res, traces = {}, {}
    for conf in ["nu", "ancien", "nouveau"]:
        for nom, liste in [("memoire", memoire), ("jamais_vus", jamais), ("denses", dense_q)]:
            if conf == "nu":
                with mod.disable_adapter(): sc, tr = interroger(liste)
            else:
                mod.set_adapter("ancien" if conf == "ancien" else "default"); sc, tr = interroger(liste)
            res[(conf, nom)] = sc; traces[f"{conf}/{nom}"] = tr
    print("[3 examen] score sans accents      memoire | jamais vus | denses (appris, info)")
    for conf in ["nu", "ancien", "nouveau"]:
        print(f"  {conf:8}                        {res[(conf,'memoire')]:5.0%} |   {res[(conf,'jamais_vus')]:5.0%}    | {res[(conf,'denses')]:5.0%}")
    moy = lambda c: (res[(c, "memoire")] + res[(c, "jamais_vus")]) / 2   # denses = deja appris, pour info seulement
    garde = moy("nouveau") >= moy("ancien") + 0.05
    h = hashlib.sha256(open(os.path.join(nv_dir, "adapter_model.safetensors"), "rb").read()).hexdigest()
    json.dump(traces, open(os.path.join(nv_dir, "examen.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"[3 verdict] moyenne ancien {moy('ancien'):.0%} -> nouveau {moy('nouveau'):.0%} : "
          + ("NOUVEAU LOBE GARDE" if garde else "NOUVEAU LOBE NON CONCLUANT, on garde l'ancien"))
    if garde:
        idx[a.nouveau] = {"nom": a.nouveau, "base": base_nom, "rang": a.rang, "passes": a.passes, "exemples_appris": len(appris),
                          "moyenne_ancien": round(moy("ancien"), 3), "moyenne_nouveau": round(moy("nouveau"), 3),
                          "sha256": h, "date": time.strftime("%Y-%m-%d %H:%M"), "garde": True}
        json.dump(idx, open(idx_f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        t = f"lobe {a.nouveau} sha256={h} corpus={len(appris)} moyenne {moy('ancien'):.0%}->{moy('nouveau'):.0%} GARDE"
        r = subprocess.run(["python3", os.path.join(RACINE, "memoire", "memoire_chaine.py"), "ajouter", t], cwd=RACINE, capture_output=True, text=True)
        print("[sceau chaine]", (r.stdout or r.stderr).strip())

if a.etape in ("tout", "corpus"):
    if etape_corpus() == 0 and a.etape == "tout":
        print("Aucune paire fabriquee : on continue avec la graine seule.")
if a.etape in ("tout", "sommeil"): etape_sommeil_examen()

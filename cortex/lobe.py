#!/usr/bin/env python3
# Lobe QLoRA de l'ensemble de Rene : entraine un adaptateur sur un corpus, l'examine avant/apres,
# le range dans la bibliotheque de lobes et scelle son hash dans la chaine de Rene.
import argparse, glob, hashlib, json, os, random, re, subprocess, time
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(ICI)
p = argparse.ArgumentParser()
p.add_argument("--nom", default="continuite", help="nom du lobe (= nom du registre)")
p.add_argument("--corpus", default=os.path.join(RACINE, "sommeil", "corpus", "*.jsonl"))
p.add_argument("--modele", default="Qwen/Qwen2.5-3B-Instruct")
p.add_argument("--rang", type=int, default=8)
p.add_argument("--passes", type=int, default=5)
p.add_argument("--lr", type=float, default=2e-4)
p.add_argument("--examen", type=float, default=0.2, help="part du corpus gardee hors apprentissage")
p.add_argument("--sceller", type=int, default=1)
a = p.parse_args()

def lire(motif):
    ex = []
    for f in sorted(glob.glob(motif)):
        for ligne in open(f, encoding="utf-8"):
            ligne = ligne.strip()
            if not ligne:
                continue
            d = json.loads(ligne)
            if "messages" in d:
                u = [m["content"] for m in d["messages"] if m.get("role") == "user"]
                r = [m["content"] for m in d["messages"] if m.get("role") == "assistant"]
                if u and r:
                    ex.append((u[-1], r[-1]))
                continue
            for q, r in (("instruction", "output"), ("prompt", "completion"), ("question", "reponse"), ("input", "output")):
                if q in d and r in d:
                    ex.append((str(d[q]), str(d[r])))
                    break
    return ex

ex = lire(a.corpus)
if len(ex) < 5:
    raise SystemExit(f"CORPUS TROP MAIGRE : {len(ex)} exemples trouves dans {a.corpus}")
random.Random(0).shuffle(ex)
n_ex = max(1, int(len(ex) * a.examen))
examen, appris = ex[:n_ex], ex[n_ex:]
rappel = appris[:15]
rappel_ref = [("Rappelle-moi precisement : " + q[0].lower() + q[1:], r) for q, r in rappel]
print(f"corpus {len(ex)} exemples : {len(appris)} appris, {len(examen)} jamais vus, {len(rappel)} appris interroges en reformulation")

tok = AutoTokenizer.from_pretrained(a.modele)
q4 = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                        bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
mod = AutoModelForCausalLM.from_pretrained(a.modele, quantization_config=q4, device_map={"": 0}, dtype=torch.bfloat16)
mod = prepare_model_for_kbit_training(mod, use_gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False})
cfg = LoraConfig(r=a.rang, lora_alpha=2 * a.rang, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
                 target_modules=["q_proj", "k_proj", "v_proj", "o_proj"])
mod = get_peft_model(mod, cfg)
mod.print_trainable_parameters()

def invite(q):
    return tok.apply_chat_template([{"role": "user", "content": q}], add_generation_prompt=True, tokenize=False)

def mots(t):
    return {m for m in re.findall(r"\w+", t.lower()) if len(m) > 3}

def interroger(liste):
    mod.eval(); score = 0.0; traces = []
    for q, r in liste:
        e = tok(invite(q), return_tensors="pt").to(0)
        with torch.no_grad():
            s = mod.generate(**e, max_new_tokens=80, do_sample=False)
        rep = tok.decode(s[0][e["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        ref = mots(r); sc = len(ref & mots(rep)) / max(1, len(ref))
        score += sc; traces.append({"q": q, "attendu": r, "repondu": rep, "score": round(sc, 2)})
    return score / len(liste), traces

with mod.disable_adapter():
    avant, tr_avant = interroger(examen)
    m_avant, trm_avant = interroger(rappel_ref)
print(f"AVANT sommeil (modele nu) : memoire {m_avant:.0%} | jamais vus {avant:.0%}")

def encoder(q, r):
    pi = tok(invite(q), add_special_tokens=False)["input_ids"]
    ri = tok(r + tok.eos_token, add_special_tokens=False)["input_ids"]
    ids = (pi + ri)[:512]; lab = ([-100] * len(pi) + ri)[:512]
    return torch.tensor([ids]).to(0), torch.tensor([lab]).to(0)

opt = torch.optim.AdamW([p_ for p_ in mod.parameters() if p_.requires_grad], lr=a.lr)
mod.train(); t0 = time.time()
for passe in range(a.passes):
    random.Random(passe).shuffle(appris); tot = 0.0
    for q, r in appris:
        ids, lab = encoder(q, r)
        perte = mod(input_ids=ids, labels=lab).loss
        perte.backward(); opt.step(); opt.zero_grad(); tot += perte.item()
    print(f"sommeil passe {passe + 1}/{a.passes} : perte moyenne {tot / len(appris):.3f}")
print(f"sommeil termine en {time.time() - t0:.0f} s")

apres, tr_apres = interroger(examen)
m_apres, trm_apres = interroger(rappel_ref)
garde = m_apres - m_avant >= 0.10
print(f"APRES sommeil (avec lobe) : memoire {m_apres:.0%} | jamais vus {apres:.0%}")
print("VERDICT :", "LOBE GARDE (memoire +%d points)" % round(100*(m_apres-m_avant)) if garde else "LOBE NON CONCLUANT (moins de +10 points de memoire)")

dossier = os.path.join(ICI, "lobes", a.nom)
os.makedirs(dossier, exist_ok=True)
mod.save_pretrained(dossier)
poids = os.path.join(dossier, "adapter_model.safetensors")
h = hashlib.sha256(open(poids, "rb").read()).hexdigest()
fiche = {"nom": a.nom, "base": a.modele, "rang": a.rang, "passes": a.passes, "exemples_appris": len(appris),
         "exemples_examen": len(examen), "examen_avant": round(avant, 3), "examen_apres": round(apres, 3),
         "memoire_avant": round(m_avant, 3), "memoire_apres": round(m_apres, 3), "garde": garde,
         "sha256": h, "date": time.strftime("%Y-%m-%d %H:%M")}
json.dump({"fiche": fiche, "avant": tr_avant, "apres": tr_apres, "memoire_avant": trm_avant, "memoire_apres": trm_apres},
          open(os.path.join(dossier, "examen.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
idx_f = os.path.join(ICI, "lobes", "INDEX.json")
idx = json.load(open(idx_f, encoding="utf-8")) if os.path.exists(idx_f) else {}
idx[a.nom] = fiche
json.dump(idx, open(idx_f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"lobe range : {dossier} | sha256 {h[:16]}…")
if a.sceller:
    texte = f"lobe {a.nom} base={a.modele} rang={a.rang} passes={a.passes} sha256={h} memoire {m_avant:.0%}->{m_apres:.0%} jamais-vus {avant:.0%}->{apres:.0%} {'GARDE' if garde else 'NON CONCLUANT'}"
    r = subprocess.run(["python3", os.path.join(RACINE, "memoire", "memoire_chaine.py"), "ajouter", texte],
                       cwd=RACINE, capture_output=True, text=True)
    print("sceau chaine :", (r.stdout or r.stderr).strip())

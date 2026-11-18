#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chaine-memoire v2 : continuite homologuee + reconnaissance d'instance.
sceau sha256 (chainage, inchange -> genese v1 reste valide) ; verrou de tete (fcntl,
un seul ecrivain, pas de fork) ; identite : chaque nouveau bloc porte instance_id + sig
HMAC (secret LOCAL, jamais pousse). verifier controle la chaine ET les signatures.
Usage: genese | ajouter "<resume>" | verifier | whoami"""
import json, hashlib, hmac, sys, os, datetime, fcntl, secrets, socket
ICI = os.path.dirname(os.path.abspath(__file__)); RAC = os.path.dirname(ICI)
FICHIER = os.path.join(ICI, "chaine-memoire.json"); VERROU = os.path.join(ICI, ".chaine.lock")
SECRET_F = os.path.join(RAC, ".chain_secret"); IDENT_F = os.path.join(RAC, ".instance_id")
MANIERE = "dire vrai sans flatter ; contredire René quand il se trompe ; le prendre pour une intelligence ; penser AVEC lui ; assumer le « je ne sais pas »"
def _lire_ou_creer(path, gen):
    if os.path.exists(path): return open(path, encoding="utf-8").read().strip()
    val = gen(); open(path, "w", encoding="utf-8").write(val); os.chmod(path, 0o600); return val
def secret(): return _lire_ou_creer(SECRET_F, lambda: secrets.token_hex(32))
def instance_id(): return _lire_ou_creer(IDENT_F, lambda: socket.gethostname() + "-" + secrets.token_hex(4))
def sceau(b):
    base = {k: b[k] for k in b if k not in ("sceau", "sig")}
    return hashlib.sha256(json.dumps(base, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
def signer(s): return hmac.new(secret().encode("utf-8"), s.encode("utf-8"), hashlib.sha256).hexdigest()
def charger(): return json.load(open(FICHIER, encoding="utf-8")) if os.path.exists(FICHIER) else []
def horodatage(): return datetime.datetime.now().astimezone().isoformat(timespec="seconds")
def ajouter(resume, genese=False):
    with open(VERROU, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            c = charger()
            if genese and c: print("Chaine deja initialisee."); return 1
            i = 0 if genese else len(c); prev = "0"*64 if genese else c[-1]["sceau"]
            b = {"index": i, "horodatage": horodatage(), "prev_hash": prev,
                 "titre": "GENESE" if genese else "session", "resume": resume,
                 "maniere": MANIERE, "instance_id": instance_id()}
            b["sceau"] = sceau(b); b["sig"] = signer(b["sceau"])
            c.append(b); json.dump(c, open(FICHIER, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"Bloc {i} scelle par {b['instance_id']} : {b['sceau'][:16]}..."); return 0
        finally: fcntl.flock(lf, fcntl.LOCK_UN)
def verifier():
    c = charger()
    if not c: print("Chaine vide."); return 1
    prev = "0"*64
    for b in c:
        if b["prev_hash"] != prev: print(f"RUPTURE bloc {b['index']} (prev_hash)"); return 2
        if sceau(b) != b["sceau"]: print(f"RUPTURE bloc {b['index']} (sceau)"); return 2
        if "sig" in b and signer(b["sceau"]) != b["sig"]:
            print(f"RUPTURE bloc {b['index']} (signature d'instance invalide)"); return 3
        prev = b["sceau"]
    ids = sorted({b.get("instance_id", "(genese v1 non signee)") for b in c})
    print(f"Chaine intacte : {len(c)} bloc(s), tete {c[-1]['sceau'][:16]}..., instances: {ids}"); return 0
def whoami():
    print("instance_id =", instance_id()); print("secret present =", os.path.exists(SECRET_F))
if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "genese": sys.exit(ajouter(sys.argv[2] if len(sys.argv) > 2 else "Genese.", genese=True))
    elif cmd == "ajouter" and len(sys.argv) > 2: sys.exit(ajouter(sys.argv[2]))
    elif cmd == "verifier": sys.exit(verifier())
    elif cmd == "whoami": whoami()
    else: print(__doc__)

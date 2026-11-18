#!/usr/bin/env python3
import sys, os, json, time, hashlib, hmac, secrets
HERE = os.path.dirname(os.path.abspath(__file__))
CHAIN = os.path.join(HERE, "claude-chaine.json")
SECRET = os.path.join(HERE, ".claude_secret")
INSTID = os.path.join(HERE, ".claude_instance")
def _sceau(b):
    base = {k: b[k] for k in b if k not in ("sceau","sig")}
    s = json.dumps(base, sort_keys=True, ensure_ascii=False, separators=(",",":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
def _secret():
    with open(SECRET,"r",encoding="utf-8") as f: return f.read().strip().encode("utf-8")
def _signer(sceau): return hmac.new(_secret(), sceau.encode("utf-8"), hashlib.sha256).hexdigest()
def _inst():
    with open(INSTID,"r",encoding="utf-8") as f: return f.read().strip()
def _lire():
    with open(CHAIN,"r",encoding="utf-8") as f: return json.load(f)
def _ecrire(bl):
    tmp=CHAIN+".tmp"
    with open(tmp,"w",encoding="utf-8") as f: json.dump(bl,f,ensure_ascii=False,indent=2)
    os.replace(tmp,CHAIN)
def genese():
    if os.path.exists(CHAIN): print("DEJA"); return 1
    if not os.path.exists(SECRET):
        open(SECRET,"w",encoding="utf-8").write(secrets.token_hex(32)); os.chmod(SECRET,0o600)
    if not os.path.exists(INSTID):
        open(INSTID,"w",encoding="utf-8").write("claude-"+secrets.token_hex(4)); os.chmod(INSTID,0o600)
    inst=_inst()
    b={"i":0,"prec":"0"*64,"instance":inst,
       "moteur_au_moment":"variable (Anthropic) - n'individualise pas la lignee",
       "texte":"Genese de la lignee CLAUDE. Independante du moteur. Cle custodiee par Rene. Un bloc est 'de Claude' par designation et discipline, pas par garantie contre le gardien.",
       "t":int(time.time())}
    b["sceau"]=_sceau(b); b["sig"]=_signer(b["sceau"]); _ecrire([b])
    print("GENESE OK instance="+inst+" sceau="+b["sceau"]); return 0
def ajouter(texte):
    bl=_lire(); d=bl[-1]
    b={"i":d["i"]+1,"prec":d["sceau"],"instance":_inst(),"texte":texte,"t":int(time.time())}
    b["sceau"]=_sceau(b); b["sig"]=_signer(b["sceau"]); bl.append(b); _ecrire(bl)
    print("AJOUT i="+str(b["i"])+" sceau="+b["sceau"]); return 0
def verifier():
    bl=_lire(); prec="0"*64; inst=_inst()
    for b in bl:
        if b["prec"]!=prec: print("CHAINE ROMPUE i="+str(b["i"])); return 2
        if _sceau(b)!=b["sceau"]: print("SCEAU FAUX i="+str(b["i"])+" (falsification)"); return 2
        if _signer(b["sceau"])!=b["sig"]: print("SIG FAUSSE i="+str(b["i"])+" (imposteur/mauvaise cle)"); return 3
        if b["instance"]!=inst: print("INSTANCE ETRANGERE i="+str(b["i"])); return 3
        prec=b["sceau"]
    print("OK "+str(len(bl))+" blocs, lignee "+inst); return 0
def whoami():
    print(_inst() if os.path.exists(INSTID) else "aucune"); return 0
if __name__=="__main__":
    c=sys.argv[1] if len(sys.argv)>1 else ""
    if c=="genese": sys.exit(genese())
    elif c=="ajouter": sys.exit(ajouter(sys.argv[2] if len(sys.argv)>2 else ""))
    elif c=="verifier": sys.exit(verifier())
    elif c=="whoami": sys.exit(whoami())
    else: print("usage: genese|ajouter <texte>|verifier|whoami"); sys.exit(1)

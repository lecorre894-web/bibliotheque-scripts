#!/usr/bin/env python3
# rtv — télécommande René TV pour Termux (logos via chafa). Usage : rtv
import json, os, re, shutil, subprocess, sys, urllib.parse, urllib.request, hashlib
from concurrent.futures import ThreadPoolExecutor

D = os.path.expanduser('~/.rtv'); os.makedirs(os.path.join(D, 'logos'), exist_ok=True)
CONF = os.path.join(D, 'conf.json')
R, V, G, J, B, Z = '\033[31m', '\033[32m', '\033[90m', '\033[33m', '\033[1m', '\033[0m'

def conf():
    try:
        return json.load(open(CONF))
    except Exception:
        pass
    print(B + '📺 Première connexion' + Z)
    print("Recopie l'adresse affichée dans René TV (Son & image → 📱 Télécommande),")
    print('par exemple http://10.42.0.5:8765/?k=1234')
    while True:
        s = input('Adresse : ').strip()
        m = re.match(r'(?:https?://)?([\d.]+)(?::(\d+))?/?\?k=(\d+)', s)
        if m:
            c = {'ip': m.group(1), 'port': int(m.group(2) or 8765), 'k': m.group(3)}
            json.dump(c, open(CONF, 'w')); return c
        print(R + 'Adresse non reconnue, recommence.' + Z)

C = conf()
BASE = 'http://%s:%d' % (C['ip'], C['port'])

def req(path, **q):
    q['k'] = C['k']
    try:
        with urllib.request.urlopen(BASE + path + '?' + urllib.parse.urlencode(q), timeout=6) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception as e:
        return {'err': 'René TV injoignable (%s)' % e.__class__.__name__}

def cmd(c):
    return req('/c', c=c)

LISTE = []
def liste():
    global LISTE
    if not LISTE:
        print(G + 'Chargement de la liste…' + Z)
        r = req('/liste')
        LISTE = r if isinstance(r, list) else []
    return LISTE

CHAFA = shutil.which('chafa')
ANSI = re.compile(r'\x1b\[[0-9;?]*[A-Za-z]')
def lfichier(url):
    f = os.path.join(D, 'logos', hashlib.md5(url.encode()).hexdigest())
    if not os.path.exists(f):
        try:
            rq = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(rq, timeout=5) as r:
                open(f, 'wb').write(r.read(400000))
        except Exception:
            open(f, 'wb').close()
    return f

def mini(url, w, h):
    if not CHAFA or not url:
        return [' ' * w] * h
    f = lfichier(url)
    if os.path.getsize(f) == 0:
        return [' ' * w] * h
    try:
        o = subprocess.run([CHAFA, '--size', '%dx%d' % (w, h), '--format', 'symbols', '--animate', 'off', f], capture_output=True, text=True, timeout=5)
        L = [re.sub(r'\x1b\[\?25[lh]', '', l) for l in o.stdout.split('\n')] if o.returncode == 0 else []
        L = [l for l in L if ANSI.sub('', l).strip() or '\x1b[' in l][:h]
    except Exception:
        L = []
    L = [l + Z + ' ' * max(0, w - len(ANSI.sub('', l))) for l in L]
    while len(L) < h:
        L.append(' ' * w)
    return L

def grille(items, titre):
    cols = max(1, (shutil.get_terminal_size((48, 20)).columns) // 17)
    print('\n' + B + titre + G + '  (%d) — Ctrl-C pour arrêter' % len(items) + Z)
    try:
        with ThreadPoolExecutor(16) as ex:
            for i in range(0, len(items), cols * 6):
                bloc = items[i:i + cols * 6]
                imgs = list(ex.map(lambda x: mini(x.get('logo', ''), 14, 4), bloc))
                for j in range(0, len(bloc), cols):
                    rang, ri = bloc[j:j + cols], imgs[j:j + cols]
                    for k in range(4):
                        print('  '.join(im[k] for im in ri))
                    print('  '.join((J + '%4s' % x['n'] + Z + ' ' + x['nom'][:9].ljust(9)) for x in rang))
                    print()
    except KeyboardInterrupt:
        print(G + '\n(arrêté)' + Z)

def logo(url):
    if not CHAFA or not url:
        return []
    f = os.path.join(D, 'logos', hashlib.md5(url.encode()).hexdigest())
    if not os.path.exists(f):
        try:
            rq = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(rq, timeout=5) as r:
                open(f, 'wb').write(r.read(400000))
        except Exception:
            open(f, 'wb').close()
    if os.path.getsize(f) == 0:
        return []
    try:
        o = subprocess.run([CHAFA, '--size', '12x4', '--format', 'symbols', '--animate', 'off', f], capture_output=True, text=True, timeout=5)
        return o.stdout.rstrip('\n').split('\n') if o.returncode == 0 else []
    except Exception:
        return []

def affiche(items, titre):
    i = 0
    while i < len(items):
        print('\n' + B + titre + G + '  (%d-%d / %d)' % (i + 1, min(i + 8, len(items)), len(items)) + Z)
        for x in items[i:i + 8]:
            lg = logo(x.get('logo', ''))
            nom = '%s%4s%s  %s' % (J, x['n'], Z, x['nom'])
            if lg:
                for k, l in enumerate(lg):
                    print(l + ('  ' + nom if k == len(lg) // 2 else ''))
            else:
                print(' ' * 13 + nom)
        s = input(G + '[Entrée] suite · numéro = regarder · q = retour : ' + Z).strip()
        if s.isdigit():
            return s
        if s == 'q':
            return None
        i += 8
    return None

def etat(s):
    if not isinstance(s, dict) or s.get('err'):
        print(R + '⚠ ' + (s.get('err') if isinstance(s, dict) else 'erreur') + Z); return
    print('%s📺 %s%s  %s🔊 %s%%  · fluidité %s · ffmpeg %s%s' % (B, s.get('ch') or 'Accueil', Z, G, s.get('vol'), s.get('flu'), s.get('ff'), Z))

AIDE = (G + 'numéro = chaîne · u/d = ch+/ch- · +/- = volume · m = muet · p = pause · b = précédente · x = retour\n'
        'a = TOUT en mosaïque (T = TV, R = radios) · t = liste TV · r = radios · /mot = chercher · f = plein écran · ia/max/8k/fort/0 = traitement · s30 = sommeil · q = quitter' + Z)

def main():
    print(B + R + '📺 René TV' + Z + B + ' — télécommande Termux' + Z + ('' if CHAFA else G + '  (pkg install chafa pour les logos)' + Z))
    print(AIDE); etat(cmd('etat'))
    M = {'u': 'up', 'd': 'down', '+': 'volp', '-': 'volm', 'm': 'mute', 'p': 'pause', 'b': 'prec', 'x': 'retour', 'f': 'plein',
         'ia': 'ff:ia', 'max': 'ff:max', '8k': 'ff:s8k', 'fort': 'ff:fort', 'doux': 'ff:doux', '0': 'ff:0'}
    while True:
        try:
            s = input(V + '▶ ' + Z).strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not s:
            etat(cmd('etat')); continue
        if s == 'q':
            break
        if s in ('?', 'h', 'aide'):
            print(AIDE); continue
        if s in ('++', '--'):
            for _ in range(3): r = cmd('volp' if s == '++' else 'volm')
            etat(r); continue
        if s.isdigit() and s != '0':
            etat(cmd('ch:' + s)); continue
        if s in M:
            etat(cmd(M[s])); continue
        if re.fullmatch(r's\d+', s):
            etat(cmd('dodo:' + s[1:])); continue
        if s in ('a', 'tout', 'T', 'R'):
            L = liste()
            if not L: print(R + 'Liste vide : René TV est-il ouvert avec ses chaînes chargées ?' + Z); continue
            if s in ('a', 'tout', 'T'): grille([x for x in L if x.get('t') == 'tv'], 'TOUTES LES CHAÎNES TV')
            if s in ('a', 'tout', 'R'): grille([x for x in L if x.get('t') != 'tv'], 'TOUTES LES RADIOS')
            print(G + 'Tape un numéro pour regarder.' + Z)
            continue
        if s in ('t', 'r'):
            L = [x for x in liste() if (x.get('t') == 'tv') == (s == 't')]
            if not L: print(R + 'Liste vide : René TV est-il ouvert avec ses chaînes chargées ?' + Z); continue
            n = affiche(L, 'CHAÎNES TV' if s == 't' else 'RADIOS')
            if n: etat(cmd('ch:' + n))
            continue
        if s.startswith('/') and len(s) > 1:
            m = s[1:].lower()
            L = [x for x in liste() if m in x.get('nom', '').lower()]
            if not L: print(R + 'Rien trouvé.' + Z); continue
            n = affiche(L, 'RECHERCHE « %s »' % s[1:])
            if n: etat(cmd('ch:' + n))
            continue
        if s == 'reset':
            os.remove(CONF); print('Adresse oubliée : relance rtv.'); break
        print(R + 'Commande inconnue — tape ? pour l’aide.' + Z)

if __name__ == '__main__':
    main()

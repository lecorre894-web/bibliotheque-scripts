# René TV v3.4 : une chaîne TV en direct affiche DIRECT (plus « 1 min » de fenêtre HLS)
import sys,os,hashlib
p=os.path.join(os.path.expanduser(sys.argv[1] if len(sys.argv)>1 else '~/rene-tv'),'index.html');s=open(p,encoding='utf-8').read()
a="dur=isFinite(v.duration)?Math.round(v.duration/60)+' min':'DIRECT';"
b="dur=(cur.t==='tv'||(hls&&hls.levels.some(l=>l.details&&l.details.live))||!isFinite(v.duration))?'DIRECT'/*v3.4*/:(v.duration>=3600?Math.floor(v.duration/3600)+' h '+String(Math.floor(v.duration%3600/60)).padStart(2,'0'):Math.max(1,Math.round(v.duration/60))+' min');"
if '/*v3.4*/' in s:print('deja en v3.4',hashlib.sha256(s.encode()).hexdigest()[:16]);sys.exit()
if s.count(a)!=1:print('ECHEC motif introuvable');sys.exit(1)
s=s.replace(a,b);open(p,'w',encoding='utf-8').write(s);print('OK index.html',hashlib.sha256(s.encode()).hexdigest()[:16])

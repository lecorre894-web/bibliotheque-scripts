import sys,os,json,hashlib
d=sys.argv[1];R=json.loads('[["main.js", "    r.statusCode = 404; r.end();", "    if (u.pathname === \'/liste\') { /*v4.9.1*/ r.setHeader(\'Content-Type\', \'application/json; charset=utf-8\'); if (!ok) { r.statusCode = 403; return r.end(\'[]\'); } const w = tWin(); if (!w) return r.end(\'[]\'); return w.webContents.executeJavaScript(\\"JSON.stringify([...listeTV(),...listeRadio()].map(x=>({n:x.num,t:x.t,nom:x.n,logo:x.logo||\'\'})))\\").then(s => r.end(s)).catch(() => r.end(\'[]\')); }\\n    r.statusCode = 404; r.end();"], ["index.html", "else if(a===\'dodo\')dodo(+b);", "else if(a===\'dodo\')dodo(+b);else if(a===\'ch\'){const x=parNum(+b);if(x)joue(x)}"]]')
src={f:open(os.path.join(d,f),encoding='utf-8').read() for f in ('main.js','index.html')}
if '/*v4.9.1*/' in src['main.js']:print('déjà v4.9.1');sys.exit(0)
if '/*v4.9-tele*/' not in src['main.js']:print('ERREUR : il faut la v4.9');sys.exit(1)
for f,a,b in R:
  if src[f].count(a)!=1:print('ERREUR motif',f,a[:50]);sys.exit(1)
  src[f]=src[f].replace(a,b)
for f,t in src.items():open(os.path.join(d,f),'w',encoding='utf-8').write(t);print('OK',f,hashlib.sha256(t.encode()).hexdigest()[:16])

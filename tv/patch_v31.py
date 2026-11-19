import sys,hashlib
p=sys.argv[1];s=open(p,encoding='utf-8').read()
R=[("const TV_DEF='https://iptv-org.github.io/iptv/countries/fr.m3u';",
"const TV_DEF='https://iptv-org.github.io/iptv/countries/fr.m3u https://iptv-org.github.io/iptv/languages/fra.m3u';"),
("async function chargeTV(){try{const r=await fetch(ls('tvurl',TV_DEF));tv=parseM3U(await r.text());dire(tv.length+' chaînes TV.')}catch(e){tv=[];dire('Liste TV injoignable (connexion ?).')}numerote();rendTout()}",
"async function chargeTV(){let s=ls('tvurl',TV_DEF);if(s==='https://iptv-org.github.io/iptv/countries/fr.m3u')s=TV_DEF;const L=String(s).split(/[\\s,]+/).filter(u=>/^https?:\\/\\//.test(u));const vus=new Set();let ok=0;tv=[];\n for(const u of L){try{const r=await fetch(u);const t=parseM3U(await r.text());ok++;for(const x of t)if(!vus.has(x.u)){vus.add(x.u);tv.push(x)}}catch(e){}}\n dire(ok?tv.length+' chaînes TV ('+ok+'/'+L.length+' listes).':'Listes TV injoignables (connexion ?).');numerote();rendTout()}"),
('<h2>Liste des chaînes TV</h2><div class="carte ligne"><input id="tvurl" size="56">',
 '<h2>Listes des chaînes TV <small>une adresse .m3u par ligne</small></h2><div class="carte ligne"><textarea id="tvurl" rows="5" cols="72"></textarea>'),
("if(e.target.tagName==='INPUT'||e.target.tagName==='SELECT')return;",
 "if(/^(INPUT|SELECT|TEXTAREA)$/.test(e.target.tagName))return;"),
("$('#tvurl').value=ls('tvurl',TV_DEF);$('#cNom')","$('#tvurl').value=String(ls('tvurl',TV_DEF)).split(/[\\s,]+/).join('\\n');$('#cNom')")]
for a,b in R:
    if s.count(a)!=1: print('ECHEC motif introuvable :',a[:60]); sys.exit(1)
    s=s.replace(a,b)
open(p,'w',encoding='utf-8').write(s);print('PATCH OK',hashlib.sha256(s.encode()).hexdigest()[:16])

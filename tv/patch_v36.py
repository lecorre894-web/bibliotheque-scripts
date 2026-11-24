# René TV v3.6 : grain plus fort + curseur d'intensité, filtre « Éclat » (contraste et couleurs légèrement relevés, appliqué après la vidéo)
import sys,os,hashlib
p=os.path.join(os.path.expanduser(sys.argv[1] if len(sys.argv)>1 else '~/rene-tv'),'index.html');s=open(p,encoding='utf-8').read()
if '/*v3.6*/' in s:print('deja en v3.6',hashlib.sha256(s.encode()).hexdigest()[:16]);sys.exit()
if '/*v3.5*/' not in s:print('ECHEC : installe d abord la v3.5');sys.exit(1)
R=[("const GRAIN={cinema:{a:.10,px:2,fps:24},photo:{a:.07,px:1,fps:8},jeux:{a:.055,px:1,fps:60}};",
"const GRAIN={cinema:{a:.16,px:2,fps:24},photo:{a:.11,px:1,fps:8},jeux:{a:.08,px:1,fps:60}};/*v3.6*/let gInt=ls('grainInt',100);"),
("gl.uniform1f(gU.a,m.a);","gl.uniform1f(gU.a,Math.min(.45,m.a*gInt/100));"),
('<option value="jeux">Jeux (anti-banding)</option></select></label>\n','<option value="jeux">Jeux (anti-banding)</option></select></label>\n  <label>Intensité grain <input type="range" id="iGInt" min="50" max="300" value="100"><span id="iGIntV">100%</span></label>\n  <label>Éclat (contraste + couleurs) <input type="checkbox" id="iEclat"></label>\n'),
("v.style.filter=`brightness(${img.lum}%) contrast(${img.con}%) saturate(${img.sat}%)`","v.style.filter=`brightness(${img.lum}%) contrast(${img.con}%) saturate(${img.sat}%)`+(img.eclat!==false?' brightness(102%) contrast(104%) saturate(115%)':'')"),
("$('#iGrain').value=gMode;","$('#iGInt').value=gInt;$('#iGIntV').textContent=gInt+'%';$('#iGInt').oninput=e=>{gInt=+e.target.value;$('#iGIntV').textContent=gInt+'%';ss('grainInt',gInt)};\n$('#iEclat').checked=img.eclat!==false;$('#iEclat').onchange=e=>{img.eclat=e.target.checked;appliqueImg()};appliqueImg();\n$('#iGrain').value=gMode;")]
for a,b in R:
    if s.count(a)!=1:print('ECHEC motif introuvable :',a[:50]);sys.exit(1)
    s=s.replace(a,b)
open(p,'w',encoding='utf-8').write(s);print('OK index.html',hashlib.sha256(s.encode()).hexdigest()[:16])

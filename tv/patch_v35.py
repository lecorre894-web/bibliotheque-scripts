# René TV v3.5 : grain numérique par-dessus l'image (Cinéma / Photo / Jeux anti-banding), vidéo intacte pour la RTX
import sys,os,hashlib
p=os.path.join(os.path.expanduser(sys.argv[1] if len(sys.argv)>1 else '~/rene-tv'),'index.html');s=open(p,encoding='utf-8').read()
if '/*v3.5*/' in s:print('deja en v3.5',hashlib.sha256(s.encode()).hexdigest()[:16]);sys.exit()
R=[('#v{width:100%;height:100%;object-fit:contain;transform-origin:center}',
'#v{width:100%;height:100%;object-fit:contain;transform-origin:center}\n#grain{position:absolute;left:0;top:0;width:100%;height:100%;pointer-events:none;mix-blend-mode:overlay;display:none}/*v3.5*/'),
(' <video id="v" autoplay></video>\n',' <video id="v" autoplay></video>\n <canvas id="grain"></canvas>\n'),
('  <label>Qualité flux <select id="iQual">','  <label>Grain <select id="iGrain"><option value="0">Aucun</option><option value="cinema">Cinéma</option><option value="photo">Photo</option><option value="jeux">Jeux (anti-banding)</option></select></label>\n  <label>Qualité flux <select id="iQual">'),
("$('#iQual').onchange=e=>{if(hls)hls.currentLevel=+e.target.value};","""$('#iQual').onchange=e=>{if(hls)hls.currentLevel=+e.target.value};
/* ===== v3.5 GRAIN : bruit généré par la carte graphique, posé en mode « overlay » (noirs OLED intacts, vidéo non touchée) ===== */
const GRAIN={cinema:{a:.10,px:2,fps:24},photo:{a:.07,px:1,fps:8},jeux:{a:.055,px:1,fps:60}};
let gMode=ls('grain','0'),gl=null,gU=null,gDer=0,gImg=0,gSec=performance.now();
function grainGL(){const c=$('#grain');gl=c.getContext('webgl',{antialias:false,depth:false,preserveDrawingBuffer:false});if(!gl)return false;
 const sh=(t,src)=>{const o=gl.createShader(t);gl.shaderSource(o,src);gl.compileShader(o);return o},pr=gl.createProgram();
 gl.attachShader(pr,sh(gl.VERTEX_SHADER,'attribute vec2 p;void main(){gl_Position=vec4(p,0.,1.);}'));
 gl.attachShader(pr,sh(gl.FRAGMENT_SHADER,'precision highp float;uniform float t,a,px;float h(vec2 q){q=fract(q*vec2(.1031,.1030)+t);q+=dot(q,q.yx+33.33);return fract((q.x+q.y)*q.x);}void main(){vec2 c=floor(gl_FragCoord.xy/px);float n=h(c)+h(c+71.7)-1.;gl_FragColor=vec4(vec3(.5+n*a),1.);}'));
 gl.linkProgram(pr);gl.useProgram(pr);const b=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,b);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([-1,-1,3,-1,-1,3]),gl.STATIC_DRAW);
 const l=gl.getAttribLocation(pr,'p');gl.enableVertexAttribArray(l);gl.vertexAttribPointer(l,2,gl.FLOAT,false,0,0);gU={t:gl.getUniformLocation(pr,'t'),a:gl.getUniformLocation(pr,'a'),px:gl.getUniformLocation(pr,'px')};return true}
function grainBoucle(now){const c=$('#grain'),m=GRAIN[gMode],vis=m&&$('#lecteur').classList.contains('on')&&!(cur&&cur.t==='radio');
 c.style.display=vis?'block':'none';
 if(vis&&(gl||grainGL())&&now-gDer>=1000/m.fps-2){gDer=now;const W=Math.round(c.clientWidth*devicePixelRatio),H=Math.round(c.clientHeight*devicePixelRatio);
  if(c.width!==W||c.height!==H){c.width=W;c.height=H;gl.viewport(0,0,W,H)}
  gl.uniform1f(gU.t,(now%10000)/97.13);gl.uniform1f(gU.a,m.a);gl.uniform1f(gU.px,m.px*Math.max(1,devicePixelRatio/1.5));gl.drawArrays(gl.TRIANGLES,0,3);gImg++}
 if(now-gSec>=1000){window.grainIPS=gImg;gImg=0;gSec=now}requestAnimationFrame(grainBoucle)}
$('#iGrain').value=gMode;$('#iGrain').onchange=e=>{gMode=e.target.value;ss('grain',gMode)};requestAnimationFrame(grainBoucle);""")]
for a,b in R:
    if s.count(a)!=1:print('ECHEC motif introuvable :',a[:50]);sys.exit(1)
    s=s.replace(a,b)
open(p,'w',encoding='utf-8').write(s);print('OK index.html',hashlib.sha256(s.encode()).hexdigest()[:16])

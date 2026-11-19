set -e
D=~/rene-tv; mkdir -p "$D"; cd "$D"
cat > package.json <<'EOF_F0'
{"name":"rene-tv","version":"3.0.0","main":"main.js","private":true}
EOF_F0
cat > main.js <<'EOF_F1'
const { app, BrowserWindow, ipcMain, shell, powerSaveBlocker } = require('electron');
const path = require('path'), fs = require('fs'), http = require('http'), https = require('https');
app.commandLine.appendSwitch('ignore-gpu-blocklist');
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('enable-zero-copy');
let w;
app.whenReady().then(() => {
  w = new BrowserWindow({ width: 1500, height: 900, title: 'René TV', autoHideMenuBar: true, backgroundColor: '#0d0f14',
    webPreferences: { webSecurity: false, preload: path.join(__dirname, 'preload.js') } });
  w.loadFile('index.html');
});
app.on('window-all-closed', () => app.quit());
ipcMain.handle('qwen', async (_e, { url, model, messages }) => {
  try {
    const r = await fetch(url + '/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model, messages, stream: false, format: 'json', options: { temperature: 0.3 } }), signal: AbortSignal.timeout(60000) });
    if (!r.ok) return { err: 'HTTP ' + r.status };
    const j = await r.json(); return { txt: j.message && j.message.content };
  } catch (e) { return { err: String(e.message || e) }; }
});
ipcMain.handle('icy', (_e, url) => new Promise(res => {
  let done = false, req; const fin = v => { if (!done) { done = true; res(v); try { req.destroy(); } catch (e) {} } };
  try {
    const lib = url.startsWith('https') ? https : http;
    req = lib.get(url, { headers: { 'Icy-MetaData': '1', 'User-Agent': 'ReneTV' } }, r => {
      const mi = parseInt(r.headers['icy-metaint'] || '0', 10); if (!mi) return fin(null);
      let buf = Buffer.alloc(0);
      r.on('data', c => { buf = Buffer.concat([buf, c]);
        if (buf.length > mi) { const L = buf[mi] * 16; if (L === 0) return fin(null);
          if (buf.length >= mi + 1 + L) { const m = buf.slice(mi + 1, mi + 1 + L).toString('utf8'); fin((m.match(/StreamTitle='([^']*)'/) || [])[1] || null); } } });
    });
    req.on('error', () => fin(null));
  } catch (e) { fin(null); }
  setTimeout(() => fin(null), 8000);
}));
ipcMain.handle('gpu', () => app.getGPUFeatureStatus());
// ---------- MAGNÉTOSCOPE : la bande est écrite sur disque au fil de l'eau (aucune limite de durée en mémoire) ----------
const K7 = path.join(app.getPath('videos'), 'Rene-K7');
let veille = null;
const nomSur = s => String(s).replace(/[\\/:*?"<>|]+/g, '-').replace(/\s+/g, '_').slice(0, 60);
ipcMain.handle('k7-liste', () => { try { return fs.readdirSync(K7).filter(f => /\.(ts|webm|mkv|mp4)$/i.test(f)).map(f => { const st = fs.statSync(path.join(K7, f)); return { n: f, f: path.join(K7, f), taille: st.size, date: st.mtimeMs }; }).sort((a, b) => b.date - a.date); } catch (e) { return []; } });
ipcMain.handle('k7-dossier', () => { fs.mkdirSync(K7, { recursive: true }); return shell.openPath(K7); });
ipcMain.handle('k7-effacer', (_e, f) => { try { if (path.dirname(f) === K7) fs.unlinkSync(f); return true; } catch (e) { return false; } });
// ---------- LOGICIELS GRATUITS PILOTÉS : VLC (moteur d'enregistrement), FreeTube, Kodi ----------
const { spawn } = require('child_process');
const env = process.env, PF = env['ProgramFiles'] || 'C:\\Program Files', PF86 = env['ProgramFiles(x86)'] || 'C:\\Program Files (x86)', LAD = env['LOCALAPPDATA'] || '';
const trouveExe = l => l.find(p => { try { return fs.existsSync(p); } catch (e) { return false; } }) || null;
const EXE = {
  vlc: () => trouveExe([path.join(PF, 'VideoLAN', 'VLC', 'vlc.exe'), path.join(PF86, 'VideoLAN', 'VLC', 'vlc.exe')]),
  freetube: () => trouveExe([path.join(LAD, 'Programs', 'FreeTube', 'FreeTube.exe'), path.join(PF, 'FreeTube', 'FreeTube.exe')]),
  kodi: () => trouveExe([path.join(PF, 'Kodi', 'kodi.exe'), path.join(PF86, 'Kodi', 'kodi.exe')])
};
ipcMain.handle('logiciels', () => ({ vlc: !!EXE.vlc(), freetube: !!EXE.freetube(), kodi: !!EXE.kodi() }));
ipcMain.handle('lancer', (_e, qui, arg) => { const x = EXE[qui] && EXE[qui](); if (!x) return false;
  spawn(x, arg ? [arg] : [], { detached: true, stdio: 'ignore' }).unref(); return true; });
// Magnétoscope : un VLC invisible par cassette, qui écrit le flux brut sur disque (.ts), sans limite de durée
const magneto = new Map();
const majVeille = () => { const g = magneto.size > 0; if (g && veille === null) veille = powerSaveBlocker.start('prevent-app-suspension'); if (!g && veille !== null && !garderVeille) { powerSaveBlocker.stop(veille); veille = null; } };
let garderVeille = false;
ipcMain.handle('rec-start', (_e, { url, nom, k7 }) => {
  const vlc = EXE.vlc(); if (!vlc) return { err: 'VLC introuvable' };
  fs.mkdirSync(K7, { recursive: true });
  const d = new Date(), p2 = n => String(n).padStart(2, '0');
  const f = path.join(K7, `K7-${String(k7).padStart(3, '0')}_${nomSur(nom)}_${d.getFullYear()}-${p2(d.getMonth() + 1)}-${p2(d.getDate())}_${p2(d.getHours())}h${p2(d.getMinutes())}.ts`);
  const p = spawn(vlc, ['-I', 'dummy', '--dummy-quiet', '--no-video-title-show', url, '--sout=#std{access=file,mux=ts,dst="' + f + '"}', '--sout-keep'], { stdio: 'ignore', windowsHide: true });
  const id = String(p.pid) + '-' + Date.now(); magneto.set(id, { p, f });
  p.on('exit', () => { magneto.delete(id); majVeille(); if (w && !w.isDestroyed()) w.webContents.send('rec-fin', id); });
  majVeille(); return { id, f };
});
ipcMain.handle('rec-stop', (_e, id) => { const m = magneto.get(id); if (!m) return null; try { m.p.kill(); } catch (e) {} return m.f; });
ipcMain.handle('garder-eveil', (_e, g) => { garderVeille = !!g; if (g && veille === null) veille = powerSaveBlocker.start('prevent-app-suspension'); majVeille(); return true; });
app.on('before-quit', () => { for (const m of magneto.values()) try { m.p.kill(); } catch (e) {} });
EOF_F1
cat > preload.js <<'EOF_F2'
const { contextBridge, ipcRenderer } = require('electron');
const inv = (c, ...a) => ipcRenderer.invoke(c, ...a);
contextBridge.exposeInMainWorld('rene', {
  qwen: a => inv('qwen', a), icy: u => inv('icy', u), gpu: () => inv('gpu'),
  logiciels: () => inv('logiciels'), lancer: (qui, arg) => inv('lancer', qui, arg),
  rec: { start: o => inv('rec-start', o), stop: id => inv('rec-stop', id), finie: cb => ipcRenderer.on('rec-fin', (_e, id) => cb(id)) },
  k7: { liste: () => inv('k7-liste'), dossier: () => inv('k7-dossier'), effacer: f => inv('k7-effacer', f) },
  eveil: g => inv('garder-eveil', g)
});
EOF_F2
cat > index.html <<'EOF_F3'
<!DOCTYPE html><html lang="fr"><head><meta charset="utf-8"><title>René TV</title>
<style>
:root{--bg:#0d0f14;--p1:#151821;--p2:#1d2130;--t:#eef0f5;--m:#8a90a2;--a:#e4002b;--g:#33ff66;--gd:#1a8a3a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--t);font:15px "Segoe UI",system-ui,sans-serif;height:100vh;display:flex;flex-direction:column;overflow:hidden}
button,select,input{font:inherit;color:var(--t);background:var(--p2);border:1px solid #2c3244;border-radius:8px;padding:6px 11px}
button{cursor:pointer}button:hover{border-color:#4a5370;background:#252a3b}
/* barre haute */
header{display:flex;align-items:center;gap:14px;padding:10px 20px;background:linear-gradient(#141722,#0d0f14)}
#logo{font-weight:800;font-size:20px;letter-spacing:.5px}#logo b{color:var(--a)}
nav{display:flex;gap:4px}nav button{background:none;border:none;color:var(--m);font-weight:600;padding:8px 12px}
nav button.on{color:var(--t);border-bottom:3px solid var(--a);border-radius:0}
#q{flex:1;max-width:340px;margin-left:auto}
#recPill{display:none;background:#3a0710;border:1px solid var(--a);color:#ff6b81;font-weight:700;border-radius:20px;padding:5px 12px;cursor:pointer}
#horloge{color:var(--m);font-variant-numeric:tabular-nums}
/* pages */
#pages{flex:1;overflow:auto;padding:6px 20px 20px}
.page{display:none}.page.on{display:block}
h2{font-size:19px;margin:20px 0 10px;display:flex;align-items:center;gap:10px}h2 small{color:var(--m);font-weight:400;font-size:13px}
.rangee{display:flex;gap:12px;overflow-x:auto;padding:4px 2px 12px;scroll-snap-type:x proximity}
.grille{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px}
.tuile{position:relative;flex:0 0 210px;height:125px;background:var(--p1);border:1px solid #232838;border-radius:12px;overflow:hidden;cursor:pointer;display:flex;flex-direction:column;justify-content:flex-end;padding:10px;scroll-snap-align:start;transition:transform .12s,border-color .12s;content-visibility:auto;contain-intrinsic-size:210px 125px}
.grille .tuile{flex:none}
.tuile:hover{transform:scale(1.04);border-color:#5a6380;z-index:2}
.tuile img{position:absolute;top:14px;left:50%;transform:translateX(-50%);max-width:62%;max-height:58px;object-fit:contain}
.tuile .num{position:absolute;top:8px;left:9px;background:#000a;border-radius:6px;padding:1px 7px;font-weight:700;font-size:13px}
.tuile .nm{font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;position:relative}
.tuile .st{color:var(--m);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;position:relative}
.tuile .fav{position:absolute;top:6px;right:8px;background:none;border:none;font-size:18px;color:#5a6178;padding:0}.tuile .fav.on{color:#ffcc33}
.tuile .rec{position:absolute;top:8px;right:34px;width:11px;height:11px;border-radius:50%;background:var(--a);animation:clig 1s steps(1) infinite}
.vide{color:var(--m);padding:10px 2px}
/* lecteur plein écran */
#lecteur{position:fixed;inset:0;background:#000;display:none;z-index:50}
#lecteur.on{display:block}
#v{width:100%;height:100%;object-fit:contain;transform-origin:center}
#zapNum{position:absolute;top:24px;right:34px;font:700 64px Consolas,monospace;color:var(--g);text-shadow:0 0 12px #33ff66aa;display:none}
#fermer{position:absolute;top:16px;left:16px}
#barre{position:absolute;left:0;right:0;bottom:0;padding:18px 26px 20px;background:linear-gradient(transparent,#000d 35%);transition:opacity .4s}
#barre.cache{opacity:0;pointer-events:none}
#bandeau{font:16px Consolas,"Courier New",monospace;color:var(--g);text-shadow:0 0 5px #33ff6688;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-bottom:10px}
#cmds{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
#cmds button{background:#ffffff14;border-color:#ffffff22}
#bRec{color:#ff6b81;font-weight:700}
/* magnétoscope années 80 */
#magneto{display:none;align-items:center;gap:12px;margin-left:auto;background:#111;border:1px solid #333;border-radius:6px;padding:5px 12px;font:14px Consolas,monospace}
#magneto.on{display:flex}
.voyant{width:12px;height:12px;border-radius:50%;background:var(--a);box-shadow:0 0 8px var(--a);animation:clig 1s steps(1) infinite}
@keyframes clig{50%{opacity:.15}}
.bobine{display:inline-block;width:18px;height:18px;border:2px solid #bbb;border-radius:50%;position:relative;animation:tourne 1.6s linear infinite}
.bobine::before,.bobine::after{content:"";position:absolute;left:50%;top:1px;width:2px;height:12px;background:#bbb;transform:translateX(-50%)}
.bobine::after{transform:translateX(-50%) rotate(60deg)}
@keyframes tourne{to{transform:rotate(360deg)}}
#compteur{background:#000;color:#ffd84a;padding:1px 6px;border:1px solid #444;letter-spacing:3px;font-weight:700}
/* réglages */
#reglages{position:absolute;top:0;right:0;bottom:0;width:340px;background:#0d0f14f2;border-left:1px solid #2c3244;padding:14px;overflow:auto;display:none}
#reglages.on{display:block}
#reglages h4{margin:14px 0 6px;color:var(--m);font-size:13px;letter-spacing:1px}
#reglages label{display:flex;justify-content:space-between;align-items:center;gap:6px;margin:4px 0;font-size:13px}
#reglages input[type=range]{flex:1;accent-color:var(--a)}
#eq{display:flex;gap:2px;height:110px}#eq div{flex:1;display:flex;flex-direction:column;align-items:center;font-size:10px}
#eq input{writing-mode:vertical-lr;direction:rtl;flex:1;width:16px;accent-color:var(--a)}
/* console RÉTRO */
#retro{background:#000;border-top:1px solid var(--gd);font:14px Consolas,"Courier New",monospace;color:var(--g);text-shadow:0 0 4px #33ff6688;position:relative;z-index:60}
#retroTete{display:flex;align-items:center;gap:10px;padding:5px 14px;cursor:pointer}
#retroTete b{letter-spacing:2px}
#log{height:120px;overflow:auto;padding:4px 14px;white-space:pre-wrap;display:none}
#retro.ouvert #log{display:block}
#log .moi{color:#b6ffc8}
#cmd{display:flex;align-items:center;padding:4px 14px 7px}
#cmd input{flex:1;background:none;border:none;outline:none;color:var(--g);font:inherit;padding:2px}
.curseur::after{content:"█";animation:clig 1s steps(1) infinite}
#lecteur.on~#retro{position:fixed;left:0;right:0;bottom:0;background:#000c}
#lecteur.on~#retro:not(.ouvert){display:none}
/* formulaires */
.carte{background:var(--p1);border:1px solid #232838;border-radius:12px;padding:14px;margin-bottom:12px}
.ligne{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin:6px 0}
.k7{display:flex;align-items:center;gap:10px;background:var(--p1);border:1px solid #232838;border-radius:10px;padding:10px;margin-bottom:8px}
.k7 .etiq{flex:1;font:14px Consolas,monospace;background:#efe6c8;color:#222;padding:6px 10px;border-radius:3px;border-left:8px solid var(--a)}
</style></head><body>
<header>
 <div id="logo">René <b>TV</b></div>
 <nav>
  <button data-p="accueil" class="on">Accueil</button><button data-p="tv">TV</button><button data-p="radio">Radio</button><button data-p="video">Vidéos</button><button data-p="k7">Cassettes</button><button data-p="prog">Programmation</button><button data-p="conf">Réglages</button>
 </nav>
 <input id="q" placeholder="🔍 Rechercher une chaîne, une radio, une vidéo…">
 <span id="recPill">● REC</span>
 <span id="horloge"></span>
</header>
<div id="pages">
 <div class="page on" id="p-accueil"></div>
 <div class="page" id="p-tv"><h2>Toutes les chaînes <small id="nbTv"></small></h2><div class="grille" id="gTv"></div></div>
 <div class="page" id="p-radio"><h2>Toutes les radios <small id="nbRadio"></small> <button id="bMonde">🌍 Chercher dans le monde</button></h2><div class="grille" id="gRadio"></div></div>
 <div class="page" id="p-video"><h2>Mes vidéos <button id="bOuvrir">📂 Ouvrir des vidéos</button> <button data-lance="freetube">▶ YouTube sans pub (FreeTube)</button> <button data-lance="kodi">🎬 Kodi</button></h2><div class="grille" id="gVideo"></div></div>
 <div class="page" id="p-k7"><h2>Mes cassettes <small>Vidéos\Rene-K7</small> <button id="bDossier">📁 Ouvrir le dossier</button></h2><div id="gK7"></div></div>
 <div class="page" id="p-prog">
  <h2>Programmer le magnétoscope</h2>
  <div class="carte"><div class="ligne">Chaîne ou radio <select id="prCh"></select></div>
  <div class="ligne">Début <input type="datetime-local" id="prDeb"> Durée <input type="number" id="prDur" value="60" min="1" style="width:80px"> min <button id="prAdd">● Programmer</button></div>
  <div class="ligne" style="color:var(--m);font-size:13px">Le PC doit rester allumé et l'appli ouverte : je l'empêche de se mettre en veille tant qu'un enregistrement est programmé.</div></div>
  <div id="prListe"></div>
 </div>
 <div class="page" id="p-conf">
  <h2>Assistant RÉTRO</h2>
  <div class="carte ligne">Nom <input id="cNom" size="12"> Ollama <input id="cOll" size="26"> Modèle <input id="cMod" size="14"> <button id="cSave">Enregistrer</button></div>
  <h2>Logiciels gratuits connectés</h2><div class="carte" id="logi"></div>
  <h2>Ajouter une chaîne ou une radio</h2>
  <div class="carte ligne"><select id="pt"><option value="tv">TV</option><option value="radio">Radio</option></select><input id="pn" placeholder="Nom" size="16"><input id="pu" placeholder="Adresse du flux http…" size="38"><button id="padd">Ajouter</button></div>
  <div id="pl"></div>
  <h2>Liste des chaînes TV</h2><div class="carte ligne"><input id="tvurl" size="56"><button id="tvsave">Enregistrer</button><button id="tvdef">Défaut</button></div>
  <h2>Sauvegarde</h2><div class="carte ligne"><button id="exp">Exporter mes réglages</button><label>Importer <input type="file" id="imp" accept=".json"></label></div>
  <h2>Machine</h2><div class="carte" id="gpu" style="color:var(--m);font-size:13px"></div>
 </div>
</div>
<div id="lecteur">
 <video id="v" autoplay></video>
 <button id="fermer">✕ Retour</button>
 <div id="zapNum"></div>
 <div id="barre">
  <div id="bandeau">&gt; …</div>
  <div id="cmds">
   <button id="bPrec" title="Chaîne précédente (↓)">⏮</button><button id="bPlay" title="Pause (Espace)">⏯</button><button id="bSuiv" title="Chaîne suivante (↑)">⏭</button>
   <button id="bRec" title="Enregistrer (R) — chaque appui ajoute 30 min">● REC</button><button id="bStopRec" title="Arrêter l'enregistrement (S)">■ STOP</button>
   <button id="bReg">🎛 Son &amp; image</button><button id="bVlc">↗ Ouvrir dans VLC</button><button id="bPlein">⛶</button><button id="bFav">☆</button>
   <div id="magneto"><span class="voyant"></span><span class="bobine"></span><span class="bobine"></span><span id="k7nom"></span><span id="compteur">0000</span><span id="otr"></span></div>
  </div>
 </div>
 <div id="reglages">
  <h4>SON</h4>
  <label>Volume <input type="range" id="aVol" min="0" max="300" value="100"><span id="aVolV">100%</span></label>
  <label>Dialogues + <input type="range" id="aDia" min="0" max="12" value="0"><span id="aDiaV">0 dB</span></label>
  <label>Mode nuit <input type="checkbox" id="aNuit"></label>
  <label>Balance <input type="range" id="aBal" min="-100" max="100" value="0"></label>
  <label>Mono <input type="checkbox" id="aMono"></label>
  <label>Égaliseur <select id="aPre"><option value="plat">Plat</option><option value="voix">Voix</option><option value="basses">Basses</option><option value="cinema">Cinéma</option><option value="musique">Musique</option><option value="aigus">Aigus</option></select></label>
  <div id="eq"></div>
  <label>Moteur audio <select id="aMoteur"><option value="1">Actif</option><option value="0">Direct (si son muet)</option></select></label>
  <h4>IMAGE</h4>
  <label>Vitesse <select id="iVit"><option>0.25</option><option>0.5</option><option>0.75</option><option selected>1</option><option>1.25</option><option>1.5</option><option>2</option><option>3</option></select></label>
  <label>Luminosité <input type="range" id="iLum" min="50" max="150" value="100"></label>
  <label>Contraste <input type="range" id="iCon" min="50" max="150" value="100"></label>
  <label>Saturation <input type="range" id="iSat" min="0" max="200" value="100"></label>
  <label>Format <select id="iFmt"><option value="contain">Adapter</option><option value="cover">Remplir</option><option value="fill">Étirer</option></select></label>
  <label>Zoom <input type="range" id="iZoom" min="100" max="200" value="100"></label>
  <label>Qualité flux <select id="iQual"><option value="-1">Auto</option></select></label>
  <div class="ligne"><button id="iPip">Image dans l'image</button><button id="iCap">Capture</button></div>
  <div class="ligne"><button id="iA">A</button><button id="iB">B</button><button id="iAB0">Boucle off</button><span id="iABv"></span></div>
  <label>Sous-titres .srt <input type="file" id="iSrt" accept=".srt,.vtt" style="width:140px"></label>
  <h4>SOMMEIL</h4>
  <div class="ligne"><button data-dodo="15">15 min</button><button data-dodo="30">30</button><button data-dodo="60">60</button><button data-dodo="0">Off</button><span id="dodoV"></span></div>
 </div>
</div>
<div id="retro">
 <div id="retroTete"><b id="nomia">RÉTRO</b><span id="retroDernier" style="flex:1;opacity:.8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis"></span><span id="retroFl">▲</span></div>
 <div id="log"></div>
 <div id="cmd"><span>&gt;&nbsp;</span><input id="in" placeholder="parle-moi : « France 2 », « du jazz », « enregistre », « chaîne 7 », « dodo 30 », « aide »"><span class="curseur"></span></div>
</div>
<script src="hls.min.js"></script>
<script>
"use strict";
const TV_DEF='https://iptv-org.github.io/iptv/countries/fr.m3u';
const RB='https://all.api.radio-browser.info/json/stations/search?hidebroken=true&order=clickcount&reverse=true';
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)],v=$('#v');
const ls=(k,d)=>{try{const x=JSON.parse(localStorage.getItem(k));return x??d}catch(e){return d}};
const ss=(k,x)=>{try{localStorage.setItem(k,JSON.stringify(x))}catch(e){}};
const R=window.rene;
let page='accueil',tv=[],radio=[],videos=[],cassettes=[],hls=null,cur=null;
let favs=ls('favs',{}),perso=ls('perso',[]),hist=ls('hist',[]),progs=ls('progs',[]);
let conf=Object.assign({nom:'RÉTRO',oll:'http://localhost:11434',mod:'qwen2.5:7b'},ls('conf',{}));
$('#nomia').textContent=conf.nom;
const dire=(t,moi)=>{const d=document.createElement('div');if(moi)d.className='moi';d.textContent=(moi?'> ':conf.nom+' : ')+t;$('#log').append(d);$('#log').scrollTop=1e9;if(!moi)$('#retroDernier').textContent=t};
const bandeau=t=>$('#bandeau').textContent='> '+t;
const echap=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* ===== numérotation façon box : TNT, puis le reste ; radios à partir de 101 ===== */
const TNT=[[2,/^france ?2\b/i],[3,/^france ?3\b/i],[4,/canal\+|canal plus/i],[5,/^france ?5\b/i],[6,/^m6\b/i],[7,/^arte\b/i],[8,/^c8\b|^c ?8\b/i],[9,/^w9\b/i],[10,/^tmc\b/i],[11,/^tfx\b/i],[12,/^nrj ?12/i],[13,/^lcp|public s[eé]nat/i],[14,/^france ?4\b/i],[15,/^bfm ?tv\b/i],[16,/^cnews/i],[17,/^cstar/i],[18,/^gulli/i],[20,/tf1 s[eé]ries/i],[21,/l'?[eé]quipe/i],[22,/^6ter/i],[23,/rmc story/i],[24,/rmc d[eé]couverte/i],[25,/ch[eé]rie ?25/i],[26,/^lci\b/i],[27,/franceinfo|france ?info/i],[1,/^tf1\b(?! s)/i]];
function numerote(){const pris=new Set();const TVall=[...perso.filter(p=>p.t==='tv'),...tv];
 for(const x of TVall){x.num=null;for(const [n,re] of TNT){if(!pris.has(n)&&re.test(x.n)){x.num=n;pris.add(n);break}}}
 let n=30;for(const x of TVall)if(x.num==null){while(pris.has(n))n++;x.num=n++}
 TVall.sort((a,b)=>a.num-b.num);
 let r=101;[...perso.filter(p=>p.t==='radio'),...radio].forEach(x=>x.num=r++);
 videos.forEach((x,i)=>x.num=901+i)}
const listeTV=()=>[...perso.filter(p=>p.t==='tv'),...tv].sort((a,b)=>a.num-b.num);
const listeRadio=()=>[...perso.filter(p=>p.t==='radio'),...radio];
const tout=()=>[...listeTV(),...listeRadio(),...videos];
const parNum=n=>tout().find(x=>x.num===n);

/* ===== catalogues ===== */
function parseM3U(txt){const out=[];let info=null;for(const l of txt.split(/\r?\n/)){const s=l.trim();if(s.startsWith('#EXTINF')){info={n:s.slice(s.lastIndexOf(',')+1).trim(),logo:(s.match(/tvg-logo="([^"]*)"/)||[])[1]||'',s:(s.match(/group-title="([^"]*)"/)||[])[1]||''}}else if(s&&!s.startsWith('#')&&info){out.push({t:'tv',n:info.n,u:s,logo:info.logo,s:info.s});info=null}}return out}
async function chargeTV(){try{const r=await fetch(ls('tvurl',TV_DEF));tv=parseM3U(await r.text());dire(tv.length+' chaînes TV.')}catch(e){tv=[];dire('Liste TV injoignable (connexion ?).')}numerote();rendTout()}
const mapR=x=>({t:'radio',n:(x.name||'').trim(),u:x.url_resolved||x.url,logo:x.favicon,s:[x.countrycode,(x.tags||'').split(',').slice(0,2).join(' ')].filter(Boolean).join(' · ')});
async function chercheRadios(params){try{const r=await fetch(RB+'&'+params);return (await r.json()).map(mapR).filter(x=>x.n&&x.u)}catch(e){return []}}
async function chargeRadio(){radio=await chercheRadios('countrycode=FR&limit=100000');dire(radio.length?radio.length+' radios françaises.':'Annuaire radio injoignable.');numerote();rendTout()}
async function chargeK7(){cassettes=await R.k7.liste();rendK7();rendAccueil()}

/* ===== tuiles ===== */
const enCours=()=>new Set(recs.map(r=>r.item.u));
function tuile(x){const d=document.createElement('div');d.className='tuile';
 if(x.logo){const i=document.createElement('img');i.loading='lazy';i.src=x.logo;i.onerror=()=>i.remove();d.append(i)}
 if(x.num!=null){const n=document.createElement('span');n.className='num';n.textContent=x.num;d.append(n)}
 if(enCours().has(x.u)){const r=document.createElement('span');r.className='rec';d.append(r)}
 const nm=document.createElement('div');nm.className='nm';nm.textContent=x.n;const st=document.createElement('div');st.className='st';
 st.textContent=x.t==='radio'?'Radio'+(x.s?' · '+x.s:''):x.t==='video'?'Vidéo · '+(x.s||''):(x.s||'TV');d.append(nm,st);
 if(x.t!=='video'){const f=document.createElement('button');f.className='fav'+(favs[x.u]?' on':'');f.textContent='★';f.onclick=e=>{e.stopPropagation();basculeFav(x)};d.append(f)}
 d.onclick=()=>joue(x);return d}
function remplir(box,L,vide){box.innerHTML='';if(!L.length){box.innerHTML='<div class="vide">'+(vide||'Rien pour l\'instant.')+'</div>';return}const fr=document.createDocumentFragment();for(const x of L)fr.append(tuile(x));box.append(fr)}
const filtre=L=>{const q=$('#q').value.toLowerCase().trim();return q?L.filter(x=>(x.n+' '+(x.s||'')+' '+(x.num||'')).toLowerCase().includes(q)):L};
function rangee(titre,L,vide){const h=document.createElement('h2');h.textContent=titre;const r=document.createElement('div');r.className='rangee';remplir(r,L,vide);$('#p-accueil').append(h,r)}
function rendAccueil(){$('#p-accueil').innerHTML='';
 const q=$('#q').value.trim();if(q){rangee('Résultats pour « '+q+' »',filtre(tout()),'Aucun résultat.');return}
 rangee('En direct',listeTV(),'Chargement des chaînes…');
 if(Object.keys(favs).length)rangee('Mes favoris',Object.values(favs));
 if(hist.length)rangee('Reprendre',hist);
 rangee('Suggestions de '+conf.nom,suggestions());
 rangee('Radios',listeRadio(),'Chargement des radios…');
 if(videos.length)rangee('Mes vidéos',videos);
 if(cassettes.length){const h=document.createElement('h2');h.textContent='Mes cassettes';$('#p-accueil').append(h);const r=document.createElement('div');r.className='rangee';
  for(const c of cassettes.slice(0,30)){const d=document.createElement('div');d.className='tuile';d.innerHTML='<div class="nm">📼 '+echap(etiquette(c.n))+'</div><div class="st">'+(c.taille/1e6).toFixed(0)+' Mo · repasse dans VLC</div>';d.onclick=()=>R.lancer('vlc',c.f);r.append(d)}$('#p-accueil').append(r)}}
function rendTout(){rendAccueil();remplir($('#gTv'),filtre(listeTV()),'Chargement…');$('#nbTv').textContent=listeTV().length+' chaînes';
 remplir($('#gRadio'),filtre(listeRadio()),'Chargement…');$('#nbRadio').textContent=listeRadio().length+' radios';
 remplir($('#gVideo'),filtre(videos),'Ouvre des vidéos de ton PC avec le bouton ci-dessus.');rendProgCh()}
function basculeFav(x){favs[x.u]?delete favs[x.u]:favs[x.u]={t:x.t,n:x.n,u:x.u,logo:x.logo,s:x.s,num:x.num};ss('favs',favs);majFav();rendTout()}
function suggestions(){const h=new Date().getHours(),pool=[],pick=a=>a.length?a[Math.floor(Math.random()*a.length)]:null,T=listeTV();
 pool.push(pick(Object.values(favs)),hist[0]);
 if(h<11)pool.push(pick(T.filter(x=>/info|news|24/i.test(x.n+x.s))));else if(h>=20)pool.push(pick(T.filter(x=>/cin|film|movie/i.test(x.n+x.s))));
 pool.push(pick(T.slice(0,20)),pick(listeRadio().slice(0,80)),pick(listeRadio().slice(0,80)),pick(videos));
 const vus=new Set();return pool.filter(x=>x&&!vus.has(x.u)&&vus.add(x.u))}

/* ===== lecteur ===== */
let icyT=null,cacheT=null;
function joue(x){cur=x;if(hls){hls.destroy();hls=null}clearInterval(icyT);v.removeAttribute('src');v.load();
 $('#lecteur').classList.add('on');v.poster=x.t==='radio'&&x.logo?x.logo:'';montreBarre();majFav();
 bandeau((x.num!=null?'['+x.num+'] ':'')+'CHARGEMENT : '+x.n);
 if(/\.m3u8(\?|$)/i.test(x.u)&&window.Hls&&Hls.isSupported()){hls=new Hls({capLevelToPlayerSize:false});hls.loadSource(x.u);hls.attachMedia(v);
  hls.on(Hls.Events.MANIFEST_PARSED,()=>{const q=$('#iQual');q.innerHTML='<option value="-1">Auto</option>'+hls.levels.map((l,i)=>`<option value="${i}">${l.height||'?'}p · ${(l.bitrate/1e6).toFixed(1)} Mb/s</option>`).join('');if(hls.levels.length){hls.currentLevel=hls.levels.length-1;q.value=hls.levels.length-1}});
  hls.on(Hls.Events.ERROR,(e,d)=>{if(d.fatal)bandeau('['+(x.num??'')+'] ✖ '+x.n+' : flux indisponible — essaie « Ouvrir dans VLC » ou zappe')})}
 else{v.src=x.u;$('#iQual').innerHTML='<option value="-1">Auto</option>'}
 v.play().catch(()=>{});
 if(x.t!=='video'){hist=[{t:x.t,n:x.n,u:x.u,logo:x.logo,s:x.s,num:x.num},...hist.filter(h=>h.u!==x.u)].slice(0,30);ss('hist',hist)}
 if(x.t==='radio'){const maj=async()=>{const t=await R.icy(x.u);if(cur===x)bandeau('['+x.num+'] RADIO · '+x.n+(t?'  ♪ '+t:'')+(x.s?'  ['+x.s+']':''))};maj();icyT=setInterval(maj,20000)}}
v.addEventListener('loadedmetadata',()=>{if(!cur||cur.t==='radio')return;const h=v.videoHeight,w=v.videoWidth,dur=isFinite(v.duration)?Math.round(v.duration/60)+' min':'DIRECT';
 bandeau((cur.num!=null?'['+cur.num+'] ':'')+(cur.t==='tv'?'TV · ':'VIDÉO · ')+cur.n+'  ['+(w&&h?w+'×'+h:'audio')+' · '+dur+']'+(cur.t==='tv'&&cur.s?'  '+cur.s:''))});
v.onerror=()=>{if(cur)bandeau('['+(cur.num??'')+'] ✖ '+cur.n+' : flux illisible — essaie « Ouvrir dans VLC »')};
function fermeLecteur(){$('#lecteur').classList.remove('on');$('#reglages').classList.remove('on');v.pause();if(hls){hls.destroy();hls=null}clearInterval(icyT);v.removeAttribute('src');v.load();cur=null;rendAccueil()}
function montreBarre(){$('#barre').classList.remove('cache');document.body.style.cursor='';clearTimeout(cacheT);cacheT=setTimeout(()=>{if(!$('#reglages').classList.contains('on')){$('#barre').classList.add('cache');document.body.style.cursor='none'}},4500)}
$('#lecteur').addEventListener('mousemove',montreBarre);
function zappe(d){if(!cur)return;const L=cur.t==='radio'?listeRadio():cur.t==='video'?videos:listeTV();if(!L.length)return;let i=L.findIndex(x=>x.u===cur.u);i=(i+d+L.length)%L.length;joue(L[i])}
let zapBuf='',zapT=null;
function tapeNum(c){zapBuf+=c;const z=$('#zapNum');z.textContent=zapBuf;z.style.display='block';clearTimeout(zapT);
 zapT=setTimeout(()=>{const n=+zapBuf;zapBuf='';z.style.display='none';const x=parNum(n);if(x)joue(x);else dire('Pas de chaîne n° '+n+'.')},1400)}
function majFav(){$('#bFav').textContent=cur&&favs[cur.u]?'★':'☆'}
$('#fermer').onclick=fermeLecteur;$('#bPrec').onclick=()=>zappe(-1);$('#bSuiv').onclick=()=>zappe(1);
$('#bPlay').onclick=()=>v.paused?v.play():v.pause();$('#bFav').onclick=()=>cur&&basculeFav(cur);
$('#bReg').onclick=()=>{$('#reglages').classList.toggle('on');montreBarre()};
$('#bPlein').onclick=()=>document.fullscreenElement?document.exitFullscreen():$('#lecteur').requestFullscreen().catch(()=>{});
$('#bVlc').onclick=async()=>{if(!cur)return;const ok=await R.lancer('vlc',cur.t==='video'?null:cur.u);dire(ok?'Ouvert dans VLC.':'VLC introuvable : relance l\'installation.')};

/* ===== MAGNÉTOSCOPE ANNÉES 80 =====
   - REC sur la chaîne regardée : un VLC invisible enregistre le flux brut sur disque, indépendamment de l'écran
     (comme le tuner du magnétoscope : tu peux zapper ou fermer, la cassette continue de tourner)
   - OTR (One Touch Recording) : chaque nouvel appui sur REC ajoute 30 min et fixe un arrêt automatique
   - compteur de bande à 4 chiffres, voyant rouge, bobines qui tournent
   - programmation différée : chaîne + date/heure + durée, le PC est empêché de dormir */
let recs=[];let k7n=ls('k7n',0);
async function demarreRec(item,dureeMin){if(!item||item.t==='video'){dire('On n\'enregistre que la TV et la radio en direct.');return null}
 const deja=recs.find(r=>r.item.u===item.u);
 if(deja){deja.fin=(deja.fin&&deja.fin>Date.now()?deja.fin:Date.now())+30*60000;dire('OTR : +30 min → arrêt à '+heure(deja.fin)+'.');majMagneto();return deja}
 k7n++;ss('k7n',k7n);const r=await R.rec.start({url:item.u,nom:item.n,k7:k7n});
 if(r.err){dire('Enregistrement impossible : '+r.err+'.');k7n--;ss('k7n',k7n);return null}
 const rec={id:r.id,f:r.f,item,k7:k7n,debut:Date.now(),fin:dureeMin?Date.now()+dureeMin*60000:null};recs.push(rec);
 dire('● REC — cassette K7-'+String(k7n).padStart(3,'0')+' : '+item.n+(rec.fin?' jusqu\'à '+heure(rec.fin):' (sans limite — appuie encore sur REC pour +30 min)')+'.');majMagneto();rendTout();return rec}
async function arreteRec(rec){if(!rec)return;await R.rec.stop(rec.id)}
R.rec.finie(id=>{const r=recs.find(x=>x.id===id);if(!r)return;recs=recs.filter(x=>x!==r);dire('■ STOP — K7-'+String(r.k7).padStart(3,'0')+' rangée ('+r.item.n+', '+duree(Date.now()-r.debut)+').');majMagneto();chargeK7();rendTout()});
const heure=t=>new Date(t).toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'});
const duree=ms=>{const s=Math.round(ms/1000);return Math.floor(s/3600)+'h'+String(Math.floor(s%3600/60)).padStart(2,'0')+'m'+String(s%60).padStart(2,'0')};
function recCourant(){return cur?recs.find(r=>r.item.u===cur.u):null}
function majMagneto(){const r=recCourant()||recs[0];$('#recPill').style.display=recs.length?'inline-block':'none';$('#recPill').textContent='● REC '+recs.length;
 const m=$('#magneto');if(!r){m.classList.remove('on');return}m.classList.add('on');
 $('#k7nom').textContent='K7-'+String(r.k7).padStart(3,'0')+' '+r.item.n.slice(0,18);
 $('#compteur').textContent=String(Math.floor((Date.now()-r.debut)/1000)%10000).padStart(4,'0');
 $('#otr').textContent=r.fin?'→ '+heure(r.fin):'∞'}
setInterval(()=>{const now=Date.now();for(const r of recs)if(r.fin&&now>=r.fin)arreteRec(r);majMagneto();
 for(const p of progs)if(!p.lance&&now>=p.debut){p.lance=true;ss('progs',progs);const x=parNum(p.num)||tout().find(y=>y.u===p.u);dire('⏰ Programmation : '+(x?x.n:p.n)+'.');demarreRec(x||{t:p.t,n:p.n,u:p.u},p.duree)}
 const actifs=progs.filter(p=>!p.lance);R.eveil(actifs.length>0);
 $('#horloge').textContent=new Date().toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'})},1000);
$('#bRec').onclick=()=>demarreRec(cur);$('#bStopRec').onclick=()=>arreteRec(recCourant()||recs[recs.length-1]);
$('#recPill').onclick=()=>{const r=recs[0];if(r)joue(r.item)};
function rendProgCh(){const s=$('#prCh'),val=s.value;s.innerHTML=[...listeTV(),...listeRadio().slice(0,400)].map(x=>`<option value="${x.num}">${x.num} — ${echap(x.n)}</option>`).join('');if(val)s.value=val}
function rendProgs(){const b=$('#prListe');b.innerHTML='';const L=progs.filter(p=>!p.lance).sort((a,c)=>a.debut-c.debut);
 if(!L.length){b.innerHTML='<div class="vide">Aucun enregistrement programmé.</div>';return}
 for(const p of L){const d=document.createElement('div');d.className='k7';d.innerHTML='<span class="etiq">'+echap(new Date(p.debut).toLocaleString('fr-FR',{weekday:'short',day:'2-digit',month:'2-digit',hour:'2-digit',minute:'2-digit'})+' · ['+p.num+'] '+p.n+' · '+p.duree+' min')+'</span>';
  const x=document.createElement('button');x.textContent='Annuler';x.onclick=()=>{progs=progs.filter(q=>q!==p);ss('progs',progs);rendProgs()};d.append(x);b.append(d)}}
$('#prAdd').onclick=()=>{const num=+$('#prCh').value,x=parNum(num),deb=new Date($('#prDeb').value).getTime(),dur=+$('#prDur').value;
 if(!x||!deb||deb<Date.now()-60000||!(dur>0)){dire('Programmation incomplète : chaîne, heure future et durée.');return}
 progs.push({num,n:x.n,u:x.u,t:x.t,debut:deb,duree:dur});ss('progs',progs);rendProgs();dire('Programmé : '+x.n+' le '+new Date(deb).toLocaleString('fr-FR')+' pendant '+dur+' min.')};
function etiquette(f){const m=f.match(/^K7-(\d+)_(.+?)_(\d{4})-(\d\d)-(\d\d)_(\d\d)h(\d\d)/);return m?'K7-'+m[1]+' · '+m[2].replace(/_/g,' ')+' · '+m[5]+'/'+m[4]+' '+m[6]+'h'+m[7]:f}
function rendK7(){const b=$('#gK7');b.innerHTML='';if(!cassettes.length){b.innerHTML='<div class="vide">Pas encore de cassette. Pendant une chaîne ou une radio, appuie sur ● REC.</div>';return}
 for(const c of cassettes){const d=document.createElement('div');d.className='k7';const e=document.createElement('span');e.className='etiq';e.textContent='📼 '+etiquette(c.n)+' · '+(c.taille/1e6).toFixed(0)+' Mo';
  const p=document.createElement('button');p.textContent='▶ Repasser';p.onclick=()=>R.lancer('vlc',c.f);
  const x=document.createElement('button');x.textContent='🗑';let arm=false;x.onclick=async()=>{if(!arm){arm=true;x.textContent='Sûr ?';setTimeout(()=>{arm=false;x.textContent='🗑'},3000);return}await R.k7.effacer(c.f);chargeK7()};
  d.append(e,p,x);b.append(d)}}
$('#bDossier').onclick=()=>R.k7.dossier();

/* ===== son ===== */
const BANDES=[32,64,125,250,500,1000,2000,4000,8000,16000];
const PRE={plat:[0,0,0,0,0,0,0,0,0,0],voix:[-4,-3,-1,0,2,4,5,4,1,0],basses:[7,6,4,2,0,0,0,0,0,0],cinema:[5,4,2,0,0,1,3,3,2,1],musique:[3,2,1,0,-1,0,1,2,3,3],aigus:[0,0,0,0,0,0,2,4,6,7]};
let A=null;const reg=Object.assign({vol:100,dia:0,nuit:false,bal:0,mono:false,pre:'plat',eq:PRE.plat.slice(),moteur:'1'},ls('reg',{}));
function audio(){if(A||reg.moteur!=='1')return A;try{const c=new AudioContext(),src=c.createMediaElementSource(v);
 const dia=c.createBiquadFilter();dia.type='peaking';dia.frequency.value=2500;dia.Q.value=0.8;
 const eq=BANDES.map(f=>{const b=c.createBiquadFilter();b.type='peaking';b.frequency.value=f;b.Q.value=1.1;return b});
 const comp=c.createDynamicsCompressor(),mono=c.createGain(),gain=c.createGain(),pan=c.createStereoPanner();
 src.connect(dia);let p=dia;for(const b of eq){p.connect(b);p=b}p.connect(comp);comp.connect(mono);mono.connect(gain);gain.connect(pan);pan.connect(c.destination);
 A={c,dia,eq,comp,mono,gain,pan};appliqueAudio();return A}catch(e){dire('Moteur audio indisponible : '+e.message);return null}}
function appliqueAudio(){ss('reg',reg);$('#aVolV').textContent=reg.vol+'%';$('#aDiaV').textContent=reg.dia+' dB';
 if(!A){v.volume=Math.min(1,reg.vol/100);return}
 A.gain.gain.value=reg.vol/100;A.dia.gain.value=reg.dia;A.pan.pan.value=reg.bal/100;A.eq.forEach((b,i)=>b.gain.value=reg.eq[i]);
 const n=reg.nuit;A.comp.threshold.value=n?-40:0;A.comp.ratio.value=n?12:1;A.comp.knee.value=n?20:0;A.comp.attack.value=0.003;A.comp.release.value=0.25;
 A.mono.channelCount=reg.mono?1:2;A.mono.channelCountMode=reg.mono?'explicit':'max';A.mono.channelInterpretation='speakers'}
v.addEventListener('play',()=>{audio();if(A&&A.c.state==='suspended')A.c.resume()});
const eqBox=$('#eq');BANDES.forEach((f,i)=>{const d=document.createElement('div'),r=document.createElement('input');r.type='range';r.min=-12;r.max=12;r.value=reg.eq[i];r.oninput=()=>{reg.eq[i]=+r.value;reg.pre='perso';appliqueAudio()};d.append(r,document.createTextNode(f<1000?f:(f/1000)+'k'));eqBox.append(d)});
function syncReg(){$('#aVol').value=reg.vol;$('#aDia').value=reg.dia;$('#aNuit').checked=reg.nuit;$('#aBal').value=reg.bal;$('#aMono').checked=reg.mono;$('#aPre').value=PRE[reg.pre]?reg.pre:'plat';$('#aMoteur').value=reg.moteur;$$('#eq input').forEach((r,i)=>r.value=reg.eq[i]);appliqueAudio()}
$('#aVol').oninput=e=>{reg.vol=+e.target.value;appliqueAudio()};$('#aDia').oninput=e=>{reg.dia=+e.target.value;appliqueAudio()};
$('#aNuit').onchange=e=>{reg.nuit=e.target.checked;appliqueAudio()};$('#aBal').oninput=e=>{reg.bal=+e.target.value;appliqueAudio()};
$('#aMono').onchange=e=>{reg.mono=e.target.checked;appliqueAudio()};$('#aPre').onchange=e=>{reg.pre=e.target.value;reg.eq=PRE[reg.pre].slice();syncReg()};
$('#aMoteur').onchange=e=>{reg.moteur=e.target.value;ss('reg',reg);location.reload()};

/* ===== image ===== */
const img=Object.assign({lum:100,con:100,sat:100,fmt:'contain',zoom:100},ls('img',{}));
function appliqueImg(){ss('img',img);v.style.filter=`brightness(${img.lum}%) contrast(${img.con}%) saturate(${img.sat}%)`;v.style.objectFit=img.fmt;v.style.transform=`scale(${img.zoom/100})`}
[['#iLum','lum'],['#iCon','con'],['#iSat','sat'],['#iZoom','zoom']].forEach(([s,k])=>{$(s).value=img[k];$(s).oninput=e=>{img[k]=+e.target.value;appliqueImg()}});
$('#iFmt').value=img.fmt;$('#iFmt').onchange=e=>{img.fmt=e.target.value;appliqueImg()};
$('#iVit').onchange=e=>v.playbackRate=+e.target.value;
$('#iQual').onchange=e=>{if(hls)hls.currentLevel=+e.target.value};
$('#iPip').onclick=()=>{(document.pictureInPictureElement?document.exitPictureInPicture():v.requestPictureInPicture()).catch(()=>{})};
$('#iCap').onclick=()=>{try{const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);const a=document.createElement('a');a.href=c.toDataURL('image/png');a.download='capture_'+Date.now()+'.png';a.click()}catch(e){dire('Capture impossible sur ce flux.')}};
let ptA=null,ptB=null;$('#iA').onclick=()=>{ptA=v.currentTime;majAB()};$('#iB').onclick=()=>{ptB=v.currentTime;majAB()};$('#iAB0').onclick=()=>{ptA=ptB=null;majAB()};
function majAB(){$('#iABv').textContent=ptA!=null?'A '+ptA.toFixed(0)+'s'+(ptB!=null?' → B '+ptB.toFixed(0)+'s':''):''}
v.addEventListener('timeupdate',()=>{if(ptA!=null&&ptB!=null&&ptB>ptA&&v.currentTime>=ptB)v.currentTime=ptA});
$('#iSrt').onchange=async e=>{const f=e.target.files[0];if(!f)return;let t=await f.text();if(!/^WEBVTT/.test(t))t='WEBVTT\n\n'+t.replace(/\r/g,'').replace(/(\d\d:\d\d:\d\d),(\d\d\d)/g,'$1.$2');
 $$('#v track').forEach(x=>x.remove());const tr=document.createElement('track');tr.kind='subtitles';tr.label='FR';tr.srclang='fr';tr.default=true;tr.src=URL.createObjectURL(new Blob([t],{type:'text/vtt'}));v.append(tr);setTimeout(()=>{if(v.textTracks[0])v.textTracks[0].mode='showing'},100);dire('Sous-titres chargés : '+f.name)};

/* ===== sommeil ===== */
let dodoT=null;
function dodo(min){clearInterval(dodoT);$('#dodoV').textContent='';if(!min){dire('Minuterie de sommeil coupée.');return}
 const fin=Date.now()+min*60000,base=reg.vol;dire('Je baisse le son en douceur et je coupe dans '+min+' min.');
 dodoT=setInterval(()=>{const r=fin-Date.now();$('#dodoV').textContent=Math.ceil(r/60000)+' min';
  if(r<120000&&r>0){const k=r/120000;if(A)A.gain.gain.value=base/100*k;else v.volume=Math.min(1,base/100)*k}
  if(r<=0){clearInterval(dodoT);v.pause();$('#dodoV').textContent='';if(A)A.gain.gain.value=base/100;else v.volume=Math.min(1,base/100);dire('Lecture arrêtée. Les enregistrements en cours continuent.')}},5000)}
$$('[data-dodo]').forEach(b=>b.onclick=()=>dodo(+b.dataset.dodo));

/* ===== assistant RÉTRO ===== */
const AIDE='Exemples : « France 2 », « chaîne 7 », « du jazz », « une radio calme », « un film », « mes favoris », « suggestions », « enregistre », « stop enregistrement », « pause », « reprends », « plus fort », « moins fort », « dialogues », « mode nuit », « dodo 30 », « YouTube », « Kodi ».';
function trouve(q,type){q=q.toLowerCase().trim();if(!q)return null;
 const pools=type==='radio'?[listeRadio()]:type==='tv'?[listeTV()]:type==='video'?[videos]:[Object.values(favs),listeTV(),listeRadio(),videos];
 for(const P of pools){const x=P.find(x=>x.n.toLowerCase()===q);if(x)return x}
 for(const P of pools){const x=P.find(x=>x.n.toLowerCase().includes(q));if(x)return x}
 const mots=q.split(/\s+/).filter(m=>m.length>2);for(const P of pools){const x=P.find(x=>mots.length&&mots.every(m=>(x.n+' '+(x.s||'')).toLowerCase().includes(m)));if(x)return x}return null}
async function joueRecherche(q,type){let x=trouve(q,type);
 if(!x&&type!=='tv'&&type!=='video'){let r=await chercheRadios('limit=200&tag='+encodeURIComponent(q.toLowerCase()));if(!r.length)r=await chercheRadios('limit=200&name='+encodeURIComponent(q));if(r.length){radio=[...r,...radio.filter(y=>!r.some(z=>z.u===y.u))];numerote();x=r[0]}}
 if(x){joue(x);return x}return null}
function reflexe(t){const s=t.toLowerCase().trim();let m;
 if(/^(aide|help|\?)$/.test(s))return dire(AIDE),true;
 if((m=s.match(/^(?:cha[iî]ne|radio|num[eé]ro)?\s*(\d{1,3})$/))){const x=parNum(+m[1]);x?joue(x):dire('Pas de n° '+m[1]+'.');return true}
 if(/stop.*enregistr|arr[eê]te.*enregistr|stop rec/.test(s))return arreteRec(recCourant()||recs[recs.length-1]),true;
 if(/^(enregistre|rec\b|record)/.test(s))return demarreRec(cur),true;
 if(/^(pause|stop|arr[eê]te)/.test(s))return v.pause(),dire('En pause.'),true;
 if(/^(reprend|lecture|play|continue)/.test(s))return v.play(),dire('Je reprends.'),true;
 if(/plus fort|monte le son/.test(s))return reg.vol=Math.min(300,reg.vol+20),syncReg(),dire('Volume '+reg.vol+'%.'),true;
 if(/moins fort|baisse le son/.test(s))return reg.vol=Math.max(0,reg.vol-20),syncReg(),dire('Volume '+reg.vol+'%.'),true;
 if(/dialogue/.test(s))return reg.dia=reg.dia?0:8,syncReg(),dire(reg.dia?'Dialogues renforcés.':'Dialogues normaux.'),true;
 if(/mode nuit/.test(s))return reg.nuit=!reg.nuit,syncReg(),dire(reg.nuit?'Mode nuit actif.':'Mode nuit coupé.'),true;
 if((m=s.match(/(dodo|dors|sommeil)\D*(\d+)?/)))return dodo(+(m[2]||30)),true;
 if(/youtube|freetube/.test(s))return R.lancer('freetube').then(ok=>dire(ok?'FreeTube lancé.':'FreeTube introuvable.')),true;
 if(/\bkodi\b/.test(s))return R.lancer('kodi').then(ok=>dire(ok?'Kodi lancé.':'Kodi introuvable.')),true;
 if(/suggestion|propose/.test(s))return va('accueil'),dire('Regarde la rangée « Suggestions ».'),true;
 if(/favori/.test(s))return va('accueil'),dire('Tes favoris sont sur l\'accueil.'),true;
 return false}
async function cerveau(t){
 const sys=`Tu es ${conf.nom}, l'assistant télé-radio de René, en français, bref et chaleureux. Il est ${new Date().toLocaleTimeString('fr-FR',{hour:'2-digit',minute:'2-digit'})}.
En cours : ${cur?cur.t+' n°'+cur.num+' « '+cur.n+' »':'rien'}. Favoris : ${Object.values(favs).slice(0,15).map(x=>x.n).join(', ')||'aucun'}.
Réponds UNIQUEMENT en JSON : {"action":"jouer|info|parler","type":"tv|radio|video|tout","requete":"nom de chaîne/radio, ou un genre musical en un mot (jazz, classique, rock, info, ambient…)","reponse":"une phrase pour René"}.
"jouer" s'il veut écouter ou regarder. "info" s'il demande ce qu'il voit ou écoute : reste prudent, n'invente rien. Sinon "parler".`;
 const r=await R.qwen({url:conf.oll,model:conf.mod,messages:[{role:'system',content:sys},{role:'user',content:t}]});
 if(r.err)return null;try{return JSON.parse(r.txt)}catch(e){return null}}
async function commande(t){if(!t.trim())return;dire(t,true);if(reflexe(t))return;
 const m=t.match(/^(mets|lance|joue|[eé]coute|regarde)\s+(.+)/i);const j=await cerveau(t);
 if(j){if(j.reponse)dire(j.reponse);if(j.action==='jouer'){const x=await joueRecherche(j.requete||t,j.type);if(!x)dire('Rien trouvé pour « '+(j.requete||t)+' ».')}return}
 dire('(cerveau Qwen hors ligne : mode mots-clés)');const x=await joueRecherche(m?m[2]:t,'tout');dire(x?'Je lance « '+x.n+' ».':'Rien trouvé. Tape « aide ».')}
$('#in').onkeydown=e=>{e.stopPropagation();if(e.key==='Enter'){const t=e.target.value;e.target.value='';commande(t)}};
$('#retroTete').onclick=()=>{$('#retro').classList.toggle('ouvert');$('#retroFl').textContent=$('#retro').classList.contains('ouvert')?'▼':'▲'};

/* ===== navigation, clavier, config ===== */
function va(p){page=p;$$('nav button').forEach(b=>b.classList.toggle('on',b.dataset.p===p));$$('.page').forEach(d=>d.classList.toggle('on',d.id==='p-'+p));
 if(p==='k7')chargeK7();if(p==='prog')rendProgs();if(p==='conf')rendConf()}
$$('nav button').forEach(b=>b.onclick=()=>va(b.dataset.p));
let qT=null;$('#q').oninput=()=>{clearTimeout(qT);qT=setTimeout(rendTout,200)};$('#q').onkeydown=e=>e.stopPropagation();
$('#bMonde').onclick=async()=>{const q=$('#q').value.trim();if(!q){dire('Tape d\'abord un nom ou un genre dans la recherche.');return}let r=await chercheRadios('limit=500&name='+encodeURIComponent(q));if(!r.length)r=await chercheRadios('limit=500&tag='+encodeURIComponent(q.toLowerCase()));radio=[...r,...radio.filter(y=>!r.some(z=>z.u===y.u))];numerote();rendTout();dire(r.length+' radios trouvées dans le monde pour « '+q+' ».')};
const fileIn=document.createElement('input');fileIn.type='file';fileIn.multiple=true;fileIn.accept='video/*,audio/*';
fileIn.onchange=()=>{for(const x of fileIn.files)videos.push({t:'video',n:x.name,u:URL.createObjectURL(x),s:(x.size/1e6).toFixed(0)+' Mo'});numerote();rendTout();dire(fileIn.files.length+' vidéo(s) ajoutée(s).')};
$('#bOuvrir').onclick=()=>fileIn.click();
$$('[data-lance]').forEach(b=>b.onclick=async()=>{const ok=await R.lancer(b.dataset.lance);dire(ok?b.textContent.trim()+' : lancé.':'Logiciel introuvable : relance l\'installation.')});
document.addEventListener('keydown',e=>{if(e.target.tagName==='INPUT'||e.target.tagName==='SELECT')return;const on=$('#lecteur').classList.contains('on');
 if(/^\d$/.test(e.key)){tapeNum(e.key);return}
 if(!on)return;montreBarre();
 if(e.key==='ArrowUp'||e.key==='PageUp'){e.preventDefault();zappe(1)}else if(e.key==='ArrowDown'||e.key==='PageDown'){e.preventDefault();zappe(-1)}
 else if(e.key===' '){e.preventDefault();v.paused?v.play():v.pause()}else if(e.key==='Escape'){if(!document.fullscreenElement)fermeLecteur()}
 else if(e.key==='r'||e.key==='R')demarreRec(cur);else if(e.key==='s'||e.key==='S')arreteRec(recCourant());else if(e.key==='f'||e.key==='F')$('#bPlein').click()});
async function rendConf(){$('#tvurl').value=ls('tvurl',TV_DEF);$('#cNom').value=conf.nom;$('#cOll').value=conf.oll;$('#cMod').value=conf.mod;
 const l=await R.logiciels();$('#logi').innerHTML=['vlc','freetube','kodi'].map(k=>`<div class="ligne">${l[k]?'✅':'❌'} ${{vlc:'VLC (lecture de secours + magnétoscope)',freetube:'FreeTube (YouTube sans pub)',kodi:'Kodi (médiathèque)'}[k]} ${l[k]&&k!=='vlc'?`<button data-l="${k}">Ouvrir</button>`:''}</div>`).join('');
 $$('#logi [data-l]').forEach(b=>b.onclick=()=>R.lancer(b.dataset.l));
 const pl=$('#pl');pl.innerHTML='';perso.forEach((p,i)=>{const d=document.createElement('div');d.className='k7';d.innerHTML='<span class="etiq">'+echap((p.t==='tv'?'[TV] ':'[RADIO] ')+p.n+' — '+p.u)+'</span>';const b=document.createElement('button');b.textContent='Supprimer';b.onclick=()=>{perso.splice(i,1);ss('perso',perso);numerote();rendTout();rendConf()};d.append(b);pl.append(d)})}
$('#cSave').onclick=()=>{conf={nom:$('#cNom').value.trim()||'RÉTRO',oll:$('#cOll').value.trim(),mod:$('#cMod').value.trim()};ss('conf',conf);$('#nomia').textContent=conf.nom;dire('Configuration enregistrée. Je m\'appelle '+conf.nom+'.')};
$('#padd').onclick=()=>{const n=$('#pn').value.trim(),u=$('#pu').value.trim();if(!n||!/^https?:\/\//.test(u))return dire('Il faut un nom et une adresse http.');perso.push({t:$('#pt').value,n,u,s:'perso'});ss('perso',perso);$('#pn').value=$('#pu').value='';numerote();rendTout();rendConf()};
$('#tvsave').onclick=()=>{ss('tvurl',$('#tvurl').value.trim()||TV_DEF);chargeTV()};$('#tvdef').onclick=()=>{ss('tvurl',TV_DEF);rendConf();chargeTV()};
$('#exp').onclick=()=>{const b=new Blob([JSON.stringify({favs,perso,conf,reg,img,progs,tvurl:ls('tvurl',TV_DEF)},null,1)],{type:'application/json'});const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='rene-tv-reglages.json';a.click()};
$('#imp').onchange=async e=>{try{const j=JSON.parse(await e.target.files[0].text());['favs','perso','conf','reg','img','progs'].forEach(k=>j[k]&&ss(k,j[k]));if(j.tvurl)ss('tvurl',j.tvurl);location.reload()}catch(x){dire('Fichier de réglages illisible.')}};

/* ===== démarrage ===== */
syncReg();appliqueImg();
const dt=new Date(Date.now()+3600000);dt.setMinutes(0,0,0);$('#prDeb').value=new Date(dt-dt.getTimezoneOffset()*60000).toISOString().slice(0,16);
R.gpu().then(g=>{$('#gpu').textContent='Décodage vidéo GPU : '+(g.video_decode||'?')+' · Rendu : '+(g.gpu_compositing||'?')+' · WebGL : '+(g.webgl||'?')}).catch(()=>{});
dire('Système prêt. Je suis '+conf.nom+'. Tape un numéro pour zapper, ou « aide ».');
rendTout();chargeTV();chargeRadio();chargeK7();
</script></body></html>
EOF_F3
[ "$DRY" = 1 ] && exit 0
echo ">> Installation des logiciels gratuits (VLC, FreeTube, Kodi) via winget…"
for id in VideoLAN.VLC FreeTube.FreeTube XBMCFoundation.Kodi; do (cd /mnt/c && cmd.exe /c "winget install -e --id $id --silent --accept-package-agreements --accept-source-agreements") || echo "   ($id : deja installe ou a refaire)"; done
echo ">> Construction de René TV…"
npm install --no-audit --no-fund hls.js >/dev/null && cp node_modules/hls.js/dist/hls.min.js .
ELECTRON_SKIP_BINARY_DOWNLOAD=1 npm install --no-audit --no-fund -D electron >/dev/null
WH=$(wslpath "$(cd /mnt/c && cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')")
npx --yes @electron/packager . Rene-TV --platform=win32 --arch=x64 --out "$WH/Applications-Rene" --overwrite --ignore=node_modules >/dev/null
EXE="$WH/Applications-Rene/Rene-TV-win32-x64/Rene-TV.exe"; EXEW=$(wslpath -w "$EXE")
(cd /mnt/c && powershell.exe -NoProfile -Command "\$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\\Rene TV.lnk');\$s.TargetPath='$EXEW';\$s.Save()")
sha256sum main.js preload.js index.html | cut -c1-16
echo "OK v3 : $EXEW  + raccourci « Rene TV » sur le bureau"

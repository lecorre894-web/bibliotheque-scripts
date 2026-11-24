const { app, BrowserWindow, ipcMain, shell, powerSaveBlocker } = require('electron');
const path = require('path'), fs = require('fs'), http = require('http'), https = require('https');
app.commandLine.appendSwitch('ignore-gpu-blocklist');
app.commandLine.appendSwitch('enable-gpu-rasterization');
app.commandLine.appendSwitch('enable-zero-copy');
// v3.3-HD : Super Résolution vidéo NVIDIA (RTX VSR) + HDR vidéo côté moteur, et toujours la carte graphique puissante
app.commandLine.appendSwitch('enable-features', 'NvidiaVpSuperResolution,NvidiaVpTrueHDR');
app.commandLine.appendSwitch('force_high_performance_gpu'); // v3.7.5 : vsync normal = 240 Hz
if (process.platform === 'win32') { try { require('child_process').spawn('reg', ['add', 'HKCU\\Software\\Microsoft\\DirectX\\UserGpuPreferences', '/v', process.execPath, '/t', 'REG_SZ', '/d', 'GpuPreference=2;', '/f'], { stdio: 'ignore', windowsHide: true }); } catch (e) {} }
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

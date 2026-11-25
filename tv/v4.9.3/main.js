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
/*v4.6-ff*/
const os = require('os');
const FFD = path.join(os.tmpdir(), 'renetv-ff');
const trouveFF = () => {
  const c = [];
  if (LAD) {
    c.push(path.join(LAD, 'Microsoft', 'WinGet', 'Links', 'ffmpeg.exe'));
    try { const P = path.join(LAD, 'Microsoft', 'WinGet', 'Packages'); for (const d of fs.readdirSync(P).filter(d => /^Gyan\.FFmpeg/i.test(d))) for (const s of fs.readdirSync(path.join(P, d))) c.push(path.join(P, d, s, 'bin', 'ffmpeg.exe')); } catch (e) {}
  }
  if (PF) c.push(path.join(PF, 'ffmpeg', 'bin', 'ffmpeg.exe'));
  return trouveExe(c) || 'ffmpeg';
};
const FFV = {
  doux: 'bwdif=mode=0:deint=1,hqdn3d=2:1.5:3:3,deblock=filter=weak:block=8,deband=1thr=0.015:2thr=0.015:3thr=0.015:range=16:blur=1',
  fort: 'bwdif=mode=0:deint=1,hqdn3d=4:3:6:4.5,deblock=filter=strong:block=8,deband=1thr=0.02:2thr=0.02:3thr=0.02:range=20:blur=1',
  ia: "bwdif=mode=0:deint=1,hqdn3d=3:5:4:6,deblock=filter=strong:block=8:alpha=0.12:beta=0.07:gamma=0.05:delta=0.05,libplacebo=w='if(lt(ih\\,1100)\\,iw*2\\,iw)':h='if(lt(ih\\,1100)\\,ih*2\\,ih)':upscaler=ewa_lanczossharp:deband=1:deband_iterations=2:deband_threshold=5:deband_radius=24:custom_shader_path=FSRCNNX_x2_8-0-4-1.glsl:format=yuv420p,hwdownload,format=yuv420p",
  max: "bwdif=mode=0:deint=1,hqdn3d=3:5:4:6,deblock=filter=strong:block=8:alpha=0.12:beta=0.07:gamma=0.05:delta=0.05,libplacebo=w='if(lt(ih\\,1100)\\,iw*2\\,iw)':h='if(lt(ih\\,1100)\\,ih*2\\,ih)':upscaler=ewa_lanczossharp:deband=1:deband_iterations=2:deband_threshold=5:deband_radius=24:custom_shader_path=FSRCNNX_x2_16-0-4-1.glsl:format=yuv420p,hwdownload,format=yuv420p",
  s8k: "bwdif=mode=0:deint=1,hqdn3d=3:5:4:6,deblock=filter=strong:block=8:alpha=0.12:beta=0.07:gamma=0.05:delta=0.05,libplacebo=w='if(lt(ih\\,1100)\\,iw*2\\,iw)':h='if(lt(ih\\,1100)\\,ih*2\\,ih)':upscaler=ewa_lanczossharp:deband=1:custom_shader_path=FSRCNNX_x2_16-0-4-1.glsl,libplacebo=w=iw*2:h=ih*2:upscaler=ewa_lanczossharp:custom_shader_path=FSRCNNX_x2_8-0-4-1.glsl,libplacebo=w=-2:h=2160:downscaler=ewa_lanczos:format=yuv420p,hwdownload,format=yuv420p"
};
const SHD = LAD ? path.join(LAD, 'ReneTV') : os.tmpdir();
const iaOK = () => fs.existsSync(path.join(SHD, 'FSRCNNX_x2_8-0-4-1.glsl'));
const maxOK = () => iaOK() && fs.existsSync(path.join(SHD, 'FSRCNNX_x2_16-0-4-1.glsl'));
let ffP = null, ffSrv = null, ffPort = 0, ffN = 0;
const ffStop = () => { if (ffP) { try { ffP.kill('SIGKILL'); } catch (e) {} ffP = null; } };
const ffServeur = () => new Promise(ok => {
  if (ffSrv) return ok(ffPort);
  ffSrv = http.createServer((q, r) => {
    const f = path.join(FFD, path.normalize(decodeURIComponent(q.url.split('?')[0])).replace(/^([\\/]|\.\.)+/, ''));
    if (!f.startsWith(FFD)) { r.writeHead(403); return r.end(); }
    fs.readFile(f, (e, b) => {
      if (e) { r.writeHead(404, { 'Access-Control-Allow-Origin': '*' }); return r.end(); }
      r.writeHead(200, { 'Content-Type': f.endsWith('.m3u8') ? 'application/vnd.apple.mpegurl' : 'video/mp2t', 'Cache-Control': 'no-store', 'Access-Control-Allow-Origin': '*' });
      r.end(b);
    });
  });
  ffSrv.listen(0, '127.0.0.1', () => { ffPort = ffSrv.address().port; ok(ffPort); });
});
const ffLance = (url, vf, enc, dir) => {
  const a = ['-hide_banner', '-loglevel', 'error'];
  if (/^https?:/i.test(url)) a.push('-user_agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124 Safari/537.36');
  if (/^https?:/i.test(url) && !/\.m3u8(\?|$)/i.test(url)) a.push('-reconnect', '1', '-reconnect_streamed', '1', '-reconnect_delay_max', '5');
  if (!/^https?:/i.test(url)) a.push('-re');
  if (enc === 'nvenc') a.push('-hwaccel', 'cuda');
  if (/libplacebo/.test(vf)) a.push('-init_hw_device', 'vulkan=vk', '-filter_hw_device', 'vk');
  a.push('-i', url, '-sn', '-dn', '-vf', vf);
  if (enc === 'nvenc') a.push('-c:v', 'h264_nvenc', '-preset', 'p5', '-tune', 'hq', '-rc', 'vbr', '-cq', '18', '-b:v', /libplacebo/.test(vf) ? '45M' : '25M', '-maxrate', '60M', '-bufsize', '60M', '-g', '50', '-bf', '0');
  else a.push('-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-g', '50', '-bf', '0');
  a.push('-c:a', 'aac', '-b:a', '192k', '-f', 'hls', '-hls_time', '1', '-hls_list_size', '8', '-hls_flags', 'delete_segments+independent_segments+omit_endlist', path.join(dir, 'index.m3u8'));
  return spawn(trouveFF(), a, { windowsHide: true, cwd: SHD, stdio: ['ignore', 'ignore', 'pipe'] });
};
const ffAttend = (p, f, ms) => new Promise(ok => {
  const t0 = Date.now(); let fini = false; p.on('exit', () => { fini = true; }); p.on('error', () => { fini = true; });
  const tic = () => {
    if (fini) return ok(false);
    try { if ((fs.readFileSync(f, 'utf8').match(/\.ts/g) || []).length >= 2) return ok(true); } catch (e) {}
    if (Date.now() - t0 > ms) return ok(false);
    setTimeout(tic, 250);
  };
  tic();
});
ipcMain.handle('ff-start', async (_e, url, niv, ro) => {
  if ((niv === 'max' || niv === 's8k') && !maxOK()) niv = 'ia';
  ffStop();
  let vf = FFV[niv]; if (!vf || !/^https?:|^file:/i.test(url)) return null;
  const port = await ffServeur(); const id = 'c' + (++ffN) + '_' + Date.now(); const dir = path.join(FFD, id);
  try { fs.rmSync(FFD, { recursive: true, force: true }); } catch (e) {}
  fs.mkdirSync(dir, { recursive: true }); try { fs.mkdirSync(SHD, { recursive: true }); } catch (e) {}
  const src = url.replace(/^file:\/\//i, '').replace(/^\/([A-Za-z]:)/, '$1');
  if ((niv === 'max' || niv === 's8k') && !maxOK()) niv = 'ia';
  const essais = niv === 's8k' ? [['nvenc', FFV.s8k], ['nvenc', FFV.max], ['nvenc', FFV.ia], ['x264', FFV.ia], ['nvenc', FFV.fort], ['x264', FFV.fort]] : niv === 'max' ? [['nvenc', FFV.max], ['nvenc', FFV.ia], ['x264', FFV.ia], ['nvenc', FFV.fort], ['x264', FFV.fort]] : niv === 'ia' && iaOK() ? [['nvenc', FFV.ia], ['x264', FFV.ia], ['nvenc', FFV.fort], ['x264', FFV.fort]] : [['nvenc', niv === 'ia' ? FFV.fort : vf], ['x264', niv === 'ia' ? FFV.fort : vf]];
  for (const [enc, f] of essais) {
    const p = ffLance(/^file:/i.test(url) ? decodeURIComponent(src) : url, compose(f, ro), enc, dir); ffP = p;
    let err = ''; p.stderr.on('data', d => { err = (err + d).slice(-400); });
    p.on('error', () => {});
    if (await ffAttend(p, path.join(dir, 'index.m3u8'), 20000)) { if (ffP !== p) { try { p.kill('SIGKILL'); } catch (e) {} return null; } return 'http://127.0.0.1:' + port + '/' + id + '/index.m3u8?m=' + (f === FFV.s8k ? 's8k' : f === FFV.max ? 'max' : /libplacebo/.test(f) ? 'ia' : 'std'); }
    try { p.kill('SIGKILL'); } catch (e) {} if (ffP === p) ffP = null; else return null;
    console.log('[ff] ' + enc + (f === FFV.s8k ? '+s8k' : f === FFV.max ? '+max' : /libplacebo/.test(f) ? '+ia' : '') + ' échec : ' + err);
    try { fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true }); } catch (e) {}
  }
  return null;
});
ipcMain.handle('ff-stop', () => { ffStop(); return true; });
ipcMain.handle('ff-ok', () => { const e = trouveFF(); return e !== 'ffmpeg' ? e : null; });
/*v4.8-ret*/
const RETS = { film: 'deflicker=size=5,curves=preset=increase_contrast,vibrance=intensity=0.15', cine: 'curves=preset=medium_contrast,colorbalance=rs=-0.04:bs=0.06:rh=0.06:bh=-0.04,vibrance=intensity=0.1', vintage: 'curves=preset=vintage', portrait: 'bilateral=sigmaS=3:sigmaR=0.06,colorbalance=rm=0.03:bm=-0.02,vibrance=intensity=0.08' };
const retouche = o => {
  o = o || {}; const f = []; const n = (v, a, b) => Math.max(a, Math.min(b, +v || 0));
  if (RETS[o.style]) f.push(RETS[o.style]);
  const L = [0, 'bilateral=sigmaS=2:sigmaR=0.05', 'bilateral=sigmaS=3:sigmaR=0.08', 'bilateral=sigmaS=4:sigmaR=0.12'][n(o.lis, 0, 3) | 0]; if (L) f.push(L);
  if (o.wb) f.push('normalize=smoothing=40:independence=0.6:strength=0.3');
  if (n(o.cla, 0, 100) > 0) f.push('unsharp=13:13:' + (n(o.cla, 0, 100) / 100 * 1.2).toFixed(2) + ':5:5:0');
  if (n(o.vib, 0, 100) > 0) f.push('vibrance=intensity=' + (n(o.vib, 0, 100) / 100 * 0.6).toFixed(2));
  if (o.lut && fs.existsSync(path.join(SHD, 'ma.cube'))) f.push('lut3d=file=ma.cube');
  if (o.lut && fs.existsSync(path.join(SHD, 'ma.acv'))) f.push('curves=psfile=ma.acv');
  if (n(o.cas, 0, 100) > 0) f.push('cas=strength=' + (n(o.cas, 0, 100) / 100).toFixed(2));
  return f.join(',');
};
const compose = (vf, o) => {
  const r = retouche(o); let s = vf;
  if (r) { const i = s.indexOf(',libplacebo'); s = i >= 0 ? s.slice(0, i) + ',' + r + s.slice(i) : s + ',' + r; }
  if (o && o.vsr && /libplacebo/.test(s)) s += ",scale=-2:'min(ih,1440)':flags=lanczos";
  return s;
};
ipcMain.handle('ff-dossier', () => { try { fs.mkdirSync(SHD, { recursive: true }); } catch (e) {} shell.openPath(SHD); return SHD; });

app.on('before-quit', () => { ffStop(); try { fs.rmSync(FFD, { recursive: true, force: true }); } catch (e) {} });
/*v4.9-tele*/
const TPORT = 8765; let tEtat = {}, tPin = null, tSrv = null;
const tPinF = () => { if (tPin) return tPin; const f = path.join(app.getPath('userData'), 'tele.json'); try { tPin = JSON.parse(fs.readFileSync(f, 'utf8')).pin; } catch (e) {} if (!tPin) { tPin = String(1000 + Math.floor(Math.random() * 9000)); try { fs.writeFileSync(f, JSON.stringify({ pin: tPin })); } catch (e) {} } return tPin; };
const tWin = () => { const W = BrowserWindow.getAllWindows(); return W.find(x => /index\.html/.test(x.webContents.getURL())) || W[0]; };
const tIPs = () => { const r = []; /*v4.9.2*/for (const [nm, l] of Object.entries(require('os').networkInterfaces())) if (!/vEthernet|WSL|Hyper-V|VirtualBox|VMware|Loopback/i.test(nm)) for (const a of l || []) if (a.family === 'IPv4' && !a.internal) r.push(a.address); return r; };
app.whenReady().then(() => {
  tSrv = http.createServer((q, r) => {
    const u = new URL(q.url, 'http://x'), ok = u.searchParams.get('k') === tPinF();
    if (u.pathname === '/') {
      if (!ok) { r.writeHead(403, { 'Content-Type': 'text/html; charset=utf-8' }); return r.end('<h2 style="font-family:sans-serif">Code manquant ou faux : tape l\'adresse affichée dans René TV (Son & image).</h2>'); }
      return fs.readFile(path.join(__dirname, 'tele.html'), (e, b) => { r.writeHead(e ? 500 : 200, { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' }); r.end(b || ''); });
    }
    if (u.pathname === '/c') {
      r.setHeader('Content-Type', 'application/json; charset=utf-8'); r.setHeader('Cache-Control', 'no-store');
      if (!ok) { r.statusCode = 403; return r.end('{"err":"code faux"}'); }
      const c = String(u.searchParams.get('c') || '').slice(0, 40), w = tWin();
      if (!w) return r.end('{"err":"René TV fermé"}');
      if (c === 'plein') w.setFullScreen(!w.isFullScreen()); else if (c !== 'etat') w.webContents.send('tele', c);
      return setTimeout(() => r.end(JSON.stringify(tEtat)), c === 'etat' ? 0 : 300);
    }
    if (u.pathname === '/liste') { /*v4.9.1*/ r.setHeader('Content-Type', 'application/json; charset=utf-8'); if (!ok) { r.statusCode = 403; return r.end('[]'); } const w = tWin(); if (!w) return r.end('[]'); return w.webContents.executeJavaScript("JSON.stringify([...listeTV(),...listeRadio()].map(x=>({n:x.num,t:x.t,nom:x.n,logo:x.logo||''})))").then(s => r.end(s)).catch(() => r.end('[]')); }
    r.statusCode = 404; r.end();
  });
  tSrv.on('error', e => console.log('[tele] ' + e.message));
  tSrv.listen(TPORT, '0.0.0.0');
});
ipcMain.on('tele-etat', (_e, s) => { tEtat = s || {}; });
ipcMain.handle('tele-info', () => ({ pin: tPinF(), urls: tIPs().map(ip => 'http://' + ip + ':' + TPORT + '/?k=' + tPinF()) }));
app.on('before-quit', () => { try { tSrv && tSrv.close(); } catch (e) {} });



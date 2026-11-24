# René TV v3.3 : très haute définition (meilleure qualité verrouillée, résolution affichée, RTX Video Super Resolution + carte RTX forcée)
import sys,os,hashlib
D=os.path.expanduser(sys.argv[1] if len(sys.argv)>1 else '~/rene-tv')
h=lambda s:hashlib.sha256(s.encode()).hexdigest()[:16]
def P(f,rep):
    p=os.path.join(D,f);s=open(p,encoding='utf-8').read()
    if 'v3.3-HD' in s:print(f,'deja en v3.3',h(s));return
    for a,b in rep:
        if s.count(a)!=1:print('ECHEC',f,'motif introuvable :',a[:60]);sys.exit(1)
        s=s.replace(a,b)
    open(p,'w',encoding='utf-8').write(s);print('OK',f,h(s))
P('main.js',[("app.commandLine.appendSwitch('enable-zero-copy');","""app.commandLine.appendSwitch('enable-zero-copy');
// v3.3-HD : Super Résolution vidéo NVIDIA (RTX VSR) + HDR vidéo côté moteur, et toujours la carte graphique puissante
app.commandLine.appendSwitch('enable-features', 'NvidiaVpSuperResolution,NvidiaVpTrueHDR');
app.commandLine.appendSwitch('force_high_performance_gpu');
if (process.platform === 'win32') { try { require('child_process').spawn('reg', ['add', 'HKCU\\\\Software\\\\Microsoft\\\\DirectX\\\\UserGpuPreferences', '/v', process.execPath, '/t', 'REG_SZ', '/d', 'GpuPreference=2;', '/f'], { stdio: 'ignore', windowsHide: true }); } catch (e) {} }""")])
P('index.html',[("new Hls({capLevelToPlayerSize:false})","new Hls({capLevelToPlayerSize:false,abrEwmaDefaultEstimate:50e6,maxBufferLength:60}/*v3.3-HD*/)"),
("if(hls.levels.length){hls.currentLevel=hls.levels.length-1;q.value=hls.levels.length-1}","if(hls.levels.length){const L=hls.levels,best=L.reduce((b,l,i)=>((l.height||0)*1e9+(l.bitrate||0))>((L[b].height||0)*1e9+(L[b].bitrate||0))?i:b,0);hls.currentLevel=best;q.value=best}"),
("+(cur.t==='tv'&&cur.s?'  '+cur.s:''))});","+(w&&h?(()=>{const E=Math.round(screen.width*devicePixelRatio),F=Math.round(screen.height*devicePixelRatio);return '  → écran '+E+'×'+F+(E>w*1.05?' · RTX ×'+(E/w).toFixed(1):' · natif')})():'')+(cur.t==='tv'&&cur.s?'  '+cur.s:''))});")])

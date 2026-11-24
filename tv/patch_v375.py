# René TV v3.7.5 : retrait des deux réglages d Electron qui bridaient à ~100 Hz (Test Hz 5 : 240 Hz sans eux) + limiteur assoupli
import sys,os,hashlib
D=os.path.expanduser(sys.argv[1] if len(sys.argv)>1 else '~/rene-tv')
m=os.path.join(D,'main.js');t=open(m,encoding='utf-8').read()
if 'v3.7.5' in t:print('main.js deja en v3.7.5')
else:
    L=t.split('\n');n=len(L);L=[x for x in L if "appendSwitch('disable-frame-rate-limit')" not in x and "appendSwitch('disable-gpu-vsync')" not in x]
    if n-len(L)!=2:print('ECHEC : lignes v3.7.1/v3.7.2 introuvables ('+str(n-len(L))+')');sys.exit(1)
    t='\n'.join(L).replace("app.commandLine.appendSwitch('force_high_performance_gpu');","app.commandLine.appendSwitch('force_high_performance_gpu'); // v3.7.5 : vsync normal = 240 Hz",1)
    open(m,'w',encoding='utf-8').write(t);print('OK main.js v3.7.5',hashlib.sha256(t.encode()).hexdigest()[:16])
p=os.path.join(D,'index.html');s=open(p,encoding='utf-8').read()
if '/*v3.7.5*/' in s:print('index.html deja en v3.7.5')
else:
    a="if(now-derD<4)return;"
    if s.count(a)!=1 or '/*v3.7.4*/' not in s:print('ECHEC : installe d abord la v3.7.4');sys.exit(1)
    s=s.replace(a,"if(now-derD<2)return;").replace('/*v3.7.4*/','/*v3.7.4*//*v3.7.5*/',1)
    open(p,'w',encoding='utf-8').write(s);print('OK index.html v3.7.5',hashlib.sha256(s.encode()).hexdigest()[:16])

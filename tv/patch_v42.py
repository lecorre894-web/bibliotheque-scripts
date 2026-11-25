# René TV v4.2 : analyse du mouvement évolutive sans IA (480 → 640 → 960 → 1280 px tant que les 240 Hz tiennent), IA coupée et mémorisée si la carte ne suit pas
import sys,os,hashlib
p=os.path.join(os.path.expanduser(sys.argv[1] if len(sys.argv)>1 else '~/rene-tv'),'index.html');s=open(p,encoding='utf-8').read()
if '/*v4.2*/' in s:print('deja en v4.2');sys.exit()
if '/*v4.1*/' not in s:print('ECHEC : installe d abord la v4.1');sys.exit(1)
R=[("if(!SR.on||!SR.pret){if(NV!==0&&SR.on===false){NV=0;ANA=480;REA=1}return}",
"if(now<gvSk)return;if(!SR.on||!SR.pret){NV=0;const AN=[480,640,960,1280];const i=AN.indexOf(ANA);if(i<0){ANA=480;REA=1;gvSk=now+3000;return}\n if(af<200){if(i>0){ANA=AN[i-1];REA=1;gvUp=now+10000;gvSk=now+3000}}else if(af>=228&&now>gvUp&&i<AN.length-1&&AN[i+1]<=W+1){ANA=AN[i+1];REA=1;gvUp=now+6000;gvSk=now+3000}return}"),
("let NV=1,ANA=640,","let gvSk=0,NV=1,ANA=480,"),
("srCoupe('carte trop chargée même au niveau 1');","try{localStorage.setItem('fluSR','0')}catch(e){}srCoupe('carte trop chargée même au niveau 1');"),
("/*v4.1*/","/*v4.1*//*v4.2*/")]
for a,b in R:
    if s.count(a)!=1:print('ECHEC motif :',a[:50]);sys.exit(1)
    s=s.replace(a,b,1)
open(p,'w',encoding='utf-8').write(s);print('OK index.html v4.2',hashlib.sha256(s.encode()).hexdigest()[:16])

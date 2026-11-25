import sys,os,json,hashlib
d=sys.argv[1];R=json.loads('[["main.js", "  max: \\"bwdif=mode=0:deint=1,hqdn3d=2:1.5:3:3,deblock=filter=weak:block=8,libplacebo=w=\'if(lt(ih\\\\\\\\,1100)\\\\\\\\,iw*2\\\\\\\\,iw)\':h=\'if(lt(ih\\\\\\\\,1100)\\\\\\\\,ih*2\\\\\\\\,ih)\':upscaler=ewa_lanczossharp:deband=1:custom_shader_path=FSRCNNX_x2_16-0-4-1.glsl,libplacebo=w=iw*2:h=ih*2:upscaler=ewa_lanczossharp:custom_shader_path=FSRCNNX_x2_8-0-4-1.glsl,libplacebo=w=-2:h=2160:downscaler=ewa_lanczos:format=yuv420p,hwdownload,format=yuv420p\\"\\n", "  max: \\"bwdif=mode=0:deint=1,hqdn3d=2:1.5:3:3,deblock=filter=weak:block=8,libplacebo=w=\'if(lt(ih\\\\\\\\,1100)\\\\\\\\,iw*2\\\\\\\\,iw)\':h=\'if(lt(ih\\\\\\\\,1100)\\\\\\\\,ih*2\\\\\\\\,ih)\':upscaler=ewa_lanczossharp:deband=1:custom_shader_path=FSRCNNX_x2_16-0-4-1.glsl:format=yuv420p,hwdownload,format=yuv420p\\" /*v4.5.1*/\\n"], ["index.html", "<option value=\\"max\\">IA Max (\\u00d74 \\u2192 8K \\u2192 4K)</option>", "<option value=\\"max\\">IA Max (FSRCNNX 16)</option>"]]')
src={f:open(os.path.join(d,f),encoding='utf-8').read() for f in ('main.js','index.html')}
if '/*v4.5.1*/' in src['main.js']:print('déjà v4.5.1');sys.exit(0)
if '/*v4.5-ff*/' not in src['main.js']:print('ERREUR : il faut la v4.5');sys.exit(1)
for f,a,b in R:
  if src[f].count(a)!=1:print('ERREUR motif',f,a[:50]);sys.exit(1)
  src[f]=src[f].replace(a,b)
for f,t in src.items():open(os.path.join(d,f),'w',encoding='utf-8').write(t);print('OK',f,hashlib.sha256(t.encode()).hexdigest()[:16])

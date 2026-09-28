import os, subprocess
from matting_base import JOBS, B, probe
from detect import is_hdr, TM
OUT='extras'; os.makedirs(OUT,exist_ok=True)
for name,fn,ss,ee,mode in JOBS:
    src=B+fn; fr,D=probe(src); ee=D if ee is None else min(ee,D); dur=ee-ss
    o=f'{OUT}/orijinal_{name}.mp4'
    if not os.path.exists(o):
        vf=(TM if is_hdr(src) else '')+f'fps={fr.numerator}/{fr.denominator},scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p'
        subprocess.run(['ffmpeg','-v','error','-y','-ss',str(ss),'-t',f'{dur:.3f}','-i',src,'-vf',vf,
          '-c:v','libx264','-crf','16','-preset','slow','-profile:v','high','-movflags','+faststart',
          '-c:a','aac','-b:a','192k',o],check=True)
    a=f'{OUT}/ses_{name}.m4a'
    if not os.path.exists(a):
        subprocess.run(['ffmpeg','-v','error','-y','-ss',str(ss),'-t',f'{dur:.3f}','-i',src,'-vn',
          '-c:a','aac','-b:a','192k',a],check=True)
    print('ok',name,flush=True)
print('EXTRAS DONE')

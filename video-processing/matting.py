import os, gc, glob, json, shutil, subprocess, time, sys
import numpy as np, cv2
from PIL import Image
from detect import is_hdr, TM
from decontaminate import decon
from confetti_mask import confetti_alpha
from matting_base import JOBS, B, OUT, CRF, probe, refine, base_mask, prepass, log

def enc_open(path, w, h, fr):
    r=f'{fr.numerator}/{fr.denominator}'
    return subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgba','-s',f'{w}x{h}','-r',r,'-i','-',
      '-c:v','libvpx-vp9','-pix_fmt','yuva420p','-b:v','0','-crf',str(CRF),'-row-mt','1','-threads','2',
      '-deadline','good','-cpu-used','1','-an',path],stdin=subprocess.PIPE)
def preview(webm, out):
    j=json.loads(subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate','-of','json',webm],capture_output=True,text=True).stdout)['streams'][0]
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f"color=c=0x22222c:s={j['width']}x{j['height']}:r={j['r_frame_rate']}",
      '-c:v','libvpx-vp9','-i',webm,'-filter_complex','[0][1]overlay=shortest=1,format=yuv420p',
      '-c:v','libx264','-crf','16','-preset','slow',out],check=True)
def tight(u):
    ys,xs=np.where(u); h,w=u.shape
    x0,y0=max(0,xs.min()-16),max(0,ys.min()-16); x1,y1=min(w,xs.max()+17),min(h,ys.max()+17)
    if (x1-x0)%2: x1-=1
    if (y1-y0)%2: y1-=1
    return (int(x0),int(y0),int(x1),int(y1))

def run(name,fn,ss,ee,mode):
    tag=f'arkaplan_{name}'
    src=B+fn; fr,D=probe(src); ee=D if ee is None else min(ee,D); dur=ee-ss
    t0=time.time(); W=f'job_{name}'; shutil.rmtree(W,ignore_errors=True); os.makedirs(W+'/in'); os.makedirs(W+'/a')
    vf=(TM if is_hdr(src) else '')+f'fps={fr.numerator}/{fr.denominator},scale=trunc(iw/2)*2:trunc(ih/2)*2'
    subprocess.run(['ffmpeg','-v','error','-ss',str(ss),'-t',str(dur),'-i',src,'-vf',vf,f'{W}/in/i_%05d.png'],check=True)
    fs=sorted(glob.glob(f'{W}/in/i_*.png')); FW,FH=Image.open(fs[0]).size; crop=(0,0,FW,FH)
    if mode in ('cat_hand','sam_hand'):
        rel=prepass(src,ss,dur)
        if rel is not None:
            px,py=int(FW*0.06)+24,int(FH*0.05)+24
            crop=(max(0,int(rel[0]*FH)-px),max(0,int(rel[1]*FH)-py),min(FW,int(rel[2]*FH)+px),min(FH,int(rel[3]*FH)+py))
    log(f'>>> {name}: {len(fs)} frames @ {float(fr):.2f}fps, {FW}x{FH}, region {crop[2]-crop[0]}x{crop[3]-crop[1]}, mode={mode}')
    found=0
    for i,f in enumerate(fs):                                   # 1) alpha
        im=Image.open(f).convert('RGB').crop(crop); m=base_mask(im,mode)
        a=np.zeros((im.size[1],im.size[0]),np.uint8) if m is None else refine(im,m)
        found+= m is not None; cv2.imwrite(f'{W}/a/a_{i:05d}.png',a)
        if i and i%60==0: el=time.time()-t0; log(f'   {i}/{len(fs)} ~{el/i*(len(fs)-i)/60:.0f} min left')
    af=sorted(glob.glob(f'{W}/a/a_*.png')); n=len(af)
    rd=lambda k: cv2.imread(af[min(max(k,0),n-1)],cv2.IMREAD_GRAYSCALE)
    meds=[]; union=None
    for i in range(n):                                          # 2) temporal median -> small files
        med=np.median(np.stack([rd(i-1),rd(i),rd(i+1)]),axis=0).astype(np.uint8)
        cv2.imwrite(f'{W}/a/m_{i:05d}.png',med); union=(med>8) if union is None else (union|(med>8))
    if not union.any(): log(f'!!! {name}: no cat found'); shutil.rmtree(W,ignore_errors=True); return
    bx=tight(union); x0,y0,x1,y1=bx
    p=enc_open(f'{OUT}/{tag}.webm',x1-x0,y1-y0,fr)             # 3) composite + encode in a stream
    for i in range(n):
        med=cv2.imread(f'{W}/a/m_{i:05d}.png',cv2.IMREAD_GRAYSCALE)
        rgb=np.array(Image.open(fs[i]).convert('RGB').crop(crop))
        fr_=np.dstack([decon(rgb,med),med])[y0:y1,x0:x1]
        p.stdin.write(np.ascontiguousarray(fr_).tobytes()); os.remove(fs[i])
    p.stdin.close(); p.wait()
    preview(f'{OUT}/{tag}.webm',f'{OUT}/{tag}_preview.mp4')
    json.dump({'source':fn,'range_s':[ss,round(ee,2)],'fps':round(float(fr),3),'frames':n,
               'cat_found_%':round(100*found/n),'size':[x1-x0,y1-y0],'mode':mode},
              open(f'{OUT}/{tag}.json','w'),ensure_ascii=False,indent=1)
    log(f'<<< {name} done: {x1-x0}x{y1-y0}, cat in {round(100*found/n)}% of frames, {(time.time()-t0)/60:.1f} min')
    shutil.rmtree(W,ignore_errors=True)

if __name__=='__main__':
    sel={}
    for a in sys.argv[1:]:
        k,_,v=a.partition(':'); sel[k]=v or None
    for (n,f,s_,e,m) in JOBS:
        if n in sel:
            if os.path.exists(f'{OUT}/arkaplan_{n}.webm'): log('exists, skipped:',n); continue
            run(n,f,s_,e,sel[n] or m); gc.collect()
    log('ALL DONE')

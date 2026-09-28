import os, glob, shutil, subprocess, json, sys
import numpy as np, cv2
from PIL import Image
from contact_sheet import info
OUT='final_loops'; os.makedirs(OUT,exist_ok=True)
LOOPS=[ # name, source webm, start, end
 ('bos_kalinca_dongu',     'final/arkaplan_bos_kalinca_animasyon.webm', 1.8, 4.6),
 ('bos_duruyor_dongu_a',   'final/arkaplan_bos_duruyor.webm',           0.0, 13.0),
 ('bos_duruyor_dongu_b',   'final/arkaplan_bos_duruyor.webm',           15.8, 18.6),
 ('kedi_bos_duruyor_2_dongu_a','final/arkaplan_kedi_bos_duruyor_2.webm',0.2, 2.1),
 ('kedi_bos_duruyor_2_dongu_b','final/arkaplan_kedi_bos_duruyor_2.webm',12.4,14.9),
]
def anchor(a):
    m=a>60
    ys,xs=np.where(m)
    if len(ys)==0: return None
    y1=ys.max(); y0=ys.min(); h=y1-y0+1
    band=m[max(y0,y1-int(0.25*h)):y1+1]
    bx=np.where(band.any(0))[0]
    return np.array([ (bx.min()+bx.max())/2.0, float(y1) ])
def make(name,webm,ss,ee):
    W,H,n,fps=info(webm)
    wd=f'lp_{name}'; shutil.rmtree(wd,ignore_errors=True); os.makedirs(wd+'/in'); os.makedirs(wd+'/o')
    subprocess.run(['ffmpeg','-v','error','-c:v','libvpx-vp9','-ss',f'{ss}','-t',f'{ee-ss}','-i',webm,
                    '-pix_fmt','rgba',f'{wd}/in/%05d.png'],check=True)
    fs=sorted(glob.glob(f'{wd}/in/*.png'))
    ims=[np.array(Image.open(f)) for f in fs]
    anc=[anchor(im[...,3]) for im in ims]
    last=next(a for a in anc if a is not None)
    A=[]
    for a in anc:
        last = a if a is not None else last; A.append(last)
    A=np.array(A)
    k=max(3,int(round(fps*0.25))|1)
    ker=np.ones(k)/k
    As=np.stack([np.convolve(np.pad(A[:,i],(k//2,k//2),mode='edge'),ker,mode='valid') for i in range(2)],1)
    target=np.median(As,0)
    off=target-As                          # move every frame to the target
    mx=int(np.ceil(np.abs(off).max()))+4
    CW,CH=W+2*mx,H+2*mx
    frames=[]; union=np.zeros((CH,CW),bool)
    for im,o in zip(ims,off):
        M=np.float32([[1,0,mx+o[0]],[0,1,mx+o[1]]])
        w=cv2.warpAffine(im,M,(CW,CH),flags=cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT,borderValue=(0,0,0,0))
        frames.append(w); union|=w[...,3]>8
    ys,xs=np.where(union)
    x0,y0=max(0,xs.min()-12),max(0,ys.min()-12); x1,y1=min(CW,xs.max()+13),min(CH,ys.max()+13)
    if (x1-x0)%2: x1-=1
    if (y1-y0)%2: y1-=1
    seq=frames+frames[-2:0:-1]            # ping-pong
    for i,f in enumerate(seq):
        Image.fromarray(f[y0:y1,x0:x1],'RGBA').save(f'{wd}/o/f_{i:05d}.png',compress_level=1)
    r=f'{fps:.5f}'
    subprocess.run(['ffmpeg','-v','error','-y','-framerate',r,'-i',f'{wd}/o/f_%05d.png','-c:v','libvpx-vp9',
      '-pix_fmt','yuva420p','-b:v','0','-crf','15','-row-mt','1','-threads','2','-deadline','good','-cpu-used','1',
      '-an',f'{OUT}/arkaplan_{name}.webm'],check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f'color=c=0x22222c:s={x1-x0}x{y1-y0}:r={r}',
      '-framerate',r,'-i',f'{wd}/o/f_%05d.png','-filter_complex','[0][1]overlay=shortest=1,format=yuv420p',
      '-c:v','libx264','-crf','16','-preset','slow',f'{OUT}/arkaplan_{name}_preview.mp4'],check=True)
    drift_before=float(np.ptp(A,0).max()); drift_after=float(np.ptp(A+off,0).max())
    json.dump({'source':os.path.basename(webm),'range_s':[ss,ee],'fps':round(fps,3),'frames':len(seq),
               'ping_pong':True,'drift_px_before':round(drift_before,1),'drift_px_after':round(drift_after,1),
               'size':[int(x1-x0),int(y1-y0)]},open(f'{OUT}/arkaplan_{name}.json','w'),ensure_ascii=False,indent=1)
    shutil.rmtree(wd,ignore_errors=True)
    print(f'{name}: {len(seq)} frames, drift {drift_before:.0f}px -> {drift_after:.0f}px, {x1-x0}x{y1-y0}',flush=True)
if __name__=='__main__':
    sel=set(sys.argv[1:])
    for L in LOOPS:
        if sel and L[0] not in sel: continue
        make(*L)
    print('LOOPS DONE')

import os, gc, glob, json, shutil, subprocess, time
from fractions import Fraction
import numpy as np, cv2
from PIL import Image
from detect import is_hdr, TM, K, yolo_mask
from decontaminate import decon
from glove_mask import glove_blobs
from confetti_mask import confetti_alpha
from rembg import new_session, remove
from ultralytics import YOLO

B=os.environ.get('SOURCE_DIR', 'source_videos/')  # folder with the raw videos
OUT=os.path.abspath('final'); os.makedirs(OUT,exist_ok=True)
CRF=15
# name, source, start, end (None = to the end), mode
JOBS=[
 ('kedi_parti_butonu',    'yeni_videolar (11).mov',      0, None, 'confetti'),
 ('kedi_temizleme_butonu','yeni_videolar.MOV',           0, None, 'glove'),
 ('sevme_buton_3',        'yeni_videolar (4).mp4',       25, 32,  'cat_hand'),
 ('sevme_buton_4',        'yeni_videolar (7).mp4',       15, 22,  'cat_hand'),
 ('kedi_bos_duruyor_2',   'yeni_videolar (9).mp4',       0, 15,   'cat_hand'),
 ('sevme_buton_1',        'yeni_videolar (6).mp4',       1, 20,   'cat_hand'),
 ('bos_duruyor',          'yeni_videolar (8).mp4',       0, 20,   'cat_hand'),
 ('kediye_yemek_ver',     'yeni_videolar (1).mp4',       0, None, 'cat_hand'),
 ('bos_kalinca_animasyon','yeni_videolar (3).mp4',       0, None, 'cat_hand'),
 ('sevme_butonu_2',       'yatarken_elle_severken.MOV',  0, None, 'cat_hand'),
]
def log(*a): print(time.strftime('%H:%M:%S'),*a, flush=True)

_u=None; _sam=None; _fast=None
def u2p():
    global _u
    if _u is None: _u=new_session('u2netp')
    return _u
def sam():
    global _sam
    if _sam is None:
        from ultralytics import SAM
        _sam=SAM('sam2.1_b.pt')
    return _sam
def fast():
    global _fast
    if _fast is None: _fast=YOLO('yolo11n-seg.pt')
    return _fast

def probe(src):
    j=json.loads(subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
       'stream=avg_frame_rate','-show_entries','format=duration','-of','json',src],
       capture_output=True,text=True).stdout)
    fr=Fraction(j['streams'][0]['avg_frame_rate'])
    if fr>31: fr=fr/2          # halve 60 fps sources
    return fr, float(j['format']['duration'])

def refine(im, m):
    m=cv2.morphologyEx(m, cv2.MORPH_CLOSE, K(9))
    core,outer=cv2.erode(m,K(11)),cv2.dilate(m,K(21)); band=(outer-core).astype(bool)
    ra=np.array(remove(im,session=u2p()).convert('RGBA'))[...,3]
    a=np.where(core>0,255,0).astype(np.uint8); a[band]=ra[band]; a[outer==0]=0
    a=cv2.GaussianBlur(a,(5,5),0)
    return np.clip((a.astype(np.float32)-40)*(255/175),0,255).astype(np.uint8)

def base_mask(im, mode):
    if mode=='sam_hand':
        from hand_tracking import cat_hand_mask
        return cat_hand_mask(im)
    m=yolo_mask(im,[0,15,16])
    if mode=='glove':
        rgb=np.array(im)
        pt,_=glove_blobs(rgb)
        if pt is not None:
            neg=[]
            mc=yolo_mask(im,[15,16])
            pts=[list(pt)]; lbl=[1]
            if mc is not None:
                ys,xs=np.where(cv2.erode(mc,K(41))>0)
                if len(xs): j=len(xs)//2; pts.append([int(xs[j]),int(ys[j])]); lbl.append(0)
            r=sam()(rgb[...,::-1].copy(), points=[pts], labels=[lbl], verbose=False)[0]
            if r.masks is not None:
                g=cv2.resize((r.masks.data[0].cpu().numpy()>0.5).astype(np.uint8),(rgb.shape[1],rgb.shape[0]))
                m = g if m is None else (m|g)
    return m

def prepass(src, ss, dur):
    vf=(TM if is_hdr(src) else '')+'fps=4,scale=-2:480'
    d='/tmp/pre'; shutil.rmtree(d,ignore_errors=True); os.makedirs(d)
    subprocess.run(['ffmpeg','-v','error','-ss',str(ss),'-t',str(dur),'-i',src,'-vf',vf,f'{d}/p_%05d.png'],check=True)
    bs=[]
    for f in sorted(glob.glob(f'{d}/p_*.png')):
        r=fast().predict(f,verbose=False,classes=[0,15,16],conf=0.2)[0]
        cls=r.boxes.cls.cpu().numpy().astype(int)
        if not any(c in (15,16) for c in cls): continue
        bs += list(r.boxes.xyxy.cpu().numpy())
    shutil.rmtree(d,ignore_errors=True)
    if not bs: return None
    bs=np.array(bs)/480.
    return (bs[:,0].min(),bs[:,1].min(),bs[:,2].max(),bs[:,3].max())

def encode(framedir, fr, box, tag):
    x0,y0,x1,y1=box
    cd=framedir+'_crop'; shutil.rmtree(cd,ignore_errors=True); os.makedirs(cd)
    for j,p in enumerate(sorted(glob.glob(f'{framedir}/f_*.png'))):
        Image.open(p).crop((x0,y0,x1,y1)).save(f'{cd}/f_{j:05d}.png',compress_level=1)
    r=f'{fr.numerator}/{fr.denominator}'
    subprocess.run(['ffmpeg','-v','error','-y','-framerate',r,'-i',f'{cd}/f_%05d.png',
      '-c:v','libvpx-vp9','-pix_fmt','yuva420p','-b:v','0','-crf',str(CRF),
      '-row-mt','1','-threads','2','-deadline','good','-cpu-used','1','-an',f'{OUT}/{tag}.webm'],check=True)
    subprocess.run(['ffmpeg','-v','error','-y','-f','lavfi','-i',f'color=c=0x22222c:s={x1-x0}x{y1-y0}:r={r}',
      '-framerate',r,'-i',f'{cd}/f_%05d.png','-filter_complex','[0][1]overlay=shortest=1,format=yuv420p',
      '-c:v','libx264','-crf','16','-preset','slow',f'{OUT}/{tag}_preview.mp4'],check=True)
    shutil.rmtree(cd,ignore_errors=True)

if __name__=='__main__':
    import sys
    sel={}
    for a in sys.argv[1:]:
        k,_,v=a.partition(':'); sel[k]=v or None
    RUN=[(n,f,s_,e,(sel.get(n) or m)) for (n,f,s_,e,m) in JOBS if (not sel or n in sel)]
    for name,fn,ss,ee,mode in RUN:
        tag=f'arkaplan_{name}'
        if os.path.exists(f'{OUT}/{tag}.webm'): log('exists, skipped:',name); continue
        src=B+fn; fr,D=probe(src); ee=D if ee is None else min(ee,D); dur=ee-ss
        t0=time.time()
        W=f'job_{name}'; shutil.rmtree(W,ignore_errors=True)
        os.makedirs(W+'/in'); os.makedirs(W+'/a'); os.makedirs(W+'/b')
        vf=(TM if is_hdr(src) else '')+f'fps={fr.numerator}/{fr.denominator},scale=trunc(iw/2)*2:trunc(ih/2)*2'
        subprocess.run(['ffmpeg','-v','error','-ss',str(ss),'-t',str(dur),'-i',src,'-vf',vf,f'{W}/in/i_%05d.png'],check=True)
        fs=sorted(glob.glob(f'{W}/in/i_*.png'))
        FW,FH=Image.open(fs[0]).size
        crop=(0,0,FW,FH)
        if mode=='cat_hand':
            rel=prepass(src,ss,dur)
            if rel is not None:
                px,py=int(FW*0.06)+24,int(FH*0.05)+24
                crop=(max(0,int(rel[0]*FH)-px),max(0,int(rel[1]*FH)-py),min(FW,int(rel[2]*FH)+px),min(FH,int(rel[3]*FH)+py))
        log(f'>>> {name}: {len(fs)} frames @ {float(fr):.2f}fps, source {FW}x{FH}, working region {crop[2]-crop[0]}x{crop[3]-crop[1]}, mode={mode}')
        # 1) alpha for every frame
        alphas=[]; found=0
        for i,f in enumerate(fs):
            im=Image.open(f).convert('RGB').crop(crop)
            m=base_mask(im,mode)
            a=np.zeros((im.size[1],im.size[0]),np.uint8) if m is None else refine(im,m)
            if m is not None: found+=1
            cv2.imwrite(f'{W}/a/a_{i:05d}.png',a)
            if i and i%60==0:
                el=time.time()-t0; log(f'   {i}/{len(fs)} ~{el/i*(len(fs)-i)/60:.0f} min left')
        # 2) temporal median (3 frames) + colour decontamination + write
        af=sorted(glob.glob(f'{W}/a/a_*.png')); n=len(af)
        rd=lambda k: cv2.imread(af[min(max(k,0),n-1)],cv2.IMREAD_GRAYSCALE)
        union=None; union_b=None
        for i in range(n):
            med=np.median(np.stack([rd(i-1),rd(i),rd(i+1)]),axis=0).astype(np.uint8)
            rgb=np.array(Image.open(fs[i]).convert('RGB').crop(crop))
            col=decon(rgb,med)
            Image.fromarray(np.dstack([col,med]),'RGBA').save(f'{W}/b/f_{i:05d}.png',compress_level=1)
            union = (med>8) if union is None else (union|(med>8))
            if mode=='confetti':
                c=confetti_alpha(rgb)
                aa=np.maximum(med,c)
                cc=np.where((c>med)[...,None],rgb,col)
                os.makedirs(f'{W}/k',exist_ok=True)
                Image.fromarray(np.dstack([cc,aa]),'RGBA').save(f'{W}/k/f_{i:05d}.png',compress_level=1)
                union_b = (aa>8) if union_b is None else (union_b|(aa>8))
        def tight(u):
            ys,xs=np.where(u); h,w=u.shape
            x0,y0=max(0,xs.min()-16),max(0,ys.min()-16); x1,y1=min(w,xs.max()+17),min(h,ys.max()+17)
            if (x1-x0)%2: x1-=1
            if (y1-y0)%2: y1-=1
            return (int(x0),int(y0),int(x1),int(y1))
        if union is None or not union.any():
            log(f'!!! {name}: no cat found'); continue
        if mode=='confetti':
            encode(f'{W}/k',fr,tight(union_b),tag)
            encode(f'{W}/b',fr,tight(union),tag+'_cat_only')
        else:
            encode(f'{W}/b',fr,tight(union),tag)
        bx=tight(union_b if mode=='confetti' else union)
        json.dump({'source':fn,'range_s':[ss,round(ee,2)],'fps':round(float(fr),3),'frames':n,
                   'cat_found_%':round(100*found/n),'size':[bx[2]-bx[0],bx[3]-bx[1]],'mode':mode},
                  open(f'{OUT}/{tag}.json','w'),ensure_ascii=False,indent=1)
        log(f'<<< {name} done: {bx[2]-bx[0]}x{bx[3]-bx[1]}, cat in {round(100*found/n)}% of frames, {(time.time()-t0)/60:.1f} min')
        shutil.rmtree(W,ignore_errors=True)
        if mode=='glove':
            _sam=None; gc.collect()
    log('ALL DONE')

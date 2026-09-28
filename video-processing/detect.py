import subprocess, json, os
import numpy as np, cv2
from PIL import Image
from rembg import new_session, remove
from ultralytics import YOLO

K = lambda n: cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(n,n))
TM = ("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
      "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")
_y=_s=None
def models():
    global _y,_s
    if _y is None: _y=YOLO('yolo11m-seg.pt'); _s=new_session('isnet-general-use')
    return _y,_s

def is_hdr(src):
    o=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
        'stream=color_transfer','-of','csv=p=0',src],capture_output=True,text=True).stdout.strip()
    return o in ('arib-std-b67','smpte2084')

def grab(src,t,h=720,out=None):
    vf=(TM if is_hdr(src) else '')+f'scale=-2:{h}'
    out = out or f'/tmp/g_{abs(hash((src,t)))}.png'
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(t),'-i',src,'-vf',vf,'-frames:v','1',out],check=True)
    return Image.open(out).convert('RGB')

def _refine(im, m):
    """kaba binary maske + rembg -> temiz RGBA"""
    _,sess = models()
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, K(9))
    core, outer = cv2.erode(m,K(11)), cv2.dilate(m,K(21))
    band = (outer-core).astype(bool)
    ra = np.array(remove(im, session=sess).convert('RGBA'))[...,3]
    a = np.where(core>0,255,0).astype(np.uint8)
    a[band]=ra[band]; a[outer==0]=0
    a = cv2.GaussianBlur(a,(5,5),0)
    a = np.clip((a.astype(np.float32)-40)*(255/175),0,255).astype(np.uint8)
    rgb = np.array(im)
    holes = cv2.dilate(((a<235)&(a>0)).astype(np.uint8),K(3))
    rgb = cv2.inpaint(rgb, holes, 4, cv2.INPAINT_TELEA)
    return Image.fromarray(np.dstack([rgb,a]),'RGBA')

def yolo_mask(im, classes):
    yolo,_ = models(); W,H = im.size
    r = yolo.predict(im, verbose=False, classes=classes, conf=0.25)[0]
    if r.masks is None or len(r.masks)==0: return None
    ms = r.masks.data.cpu().numpy()
    cls = r.boxes.cls.cpu().numpy().astype(int)
    conf= r.boxes.conf.cpu().numpy()
    # most confident cat/dog + other objects touching it
    animal = [i for i,c in enumerate(cls) if c in (15,16)]
    if not animal: return None
    ai = animal[int(np.argmax(conf[animal]))]
    keep=[ai]
    base = cv2.dilate((cv2.resize(ms[ai],(W,H))>0.5).astype(np.uint8), K(41))
    for i in range(len(ms)):
        if i==ai: continue
        mi=(cv2.resize(ms[i],(W,H))>0.5).astype(np.uint8)
        if mi.sum() and (mi&base).sum()/mi.sum() > 0.06:   # does it touch the cat?
            keep.append(i)
    out=np.zeros((H,W),np.uint8)
    for i in keep: out |= (cv2.resize(ms[i],(W,H))>0.5).astype(np.uint8)
    return out

def mode_cat(im):
    m = yolo_mask(im,[15,16]);  return _refine(im,m) if m is not None else None
def mode_cat_hand(im):
    m = yolo_mask(im,[0,15,16]); return _refine(im,m) if m is not None else None
def mode_scene(im):
    _,sess = models()
    return remove(im, session=sess).convert('RGBA')

MODES={'cat':mode_cat,'cat+hand':mode_cat_hand,'scene':mode_scene}

def checker(im):
    w,h=im.size; yy,xx=np.mgrid[0:h,0:w]
    c=(((xx//20)+(yy//20))%2==0)
    bg=np.where(c[...,None],np.array([38,38,50]),np.array([88,52,118])).astype(float)
    arr=np.array(im).astype(float); a=arr[...,3:4]/255.
    return Image.fromarray((arr[...,:3]*a+bg*(1-a)).astype(np.uint8))

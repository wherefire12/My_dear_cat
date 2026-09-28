import numpy as np, cv2
from PIL import Image
from detect import models, grab, K, yolo_mask
from rembg import new_session, remove
_s={}
def sess(n):
    if n not in _s: _s[n]=new_session(n)
    return _s[n]

def decon(rgb, a):
    """yumusak renk temizligi: yari saydam pikselleri opak komsularin rengine cek"""
    af = (a.astype(np.float32)/255.)
    op = (af>0.94).astype(np.float32)
    img = rgb.astype(np.float32)
    num = cv2.blur(img*op[...,None],(21,21)); den = cv2.blur(op,(21,21))[...,None]+1e-5
    inside = num/den
    w = np.clip(1.0-af/0.94, 0, 1)[...,None]      # pull inward as alpha drops
    w = w*(af>0.02)[...,None]
    return np.clip(img*(1-w)+inside*w, 0, 255).astype(np.uint8)

def cut(im, model='u2netp', use_inpaint=False, curve=True):
    m = yolo_mask(im,[0,15,16])
    if m is None: return None
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, K(9))
    core,outer = cv2.erode(m,K(11)), cv2.dilate(m,K(21))
    band=(outer-core).astype(bool)
    ra = np.array(remove(im, session=sess(model)).convert('RGBA'))[...,3]
    a = np.where(core>0,255,0).astype(np.uint8)
    a[band]=ra[band]; a[outer==0]=0
    a = cv2.GaussianBlur(a,(5,5),0)
    if curve: a = np.clip((a.astype(np.float32)-40)*(255/175),0,255).astype(np.uint8)
    rgb=np.array(im)
    if use_inpaint:
        holes=cv2.dilate(((a<235)&(a>0)).astype(np.uint8),K(3))
        rgb=cv2.inpaint(rgb,holes,4,cv2.INPAINT_TELEA)
    else:
        rgb=decon(rgb,a)
    return Image.fromarray(np.dstack([rgb,a]),'RGBA')

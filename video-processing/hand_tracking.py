import numpy as np, cv2
from ultralytics import SAM
from detect import K, models
_sam=None
def S():
    global _sam
    if _sam is None: _sam=SAM('sam2.1_b.pt')
    return _sam
def skin(rgb):
    ycc=cv2.cvtColor(rgb,cv2.COLOR_RGB2YCrCb); hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    cr,cb=ycc[...,1].astype(int),ycc[...,2].astype(int); v=hsv[...,2]; s=hsv[...,1]
    h=hsv[...,0].astype(int)
    m=((cr>=140)&(cr<=180)&(cb>=95)&(cb<=128)&(v>50)&(s>55)&((h<=13)|(h>=168))).astype(np.uint8)
    return cv2.morphologyEx(cv2.morphologyEx(m,cv2.MORPH_OPEN,K(7)),cv2.MORPH_CLOSE,K(15))
def cat_hand_mask(im, want_hand=True):
    rgb=np.array(im); H,W=rgb.shape[:2]
    yolo,_=models()
    r=yolo.predict(im,verbose=False,classes=[15,16],conf=0.2)[0]
    if len(r.boxes)==0: return None
    cb=r.boxes.xyxy.cpu().numpy()[int(np.argmax(r.boxes.conf.cpu().numpy()))].tolist()
    boxes=[cb]
    if want_hand:
        sk=skin(rgb)
        n,lab,st,_=cv2.connectedComponentsWithStats(sk)
        catbox=np.zeros((H,W),np.uint8)
        x0,y0,x1,y1=map(int,cb); catbox[max(0,y0-40):y1+40,max(0,x0-40):x1+40]=1
        for i in range(1,n):
            x,y,w,h,a=st[i]
            if a<0.004*H*W: continue
            if ((lab==i)&(catbox>0)).sum()<200: continue
            boxes.append([float(x),float(y),float(x+w),float(y+h)])
    s=S()(rgb[...,::-1].copy(), bboxes=boxes, verbose=False)[0]
    ms=s.masks.data.cpu().numpy()>0.5
    out=np.zeros((H,W),np.uint8)
    for k in range(ms.shape[0]):
        out|=cv2.resize(ms[k].astype(np.uint8),(W,H),interpolation=cv2.INTER_NEAREST)
    return out

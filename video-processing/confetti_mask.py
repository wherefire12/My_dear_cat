import numpy as np, cv2
from detect import K
def confetti_alpha(rgb, cat_mask=None, SMIN=0.26):
    hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV).astype(np.float32)
    h,s,v=hsv[...,0],hsv[...,1]/255.,hsv[...,2]/255.
    soft=np.clip((s-SMIN)/0.12,0,1)*np.clip((v-0.30)/0.15,0,1)
    brown=(h>=6)&(h<=21)&(s<0.62)&(v<0.78)
    soft[brown]=0
    hard=(soft>0.5).astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(hard)
    H,W=hard.shape; keep=np.zeros_like(hard)
    for i in range(1,n):
        x,y,w,hh,a=st[i]
        if a<12: continue                      # noise
        if a>0.006*H*W: continue               # large coloured object (cupboard etc.)
        if max(w,hh)>0.18*max(H,W): continue   # long streak
        keep[lab==i]=1
    keep=cv2.dilate(keep,K(5))
    a=(soft*keep*255).astype(np.uint8)
    return cv2.GaussianBlur(a,(3,3),0)

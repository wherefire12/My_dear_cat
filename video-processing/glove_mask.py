import numpy as np, cv2
from detect import K
def glove_blobs(rgb):
    """sari firca + kirmizi yuz: doygun sari/kirmizi pikseller"""
    hsv=cv2.cvtColor(rgb,cv2.COLOR_RGB2HSV)
    h,s,v=hsv[...,0].astype(int),hsv[...,1],hsv[...,2]
    yellow=((h>=18)&(h<=38)&(s>120)&(v>110))
    red=(((h<=8)|(h>=170))&(s>140)&(v>70))
    m=((yellow|red)*255).astype(np.uint8)
    m=cv2.morphologyEx(m,cv2.MORPH_OPEN,K(5))
    n,lab,st,cen=cv2.connectedComponentsWithStats(m)
    if n<=1: return None, m
    i=1+int(np.argmax(st[1:,cv2.CC_STAT_AREA]))
    if st[i,cv2.CC_STAT_AREA] < 0.0015*m.size: return None, m
    return (int(cen[i][0]),int(cen[i][1])), (lab==i)

import sys, os, json, subprocess, shutil
import numpy as np, cv2
from contact_sheet import info
def specks(a, frac):
    m=(a>20).astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(m,8)
    if n<=2: return None
    areas=st[1:,cv2.CC_STAT_AREA]; big=areas.max()
    lim=max(frac*a.size, 0.02*big)
    bad=[i+1 for i,ar in enumerate(areas) if ar<lim]
    if not bad: return None
    return np.isin(lab,bad)
def scan(webm, frac=0.0015):
    W,H,n,fps=info(webm)
    p=subprocess.Popen(['ffmpeg','-v','error','-c:v','libvpx-vp9','-i',webm,'-f','rawvideo','-pix_fmt','rgba','-'],stdout=subprocess.PIPE)
    cnt=0; tot=0
    while True:
        b=p.stdout.read(W*H*4)
        if len(b)<W*H*4: break
        f=np.frombuffer(b,np.uint8).reshape(H,W,4); s=specks(f[...,3],frac)
        if s is not None: cnt+=1; tot+=int(s.sum())
    p.wait(); return cnt,tot,n
def clean(webm, frac=0.0015):
    W,H,n,fps=info(webm)
    j=json.loads(subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=r_frame_rate','-of','json',webm],capture_output=True,text=True).stdout)['streams'][0]
    tmp=webm+'.tmp.webm'
    dec=subprocess.Popen(['ffmpeg','-v','error','-c:v','libvpx-vp9','-i',webm,'-f','rawvideo','-pix_fmt','rgba','-'],stdout=subprocess.PIPE)
    enc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgba','-s',f'{W}x{H}','-r',j['r_frame_rate'],'-i','-',
      '-c:v','libvpx-vp9','-pix_fmt','yuva420p','-b:v','0','-crf','15','-row-mt','1','-threads','2','-deadline','good','-cpu-used','1','-an',tmp],stdin=subprocess.PIPE)
    while True:
        b=dec.stdout.read(W*H*4)
        if len(b)<W*H*4: break
        f=np.frombuffer(b,np.uint8).reshape(H,W,4).copy(); s=specks(f[...,3],frac)
        if s is not None: f[s,3]=0
        enc.stdin.write(f.tobytes())
    dec.wait(); enc.stdin.close(); enc.wait(); os.replace(tmp,webm)
if __name__=='__main__':
    mode=sys.argv[1]
    for w in sys.argv[2:]:
        if mode=='scan': c,t,n=scan(w); print(f'{os.path.basename(w)}: {c}/{n} frames with specks, {t}px total',flush=True)
        else: clean(w); print('cleaned',w,flush=True)

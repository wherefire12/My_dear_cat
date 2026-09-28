import sys, os, json, subprocess
import numpy as np, cv2
from contact_sheet import info
from despeckle import specks
def decode(webm):
    W,H,n,fps=info(webm)
    p=subprocess.Popen(['ffmpeg','-v','error','-c:v','libvpx-vp9','-i',webm,'-f','rawvideo','-pix_fmt','rgba','-'],stdout=subprocess.PIPE)
    while True:
        b=p.stdout.read(W*H*4)
        if len(b)<W*H*4: break
        yield np.frombuffer(b,np.uint8).reshape(H,W,4)
    p.wait()
def analyze(webm, thr=0.6, win=4):
    ms=[]
    for f in decode(webm):
        ms.append(cv2.resize((f[...,3]>128).astype(np.uint8),None,fx=0.25,fy=0.25,interpolation=cv2.INTER_NEAREST).astype(bool))
    M=np.stack(ms); n=len(M); bad=np.zeros(n,bool); ious=[]
    for i in range(n):
        lo,hi=max(0,i-win),min(n,i+win+1)
        ref=M[lo:hi].mean(0)>=0.5
        inter=(M[i]&ref).sum(); uni=(M[i]|ref).sum()
        iou=inter/uni if uni else 0.0; ious.append(iou)
        if M[i].sum()<0.02*M[i].size or iou<thr: bad[i]=True
    return bad, np.array(ious)
def repair(webm, bad, frac=0.0015):
    W,H,n,fps=info(webm)
    r=json.loads(subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=r_frame_rate','-of','json',webm],capture_output=True,text=True).stdout)['streams'][0]['r_frame_rate']
    good=np.where(~bad)[0]
    if len(good)==0: return
    # for each bad frame, the nearest good frame (prefer the previous one)
    src_idx=[]
    for i in range(len(bad)):
        if not bad[i]: src_idx.append(i); continue
        prev=good[good<i]; nxt=good[good>i]
        src_idx.append(int(prev[-1]) if len(prev) else int(nxt[0]))
    need=set(src_idx)
    tmp=webm+'.tmp.webm'
    enc=subprocess.Popen(['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgba','-s',f'{W}x{H}','-r',r,'-i','-',
      '-c:v','libvpx-vp9','-pix_fmt','yuva420p','-b:v','0','-crf','15','-row-mt','1','-threads','2','-deadline','good','-cpu-used','1','-an',tmp],stdin=subprocess.PIPE)
    cache={}; out_i=0
    for i,f in enumerate(decode(webm)):
        f=f.copy(); s=specks(f[...,3],frac)
        if s is not None: f[s,3]=0
        if i in need: cache[i]=f
        # write out the frames that are ready, in order
        while out_i<len(src_idx) and src_idx[out_i] in cache:
            enc.stdin.write(cache[src_idx[out_i]].tobytes()); out_i+=1
            for k in [k for k in cache if k< src_idx[min(out_i,len(src_idx)-1)] and k<out_i-1]: cache.pop(k,None)
    while out_i<len(src_idx):
        enc.stdin.write(cache[src_idx[out_i]].tobytes()); out_i+=1
    enc.stdin.close(); enc.wait(); os.replace(tmp,webm)
if __name__=='__main__':
    mode=sys.argv[1]
    for w in sys.argv[2:]:
        bad,ious=analyze(w)
        runs=[]; st=None
        for i,b in enumerate(bad):
            if b and st is None: st=i
            if not b and st is not None: runs.append((st,i-1)); st=None
        if st is not None: runs.append((st,len(bad)-1))
        print(f'{os.path.basename(w)}: {bad.sum()}/{len(bad)} bad frames, runs {runs[:12]}{"..." if len(runs)>12 else ""}',flush=True)
        if mode=='repair': repair(w,bad); print('  repaired',flush=True)

import sys, subprocess, json, numpy as np
from PIL import Image
def info(webm):
    j=json.loads(subprocess.run(['ffprobe','-v','error','-count_packets','-select_streams','v:0','-show_entries',
       'stream=width,height,nb_read_packets,avg_frame_rate','-of','json',webm],capture_output=True,text=True).stdout)['streams'][0]
    fr=j['avg_frame_rate'].split('/'); fps=float(fr[0])/float(fr[1])
    return j['width'],j['height'],int(j['nb_read_packets']),fps
def frame_at(webm,t,W,H):
    raw=subprocess.run(['ffmpeg','-v','error','-c:v','libvpx-vp9','-ss',f'{t:.3f}','-i',webm,'-frames:v','1',
        '-f','rawvideo','-pix_fmt','rgba','-'],capture_output=True).stdout
    return np.frombuffer(raw,np.uint8)[:W*H*4].reshape(H,W,4)
def bg(w,h,kind):
    yy,xx=np.mgrid[0:h,0:w]
    if kind==0: return np.dstack([np.full((h,w),30),np.full((h,w),31),np.full((h,w),40)]).astype(float)
    return np.dstack([60+120*xx/w, 90+60*yy/h, 200-80*xx/w]).astype(float)
def sheet(webm,out,pos=(0.05,0.3,0.55,0.8,0.97)):
    W,H,n,fps=info(webm); dur=n/fps
    fr=[frame_at(webm,min(p*dur,dur-1.5/fps),W,H) for p in pos]
    tiles=[]
    for k in (0,1):
        for f in fr:
            a=f[...,3:4]/255.; comp=(f[...,:3]*a+bg(W,H,k)*(1-a)).astype(np.uint8)
            im=Image.fromarray(comp); im.thumbnail((260,420)); tiles.append(im)
    tw=max(t.width for t in tiles); th=max(t.height for t in tiles)
    s=Image.new('RGB',(tw*len(fr),th*2),(10,10,12))
    for i,t in enumerate(tiles): s.paste(t,((i%len(fr))*tw,(i//len(fr))*th))
    s.save(out,quality=88); print(out,'frames',n,f'{fps:.2f}fps',f'{W}x{H}')
if __name__=='__main__': sheet(sys.argv[1],sys.argv[2])

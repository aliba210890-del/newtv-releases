import subprocess, math, sys, numpy as np
import scipy.ndimage as ndi
from PIL import Image, ImageDraw, ImageFont, ImageFilter
MODE=sys.argv[1]  # 'own' or 'ad'
SRC='/mnt/user-data/attachments/5bbc8bae-7cb5-5c91-a614-4a9bed5869bd/8f49bb3c-1000315481.mp4'
P='/mnt/user-data/attachments/5bbc8bae-7cb5-5c91-a614-4a9bed5869bd/'
def load(n): return Image.open(P+n+'-image.jpg').convert('RGB').crop((251,0,2310,1159))
ACT,TV,KINO,KAR,RAD=[load(n) for n in ['70efd5da','25be1807','06b78fed','c3aa436b','661232b2']]
if MODE=='ad':
    TV=Image.open('/tmp/claude-0/vid/demo_tv.png').convert('RGB').resize(ACT.size)
    k=KINO.copy(); sw,sh=k.size
    for box in [(int(sw*0.6),int(sh*0.08),sw,int(sh*0.58)),(0,int(sh*0.72),sw,sh),(0,int(sh*0.18),int(sw*0.6),int(sh*0.45))]:
        k.paste(k.crop(box).filter(ImageFilter.GaussianBlur(28)),box[:2])
    KINO=k
w,h=720,1280; W,H=1080,1920; FPS=30; AR=1.52
F='/usr/share/fonts/opentype/inter/Inter-'
f1=ImageFont.truetype(F+'ExtraBold.otf',80); fs=ImageFont.truetype(F+'Bold.otf',54)
EMO=ImageFont.truetype('/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf',109)
def screen(t):
    if t<5.0:
        im=ACT.copy()
        if t>2.4:
            d=ImageDraw.Draw(im); k=((t-2.4)%0.6)/0.6; r=int(20+40*k)
            d.rounded_rectangle((640-r*3,1030-r,1420+r*3,1150+r),radius=60,outline=(255,255,255),width=14)
        return im
    return [TV,KINO,KAR,RAD][min(3,int((t-5.0)/0.75))] if t<8.0 else TV
caps=[(0,2.3,"ЖИВЁШЬ ЗА ГРАНИЦЕЙ?",(255,255,255)),(2.3,5,"НАЖАЛ ОДНУ КНОПКУ",(255,255,255)),(5,5.75,"КАНАЛЫ",(255,255,255)),(5.75,6.5,"КИНОЗАЛ",(255,255,255)),(6.5,7.25,"КАРАОКЕ",(255,255,255)),(7.25,8,"РАДИО",(255,255,255)),(8,10.1,"СУТКИ БЕСПЛАТНО!",(255,180,60))]
dec=subprocess.Popen(['ffmpeg','-loglevel','error','-i',SRC,'-vf','fps=30','-f','rawvideo','-pix_fmt','rgb24','-'],stdout=subprocess.PIPE)
out='g4_'+MODE+'.mp4'
enc=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-','-i',SRC,'-map','0:v','-map','1:a','-shortest','-c:v','libx264','-preset','veryfast','-crf','19','-pix_fmt','yuv420p','-c:a','aac',out],stdin=subprocess.PIPE)
n=0; sm=None
while True:
    raw=dec.stdout.read(w*h*3)
    if len(raw)<w*h*3: break
    a=np.frombuffer(raw,np.uint8).reshape(h,w,3).copy(); t=n/FPS
    ai=a.astype(int); blue=(ai[...,2]>140)&(ai[...,2]>ai[...,0]+55)
    rows=np.where(blue[:, :200].mean(1)>0.5)[0]; band=blue[rows.min()+20:rows.max()-20]
    cols=np.where(band.mean(0)>0.5)[0]
    cur=np.array([cols.min(),rows.min(),rows.max()],float)
    sm=cur if sm is None else sm*0.6+cur*0.4
    x0,y0,y1=sm; hh=y1-y0; ww=hh*AR; X0,Y0,X1,Y1=int(x0)-2,int(y0)-2,int(x0+ww)+2,int(y1)+3
    X1=min(X1,w)
    sub=blue[Y0:Y1,X0:X1]; filled=ndi.binary_fill_holes(sub)
    filled=ndi.binary_dilation(filled,iterations=1)
    km=np.array(Image.fromarray((filled*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.0)))/255.0
    sc=screen(t).resize((int(ww)+4,Y1-Y0),Image.LANCZOS).crop((0,0,X1-X0,Y1-Y0))
    s=np.array(sc).astype(float); reg=a[Y0:Y1,X0:X1].astype(float)
    a[Y0:Y1,X0:X1]=(reg*(1-km[...,None])+s*km[...,None]).astype(np.uint8)
    img=Image.fromarray(a).resize((W,H),Image.LANCZOS).convert('RGBA')
    ov=Image.new('RGBA',(W,H),(0,0,0,0)); d=ImageDraw.Draw(ov)
    for s0,e0,tx,col in caps:
        if s0<=t<e0:
            tw=d.textlength(tx,font=f1); d.text(((W-tw)/2,170),tx,font=f1,fill=col,stroke_width=8,stroke_fill=(0,0,0))
    if 2.3<=t<5.0:
        bx=(X0+(X1-X0)*0.5)*W/w; by=(Y0+(Y1-Y0)*0.94)*H/h
        k=((t-2.3)%0.7)/0.7; R=int(40+50*k)
        d.ellipse((bx-R*2.8,by-R,bx+R*2.8,by+R),outline=(255,170,40,int(255*(1-k))),width=10)
        bob=int(18*math.sin(t*9)); d.text((bx-50,by+40+bob),"👆",font=EMO,embedded_color=True)
        lab="ЖМИ СЮДА"; lw=d.textlength(lab,font=f1)
        d.rounded_rectangle(((W-lw)/2-30,by+190,(W+lw)/2+30,by+295),radius=30,fill=(255,140,30,240)); d.text(((W-lw)/2,by+198),lab,font=f1,fill=(20,20,40))
    tx="newtvglobal.online"; tw=d.textlength(tx,font=fs)
    d.rounded_rectangle(((W-tw)/2-36,H-250,(W+tw)/2+36,H-150),radius=50,fill=(10,14,48,230),outline=(255,120,40),width=5); d.text(((W-tw)/2,H-238),tx,font=fs,fill=(255,255,255))
    enc.stdin.write(Image.alpha_composite(img,ov).convert('RGB').tobytes()); n+=1
enc.stdin.close(); enc.wait(); print(out,n)

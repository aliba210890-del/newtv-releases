#!/usr/bin/env python3
"""Короткий вертикальный ролик-фишка New TV (1080x1920, ~16 c).
Использование: python3 tip.py <id темы из topics.json> <out.mp4>
Ассеты берутся из ../assets. Нужны: Pillow, ffmpeg, шрифты Inter."""
import json, math, os, sys, glob, subprocess, tempfile, shutil
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))
A = os.path.join(HERE, '..', 'assets')
W, H, FPS = 1080, 1920, 30
ORANGE = (255, 138, 0)

def font(name, size):
    for p in ['/usr/share/fonts/opentype/inter/' + name] + glob.glob('/usr/share/fonts/**/' + name, recursive=True):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    for p in glob.glob('/usr/share/fonts/**/DejaVuSans-Bold.ttf', recursive=True):
        return ImageFont.truetype(p, size)
    return ImageFont.load_default()

EMOJI = glob.glob('/usr/share/fonts/**/NotoColorEmoji*.ttf', recursive=True)

def emoji(ch, size):
    if not EMOJI:
        return None
    e = Image.new('RGBA', (140, 140), (0, 0, 0, 0))
    ImageDraw.Draw(e).text((0, 0), ch, font=ImageFont.truetype(EMOJI[0], 109), embedded_color=True)
    return e.resize((size, size), Image.LANCZOS)

def background():
    b = Image.new('RGB', (W, H)); d = ImageDraw.Draw(b)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(8 + 6 * k), int(14 + 4 * k), int(46 - 18 * k)))
    g = Image.new('RGB', (W, H)); ImageDraw.Draw(g).ellipse((300, -300, 1500, 700), fill=(60, 30, 110))
    return ImageChops.add(b, g.filter(ImageFilter.GaussianBlur(200)))

BG = background()

def ease(t):
    t = min(max(t, 0), 1); return 1 - (1 - t) ** 3

def wrap(d, text, f, maxw):
    words, lines, cur = text.split(), [], ''
    for w in words:
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=f) <= maxw: cur = t
        else: lines.append(cur); cur = w
    lines.append(cur); return lines

def centered(d, lines, y, f, fill, gap=12):
    for ln in lines:
        d.text((W // 2, y), ln, font=f, fill=fill, anchor='ma'); y += f.size + gap
    return y

def card(img, w):
    h = int(img.height * w / img.width); im = img.resize((w, h), Image.LANCZOS)
    c = Image.new('RGBA', (w + 12, h + 12), (0, 0, 0, 0))
    ImageDraw.Draw(c).rounded_rectangle((0, 0, w + 11, h + 11), 26, fill=ORANGE)
    m = Image.new('L', (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), 22, fill=255)
    c.paste(im, (6, 6), m); return c

def place(base, c, x, y):
    s = Image.new('L', base.size, 0); s.paste(190, (x + 14, y + 24), c.split()[3])
    base.paste((0, 0, 0), (0, 0), s.filter(ImageFilter.GaussianBlur(24))); base.paste(c, (x, y), c)

def load_screen(name):
    im = Image.open(os.path.join(A, name)).convert('RGB')
    if im.width > 2400:  # снимки 2576x1159 с чёрными полями
        im = im.crop((250, 0, 2320, 1159))
    return im

def r_hook(topic):
    def r(t, dur):
        im = BG.copy(); d = ImageDraw.Draw(im, 'RGBA'); k = ease(t / 0.5)
        e = emoji(topic.get('emoji', '📺'), 200)
        if e: im.paste(e, (W // 2 - 100, int(470 - 60 * (1 - k))), e)
        f = font('Inter-ExtraBold.otf', 88)
        centered(d, wrap(d, topic['hook'], f, 940), int(760 + 50 * (1 - k)), f, (255, 255, 255, int(255 * k)), 18)
        return im
    return r

def r_step(topic, step):
    img = load_screen(step['screen'])
    def r(t, dur):
        im = BG.copy(); d = ImageDraw.Draw(im, 'RGBA'); k = ease(t / 0.45)
        ft = font('Inter-ExtraBold.otf', 70)
        y = centered(d, wrap(d, step['title'], ft, 960), int(250 - 30 * (1 - k)), ft, (255, 255, 255, int(255 * k)), 10)
        if step.get('sub'):
            fs = font('Inter-Medium.otf', 42)
            centered(d, wrap(d, step['sub'], fs, 940), y + 16, fs, (190, 205, 230, int(255 * k)), 8)
        src = img
        z = step.get('zoom')
        if z and t > 0.6:
            q = ease((t - 0.6) / 0.9)
            box = [img.width * 0 * (1 - q) + z[0] * q, z[1] * q, img.width * (1 - q) + z[2] * q, img.height * (1 - q) + z[3] * q]
            src = img.crop(tuple(int(v) for v in box)).resize(img.size, Image.LANCZOS)
        cw = int(1040 * (1 + 0.03 * t / dur))
        c = card(src, cw); x = (W - c.width) // 2; yy = int(820 + (1 - k) * 90)
        place(im, c, x, yy)
        ring = step.get('ring')
        if ring and t > 0.8 and not z:
            s = cw / img.width; cx = x + 6 + ring[0] * s; cy = yy + 6 + ring[1] * s
            p = 0.5 + 0.5 * math.sin((t - 0.8) * 2 * math.pi * 1.6)
            hw = ring[2] * s / 2 + 22 + p * 12; hh = ring[3] * s / 2 + 16 + p * 8
            d = ImageDraw.Draw(im, 'RGBA')
            d.rounded_rectangle((cx - hw, cy - hh, cx + hw, cy + hh), hh, outline=(255, 230, 0, 255), width=8)
            lf = font('Inter-ExtraBold.otf', 56); lab = 'ЖМИ СЮДА'; lw = d.textlength(lab, font=lf)
            ly = yy + c.height + 50; bx = W // 2 - (lw + 120) // 2
            d.rounded_rectangle((bx, ly, bx + lw + 120, ly + 92), 24, fill=(255, 230, 0, 255))
            d.text((bx + 26, ly + 14), lab, font=lf, fill=(15, 20, 50))
            e = emoji('👆', 66)
            if e: im.paste(e, (int(bx + lw + 40), int(ly + 12)), e)
        if step.get('note') and not topic.get('voice'):
            fn = font('Inter-Bold.otf', 46); d = ImageDraw.Draw(im, 'RGBA')
            centered(d, wrap(d, step['note'], fn, 940), 1560 if not ring else 1640, fn, (255, 200, 120, int(255 * ease((t - 1.0) / 0.5))), 10)
        return im
    return r

LOGO_SRC = os.path.join(A, 'act-screen.png')

def r_cta(t, dur):
    im = BG.copy(); d = ImageDraw.Draw(im, 'RGBA'); k = ease(t / 0.5)
    if os.path.exists(LOGO_SRC):
        lg = Image.open(LOGO_SRC).convert('RGB').crop((810, 57, 1110, 357)).resize((300, 300))
        m = Image.new('L', (300, 300), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, 299, 299), 52, fill=255)
        im.paste(lg, (390, int(330 + 40 * (1 - k))), m); d = ImageDraw.Draw(im, 'RGBA')
    d.text((W // 2, 720), 'Попробуйте сами', font=font('Inter-ExtraBold.otf', 80), fill=(255, 255, 255, int(255 * k)), anchor='ma')
    d.text((W // 2, 830), '24 часа бесплатно', font=font('Inter-ExtraBold.otf', 66), fill=(255, 170, 40, int(255 * k)), anchor='ma')
    q = ease((t - 0.5) / 0.5)
    d.text((W // 2, 1010), 'Код в Downloader', font=font('Inter-Medium.otf', 44), fill=(190, 205, 230, int(255 * q)), anchor='ma')
    d.rounded_rectangle((250, 1080, 830, 1210), 34, outline=(255, 138, 0, int(255 * q)), width=6)
    d.text((W // 2, 1098), '5451207', font=font('Inter-ExtraBold.otf', 82), fill=(255, 255, 255, int(255 * q)), anchor='ma')
    d.text((W // 2, 1300), 'newtvglobal.online', font=font('Inter-Bold.otf', 48), fill=(255, 255, 255, int(255 * q)), anchor='ma')
    return im

VOICE = os.environ.get('TIP_VOICE', 'artemiy')
SAY = [('New TV', 'Нью Ти Ви'), ('Fire TV Stick', 'Файр Ти Ви Стик'), ('Downloader', 'Даунлоадер'), ('QR', 'кью ар'), ('Избранное', 'Избранное')]

def tts(text, path):
    for a, b in SAY: text = text.replace(a, b)
    subprocess.run(['RHVoice-test', '-p', VOICE, '-r', '105', '-o', path], input=text.encode('utf-8'), check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    out = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path],
                         capture_output=True, text=True).stdout.strip()
    return float(out)

def chunks(text, dur):
    words = text.split(); res, cur = [], []
    for w in words:
        if cur and (len(' '.join(cur + [w])) > 22 or len(cur) >= 4): res.append(' '.join(cur)); cur = [w]
        else: cur.append(w)
    if cur: res.append(' '.join(cur))
    tot = sum(len(c) + 3 for c in res); t = 0.15; out = []
    for c in res:
        d = dur * (len(c) + 3) / tot; out.append((t, t + d, c)); t += d
    return out

def draw_caption(im, t, caps, y):
    for a, b, c in caps:
        if a <= t < b:
            d = ImageDraw.Draw(im, 'RGBA'); f = font('Inter-ExtraBold.otf', 62)
            w = d.textlength(c, font=f); x = (W - w) / 2
            d.rounded_rectangle((x - 30, y - 16, x + w + 30, y + f.size + 22), 22, fill=(0, 0, 0, 170))
            d.text((W // 2, y), c, font=f, fill=(255, 235, 60), anchor='ma', stroke_width=3, stroke_fill=(0, 0, 0))
            return

def main():
    tid, out = sys.argv[1], sys.argv[2]
    topics = json.load(open(os.path.join(HERE, 'topics.json'), encoding='utf-8'))
    topic = next(t for t in topics if t['id'] == tid)
    tmp = tempfile.mkdtemp()
    v = topic.get('voice')
    texts = [v['hook']] + v['steps'] + ['Попробуйте сами. Downloader, код пять, четыре, пять, один, два, ноль, семь. Двадцать четыре часа бесплатно.'] if v else None
    renders = [r_hook(topic)] + [r_step(topic, s) for s in topic['steps']] + [r_cta]
    base = [2.6] + [s.get('dur', 4.5) for s in topic['steps']] + [3.6]
    segs, wavs = [], []
    for i, fn in enumerate(renders):
        caps, dur = [], base[i]
        if texts:
            wp = os.path.join(tmp, 'v%d.wav' % i); ad = tts(texts[i], wp)
            dur = max(ad + 0.45, 2.2); wavs.append((wp, dur))
            if i < len(renders) - 1: caps = chunks(texts[i], ad)
        segs.append((dur, fn, caps, 1300 if i == 0 else 1680))
    n = 0
    for dur, fn, caps, cy in segs:
        for i in range(int(round(dur * FPS))):
            t = i / FPS; im = fn(t, dur)
            if caps: draw_caption(im, t, caps, cy)
            if i < 6: im = Image.blend(Image.new('RGB', im.size, (0, 0, 0)), im, (i + 1) / 7)
            im.save(os.path.join(tmp, '%05d.jpg' % n), quality=92); n += 1
    total = n / FPS
    music = os.path.join(A, 'music.wav')
    if wavs:
        parts = []
        for j, (wp, dur) in enumerate(wavs):
            pp = os.path.join(tmp, 'p%d.wav' % j)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', wp, '-af', f'aresample=48000,aformat=channel_layouts=stereo,adelay=150|150,apad,atrim=0:{round(dur*FPS)/FPS:.4f}', pp], check=True)
            parts.append(pp)
        lst = os.path.join(tmp, 'l.txt'); open(lst, 'w').write(''.join(f"file '{p}'\n" for p in parts))
        voice = os.path.join(tmp, 'voice.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'pcm_s16le', voice], check=True)
        afilter = (f'[1:a]aresample=48000,aformat=channel_layouts=stereo,volume=0.16,atrim=0:{total:.2f},afade=t=out:st={total-1.0:.2f}:d=1.0[m];'
                   f'[2:a]volume=1.6,highpass=f=80,acompressor=threshold=-18dB:ratio=3[vo];[vo][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[a]')
        cmd = ['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, '%05d.jpg'), '-stream_loop', '-1', '-i', music, '-i', voice,
               '-filter_complex', afilter]
    else:
        cmd = ['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', os.path.join(tmp, '%05d.jpg'), '-stream_loop', '-1', '-i', music, '-filter_complex',
               f'[1:a]aresample=48000,aformat=channel_layouts=stereo,volume=0.6,atrim=0:{total:.2f},afade=t=in:d=0.4,afade=t=out:st={total-1.2:.2f}:d=1.2[a]']
    subprocess.run(cmd + ['-map', '0:v', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '20', '-pix_fmt', 'yuv420p',
                          '-c:a', 'aac', '-b:a', '160k', '-t', f'{total:.2f}', '-movflags', '+faststart', out], check=True)
    shutil.rmtree(tmp); print(out, round(total, 1))

if __name__ == '__main__':
    main()

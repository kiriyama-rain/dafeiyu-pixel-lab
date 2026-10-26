#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Day3 角色动起来 demo：整身傀儡 + 程序化运动 + 代码画的碗。

不切片、不拆骨骼——先用最简单的办法验证「这张设定图动起来能不能看」：
整身做位移/缩放/倾斜，尾巴单独一层摆动，道具用代码画并跟着手的高度走。

产物：frames/*.png（30fps）+ demo.mp4（1920×1080）
"""
import math, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 1920, 1080
FPS = 30
DUR = 9.0
OUT = os.path.join(HERE, 'out')
def _pick(*paths):
    for p in paths:
        if os.path.exists(p):
            return p
    raise SystemExit('找不到字体: %s' % (paths,))


FONT = _pick('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
             os.path.expanduser('~/.local/share/fonts/NotoSansCJK-Bold.ttc'),
             os.path.expanduser('~/.local/share/fonts/NotoSansSC-Bold.otf'))
FONT_M = _pick('/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc',
               os.path.expanduser('~/.local/share/fonts/NotoSansCJK-Regular.ttc'),
               os.path.expanduser('~/.local/share/fonts/NotoSansSC-Regular.otf'))

# 段落：开始时间 / 名字 / 说明
SEGMENTS = [
    (0.0, 'idle', '站着呼吸'),
    (2.2, 'walk', '走'),
    (4.4, 'run', '跑'),
    (6.0, 'jump', '跳'),
    (7.2, 'hold', '端碗'),
]


def load_parts():
    body = Image.open(os.path.join(HERE, 'char-alpha.png')).convert('RGBA')
    # 尾巴单独切出来：右侧那条，用椭圆蒙版柔化
    tw = body.copy()
    mask = Image.new('L', body.size, 0)
    d = ImageDraw.Draw(mask)
    bw, bh = body.size
    d.ellipse([int(bw * 0.52), int(bh * 0.55), bw + 40, int(bh * 0.98)], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(8))
    # 尾巴层只保留蒙版内像素
    tail = Image.new('RGBA', body.size, (0, 0, 0, 0))
    tail.paste(tw, (0, 0), mask)
    return body, tail


def bg(t):
    """深海背景：垂直渐变 + 光柱 + 缓慢飘的气泡，写死随机种子。"""
    im = Image.new('RGB', (W, H), (8, 14, 26))
    d = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(8 + 10 * k), int(16 + 16 * k), int(30 + 24 * k)))
    # 光柱
    for i, x in enumerate((360, 780, 1300, 1680)):
        alpha = 16 + i * 3
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).polygon([(x, 0), (x + 90, 0), (x + 210, H), (x + 40, H)],
                                    fill=(120, 180, 240, alpha))
        lay = lay.filter(ImageFilter.GaussianBlur(18))
        im = Image.alpha_composite(im.convert('RGBA'), lay).convert('RGB')
    # 气泡
    d = ImageDraw.Draw(im)
    for i in range(26):
        bx = (i * 137) % W
        by = H - ((i * 91 + t * (18 + (i % 5) * 9)) % (H + 60))
        r = 1.5 + (i % 4)
        d.ellipse([bx - r, by - r, bx + r, by + r], outline=(150, 200, 240), width=1)
    return im.convert('RGBA')


def shadow(w, h, cx, cy, scale=1.0, alpha=90):
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ew = int(w * 0.42 * scale)
    eh = int(h * 0.045 * scale)
    ImageDraw.Draw(lay).ellipse([cx - ew, cy - eh, cx + ew, cy + eh], fill=(0, 0, 0, alpha))
    return lay.filter(ImageFilter.GaussianBlur(10))


def bowl(size=110):
    """代码画的饭碗：一个碗 + 米饭堆 + 两处高光。"""
    s = size
    im = Image.new('RGBA', (s, int(s * 0.8)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([0, int(s * 0.18), s, int(s * 0.5)], fill=(236, 240, 245, 255),
              outline=(30, 40, 66, 255), width=max(2, s // 42))
    d.pieslice([0, int(s * 0.3), s, int(s * 0.78)], 0, 180, fill=(245, 248, 252, 255),
               outline=(30, 40, 66, 255), width=max(2, s // 42))
    # 米饭
    d.ellipse([int(s * 0.10), int(s * 0.05), int(s * 0.90), int(s * 0.36)],
              fill=(252, 252, 250, 255), outline=(30, 40, 66, 255), width=max(2, s // 48))
    for i in range(7):
        bx = int(s * (0.20 + 0.09 * i))
        d.ellipse([bx, int(s * 0.10), bx + s // 12, int(s * 0.10) + s // 12],
                  fill=(255, 255, 255, 255), outline=(210, 214, 224, 255))
    return im


def ease(x):
    return x * x * (3 - 2 * x)


def state(t):
    """返回该时刻的身体参数。"""
    if t < 2.2:                      # idle
        k = t / 2.2
        return dict(x=W / 2, y=920, scale=1.0 + 0.012 * math.sin(k * math.pi * 2),
                    rot=0, tail=4 * math.sin(k * math.pi * 2), prop=None, label='idle')
    if t < 4.4:                      # walk
        k = (t - 2.2) / 2.2
        x = W * 0.22 + k * W * 0.56
        bob = abs(math.sin(k * math.pi * 4)) * 14
        return dict(x=x, y=920 - bob, scale=1.0, rot=2.0 * math.sin(k * math.pi * 4),
                    tail=9 * math.sin(k * math.pi * 4), prop=None, label='walk')
    if t < 6.0:                      # run
        k = (t - 4.4) / 1.6
        x = W * 0.18 + k * W * 0.64
        bob = abs(math.sin(k * math.pi * 8)) * 22
        return dict(x=x, y=920 - bob, scale=1.0, rot=5.0 * math.sin(k * math.pi * 8),
                    tail=16 * math.sin(k * math.pi * 8), prop=None, label='run')
    if t < 7.2:                      # jump
        k = (t - 6.0) / 1.2
        lift = math.sin(k * math.pi) * 150
        squash = 1.0 + 0.10 * math.sin(k * math.pi * 2)
        return dict(x=W / 2, y=920 - lift, scale=squash, rot=0,
                    tail=-18 * math.sin(k * math.pi), prop=None, label='jump')
    k = (t - 7.2) / 1.8              # hold
    return dict(x=W / 2, y=920, scale=1.0 + 0.01 * math.sin(k * math.pi * 2),
                rot=0, tail=5 * math.sin(k * math.pi * 2), prop='bowl', label='hold')


def compose(t, body, tail, prop_img, font, font_m):
    st = state(t)
    im = bg(t)
    # 影子
    sh = shadow(body.width, body.height, st['x'], 920 + 18, st['scale'] * 1.0)
    im = Image.alpha_composite(im, sh)

    # 尾巴层（先转再贴，绕根部旋转）
    tail_rot = tail.rotate(st['tail'] * 0.6, resample=Image.BICUBIC,
                           center=(int(tail.width * 0.62), int(tail.height * 0.62)))
    # 身体
    sp = body
    if abs(st['rot']) > 0.01:
        sp = sp.rotate(-st['rot'], resample=Image.BICUBIC, expand=False)
    if abs(st['scale'] - 1.0) > 0.001:
        nw = int(sp.width * st['scale'])
        nh = int(sp.height * st['scale'])
        sp = sp.resize((nw, nh), Image.LANCZOS)
        tail_rot = tail_rot.resize((int(tail_rot.width * st['scale']),
                                    int(tail_rot.height * st['scale'])), Image.LANCZOS)
    x = int(st['x'] - sp.width / 2)
    y = int(st['y'] - sp.height)
    # 尾巴先贴（在身体后面），再贴身体
    im.alpha_composite(tail_rot, (x, y))
    im.alpha_composite(sp, (x, y))

    # 道具：挂在胸前偏右，跟手的高度走
    if st['prop'] == 'bowl':
        pw = int(prop_img.width * 0.9)
        ph = int(prop_img.height * pw / prop_img.width)
        p = prop_img.resize((pw, ph), Image.LANCZOS)
        px = int(st['x'] + sp.width * 0.13)
        py = int(st['y'] - sp.height * 0.34)
        im.alpha_composite(p, (px, py))

    d = ImageDraw.Draw(im)
    # 顶部 HUD
    d.text((90, 54), '角色动起来 demo', font=font, fill=(238, 244, 252))
    d.text((90, 104), '整身傀儡 · 未经骨骼拆解 · 只为验证「设定图动起来能不能看」',
           font=font_m, fill=(130, 158, 190))
    # 当前状态
    lab = st['label']
    lw = d.textlength(lab, font=font)
    d.rounded_rectangle([W - 90 - lw - 48, 54, W - 90, 54 + 64], radius=12, fill=(200, 62, 47))
    d.text((W - 90 - lw - 24, 66), lab, font=font, fill=(255, 250, 244))
    # 底部进度条
    y0 = H - 46
    d.rectangle([90, y0, W - 90, y0 + 6], fill=(40, 56, 80))
    d.rectangle([90, y0, 90 + int((W - 180) * (t / DUR)), y0 + 6], fill=(120, 190, 240))
    return im.convert('RGB')


def main():
    os.makedirs(OUT, exist_ok=True)
    body, tail = load_parts()
    # 角色统一缩放到 640 高
    scale = 760 / body.height
    body = body.resize((int(body.width * scale), 760), Image.LANCZOS)
    tail = tail.resize(body.size, Image.LANCZOS)
    font = ImageFont.truetype(FONT, 40)
    font_m = ImageFont.truetype(FONT_M, 26)
    prop = bowl(118)

    n = int(DUR * FPS)
    for i in range(n):
        compose(i / FPS, body, tail, prop, font, font_m).save(os.path.join(OUT, 'f%04d.png' % i))
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y',
                    '-framerate', str(FPS), '-i', os.path.join(OUT, 'f%04d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20',
                    os.path.join(HERE, 'demo.mp4')], check=True)
    print('frames', n, '-> demo.mp4')


if __name__ == '__main__':
    main()

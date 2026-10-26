#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把各条路线的结果拼成一张对比图：图 + 文件名 + 颜色数/网格对齐率。"""
import json, os
from PIL import Image, ImageDraw, ImageFont

F = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
FM = '/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc'
ROWS = [
    ('A 插画（模型主场）', ['r1-A1.jpg', 'r1-A2.jpg', 'r2-A3.png']),
    ('B 让模型直接画像素', ['r1-B1.jpg', 'r1-B2.jpg', 'r1-B3.jpg']),
    ('C 模型出图 + 代码压成像素', ['r1-C1_64_16.png', 'r1-C4_64_12_crop.png', 'r2-C5_64_12_crop.png']),
]
CELL, PAD, HEAD = 380, 26, 56


def main():
    metrics = {}
    if os.path.exists('docs/metrics.json'):
        metrics = json.load(open('docs/metrics.json'))
    W = PAD + (CELL + PAD) * 3
    H = PAD + len(ROWS) * (HEAD + CELL + 62 + PAD)
    canvas = Image.new('RGB', (W, H), (14, 20, 32))
    d = ImageDraw.Draw(canvas)
    fh = ImageFont.truetype(F, 30)
    fs = ImageFont.truetype(FM, 22)
    y = PAD
    for title, files in ROWS:
        d.text((PAD, y), title, font=fh, fill=(240, 246, 255))
        y += HEAD
        for i, fn in enumerate(files):
            p = os.path.join('results', fn)
            if not os.path.exists(p):
                continue
            im = Image.open(p).convert('RGB')
            s = min(im.width, im.height)
            im = im.crop(((im.width - s) // 2, (im.height - s) // 2,
                          (im.width + s) // 2, (im.height + s) // 2)).resize((CELL, CELL), Image.LANCZOS)
            x = PAD + i * (CELL + PAD)
            canvas.paste(im, (x, y))
            m = metrics.get(fn, {})
            label = fn
            sub = ('色 %s · 对齐 %s' % (m.get('colors', '?'), m.get('grid_score', '?'))) if m else ''
            d.text((x, y + CELL + 8), label, font=fs, fill=(190, 205, 225))
            if sub:
                d.text((x, y + CELL + 34), sub, font=fs, fill=(120, 200, 160))
        y += CELL + 62 + PAD
    canvas.save('docs/comparison.jpg', quality=92)
    print('wrote docs/comparison.jpg', canvas.size)


if __name__ == '__main__':
    main()

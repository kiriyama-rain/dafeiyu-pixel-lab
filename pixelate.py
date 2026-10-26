#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把任意插画压成真像素：调色板量化 → NEAREST 下采样 → NEAREST 放大。

和「让模型画像素」的区别：颜色数受控、每格唯一色、网格对齐率恒为 1.0。
"""
import argparse
from PIL import Image


def auto_crop(im, pad=0.06):
    """按背景色差分找主体框，像素密度才能用满。"""
    w, h = im.size
    bg = im.getpixel((2, 2))
    px = im.load()
    xs, ys = [], []
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            r, g, b = px[x, y]
            if abs(r - bg[0]) + abs(g - bg[1]) + abs(b - bg[2]) > 40:
                xs.append(x); ys.append(y)
    if not xs:
        return im
    x0, x1 = max(0, min(xs) - int(w * pad)), min(w, max(xs) + int(w * pad))
    y0, y1 = max(0, min(ys) - int(h * pad)), min(h, max(ys) + int(h * pad))
    side = max(x1 - x0, y1 - y0)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    x0 = max(0, cx - side // 2); y0 = max(0, cy - side // 2)
    return im.crop((x0, y0, min(w, x0 + side), min(h, y0 + side)))


def pixelate(src, out, grid=64, colors=16, scale=8, crop=False):
    im = Image.open(src).convert('RGB')
    if crop:
        im = auto_crop(im)
    # 先缩到网格尺寸（先量化再缩，避免缩完再量化产生杂色）
    small = im.resize((grid, grid), Image.LANCZOS)
    pal = small.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE)
    small = pal.convert('RGB')
    big = small.resize((grid * scale, grid * scale), Image.NEAREST)
    big.save(out)
    return out, big.size, colors


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('out')
    ap.add_argument('--grid', type=int, default=64)
    ap.add_argument('--colors', type=int, default=16)
    ap.add_argument('--scale', type=int, default=8)
    ap.add_argument('--crop', action='store_true')
    a = ap.parse_args()
    print(pixelate(a.src, a.out, a.grid, a.colors, a.scale, a.crop))

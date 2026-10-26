#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""像素纯度检测：颜色数、网格对齐率。用来判断「真像素」还是「模型画的伪像素」。"""
import sys, json
from PIL import Image

def analyze(path, grid_guess=None):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    cols = im.getcolors(maxcolors=1 << 24) or []
    ncolor = len(cols)
    px = im.load()
    # 找最大网格：把图按 n 等分，检查每格内是否单一颜色
    best = None
    for n in (16, 32, 48, 64, 96, 128, 256):
        if w % n or h % n:
            continue
        cw, ch = w // n, h // n
        if cw < 2:
            continue
        same = 0
        total = 0
        for gy in range(n):
            for gx in range(n):
                total += 1
                c0 = px[gx * cw, gy * ch]
                ok = True
                for dy in (0, ch // 2, ch - 1):
                    for dx in (0, cw // 2, cw - 1):
                        if px[gx * cw + dx, gy * ch + dy] != c0:
                            ok = False
                            break
                    if not ok:
                        break
                if ok:
                    same += 1
        rate = same / total
        if best is None or rate > best[1]:
            best = (n, rate)
        if rate > 0.98:
            break
    return {'file': path, 'size': [w, h], 'colors': ncolor,
            'best_grid': best[0] if best else None,
            'grid_score': round(best[1], 4) if best else 0}

if __name__ == '__main__':
    for p in sys.argv[1:]:
        print(json.dumps(analyze(p), ensure_ascii=False))

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dafeiyu-pixel-lab 复现脚本

用法：
    python3 run.py prompts/round1-A1.txt --out results/A1 --model banana-2.1

读取同目录（或 --env 指定）的 config.env：
    API_KEY=...           你的 key
    API_BASE=https://...  兼容 OpenAI 风格的中转/自建地址
    MODEL=banana-2.1
    ASPECT_RATIO=1:1
    IMAGE_SIZE=1K

不写死任何渠道，key 与 base 全部走环境变量。产物：
    <out>.jpg        图
    <out>.meta.json  模型 / 参数 / 耗时 / 尺寸 / 提示词全文
"""
import argparse, base64, json, os, sys, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))


def load_env(path):
    cfg = {}
    if os.path.exists(path):
        for line in open(path, encoding='utf-8'):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            cfg[k.strip()] = v.strip()
    return cfg


def post_json(url, body, key, timeout=120):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={'Authorization': 'Bearer ' + key,
                                          'Content-Type': 'application/json'})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def get_json(url, key, timeout=60):
    req = urllib.request.Request(url, headers={'Authorization': 'Bearer ' + key})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('prompt', help='提示词文件（全文照发，不加工）')
    ap.add_argument('--out', required=True, help='输出前缀，如 results/A1')
    ap.add_argument('--env', default=os.path.join(HERE, 'config.env'))
    ap.add_argument('--model', default=None)
    ap.add_argument('--aspect', default=None)
    ap.add_argument('--size', default=None)
    ap.add_argument('--timeout', type=int, default=600)
    ap.add_argument('--ref', action='append', default=[], help='参考图文件，可重复；会以 base64 data URI 数组传给 images')
    a = ap.parse_args()

    cfg = load_env(a.env)
    key = cfg.get('API_KEY') or os.environ.get('API_KEY', '')
    base = (cfg.get('API_BASE') or os.environ.get('API_BASE', '')).rstrip('/')
    if not key or not base:
        sys.exit('缺 API_KEY / API_BASE，检查 config.env')
    model = a.model or cfg.get('MODEL', 'banana-2.1')
    ratio = a.aspect or cfg.get('ASPECT_RATIO', '1:1')
    size = a.size or cfg.get('IMAGE_SIZE', '1K')

    prompt = open(a.prompt, encoding='utf-8').read().strip()
    t0 = time.time()
    body = {'model': model, 'prompt': prompt, 'aspectRatio': ratio, 'imageSize': size}
    if a.ref:
        import base64, mimetypes
        refs = []
        for f in a.ref:
            mime = mimetypes.guess_type(f)[0] or 'image/jpeg'
            refs.append('data:%s;base64,%s' % (mime, base64.b64encode(open(f, 'rb').read()).decode()))
        body['images'] = refs
    r = post_json(base + '/v1/media/generate', body, key)
    tid = (r.get('data') or {}).get('task_id')
    if not tid:
        sys.exit('提交失败: %s' % json.dumps(r, ensure_ascii=False)[:300])

    url = None
    while time.time() - t0 < a.timeout:
        time.sleep(6)
        s = get_json(base + '/v1/skills/task-status?task_id=%s' % tid, key)
        if s.get('state') == 'success':
            url = s.get('result_url')
            break
        if s.get('state') == 'failed':
            sys.exit('生成失败: %s' % s.get('error'))
    if not url:
        sys.exit('轮询超时')

    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or '.', exist_ok=True)
    raw = urllib.request.urlopen(url, timeout=180).read()
    ext = os.path.splitext(url.split('?')[0])[1] or '.jpg'
    img_path = a.out + ext
    open(img_path, 'wb').write(raw)
    meta = {'model': model, 'refs': [os.path.basename(x) for x in a.ref], 'aspect_ratio': ratio, 'image_size': size,
            'prompt_file': os.path.relpath(a.prompt, HERE), 'prompt': prompt,
            'task_id': tid, 'elapsed_sec': round(time.time() - t0, 1),
            'file': os.path.basename(img_path), 'bytes': len(raw)}
    json.dump(meta, open(a.out + '.meta.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print(json.dumps({'out': img_path, 'bytes': len(raw), 'sec': meta['elapsed_sec']}))


if __name__ == '__main__':
    main()

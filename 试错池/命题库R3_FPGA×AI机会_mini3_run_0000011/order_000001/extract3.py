#!/usr/bin/env python3
import re

def text_only(f):
    with open(f) as fh:
        h = fh.read()
    h = re.sub(r'<script.*?</script>', '', h, flags=re.S)
    h = re.sub(r'<style.*?</style>', '', h, flags=re.S)
    h = re.sub(r'<[^>]+>', ' ', h)
    h = re.sub(r'&[^;]+;', ' ', h)
    h = re.sub(r'\s+', ' ', h)
    return h

files = {
    'A100_wiki': 'sources/wiki_a100.html',
    'RTX4090_wiki': 'sources/wiki_rtx4090.html',
    'VU13P_wiki': 'sources/wiki_virtex.html',
    'Agilex_wiki': 'sources/wiki_agilex.html',
}

for name, f in files.items():
    t = text_only(f)
    print(f"\n=== {name} (len={len(t)}) ===")
    keywords = ['TDP','Tensor Core','FP16','FP32','HBM','Bandwidth','MHz','GHz','CUDA Cores','SM count','GA100','AD102','7 nm','5 nm','TSMC','Boost clock','Base clock','logic cells','DSP slices','system logic','UltraRAM']
    for kw in keywords:
        pattern = r'([^.]*?\b' + re.escape(kw) + r'\b[^.]*?\d[^.]*?\.)'
        seen = 0
        for m in re.finditer(pattern, t, re.I):
            s = m.group(1).strip()
            if 30 < len(s) < 400 and len(re.findall(r'\d', s)) >= 1:
                print(f"  [{kw}] {s[:300]}")
                seen += 1
                if seen >= 2:
                    break
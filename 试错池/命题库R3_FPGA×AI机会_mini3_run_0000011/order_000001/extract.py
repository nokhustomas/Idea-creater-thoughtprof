#!/usr/bin/env python3
import re
import sys
from bs4 import BeautifulSoup

def clean(s):
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def show(file, keywords, max_lines=20):
    print(f"\n=== {file} ===")
    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
        raw = f.read()
    try:
        soup = BeautifulSoup(raw, 'html.parser')
        text = soup.get_text(separator='\n')
    except:
        text = raw
    text = re.sub(r'\n\s*\n+', '\n', text)
    found = 0
    for line in text.split('\n'):
        line = line.strip()
        if not line or len(line) > 250:
            continue
        for kw in keywords:
            if kw.lower() in line.lower() and any(c.isdigit() for c in line):
                print(f"  [{kw}] {line[:200]}")
                found += 1
                break
        if found >= max_lines:
            break

show('sources/tpu_a100.html', ['TDP','Tensor','FP16','FP32','Memory','Bandwidth','CUDA Cores','SM Count','Boost','Base'])
show('sources/tpu_rtx4090.html', ['TDP','Tensor','FP16','FP32','Memory','Bandwidth','CUDA Cores','SM Count','Boost','Base'])
show('sources/wiki_virtex.html', ['VU13P','DSP','Logic','system logic','Mhz','MHz','UltraRAM','HBM','PCIe','Gb/s'])
show('sources/wiki_agilex.html', ['Agilex','DSP','Logic','MHz','HBM','PCIe','Gb/s','TOPS','TFLOP'])
show('sources/wiki_rtx4090.html', ['4090','Tensor','FP16','TDP','Bandwidth','CUDA Cores','GB','MHz','Boost'])
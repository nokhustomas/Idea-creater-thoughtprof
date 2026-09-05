#!/usr/bin/env python3
import re

# 找TPU规格
def get_specs(fname):
    print(f"\n=== {fname} ===")
    with open(fname, 'r', encoding='utf-8') as f:
        raw = f.read()
    # TPU的格式：<dt>字段</dt><dd>值</dd>  或者
    # 找 "TDP" 等关键字段后面的数字
    patterns = [
        r'(?:TDP|Power|功耗)[^<]{0,40}?(\d{2,4}\s*W)',
        r'(?:Memory|显存|内存)[\s\S]{0,200}?(\d+\s*GB)',
        r'(?:Bandwidth|带宽)[\s\S]{0,200}?(\d+(?:\.\d+)?\s*(?:TB|GB)/s)',
        r'(?:FP16|FP32)[\s\S]{0,200}?(\d+(?:\.\d+)?\s*TFLOPS)',
        r'(?:Boost|加速)[\s\S]{0,100}?(\d{3,4}\s*MHz)',
        r'(?:Base|基础)[\s\S]{0,100}?(\d{3,4}\s*MHz)',
        r'(?:CUDA|Shader|流处理器)[\s\S]{0,100}?(\d{1,3}[,\s]?\d{3,6})',
        r'(?:SMs?|SM)[\s\S]{0,100}?(\d{1,4})',
    ]
    for p in patterns:
        m = re.search(p, raw, re.I)
        if m:
            print(f"  Pattern {p[:30]}: {m.group(0)[:120]}")
    # 用TPU的特殊JSON数据
    m = re.search(r'"name":"([^"]+)".*?"specs":(\{[^}]+\})', raw, re.S)
    if m:
        print(f"  Name: {m.group(1)}")
        print(f"  Specs JSON snippet: {m.group(2)[:500]}")

get_specs('sources/tpu_a100.html')
get_specs('sources/tpu_rtx4090.html')
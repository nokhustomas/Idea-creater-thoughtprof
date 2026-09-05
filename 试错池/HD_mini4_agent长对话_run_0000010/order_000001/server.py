#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HDIBS 科普网站 - 服务端入口（与 app.py 等价）
端口: 8765
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app import main

if __name__ == '__main__':
    main()
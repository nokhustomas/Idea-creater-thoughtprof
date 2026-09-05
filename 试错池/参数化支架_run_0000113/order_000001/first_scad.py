#!/usr/bin/env python3
import os

# Check info_000010 directory
if os.path.exists('info_000010'):
    files = os.listdir('info_000010')
    print("Files in info_000010:")
    for f in files:
        print(f"  {f}")
else:
    print("info_000010 not found")

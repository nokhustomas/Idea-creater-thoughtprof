#!/usr/bin/env python3
"""
Generate synthetic A‑share data for backtest.py
"""
import sys
sys.path.insert(0, '.')
from backtest import generate_synthetic_data

if __name__ == "__main__":
    generate_synthetic_data("sample_data")
    print("Done. Run: python3 backtest.py --data sample_data --rules rules_example.json --start 2025-01-01 --end 2025-12-31")

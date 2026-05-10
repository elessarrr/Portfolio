#!/usr/bin/env python3
"""
Minimal test: Load 5 rows, expand subparts, and print result.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.data_preprocessor import DataPreprocessor
from utils.subpart_processing import expand_comma_separated_subparts
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

import pandas as pd

def minimal_parquet_load():
    print("=== Minimal Parquet Load Test ===")
    df = pd.read_parquet("data/emissions_data.parquet")
    print(f"Loaded DataFrame shape: {df.shape}")
    print(df.head())

def minimal_expansion_test():
    print("=== Minimal Subpart Expansion Test ===")
    df = pd.read_parquet("data/emissions_data.parquet")
    df_sample = df.head(5)
    print("Original sample:")
    print(df_sample[["SUBPARTS", "GHG QUANTITY (METRIC TONS CO2e)"]])
    expanded = expand_comma_separated_subparts(df_sample)
    print("Expanded sample:")
    print(expanded[["SUBPARTS", "GHG QUANTITY (METRIC TONS CO2e)"]])

if __name__ == '__main__':
    minimal_parquet_load()
    minimal_expansion_test()
# Context:
# This module handles data preprocessing for the emissions dashboard to optimize performance.
# It converts Excel data into a more efficient format (Parquet) and provides utilities for
# data transformation. The preprocessed data significantly reduces load times and memory usage
# compared to reading directly from Excel.

from pathlib import Path
import pandas as pd
from typing import List, Optional, Dict, Any
import os

class DataPreprocessor:
    def __init__(self, data_dir: str = 'data'):
        """Initialize the DataPreprocessor.
        
        Args:
            data_dir: Directory containing the data files, relative to project root
        """
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / data_dir
        self.excel_file = self.data_dir / 'emissions_data.xlsx'
        self.parquet_file = self.data_dir / 'emissions_data.parquet'
        
        # Essential columns for the dashboard
        self.columns_to_read = [
            'STATE',
            'REPORTING YEAR',
            'GHG QUANTITY (METRIC TONS CO2e)',
            'SUBPARTS',
            'PARENT COMPANIES'
        ]
        
    def convert_to_parquet(self) -> None:
        """Convert Excel data to Parquet format with optimized settings.
        
        This is a one-time operation that should be run when:
        1. Setting up the project for the first time
        2. The source Excel file has been updated
        """
        try:
            # Read and combine all sheets with optimized settings
            with pd.ExcelFile(self.excel_file) as xl:
                df = pd.concat([
                    pd.read_excel(
                        xl,
                        sheet_name=sheet,
                        usecols=self.columns_to_read,
                        dtype={
                            'STATE': 'category',
                            'REPORTING YEAR': 'Int64',
                            'GHG QUANTITY (METRIC TONS CO2e)': 'float64',
                            'SUBPARTS': 'string',
                            'PARENT COMPANIES': 'category'
                        }
                    ) for sheet in xl.sheet_names
                ])
            
            # Write to Parquet with compression
            df.to_parquet(
                self.parquet_file,
                compression='snappy',  # Fast compression/decompression
                index=False
            )
            print(f"Successfully converted Excel data to Parquet format at {self.parquet_file}")
            
        except Exception as e:
            print(f"[ERROR] Failed to convert Excel to Parquet: {str(e)}")
            raise
    
    def load_data(self, nrows: int = None) -> pd.DataFrame:
        """Load data from Parquet file, converting from Excel if necessary.
        Optionally limit to nrows for debugging.
        Returns:
            DataFrame containing the emissions data
        """
        try:
            # Convert to Parquet if it doesn't exist
            if not self.parquet_file.exists():
                self.convert_to_parquet()
            # Load from Parquet with optimized settings
            df = pd.read_parquet(self.parquet_file)
            if nrows is not None:
                df = df.head(nrows)
            return df
        except Exception as e:
            print(f"[ERROR] Failed to load data: {str(e)}")
            raise
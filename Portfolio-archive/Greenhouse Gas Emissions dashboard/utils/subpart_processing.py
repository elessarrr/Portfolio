# Context
#
# This module provides utility functions for processing and validating subpart data
# from GHG emissions reports. Its primary responsibilities include:
#
# - **Expanding Comma-Separated Subparts**: The `expand_comma_separated_subparts`
#   function is the core of this module. It takes rows with multiple subparts
#   listed in a single string (e.g., "A, B, C") and splits them into individual
#   rows, one for each subpart. During this process, it proportionally distributes
#   the total emissions among the individual subparts.
#
# - **Data Cleaning and Validation**: The `clean_subpart_data` function orchestrates
#   the cleaning process by first expanding the subparts and then validating each
#   subpart code against a known list of valid codes. Any rows with invalid
#   subparts are removed to ensure data integrity.
#
# - **Display Name Generation**: The `get_subpart_display_name` function provides
#   a human-readable name for a given subpart code, which is useful for
#   visualizations and reports.
#
# This module is critical for ensuring that the subpart data is in a clean,
# standardized, and usable format for downstream analysis and visualization.

from typing import List, Dict, Any, Tuple
import pandas as pd
import logging
from typing import List
from utils.subpart_mappings import subpart_mappings, get_subpart_description, validate_subpart_code

# Configure logging for this module
logger = logging.getLogger(__name__)

def expand_comma_separated_subparts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand rows with comma-separated subparts into individual rows.
    
    This function takes a DataFrame where the 'SUBPARTS' column may contain
    comma-separated values (e.g., 'A,B,C') and creates separate rows for
    each individual subpart while preserving all other column values.
    
    Args:
        df: Input DataFrame with potential comma-separated subparts
        
    Returns:
        DataFrame with expanded subpart rows
        
    Raises:
        ValueError: If SUBPARTS column is missing from DataFrame
    """
    if df.empty:
        logger.warning("Empty DataFrame provided to expand_comma_separated_subparts")
        return df.copy()
    
    if 'SUBPARTS' not in df.columns:
        raise ValueError("DataFrame must contain 'SUBPARTS' column")
    
    print(f"[DEBUG] Starting subpart expansion for {len(df)} rows...")
    
    # Filter out rows with empty/NaN subparts first
    df_clean = df.dropna(subset=['SUBPARTS']).copy()
    df_clean = df_clean[df_clean['SUBPARTS'].astype(str).str.strip() != '']
    df_clean = df_clean[df_clean['SUBPARTS'].astype(str).str.lower() != 'nan']
    
    if df_clean.empty:
        logger.warning("No valid subparts found after filtering")
        return pd.DataFrame(columns=df.columns)
    
    print(f"[DEBUG] Processing {len(df_clean)} rows with valid subparts...")

    # Vectorized approach for performance
    # Ensure 'SUBPARTS' column is of string type before using .str accessor
    df_clean['SUBPARTS'] = df_clean['SUBPARTS'].astype(str)

    # 1. Split the 'SUBPARTS' string into a list of subparts
    print(f"[DEBUG] df_clean shape before split: {df_clean.shape}")
    print(f"[DEBUG] df_clean 'SUBPARTS' dtype before split: {df_clean['SUBPARTS'].dtype}")
    print(f"[DEBUG] df_clean['SUBPARTS'] type: {type(df_clean['SUBPARTS'])}")
    
    try:
        # Ensure we're working with a Series, not a DataFrame
        subparts_series = df_clean['SUBPARTS']
        if not isinstance(subparts_series, pd.Series):
            raise TypeError(f"Expected Series, got {type(subparts_series)}")
        
        df_clean['SUBPARTS_LIST'] = subparts_series.str.split(',')
        print(f"[DEBUG] Successfully split subparts into lists")
    except Exception as e:
        print(f"[DEBUG] Error during subpart split: {e}")
        print(f"[DEBUG] Error type: {type(e)}")
        import traceback
        traceback.print_exc()
        raise


    # 2. Calculate the number of subparts for each row
    df_clean['NUM_SUBPARTS'] = df_clean['SUBPARTS_LIST'].apply(len)

    # 3. Calculate proportional emissions
    df_clean['GHG_QUANTITY'] = df_clean.get('GHG_QUANTITY', 0) / df_clean['NUM_SUBPARTS']

    # 4. Explode the DataFrame to create new rows for each subpart
    expanded_df = df_clean.explode('SUBPARTS_LIST')

    # 5. Drop the original SUBPARTS column to avoid duplication, then rename
    expanded_df = expanded_df.drop(columns=['SUBPARTS'])
    expanded_df.rename(columns={'SUBPARTS_LIST': 'SUBPARTS'}, inplace=True)
    
    print(f"[DEBUG] After explode and rename, SUBPARTS column type: {type(expanded_df['SUBPARTS'])}")
    print(f"[DEBUG] Expanded df columns: {expanded_df.columns.tolist()}")
    print(f"[DEBUG] Expanded df shape: {expanded_df.shape}")
    print(f"[DEBUG] SUBPARTS dtype: {expanded_df['SUBPARTS'].dtype}")
    print(f"[DEBUG] Sample SUBPARTS values: {expanded_df['SUBPARTS'].head().tolist()}")
    
    # Clean up the SUBPARTS column
    try:
        expanded_df['SUBPARTS'] = expanded_df['SUBPARTS'].str.strip().str.upper()
        print(f"[DEBUG] Successfully cleaned SUBPARTS column")
    except Exception as e:
        print(f"[DEBUG] Error cleaning SUBPARTS: {e}")
        print(f"[DEBUG] SUBPARTS column sample after explode: {expanded_df['SUBPARTS'].head()}")
        import traceback
        traceback.print_exc()
        raise
    
    expanded_df.drop(columns=['NUM_SUBPARTS'], inplace=True)

    if expanded_df.empty:
        logger.warning("No valid subparts found after expansion")
        return pd.DataFrame(columns=df.columns)

    print(f"[DEBUG] Created {len(expanded_df)} expanded rows")

    # Reset index to ensure clean indexing
    expanded_df = expanded_df.reset_index(drop=True)

    logger.info(f"Expanded {len(df)} rows to {len(expanded_df)} rows")
    return expanded_df

def validate_subpart_codes(subpart_codes: List[str]) -> List[str]:
    """
    Validate subpart codes against known mappings.
    
    Args:
        subpart_codes: List of subpart codes to validate
        
    Returns:
        List of valid subpart codes
    """
    if not subpart_codes:
        return []
    
    valid_codes = []
    invalid_codes = []
    
    for code in subpart_codes:
        if validate_subpart_code(code):
            valid_codes.append(code)
        else:
            invalid_codes.append(code)
    
    if invalid_codes:
        logger.warning(f"Invalid subpart codes found: {invalid_codes}")
    
    logger.debug(f"Validated {len(valid_codes)} out of {len(subpart_codes)} subpart codes")
    return valid_codes

def get_subpart_display_name(subpart_code: str) -> str:
    """
    Get human-readable display name for subpart code.
    
    Args:
        subpart_code: EPA subpart code (e.g., 'A', 'B', 'C')
        
    Returns:
        Human-readable subpart name
    """
    if not subpart_code or pd.isna(subpart_code):
        return "Unknown"
    
    # Clean and uppercase the code
    clean_code = str(subpart_code).strip().upper()
    
    # Get description from mappings, fallback to code if not found
    description = get_subpart_description(clean_code)
    
    # Format as "Code: Description" for better readability
    if description != clean_code:  # If we found a description
        return f"{clean_code}: {description}"
    else:
        logger.warning(f"No description found for subpart code: {clean_code}")
        return clean_code

def clean_subpart_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and standardize subpart data in DataFrame.
    
    This function:
    1. Expands comma-separated subparts
    2. Validates subpart codes
    3. Removes rows with invalid subparts
    4. Standardizes subpart code format
    
    Args:
        df: Input DataFrame with subpart data
        
    Returns:
        Cleaned DataFrame with individual, valid subparts
    """
    if df.empty:
        return df.copy()
    
    logger.info(f"Starting subpart data cleaning for {len(df)} rows")
    
    # Step 1: Expand comma-separated subparts
    expanded_df = expand_comma_separated_subparts(df)
    
    if expanded_df.empty:
        logger.warning("No data remaining after subpart expansion")
        return expanded_df
    
    # Step 2: Validate and filter subpart codes
    valid_mask = expanded_df['SUBPARTS'].apply(lambda x: validate_subpart_code(str(x).strip().upper()))
    cleaned_df = expanded_df[valid_mask].copy()
    
    # Step 3: Standardize subpart codes (ensure uppercase)
    cleaned_df['SUBPARTS'] = cleaned_df['SUBPARTS'].str.strip().str.upper()
    
    invalid_count = len(expanded_df) - len(cleaned_df)
    if invalid_count > 0:
        logger.warning(f"Removed {invalid_count} rows with invalid subpart codes")
    
    logger.info(f"Subpart data cleaning complete: {len(cleaned_df)} valid rows remaining")
    return cleaned_df
#
# This module provides aggregation functionalities for the inverse dashboard functionality,
# enabling users to view subpart emissions over time and state breakdown by selected subparts.
# This complements the existing aggregation_v2.py by providing inverse data processing.
#
# Key Functions:
# - `get_subpart_timeline_data`: Aggregates emissions data by subpart over time
# - `get_state_breakdown_data`: Gets state breakdown for selected subparts
# - `prepare_subpart_timeline`: Prepares data for subpart timeline visualization
# - `prepare_state_breakdown`: Prepares data for state breakdown visualization
#
# This module follows the same patterns as aggregation_v2.py and integrates with
# the existing caching and data processing infrastructure.

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
import logging
from utils.subpart_processing import (
    expand_comma_separated_subparts,
    validate_subpart_codes,
    get_subpart_display_name,
    clean_subpart_data
)
from utils.subpart_mappings import get_valid_subpart_codes

# Configure logging for this module
logger = logging.getLogger(__name__)

def get_subpart_timeline_data(
    df: pd.DataFrame,
    year_filter: Tuple[int, int],
    subpart_filter: Optional[List[str]] = None,
    state_filter: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Aggregate emissions data by subpart over time.
    Similar to state timeline but grouped by subpart.
    
    This function processes the data to show how each subpart's emissions
    change over time, which is the inverse of the current state timeline view.
    
    Args:
        df: Input DataFrame with emissions data
        year_filter: Year range filter (start_year, end_year)
        subpart_filter: Optional list of subpart codes to filter by
        state_filter: Optional list of state codes to filter by
        
    Returns:
        DataFrame with columns: ['subpart', 'year', 'value', 'display_name']
        Ready for timeline visualization
        
    Raises:
        ValueError: If required columns are missing from the DataFrame
        TypeError: If input parameters are of incorrect type
    """
    try:
        # Validate input DataFrame
        if df.empty:
            logger.warning("Input DataFrame is empty")
            return pd.DataFrame(columns=['subpart', 'year', 'value', 'display_name'])
        
        # Check for required columns
        required_columns = ['SUBPARTS', 'GHG QUANTITY (METRIC TONS CO2e)', 'REPORTING YEAR', 'STATE']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Create a working copy and apply filters
        working_df = df.copy()
        
        # Apply year filter
        if year_filter and len(year_filter) == 2:
            start_year, end_year = year_filter
            working_df = working_df[
                (working_df['REPORTING YEAR'] >= start_year) & 
                (working_df['REPORTING YEAR'] <= end_year)
            ]
        
        # Apply state filter if provided
        if state_filter:
            working_df = working_df[working_df['STATE'].isin(state_filter)]
        
        # Standardize the emissions column name
        if 'GHG QUANTITY (METRIC TONS CO2e)' in working_df.columns:
            working_df.rename(
                columns={'GHG QUANTITY (METRIC TONS CO2e)': 'GHG_QUANTITY'},
                inplace=True
            )
        
        # Clean and expand subpart data
        # Limit data size for performance - take a sample if dataset is too large
        if len(working_df) > 10000:
            print(f"[DEBUG] Large dataset detected ({len(working_df)} rows), sampling 10000 rows for performance...")
            working_df = working_df.sample(n=10000, random_state=42)
        
        print(f"[DEBUG] About to clean subpart data with {len(working_df)} rows...")
        expanded_df = clean_subpart_data(working_df)
        print(f"[DEBUG] Cleaned and expanded to {len(expanded_df)} rows for subpart timeline")
        logger.info(f"Cleaned and expanded to {len(expanded_df)} rows for subpart timeline")
        
        # Apply subpart filter if provided
        if subpart_filter:
            expanded_df = expanded_df[expanded_df['SUBPARTS'].isin(subpart_filter)]
        
        # Aggregate by subpart and year
        timeline_data = expanded_df.groupby(['SUBPARTS', 'REPORTING YEAR']).agg({
            'GHG_QUANTITY': 'sum'
        }).reset_index()
        
        # Rename columns to match expected format for timeline visualization
        timeline_data.columns = ['subpart', 'year', 'value']
        
        # Add display names for better visualization
        timeline_data['display_name'] = timeline_data['subpart'].apply(get_subpart_display_name)
        
        # Ensure numeric types
        timeline_data['year'] = pd.to_numeric(timeline_data['year'], errors='coerce')
        timeline_data['value'] = pd.to_numeric(timeline_data['value'], errors='coerce')
        
        # Drop any rows with NaN values after conversion
        timeline_data = timeline_data.dropna(subset=['year', 'value'])
        
        # Sort by year for better visualization
        timeline_data = timeline_data.sort_values(['subpart', 'year']).reset_index(drop=True)
        
        logger.info(f"Successfully created subpart timeline data with {len(timeline_data)} rows")
        return timeline_data
        
    except Exception as e:
        logger.error(f"Error in get_subpart_timeline_data: {str(e)}")
        # Return empty DataFrame with correct structure on error
        return pd.DataFrame(columns=['subpart', 'year', 'value', 'display_name'])

def get_state_breakdown_data(
    df: pd.DataFrame,
    year_filter: Tuple[int, int],
    subpart_filter: List[str],
    state_filter: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Get state breakdown for selected subparts.
    Similar to subpart breakdown but grouped by state.
    
    This function processes the data to show which states contribute to
    the emissions for selected subparts, which is the inverse of the
    current subpart breakdown view.
    
    Args:
        df: Input DataFrame with emissions data
        year_filter: Year range filter (start_year, end_year)
        subpart_filter: List of subpart codes to analyze
        state_filter: Optional list of state codes to filter by
        
    Returns:
        Dictionary containing:
        - 'data': List of dictionaries with state breakdown data
        - 'total_emissions': Total emissions for the selected subparts
        - 'subpart_count': Number of subparts analyzed
        
    Raises:
        ValueError: If required columns are missing or subpart_filter is empty
        TypeError: If input parameters are of incorrect type
    """
    try:
        # Validate inputs
        if df.empty:
            logger.warning("Input DataFrame is empty")
            return {'data': [], 'total_emissions': 0, 'subpart_count': 0}
        
        if not subpart_filter:
            raise ValueError("subpart_filter cannot be empty for state breakdown")
        
        # Check for required columns
        required_columns = ['SUBPARTS', 'GHG QUANTITY (METRIC TONS CO2e)', 'REPORTING YEAR', 'STATE']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Create a working copy and apply filters
        working_df = df.copy()
        
        # Apply year filter
        if year_filter and len(year_filter) == 2:
            start_year, end_year = year_filter
            working_df = working_df[
                (working_df['REPORTING YEAR'] >= start_year) & 
                (working_df['REPORTING YEAR'] <= end_year)
            ]
        
        # Apply state filter if provided
        if state_filter:
            working_df = working_df[working_df['STATE'].isin(state_filter)]
        
        # Standardize the emissions column name
        if 'GHG QUANTITY (METRIC TONS CO2e)' in working_df.columns:
            working_df.rename(
                columns={'GHG QUANTITY (METRIC TONS CO2e)': 'GHG_QUANTITY'},
                inplace=True
            )
        
        # DEBUG: Log before cleaning subpart data
        print(f"[DEBUG] get_state_breakdown_data: About to clean subpart data with {len(working_df)} rows")
        print(f"[DEBUG] get_state_breakdown_data: subpart_filter = {subpart_filter}")
        
        # Clean and expand subpart data
        print(f"[DEBUG] inverse_aggregation: working_df info before clean_subpart_data: {working_df.info()}")
        expanded_df = clean_subpart_data(working_df)
        logger.info(f"Cleaned and expanded to {len(expanded_df)} rows for state breakdown")
        print(f"[DEBUG] get_state_breakdown_data: After cleaning, expanded_df has {len(expanded_df)} rows")
        
        # Filter for selected subparts
        filtered_df = expanded_df[expanded_df['SUBPARTS'].isin(subpart_filter)]
        print(f"[DEBUG] get_state_breakdown_data: After filtering for subparts, filtered_df has {len(filtered_df)} rows")
        
        if filtered_df.empty:
            logger.warning(f"No data found for selected subparts: {subpart_filter}")
            print(f"[DEBUG] get_state_breakdown_data: No data found for selected subparts")
            return {'data': [], 'total_emissions': 0, 'subpart_count': len(subpart_filter)}
        
        # Aggregate by state
        state_breakdown = filtered_df.groupby('STATE').agg({
            'GHG_QUANTITY': 'sum'
        }).reset_index()
        print(f"[DEBUG] get_state_breakdown_data: After aggregation, state_breakdown has {len(state_breakdown)} states")
        
        # Calculate total emissions
        total_emissions = state_breakdown['GHG_QUANTITY'].sum()
        print(f"[DEBUG] get_state_breakdown_data: Total emissions = {total_emissions}")
        
        # Calculate percentages
        if total_emissions > 0:
            state_breakdown['PERCENTAGE'] = (state_breakdown['GHG_QUANTITY'] / total_emissions) * 100
        else:
            state_breakdown['PERCENTAGE'] = 0
        
        # Sort by emissions quantity (descending)
        state_breakdown = state_breakdown.sort_values('GHG_QUANTITY', ascending=False).reset_index(drop=True)
        
        # Convert to list of dictionaries for visualization
        breakdown_data = []
        for _, row in state_breakdown.iterrows():
            breakdown_data.append({
                'state': row['STATE'],
                'emissions': float(row['GHG_QUANTITY']),
                'percentage': float(row['PERCENTAGE'])
            })
        
        result = {
            'data': breakdown_data,
            'total_emissions': float(total_emissions),
            'subpart_count': len(subpart_filter)
        }
        
        print(f"[DEBUG] get_state_breakdown_data: Returning {len(breakdown_data)} states in result")
        if breakdown_data:
            print(f"[DEBUG] get_state_breakdown_data: Sample data: {breakdown_data[:3]}")
        
        logger.info(f"Successfully created state breakdown for {len(subpart_filter)} subparts, {len(breakdown_data)} states")
        return result
        
    except Exception as e:
        logger.error(f"Error in get_state_breakdown_data: {str(e)}")
        # Return empty result on error
        return {'data': [], 'total_emissions': 0, 'subpart_count': 0}

def prepare_subpart_timeline(
    df: pd.DataFrame, 
    selected_subparts: List[str],
    year_filter: Tuple[int, int],
    state_filter: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Prepare data for subpart timeline visualization.
    
    This is a convenience function that wraps get_subpart_timeline_data
    with additional processing for visualization components.
    
    Args:
        df: Input DataFrame with emissions data
        selected_subparts: List of selected subpart codes
        year_filter: Year range filter (start_year, end_year)
        state_filter: Optional list of state codes to filter by
        
    Returns:
        DataFrame ready for timeline plotting
    """
    timeline_data = get_subpart_timeline_data(
        df=df,
        year_filter=year_filter,
        subpart_filter=selected_subparts,
        state_filter=state_filter
    )
    
    # If no subparts selected, return data for all subparts
    if not selected_subparts:
        timeline_data = get_subpart_timeline_data(
            df=df,
            year_filter=year_filter,
            subpart_filter=None,
            state_filter=state_filter
        )
    
    return timeline_data

def prepare_state_breakdown(
    df: pd.DataFrame,
    selected_subparts: List[str],
    year_filter: Tuple[int, int],
    state_filter: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Prepare data for state breakdown visualization.
    
    This is a convenience function that wraps get_state_breakdown_data
    with additional processing for visualization components.
    
    Args:
        df: Input DataFrame with emissions data
        selected_subparts: List of selected subpart codes
        year_filter: Year range filter (start_year, end_year)
        state_filter: Optional list of state codes to filter by
        
    Returns:
        Dictionary with state breakdown data ready for pie chart visualization
    """
    if not selected_subparts:
        logger.warning("No subparts selected for state breakdown")
        return {'data': [], 'total_emissions': 0, 'subpart_count': 0}
    
    return get_state_breakdown_data(
        df=df,
        year_filter=year_filter,
        subpart_filter=selected_subparts,
        state_filter=state_filter
    )
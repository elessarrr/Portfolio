# Context:
# This module handles data filtering and aggregation for the emissions dashboard.
# It provides functions to:
# - Filter emissions data by state, year, company, and subpart categories
# - Pre-aggregate common data combinations to improve query performance
# - Format data for visualization in charts
#
# The module uses pandas for efficient data manipulation and implements caching
# strategies to reduce processing time for frequently accessed data combinations.

import pandas as pd
from typing import List, Dict, Any, Optional
from functools import lru_cache

def get_pre_aggregated_state_year(data: pd.DataFrame) -> pd.DataFrame:
    """Pre-aggregate emissions data by state and year.
    
    This function performs the basic state-year aggregation efficiently
    without caching, focusing on optimized data processing.
    
    Args:
        data: Raw emissions DataFrame
        
    Returns:
        Aggregated DataFrame with columns: STATE, REPORTING YEAR,
        GHG QUANTITY (METRIC TONS CO2e), SUBPARTS
    """
    try:
        # Use only necessary columns to reduce memory usage
        columns = ['STATE', 'REPORTING YEAR', 'GHG QUANTITY (METRIC TONS CO2e)', 'SUBPARTS']
        data = data[columns].copy()
        
        # Convert data types efficiently
        data['REPORTING YEAR'] = pd.to_numeric(data['REPORTING YEAR'], errors='coerce')
        data['GHG QUANTITY (METRIC TONS CO2e)'] = pd.to_numeric(data['GHG QUANTITY (METRIC TONS CO2e)'], errors='coerce')
        
        # Drop rows with missing values in critical columns
        data = data.dropna(subset=['REPORTING YEAR', 'STATE', 'GHG QUANTITY (METRIC TONS CO2e)'])
        
        # Perform efficient aggregation
        return data.groupby(['STATE', 'REPORTING YEAR'], as_index=False).agg({
            'GHG QUANTITY (METRIC TONS CO2e)': 'sum',
            'SUBPARTS': lambda x: ','.join(sorted(set(','.join(str(s) for s in x).split(','))))
        })
    except Exception as e:
        print(f"[WARNING] Error in aggregation: {str(e)}")
        return pd.DataFrame(columns=['STATE', 'REPORTING YEAR', 'GHG QUANTITY (METRIC TONS CO2e)', 'SUBPARTS'])

def filter_by_subpart(
    data: pd.DataFrame,
    selected_subparts: Optional[List[str]] = None
) -> pd.DataFrame:
    """Filter data by selected subparts (categories).
    
    Args:
        data: DataFrame containing emissions data
        selected_subparts: List of selected subpart codes
        
    Returns:
        Filtered DataFrame containing only matching subparts
    
    Raises:
        KeyError: If neither 'SUBPARTS' nor 'SUBPART' column is found in the data
    """
    # Return all data if no subparts are selected
    if not selected_subparts:
        return data
        
    # Determine which subpart column name is present
    if 'SUBPARTS' in data.columns:
        subpart_col = 'SUBPARTS'
    elif 'SUBPART' in data.columns:
        subpart_col = 'SUBPART'
    else:
        raise KeyError("No subpart column found in data. Expected 'SUBPARTS' or 'SUBPART'.")
    
    # Get valid codes from both mappings and existing data
    from .subpart_mappings import get_valid_subpart_codes
    
    # Get valid codes from both mappings and existing data
    valid_subparts = get_valid_subpart_codes(selected_subparts)
    
    # Handle comma-separated subpart codes
    def has_matching_subpart(subparts_str):
        if pd.isna(subparts_str):
            return False
        facility_subparts = [s.strip() for s in str(subparts_str).split(',')]
        return any(subpart in valid_subparts for subpart in facility_subparts)
    
    # If no valid subparts found, return all data
    if not valid_subparts:
        return data
        
    return data[data[subpart_col].apply(has_matching_subpart)]

def filter_and_aggregate_data(
    raw_data: pd.DataFrame,
    selected_states: Optional[List[str]] = None,
    year_range: Optional[List[int]] = None,
    selected_companies: Optional[List[str]] = None,
    selected_subparts: Optional[List[str]] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Filter and aggregate emissions data based on selected criteria.
    
    This function uses pre-aggregated data when possible to improve performance,
    falling back to full data processing when company or subpart filters are applied.
    
    Args:
        raw_data: DataFrame containing the raw emissions data
        selected_states: List of selected state codes
        year_range: List containing [start_year, end_year]
        selected_companies: List of selected parent company names
        selected_subparts: List of selected subpart categories
        
    Returns:
        Dictionary containing:
            - main_chart_data: List of dicts with keys 'state', 'year', 'value', 'subparts'
            - parent_chart_data: List of dicts for parent company breakdown
    """
    try:
        if raw_data.empty:
            print("[DEBUG] filter_and_aggregate_data - Input data is empty")
            return {'main_chart_data': [], 'parent_chart_data': []}

        print(f"[DEBUG] filter_and_aggregate_data - Initial data shape: {raw_data.shape}")
        
        # Determine if we can use pre-aggregated data
        use_pre_aggregated = not (selected_companies or selected_subparts)
        
        if use_pre_aggregated:
            print("[DEBUG] filter_and_aggregate_data - Using pre-aggregated data")
            # Get pre-aggregated data
            aggregated_data = get_pre_aggregated_state_year(raw_data)
            
            # Apply filters to pre-aggregated data
            mask = pd.Series(True, index=aggregated_data.index)
            
            if year_range and len(year_range) == 2:
                mask &= (aggregated_data['REPORTING YEAR'] >= year_range[0]) & \
                        (aggregated_data['REPORTING YEAR'] <= year_range[1])
            
            if selected_states:
                mask &= aggregated_data['STATE'].isin(selected_states)
            
            filtered_data = aggregated_data[mask]
            
        else:
            print("[DEBUG] filter_and_aggregate_data - Using full data processing")
            # Ensure required columns exist
            required_columns = ['REPORTING YEAR', 'STATE', 'GHG QUANTITY (METRIC TONS CO2e)', 'SUBPARTS']
            missing_columns = [col for col in required_columns if col not in raw_data.columns]
            if missing_columns:
                print(f"[ERROR] filter_and_aggregate_data - Missing required columns: {missing_columns}")
                return {'main_chart_data': [], 'parent_chart_data': []}

            # Convert data types and handle missing values
            raw_data = raw_data.copy()
            raw_data['REPORTING YEAR'] = pd.to_numeric(raw_data['REPORTING YEAR'], errors='coerce')
            raw_data['GHG QUANTITY (METRIC TONS CO2e)'] = pd.to_numeric(raw_data['GHG QUANTITY (METRIC TONS CO2e)'], errors='coerce')
            
            # Drop rows with missing values in critical columns
            raw_data = raw_data.dropna(subset=['REPORTING YEAR', 'STATE', 'GHG QUANTITY (METRIC TONS CO2e)'])
            
            # Apply all filters
            mask = pd.Series(True, index=raw_data.index)
            
            if year_range and len(year_range) == 2:
                mask &= (raw_data['REPORTING YEAR'] >= year_range[0]) & \
                        (raw_data['REPORTING YEAR'] <= year_range[1])
            
            if selected_states:
                mask &= raw_data['STATE'].isin(selected_states)
                
            if selected_companies:
                mask &= raw_data['PARENT COMPANIES'].isin(selected_companies)
            
            filtered_data = raw_data[mask]
            
            if selected_subparts:
                filtered_data = filter_by_subpart(filtered_data, selected_subparts)
            
            # Group and aggregate data
            filtered_data = filtered_data.groupby(['STATE', 'REPORTING YEAR']).agg({
                'GHG QUANTITY (METRIC TONS CO2e)': 'sum',
                'SUBPARTS': lambda x: ','.join(sorted(set(','.join(str(s) for s in x).split(','))))
            }).reset_index()
        
        if filtered_data.empty:
            print("[DEBUG] filter_and_aggregate_data - No data after applying filters")
            return {'main_chart_data': [], 'parent_chart_data': []}
        
        # Format data for output
        main_chart_data = [{
            'state': str(row['STATE']),
            'year': int(row['REPORTING YEAR']),
            'value': float(row['GHG QUANTITY (METRIC TONS CO2e)']),
            'subparts': str(row['SUBPARTS'])
        } for _, row in filtered_data.iterrows()]
        
        print(f"[DEBUG] filter_and_aggregate_data - Processed {len(main_chart_data)} data points")
        
        # Process parent company data if needed
        parent_chart_data = []
        if not use_pre_aggregated and selected_companies:
            try:
                parent_chart_data = (
                    filtered_data
                    .groupby(['PARENT COMPANIES', 'REPORTING YEAR'])['GHG QUANTITY (METRIC TONS CO2e)']
                    .sum()
                    .round()
                    .reset_index()
                    .rename(columns={
                        'PARENT COMPANIES': 'company',
                        'REPORTING YEAR': 'year',
                        'GHG QUANTITY (METRIC TONS CO2e)': 'value'
                    })
                    .sort_values(['company', 'year'])
                    .to_dict('records')
                )
            except Exception as e:
                print(f"[WARNING] Error processing parent company data: {str(e)}")
        
        return {
            'main_chart_data': main_chart_data,
            'parent_chart_data': parent_chart_data
        }
        
    except Exception as e:
        print(f"[ERROR] filter_and_aggregate_data - Error processing data: {str(e)}")
        return {'main_chart_data': [], 'parent_chart_data': []}
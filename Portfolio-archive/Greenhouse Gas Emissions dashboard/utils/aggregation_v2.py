# Context
#
# This module provides enhanced aggregation functionalities for GHG emissions data,
# with a specific focus on breaking down emissions by individual subparts.
# The primary goal is to address complexities arising from comma-separated
# subpart entries in the original dataset and to ensure that percentage
# calculations are accurate and sum to 100%.
#
# Key Functions:
# - `aggregate_by_individual_subparts`: The main function that orchestrates
#   the filtering, cleaning, and aggregation of data by individual subparts.
# - `calculate_accurate_percentages`: A utility to calculate percentages
#   while correcting for rounding errors to ensure the total is exactly 100%.
# - `get_subpart_breakdown_data`: A high-level function that prepares the
#   final data structure for visualization, including grouping minor subparts
#   into an "OTHER" category.
#
# This module supersedes the older `aggregation.py` by providing more robust
# and accurate subpart handling.

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

def aggregate_by_individual_subparts(
    df: pd.DataFrame,
    year_filter: Optional[Tuple[int, int]] = None,
    state_filter: Optional[List[str]] = None,
    category_filter: Optional[str] = None
) -> pd.DataFrame:
    """
    Aggregate emissions data by individual subparts.
    
    This function ensures that:
    1. All comma-separated subparts are expanded into individual entries
    2. Emissions are properly attributed to each subpart
    3. Percentages add up to exactly 100%
    
    Args:
        df: Input DataFrame with emissions data
        year_filter: Optional year range filter (start_year, end_year)
        state_filter: Optional list of state codes to filter by
        category_filter: Optional category filter (not used in subpart breakdown)
        
    Returns:
        Aggregated DataFrame with individual subpart breakdowns
        
    Raises:
        ValueError: If required columns are missing from the DataFrame
        TypeError: If input parameters are of incorrect type
    """
    try:
        # Validate input DataFrame
        if df.empty:
            logger.warning("Input DataFrame is empty")
            return pd.DataFrame(columns=['SUBPART', 'GHG_QUANTITY', 'PERCENTAGE', 'DISPLAY_NAME'])
        
        # Check for required columns
        required_columns = ['SUBPARTS', 'GHG QUANTITY (METRIC TONS CO2e)', 'REPORTING YEAR', 'STATE']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Create a working copy and apply filters first
        working_df = df.copy()
        if year_filter and len(year_filter) == 2:
            start_year, end_year = year_filter
            working_df = working_df[
                (working_df['REPORTING YEAR'] >= start_year) & 
                (working_df['REPORTING YEAR'] <= end_year)
            ]
        
        if state_filter:
            working_df = working_df[working_df['STATE'].isin(state_filter)]

        # Standardize the emissions column name to 'GHG_QUANTITY' before processing.
        # This ensures that `clean_subpart_data` can reliably find the emissions data
        # and correctly calculate proportional emissions for expanded subparts.
        if 'GHG QUANTITY (METRIC TONS CO2e)' in working_df.columns:
            working_df.rename(
                columns={'GHG QUANTITY (METRIC TONS CO2e)': 'GHG_QUANTITY'},
                inplace=True
            )

        # Clean the data, which includes expanding subparts and calculating
        # proportional emissions. This function is expected to work with 'GHG_QUANTITY'.
        expanded_df = clean_subpart_data(working_df)
        logger.info(f"Cleaned and expanded to {len(expanded_df)} rows")

        # Aggregate by individual subparts.
        # Group by the individual subpart and sum emissions from the 'GHG_QUANTITY' column
        # created during expansion.
        aggregated = expanded_df.groupby('SUBPARTS').agg({
            'GHG_QUANTITY': 'sum'
        }).reset_index()
        
        # Rename columns for clarity
        aggregated.columns = ['SUBPART', 'GHG_QUANTITY']
        
        # Calculate accurate percentages
        aggregated = calculate_accurate_percentages(aggregated)
        
        # Add display names for better visualization
        aggregated['DISPLAY_NAME'] = aggregated['SUBPART'].apply(get_subpart_display_name)
        
        # Sort by emissions quantity (descending) for better visualization
        aggregated = aggregated.sort_values('GHG_QUANTITY', ascending=False).reset_index(drop=True)
        
        logger.info(f"Successfully aggregated {len(aggregated)} individual subparts")
        return aggregated
        
    except Exception as e:
        logger.error(f"Error in aggregate_by_individual_subparts: {str(e)}")
        # Return empty DataFrame with correct structure on error
        return pd.DataFrame(columns=['SUBPART', 'GHG_QUANTITY', 'PERCENTAGE', 'DISPLAY_NAME'])

def calculate_accurate_percentages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate percentages that sum to exactly 100%.
    
    This function handles rounding issues to ensure percentages are accurate
    and sum to exactly 100%. It uses the largest remainder method to
    distribute any rounding discrepancies.
    
    Args:
        df: DataFrame with 'GHG_QUANTITY' column
        
    Returns:
        DataFrame with added 'PERCENTAGE' column that sums to 100%
        
    Raises:
        ValueError: If GHG_QUANTITY column is missing or contains invalid data
    """
    try:
        if df.empty:
            logger.warning("Empty DataFrame provided to calculate_accurate_percentages")
            return df
        
        if 'GHG_QUANTITY' not in df.columns:
            raise ValueError("GHG_QUANTITY column is required for percentage calculation")
        
        # Create a copy to avoid modifying the original
        result_df = df.copy()
        
        # Calculate total emissions
        total_emissions = result_df['GHG_QUANTITY'].sum()
        
        if total_emissions == 0:
            logger.warning("Total emissions is zero, setting all percentages to 0")
            result_df['PERCENTAGE'] = 0.0
            return result_df
        
        # Check if the percentage calculation is correct
        raw_percentages = (result_df['GHG_QUANTITY'] / total_emissions) * 100
        
        # ADD DEBUG CHECK
        print(f"Raw percentage calculation check:")
        print(f"Sample GHG_QUANTITY: {result_df['GHG_QUANTITY'].iloc[0] if not result_df.empty else 'N/A'}")
        print(f"Total emissions: {total_emissions}")
        print(f"Sample raw percentage: {raw_percentages.iloc[0] if not raw_percentages.empty else 'N/A'}")
        
        # Round to 1 decimal place
        rounded_percentages = np.round(raw_percentages, 1)
        
        # Calculate the difference from 100%
        total_rounded = rounded_percentages.sum()
        difference = 100.0 - total_rounded
        
        # Always adjust to ensure exact 100% using largest remainder method
        if abs(difference) > 0.001:  # Adjust for any meaningful difference
            # Calculate remainders (how much each percentage was rounded)
            remainders = raw_percentages - rounded_percentages
            
            # Determine how many 0.1% adjustments we need
            adjustments_needed = int(round(abs(difference) / 0.1))
            
            if adjustments_needed > 0:
                # Sort indices by remainder magnitude (descending)
                if difference > 0:  # Need to add
                    # For positive difference, prioritize items that were rounded down the most
                    sorted_indices = remainders.nlargest(adjustments_needed).index
                    for idx in sorted_indices:
                        rounded_percentages.iloc[idx] += 0.1
                else:  # Need to subtract
                    # For a negative difference (total > 100%), we need to subtract from the values
                    # that were rounded up the LEAST. A number is rounded up when its remainder
                    # (raw - rounded) is negative. The one rounded up the least has a remainder
                    # closest to zero, which is the largest value among the negative remainders.
                    sorted_indices = remainders.nlargest(adjustments_needed).index
                    for idx in sorted_indices:
                        rounded_percentages.iloc[idx] -= 0.1
        
        result_df['PERCENTAGE'] = rounded_percentages
        
        # Final validation
        final_total = result_df['PERCENTAGE'].sum()
        if abs(final_total - 100.0) > 0.1:
            logger.warning(f"Percentage total is {final_total:.6f}%, not exactly 100%")
            logger.warning(f"Individual percentages: {result_df['PERCENTAGE'].tolist()}")
        else:
            logger.info(f"✅ Percentage calculation successful: {final_total:.6f}%")
        
        logger.info(f"Calculated percentages for {len(result_df)} subparts, total: {final_total:.6f}%")
        return result_df
        
    except Exception as e:
        logger.error(f"Error in calculate_accurate_percentages: {str(e)}")
        # Return original DataFrame with zero percentages on error
        result_df = df.copy()
        result_df['PERCENTAGE'] = 0.0
        return result_df

def get_subpart_breakdown_data(
    df: pd.DataFrame,
    year_filter: Optional[Tuple[int, int]] = None,
    state_filter: Optional[List[str]] = None,
    min_percentage_threshold: float = 1.0
) -> Dict[str, Any]:
    """
    Get formatted subpart breakdown data for visualization.
    
    This function provides a complete data structure ready for chart rendering,
    including proper grouping of small subparts and metadata for tooltips.
    
    Args:
        df: Input DataFrame with emissions data
        year_filter: Optional year range filter
        state_filter: Optional state filter
        min_percentage_threshold: Minimum percentage to show individually (default 1.0%)
        
    Returns:
        Dictionary containing:
        - 'data': List of subpart data for chart rendering
        - 'metadata': Additional information about the aggregation
        - 'total_emissions': Total emissions value
        - 'subpart_count': Number of individual subparts
    """
    try:
        # Get aggregated subpart data
        aggregated_df = aggregate_by_individual_subparts(
            df, year_filter=year_filter, state_filter=state_filter
        )
        
        if aggregated_df.empty:
            return {
                'data': [],
                'metadata': {'message': 'No data available for the selected filters'},
                'total_emissions': 0,
                'subpart_count': 0
            }
        
        # Separate subparts above and below threshold
        major_subparts = aggregated_df[aggregated_df['PERCENTAGE'] >= min_percentage_threshold]
        minor_subparts = aggregated_df[aggregated_df['PERCENTAGE'] < min_percentage_threshold]
        
        # Prepare chart data
        chart_data = []
        
        # ADD DEBUG LOGGING BEFORE RETURNING
        print("=== DEBUG: Aggregation Data Check ===")
        print(f"Sample raw emissions from aggregated_df:")
        print(aggregated_df[['SUBPART', 'GHG_QUANTITY', 'PERCENTAGE']].head())
        print(f"Total emissions: {aggregated_df['GHG_QUANTITY'].sum()}")
        print(f"Total percentage: {aggregated_df['PERCENTAGE'].sum()}")
        print("=== END DEBUG ===")
        
        # Add major subparts
        for _, row in major_subparts.iterrows():
            chart_data.append({
                'subpart': row['SUBPART'],
                'display_name': row['DISPLAY_NAME'],
                'emissions': float(row['GHG_QUANTITY']),
                'percentage': float(row['PERCENTAGE']),
                'type': 'individual'
            })
        
        # Group minor subparts if any exist
        if not minor_subparts.empty:
            total_minor_emissions = minor_subparts['GHG_QUANTITY'].sum()
            total_minor_percentage = minor_subparts['PERCENTAGE'].sum()
            minor_subpart_list = minor_subparts['SUBPART'].tolist()
            
            chart_data.append({
                'subpart': 'OTHER',
                'display_name': f'Other Subparts ({len(minor_subparts)} subparts)',
                'emissions': float(total_minor_emissions),
                'percentage': float(total_minor_percentage),
                'type': 'grouped',
                'grouped_subparts': minor_subpart_list
            })
        
        # Calculate metadata
        total_emissions = aggregated_df['GHG_QUANTITY'].sum()
        subpart_count = len(aggregated_df)
        
        # Validate final chart data percentages
        chart_total_percentage = sum(item['percentage'] for item in chart_data)
        if abs(chart_total_percentage - 100.0) > 0.1:
            logger.warning(f"Chart data percentages total {chart_total_percentage:.6f}%, not 100%")
            logger.warning(f"Chart data breakdown: {[(item['subpart'], item['percentage']) for item in chart_data]}")
        else:
            logger.info(f"✅ Chart data percentages sum correctly: {chart_total_percentage:.6f}%")
        
        metadata = {
            'total_subparts': subpart_count,
            'major_subparts': len(major_subparts),
            'minor_subparts': len(minor_subparts),
            'threshold_used': min_percentage_threshold,
            'chart_percentage_total': chart_total_percentage,
            'filters_applied': {
                'year_filter': year_filter,
                'state_filter': state_filter
            }
        }
        
        logger.info(f"Generated breakdown data for {len(chart_data)} chart elements")
        
        return {
            'data': chart_data,
            'metadata': metadata,
            'total_emissions': float(total_emissions),
            'subpart_count': subpart_count
        }
        
    except Exception as e:
        logger.error(f"Error in get_subpart_breakdown_data: {str(e)}")
        return {
            'data': [],
            'metadata': {'error': str(e)},
            'total_emissions': 0,
            'subpart_count': 0
        }

def validate_aggregation_results(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validate the results of subpart aggregation.
    
    This function performs quality checks on aggregated data to ensure
    data integrity and accuracy.
    
    Args:
        df: Aggregated DataFrame to validate
        
    Returns:
        Dictionary containing validation results and any issues found
    """
    validation_results = {
        'is_valid': True,
        'issues': [],
        'warnings': [],
        'summary': {}
    }
    
    try:
        if df.empty:
            validation_results['issues'].append('DataFrame is empty')
            validation_results['is_valid'] = False
            return validation_results
        
        # Check percentage sum
        if 'PERCENTAGE' in df.columns:
            percentage_sum = df['PERCENTAGE'].sum()
            if abs(percentage_sum - 100.0) > 0.1:
                validation_results['issues'].append(
                    f'Percentages sum to {percentage_sum:.2f}%, not 100%'
                )
                validation_results['is_valid'] = False
        
        # Check for negative values
        if 'GHG_QUANTITY' in df.columns:
            negative_count = (df['GHG_QUANTITY'] < 0).sum()
            if negative_count > 0:
                validation_results['warnings'].append(
                    f'{negative_count} rows have negative emissions values'
                )
        
        # Check for duplicate subparts
        if 'SUBPART' in df.columns:
            duplicate_count = df['SUBPART'].duplicated().sum()
            if duplicate_count > 0:
                validation_results['issues'].append(
                    f'{duplicate_count} duplicate subpart entries found'
                )
                validation_results['is_valid'] = False
        
        # Summary statistics
        validation_results['summary'] = {
            'total_rows': len(df),
            'total_emissions': float(df['GHG_QUANTITY'].sum()) if 'GHG_QUANTITY' in df.columns else 0,
            'percentage_sum': float(df['PERCENTAGE'].sum()) if 'PERCENTAGE' in df.columns else 0
        }
        
        logger.info(f"Validation completed: {'PASSED' if validation_results['is_valid'] else 'FAILED'}")
        
    except Exception as e:
        validation_results['issues'].append(f'Validation error: {str(e)}')
        validation_results['is_valid'] = False
        logger.error(f"Error during validation: {str(e)}")
    
    return validation_results
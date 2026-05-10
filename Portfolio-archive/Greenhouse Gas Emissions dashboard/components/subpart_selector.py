"""Subpart Selector Component for Inverse Dashboard

This module provides a dropdown component for selecting subparts in the inverse dashboard.
Users can select multiple subparts to analyze which states contribute to their emissions.
"""

from typing import List, Dict, Any
import dash_core_components as dcc
from utils.subpart_mappings import subpart_mappings


def create_subpart_selector() -> dcc.Dropdown:
    """
    Create a multi-select dropdown for subpart selection.
    
    This component allows users to select multiple subparts for analysis
    in the inverse dashboard. It uses the subpart mappings to provide
    user-friendly display names while maintaining the subpart codes as values.
    
    Returns:
        dcc.Dropdown: A Dash dropdown component configured for subpart selection
        
    Example:
        >>> selector = create_subpart_selector()
        >>> # Returns a dropdown with subpart options and default selections
    """
    
    # Create options from subpart mappings
    # Format: [{'label': 'C - General Stationary Fuel Combustion Sources', 'value': 'C'}, ...]
    options = [
        {
            'label': f"{code} - {name}",
            'value': code
        }
        for code, name in subpart_mappings.items()
        if name != '(Reserved)'  # Exclude reserved subparts
    ]
    
    # Sort options by subpart code for consistent ordering
    options = sorted(options, key=lambda x: x['value'])
    
    # Default selection of common subparts as specified in the plan
    default_values = ['C', 'AA', 'D']  # General Stationary Fuel, Pulp & Paper, Electricity
    
    return dcc.Dropdown(
        id='subpart-selector',
        options=options,
        value=default_values,
        multi=True,
        placeholder="Select subparts to analyze...",
        style={
            'marginBottom': '10px',
            'fontSize': '14px'
        },
        # Enable search functionality for easier navigation
        searchable=True,
        # Clear button for easy reset
        clearable=True
    )


def get_subpart_display_name(subpart_code: str) -> str:
    """
    Get the display name for a subpart code.
    
    Args:
        subpart_code: The subpart code (e.g., 'C', 'AA', 'D')
        
    Returns:
        str: The formatted display name (e.g., 'C - General Stationary Fuel Combustion Sources')
        
    Example:
        >>> get_subpart_display_name('C')
        'C - General Stationary Fuel Combustion Sources'
    """
    if subpart_code in subpart_mappings:
        return f"{subpart_code} - {subpart_mappings[subpart_code]}"
    return subpart_code  # Fallback to code if mapping not found


def validate_subpart_selection(selected_subparts: List[str]) -> List[str]:
    """
    Validate and filter subpart selections.
    
    Ensures that only valid subpart codes are included in the selection
    and removes any invalid or reserved subparts.
    
    Args:
        selected_subparts: List of selected subpart codes
        
    Returns:
        List[str]: Filtered list of valid subpart codes
        
    Example:
        >>> validate_subpart_selection(['C', 'INVALID', 'AA'])
        ['C', 'AA']
    """
    if not selected_subparts:
        return []
    
    valid_subparts = [
        subpart for subpart in selected_subparts
        if subpart in subpart_mappings and subpart_mappings[subpart] != '(Reserved)'
    ]
    
    return valid_subparts
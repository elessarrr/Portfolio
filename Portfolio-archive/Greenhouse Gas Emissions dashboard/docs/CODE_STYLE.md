# Code Style Guide

## Python Code Style

### Imports
```python
# Standard library imports first
import sys
from pathlib import Path

# Third-party imports
import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc

# Local imports
from utils.cache_utils import get_cached_data
from components.state_graph import create_state_emissions_graph
```

### Type Hints
```python
from typing import List, Dict, Optional

def filter_by_subpart(
    data: pd.DataFrame,
    selected_subparts: Optional[List[str]] = None
) -> pd.DataFrame:
    """Filter emissions data by subpart."""
    pass
```

### Docstrings
```python
def create_subpart_breakdown(
    data: List[Dict],
    selected_states: Optional[List[str]] = None,
    year_range: Optional[List[int]] = None
) -> dcc.Graph:
    """Creates a Plotly donut chart showing emissions breakdown by subpart.
    
    Args:
        data: List of dictionaries containing emissions data
            Required fields: STATE, YEAR, SUBPART, EMISSIONS, FACILITY_ID
        selected_states: List of state codes to filter by
        year_range: List of [start_year, end_year] to filter by
    
    Returns:
        A Dash Graph component containing the donut chart
    
    Example:
        >>> breakdown = create_subpart_breakdown(
        ...     data=emissions_data,
        ...     selected_states=['CA', 'NY'],
        ...     year_range=[2019, 2020]
        ... )
    """
    pass
```

### Variable Naming
- Use descriptive names that indicate purpose
- Follow standard Python naming conventions:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_CASE` for constants

### Function Structure
- Single responsibility principle
- Clear input validation
- Explicit return types
- Appropriate error handling

### Component Structure
```python
def create_component(app):
    """Create a Dash component with associated callbacks."""
    # 1. Define callbacks
    @app.callback(
        Output('component-id', 'property'),
        [Input('input-id', 'value')]
    )
    def update_component(value):
        # Input validation
        if not value:
            return default_value
            
        # Processing
        result = process_data(value)
        
        # Return formatted output
        return format_output(result)
    
    # 2. Return component layout
    return html.Div([
        dcc.Graph(id='component-id'),
        html.Div(className='component-container')
    ])
```

### Error Handling
```python
def process_data(data: pd.DataFrame) -> pd.DataFrame:
    """Process emissions data with proper error handling."""
    try:
        # Validate input
        if data.empty:
            raise ValueError("Empty dataset provided")
            
        # Process data
        result = data.groupby('SUBPART').sum()
        
        return result
        
    except KeyError as e:
        raise KeyError(f"Required column missing: {str(e)}")
    except Exception as e:
        raise RuntimeError(f"Error processing data: {str(e)}")
```

### Testing
```python
class TestComponent(unittest.TestCase):
    """Test suite for component functionality."""
    
    def setUp(self):
        """Set up test data and fixtures."""
        self.test_data = pd.DataFrame({
            'YEAR': [2020, 2021],
            'EMISSIONS': [100, 200]
        })
    
    def test_normal_operation(self):
        """Test component under normal conditions."""
        result = process_data(self.test_data)
        self.assertIsNotNone(result)
    
    def test_edge_cases(self):
        """Test component with edge cases."""
        empty_data = pd.DataFrame()
        with self.assertRaises(ValueError):
            process_data(empty_data)
```

### Comments
- Use comments to explain complex logic
- Avoid obvious comments
- Keep comments current with code changes
- Document assumptions and limitations

### Code Organization
- Group related functions together
- Separate concerns into appropriate modules
- Use consistent file structure across project
- Keep files focused and manageable in size
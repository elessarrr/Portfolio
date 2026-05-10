# GHG Dashboard API Documentation

## Components

### State Emissions Graph

#### `create_state_emissions_graph(app)`
Creates an interactive line graph showing GHG emissions trends by state over time.

**Parameters:**
- `app`: Dash application instance

**Returns:**
- Dash component containing the emissions graph

**Callback Inputs:**
- `year-range-slider`: List of [start_year, end_year]
- `state-dropdown`: List of selected state codes
- `category-dropdown`: Selected emissions category

**Graph Features:**
- Interactive legend
- Hover tooltips with detailed emissions data
- Responsive layout
- Zoom and pan capabilities

### Subpart Breakdown Graph

#### `create_subpart_breakdown(data, selected_states=None, year_range=None)`
Creates a donut chart showing emissions breakdown by EPA subpart.

**Parameters:**
- `data`: List of dictionaries containing emissions data
  - Required fields: 'STATE', 'YEAR', 'SUBPART', 'EMISSIONS', 'FACILITY_ID'
- `selected_states`: List of state codes to filter by
- `year_range`: List of [start_year, end_year] to filter by

**Returns:**
- Dash Graph component with donut chart

**Features:**
- Interactive legend
- Hover tooltips showing:
  - Emissions value
  - Percentage of total
  - Facility count
- Responsive layout

## Utilities

### Data Filtering

#### `filter_by_subpart(data, selected_subparts)`
Filters emissions data by EPA subpart.

**Parameters:**
- `data`: DataFrame with emissions data
- `selected_subparts`: List of subpart codes to include

**Returns:**
- Filtered DataFrame

### Data Caching

#### `get_cached_data(state_filter, year_range)`
Retrieves cached emissions data based on filters.

**Parameters:**
- `state_filter`: Tuple of state codes
- `year_range`: Tuple of (start_year, end_year)

**Returns:**
- Dictionary with filtered data

## Usage Examples

### Creating a State Emissions Graph
```python
from dash import Dash
from components.state_graph import create_state_emissions_graph

app = Dash(__name__)

# Add the graph to your layout
app.layout = create_state_emissions_graph(app)
```

### Creating a Subpart Breakdown
```python
from components.subpart_graph import create_subpart_breakdown

# Example data structure
data = [
    {
        'STATE': 'CA',
        'YEAR': 2020,
        'SUBPART': 'C',
        'EMISSIONS': 1000,
        'FACILITY_ID': 'F1'
    },
    # ... more data entries
]

# Create the breakdown chart
breakdown = create_subpart_breakdown(
    data=data,
    selected_states=['CA'],
    year_range=[2019, 2020]
)
```

## Configuration

### Environment Variables
None required for basic operation.

### Dependencies
- dash
- plotly
- pandas

### Browser Support
- Modern browsers (Chrome, Firefox, Safari, Edge)
- Requires JavaScript enabled
- Responsive design supports desktop and mobile devices
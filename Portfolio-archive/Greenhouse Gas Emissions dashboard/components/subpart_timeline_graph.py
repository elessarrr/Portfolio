#
# Context:
# This module creates the subpart timeline graph component for the inverse dashboard functionality.
# It displays subpart emissions over time as a line graph, which is the inverse of the current
# state timeline view. Users can select specific subparts to see their emissions trends.
#
# Key Functions:
# - validate_subpart_data: Validates DataFrame for subpart timeline plotting
# - prepare_subpart_plot_data: Prepares data for subpart timeline visualization
# - create_subpart_timeline_graph: Main component creation function with callbacks
#
# This component follows the same patterns as state_graph.py but processes subpart data
# using the inverse_aggregation utility functions. Recent changes include:
# - Removed legend display (showlegend=False) for cleaner visualization as requested by user
# - Simplified to remove unused category filter parameter

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from typing import Tuple, List, Dict, Optional
from utils.cache_utils import get_cached_data, get_cached_layout
from utils.inverse_aggregation import get_subpart_timeline_data, prepare_subpart_timeline
from utils.data_preprocessor import DataPreprocessor
from utils.feature_flags import feature_flags
from utils.performance_monitor import monitor_performance
from utils.data_manager import get_global_data
from dash.exceptions import PreventUpdate
import time
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)

def validate_subpart_data(df: pd.DataFrame) -> Tuple[bool, str]:
    """Validate the dataframe for subpart timeline plotting.
    
    This function ensures the DataFrame has the required columns and structure
    for creating subpart timeline visualizations.
    
    Args:
        df: Input dataframe to validate
        
    Returns:
        Tuple containing:
            - Boolean indicating if data is valid
            - Error message if invalid, empty string if valid
    """
    if df is None or df.empty:
        return False, "No data available"
    
    # Required columns for subpart timeline: subpart, year, value, display_name
    required_columns = ['subpart', 'year', 'value']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    
    return True, ""

def prepare_subpart_plot_data(df: pd.DataFrame, selected_subparts: List[str]) -> pd.DataFrame:
    """Prepare data for subpart timeline plot.
    
    This function filters and processes the subpart timeline data for visualization,
    ensuring numeric types and handling empty selections.
    
    Args:
        df: Input dataframe with subpart timeline data
        selected_subparts: List of selected subpart codes. If empty, all subparts will be included.
        
    Returns:
        Processed dataframe ready for plotting, containing either all subparts or selected subparts
    """
    # Return data for all subparts if none are selected, otherwise filter for selected subparts
    subparts_data = df.copy() if not selected_subparts else df[df['subpart'].isin(selected_subparts)].copy()
    
    # Ensure numeric types for plotting
    subparts_data['year'] = pd.to_numeric(subparts_data['year'], errors='coerce')
    subparts_data['value'] = pd.to_numeric(subparts_data['value'], errors='coerce')
    
    # Drop any rows with NaN values after conversion
    subparts_data = subparts_data.dropna(subset=['year', 'value'])
    
    return subparts_data

def create_subpart_timeline_graph(app):
    """Creates and configures the subpart timeline graph component.
    
    This function creates the inverse dashboard component that shows subpart emissions
    over time. It follows the same pattern as the state graph but processes subpart data.
    
    Args:
        app: The Dash application instance for registering callbacks
        
    Returns:
        A Dash component representing the subpart timeline graph with interactive controls
    """
    # Store for tracking last update timestamp to prevent excessive updates
    last_update_store = dcc.Store(id='subpart-timeline-last-update', data=0)
    
    # Create the component structure with loading indicator
    component = html.Div([
        dcc.Loading(
            id="loading-subpart-timeline",
            type="default",
            children=[
                dcc.Graph(
                    id='subpart-timeline-graph',
                    config={'displayModeBar': True}
                )
            ]
        ),
        last_update_store
    ], style={"position": "relative"})
    
    @monitor_performance
    @app.callback(
        Output('subpart-timeline-graph', 'figure'),
        [
            Input('year-range-slider', 'value'),
            Input('state-dropdown', 'value')
        ],
        [
            State('subpart-timeline-last-update', 'data')
        ]
    )
    def update_subpart_timeline(year_range, selected_states, last_update):
        """Update the subpart timeline graph based on user selections.
        
        This callback processes user inputs and creates a timeline visualization
        showing how subpart emissions change over time.
        
        Args:
            year_range: Selected year range [start_year, end_year]
            selected_states: List of selected state codes for filtering
            last_update: Timestamp of last update for debouncing
            
        Returns:
            Plotly figure object with subpart timeline visualization
        """
        # DEBUG: Log callback execution
        print(f"[DEBUG] update_subpart_timeline called with:")
        print(f"  year_range: {year_range}")
        print(f"  selected_states: {selected_states}")
        # Category parameter removed - was not used in processing
        
        # Get current timestamp for debouncing
        current_time = time.time()
        
        # Prevent excessive updates with 1 second debounce
        if last_update and current_time - last_update < 1.0:
            print(f"[DEBUG] Preventing update due to debounce")
            raise PreventUpdate
            
        try:
            # Input validation and defaults
            if not year_range or not isinstance(year_range, list) or len(year_range) != 2:
                year_range = [2010, 2023]  # Default range based on available data
            
            if not selected_states or not isinstance(selected_states, list):
                selected_states = []
            
            # Ensure year_range values are integers
            year_range = [int(year_range[0]), int(year_range[1])]
            
            # Get cached layout configuration
            layout = get_cached_layout('subpart_timeline')
            
            # Phase 4 Optimization: Try to use pre-computed aggregations first
            subpart_timeline_data = None
            
            if feature_flags.is_enabled('use_pre_aggregation'):
                try:
                    from utils.data_aggregator import get_data_aggregator
                    aggregator = get_data_aggregator()
                    
                    # Check if yearly trends are available
                    if aggregator.is_aggregation_available('yearly_trends'):
                        yearly_data = aggregator.get_aggregation('yearly_trends')
                        
                        if yearly_data is not None:
                            # Filter by year range
                            filtered_data = yearly_data[
                                (yearly_data['REPORTING YEAR'] >= year_range[0]) &
                                (yearly_data['REPORTING YEAR'] <= year_range[1])
                            ]
                            
                            if not filtered_data.empty:
                                # Convert to expected format for subpart timeline
                                timeline_data = []
                                for _, row in filtered_data.iterrows():
                                    timeline_data.append({
                                        'year': row['REPORTING YEAR'],
                                        'subpart': 'Total',  # Aggregate view
                                        'value': row['total_emissions']
                                    })
                                
                                subpart_timeline_data = pd.DataFrame(timeline_data)
                                print(f"[DEBUG] Using pre-computed yearly trends for timeline")
                                
                except Exception as e:
                    print(f"[WARNING] Failed to use pre-computed aggregations: {str(e)}")
                    subpart_timeline_data = None
            
            # Fallback to existing method if pre-computed data not available
            if subpart_timeline_data is None:
                # Load raw data using global data manager if available
                print(f"[DEBUG] Loading data...")
                df = None
                
                # Try to use global data manager if feature flag is enabled
                if feature_flags.is_enabled('use_global_data_manager'):
                    try:
                        df = get_global_data()
                        if df is not None:
                            print(f"[DEBUG] Using global data, shape: {df.shape}")
                    except Exception as e:
                        print(f"[DEBUG] Global data not available, falling back to DataPreprocessor: {e}")
                
                # Fallback to DataPreprocessor if global data not available
                if df is None:
                    print(f"[DEBUG] Loading data with DataPreprocessor...")
                    from utils.data_preprocessor import DataPreprocessor
                    preprocessor = DataPreprocessor()
                    df = preprocessor.load_data()
                    print(f"[DEBUG] Loaded data shape: {df.shape}")
                
                if df.empty:
                    print(f"[DEBUG] ERROR: No data available for processing")
                    raise ValueError("No data available for processing")
                
                # Use inverse aggregation to get subpart timeline data
                print(f"[DEBUG] Getting subpart timeline data...")
                subpart_timeline_data = get_subpart_timeline_data(
                    df=df,
                    year_filter=tuple(year_range),
                    subpart_filter=None,  # Show all subparts initially
                    state_filter=selected_states if selected_states else None
                )
            
            print(f"[DEBUG] Subpart timeline data shape: {subpart_timeline_data.shape}")
            
            # Validate the processed data
            is_valid, error_message = validate_subpart_data(subpart_timeline_data)
            if not is_valid:
                raise ValueError(error_message)
            
            # Prepare data for plotting
            print(f"[DEBUG] Preparing plot data...")
            plot_data = prepare_subpart_plot_data(subpart_timeline_data, [])
            print(f"[DEBUG] Plot data shape: {plot_data.shape}")
            if plot_data.empty:
                print(f"[DEBUG] ERROR: No data available for subpart timeline")
                raise ValueError("No data available for subpart timeline")
            
            # Create figure
            print(f"[DEBUG] Creating figure...")
            fig = go.Figure()
            
            # Add traces for each subpart
            colors = px.colors.qualitative.Set1
            
            # Get unique subparts from the data, limit to top 10 for readability
            subparts_to_plot = plot_data.groupby('subpart')['value'].sum().nlargest(10).index.tolist()
            print(f"[DEBUG] Subparts to plot: {subparts_to_plot}")
            
            if not plot_data.empty:
                for idx, subpart in enumerate(subparts_to_plot):
                    subpart_data = plot_data[plot_data['subpart'] == subpart]
                    
                    if len(subpart_data) > 0:
                        try:
                            # Get display name if available, otherwise use subpart code
                            display_name = subpart_data['display_name'].iloc[0] if 'display_name' in subpart_data.columns else subpart
                            
                            fig.add_trace(
                                go.Scatter(
                                    x=subpart_data['year'].astype(int),
                                    y=subpart_data['value'].astype(float),
                                    name=display_name,
                                    mode='lines+markers',
                                    line=dict(color=colors[idx % len(colors)]),
                                    hovertemplate=(
                                        '<b>%{x}</b><br>'
                                        'Subpart: ' + display_name + '<br>'
                                        'GHG Emissions: %{y:,.2f}<br>'
                                        '<extra></extra>'
                                    )
                                )
                            )
                        except Exception as e:
                            logger.error(f"Error adding trace for subpart {subpart}: {str(e)}")
                            continue
            
            # Update layout using cached configuration with subpart-specific settings
            try:
                # Get base layout from cache or create default
                if not layout:
                    layout = {}
                
                layout.update({
                    'title': {
                        'text': 'Subpart Emissions Over Time',
                        'font': {'size': 18},
                        'x': 0.03,
                        'xanchor': 'left',
                        'y': 0.95,  # Standardized y position for consistent alignment with state graph
                        'yanchor': 'top'
                    },
                    'xaxis': {
                        **layout.get('xaxis', {}),
                        'title': 'Year',
                        'gridcolor': 'lightgray',
                        'showgrid': True,
                        'tickmode': 'linear',
                        'range': [year_range[0], year_range[1]]
                    },
                    'yaxis': {
                        **layout.get('yaxis', {}),
                        'title': 'GHG Emissions (Metric Tons CO2e)',
                        'gridcolor': 'lightgray',
                        'showgrid': True
                    },
                    'plot_bgcolor': 'white',
                    'paper_bgcolor': 'white',
                    'hovermode': 'closest',
                    'showlegend': False,  # Legend removed for cleaner visualization
                    'legend': {
                        'orientation': 'v',
                        'yanchor': 'top',
                        'y': 1,
                        'xanchor': 'left',
                        'x': 1.02
                    }
                })
                
                fig.update_layout(layout)
                return fig
                
            except Exception as e:
                logger.error(f"Error updating layout: {str(e)}")
                # Return a basic figure with error message
                return go.Figure().add_annotation(
                    text='Error loading subpart timeline data. Please try again.',
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False, font=dict(size=16)
                )
                
        except Exception as e:
            logger.error(f"Error in update_subpart_timeline: {str(e)}")
            # Return error figure
            return go.Figure().add_annotation(
                text=f'Error: {str(e)}',
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=14, color='red')
            )
    
    return component
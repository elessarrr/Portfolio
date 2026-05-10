import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import plotly.express as px
import pandas as pd
from typing import Tuple, List, Dict, Optional
from utils.cache_utils import get_cached_data, get_cached_layout
from dash.exceptions import PreventUpdate
import time

def validate_state_data(df: pd.DataFrame) -> Tuple[bool, str]:
    """Validate the dataframe for state emissions plotting.
    
    Args:
        df: Input dataframe to validate
        
    Returns:
        Tuple containing:
            - Boolean indicating if data is valid
            - Error message if invalid, empty string if valid
    """
    if df is None or df.empty:
        return False, "No data available"
    
    required_columns = ['state', 'year', 'value']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    
    return True, ""

def prepare_state_plot_data(df: pd.DataFrame, selected_states: List[str]) -> pd.DataFrame:
    """Prepare data for state emissions plot.
    
    Args:
        df: Input dataframe with emissions data
        selected_states: List of selected state names. If empty, all states will be included.
        
    Returns:
        Processed dataframe ready for plotting, containing either all states or selected states
    """
    # Return data for all states if none are selected, otherwise filter for selected states
    states_data = df.copy() if not selected_states else df[df['state'].isin(selected_states)].copy()
    
    # Ensure numeric types
    states_data['year'] = pd.to_numeric(states_data['year'], errors='coerce')
    states_data['value'] = pd.to_numeric(states_data['value'], errors='coerce')
    
    # Drop any rows with NaN values after conversion
    states_data = states_data.dropna(subset=['year', 'value'])
    
    return states_data

def create_state_emissions_graph(app):
    """Creates and configures the state emissions graph component.
    
    Args:
        app: The Dash application instance for registering callbacks
        
    Returns:
        A Dash component representing the emissions graph with interactive controls
    """
    # Store for tracking last update timestamp
    last_update_store = dcc.Store(id='last-update-timestamp', data=0)
    
    # Create the component structure
    component = html.Div([
        dcc.Loading(
            id="loading-state-graph",
            type="default",
            children=[
                dcc.Graph(
                    id='state-emissions-graph',
                    config={'displayModeBar': True}
                )
            ]
        ),
        last_update_store
    ], style={"position": "relative"})
    
    @app.callback(
        Output('state-emissions-graph', 'figure'),
        [
            Input('year-range-slider', 'value'),
            Input('state-dropdown', 'value')
        ],
        [
            State('last-update-timestamp', 'data')
        ]
    )
    def update_graph(year_range, selected_states, last_update):
        """
        Update state emissions graph based on selected filters.
        
        Args:
            year_range: List containing [start_year, end_year]
            selected_states: List of selected state codes
            last_update: Timestamp for debouncing updates
            
        Returns:
            Plotly figure object
        """
        # Get current timestamp
        current_time = time.time()
        
        # Allow initial load or if sufficient time has passed (1 second debounce)
        if last_update and current_time - last_update < 1.0:
            raise PreventUpdate
            
        try:
            # Input validation and defaults
            if not year_range or not isinstance(year_range, list) or len(year_range) != 2:
                year_range = [2010, 2023]  # Updated default range based on available data
            
            if not selected_states or not isinstance(selected_states, list):
                selected_states = []
            
            # Ensure year_range values are integers
            year_range = [int(year_range[0]), int(year_range[1])]
            
            # Get cached layout configuration
            layout = get_cached_layout('state')
            
            # Use cached data retrieval with proper state filtering
            cache_result = get_cached_data(
                state_filter=None if not selected_states else tuple(selected_states),
                year_range=tuple(year_range)
            )
            
            if not isinstance(cache_result, dict) or 'main_chart_data' not in cache_result:
                raise ValueError("Invalid data format returned from cache")
                
            filtered_data = cache_result['main_chart_data']
            
            # Convert to DataFrame and validate
            states_data = pd.DataFrame(filtered_data)
            is_valid, error_message = validate_state_data(states_data)
            if not is_valid:
                raise ValueError(error_message)
            
            # Prepare data for plotting
            states_data = prepare_state_plot_data(states_data, selected_states)
            if states_data.empty:
                raise ValueError("No data available for selected states")
            
            # Create figure
            fig = go.Figure()
            
            # Add traces for each state
            colors = px.colors.qualitative.Set1
            
            # Get unique states from the data
            states_to_plot = selected_states if selected_states else sorted(states_data['state'].unique())
            
            if not states_data.empty:
                for idx, state in enumerate(states_to_plot):
                    state_data = states_data[states_data['state'] == state]
                    
                    if len(state_data) > 0:
                        try:
                            fig.add_trace(
                                go.Scatter(
                                    x=state_data['year'].astype(int),
                                    y=state_data['value'].astype(float),
                                    name=state,
                                    mode='lines+markers',
                                    line=dict(color=colors[idx % len(colors)]),
                                    hovertemplate=(
                                        '<b>%{x}</b><br>'
                                        'State: ' + state + '<br>'
                                        'GHG Emissions: %{y:,.2f}<br>'
                                        '<extra></extra>'
                                    )
                                )
                            )
                        except Exception as e:
                            print(f"Error adding trace for state {state}: {str(e)}")
                            continue
            
            # Update layout using cached configuration
            try:
                # Get base layout from cache
                layout.update({
                    'xaxis': {
                        **layout.get('xaxis', {}),
                        'gridcolor': 'lightgray',
                        'showgrid': True,
                        'tickmode': 'linear',
                        'range': [year_range[0], year_range[1]]
                    },
                    'yaxis': {
                        **layout.get('yaxis', {}),
                        'gridcolor': 'lightgray',
                        'showgrid': True
                    },
                    'plot_bgcolor': 'white',
                    'paper_bgcolor': 'white',
                    'hovermode': 'closest',
                    'showlegend': False  # Hide the legend to reduce clutter
                })
                
                fig.update_layout(layout)
                return fig
                
            except Exception as e:
                print(f"Error updating layout: {str(e)}")
                # Return a basic figure with error message
                return go.Figure().add_annotation(
                    text='Error loading emissions data. Please try again.',
                    xref='paper',
                    yref='paper',
                    x=0.5,
                    y=0.5,
                    showarrow=False
                )
        
        except Exception as e:
            print(f"Error in update_graph: {str(e)}")
            return go.Figure().add_annotation(
                text='Error updating graph. Please check your selections.',
                xref='paper',
                yref='paper',
                x=0.5,
                y=0.5,
                showarrow=False
            )
    
    return component
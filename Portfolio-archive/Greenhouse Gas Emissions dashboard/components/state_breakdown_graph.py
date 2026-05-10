#
# Context:
# This module creates the state breakdown graph component for the inverse dashboard functionality.
# It displays state contributions to selected subparts as a pie chart, which is the inverse
# of the current subpart breakdown view. Users can select specific subparts to see which
# states contribute most to those emissions.
#
# Key Functions:
# - format_state_pie_labels: Formats pie chart labels with enhanced readability
# - validate_state_breakdown_data: Validates DataFrame for state breakdown plotting  
# - create_state_breakdown_graph: Main component creation function with callbacks
#
# This component follows the same patterns as subpart_graph_v2.py but processes state data
# using the inverse_aggregation utility functions. Recent fixes include:
# - Corrected column name mismatches where validation expected 'state'/'percentage' but data had 'STATE'/'PERCENTAGE'
# - Removed legend display (showlegend=False) for cleaner visualization as requested by user
# - Set label threshold to 1% (threshold=1.0) to hide labels for states with less than 1% contribution
# - Implemented custom text labels with percentages only for states >= 1% to reduce visual clutter
# - Simplified to remove unused category filter parameter

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash import callback_context
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Optional, Dict, Any, Union, Tuple
import time
import logging

# Import utilities
from utils.inverse_aggregation import get_state_breakdown_data
from utils.cache_utils import get_cached_data, get_cached_layout
from utils.data_preprocessor import DataPreprocessor
from utils.feature_flags import feature_flags
from utils.performance_monitor import performance_monitor, monitor_performance
from utils.callback_debouncer import debounce_graph_callback
from dash.exceptions import PreventUpdate

# Configure logging for this component
logger = logging.getLogger(__name__)

def format_state_pie_labels(df: pd.DataFrame, threshold: float = 2.0) -> Dict[str, Any]:
    """
    Format pie chart labels for state breakdown with enhanced readability.
    
    This function creates optimized labels for the state breakdown pie chart that:
    1. Show labels only for states above the threshold
    2. Provide detailed hover information for all states
    3. Handle grouped "Other" categories appropriately
    
    Args:
        df: DataFrame with state data including 'PERCENTAGE' column
        threshold: Minimum percentage to show label (default 2%)
        
    Returns:
        Dictionary with formatted labels, hover templates, and display settings
    """
    try:
        if df.empty:
            return {
                'labels': [],
                'text_labels': [],
                'hover_template': '',
                'custom_data': []
            }
        
        # Create display labels (shown on chart)
        text_labels = [
            row['STATE'] if row['PERCENTAGE'] >= threshold else ''
            for _, row in df.iterrows()
        ]
        
        # Create hover labels (always shown in tooltips)
        labels = [row['STATE'] for _, row in df.iterrows()]
        
        # Create custom data for enhanced tooltips
        custom_data = []
        for _, row in df.iterrows():
            if row.get('type') == 'grouped' and 'grouped_states' in row:
                # For grouped "Other" category, show constituent states
                state_list = ', '.join(row['grouped_states'])
                custom_data.append(f"Includes: {state_list}")
            else:
                # For individual states, show the state code
                custom_data.append(f"State Code: {row['STATE']}")
        
        # Enhanced hover template with more information
        hover_template = (
            '<b>%{label}</b><br>' +
            'Emissions: %{value:,.0f} MT CO2e<br>' +
            'Percentage: %{percent:.1f}%<br>' +
            '%{customdata}<br>' +
            '<extra></extra>'
        )
        
        return {
            'labels': labels,
            'text_labels': text_labels,
            'hover_template': hover_template,
            'custom_data': custom_data
        }
        
    except Exception as e:
        logger.error(f"Error formatting state pie labels: {str(e)}")
        return {
            'labels': [],
            'text_labels': [],
            'hover_template': '',
            'custom_data': []
        }

def validate_state_breakdown_data(df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Validate the dataframe for state breakdown plotting.
    
    This function ensures the DataFrame has the required columns and structure
    for creating state breakdown visualizations.
    
    Args:
        df: Input dataframe to validate
        
    Returns:
        Tuple containing:
            - Boolean indicating if data is valid
            - Error message if invalid, empty string if valid
    """
    if df is None or df.empty:
        return False, "No data available for state breakdown"
    
    # Required columns for state breakdown: STATE, value, PERCENTAGE
    required_columns = ['STATE', 'value', 'PERCENTAGE']
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        return False, f"Missing required columns: {', '.join(missing_columns)}"
    
    # Check if percentages sum to approximately 100%
    total_percentage = df['PERCENTAGE'].sum()
    if abs(total_percentage - 100.0) > 0.1:  # Allow small rounding errors
        logger.warning(f"State breakdown percentages sum to {total_percentage:.2f}%, not 100%")
    
    return True, ""

def create_state_breakdown_graph(app) -> html.Div:
    """
    Create state breakdown component for inverse dashboard functionality.
    
    This component shows which states contribute most to selected subparts,
    providing the inverse view of the traditional subpart breakdown.
    
    Features:
    - State-based pie chart for selected subparts
    - Accurate percentage calculations (sums to 100%)
    - Enhanced tooltips with detailed information
    - Validation and error handling
    - Responsive design with loading indicators
    
    Args:
        app: The Dash application instance for registering callbacks
        
    Returns:
        Dash HTML component for the state breakdown graph
    """
    
    # Store for tracking last update timestamp (debouncing)
    last_update_store = dcc.Store(id='state-breakdown-last-update', data=0)
    
    # Store for validation results
    validation_store = dcc.Store(id='state-breakdown-validation-store', data={})
    
    # Create the component structure with loading indicator
    component = html.Div([
        dcc.Loading(
            id="loading-state-breakdown",
            type="default",
            children=[
                dcc.Graph(
                    id='state-breakdown-graph',
                    config={'displayModeBar': True}
                )
            ]
        ),
        last_update_store,
        validation_store
    ], style={"position": "relative"})
    
    @app.callback(
        [
            Output('state-breakdown-graph', 'figure'),
            Output('state-breakdown-validation-store', 'data')
        ],
        [
            Input('year-range-slider', 'value'),
            Input('subpart-selector', 'value')  # This would be a new input for subpart selection
        ],
        [
            State('state-breakdown-last-update', 'data')
        ]
    )
    @debounce_graph_callback(delay_ms=400, key="state_breakdown_graph")
    @monitor_performance("state_breakdown_graph_update", "state_breakdown_graph")
    def update_state_breakdown_graph(year_range, selected_subparts, last_update):
        """
        Update state breakdown graph based on selected subparts.
        
        This callback processes user inputs and creates a pie chart visualization
        showing which states contribute most to the selected subparts.
        
        Args:
            year_range: Selected year range [start_year, end_year]
            selected_subparts: List of selected subpart codes
            last_update: Timestamp of last update for debouncing
            
        Returns:
            Tuple of (Plotly figure object, validation results)
        """
        # Safety check: Ensure we always return a tuple to prevent Dash schema errors
        try:
            # DEBUG: Log callback execution
            print(f"[DEBUG] update_state_breakdown_graph called with:")
            print(f"  year_range: {year_range}")
            print(f"  selected_subparts: {selected_subparts}")
            # Category parameter removed - was not used in processing
            
            # Get current timestamp for debouncing
            current_time = time.time()
            
            # Prevent excessive updates with 1 second debounce
            if last_update and current_time - last_update < 1.0:
                print(f"[DEBUG] Preventing update due to debounce")
                raise PreventUpdate
            # Input validation and defaults
            if not year_range or not isinstance(year_range, list) or len(year_range) != 2:
                year_range = [2010, 2023]  # Default range
            
            if not selected_subparts or not isinstance(selected_subparts, list):
                # Default to showing top subparts if none selected
                selected_subparts = ['C', 'AA', 'D']  # Common subparts
            
            # Ensure year_range values are integers
            year_range = [int(year_range[0]), int(year_range[1])]
            
            # Phase 4 Optimization: Try to use pre-computed aggregations first
            breakdown_result = None
            
            if feature_flags.is_enabled('use_pre_aggregation'):
                try:
                    from utils.data_aggregator import get_data_aggregator
                    aggregator = get_data_aggregator()
                    
                    # Check if state-subpart aggregations are available
                    if aggregator.is_aggregation_available('state_subpart_totals'):
                        state_subpart_data = aggregator.get_aggregation('state_subpart_totals')
                        
                        if state_subpart_data is not None:
                            # Filter by selected subparts
                            filtered_data = state_subpart_data[
                                state_subpart_data['SUBPART'].isin(selected_subparts)
                            ]
                            
                            if not filtered_data.empty:
                                # Aggregate by state for the selected subparts
                                state_totals = filtered_data.groupby('STATE')[
                                    'GHG QUANTITY (METRIC TONS CO2e)'
                                ].sum().reset_index()
                                
                                # Calculate percentages
                                total_emissions = state_totals['GHG QUANTITY (METRIC TONS CO2e)'].sum()
                                state_totals['PERCENTAGE'] = (
                                    state_totals['GHG QUANTITY (METRIC TONS CO2e)'] / total_emissions * 100
                                )
                                
                                # Format as expected by the visualization
                                breakdown_data = []
                                for _, row in state_totals.iterrows():
                                    breakdown_data.append({
                                        'state': row['STATE'],
                                        'emissions': row['GHG QUANTITY (METRIC TONS CO2e)'],
                                        'percentage': row['PERCENTAGE']
                                    })
                                
                                breakdown_result = {
                                    'data': breakdown_data,
                                    'total_emissions': total_emissions
                                }
                                
                                print(f"[DEBUG] Using pre-computed aggregations for state breakdown")
                                
                except Exception as e:
                    print(f"[WARNING] Failed to use pre-computed aggregations: {str(e)}")
                    breakdown_result = None
            
            # Fallback to existing method if pre-computed data not available
            if breakdown_result is None:
                # Load raw data for processing - use global data manager when available
                if feature_flags.is_enabled('use_global_data_manager'):
                    from utils.data_manager import get_global_data
                    df = get_global_data()
                    if df is None:
                        print("[WARNING] Global data not available in state_breakdown_graph, falling back to DataPreprocessor")
                        preprocessor = DataPreprocessor()
                        df = preprocessor.load_data()
                else:
                    # Fallback to DataPreprocessor
                    preprocessor = DataPreprocessor()
                    df = preprocessor.load_data()
                
                if df.empty:
                    empty_fig = go.Figure().add_annotation(
                        text='No data available for state breakdown',
                        xref='paper', yref='paper', x=0.5, y=0.5, showarrow=False
                    )
                    return empty_fig, {'error': 'No data available'}
                
                # DEBUG: Add debugging before calling get_state_breakdown_data
                print(f"[DEBUG] About to call get_state_breakdown_data with:")
                print(f"  year_range: {year_range}")
                print(f"  selected_subparts: {selected_subparts}")
                print(f"  df shape: {df.shape}")
                
                # Use inverse aggregation to get state breakdown data
                breakdown_result = get_state_breakdown_data(
                    df=df,
                    year_filter=tuple(year_range),
                    subpart_filter=selected_subparts,
                    state_filter=None  # Show all states
                )
            
            # DEBUG: Log the result structure
            print(f"[DEBUG] get_state_breakdown_data returned:")
            print(f"  type: {type(breakdown_result)}")
            print(f"  keys: {breakdown_result.keys() if isinstance(breakdown_result, dict) else 'Not a dict'}")
            if isinstance(breakdown_result, dict) and 'data' in breakdown_result:
                print(f"  data length: {len(breakdown_result['data'])}")
                print(f"  total_emissions: {breakdown_result.get('total_emissions', 'N/A')}")
            
            if not breakdown_result or 'data' not in breakdown_result or not breakdown_result['data']:
                print(f"[DEBUG] No valid breakdown data found")
                error_fig = go.Figure().add_annotation(
                    text='No breakdown data available for selected subparts',
                    xref='paper', yref='paper', x=0.5, y=0.5, showarrow=False
                )
                return error_fig, {'error': 'No breakdown data'}
            
            # Convert the data format to what the visualization expects
            breakdown_data = breakdown_result['data']
            breakdown_df = pd.DataFrame(breakdown_data)
            
            # Rename columns to match expected format
            if 'state' in breakdown_df.columns:
                breakdown_df.rename(columns={'state': 'STATE'}, inplace=True)
            if 'emissions' in breakdown_df.columns:
                breakdown_df.rename(columns={'emissions': 'value'}, inplace=True)
            if 'percentage' in breakdown_df.columns:
                breakdown_df.rename(columns={'percentage': 'PERCENTAGE'}, inplace=True)
            
            print(f"[DEBUG] Converted breakdown_df shape: {breakdown_df.shape}")
            print(f"[DEBUG] Breakdown_df columns: {breakdown_df.columns.tolist()}")
            if not breakdown_df.empty:
                print(f"[DEBUG] Sample data: {breakdown_df.head(3).to_dict('records')}")
            
            # Validate the breakdown data
            is_valid, error_message = validate_state_breakdown_data(breakdown_df)
            if not is_valid:
                error_fig = go.Figure().add_annotation(
                    text=f'Data validation error: {error_message}',
                    xref='paper', yref='paper', x=0.5, y=0.5, showarrow=False
                )
                return error_fig, {'error': error_message}
            
            # Format labels for the pie chart - only show labels for states >= 1%
            label_config = format_state_pie_labels(breakdown_df, threshold=1.0)
            
            # Create the pie chart
            fig = go.Figure()
            
            if not breakdown_df.empty:
                # Use a consistent color palette
                colors = px.colors.qualitative.Set3
                
                # Create custom text labels with percentages for states >= 1% only
                custom_text_labels = [
                    f"{row['STATE']}\n{row['PERCENTAGE']:.1f}%" if row['PERCENTAGE'] >= 1.0 else ''
                    for _, row in breakdown_df.iterrows()
                ]
                
                fig.add_trace(
                    go.Pie(
                        labels=label_config['labels'],
                        values=breakdown_df['PERCENTAGE'],  # ✅ FIX: Use percentage values instead
                        text=custom_text_labels,
                        textinfo='text',  # Only show custom text labels
                        textposition='auto',
                        hovertemplate=(
                            '<b>%{label}</b><br>' +
                            'Emissions: %{customdata:,.0f} MT CO2e<br>' +
                            'Percentage: %{value:.1f}%<br>' +
                            '<extra></extra>'
                        ),
                        customdata=breakdown_df['value'],  # Pass emissions as custom data for hover
                    )
                )
                
                # Update layout
                subpart_list = ', '.join(selected_subparts)
                fig.update_layout(
                    title={
                        'text': f'State Breakdown for Subparts: {subpart_list}',
                        'font': {'size': 18},
                        'x': 0.03,
                        'xanchor': 'left',
                        'y': 0.95,  # Standardized y position for consistent alignment with other graphs
                        'yanchor': 'top'
                    },
                    showlegend=False,  # Legend removed for cleaner visualization
                    legend={
                        'orientation': 'v',
                        'yanchor': 'middle',
                        'y': 0.5,
                        'xanchor': 'left',
                        'x': 1.05
                    },
                    margin=dict(l=20, r=150, t=60, b=20),
                    paper_bgcolor='white',
                    plot_bgcolor='white'
                )
                
                # Add summary information
                total_emissions = breakdown_df['value'].sum()
                summary_text = f"Total Emissions: {total_emissions:,.0f} MT CO2e"
                
                fig.add_annotation(
                    text=summary_text,
                    xref='paper', yref='paper',
                    x=0.5, y=-0.1,
                    xanchor='center', yanchor='top',
                    showarrow=False,
                    font=dict(size=12, color='gray')
                )
            
            else:
                # Empty data case
                fig.add_annotation(
                    text='No state breakdown data available for selected criteria',
                    xref='paper', yref='paper',
                    x=0.5, y=0.5, xanchor='center', yanchor='middle',
                    showarrow=False, font=dict(size=14)
                )
            
            # Return figure and validation results
            validation_results = {
                'is_valid': is_valid,
                'total_states': len(breakdown_df),
                'total_emissions': breakdown_df['value'].sum() if not breakdown_df.empty else 0,
                'percentage_sum': breakdown_df['PERCENTAGE'].sum() if not breakdown_df.empty else 0
            }
            
            return fig, validation_results
            
        except PreventUpdate:
            # Re-raise PreventUpdate to maintain Dash functionality
            raise
        except Exception as e:
            logger.error(f"Error in update_state_breakdown_graph: {str(e)}")
            print(f"[ERROR] Exception in update_state_breakdown_graph: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Return error figure and validation data (ensure we always return a tuple)
            error_fig = go.Figure().add_annotation(
                text=f'Error: {str(e)}',
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=14, color='red')
            )
            return error_fig, {'error': str(e), 'is_valid': False}
            
        # Final safety net - ensure we never return None
        except:
            error_fig = go.Figure().add_annotation(
                text='Unexpected error occurred',
                xref="paper", yref="paper",
                x=0.5, y=0.5, xanchor='center', yanchor='middle',
                showarrow=False, font=dict(size=14, color='red')
            )
            return error_fig, {'error': 'Unexpected error', 'is_valid': False}
    
    return component
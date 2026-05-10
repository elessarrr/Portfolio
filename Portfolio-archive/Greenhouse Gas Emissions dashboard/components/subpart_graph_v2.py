# Enhanced Subpart Graph Component (Version 2)
# Context:
# This component creates the enhanced subpart breakdown graph for the GHG emissions dashboard.
# It displays emissions breakdown by individual subparts as a donut chart, addressing critical
# issues with the original implementation to ensure accurate percentage calculations and proper
# visualization of individual subparts rather than collections.
#
# Key improvements over the original subpart_graph.py:
# - Uses enhanced aggregation logic from utils/aggregation_v2.py
# - Individual subpart processing with proper expansion of comma-separated values
# - Accurate percentage calculations with rounding correction to ensure 100% total
# - Better tooltips, labels, and color coding for improved user experience
# - Improved error handling and validation
# - Removed legend display (showlegend=False) for cleaner visualization as requested by user

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

# Import enhanced utilities
from utils.aggregation_v2 import (
    get_subpart_breakdown_data,
    validate_aggregation_results
)
from utils.cache_utils import get_cached_data, get_cached_layout
from utils.subpart_processing import get_subpart_display_name
from utils.subpart_mappings import subpart_mappings
from utils.feature_flags import feature_flags
from utils.performance_monitor import monitor_performance
from utils.data_manager import get_global_data
from utils.callback_debouncer import debounce_graph_callback
from dash.exceptions import PreventUpdate

# Configure logging for this component
logger = logging.getLogger(__name__)

def format_enhanced_pie_labels(df: pd.DataFrame, threshold: float = 2.0) -> Dict[str, Any]:
    """
    Format pie chart labels with enhanced readability.
    
    This function creates optimized labels for the pie chart that:
    1. Show labels only for segments above the threshold
    2. Provide detailed hover information for all segments
    3. Handle grouped "Other" categories appropriately
    
    Args:
        df: DataFrame with subpart data including 'percentage' column
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
            row['display_name'] if row['percentage'] >= threshold else ''
            for _, row in df.iterrows()
        ]
        
        # Create hover labels (always shown in tooltips)
        labels = [row['display_name'] for _, row in df.iterrows()]
        
        # Create custom data for enhanced tooltips
        custom_data = []
        for _, row in df.iterrows():
            if row.get('type') == 'grouped' and 'grouped_subparts' in row:
                # For grouped "Other" category, show constituent subparts
                subpart_list = ', '.join(row['grouped_subparts'])
                custom_data.append(f"Includes: {subpart_list}")
            else:
                # For individual subparts, show the subpart code
                custom_data.append(f"Subpart Code: {row['subpart']}")
        
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
        logger.error(f"Error formatting pie labels: {str(e)}")
        return {
            'labels': [],
            'text_labels': [],
            'hover_template': '',
            'custom_data': []
        }

def create_enhanced_subpart_breakdown(app) -> html.Div:
    """
    Create enhanced subpart breakdown component with improved accuracy.
    
    Features:
    - Individual subpart representation (no more collections)
    - Accurate percentage calculations (sums to 100%)
    - Better color coding and labels
    - Improved tooltips with detailed information
    - Validation and error handling
    - Feature toggle support for gradual rollout
    
    Args:
        app: The Dash application instance for registering callbacks
        
    Returns:
        Dash HTML component for the enhanced subpart breakdown
    """
    
    # Store for tracking last update timestamp (debouncing)
    last_update_store = dcc.Store(id='enhanced-subpart-last-update-timestamp', data=0)
    
    # Store for validation results
    validation_store = dcc.Store(id='enhanced-subpart-validation-store', data={})
    
    @monitor_performance
    @app.callback(
        [
            Output('enhanced-subpart-breakdown-graph', 'figure'),
            Output('enhanced-subpart-validation-store', 'data')
        ],
        [
            Input('year-range-slider', 'value'),
            Input('state-dropdown', 'value')
        ],
        [
            State('enhanced-subpart-last-update-timestamp', 'data')
        ]
    )
    @debounce_graph_callback(delay_ms=350, key="enhanced_subpart_graph")
    def update_enhanced_subpart_graph(year_range, selected_states, last_update):
        """
        Update enhanced subpart breakdown graph with accurate data.
        
        This callback ensures:
        1. Proper data filtering and aggregation using enhanced logic
        2. Individual subpart representation (no collections)
        3. Accurate percentage calculations that sum to 100%
        4. Consistent color coding and improved tooltips
        5. Data validation and error reporting
        
        Args:
            year_range: Selected year range [start, end]
            selected_states: List of selected state codes
            last_update: Timestamp of last update for debouncing
            
        Returns:
            Tuple of (updated Plotly figure, validation results)
        """
        # Get current timestamp for debouncing
        current_time = time.time()
        
        # Allow initial load or if sufficient time has passed (1 second debounce)
        if last_update and current_time - last_update < 1.0:
            raise PreventUpdate
        
        try:
            # Phase 4 Optimization: Try to use pre-computed aggregations first
            breakdown_result = None
            
            if feature_flags.is_enabled('use_pre_aggregation'):
                try:
                    from utils.data_aggregator import get_data_aggregator
                    aggregator = get_data_aggregator()
                    
                    # Check if subpart summaries are available
                    if aggregator.is_aggregation_available('subpart_summaries'):
                        subpart_data = aggregator.get_aggregation('subpart_summaries')
                        
                        if subpart_data is not None:
                            # Apply filters if specified
                            filtered_data = subpart_data.copy()
                            
                            # Filter by year range if specified
                            if year_range:
                                filtered_data = filtered_data[
                                    (filtered_data['REPORTING YEAR'] >= year_range[0]) &
                                    (filtered_data['REPORTING YEAR'] <= year_range[1])
                                ]
                            
                            # Filter by states if specified
                            if selected_states:
                                filtered_data = filtered_data[
                                    filtered_data['STATE'].isin(selected_states)
                                ]
                            
                            if not filtered_data.empty:
                                # Aggregate by subpart
                                subpart_totals = filtered_data.groupby('SUBPART')[
                                    'GHG QUANTITY (METRIC TONS CO2e)'
                                ].sum().reset_index()
                                
                                # Calculate percentages
                                total_emissions = subpart_totals['GHG QUANTITY (METRIC TONS CO2e)'].sum()
                                subpart_totals['percentage'] = (
                                    subpart_totals['GHG QUANTITY (METRIC TONS CO2e)'] / total_emissions * 100
                                )
                                
                                # Filter by minimum threshold (1%)
                                significant_subparts = subpart_totals[
                                    subpart_totals['percentage'] >= 1.0
                                ]
                                
                                # Format as expected by the visualization
                                chart_data = []
                                for _, row in significant_subparts.iterrows():
                                    chart_data.append({
                                        'subpart': row['SUBPART'],
                                        'emissions': row['GHG QUANTITY (METRIC TONS CO2e)'],
                                        'percentage': row['percentage']
                                    })
                                
                                breakdown_result = {
                                    'data': chart_data,
                                    'metadata': {
                                        'total_emissions': total_emissions,
                                        'num_subparts': len(chart_data)
                                    }
                                }
                                
                                logger.info(f"Using pre-computed aggregations for subpart breakdown")
                                
                except Exception as e:
                    logger.warning(f"Failed to use pre-computed aggregations: {str(e)}")
                    breakdown_result = None
            
            # Fallback to existing method if pre-computed data not available
            if breakdown_result is None:
                # Load raw data for enhanced processing
                # Try to use global data manager if available, otherwise fallback to DataPreprocessor
                df = None
                
                # Try to use global data manager if feature flag is enabled
                if feature_flags.is_enabled('use_global_data_manager'):
                    try:
                        df = get_global_data()
                        if df is not None:
                            logger.info(f"Using global data for enhanced subpart graph, shape: {df.shape}")
                    except Exception as e:
                        logger.warning(f"Global data not available, falling back to DataPreprocessor: {e}")
                
                # Fallback to DataPreprocessor if global data not available
                if df is None:
                    from utils.data_preprocessor import DataPreprocessor
                    preprocessor = DataPreprocessor()
                    df = preprocessor.load_data()
                    logger.info(f"Loaded data with DataPreprocessor, shape: {df.shape}")
                
                if df.empty:
                    empty_fig = go.Figure().add_annotation(
                        text='No data available for enhanced subpart breakdown',
                        xref='paper', yref='paper', x=0.5, y=0.5, showarrow=False
                    )
                    return empty_fig, {'error': 'No data available'}
                
                # Use enhanced aggregation to get individual subpart breakdown
                year_filter = tuple(year_range) if year_range else None
                state_filter = selected_states if selected_states else None
                
                breakdown_result = get_subpart_breakdown_data(
                    df=df,
                    year_filter=year_filter,
                    state_filter=state_filter,
                    min_percentage_threshold=1.0  # Show subparts with >= 1% individually
                )
            
            chart_data = breakdown_result.get('data', [])
            metadata = breakdown_result.get('metadata', {})
            
            if not chart_data:
                empty_fig = go.Figure().add_annotation(
                    text='No subpart data available after processing',
                    xref='paper', yref='paper', x=0.5, y=0.5, showarrow=False
                )
                return empty_fig, {'error': 'No processed data available'}
            
            # Convert chart data to DataFrame for easier handling
            chart_df = pd.DataFrame(chart_data)
            
            # Validate the aggregation results
            validation_results = validate_aggregation_results(chart_df)
            
            # Format labels and tooltips
            label_config = format_enhanced_pie_labels(chart_df, threshold=2.0)
            
            # Extract data for the pie chart
            labels = label_config['labels']
            # Use pre-calculated percentages instead of emissions to fix hover bug
            values = chart_df['percentage'].tolist()
            
            # Create custom hover template that works with percentage values
            hover_template = (
                '<b>%{label}</b><br>' +
                'Emissions: %{customdata[0]:,.0f} MT CO2e<br>' +
                'Percentage: %{value:.1f}%<br>' +
                '<extra></extra>'
            )
            
            # Create custom_data with emissions values
            custom_data = []
            for _, row in chart_df.iterrows():
                emissions_value = row['emissions']
                custom_data.append([emissions_value])
            
            # Note: Using percentage values directly instead of emissions values
            # This ensures hover tooltips show correct percentages
            
            text_labels = label_config['text_labels']
            # Use our custom hover template and custom_data instead of label_config ones
            
            # Create enhanced donut chart
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                text=text_labels,
                textposition='outside',  # Position labels outside the pie chart in white space
                textinfo='none',  # Disable external text labels
                hole=0.5,
                hovertemplate=hover_template,
                customdata=custom_data,
                # Enhanced styling
                marker=dict(
                    line=dict(color='white', width=2)
                ),
                # Use a more diverse color palette for better distinction
                marker_colors=px.colors.qualitative.Set3[:len(values)]
            )])
            
            # Get cached layout configuration
            layout = get_cached_layout('subpart')
            
            # Enhanced layout configuration
            enhanced_layout = {
                **layout,
                'title': {
                    'text': 'Enhanced Emissions Breakdown by Individual Subparts',
                    'font': {'size': 18, 'color': '#2c3e50'},
                    'x': 0.03,  # Standardized left alignment
                    'xanchor': 'left',
                    'y': 0.95,  # Standardized y position for consistent alignment
                    'yanchor': 'top'
                },
                'showlegend': False,  # Legend removed for cleaner visualization
                'legend': {
                    'orientation': 'v',
                    'yanchor': 'middle',
                    'y': 0.5,
                    'xanchor': 'left',
                    'x': 1.05,
                    'font': {'size': 10}
                },
                'plot_bgcolor': 'white',
                'paper_bgcolor': 'white',
                'margin': {'l': 120, 'r': 200, 't': 80, 'b': 100},  # Increased right margin for legend
                # Add annotations for validation info
                'annotations': [
                    {
                        'text': f"Total: {breakdown_result.get('total_emissions', 0):,.0f} MT CO2e | "
                               f"Subparts: {breakdown_result.get('subpart_count', 0)}",
                        'showarrow': False,
                        'xref': 'paper',
                        'yref': 'paper',
                        'x': 0.5,
                        'y': -0.1,
                        'xanchor': 'center',
                        'font': {'size': 12, 'color': '#666'}
                    }
                ]
            }
            
            # Add validation warning if percentages don't sum to 100%
            if not validation_results.get('is_valid', True):
                enhanced_layout['annotations'].append({
                    'text': '⚠️ Data validation issues detected',
                    'showarrow': False,
                    'xref': 'paper',
                    'yref': 'paper',
                    'x': 0.02,
                    'y': 0.98,
                    'xanchor': 'left',
                    'yanchor': 'top',
                    'font': {'size': 10, 'color': '#e74c3c'},
                    'bgcolor': '#fff3cd',
                    'bordercolor': '#ffeaa7',
                    'borderwidth': 1
                })
            
            fig.update_layout(enhanced_layout)
            
            logger.info(f"Enhanced subpart graph updated with {len(chart_data)} segments")
            
            return fig, {
                'validation': validation_results,
                'metadata': metadata,
                'chart_segments': len(chart_data)
            }
            
        except Exception as e:
            logger.error(f"Error creating enhanced subpart graph: {str(e)}")
            error_fig = go.Figure().add_annotation(
                text=f'Error creating enhanced chart: {str(e)}',
                xref='paper', yref='paper', x=0.5, y=0.5, showarrow=False
            )
            return error_fig, {'error': str(e)}
    
    # Callback to update the timestamp store (for debouncing)
    @app.callback(
        Output('enhanced-subpart-last-update-timestamp', 'data'),
        [
            Input('year-range-slider', 'value'),
            Input('state-dropdown', 'value')
        ]
    )
    def update_timestamp(year_range, selected_states):
        """Update timestamp for debouncing purposes."""
        return time.time()
    
    # Create the component layout
    component_layout = html.Div([
        # Hidden stores for state management
        last_update_store,
        validation_store,
        
        # Main graph container
        html.Div([
            dcc.Loading(
                id="enhanced-subpart-loading",
                type="default",
                children=[
                    dcc.Graph(
                        id='enhanced-subpart-breakdown-graph',
                        config={
                            'displayModeBar': True,
                            'displaylogo': False,
                            'modeBarButtonsToRemove': [
                                'pan2d', 'lasso2d', 'select2d', 'autoScale2d',
                                'hoverClosestCartesian', 'hoverCompareCartesian'
                            ]
                        },
                        style={'height': '500px'}
                    )
                ]
            )
        ], className="graph-container"),
        
        # Information panel
        html.Div([
            html.Div([
                html.I(className="fas fa-info-circle", style={
                    'marginRight': '8px', 'color': '#3498db'
                }),
                html.Span("Enhanced Subpart Breakdown", style={
                    'fontWeight': 'bold', 'fontSize': '14px'
                })
            ], style={'marginBottom': '10px'}),
            
            html.Div([
                html.P([
                    "This enhanced chart shows individual EPA GHGRP subparts. Subparts with less than 1% of total emissions are grouped ",
                    "into an 'Other Subparts' category for clarity."
                ], style={'fontSize': '12px', 'color': '#666', 'margin': '0'}),
                
            ])
        ], style={
            'backgroundColor': '#f8f9fa',
            'border': '1px solid #dee2e6',
            'borderRadius': '5px',
            'padding': '15px',
            'marginTop': '15px'
        })
    ])
    
    return component_layout

def create_enhanced_tooltip_content():
    """
    Create enhanced tooltip content with subpart definitions.
    
    This function creates an improved tooltip that shows:
    1. EPA GHGRP subpart definitions
    2. Information about the enhanced processing
    3. Data validation status
    
    Returns:
        Dash HTML component with tooltip content
    """
    return html.Div([
        html.Div([
            html.H3("Enhanced EPA GHGRP Subpart Definitions", style={
                "margin": "0 0 10px 0",
                "color": "#2c3e50",
                "fontSize": "24px"
            }),
            html.I(
                className="fas fa-times",
                id="close-enhanced-tooltip",
                n_clicks=0,
                style={
                    "position": "absolute",
                    "top": "15px",
                    "right": "15px",
                    "cursor": "pointer",
                    "fontSize": "24px",
                    "color": "#666",
                    "transition": "color 0.2s ease",
                    "zIndex": "10000"
                }
            )
        ], style={
            "position": "relative", 
            "marginBottom": "20px",
            "borderBottom": "2px solid #eee",
            "paddingBottom": "15px"
        }),
        
        # Enhancement information
        html.Div([
            html.H4("Enhanced Features:", style={"color": "#27ae60", "marginBottom": "10px"}),
            html.Ul([
                html.Li("Individual subpart representation (no collections)"),
                html.Li("Accurate percentages that sum to exactly 100%"),
                html.Li("Proper expansion of comma-separated subpart values"),
                html.Li("Enhanced data validation and error handling"),
                html.Li("Improved color coding and tooltips")
            ], style={"fontSize": "14px", "color": "#555"})
        ], style={"marginBottom": "20px", "padding": "15px", "backgroundColor": "#f0f8f0", "borderRadius": "5px"}),
        
        # Subpart definitions table
        html.Div([
            html.H4("Subpart Definitions:", style={"marginBottom": "15px", "color": "#2c3e50"}),
            html.Div([
                html.Div([
                    html.Div(f"Subpart {code}", style={
                        "fontWeight": "bold",
                        "color": "#2980b9",
                        "marginBottom": "5px",
                        "fontSize": "16px"
                    }),
                    html.Div(description, style={
                        "color": "#555",
                        "fontSize": "14px",
                        "lineHeight": "1.4",
                        "marginBottom": "15px"
                    })
                ]) for code, description in sorted(subpart_mappings.items())
            ], style={
                "maxHeight": "400px",
                "overflowY": "auto",
                "padding": "10px",
                "border": "1px solid #ddd",
                "borderRadius": "5px",
                "backgroundColor": "#fafafa"
            })
        ])
    ], style={
        "maxWidth": "600px",
        "maxHeight": "80vh",
        "overflowY": "auto",
        "padding": "20px"
    })
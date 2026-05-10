from dash import html, dcc, callback_context
# Context: This component creates and manages the subpart breakdown chart (pie chart) that displays
# emissions data categorized by EPA GHGRP subparts. It includes interactive tooltips, dynamic filtering,
# and a collapsible mapping table for subpart definitions.
# Recent addition: Standardized title margins for consistent heading alignment with state graph.
# Simplified to remove unused category filter parameter.

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import List, Optional, Dict, Any, Union, Tuple
from utils.cache_utils import get_cached_data, get_cached_layout
from utils.subpart_mappings import subpart_mappings
from dash.exceptions import PreventUpdate
import time

def format_pie_labels(values: List[float], labels: List[str], threshold: float = 5.0) -> Tuple[List[str], str]:
    """Format pie chart labels based on percentage threshold.
    
    Args:
        values: Values for pie chart segments
        labels: Labels for segments
        threshold: Minimum percentage to show label (default: 5.0)
        
    Returns:
        Tuple containing:
            - List of formatted labels (empty string for values below threshold)
            - Hover template string
    """
    total = sum(values)
    percentages = [(v / total) * 100 for v in values]
    
    # Format labels based on threshold
    formatted_labels = [
        label if pct >= threshold else ""
        for label, pct in zip(labels, percentages)
    ]
    
    # Create hover template that always shows the label
    hover_template = (
        '<b>%{label}</b><br>' +
        'Emissions: %{value:,.0f} MT CO2e<br>' +
        'Percentage: %{percent:.1f}%<br>' +
        '%{customdata}<br>' +
        '<extra></extra>'
    )
    
    return formatted_labels, hover_template

def create_subpart_breakdown(app):
    @app.callback(
        Output('tooltip-state-store', 'data'),
        [Input('subpart-info-icon', 'n_clicks'),
         Input('close-tooltip', 'n_clicks'),
         Input('tooltip-overlay', 'n_clicks')],
        [State('tooltip-state-store', 'data')],
        prevent_initial_call=True
    )
    def update_tooltip_state(info_clicks, close_clicks, overlay_clicks, current_state):
        from dash import no_update
        ctx = callback_context
        if not ctx.triggered:
            return no_update

        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        if trigger_id == 'subpart-info-icon':
            return 'visible'
        elif trigger_id in ['close-tooltip', 'tooltip-overlay']:
            return 'hidden'
        
        return no_update

    @app.callback(
        Output('subpart-tooltip', 'className'),
        Output('tooltip-overlay', 'className'),
        Input('tooltip-state-store', 'data')
    )
    def update_tooltip_visibility(state):
        if state == 'visible':
            return 'tooltip-content visible', 'tooltip-overlay visible'
        return 'tooltip-content', 'tooltip-overlay'
    """
    Creates a Plotly donut chart showing emissions breakdown by subpart.
    
    Args:
        app: The Dash application instance for registering callbacks
    
    Returns:
        A Dash component containing the donut chart with loading state
    """
    # Store for tracking last update timestamp
    last_update_store = dcc.Store(id='subpart-last-update-timestamp', data=0)
    
    @app.callback(
        Output('subpart-breakdown-graph', 'figure'),
        [
            Input('year-range-slider', 'value'),
            Input('state-dropdown', 'value')
        ],
        [
            State('subpart-last-update-timestamp', 'data')
        ]
    )
    def update_subpart_graph(year_range, selected_states, last_update):
        # Get current timestamp
        current_time = time.time()
        
        # Allow initial load or if sufficient time has passed (1 second debounce)
        if last_update and current_time - last_update < 1.0:
            raise PreventUpdate
            
        try:
            # Get data using the cached function
            cache_result = get_cached_data(
                state_filter=tuple(selected_states) if selected_states else None,
                year_range=tuple(year_range) if year_range else None,
                category_filter=tuple([selected_category]) if selected_category else None
            )
            data = cache_result['main_chart_data']
            
            if not data or len(data) == 0:
                return go.Figure().add_annotation(
                    text='No data available for breakdown chart',
                    xref='paper',
                    yref='paper',
                    x=0.5,
                    y=0.5,
                    showarrow=False
                )

            # Convert to DataFrame for easier manipulation
            df = pd.DataFrame(data)
            
            # Apply filters if provided
            if selected_states and len(selected_states) > 0:
                df = df[df['state'].isin(selected_states)]
            
            if year_range:
                df = df[(df['year'].astype(int) >= year_range[0]) & 
                        (df['year'].astype(int) <= year_range[1])]

            # Check for subpart column
            if 'subparts' not in df.columns:
                return go.Figure().add_annotation(
                    text='No subpart data available',
                    xref='paper',
                    yref='paper',
                    x=0.5,
                    y=0.5,
                    showarrow=False
                )
            
            # Apply category filter if provided
            if selected_category:
                df = df[df['subparts'] == selected_category]
                if len(df) == 0:
                    return go.Figure().add_annotation(
                        text=f'No data available for category: {selected_category}',
                        xref='paper',
                        yref='paper',
                        x=0.5,
                        y=0.5,
                        showarrow=False
                    )
            
            if 'value' not in df.columns:
                return go.Figure().add_annotation(
                    text='No emissions data available',
                    xref='paper',
                    yref='paper',
                    x=0.5,
                    y=0.5,
                    showarrow=False
                )
            
            # Group by subpart
            if selected_category:
                # Group by state when category is selected
                group_data = df.groupby('state').agg({
                    'value': 'sum'
                }).reset_index()
                
                group_data.columns = ['entity', 'emissions']
                title = f'Emissions for Subpart {selected_category} by State'
                label_prefix = ''
            else:
                # Group by subpart
                group_data = df.groupby('subparts').agg({
                    'value': 'sum',
                    'state': 'nunique'
                }).reset_index()
                
                group_data.columns = ['entity', 'emissions', 'stateCount']
                title = 'Emissions by Subpart'
                label_prefix = 'Subpart '
            
            group_data['emissions'] = group_data['emissions'].round(0)
            
            # Calculate percentages with accurate adjustment to ensure they sum to 100%
            total_emissions = group_data['emissions'].sum()
            raw_percentages = (group_data['emissions'] / total_emissions * 100)
            
            # Apply accurate percentage calculation (same logic as enhanced version)
            rounded_percentages = raw_percentages.round(1)
            total_rounded = rounded_percentages.sum()
            difference = 100.0 - total_rounded
            
            # Adjust percentages if they don't sum to exactly 100%
            if abs(difference) > 0.001:  # Only adjust if meaningful difference
                # Calculate remainders for largest remainder method
                remainders = raw_percentages - rounded_percentages.round(0)
                
                # Determine how many 0.1% adjustments we need
                adjustments_needed = int(abs(difference) * 10)
                
                if difference > 0:  # Need to add percentage
                    # Add 0.1% to the items with largest remainders
                    indices_to_adjust = remainders.nlargest(adjustments_needed).index
                    for idx in indices_to_adjust:
                        rounded_percentages.loc[idx] += 0.1
                else:  # Need to subtract percentage
                    # Subtract 0.1% from the items with smallest remainders
                    indices_to_adjust = remainders.nsmallest(adjustments_needed).index
                    for idx in indices_to_adjust:
                        rounded_percentages.loc[idx] -= 0.1
            
            group_data['percentage'] = rounded_percentages.round(1)
            
            # Sort by emissions
            group_data = group_data.sort_values('emissions', ascending=False)

            # Create donut chart with hover-only labels for cleaner visualization
            if selected_category:
                labels = [row.entity for _, row in group_data.iterrows()]
                values = group_data['percentage'].tolist()  # Use calculated percentages for accurate visual representation
                emissions_data = group_data['emissions'].tolist()  # Keep emissions for hover display
                
                fig = go.Figure(data=[go.Pie(
                    labels=labels,  # Keep original labels for hover text
                    text=[''] * len(labels),  # Remove text labels for cleaner look
                    textposition='none',  # Disable text display
                    values=values,  # Use percentages for accurate pie slice sizes
                    hole=0.5,
                    hovertemplate=('<b>%{label}</b><br>' +
                                  'Emissions: %{customdata:,.0f} MT CO2e<br>' +
                                  'Percentage: %{value:.1f}%<br>' +
                                  '<extra></extra>'),
                    customdata=emissions_data  # Pass emissions data for hover display
                )])
            else:
                labels = [f'{label_prefix}{row.entity}' for _, row in group_data.iterrows()]
                values = group_data['percentage'].tolist()  # Use calculated percentages for accurate visual representation
                emissions_data = group_data['emissions'].tolist()  # Keep emissions for hover display
                state_counts = group_data['stateCount'].tolist()  # Keep state counts for hover display
                
                fig = go.Figure(data=[go.Pie(
                    labels=labels,  # Keep original labels for hover text
                    text=[''] * len(labels),  # Remove text labels for cleaner look
                    textposition='none',  # Disable text display
                    values=values,  # Use percentages for accurate pie slice sizes
                    hole=0.5,
                    hovertemplate=('<b>%{label}</b><br>' +
                                  'Emissions: %{customdata[0]:,.0f} MT CO2e<br>' +
                                  'Percentage: %{value:.1f}%<br>' +
                                  'States: %{customdata[1]}<br>' +
                                  '<extra></extra>'),
                    customdata=list(zip(emissions_data, state_counts))  # Pass both emissions and state counts
                )])

            # Get cached layout configuration
            layout = get_cached_layout('subpart')
            
            # Update layout with chart-specific settings
            layout.update({
                'title': {
                    **layout.get('title', {}),
                    'text': title
                },
                'showlegend': False,  # Hide legend for cleaner look
                'plot_bgcolor': 'white',
                'paper_bgcolor': 'white'
            })
            
            fig.update_layout(layout)
            return fig
            
        except Exception as e:
            print(f"Error creating figure: {str(e)}")
            return go.Figure().add_annotation(
                text='Error creating chart. Please try again.',
                xref='paper',
                yref='paper',
                x=0.5,
                y=0.5,
                showarrow=False
            )
    
    def create_tooltip_content():
        # Format subpart definitions for tooltip with a header and organized content
        return html.Div([
            html.Div([
                html.H3("EPA GHGRP Subpart Definitions", style={
                    "margin": "0 0 10px 0",
                    "color": "#2c3e50",
                    "fontSize": "24px"
                }),
                html.I(
                    className="fas fa-times",
                    id="close-tooltip",
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
            html.Div([
                html.Div([
                    html.Strong(
                        f"Subpart {code}",
                        style={
                            "color": "#2980b9",
                            "fontSize": "16px",
                            "display": "block",
                            "marginBottom": "5px"
                        }
                    ),
                    html.P(
                        desc,
                        style={
                            "margin": "0",
                            "color": "#333",
                            "lineHeight": "1.6"
                        }
                    )
                ], style={
                    "padding": "15px",
                    "marginBottom": "15px",
                    "borderRadius": "8px",
                    "backgroundColor": "#f8f9fa",
                    "border": "1px solid #e9ecef"
                })
                for code, desc in sorted(subpart_mappings.items())
            ], style={
                "maxHeight": "calc(80vh - 100px)",
                "overflowY": "auto",
                "paddingRight": "15px"
            })
        ])
    
    # Context
    # This file defines the subpart breakdown graph and related UI components for the GHG emissions dashboard.
    # It includes the donut chart, tooltip logic, and a concise, collapsible table mapping subpart codes to their definitions.
    # The subpart mapping table is now wrapped in a dropdown (html.Details) for minimal UI clutter.
    # All code is minimal and focused on this specific UI feature.
    # Create the tooltip content
    tooltip_content = create_tooltip_content()
    
    # --- Concise subpart mapping table (collapsible) ---
    # This table provides a quick reference for subpart codes and their definitions, hidden by default.
    mapping_table = html.Details([
        html.Summary("Show subpart code definitions"),
        html.Table([
            html.Thead([
                html.Tr([
                    html.Th("Subpart Code"),
                    html.Th("Definition")
                ])
            ]),
            html.Tbody([
                html.Tr([
                    html.Td(code),
                    html.Td(desc)
                ]) for code, desc in subpart_mappings.items()
            ])
        ], style={"marginTop": "10px", "width": "100%", "maxWidth": "600px", "fontSize": "14px", "borderCollapse": "collapse"})
    ], style={"marginTop": "30px"})
    
    # Return the component structure
    return html.Div([
        # Info icon positioned absolutely in top-right corner
        html.I(
            className="fas fa-info-circle info-icon",
            id="subpart-info-icon",
            n_clicks=0,
            style={"position": "absolute", "top": "10px", "right": "10px", "zIndex": "2"}
        ),
        # Overlay for closing tooltip
        html.Div(
            id="tooltip-overlay",
            className="tooltip-overlay",
            n_clicks=0
        ),
        # Tooltip content
        html.Div(
            tooltip_content,
            id="subpart-tooltip",
            className="tooltip-content"
        ),
        # Graph component
        dcc.Loading(
            id="loading-subpart-graph",
            type="default",
            children=[
                dcc.Graph(
                    id='subpart-breakdown-graph',
                    config={'displayModeBar': True, 'scrollZoom': False}
                )
            ]
        ),
        # --- Collapsible subpart mapping table below the graph ---
        mapping_table,
        last_update_store
    ], style={"position": "relative"})
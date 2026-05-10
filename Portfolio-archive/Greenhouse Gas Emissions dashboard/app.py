# Context:
# This is the main application file that creates a Dash web application for visualizing greenhouse gas emissions data.
# It provides an interactive dashboard with filters for year range and states, and displays two main
# visualizations side by side: a time series graph showing state emissions trends and a donut chart showing
# emissions breakdown by subpart.
# 
# INVERSE DASHBOARD ADDITION:
# Added inverse analysis functionality below the existing dashboard that allows users to:
# 1. View subpart emissions over time (left graph)
# 2. See state breakdown for selected subparts (right graph)
# This provides a complementary "subpart-centric" view alongside the existing "state-centric" view.
#
# FILTER SIMPLIFICATION:
# Removed the category filter as it was not being used by any of the visualization components.
#
# LAYOUT ORGANIZATION:
# Filters are positioned above section headers to provide global controls that affect all visualizations below.
# Year range and state selection are grouped together as they both filter the main state-centric dashboard.

import dash
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output
import pandas as pd
from components.state_graph import create_state_emissions_graph
from components.subpart_graph import create_subpart_breakdown
from components.subpart_graph_v2 import create_enhanced_subpart_breakdown
from components.subpart_selector import create_subpart_selector
from components.subpart_timeline_graph import create_subpart_timeline_graph
from components.state_breakdown_graph import create_state_breakdown_graph
# Removed company_table import as it doesn't exist in current codebase
from utils.cache_utils import get_cached_data, clear_data_cache
from utils.feature_flags import feature_flags
# Performance optimization imports
from utils.data_manager import get_global_data, get_global_data_manager
from utils.performance_monitor import performance_monitor, monitor_performance
from utils.smart_cache import get_smart_cache
from utils.callback_debouncer import get_callback_debouncer
from utils.data_aggregator import get_data_aggregator

# Initialize the Dash app
app = dash.Dash(__name__)

# Initialize server for Gunicorn
server = app.server

# Performance optimization: Initialize global data at startup
# This loads the parquet file once instead of multiple times per component
if feature_flags.is_enabled('use_global_data_manager'):
    print("[INFO] Initializing global data manager for performance optimization...")
    performance_monitor.start_timer("app_startup_data_load", "app")
    
    try:
        data_manager = get_global_data_manager()
        success = data_manager.load_global_data()
        load_time = performance_monitor.end_timer("app_startup_data_load", "app")
        if success:
            print(f"[INFO] Global data loaded successfully in {load_time:.2f} seconds")
        else:
            print(f"[WARNING] Global data loading failed, fallback will be used")
        
        # Record memory usage after data loading
        memory_info = performance_monitor.record_memory_usage("app", "startup_complete")
        if memory_info:
            print(f"[INFO] Memory usage after startup: {memory_info.get('process_memory_mb', 0):.1f} MB")
            
    except Exception as e:
        print(f"[ERROR] Failed to initialize global data: {e}")
        print("[INFO] Falling back to individual component data loading")
else:
    print("[INFO] Global data manager disabled, using individual component data loading")

# Phase 2 Performance optimization: Initialize smart cache and debouncer
if feature_flags.is_enabled('use_smart_cache'):
    print("[INFO] Initializing smart cache for Phase 2 performance optimization...")
    try:
        smart_cache = get_smart_cache()
        cache_stats = smart_cache.get_stats()
        print(f"[INFO] Smart cache initialized: max_size={cache_stats['max_size']}, max_memory={cache_stats['max_memory_mb']}MB")
    except Exception as e:
        print(f"[ERROR] Failed to initialize smart cache: {e}")
else:
    print("[INFO] Smart cache disabled, using LRU cache only")

if feature_flags.is_enabled('use_callback_debouncing'):
    print("[INFO] Initializing callback debouncer for Phase 2 performance optimization...")
    try:
        debouncer = get_callback_debouncer()
        debouncer_stats = debouncer.get_stats()
        print(f"[INFO] Callback debouncer initialized: default_delay={debouncer_stats['default_delay_ms']}ms")
    except Exception as e:
        print(f"[ERROR] Failed to initialize callback debouncer: {e}")
else:
    print("[INFO] Callback debouncing disabled, using immediate execution")

# Phase 3 Performance optimization: Initialize data aggregator
if feature_flags.is_enabled('use_pre_aggregation'):
    print("[INFO] Initializing data aggregator for Phase 3 performance optimization...")
    try:
        data_aggregator = get_data_aggregator()
        # Pre-compute aggregations if global data is available
        if feature_flags.is_enabled('use_global_data_manager'):
            global_data = get_global_data()
            if global_data is not None:
                performance_monitor.start_timer("aggregation_precompute", "app")
                success = data_aggregator.precompute_aggregations(global_data)
                precompute_time = performance_monitor.end_timer("aggregation_precompute", "app")
                if success:
                    aggregation_status = data_aggregator.get_aggregation_status()
                    available_aggregations = len([k for k, v in aggregation_status.items() if v])
                    print(f"[INFO] Data aggregator initialized with {available_aggregations} aggregations in {precompute_time:.2f} seconds")
                else:
                    print("[WARNING] Data aggregator initialization failed, fallback will be used")
            else:
                print("[WARNING] Global data not available for pre-aggregation")
        else:
            print("[INFO] Data aggregator initialized (pre-aggregation will be done on-demand)")
    except Exception as e:
        print(f"[ERROR] Failed to initialize data aggregator: {e}")
else:
    print("[INFO] Data aggregator disabled, using direct data processing")

# Define the app layout
app.layout = html.Div([
    # Header
    html.H1('Greenhouse Gas (GHG) Emissions Dashboard', className='dashboard-header'),
    # Tooltip state store for subpart tooltip (must be top-level for Dash callbacks)
    dcc.Store(id='tooltip-state-store', data='hidden'),
    
    # Global year range filter - positioned above all sections to control all visualizations
    html.Div([
        html.H3('Filters', className='filters-header'),
        
        # Year range filter - affects both state-centric and subpart-centric views
        html.Label('Reporting Year Range'),
        dcc.RangeSlider(
            id='year-range-slider',
            min=2010,  # Starting year based on data
            max=2023,  # Latest year based on data
            step=1,
            value=[2010, 2023],  # Default to full range
            marks={str(year): str(year) for year in range(2010, 2024, 2)}  # Show every other year for better readability
        ),
    ], className='filters-container'),
    
    # First section - Combined into single white container
    html.Div([
        # Section header and filter
        html.H2('GHG Emissions: by U.S. State', 
                   className='section-header',
                   style={'marginTop': '0px', 'marginBottom': '15px', 'color': '#2c3e50'}),
        
        html.Label('Select States'),
        dcc.Dropdown(
            id='state-dropdown',
            options=[],  # Will be populated from data
            multi=True,
            placeholder='Select states...',
            value=[]  # Initialize with an empty list to prevent None
        ),
        
        # Add some spacing between filter and charts
        html.Div(style={'marginBottom': '20px'}),
        
        # Main content area with charts
        html.Div([
            # Left column: State emissions chart
            html.Div([
                create_state_emissions_graph(app)
            ], className='chart-container'),
            
            # Right column: Subpart breakdown chart
            html.Div([
                (lambda: (
                    print(f"[DEBUG] Using enhanced subpart: {feature_flags.is_enabled('enhanced_subpart_breakdown')}"),
                    create_enhanced_subpart_breakdown(app) if feature_flags.is_enabled('enhanced_subpart_breakdown') else create_subpart_breakdown(app)
                )[1])()
            ], className='chart-container')
        ], className='charts-container')
    ], className='main-container'),
    
    # Inverse Dashboard Section - Combined into single white container
    html.Div([
        # Section header and filter
        html.H2('GHG Emissions: by Subpart', 
               className='section-header',
               style={'marginTop': '0px', 'marginBottom': '15px', 'color': '#2c3e50'}),
        
        # Subpart selector
        html.Label('Select Subparts for Analysis', 
                  style={'fontWeight': 'bold', 'marginBottom': '10px'}),
        create_subpart_selector(),
        
        # Add some spacing between filter and charts
        html.Div(style={'marginBottom': '20px'}),
        
        # Inverse charts container
        html.Div([
            # Left: Subpart timeline graph
            html.Div([
                create_subpart_timeline_graph(app)
            ], className='chart-container'),
            
            # Right: State breakdown graph
            html.Div([
                create_state_breakdown_graph(app)
            ], className='chart-container')
        ], className='charts-container')
    ], className='main-container'),
    
    # Subpart Classification Reference Section
    html.Div([
        html.Details([
            html.Summary([
                html.H2('Subpart Classification Reference', 
                       className='section-header',
                       style={'marginTop': '0px', 'marginBottom': '15px', 'color': '#2c3e50', 'display': 'inline-block'}),
                html.Span(' (Click to expand)', 
                         style={'fontSize': '14px', 'color': '#7f8c8d', 'fontWeight': 'normal', 'marginLeft': '10px'})
            ], style={'cursor': 'pointer', 'outline': 'none'}),
            
            html.Div([
                html.P('This table shows the mapping between subpart classifications and their definitions as used in the GHG emissions data.',
                      style={'marginBottom': '20px', 'color': '#34495e', 'fontSize': '14px'}),
                
                html.Table([
                    html.Thead([
                        html.Tr([
                            html.Th('Classification', style={'padding': '12px', 'backgroundColor': '#f8f9fa', 'borderBottom': '2px solid #dee2e6', 'fontWeight': 'bold', 'color': '#2c3e50'}),
                            html.Th('Definition', style={'padding': '12px', 'backgroundColor': '#f8f9fa', 'borderBottom': '2px solid #dee2e6', 'fontWeight': 'bold', 'color': '#2c3e50'})
                        ])
                    ]),
                    html.Tbody([
                        html.Tr([
                            html.Td('Subpart A', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('General Provisions', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart B', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('(Reserved)', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontStyle': 'italic', 'color': '#6c757d'})
                        ]),
                        html.Tr([
                            html.Td('Subpart C', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('General Stationary Fuel Combustion Sources', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart D', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Electricity Generation', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart E', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Adipic Acid Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart F', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Aluminum Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart G', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Ammonia Manufacturing', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart H', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Cement Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart I', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Electronics Manufacturing', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart J', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Ethanol Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart K', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Ferroalloy Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart L', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Fluorinated Gas Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart M', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Food Processing', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart N', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Glass Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart O', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('HCFC–22 Production and HFC–23 Destruction', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart P', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Hydrogen Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart Q', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Iron and Steel Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart R', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Lead Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart S', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Lime Manufacturing', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart T', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Magnesium Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart U', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Miscellaneous Uses of Carbonate', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart V', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Nitric Acid Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart W', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Petroleum and Natural Gas Systems', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart X', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Petrochemical Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart Y', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Petroleum Refineries', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart Z', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Phosphoric Acid Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart AA', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Pulp and Paper Manufacturing', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart BB', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Silicon Carbide Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart CC', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Soda Ash Manufacturing', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart DD', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Use of Electric Transmission and Distribution Equipment', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart EE', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Titanium Dioxide Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart FF', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Underground Coal Mines', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart GG', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Zinc Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart HH', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Municipal Solid Waste Landfills', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart II', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Industrial Wastewater Treatment', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart JJ', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Manure Management', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart KK', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Suppliers of Coal', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart LL', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Suppliers of Coal-based Liquid Fuels', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart MM', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Suppliers of Petroleum Products', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart NN', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Suppliers of Natural Gas and Natural Gas Liquids', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart OO', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Suppliers of Industrial Greenhouse Gases', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart PP', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Suppliers of Carbon Dioxide', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart QQ', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Imports and Exports of Equipment Pre–charged with Fluorinated GHGs or Containing Fluorinated GHGs in Closed–cell Foams', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart RR', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Geologic Sequestration of Carbon Dioxide', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart SS', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Manufacture of Electric Transmission and Distribution Equipment', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart TT', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Industrial Waste Landfills', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart UU', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Injection of Carbon Dioxide', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart VV', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Geologic Sequestration of Carbon Dioxide with Enhanced Oil Recovery Using ISO 27916', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart WW', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Coke Calciners', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart XX', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Calcium Carbide Producers', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart YY', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Caprolactam, Glyoxal, and Glyoxylic Acid Production', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ]),
                        html.Tr([
                            html.Td('Subpart ZZ', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6', 'fontFamily': 'monospace', 'fontWeight': 'bold'}),
                            html.Td('Ceramics Manufacturing', style={'padding': '8px 12px', 'borderBottom': '1px solid #dee2e6'})
                        ])
                    ])
                ], style={
                    'width': '100%',
                    'borderCollapse': 'collapse',
                    'backgroundColor': 'white',
                    'boxShadow': '0 1px 3px rgba(0,0,0,0.1)',
                    'borderRadius': '4px',
                    'overflow': 'hidden'
                })
            ], style={'marginTop': '15px'})
        ], open=False)  # Collapsed by default
    ], className='main-container', style={'marginTop': '30px'})
], className='dashboard-container')



# Clear cache on app startup
clear_data_cache()

# Callback to populate dropdowns
# Add at the top of the file, after imports
import os

# Define base paths - Update for Docker compatibility
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
PARQUET_FILE = os.path.join(DATA_DIR, 'emissions_data.parquet')

# Update the parquet file path in update_dropdown_options
@app.callback(
    Output('state-dropdown', 'options'),
    Input('year-range-slider', 'value')
)
@monitor_performance("dropdown_options_update", "app")
def update_dropdown_options(year_range):
    """Update state dropdown options based on available data.
    
    Args:
        year_range: Selected year range from the slider
        
    Returns:
        List of state options for the dropdown
    """
    print(f"[DEBUG] update_dropdown_options - year_range: {year_range}")

    try:
        # Performance optimization: Use global data manager when available
        if feature_flags.is_enabled('use_global_data_manager'):
            raw_data = get_global_data()
            if raw_data is None:
                print("[WARNING] Global data not available, falling back to direct file read")
                raw_data = pd.read_parquet(PARQUET_FILE)
        else:
            # Fallback to direct file reading
            raw_data = pd.read_parquet(PARQUET_FILE)
        
        # Clean the data by dropping NA values first
        raw_data = raw_data.dropna(subset=['STATE'])
        
        # Get unique states from cleaned data
        states = sorted(raw_data['STATE'].unique().tolist())
        
        # Create dropdown options
        state_options = [{'label': state, 'value': state} for state in states if pd.notna(state)]
        
        print(f"[DEBUG] update_dropdown_options - States found: {len(state_options)}")
        
        return state_options
    except Exception as e:
        print(f"[ERROR] update_dropdown_options - Error updating dropdown options: {str(e)}")
        return []

# Add logging to the update_graph callback in create_state_emissions_graph
# This part is within components/state_graph.py, but I'm showing how it would look conceptually.
# You would need to apply this change in components/state_graph.py directly.

# In components/state_graph.py, inside the update_graph callback:
# @app.callback(
#     Output('state-emissions-graph', 'figure'),
#     [
#         Input('year-range-slider', 'value'),
#         Input('state-dropdown', 'value'),
#         Input('category-dropdown', 'value')
#     ]
# )
# def update_graph(year_range, selected_states, category):
#     print(f"[DEBUG] update_state_graph - Year Range: {year_range}, States: {selected_states}, Category: {category}")
#     # ... existing code ...

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
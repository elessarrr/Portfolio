# Context:
# Context: This module implements caching strategies for the emissions dashboard to improve performance.
# It provides LRU (Least Recently Used) caching for data queries to reduce database/file access
# and computation overhead. The cache is optimized for common query patterns and sized based
# on typical data access patterns in the application.
# Recent addition: Standardized chart title margins for consistent heading alignment across graphs.
# 
# The module now uses Parquet format for data storage, which provides:
# - Faster data loading (10-100x faster than Excel)
# - Column-based storage for efficient querying
# - Better compression for reduced memory usage
# - Native support for categorical data types

from functools import lru_cache
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from .data_preprocessor import DataPreprocessor
from .feature_flags import feature_flags
from .performance_monitor import monitor_performance
from .smart_cache import get_smart_cache, smart_cache_decorator

def _generate_cache_key(*args, **kwargs) -> str:
    """Generate cache key for data retrieval."""
    state_filter = kwargs.get('state_filter') or args[0] if args else None
    year_range = kwargs.get('year_range') or args[1] if len(args) > 1 else None
    company_filter = kwargs.get('company_filter') or args[2] if len(args) > 2 else None
    category_filter = kwargs.get('category_filter') or args[3] if len(args) > 3 else None
    
    return f"data:{state_filter}:{year_range}:{company_filter}:{category_filter}"

# Dual caching strategy: Smart cache (Phase 2) with LRU fallback (Phase 1)
# Smart cache provides TTL and memory management, LRU provides simple fallback
@lru_cache(maxsize=512)
@smart_cache_decorator(key_func=_generate_cache_key, ttl_seconds=1800)  # 30 minutes TTL
@monitor_performance("cached_data_retrieval", "cache_utils")
def get_cached_data(
    state_filter: Optional[Tuple[str, ...]] = None,
    year_range: Optional[Tuple[int, int]] = None,
    company_filter: Optional[Tuple[str, ...]] = None,
    category_filter: Optional[Tuple[str, ...]] = None
) -> Dict[str, Any]:
    """Cached version of data filtering and aggregation.
    
    Args:
        state_filter: Tuple of selected state codes (immutable for caching)
        year_range: Tuple of (start_year, end_year)
        company_filter: Tuple of selected company names
        category_filter: Tuple of selected subpart categories (immutable for caching)
    
    Returns:
        Dictionary containing cached aggregated data
    """
    from .aggregation import filter_and_aggregate_data
    from .aggregation_v2 import get_subpart_breakdown_data
    
    # Convert tuple filters back to lists for the underlying function
    states = list(state_filter) if state_filter else None
    companies = list(company_filter) if company_filter else None
    years = list(year_range) if year_range else None
    
    # Load data from Parquet using the preprocessor or global data manager
    try:
        # Performance optimization: Use global data manager when available
        if feature_flags.is_enabled('use_global_data_manager'):
            from .data_manager import get_global_data
            raw_data = get_global_data()
            if raw_data is None:
                print("[WARNING] Global data not available in cache_utils, falling back to DataPreprocessor")
                preprocessor = DataPreprocessor()
                raw_data = preprocessor.load_data()
        else:
            # Fallback to DataPreprocessor
            preprocessor = DataPreprocessor()
            raw_data = preprocessor.load_data()
        
        # Set year range if not provided
        if not years and 'REPORTING YEAR' in raw_data.columns:
            years = [int(raw_data['REPORTING YEAR'].min()), int(raw_data['REPORTING YEAR'].max())]
        
        # Convert category filter to list
        categories = list(category_filter) if category_filter else None
        
        # Use original aggregation for state graph compatibility
        result = filter_and_aggregate_data(
            raw_data=raw_data,
            selected_states=states,
            year_range=years,
            selected_companies=companies,
            selected_subparts=categories
        )
        
        return result
        
    except Exception as e:
        print(f"[ERROR] get_cached_data - Error loading or processing data: {str(e)}")
        return {'main_chart_data': []}

@lru_cache(maxsize=2)
@smart_cache_decorator(ttl_seconds=3600)  # 1 hour TTL for layouts
def get_cached_layout(chart_type: str) -> Dict[str, Any]:
    """Get cached layout configuration for charts.
    
    Args:
        chart_type: Type of chart ('state' or 'subpart')
    
    Returns:
        Dictionary containing Plotly layout configuration
    """
    if chart_type == 'state':
        return {
            'title': {
                'text': 'State GHG Emissions Over Time',
                'font': {'size': 18},
                'x': 0.03,
                'xanchor': 'left',
                'y': 0.95,  # Standardized y position for consistent alignment
                'yanchor': 'top'
            },
            'height': 500,
            'margin': {'l': 50, 'r': 20, 't': 80, 'b': 50},  # Consistent margins for title alignment
            'legend': {
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': -0.2,
                'xanchor': 'center',
                'x': 0.5,
                'font': {'size': 10},
                'itemwidth': 30
            },
            'xaxis': {'title': 'Year'},
            'yaxis': {'title': 'Emissions (MT CO2e)'}
        }
    elif chart_type == 'subpart':
        return {
            'height': 500,
            'margin': {'l': 20, 'r': 20, 't': 80, 'b': 50},  # Increased top margin to accommodate title
            'title': {
                'font': {'size': 18},
                'x': 0.03,
                'xanchor': 'left',
                'y': 0.95,  # Standardized y position for consistent alignment
                'yanchor': 'top'
            },
            'legend': {
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': -0.2,
                'xanchor': 'center',
                'x': 0.5,
                'font': {'size': 10},
                'itemwidth': 30
            },
            'showlegend': True
        }
    return {}

def clear_data_cache():
    """Clear all cached data when needed (e.g., after data updates)"""
    # Clear LRU caches
    get_cached_data.cache_clear()
    get_cached_layout.cache_clear()
    
    # Clear smart cache if enabled
    if feature_flags.is_enabled('use_smart_cache'):
        smart_cache = get_smart_cache()
        smart_cache.clear()

def get_cache_stats() -> Dict[str, Any]:
    """Get comprehensive cache statistics.
    
    Returns:
        Dictionary containing cache performance metrics
    """
    stats = {
        'lru_cache': {
            'get_cached_data': get_cached_data.cache_info()._asdict(),
            'get_cached_layout': get_cached_layout.cache_info()._asdict()
        }
    }
    
    # Add smart cache stats if enabled
    if feature_flags.is_enabled('use_smart_cache'):
        smart_cache = get_smart_cache()
        stats['smart_cache'] = smart_cache.get_stats()
    
    return stats
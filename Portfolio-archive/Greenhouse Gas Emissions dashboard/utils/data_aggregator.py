#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Aggregator Module - Phase 3 Performance Optimization

This module implements pre-aggregation of common data combinations to improve
dashboard performance. It pre-computes frequently accessed aggregations at
startup and provides cached access to these pre-processed datasets.

Key Features:
- State-year aggregations
- Subpart summaries
- Company rankings
- Trend calculations
- Cache warming for aggregations
- Thread-safe access to pre-aggregated data

This is part of Phase 3 performance optimization as outlined in
app_performance_optimisation_Jun22.md
"""

import pandas as pd
import numpy as np
import threading
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from utils.feature_flags import FeatureFlags
# from utils.performance_monitor import monitor_performance  # Removed to avoid psutil dependency

# Configure logging for this module
logger = logging.getLogger(__name__)

class DataAggregator:
    """
    Pre-compute and cache common data aggregations for improved performance.
    
    This class implements pre-aggregation of frequently accessed data combinations
    to reduce computation time during user interactions. It follows the singleton
    pattern to ensure aggregations are computed only once.
    """
    
    _instance = None
    _lock = threading.Lock()
    _data_lock = threading.Lock()
    
    def __new__(cls):
        """Implement singleton pattern with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DataAggregator, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the DataAggregator (only once due to singleton pattern)."""
        if self._initialized:
            return
            
        self.feature_flags = FeatureFlags()
        self._aggregations = {}
        self._aggregation_status = {}
        self._initialized = True
        
        logger.info("DataAggregator initialized")
    
    def precompute_aggregations(self, df: pd.DataFrame) -> bool:
        """
        Pre-compute all common aggregations from the source data.
        
        Args:
            df: Source emissions DataFrame
            
        Returns:
            bool: True if aggregations were successfully computed
        """
        if not self.feature_flags.is_enabled('use_pre_aggregation'):
            logger.info("Pre-aggregation disabled by feature flag")
            return False
            
        try:
            with self._data_lock:
                logger.info("Starting pre-aggregation computation...")
                
                # 1. State-year aggregations
                self._compute_state_year_aggregations(df)
                
                # 2. Subpart summaries
                self._compute_subpart_summaries(df)
                
                # 3. Company rankings
                self._compute_company_rankings(df)
                
                # 4. Trend calculations
                self._compute_trend_calculations(df)
                
                # 5. Additional common aggregations
                self._compute_additional_aggregations(df)
                
                logger.info("Pre-aggregation computation completed successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to compute pre-aggregations: {str(e)}")
            return False
    
    def _compute_state_year_aggregations(self, df: pd.DataFrame) -> None:
        """
        Pre-compute state-year aggregations for faster state timeline access.
        """
        try:
            # State totals by year
            state_year_totals = df.groupby(['STATE', 'REPORTING YEAR'], as_index=False)[
                'GHG QUANTITY (METRIC TONS CO2e)'
            ].sum()
            
            # Vectorized state rankings by year
            state_year_sorted = state_year_totals.sort_values(
                ['REPORTING YEAR', 'GHG QUANTITY (METRIC TONS CO2e)'], 
                ascending=[True, False]
            )
            state_rankings_df = state_year_sorted.copy()
            state_rankings_df['rank'] = state_rankings_df.groupby('REPORTING YEAR').cumcount() + 1
            
            # Store aggregations
            self._aggregations['state_year_totals'] = state_year_totals
            self._aggregations['state_rankings_by_year'] = state_rankings_df
            self._aggregation_status['state_year'] = True
            
            logger.debug(f"State-year aggregations computed for {state_year_totals['STATE'].nunique()} states across {state_year_totals['REPORTING YEAR'].nunique()} years")
            
        except Exception as e:
            logger.error(f"Failed to compute state-year aggregations: {str(e)}")
            self._aggregation_status['state_year'] = False
    
    def _compute_subpart_summaries(self, df: pd.DataFrame) -> None:
        """
        Pre-compute subpart summaries for faster subpart analysis.
        """
        try:
            # Vectorized subpart processing
            df_clean = df[df['SUBPARTS'].notna() & (df['SUBPARTS'] != '')].copy()
            
            if len(df_clean) == 0:
                logger.warning("No valid subpart data found for aggregation")
                self._aggregation_status['subpart_summaries'] = False
                return
            
            # Split subparts and explode into separate rows (vectorized)
            df_clean['SUBPARTS'] = df_clean['SUBPARTS'].astype(str)
            df_clean['SUBPART_LIST'] = df_clean['SUBPARTS'].str.split(',')
            subpart_df = df_clean.explode('SUBPART_LIST')
            subpart_df['SUBPART'] = subpart_df['SUBPART_LIST'].str.strip()
            subpart_df = subpart_df[subpart_df['SUBPART'] != 'nan']
            
            if len(subpart_df) == 0:
                logger.warning("No valid subpart data after processing")
                self._aggregation_status['subpart_summaries'] = False
                return
            
            # Vectorized aggregations
            subpart_year_totals = subpart_df.groupby(['SUBPART', 'REPORTING YEAR'], as_index=False)[
                'GHG QUANTITY (METRIC TONS CO2e)'
            ].sum()
            
            subpart_totals = subpart_df.groupby('SUBPART', as_index=False)[
                'GHG QUANTITY (METRIC TONS CO2e)'
            ].sum().sort_values('GHG QUANTITY (METRIC TONS CO2e)', ascending=False)
            
            # Store aggregations
            self._aggregations['subpart_year_totals'] = subpart_year_totals
            self._aggregations['subpart_totals'] = subpart_totals
            self._aggregation_status['subpart_summaries'] = True
            
            logger.debug(f"Subpart summaries computed for {len(subpart_totals)} subparts")
                
        except Exception as e:
            logger.error(f"Failed to compute subpart summaries: {str(e)}")
            self._aggregation_status['subpart_summaries'] = False
    
    def _compute_company_rankings(self, df: pd.DataFrame) -> None:
        """
        Pre-compute company rankings for faster company analysis.
        """
        try:
            # Company totals by year
            company_year_totals = df.groupby(['PARENT COMPANIES', 'REPORTING YEAR'], as_index=False)[
                'GHG QUANTITY (METRIC TONS CO2e)'
            ].sum()
            
            # Overall company rankings
            company_totals = df.groupby('PARENT COMPANIES', as_index=False)[
                'GHG QUANTITY (METRIC TONS CO2e)'
            ].sum().sort_values('GHG QUANTITY (METRIC TONS CO2e)', ascending=False)
            company_totals['rank'] = range(1, len(company_totals) + 1)
            
            # Vectorized top companies by year calculation
            company_year_sorted = company_year_totals.sort_values(
                ['REPORTING YEAR', 'GHG QUANTITY (METRIC TONS CO2e)'], 
                ascending=[True, False]
            )
            
            # Use groupby with head to get top 20 per year efficiently
            top_companies_df = company_year_sorted.groupby('REPORTING YEAR').head(20).copy()
            top_companies_df['rank'] = top_companies_df.groupby('REPORTING YEAR').cumcount() + 1
            
            # Store aggregations
            self._aggregations['company_year_totals'] = company_year_totals
            self._aggregations['company_rankings'] = company_totals
            self._aggregations['top_companies_by_year'] = top_companies_df
            self._aggregation_status['company_rankings'] = True
            
            logger.debug(f"Company rankings computed for {len(company_totals)} companies across {company_year_totals['REPORTING YEAR'].nunique()} years")
            
        except Exception as e:
            logger.error(f"Failed to compute company rankings: {str(e)}")
            self._aggregation_status['company_rankings'] = False
    
    def _compute_trend_calculations(self, df: pd.DataFrame) -> None:
        """
        Pre-compute trend calculations for faster trend analysis.
        """
        try:
            # Overall yearly trends
            yearly_totals = df.groupby('REPORTING YEAR', as_index=False)[
                'GHG QUANTITY (METRIC TONS CO2e)'
            ].sum().sort_values('REPORTING YEAR')
            
            # Calculate year-over-year changes
            yearly_totals['yoy_change'] = yearly_totals['GHG QUANTITY (METRIC TONS CO2e)'].pct_change()
            yearly_totals['yoy_change_abs'] = yearly_totals['GHG QUANTITY (METRIC TONS CO2e)'].diff()
            
            # Vectorized state trends calculation
            state_year_data = df.groupby(['STATE', 'REPORTING YEAR'], as_index=False)[
                'GHG QUANTITY (METRIC TONS CO2e)'
            ].sum().sort_values(['STATE', 'REPORTING YEAR'])
            
            # Calculate year-over-year changes by state using transform
            state_year_data['yoy_change'] = state_year_data.groupby('STATE')[
                'GHG QUANTITY (METRIC TONS CO2e)'
            ].pct_change()
            
            # Store aggregations
            self._aggregations['yearly_trends'] = yearly_totals
            self._aggregations['state_trends'] = state_year_data
            self._aggregation_status['trend_calculations'] = True
            
            logger.debug(f"Trend calculations computed for {len(yearly_totals)} years and {state_year_data['STATE'].nunique()} states")
            
        except Exception as e:
            logger.error(f"Failed to compute trend calculations: {str(e)}")
            self._aggregation_status['trend_calculations'] = False
    
    def _compute_additional_aggregations(self, df: pd.DataFrame) -> None:
        """
        Pre-compute additional common aggregations.
        """
        try:
            # Vectorized state-subpart combinations (for state breakdown graphs)
            df_clean = df[df['SUBPARTS'].notna() & (df['SUBPARTS'] != '')].copy()
            
            if len(df_clean) > 0:
                # Reuse vectorized subpart processing
                df_clean['SUBPARTS'] = df_clean['SUBPARTS'].astype(str)
                df_clean['SUBPART_LIST'] = df_clean['SUBPARTS'].str.split(',')
                state_subpart_df = df_clean.explode('SUBPART_LIST')
                state_subpart_df['SUBPART'] = state_subpart_df['SUBPART_LIST'].str.strip()
                state_subpart_df = state_subpart_df[state_subpart_df['SUBPART'] != 'nan']
                
                if len(state_subpart_df) > 0:
                    state_subpart_totals = state_subpart_df.groupby(['STATE', 'SUBPART'], as_index=False)[
                        'GHG QUANTITY (METRIC TONS CO2e)'
                    ].sum()
                    
                    self._aggregations['state_subpart_totals'] = state_subpart_totals
            
            # Summary statistics
            summary_stats = {
                'total_emissions': df['GHG QUANTITY (METRIC TONS CO2e)'].sum(),
                'total_records': len(df),
                'unique_states': df['STATE'].nunique(),
                'unique_companies': df['PARENT COMPANIES'].nunique(),
                'year_range': (df['REPORTING YEAR'].min(), df['REPORTING YEAR'].max()),
                'avg_emissions_per_record': df['GHG QUANTITY (METRIC TONS CO2e)'].mean()
            }
            
            self._aggregations['summary_stats'] = summary_stats
            self._aggregation_status['additional'] = True
            
            logger.debug("Additional aggregations computed")
            
        except Exception as e:
            logger.error(f"Failed to compute additional aggregations: {str(e)}")
            self._aggregation_status['additional'] = False
    
    def get_aggregation(self, aggregation_name: str) -> Optional[pd.DataFrame]:
        """
        Get a pre-computed aggregation by name.
        
        Args:
            aggregation_name: Name of the aggregation to retrieve
            
        Returns:
            DataFrame with the requested aggregation, or None if not available
        """
        with self._data_lock:
            if aggregation_name in self._aggregations:
                data = self._aggregations[aggregation_name]
                # Return a copy to prevent modifications
                return data.copy() if isinstance(data, pd.DataFrame) else data
            return None
    
    def get_aggregation_status(self) -> Dict[str, bool]:
        """
        Get the status of all aggregation computations.
        
        Returns:
            Dictionary with aggregation names and their computation status
        """
        return self._aggregation_status.copy()
    
    def is_aggregation_available(self, aggregation_name: str) -> bool:
        """
        Check if a specific aggregation is available.
        
        Args:
            aggregation_name: Name of the aggregation to check
            
        Returns:
            bool: True if aggregation is available, False otherwise
        """
        return aggregation_name in self._aggregations
    
    def get_available_aggregations(self) -> List[str]:
        """
        Get list of all available aggregation names.
        
        Returns:
            List of aggregation names that are available
        """
        return list(self._aggregations.keys())
    
    def clear_aggregations(self) -> None:
        """
        Clear all pre-computed aggregations to free memory.
        """
        with self._data_lock:
            self._aggregations.clear()
            self._aggregation_status.clear()
            logger.info("All aggregations cleared")

# Global instance for easy access
_data_aggregator = None

def get_data_aggregator() -> DataAggregator:
    """
    Get the global DataAggregator instance.
    
    Returns:
        DataAggregator: Global singleton instance
    """
    global _data_aggregator
    if _data_aggregator is None:
        _data_aggregator = DataAggregator()
    return _data_aggregator

def get_pre_aggregated_data(aggregation_name: str) -> Optional[pd.DataFrame]:
    """
    Convenience function to get pre-aggregated data.
    
    Args:
        aggregation_name: Name of the aggregation to retrieve
        
    Returns:
        DataFrame with the requested aggregation, or None if not available
    """
    aggregator = get_data_aggregator()
    return aggregator.get_aggregation(aggregation_name)
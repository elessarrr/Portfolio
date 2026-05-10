import pandas as pd
import streamlit as st
from datetime import timedelta
from typing import Dict

# Error handling decorator
def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"Error in {func.__name__}: {str(e)}")
            return None
    return wrapper

@handle_exceptions
def run_simulation(input_df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """Run supply disruption simulation with the following logic:
    - Uses historical data as baseline
    - Applies weekly changes based on selected scenarios
    - Incorporates compounding effects over time
    - Prevents negative inventory values
    """
    try:
        # Check if input data is empty and return empty dataframe if so
        if input_df.empty:
            return pd.DataFrame(columns=['period', 'inventory', 'type'])
            
        # Sort data by period and calculate total inventory per period
        recent_data = input_df.copy()
        # Ensure inventory is numeric
        recent_data['inventory'] = pd.to_numeric(recent_data['inventory'], errors='coerce')
        recent_data = recent_data.groupby('period')['inventory'].sum().reset_index()
        recent_data = recent_data.sort_values('period')
        
        # Calculate 13-week moving average on aggregated data
        recent_data['MA_13w'] = recent_data['inventory'].rolling(window=13, min_periods=1).mean()
        
        # Drop any remaining NaN values
        recent_data = recent_data.dropna(subset=['MA_13w'])
        
        # Check if we have enough data points after preprocessing
        if len(recent_data) < 2:
            st.warning("Not enough data points to calculate trend.")
            return pd.DataFrame(columns=['period', 'inventory', 'type'])
        
        # Get latest date and use moving average as starting point
        latest_date = recent_data['period'].max()
        start_inventory = float(recent_data['MA_13w'].iloc[-1])  # Ensure numeric type
        
        # Calculate average weekly change from moving average
        ma_weekly_change = float((recent_data['MA_13w'].iloc[-1] - recent_data['MA_13w'].iloc[0])) / len(recent_data)
        
        # Create future dates for simulation period
        future_dates = [latest_date + timedelta(weeks=i) for i in range(1, params['sim_duration']+1)]
        
        # Initialize simulation results
        sim_results = []
        current_inventory = start_inventory  # Track running inventory level

        # Apply scenario effects week by week
        for i, date in enumerate(future_dates):
            # Base weekly change from moving average trend
            weekly_change = ma_weekly_change
            
            # Apply production cut impact with compounding effect
            if params['prod_cut']:
                production_impact = 2.5 + (i * 0.2)  # Increased impact over time
                weekly_change *= production_impact
            
            # Apply demand spike impact with compounding effect
            if params['demand_spike']:
                demand_impact = 2.3 + (i * 0.1)  # Increased impact over time
                weekly_change *= demand_impact
            
            # Add SPR release effect if enabled
            if params['spr_release']:
                # Calculate the proportion of total inventory for scaling SPR release
                total_us_inventory = float(input_df.groupby('period')['inventory'].sum().iloc[-1])
                selected_regions_inventory = float(input_df[input_df['period'] == latest_date]['inventory'].sum())
                spr_scale_factor = selected_regions_inventory / total_us_inventory if total_us_inventory > 0 else 1
                weekly_change += 3000 * spr_scale_factor  # Scale SPR release based on regional proportion

            # Update inventory
            current_inventory = float(current_inventory + weekly_change)
            
            # Store result for this week
            sim_results.append({
                'period': date,
                'inventory': current_inventory,
                'type': 'Simulated'
            })
        
        # Create simulation DataFrame
        sim_df = pd.DataFrame(sim_results)
        
        # Add historical data and moving average with type labels
        hist_df = recent_data.copy()
        hist_df['type'] = 'Historical'
        
        # Create trendline data
        trend_df = recent_data.copy()
        trend_df['type'] = 'Trendline'
        trend_df['inventory'] = trend_df['MA_13w']
        
        # Select columns for visualization
        hist_df = hist_df[['period', 'inventory', 'type']]
        trend_df = trend_df[['period', 'inventory', 'type']]
        
        # Combine historical and simulated data for visualization
        combined_df = pd.concat([hist_df, trend_df, sim_df], ignore_index=True)
        return combined_df
    
    except Exception as e:
        st.error(f"Simulation error: {str(e)}")
        return pd.DataFrame(columns=['period', 'inventory', 'type'])
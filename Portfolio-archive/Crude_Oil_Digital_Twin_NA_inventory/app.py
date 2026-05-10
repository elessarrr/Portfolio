import streamlit as st
from modules.data_handler import load_crude_oil_data, load_wti_price_data
from modules.simulation import run_simulation
from modules.visualization import (
    display_key_metrics,
    plot_inventory_trends,
    display_scenario_controls,
    display_region_selector
)

# Configuration
try:
    st.set_page_config(
        page_title="Crude Oil Digital Twin",
        page_icon="🛢️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
except Exception as e:
    st.error(f"Page configuration error: {str(e)}")

def main():
    st.title("🛢️ Crude Oil Inventory Digital Twin")
    st.markdown("Interactive analysis of U.S. crude oil stockpiles with supply disruption simulation")
    st.markdown("**Note:** BBL stands for 'Barrel', the standard unit of measurement for petroleum products. One barrel equals 42 U.S. gallons or 159 liters.")

    # Load data
    data = load_crude_oil_data()
    if not data:
        st.stop()
        
    # Load WTI price data using the same date range
    price_data = load_wti_price_data(
        start_date=data['start_date'].strftime('%Y-%m-%d'),
        end_date=data['latest_date'].strftime('%Y-%m-%d')
    )

    # Display region selector in sidebar
    selected_region = display_region_selector(data['regions'])

    # Get latest data for metrics display (using full dataset)
    latest_data = data['data'].sort_values('period', ascending=False)
    display_key_metrics(latest_data, price_data)
    
    # Filter data for selected region (for simulation)
    region_data = data['data'][data['data']['region'] == selected_region].copy()

    # Get simulation parameters from sidebar
    sim_params = display_scenario_controls()

    # Run simulation
    simulation_results = run_simulation(region_data, sim_params)

    # Plot results
    if simulation_results is not None and not simulation_results.empty:
        plot_inventory_trends(simulation_results, price_data, sim_params)
    else:
        st.error("No simulation results available to display")

    # Add footer with data attribution
    st.markdown("""
    <div style='margin-top:30px; padding-top:20px; border-top:1px solid #e6e6e6; text-align:center; color:#666; font-size:12px;'>
        Data source: U.S. Energy Information Administration (EIA)
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()

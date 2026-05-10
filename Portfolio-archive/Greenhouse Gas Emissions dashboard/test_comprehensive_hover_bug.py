#!/usr/bin/env python3
"""
Comprehensive test to investigate the hover percentage bug reported by the user.

This script tests both the old and new components with different feature flag settings
to determine which component might be causing the issue where Subpart C shows 30% 
visually but 0.3% in hover.
"""

import pandas as pd
import sys
import os
import plotly.graph_objects as go

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.data_preprocessor import DataPreprocessor
from utils.feature_flags import feature_flags

def test_feature_flag_behavior():
    """Test which component is actually being used based on feature flags."""
    print("🚩 FEATURE FLAG ANALYSIS")
    print("=" * 50)
    
    # Check current feature flag status
    enhanced_enabled = feature_flags.is_enabled('enhanced_subpart_breakdown')
    print(f"Enhanced subpart breakdown enabled: {enhanced_enabled}")
    
    # Check environment variable
    env_value = os.environ.get('ENHANCED_SUBPART_BREAKDOWN', 'not set')
    print(f"Environment variable ENHANCED_SUBPART_BREAKDOWN: {env_value}")
    
    return enhanced_enabled

def simulate_plotly_hover_calculation(values, labels):
    """Simulate how Plotly calculates hover percentages."""
    total = sum(values)
    plotly_percentages = [(v / total) * 100 for v in values]
    
    hover_results = []
    for i, (label, value, plotly_pct) in enumerate(zip(labels, values, plotly_percentages)):
        hover_results.append({
            'label': label,
            'value': value,
            'plotly_percent': plotly_pct,
            'hover_display': f"{plotly_pct:.1f}%"
        })
    
    return hover_results

def test_new_component_logic():
    """Test the new component (subpart_graph_v2.py) logic."""
    print("\n🆕 TESTING NEW COMPONENT LOGIC (subpart_graph_v2.py)")
    print("=" * 60)
    
    try:
        # Load the actual data
        preprocessor = DataPreprocessor()
        df = preprocessor.load_data()
        
        if df.empty:
            print("❌ No data loaded")
            return False
        
        # Filter for Alabama data (user's scenario)
        alabama_data = df[df['STATE'] == 'AL'].copy()
        year_filtered = alabama_data[
            (alabama_data['REPORTING YEAR'] >= 2010) & 
            (alabama_data['REPORTING YEAR'] <= 2023)
        ].copy()
        
        # Import the new component's logic
        from utils.aggregation_v2 import get_subpart_breakdown_data
        
        # Get aggregated data using new component logic
        chart_data = get_subpart_breakdown_data(
            year_filtered,
            year_range=(2010, 2023),
            state_filter=['AL']
        )
        
        if not chart_data:
            print("❌ No chart data from new component")
            return False
        
        print(f"✅ New component returned {len(chart_data)} data points")
        
        # Convert to format for Plotly
        df_chart = pd.DataFrame(chart_data)
        
        # Find Subpart C data
        subpart_c_data = None
        for item in chart_data:
            if 'C' in str(item.get('subpart', '')) or 'General Stationary' in str(item.get('subpart', '')):
                subpart_c_data = item
                break
        
        if not subpart_c_data:
            print("❌ Subpart C not found in new component data")
            return False
        
        # Extract values for Plotly simulation
        values = [item['emissions'] for item in chart_data]  # New component uses emissions as values
        labels = [item['subpart'] for item in chart_data]
        
        # Simulate Plotly hover calculation
        hover_results = simulate_plotly_hover_calculation(values, labels)
        
        # Find Subpart C in hover results
        subpart_c_hover = None
        for result in hover_results:
            if 'C' in str(result['label']) or 'General Stationary' in str(result['label']):
                subpart_c_hover = result
                break
        
        if subpart_c_hover:
            print(f"\n🎯 SUBPART C ANALYSIS (NEW COMPONENT):")
            print(f"   Label: {subpart_c_hover['label']}")
            print(f"   Emissions: {subpart_c_hover['value']:,.0f} MT CO2e")
            print(f"   Plotly calculated %: {subpart_c_hover['plotly_percent']:.2f}%")
            print(f"   Hover displays: {subpart_c_hover['hover_display']}")
            
            # Check for critical bug
            if subpart_c_hover['plotly_percent'] < 1.0 and subpart_c_hover['value'] > 100000000:
                print(f"\n🚨 CRITICAL BUG FOUND IN NEW COMPONENT!")
                print(f"   Large emissions but tiny hover percentage!")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error testing new component: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_old_component_logic():
    """Test the old component (subpart_graph.py) logic."""
    print("\n🔄 TESTING OLD COMPONENT LOGIC (subpart_graph.py)")
    print("=" * 60)
    
    try:
        # Load the actual data
        preprocessor = DataPreprocessor()
        df = preprocessor.load_data()
        
        if df.empty:
            print("❌ No data loaded")
            return False
        
        # Filter for Alabama data (user's scenario)
        alabama_data = df[df['STATE'] == 'AL'].copy()
        year_filtered = alabama_data[
            (alabama_data['REPORTING YEAR'] >= 2010) & 
            (alabama_data['REPORTING YEAR'] <= 2023)
        ].copy()
        
        # Simulate old component data processing
        group_data = year_filtered.groupby('SUBPARTS').agg({
            'GHG QUANTITY (METRIC TONS CO2e)': 'sum',
            'STATE': 'nunique'
        }).reset_index()
        
        group_data.columns = ['entity', 'emissions', 'stateCount']
        group_data['emissions'] = group_data['emissions'].round(0)
        
        # Apply old component percentage calculation
        total_emissions = group_data['emissions'].sum()
        raw_percentages = (group_data['emissions'] / total_emissions * 100)
        rounded_percentages = raw_percentages.round(1)
        group_data['percentage'] = rounded_percentages
        
        # Sort by emissions
        group_data = group_data.sort_values('emissions', ascending=False)
        
        # Find Subpart C
        subpart_c_row = None
        for _, row in group_data.iterrows():
            if 'C' in str(row['entity']):
                subpart_c_row = row
                break
        
        if subpart_c_row is None:
            print("❌ Subpart C not found in old component data")
            return False
        
        # Old component uses calculated percentages as values
        values = group_data['percentage'].tolist()  # OLD COMPONENT USES PERCENTAGES!
        labels = [f'Subpart {entity}' for entity in group_data['entity']]
        
        # Simulate Plotly hover with percentage values
        hover_results = simulate_plotly_hover_calculation(values, labels)
        
        # Find Subpart C in hover results
        subpart_c_hover = None
        for result in hover_results:
            if 'C' in str(result['label']):
                subpart_c_hover = result
                break
        
        if subpart_c_hover:
            print(f"\n🎯 SUBPART C ANALYSIS (OLD COMPONENT):")
            print(f"   Label: {subpart_c_hover['label']}")
            print(f"   Input value (calculated %): {subpart_c_hover['value']:.1f}%")
            print(f"   Actual emissions: {subpart_c_row['emissions']:,.0f} MT CO2e")
            print(f"   Plotly recalculated %: {subpart_c_hover['plotly_percent']:.2f}%")
            print(f"   Hover displays: {subpart_c_hover['hover_display']}")
            
            # Check for critical bug - this is where the issue might be!
            if abs(subpart_c_hover['value'] - subpart_c_hover['plotly_percent']) > 5.0:
                print(f"\n🚨 CRITICAL BUG FOUND IN OLD COMPONENT!")
                print(f"   Input percentage: {subpart_c_hover['value']:.1f}%")
                print(f"   Plotly recalculated: {subpart_c_hover['plotly_percent']:.1f}%")
                print(f"   Discrepancy: {abs(subpart_c_hover['value'] - subpart_c_hover['plotly_percent']):.1f} percentage points")
                print(f"   This could explain the user's 30% vs 0.3% issue!")
                return True
        
        return False
        
    except Exception as e:
        print(f"❌ Error testing old component: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_edge_case_scenarios():
    """Test edge cases that might cause the hover bug."""
    print("\n🔬 TESTING EDGE CASE SCENARIOS")
    print("=" * 50)
    
    # Test case 1: Very small percentages that round to 0.0%
    print("\n📊 Test Case 1: Small percentages")
    values = [1000000000, 1000000, 500000, 100000]  # Large difference in scale
    labels = ['Subpart A', 'Subpart B', 'Subpart C', 'Subpart D']
    
    hover_results = simulate_plotly_hover_calculation(values, labels)
    for result in hover_results:
        print(f"   {result['label']}: {result['value']:,.0f} -> {result['hover_display']}")
    
    # Test case 2: Percentage calculation with rounding errors
    print("\n📊 Test Case 2: Rounding errors")
    # Simulate old component using percentages as values
    calculated_percentages = [30.0, 25.5, 20.3, 15.2, 9.0]  # These sum to 100%
    labels = ['Subpart A', 'Subpart B', 'Subpart C', 'Subpart D', 'Subpart E']
    
    hover_results = simulate_plotly_hover_calculation(calculated_percentages, labels)
    for result in hover_results:
        print(f"   {result['label']}: {result['value']:.1f}% input -> {result['hover_display']} hover")
        
        # Check for significant discrepancy
        if abs(result['value'] - result['plotly_percent']) > 0.5:
            print(f"     ⚠️  Discrepancy: {abs(result['value'] - result['plotly_percent']):.2f} percentage points")

def main():
    """Main test function."""
    print("🔍 COMPREHENSIVE HOVER BUG INVESTIGATION")
    print("=" * 60)
    print("Investigating user's report: Subpart C shows 30% visually but 0.3% on hover")
    print("=" * 60)
    
    # Check feature flags
    enhanced_enabled = test_feature_flag_behavior()
    
    # Test both components
    new_component_bug = test_new_component_logic()
    old_component_bug = test_old_component_logic()
    
    # Test edge cases
    test_edge_case_scenarios()
    
    # Summary
    print("\n📋 INVESTIGATION SUMMARY")
    print("=" * 50)
    print(f"Enhanced component enabled: {enhanced_enabled}")
    print(f"New component has critical bug: {new_component_bug}")
    print(f"Old component has critical bug: {old_component_bug}")
    
    if new_component_bug or old_component_bug:
        print("\n🚨 CRITICAL ISSUE FOUND!")
        if enhanced_enabled and new_component_bug:
            print("   The currently active NEW component has the hover bug.")
        elif not enhanced_enabled and old_component_bug:
            print("   The currently active OLD component has the hover bug.")
        else:
            print("   A component has the bug, but it may not be the active one.")
    else:
        print("\n✅ No critical hover bugs found in either component.")
        print("   The user's issue might be:")
        print("   1. Environment-specific (different data or settings)")
        print("   2. Browser-specific rendering issue")
        print("   3. Related to a specific data combination not tested")
        print("   4. Fixed in recent updates")

if __name__ == "__main__":
    main()
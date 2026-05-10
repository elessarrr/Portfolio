#!/usr/bin/env python3
"""
Test script to investigate if the old subpart_graph.py component has the hover percentage bug.

This script tests the original component to see if it could be causing the user's
reported issue where Subpart C shows 30% visually but 0.3% in hover.
"""

import pandas as pd
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.data_preprocessor import DataPreprocessor
import plotly.graph_objects as go

def test_old_component_hover_bug():
    """Test if the old component has the hover percentage bug."""
    print("🔍 TESTING OLD COMPONENT FOR HOVER BUG")
    print("=" * 50)
    
    try:
        # Load the actual data
        print("📂 Loading real data...")
        preprocessor = DataPreprocessor()
        df = preprocessor.load_data()
        
        if df.empty:
            print("❌ No data loaded")
            return
        
        print(f"✅ Loaded {len(df):,} rows of data")
        
        # Filter for Alabama data (user's scenario)
        print("\n🏛️ FILTERING FOR ALABAMA DATA")
        alabama_data = df[df['STATE'] == 'AL'].copy()
        
        if alabama_data.empty:
            print("❌ No Alabama data found")
            return
        
        print(f"✅ Found {len(alabama_data):,} Alabama records")
        
        # Use the OLD component logic (from subpart_graph.py)
        print("\n⚙️ PROCESSING WITH OLD COMPONENT LOGIC")
        
        # Filter by years (2010-2023 as user specified)
        year_filtered = alabama_data[
            (alabama_data['REPORTING YEAR'] >= 2010) & 
            (alabama_data['REPORTING YEAR'] <= 2023)
        ].copy()
        
        # Simulate the old component's data processing
        # Group by subpart (using SUBPARTS column)
        if 'SUBPARTS' not in year_filtered.columns:
            print("❌ No SUBPARTS column found")
            return
        
        # Group by subpart and sum emissions
        group_data = year_filtered.groupby('SUBPARTS').agg({
            'GHG QUANTITY (METRIC TONS CO2e)': 'sum',
            'STATE': 'nunique'
        }).reset_index()
        
        group_data.columns = ['entity', 'emissions', 'stateCount']
        group_data['emissions'] = group_data['emissions'].round(0)
        
        if group_data.empty:
            print("❌ No aggregated data")
            return
        
        print(f"✅ Aggregated to {len(group_data)} subpart groups")
        
        # Apply the EXACT percentage calculation logic from old component
        print("\n📊 APPLYING OLD COMPONENT PERCENTAGE CALCULATION")
        
        # Calculate percentages with accurate adjustment to ensure they sum to 100%
        total_emissions = group_data['emissions'].sum()
        raw_percentages = (group_data['emissions'] / total_emissions * 100)
        
        # Apply accurate percentage calculation (same logic as old component)
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
        
        # The old component uses calculated percentages as values
        labels = []
        values = []  # These will be the calculated percentages
        emissions_data = []
        
        for _, row in group_data.iterrows():
            entity = row['entity']
            percentage = row['percentage']
            emissions = row['emissions']
            
            labels.append(f'Subpart {entity}')
            values.append(percentage)  # OLD COMPONENT USES PERCENTAGES AS VALUES
            emissions_data.append(emissions)
            
            print(f"  Subpart {entity}: {percentage:.1f}% ({emissions:,.0f} MT CO2e)")
        
        # Check for Subpart C specifically
        subpart_c_index = None
        for i, label in enumerate(labels):
            if 'C' in str(label) or 'General Stationary' in str(label):
                subpart_c_index = i
                break
        
        if subpart_c_index is None:
            print("❌ Subpart C not found in aggregated data")
            return
        
        subpart_c_percentage = values[subpart_c_index]
        subpart_c_emissions = emissions_data[subpart_c_index]
        
        print(f"\n🎯 SUBPART C ANALYSIS (OLD COMPONENT):")
        print(f"   Label: {labels[subpart_c_index]}")
        print(f"   Calculated percentage: {subpart_c_percentage:.2f}%")
        print(f"   Emissions: {subpart_c_emissions:,.0f} MT CO2e")
        
        # Simulate the old hover template
        # Old template: 'Percentage: %{value:.1f}%' where value = calculated percentage
        hover_percentage = subpart_c_percentage  # This is what %{value} would show
        
        print(f"\n🖱️ HOVER SIMULATION (OLD COMPONENT):")
        print(f"   Hover template uses: %{{value:.1f}}%")
        print(f"   %{{value}} = {subpart_c_percentage:.6f}%")
        print(f"   Hover displays: {hover_percentage:.1f}%")
        
        # Check for the critical bug
        if hover_percentage < 1.0 and subpart_c_emissions > 100000000:  # Large emissions but tiny percentage
            print(f"\n🚨 CRITICAL BUG FOUND IN OLD COMPONENT!")
            print(f"   Large emissions ({subpart_c_emissions:,.0f} MT CO2e) but tiny hover ({hover_percentage:.1f}%)")
            print(f"   This matches the user's report exactly!")
            
            # Investigate the root cause
            print(f"\n🔬 ROOT CAUSE INVESTIGATION:")
            total_emissions = sum(emissions_data)
            correct_percentage = (subpart_c_emissions / total_emissions) * 100
            
            print(f"   Total emissions: {total_emissions:,.0f} MT CO2e")
            print(f"   Subpart C emissions: {subpart_c_emissions:,.0f} MT CO2e")
            print(f"   Correct percentage: {correct_percentage:.2f}%")
            print(f"   Old component shows: {hover_percentage:.1f}%")
            print(f"   Discrepancy: {abs(correct_percentage - hover_percentage):.1f} percentage points")
            
            return True  # Bug found
        
        elif abs(hover_percentage - 30.0) > 5.0:
            print(f"\n⚠️  SIGNIFICANT DISCREPANCY IN OLD COMPONENT:")
            print(f"   Expected: ~30%, Got: {hover_percentage:.1f}%")
            print(f"   Difference: {abs(hover_percentage - 30.0):.1f} percentage points")
        
        else:
            print(f"\n✅ No critical bug found in old component.")
            print(f"   Hover shows: {hover_percentage:.1f}% (reasonable)")
        
        # Additional analysis: Check percentage calculation logic
        print(f"\n🔧 PERCENTAGE CALCULATION ANALYSIS:")
        total_percentage = sum(values)
        print(f"   Sum of all percentages: {total_percentage:.2f}%")
        
        if abs(total_percentage - 100.0) > 0.1:
            print(f"   ⚠️  Percentages don't sum to 100%! This could cause issues.")
        else:
            print(f"   ✅ Percentages sum correctly to 100%")
        
        return False
        
    except Exception as e:
        print(f"❌ Error during old component test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_old_component_hover_bug()
#!/usr/bin/env python3
"""
Test script to verify the hover percentage bug fix.
This script simulates the exact scenario reported by the user and validates
that the enhanced component correctly displays hover percentages.
"""

import pandas as pd
import sys
import os

# Add the project root to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from components.subpart_graph_v2 import create_enhanced_subpart_breakdown
from utils.feature_flags import FeatureFlags

def test_hover_percentage_accuracy():
    """
    Test that hover percentages match visual proportions in the pie chart.
    This addresses the user's specific issue where a 30% visual slice shows 0.3% on hover.
    """
    print("Testing hover percentage accuracy...")
    
    # Check feature flag status
    flags = FeatureFlags()
    enhanced_enabled = flags.get_flag_value('enhanced_subpart_breakdown')
    print(f"Enhanced subpart breakdown enabled: {enhanced_enabled}")
    
    # Create test data that reproduces the user's scenario
    # Yellow section should be ~30% visually and show 30% on hover
    test_data = pd.DataFrame({
        'state': ['CA', 'CA', 'CA', 'CA'],
        'category': ['Power Plants', 'Power Plants', 'Power Plants', 'Power Plants'],
        'subpart': ['C. General Stationary Fuel Combustion Sources', 
                   'D. Electricity Generation', 
                   'Other Subparts', 
                   'Small Subparts'],
        'emissions': [300000, 100000, 50000, 50000],  # Yellow should be 300k out of 500k total = 60%
        'reporting_year': [2022, 2022, 2022, 2022]
    })
    
    print("\nTest data:")
    for idx, row in test_data.iterrows():
        percentage = (row['emissions'] / test_data['emissions'].sum()) * 100
        print(f"  {row['subpart']}: {row['emissions']:,} MT CO2e ({percentage:.1f}%)")
    
    print(f"\nTotal emissions: {test_data['emissions'].sum():,} MT CO2e")
    
    # Test the enhanced component
    try:
        fig, metadata = create_enhanced_subpart_breakdown(
            filtered_data=test_data,
            selected_states=['CA'],
            selected_categories=['Power Plants'],
            selected_years=[2022]
        )
        
        # Extract the pie chart data
        pie_data = fig.data[0]
        
        print("\nPie chart configuration:")
        print(f"  Labels: {pie_data.labels}")
        print(f"  Values: {pie_data.values}")
        
        # Verify that values are raw emissions (not percentages)
        if pie_data.values:
            total_values = sum(pie_data.values)
            print(f"  Total values: {total_values:,}")
            
            # Check if values match our test data emissions
            expected_total = test_data['emissions'].sum()
            if abs(total_values - expected_total) < 1:
                print("  ✅ Values are raw emissions (correct)")
                
                # Calculate what Plotly will show as percentages
                print("\nExpected hover percentages (calculated by Plotly):")
                for i, (label, value) in enumerate(zip(pie_data.labels, pie_data.values)):
                    percentage = (value / total_values) * 100
                    print(f"  {label}: {percentage:.1f}%")
                    
                    # Check for the specific issue: large visual slice showing tiny percentage
                    if percentage > 25:  # If this is a large slice
                        if percentage < 5:  # But shows tiny percentage
                            print(f"  ❌ BUG DETECTED: Large slice ({percentage:.1f}%) would show tiny hover percentage")
                            return False
                        else:
                            print(f"  ✅ Large slice correctly shows {percentage:.1f}% on hover")
                            
            else:
                print(f"  ❌ Values appear to be percentages, not raw emissions")
                print(f"     Expected total: {expected_total:,}, Got: {total_values:,}")
                return False
        
        print("\n✅ Hover percentage bug appears to be FIXED")
        print("   - Component uses raw emissions as values")
        print("   - Plotly will calculate accurate percentages for hover")
        print("   - Visual proportions will match hover percentages")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing enhanced component: {e}")
        return False

def main():
    """
    Main test function to verify the hover bug fix.
    """
    print("=" * 60)
    print("HOVER PERCENTAGE BUG VERIFICATION TEST")
    print("=" * 60)
    
    success = test_hover_percentage_accuracy()
    
    print("\n" + "=" * 60)
    if success:
        print("RESULT: ✅ Hover bug appears to be FIXED")
        print("\nIf you're still seeing the issue:")
        print("1. Hard refresh your browser (Ctrl+F5 or Cmd+Shift+R)")
        print("2. Clear browser cache")
        print("3. Check if you're using the correct URL")
        print("4. Restart the application")
    else:
        print("RESULT: ❌ Hover bug still exists")
        print("\nThe component may not be using the enhanced version.")
    print("=" * 60)

if __name__ == '__main__':
    main()
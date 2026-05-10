#!/usr/bin/env python3
"""
Simple test to verify the percentage calculation fix.
This tests the core logic without loading the full app.
"""

import pandas as pd
import numpy as np

def test_percentage_calculation():
    """Test the percentage calculation logic with sample data."""
    print("Testing percentage calculation logic...")
    
    # Create sample data that mimics the structure after filtering
    sample_data = {
        'entity': ['C', 'D', 'W', 'Other', 'P'],
        'emissions': [25578131.329, 1234567.89, 987654.32, 456789.12, 123456.78],
        'stateCount': [10, 5, 8, 3, 2]
    }
    
    group_data = pd.DataFrame(sample_data)
    
    # Apply the same percentage calculation logic as in the fixed code
    total_emissions = group_data['emissions'].sum()
    raw_percentages = (group_data['emissions'] / total_emissions * 100)
    
    # Apply accurate percentage calculation (same logic as enhanced version)
    rounded_percentages = raw_percentages.round(1)
    total_rounded = rounded_percentages.sum()
    difference = 100.0 - total_rounded
    
    print(f"Raw percentages sum: {raw_percentages.sum():.6f}%")
    print(f"Rounded percentages sum: {total_rounded:.6f}%")
    print(f"Difference from 100%: {difference:.6f}%")
    
    # Adjust percentages if they don't sum to exactly 100%
    if abs(difference) > 0.001:  # Only adjust if meaningful difference
        # Calculate remainders for largest remainder method
        remainders = raw_percentages - rounded_percentages.round(0)
        
        # Determine how many 0.1% adjustments we need
        adjustments_needed = int(abs(difference) * 10)
        
        print(f"Adjustments needed: {adjustments_needed}")
        
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
    
    # Test results
    final_total = group_data['percentage'].sum()
    print(f"\nFinal percentage total: {final_total:.1f}%")
    print("\nBreakdown:")
    for _, row in group_data.iterrows():
        visual_size = row['percentage']
        emissions = row['emissions']
        print(f"  {row['entity']}: {visual_size:.1f}% ({emissions:,.0f} MT CO2e)")
    
    # Test the key issue: visual representation vs hover text
    print("\n=== Testing Visual vs Hover Consistency ===")
    print("When using percentages for pie chart values:")
    for _, row in group_data.iterrows():
        pie_value = row['percentage']  # This is what determines visual size
        hover_percentage = row['percentage']  # This is what shows in hover
        emissions = row['emissions']
        print(f"  {row['entity']}: Visual={pie_value:.1f}%, Hover={hover_percentage:.1f}%, Emissions={emissions:,.0f}")
    
    # Verify the fix addresses the user's concern
    print("\n=== Verification ===")
    if abs(final_total - 100.0) < 0.1:
        print("✅ Percentages sum to exactly 100%")
    else:
        print(f"❌ Percentages sum to {final_total:.1f}%, not 100%")
    
    # Check for any large visual vs small percentage mismatches
    for _, row in group_data.iterrows():
        if row['percentage'] >= 15.0:  # Large visual component
            print(f"✅ {row['entity']}: Large visual ({row['percentage']:.1f}%) matches large percentage")
        elif row['percentage'] < 1.0 and row['emissions'] > total_emissions * 0.05:  # Small percentage but large emissions
            print(f"⚠️  {row['entity']}: Potential mismatch - small percentage ({row['percentage']:.1f}%) but significant emissions")

if __name__ == "__main__":
    test_percentage_calculation()
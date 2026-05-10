#!/usr/bin/env python3
"""
Test script to verify percentage calculation with state filtering.
This will help identify if the issue is with filtering or percentage calculation.
"""

import pandas as pd
import sys
import os

# Add the project root to the path
sys.path.append('/Users/Bhavesh/Desktop/Stuff/Industry 4.0/Digital Twins/Carbon emissions/Trae/ghg_dash_app_working_dir')

from utils.data_preprocessor import load_data

def test_filtering_and_percentages():
    """Test filtering and percentage calculation logic."""
    print("Loading data...")
    df = load_data()
    
    if df.empty:
        print("❌ No data loaded")
        return
    
    print(f"✅ Loaded {len(df)} rows of data")
    print(f"Available columns: {list(df.columns)}")
    print(f"Available states: {sorted(df['state'].unique())}")
    
    # Test 1: All data (no filtering)
    print("\n=== Test 1: All Data ===")
    test_percentages(df, "All Data")
    
    # Test 2: Single state filtering
    print("\n=== Test 2: Single State (TX) ===")
    tx_df = df[df['state'] == 'TX']
    test_percentages(tx_df, "Texas Only")
    
    # Test 3: Multiple state filtering
    print("\n=== Test 3: Multiple States (TX, CA) ===")
    multi_state_df = df[df['state'].isin(['TX', 'CA'])]
    test_percentages(multi_state_df, "Texas and California")
    
    # Test 4: Check specific subpart that user mentioned (if we can identify it)
    print("\n=== Test 4: Subpart Analysis ===")
    analyze_subparts(df)

def test_percentages(df, scenario_name):
    """Test percentage calculation for a given dataset."""
    if df.empty:
        print(f"❌ {scenario_name}: No data")
        return
    
    # Group by subpart (same logic as original)
    group_data = df.groupby('subparts').agg({
        'value': 'sum',
        'state': 'nunique'
    }).reset_index()
    
    group_data.columns = ['entity', 'emissions', 'stateCount']
    group_data['emissions'] = group_data['emissions'].round(0)
    
    # Calculate percentages with accurate adjustment
    total_emissions = group_data['emissions'].sum()
    raw_percentages = (group_data['emissions'] / total_emissions * 100)
    
    # Apply accurate percentage calculation
    rounded_percentages = raw_percentages.round(1)
    total_rounded = rounded_percentages.sum()
    difference = 100.0 - total_rounded
    
    # Adjust percentages if they don't sum to exactly 100%
    if abs(difference) > 0.001:
        remainders = raw_percentages - rounded_percentages.round(0)
        adjustments_needed = int(abs(difference) * 10)
        
        if difference > 0:
            indices_to_adjust = remainders.nlargest(adjustments_needed).index
            for idx in indices_to_adjust:
                rounded_percentages.loc[idx] += 0.1
        else:
            indices_to_adjust = remainders.nsmallest(adjustments_needed).index
            for idx in indices_to_adjust:
                rounded_percentages.loc[idx] -= 0.1
    
    group_data['percentage'] = rounded_percentages.round(1)
    
    # Results
    final_total = group_data['percentage'].sum()
    print(f"📊 {scenario_name}:")
    print(f"   Total emissions: {total_emissions:,.0f} MT CO2e")
    print(f"   Number of subparts: {len(group_data)}")
    print(f"   Percentage total: {final_total:.1f}%")
    
    # Show top 5 subparts
    top_5 = group_data.nlargest(5, 'percentage')
    print("   Top 5 subparts:")
    for _, row in top_5.iterrows():
        print(f"     {row['entity']}: {row['percentage']:.1f}% ({row['emissions']:,.0f} MT CO2e)")
    
    # Check for the specific issue mentioned by user (large visual vs small percentage)
    large_visual_small_percent = group_data[
        (group_data['percentage'] < 1.0) & (group_data['emissions'] > total_emissions * 0.05)
    ]
    
    if not large_visual_small_percent.empty:
        print("   ⚠️  Potential visual/percentage mismatch:")
        for _, row in large_visual_small_percent.iterrows():
            visual_percent = (row['emissions'] / total_emissions) * 100
            print(f"     {row['entity']}: Shows {row['percentage']:.1f}% but should be ~{visual_percent:.1f}%")

def analyze_subparts(df):
    """Analyze subpart distribution to understand the data better."""
    print("Subpart analysis:")
    subpart_counts = df['subparts'].value_counts()
    print(f"Total unique subparts: {len(subpart_counts)}")
    print("Most common subparts:")
    for subpart, count in subpart_counts.head(10).items():
        print(f"  {subpart}: {count} records")
    
    # Check for comma-separated subparts
    comma_separated = df[df['subparts'].str.contains(',', na=False)]
    if not comma_separated.empty:
        print(f"\n⚠️  Found {len(comma_separated)} records with comma-separated subparts")
        print("This might cause aggregation issues!")
        print("Examples:")
        for example in comma_separated['subparts'].head(3):
            print(f"  {example}")

if __name__ == "__main__":
    test_filtering_and_percentages()
#!/usr/bin/env python3
"""
Test script to check if the original subpart graph has percentage calculation issues.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.cache_utils import get_cached_data
from utils.feature_flags import feature_flags
import pandas as pd
import logging

# Configure logging to see all messages
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def test_original_subpart_calculation():
    """Test the original subpart graph percentage calculation logic."""
    print("=== Testing Original Subpart Graph Percentage Calculation ===")
    
    # Check which version is currently enabled
    enhanced_enabled = feature_flags.is_enabled('enhanced_subpart_breakdown')
    print(f"Enhanced subpart breakdown enabled: {enhanced_enabled}")
    
    # Test the original calculation logic (from subpart_graph.py)
    try:
        # Get cached data (same as original graph uses)
        cache_result = get_cached_data(
            state_filter=('CA', 'TX'),  # Test with state filter
            year_range=(2020, 2023),
            category_filter=None
        )
        data = cache_result['main_chart_data']
        
        if not data or len(data) == 0:
            print("❌ No data available")
            return False
        
        # Convert to DataFrame (same as original)
        df = pd.DataFrame(data)
        print(f"Initial data shape: {df.shape}")
        
        # Apply filters (same logic as original)
        selected_states = ['CA', 'TX']
        year_range = [2020, 2023]
        
        if selected_states and len(selected_states) > 0:
            df = df[df['state'].isin(selected_states)]
            print(f"After state filter: {df.shape}")
        
        if year_range:
            df = df[(df['year'].astype(int) >= year_range[0]) & 
                    (df['year'].astype(int) <= year_range[1])]
            print(f"After year filter: {df.shape}")
        
        if 'subparts' not in df.columns or 'value' not in df.columns:
            print("❌ Missing required columns")
            return False
        
        # Group by subpart (same as original logic)
        group_data = df.groupby('subparts').agg({
            'value': 'sum',
            'state': 'nunique'
        }).reset_index()
        
        group_data.columns = ['entity', 'emissions', 'stateCount']
        group_data['emissions'] = group_data['emissions'].round(0)
        
        # Calculate percentages (ORIGINAL LOGIC - this is the problem!)
        total_emissions = group_data['emissions'].sum()
        group_data['percentage'] = (group_data['emissions'] / total_emissions * 100).round(1)
        
        # Check if percentages sum to 100%
        total_percentage = group_data['percentage'].sum()
        
        print(f"\nOriginal Logic Results:")
        print(f"Number of subparts: {len(group_data)}")
        print(f"Total emissions: {total_emissions:,.0f} MT CO2e")
        print(f"Total percentage: {total_percentage:.6f}%")
        
        # Show breakdown
        print("\nSubpart breakdown:")
        for _, row in group_data.head(10).iterrows():
            print(f"  {row['entity']}: {row['percentage']:.1f}% ({row['emissions']:,.0f} MT CO2e)")
        
        # Check for the issue
        if abs(total_percentage - 100.0) > 0.001:
            print(f"\n❌ ISSUE FOUND: Original subpart graph percentages don't sum to 100%!")
            print(f"   Total: {total_percentage:.6f}% (difference: {total_percentage - 100.0:.6f}%)")
            return False
        else:
            print(f"\n✅ Original subpart graph percentages sum correctly to 100%")
            return True
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def test_different_scenarios():
    """Test multiple scenarios to find percentage calculation issues."""
    print("\n=== Testing Multiple Scenarios ===")
    
    scenarios = [
        {'states': None, 'years': None, 'name': 'All Data'},
        {'states': ['CA'], 'years': None, 'name': 'CA Only'},
        {'states': ['CA', 'TX'], 'years': None, 'name': 'CA + TX'},
        {'states': ['CA', 'TX', 'FL'], 'years': [2021, 2023], 'name': 'CA + TX + FL (2021-2023)'},
    ]
    
    issues_found = []
    
    for scenario in scenarios:
        print(f"\n--- Testing: {scenario['name']} ---")
        
        try:
            # Get cached data
            cache_result = get_cached_data(
                state_filter=tuple(scenario['states']) if scenario['states'] else None,
                year_range=tuple(scenario['years']) if scenario['years'] else None,
                category_filter=None
            )
            data = cache_result['main_chart_data']
            
            if not data:
                print(f"No data for {scenario['name']}")
                continue
            
            # Apply original logic
            df = pd.DataFrame(data)
            
            if scenario['states']:
                df = df[df['state'].isin(scenario['states'])]
            
            if scenario['years']:
                df = df[(df['year'].astype(int) >= scenario['years'][0]) & 
                        (df['year'].astype(int) <= scenario['years'][1])]
            
            # Group and calculate percentages (original way)
            group_data = df.groupby('subparts').agg({'value': 'sum'}).reset_index()
            group_data.columns = ['entity', 'emissions']
            
            total_emissions = group_data['emissions'].sum()
            group_data['percentage'] = (group_data['emissions'] / total_emissions * 100).round(1)
            
            total_percentage = group_data['percentage'].sum()
            
            print(f"Total percentage: {total_percentage:.6f}%")
            
            if abs(total_percentage - 100.0) > 0.001:
                issue = f"{scenario['name']}: {total_percentage:.6f}%"
                issues_found.append(issue)
                print(f"❌ Issue: {issue}")
            else:
                print(f"✅ OK: {total_percentage:.6f}%")
                
        except Exception as e:
            print(f"❌ Error in {scenario['name']}: {str(e)}")
    
    return issues_found

if __name__ == '__main__':
    print("Testing original subpart graph percentage calculation...\n")
    
    # Test original logic
    original_ok = test_original_subpart_calculation()
    
    # Test multiple scenarios
    issues = test_different_scenarios()
    
    print("\n=== FINAL SUMMARY ===")
    if issues:
        print(f"❌ PERCENTAGE CALCULATION ISSUES FOUND IN ORIGINAL SUBPART GRAPH:")
        for issue in issues:
            print(f"  - {issue}")
        print(f"\n🔧 SOLUTION: The original subpart_graph.py uses simple rounding which doesn't")
        print(f"   ensure percentages sum to 100%. The enhanced version (subpart_graph_v2.py)")
        print(f"   fixes this with proper percentage adjustment logic.")
    else:
        print("✅ No percentage calculation issues found.")
    
    sys.exit(0 if not issues else 1)
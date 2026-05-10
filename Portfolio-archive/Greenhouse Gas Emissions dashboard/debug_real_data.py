#!/usr/bin/env python3
"""
Debug script to investigate the real Alabama Subpart C hover issue.

This script loads the actual data and analyzes Alabama state data
to reproduce the user's reported issue where Subpart C shows:
- Visual: ~30% (383,334,577 MT out of 1,271,589,596 MT total)
- Hover: 0.3% (incorrect)
"""

import pandas as pd
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.data_preprocessor import DataPreprocessor
from utils.aggregation_v2 import get_subpart_breakdown_data
from components.subpart_graph_v2 import format_enhanced_pie_labels

def debug_alabama_data():
    """Debug the actual Alabama data to find the hover issue."""
    print("🔍 DEBUGGING REAL ALABAMA DATA")
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
        print(f"Columns: {list(df.columns)}")
        
        # Filter for Alabama data
        print("\n🏛️ FILTERING FOR ALABAMA DATA")
        alabama_data = df[df['STATE'] == 'AL'].copy()
        
        if alabama_data.empty:
            print("❌ No Alabama data found")
            return
        
        print(f"✅ Found {len(alabama_data):,} Alabama records")
        
        # Show year range
        years = sorted(alabama_data['REPORTING YEAR'].unique())
        print(f"📅 Years available: {years[0]} - {years[-1]}")
        
        # Show subparts available
        subparts = sorted(alabama_data['SUBPARTS'].unique())
        print(f"📊 Subparts available: {subparts}")
        
        # Calculate total emissions for Alabama (all years)
        total_alabama_emissions = alabama_data['GHG QUANTITY (METRIC TONS CO2e)'].sum()
        print(f"\n💨 TOTAL ALABAMA EMISSIONS (ALL YEARS): {total_alabama_emissions:,} MT CO2e")
        
        # Check Subpart C specifically
        subpart_c_data = alabama_data[alabama_data['SUBPARTS'].str.contains('C', na=False)]
        if not subpart_c_data.empty:
            subpart_c_emissions = subpart_c_data['GHG QUANTITY (METRIC TONS CO2e)'].sum()
            subpart_c_percentage = (subpart_c_emissions / total_alabama_emissions) * 100
            
            print(f"\n🎯 SUBPART C ANALYSIS:")
            print(f"   Records: {len(subpart_c_data):,}")
            print(f"   Total emissions: {subpart_c_emissions:,} MT CO2e")
            print(f"   Percentage: {subpart_c_percentage:.2f}%")
            print(f"   User reported: 383,334,577 MT CO2e (30%)")
            print(f"   Match user report: {abs(subpart_c_emissions - 383334577) < 1000000}")
        
        # Process through the aggregation pipeline
        print("\n⚙️ PROCESSING THROUGH AGGREGATION PIPELINE")
        
        # Test with all years (as user specified)
        filtered_breakdown = get_subpart_breakdown_data(
            alabama_data,
            year_filter=(2010, 2023),  # All years as user specified
            state_filter=['AL']
        )
        
        chart_data = filtered_breakdown['data']
        total_processed = filtered_breakdown.get('total_emissions', 0)
        
        print(f"✅ Processed {len(chart_data)} chart segments")
        print(f"📊 Total processed emissions: {total_processed:,} MT CO2e")
        print(f"🔄 Data preservation: {(total_processed/total_alabama_emissions)*100:.2f}%")
        
        # Analyze each segment
        print("\n📈 CHART SEGMENTS ANALYSIS:")
        for i, segment in enumerate(chart_data):
            subpart = segment['subpart']
            display_name = segment['display_name']
            emissions = segment['emissions']
            our_percentage = segment['percentage']
            
            # Calculate what Plotly would show
            plotly_percentage = (emissions / total_processed) * 100
            
            print(f"\n  {i+1}. {display_name} (Subpart {subpart}):")
            print(f"     Emissions: {emissions:,} MT CO2e")
            print(f"     Our %: {our_percentage:.2f}%")
            print(f"     Plotly %: {plotly_percentage:.2f}%")
            print(f"     Hover shows: {plotly_percentage:.1f}%")
            
            # Check for the critical issue
            if subpart == 'C':
                print(f"\n  🎯 SUBPART C CRITICAL ANALYSIS:")
                print(f"     Expected visual: ~30%")
                print(f"     Actual visual: {our_percentage:.1f}%")
                print(f"     Expected hover: ~30%")
                print(f"     Actual hover: {plotly_percentage:.1f}%")
                
                if plotly_percentage < 1.0 and our_percentage > 15.0:
                    print(f"\n  🚨 CRITICAL BUG FOUND!")
                    print(f"     Visual shows: {our_percentage:.1f}%")
                    print(f"     Hover shows: {plotly_percentage:.1f}%")
                    print(f"     This matches the user's report!")
                    
                    # Investigate the root cause
                    print(f"\n  🔬 ROOT CAUSE INVESTIGATION:")
                    print(f"     Raw emissions in segment: {emissions:,}")
                    print(f"     Total for percentage calc: {total_processed:,}")
                    print(f"     Mathematical result: {(emissions/total_processed)*100:.6f}%")
                    
                    return True  # Bug found
                elif abs(plotly_percentage - our_percentage) > 5.0:
                    print(f"\n  ⚠️  SIGNIFICANT DISCREPANCY:")
                    print(f"     Difference: {abs(plotly_percentage - our_percentage):.1f} percentage points")
        
        print(f"\n✅ Analysis completed. No critical bug reproduced with current data.")
        return False
        
    except Exception as e:
        print(f"❌ Error during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_alabama_data()
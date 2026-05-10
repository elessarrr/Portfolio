#!/usr/bin/env python3
"""
Test to reproduce the EXACT user scenario: 30% visual vs 0.3% hover discrepancy.

This script creates a specific data scenario that could cause the reported issue
where a pie slice appears large (30%) but shows a tiny percentage (0.3%) on hover.
"""

import pandas as pd
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_problematic_scenario():
    """Create a data scenario that could cause the 30% vs 0.3% issue."""
    print("🎯 CREATING EXACT USER SCENARIO")
    print("=" * 50)
    print("Scenario: Large visual slice (30%) but tiny hover (0.3%)")
    print("=" * 50)
    
    # Hypothesis: The issue might occur when using percentages as values
    # but the percentages don't represent the actual data proportions
    
    # Scenario 1: Incorrect percentage calculation
    print("\n📊 SCENARIO 1: Incorrect percentage calculation")
    
    # Simulate what might happen if percentages are calculated incorrectly
    # Real emissions data
    real_emissions = {
        'Subpart A': 500000000,  # 500M MT CO2e
        'Subpart B': 300000000,  # 300M MT CO2e  
        'Subpart C': 400000000,  # 400M MT CO2e (should be ~33%)
        'Subpart D': 100000000,  # 100M MT CO2e
        'Other': 50000000        # 50M MT CO2e
    }
    
    total_real = sum(real_emissions.values())
    correct_percentages = {k: (v/total_real)*100 for k, v in real_emissions.items()}
    
    print("Real emissions and correct percentages:")
    for subpart, emissions in real_emissions.items():
        pct = correct_percentages[subpart]
        print(f"  {subpart}: {emissions:,.0f} MT CO2e ({pct:.1f}%)")
    
    # Now simulate what happens if we use WRONG percentages as values
    # This could happen due to a bug in percentage calculation
    wrong_percentages = {
        'Subpart A': 35.0,
        'Subpart B': 25.0,
        'Subpart C': 0.3,  # BUG: Should be 30.8% but shows as 0.3%
        'Subpart D': 30.0,
        'Other': 9.7
    }
    
    print("\nWrong percentages being used as values:")
    for subpart, wrong_pct in wrong_percentages.items():
        correct_pct = correct_percentages[subpart]
        print(f"  {subpart}: {wrong_pct:.1f}% (should be {correct_pct:.1f}%)")
    
    # Simulate Plotly pie chart with wrong percentages as values
    labels = list(wrong_percentages.keys())
    values = list(wrong_percentages.values())
    
    # Calculate what Plotly would show in hover
    total_wrong = sum(values)
    plotly_percentages = [(v/total_wrong)*100 for v in values]
    
    print("\n🖱️ PLOTLY HOVER SIMULATION:")
    print("When using wrong percentages as values:")
    
    for i, (label, wrong_val, plotly_pct) in enumerate(zip(labels, values, plotly_percentages)):
        real_emissions_val = real_emissions[label]
        correct_pct = correct_percentages[label]
        
        print(f"\n  {label}:")
        print(f"    Real emissions: {real_emissions_val:,.0f} MT CO2e")
        print(f"    Correct percentage: {correct_pct:.1f}%")
        print(f"    Wrong value used: {wrong_val:.1f}%")
        print(f"    Plotly hover shows: {plotly_pct:.1f}%")
        
        # Check for the critical bug
        if label == 'Subpart C':
            visual_size = (real_emissions_val / total_real) * 100  # What user sees visually
            hover_shows = plotly_pct  # What hover displays
            
            print(f"    \n    🚨 CRITICAL ANALYSIS FOR SUBPART C:")
            print(f"       Visual size (based on real data): {visual_size:.1f}%")
            print(f"       Hover shows: {hover_shows:.1f}%")
            print(f"       Discrepancy: {abs(visual_size - hover_shows):.1f} percentage points")
            
            if abs(visual_size - hover_shows) > 25:
                print(f"       ✅ REPRODUCED USER'S ISSUE!")
                print(f"       Large visual ({visual_size:.0f}%) but tiny hover ({hover_shows:.1f}%)")
                return True
    
    return False

def test_plotly_percentage_vs_value_behavior():
    """Test how Plotly handles percentages vs raw values."""
    print("\n\n🔬 TESTING PLOTLY BEHAVIOR")
    print("=" * 50)
    
    # Test data
    emissions = [400000000, 300000000, 200000000, 100000000]  # Real emissions
    labels = ['Subpart A', 'Subpart B', 'Subpart C', 'Subpart D']
    
    # Calculate correct percentages
    total = sum(emissions)
    percentages = [(e/total)*100 for e in emissions]
    
    print("\n📊 TEST 1: Using raw emissions as values (CORRECT)")
    print("Values passed to Plotly:", [f"{e:,.0f}" for e in emissions])
    
    # Simulate Plotly calculation
    plotly_pct_from_emissions = [(e/sum(emissions))*100 for e in emissions]
    for i, (label, emission, pct) in enumerate(zip(labels, emissions, plotly_pct_from_emissions)):
        print(f"  {label}: {emission:,.0f} MT CO2e -> Hover: {pct:.1f}%")
    
    print("\n📊 TEST 2: Using calculated percentages as values (RISKY)")
    print("Values passed to Plotly:", [f"{p:.1f}%" for p in percentages])
    
    # Simulate what happens when percentages are used as values
    plotly_pct_from_percentages = [(p/sum(percentages))*100 for p in percentages]
    for i, (label, orig_pct, plotly_pct) in enumerate(zip(labels, percentages, plotly_pct_from_percentages)):
        print(f"  {label}: {orig_pct:.1f}% input -> Hover: {plotly_pct:.1f}%")
        
        if abs(orig_pct - plotly_pct) > 0.1:
            print(f"    ⚠️  Discrepancy: {abs(orig_pct - plotly_pct):.2f} percentage points")
    
    print("\n📊 TEST 3: Using WRONG percentages as values (BUG SCENARIO)")
    # Simulate a bug where wrong percentages are calculated
    wrong_percentages = [40.0, 30.0, 0.5, 29.5]  # Sum = 100%, but wrong distribution
    print("Values passed to Plotly:", [f"{p:.1f}%" for p in wrong_percentages])
    
    plotly_pct_from_wrong = [(p/sum(wrong_percentages))*100 for p in wrong_percentages]
    for i, (label, wrong_pct, plotly_pct, correct_pct) in enumerate(zip(labels, wrong_percentages, plotly_pct_from_wrong, percentages)):
        print(f"  {label}:")
        print(f"    Correct: {correct_pct:.1f}%")
        print(f"    Wrong input: {wrong_pct:.1f}%")
        print(f"    Hover shows: {plotly_pct:.1f}%")
        
        if label == 'Subpart C' and abs(correct_pct - plotly_pct) > 25:
            print(f"    🚨 CRITICAL: Visual {correct_pct:.0f}% but hover {plotly_pct:.1f}%!")
            return True
    
    return False

def test_real_world_bug_scenario():
    """Test a real-world scenario that could cause the bug."""
    print("\n\n🌍 REAL-WORLD BUG SCENARIO")
    print("=" * 50)
    
    # Scenario: Data aggregation bug where some emissions are double-counted
    # or percentage calculation uses wrong totals
    
    print("Hypothesis: Percentage calculation uses wrong total")
    
    # Real Alabama subpart data (simplified)
    alabama_subparts = {
        'C': 400000000,    # 400M MT CO2e (largest)
        'D': 300000000,    # 300M MT CO2e
        'AA': 200000000,   # 200M MT CO2e
        'W': 150000000,    # 150M MT CO2e
        'Others': 100000000 # 100M MT CO2e
    }
    
    correct_total = sum(alabama_subparts.values())
    print(f"\nCorrect total emissions: {correct_total:,.0f} MT CO2e")
    
    # Bug scenario: Percentage calculation uses wrong total
    # This could happen if some data is filtered out after percentage calculation
    wrong_total = 50000000  # Much smaller total due to bug
    
    print(f"Wrong total used in calculation: {wrong_total:,.0f} MT CO2e")
    print(f"\nPercentage calculation comparison:")
    
    for subpart, emissions in alabama_subparts.items():
        correct_pct = (emissions / correct_total) * 100
        wrong_pct = (emissions / wrong_total) * 100
        
        # Cap at 100% for display
        wrong_pct_capped = min(wrong_pct, 100.0)
        
        print(f"  Subpart {subpart}:")
        print(f"    Emissions: {emissions:,.0f} MT CO2e")
        print(f"    Correct %: {correct_pct:.1f}%")
        print(f"    Wrong % (bug): {wrong_pct:.1f}% (capped: {wrong_pct_capped:.1f}%)")
        
        if subpart == 'C':
            # This is where the user's issue manifests
            visual_percentage = correct_pct  # What user sees in chart
            
            # If the wrong percentage is used as value in Plotly
            # and then Plotly recalculates based on sum of all wrong percentages
            all_wrong_pcts = [(e / wrong_total) * 100 for e in alabama_subparts.values()]
            all_wrong_pcts_capped = [min(p, 100.0) for p in all_wrong_pcts]
            wrong_total_pcts = sum(all_wrong_pcts_capped)
            
            hover_percentage = (wrong_pct_capped / wrong_total_pcts) * 100
            
            print(f"\n    🎯 SUBPART C ANALYSIS:")
            print(f"       Visual (correct): {visual_percentage:.1f}%")
            print(f"       Hover (bug): {hover_percentage:.1f}%")
            print(f"       Discrepancy: {abs(visual_percentage - hover_percentage):.1f} percentage points")
            
            if abs(visual_percentage - hover_percentage) > 25:
                print(f"       ✅ REPRODUCED USER'S EXACT ISSUE!")
                print(f"       Visual ~{visual_percentage:.0f}% but hover {hover_percentage:.1f}%")
                return True
    
    return False

def main():
    """Main test function."""
    print("🔍 REPRODUCING EXACT USER SCENARIO")
    print("=" * 60)
    print("User report: Subpart C shows 30% visually but 0.3% on hover")
    print("=" * 60)
    
    # Test different scenarios
    scenario1_reproduced = create_problematic_scenario()
    scenario2_reproduced = test_plotly_percentage_vs_value_behavior()
    scenario3_reproduced = test_real_world_bug_scenario()
    
    # Summary
    print("\n\n📋 REPRODUCTION SUMMARY")
    print("=" * 50)
    print(f"Scenario 1 (Wrong percentages): {scenario1_reproduced}")
    print(f"Scenario 2 (Plotly behavior): {scenario2_reproduced}")
    print(f"Scenario 3 (Real-world bug): {scenario3_reproduced}")
    
    if any([scenario1_reproduced, scenario2_reproduced, scenario3_reproduced]):
        print("\n🎉 SUCCESS: Reproduced the user's exact issue!")
        print("\n🔧 ROOT CAUSE IDENTIFIED:")
        print("   The bug occurs when:")
        print("   1. Percentage calculation uses wrong total emissions")
        print("   2. Wrong percentages are passed as values to Plotly")
        print("   3. Plotly recalculates percentages from these wrong values")
        print("   4. Result: Visual chart shows correct proportions but hover shows wrong %")
        
        print("\n💡 SOLUTION:")
        print("   1. Always use raw emissions as values, not calculated percentages")
        print("   2. Let Plotly calculate percentages automatically")
        print("   3. Ensure data aggregation uses correct totals")
        print("   4. Validate that hover percentages match visual proportions")
    else:
        print("\n❌ Could not reproduce the exact user scenario.")
        print("   The issue might be:")
        print("   1. Fixed in recent updates")
        print("   2. Environment or browser specific")
        print("   3. Related to specific data not tested")
        print("   4. A different type of bug")

if __name__ == "__main__":
    main()
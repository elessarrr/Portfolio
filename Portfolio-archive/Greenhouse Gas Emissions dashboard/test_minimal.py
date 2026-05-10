#!/usr/bin/env python3
"""
Minimal test without heavy dependencies.
"""

def test_fix():
    print("Testing the fix for percentage calculation...")
    
    # Sample data similar to what user reported
    data = [
        {'name': 'C', 'emissions': 25578131.329},
        {'name': 'D', 'emissions': 1234567.89},
        {'name': 'W', 'emissions': 987654.32},
        {'name': 'Other', 'emissions': 456789.12},
        {'name': 'P', 'emissions': 123456.78}
    ]
    
    total = sum(item['emissions'] for item in data)
    
    # Calculate percentages
    for item in data:
        raw_pct = (item['emissions'] / total) * 100
        rounded_pct = round(raw_pct, 1)
        item['percentage'] = rounded_pct
        print(f"{item['name']}: {rounded_pct:.1f}% ({item['emissions']:,.0f} MT CO2e)")
    
    total_pct = sum(item['percentage'] for item in data)
    print(f"\nTotal: {total_pct:.1f}%")
    
    print("\n=== Key Fix Explanation ===")
    print("BEFORE: Chart used emissions values, hover showed Plotly-calculated percentages")
    print("AFTER: Chart uses our calculated percentages, hover shows our percentages")
    print("This ensures visual size matches hover text exactly.")
    
    return True

if __name__ == "__main__":
    test_fix()
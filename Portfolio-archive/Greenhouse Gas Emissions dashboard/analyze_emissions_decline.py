#!/usr/bin/env python3
"""
Analyze total emissions decline over the 14-year period.

This script loads the emissions data and calculates the total decline
in greenhouse gas emissions from the earliest to latest year in the dataset.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def analyze_emissions_decline():
    """
    Analyze the decline in total emissions over the available years.
    
    Returns:
        dict: Analysis results including total decline, percentage change, etc.
    """
    # Load the emissions data
    data_path = Path('data/emissions_data.parquet')
    
    if not data_path.exists():
        print(f"❌ Data file not found: {data_path}")
        return None
    
    print("📊 Loading emissions data...")
    df = pd.read_parquet(data_path)
    
    # Display basic info about the dataset
    print(f"\n📋 Dataset Info:")
    print(f"   Total records: {len(df):,}")
    print(f"   Columns: {list(df.columns)}")
    
    # Check the year range
    years = df['REPORTING YEAR'].unique()
    years_sorted = sorted(years)
    print(f"\n📅 Year Range:")
    print(f"   Years available: {years_sorted}")
    print(f"   Total years: {len(years_sorted)}")
    print(f"   From {min(years_sorted)} to {max(years_sorted)}")
    
    # Calculate total emissions by year
    print("\n🔢 Calculating total emissions by year...")
    yearly_totals = df.groupby('REPORTING YEAR')['GHG QUANTITY (METRIC TONS CO2e)'].sum().sort_index()
    
    print("\n📈 Yearly Total Emissions (Metric Tons CO2e):")
    for year, total in yearly_totals.items():
        print(f"   {year}: {total:,.0f}")
    
    # Calculate decline metrics
    first_year = min(years_sorted)
    last_year = max(years_sorted)
    first_year_emissions = yearly_totals[first_year]
    last_year_emissions = yearly_totals[last_year]
    
    total_decline = first_year_emissions - last_year_emissions
    percentage_decline = (total_decline / first_year_emissions) * 100
    years_span = last_year - first_year
    annual_average_decline = total_decline / years_span if years_span > 0 else 0
    annual_percentage_decline = percentage_decline / years_span if years_span > 0 else 0
    
    print("\n📉 Emissions Decline Analysis:")
    print(f"   Period: {first_year} to {last_year} ({years_span} years)")
    print(f"   {first_year} emissions: {first_year_emissions:,.0f} metric tons CO2e")
    print(f"   {last_year} emissions: {last_year_emissions:,.0f} metric tons CO2e")
    print(f"   Total decline: {total_decline:,.0f} metric tons CO2e")
    print(f"   Percentage decline: {percentage_decline:.1f}%")
    print(f"   Average annual decline: {annual_average_decline:,.0f} metric tons CO2e")
    print(f"   Average annual percentage decline: {annual_percentage_decline:.1f}%")
    
    # Find peak and lowest years
    peak_year = yearly_totals.idxmax()
    peak_emissions = yearly_totals.max()
    lowest_year = yearly_totals.idxmin()
    lowest_emissions = yearly_totals.min()
    
    print(f"\n🔝 Peak and Lowest Emissions:")
    print(f"   Peak year: {peak_year} with {peak_emissions:,.0f} metric tons CO2e")
    print(f"   Lowest year: {lowest_year} with {lowest_emissions:,.0f} metric tons CO2e")
    
    # Calculate year-over-year changes
    print("\n📊 Year-over-Year Changes:")
    for i in range(1, len(yearly_totals)):
        prev_year = yearly_totals.index[i-1]
        curr_year = yearly_totals.index[i]
        prev_emissions = yearly_totals.iloc[i-1]
        curr_emissions = yearly_totals.iloc[i]
        change = curr_emissions - prev_emissions
        pct_change = (change / prev_emissions) * 100
        direction = "📈" if change > 0 else "📉" if change < 0 else "➡️"
        print(f"   {prev_year} → {curr_year}: {change:+,.0f} ({pct_change:+.1f}%) {direction}")
    
    return {
        'first_year': first_year,
        'last_year': last_year,
        'years_span': years_span,
        'first_year_emissions': first_year_emissions,
        'last_year_emissions': last_year_emissions,
        'total_decline': total_decline,
        'percentage_decline': percentage_decline,
        'annual_average_decline': annual_average_decline,
        'annual_percentage_decline': annual_percentage_decline,
        'peak_year': peak_year,
        'peak_emissions': peak_emissions,
        'lowest_year': lowest_year,
        'lowest_emissions': lowest_emissions,
        'yearly_totals': yearly_totals
    }

if __name__ == "__main__":
    print("🌍 GHG Emissions Decline Analysis")
    print("=" * 50)
    
    results = analyze_emissions_decline()
    
    if results:
        print("\n✅ Analysis completed successfully!")
    else:
        print("\n❌ Analysis failed!")
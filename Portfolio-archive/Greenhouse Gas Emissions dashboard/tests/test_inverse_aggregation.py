import sys
import os
import pandas as pd
import pytest
from typing import List, Dict, Any

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.inverse_aggregation import get_subpart_timeline_data, get_state_breakdown_data

@pytest.fixture
def sample_emissions_data():
    """Provides a sample DataFrame for testing inverse aggregation functions."""
    data = {
        'REPORTING YEAR': [2020, 2020, 2021, 2021, 2022, 2022],
        'STATE': ['CA', 'TX', 'CA', 'NY', 'TX', 'FL'],
        'SUBPARTS': ['C', 'D', 'C', 'AA', 'D', 'C'],  # Changed to SUBPARTS (plural)
        'GHG QUANTITY (METRIC TONS CO2e)': [1000, 2000, 1500, 800, 2500, 1200]
    }
    return pd.DataFrame(data)

class TestGetSubpartTimelineData:
    """Test cases for get_subpart_timeline_data function."""
    
    def test_basic_aggregation(self, sample_emissions_data):
        """Test basic subpart timeline aggregation."""
        result = get_subpart_timeline_data(
            df=sample_emissions_data,
            year_filter=(2020, 2022),
            subpart_filter=None,
            state_filter=None
        )
        
        # Check that result is a DataFrame
        assert isinstance(result, pd.DataFrame)
        
        # Check required columns exist
        required_columns = ['subpart', 'year', 'value', 'display_name']
        for col in required_columns:
            assert col in result.columns, f"Missing column: {col}"
        
        # Check data integrity
        assert len(result) > 0, "Result should not be empty"
        assert result['value'].sum() > 0, "Total emissions should be positive"
    
    def test_year_filtering(self, sample_emissions_data):
        """Test that year filtering works correctly."""
        result = get_subpart_timeline_data(
            df=sample_emissions_data,
            year_filter=(2021, 2021),  # Only 2021
            subpart_filter=None,
            state_filter=None
        )
        
        # Should only have 2021 data
        unique_years = result['year'].unique()
        assert len(unique_years) == 1
        assert unique_years[0] == 2021
    
    def test_state_filtering(self, sample_emissions_data):
        """Test that state filtering works correctly."""
        result = get_subpart_timeline_data(
            df=sample_emissions_data,
            year_filter=(2020, 2022),
            subpart_filter=None,
            state_filter=['CA', 'TX']  # Only CA and TX
        )
        
        # Verify only CA and TX data is included
        # Check by verifying expected emissions values
        ca_tx_total = sample_emissions_data[
            sample_emissions_data['STATE'].isin(['CA', 'TX'])
        ]['GHG QUANTITY (METRIC TONS CO2e)'].sum()
        
        result_total = result['value'].sum()
        assert result_total == ca_tx_total
    
    def test_subpart_filtering(self, sample_emissions_data):
        """Test that subpart filtering works correctly."""
        result = get_subpart_timeline_data(
            df=sample_emissions_data,
            year_filter=(2020, 2022),
            subpart_filter=['C', 'D'],  # Only C and D
            state_filter=None
        )
        
        # Should only have C and D subparts
        unique_subparts = result['subpart'].unique()
        assert set(unique_subparts).issubset({'C', 'D'})
    
    def test_empty_data(self):
        """Test handling of empty DataFrame."""
        empty_df = pd.DataFrame(columns=['REPORTING YEAR', 'STATE', 'SUBPART', 'GHG QUANTITY (METRIC TONS CO2e)'])
        
        result = get_subpart_timeline_data(
            df=empty_df,
            year_filter=(2020, 2022),
            subpart_filter=None,
            state_filter=None
        )
        
        # Should return empty DataFrame with correct structure
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0
        required_columns = ['subpart', 'year', 'value', 'display_name']
        for col in required_columns:
            assert col in result.columns

class TestGetStateBreakdownData:
    """Test cases for get_state_breakdown_data function."""
    
    def test_basic_breakdown(self, sample_emissions_data):
        """Test basic state breakdown functionality."""
        result = get_state_breakdown_data(
            df=sample_emissions_data,
            year_filter=(2020, 2022),
            subpart_filter=['C', 'D'],
            state_filter=None
        )
        
        # Should return a dictionary with expected keys
        assert isinstance(result, dict)
        expected_keys = ['data', 'total_emissions', 'subpart_count']
        assert all(key in result for key in expected_keys)
        
        # Should have data for all states
        assert len(result['data']) == 3
        
        # Check that percentages sum to approximately 100%
        total_percentage = sum(item['percentage'] for item in result['data'])
        assert abs(total_percentage - 100.0) < 0.01
        
        # Check total emissions (C: 1000+1500+1200=3700, D: 2000+2500=4500, total=8200)
        assert result['total_emissions'] == 8200
        assert result['subpart_count'] == 2
    
    def test_percentage_calculation(self, sample_emissions_data):
        """Test that percentages are calculated correctly."""
        result = get_state_breakdown_data(
            df=sample_emissions_data,
            year_filter=(2020, 2022),
            subpart_filter=['C', 'D'],
            state_filter=None
        )
        
        # Check that percentages sum to 100%
        total_percentage = sum(item['percentage'] for item in result['data'])
        assert abs(total_percentage - 100.0) < 0.01
        
        # Check individual percentages are reasonable
        for item in result['data']:
            assert 0 <= item['percentage'] <= 100
    
    def test_emissions_accuracy(self, sample_emissions_data):
        """Test that emissions values are accurate."""
        result = get_state_breakdown_data(
            sample_emissions_data,
            year_filter=(2020, 2022),
            subpart_filter=['C']
        )
        
        # Check total emissions match expected
        total_emissions = result['total_emissions']
        expected_total = sample_emissions_data[
            sample_emissions_data['SUBPARTS'].str.contains('C', na=False)
        ]['GHG QUANTITY (METRIC TONS CO2e)'].sum()
        
        assert abs(total_emissions - expected_total) < 0.01
    
    def test_state_filtering(self, sample_emissions_data):
        """Test that state filtering works in breakdown."""
        result = get_state_breakdown_data(
            df=sample_emissions_data,
            year_filter=(2020, 2022),
            subpart_filter=['C', 'D'],
            state_filter=['CA', 'TX']  # Only CA and TX
        )
        
        # Should only have CA and TX (if they have data for selected subparts)
        states_in_result = {item['state'] for item in result['data']}
        expected_states = {'CA', 'TX'}
        assert states_in_result.issubset(expected_states)
    
    def test_year_filtering(self, sample_emissions_data):
        """Test year filtering functionality."""
        # Test with limited year range
        result_2020 = get_state_breakdown_data(
            sample_emissions_data,
            year_filter=(2020, 2020),
            subpart_filter=['C', 'D']
        )
        
        result_all_years = get_state_breakdown_data(
            sample_emissions_data,
            year_filter=(2020, 2022),
            subpart_filter=['C', 'D']
        )
        
        # 2020 only should have less or equal emissions than all years
        assert result_2020['total_emissions'] <= result_all_years['total_emissions']
    
    def test_empty_subpart_filter(self, sample_emissions_data):
        """Test handling of empty subpart filter."""
        result = get_state_breakdown_data(
            sample_emissions_data,
            year_filter=(2020, 2022),
            subpart_filter=[]
        )
        
        # Should return empty result when subpart_filter is empty
        assert len(result['data']) == 0
        assert result['total_emissions'] == 0
        assert result['subpart_count'] == 0
    
    def test_nonexistent_subpart(self, sample_emissions_data):
        """Test handling of non-existent subpart."""
        result = get_state_breakdown_data(
            df=sample_emissions_data,
            year_filter=(2020, 2022),
            subpart_filter=['NONEXISTENT'],  # Non-existent subpart
            state_filter=None
        )
        
        # Should return empty breakdown
        assert len(result['data']) == 0
        assert result['total_emissions'] == 0
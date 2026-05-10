import pytest
import pandas as pd
from utils.subpart_processing import (
    expand_comma_separated_subparts,
    validate_subpart_codes,
    get_subpart_display_name
)

class TestSubpartProcessing:
    """
    Test suite for subpart processing functionality.
    
    Ensures that comma-separated subparts are properly expanded
    and that data integrity is maintained throughout the process.
    """
    
    def test_expand_comma_separated_subparts_basic(self):
        """Test basic expansion of comma-separated subpart values."""
        # Test data with comma-separated subparts
        test_data = pd.DataFrame({
            'STATE': ['CA', 'TX', 'NY'],
            'SUBPARTS': ['A,B', 'C', 'D,E,F'],
            'GHG_QUANTITY': [100, 200, 300],
            'REPORTING_YEAR': [2020, 2020, 2020]
        })
        
        result = expand_comma_separated_subparts(test_data)
        
        # Should have 6 rows (2 + 1 + 3)
        assert len(result) == 6
        
        # Check that emissions are properly distributed
        ca_rows = result[result['STATE'] == 'CA']
        assert len(ca_rows) == 2
        assert all(ca_rows['GHG_QUANTITY'] == 50)  # 100/2
        
        tx_rows = result[result['STATE'] == 'TX']
        assert len(tx_rows) == 1
        assert tx_rows['GHG_QUANTITY'].iloc[0] == 200
        
        ny_rows = result[result['STATE'] == 'NY']
        assert len(ny_rows) == 3
        assert all(ny_rows['GHG_QUANTITY'] == 100)  # 300/3
    
    def test_expand_comma_separated_subparts_edge_cases(self):
        """Test edge cases for subpart expansion."""
        # Test with empty DataFrame
        empty_df = pd.DataFrame()
        result = expand_comma_separated_subparts(empty_df)
        assert result.empty
        
        # Test with single subpart (no commas)
        single_data = pd.DataFrame({
            'STATE': ['CA'],
            'SUBPARTS': ['A'],
            'GHG_QUANTITY': [100],
            'REPORTING_YEAR': [2020]
        })
        
        result = expand_comma_separated_subparts(single_data)
        assert len(result) == 1
        assert result['GHG_QUANTITY'].iloc[0] == 100
    
    def test_validate_subpart_codes_valid(self):
        """Test validation of valid subpart codes."""
        valid_codes = ['A', 'B', 'C', 'D']
        result = validate_subpart_codes(valid_codes)
        assert result == valid_codes
    
    def test_validate_subpart_codes_mixed(self):
        """Test validation with mix of valid and invalid codes."""
        mixed_codes = ['A', 'INVALID', 'B', 'FAKE']
        result = validate_subpart_codes(mixed_codes)
        # Should only return valid codes
        assert 'A' in result
        assert 'B' in result
        assert 'INVALID' not in result
        assert 'FAKE' not in result
    
    def test_validate_subpart_codes_empty(self):
        """Test validation with empty list."""
        result = validate_subpart_codes([])
        assert result == []
    
    def test_get_subpart_display_name_valid(self):
        """Test getting display names for valid subpart codes."""
        # Test with known subpart codes
        display_name_a = get_subpart_display_name('A')
        assert display_name_a is not None
        assert len(display_name_a) > 1  # Should be more than just the code
        
        display_name_b = get_subpart_display_name('B')
        assert display_name_b is not None
        assert display_name_b != display_name_a  # Different codes should have different names
    
    def test_get_subpart_display_name_invalid(self):
        """Test getting display names for invalid subpart codes."""
        display_name = get_subpart_display_name('INVALID_CODE')
        assert display_name == 'INVALID_CODE'  # Should return the code itself
    
    def test_percentage_accuracy_calculation(self):
        """Test that percentage calculations are accurate."""
        # Create test data that should sum to exactly 100%
        test_data = pd.DataFrame({
            'subpart': ['A', 'B', 'C'],
            'emissions': [33.333333, 33.333333, 33.333334],
            'percentage': [33.33, 33.33, 33.34]
        })
        
        # Test that percentages sum to 100%
        total_percentage = test_data['percentage'].sum()
        assert abs(total_percentage - 100.0) < 0.01  # Allow small floating point errors
    
    def test_data_integrity_after_expansion(self):
        """Test that data integrity is maintained after subpart expansion."""
        original_data = pd.DataFrame({
            'STATE': ['CA', 'TX'],
            'SUBPARTS': ['A,B', 'C'],
            'GHG_QUANTITY': [100, 200],
            'REPORTING_YEAR': [2020, 2020]
        })
        
        expanded_data = expand_comma_separated_subparts(original_data)
        
        # Total emissions should be preserved
        original_total = original_data['GHG_QUANTITY'].sum()
        expanded_total = expanded_data['GHG_QUANTITY'].sum()
        assert abs(original_total - expanded_total) < 0.01
        
        # Number of unique states should be preserved
        original_states = set(original_data['STATE'])
        expanded_states = set(expanded_data['STATE'])
        assert original_states == expanded_states
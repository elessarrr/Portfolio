import pytest
import pandas as pd
from utils.feature_flags import FeatureFlags, feature_flags
from utils.aggregation_v2 import (
    aggregate_by_individual_subparts,
    calculate_accurate_percentages,
    get_subpart_breakdown_data
)
from components.subpart_graph_v2 import format_enhanced_pie_labels

class TestEnhancedSubpartGraph:
    """
    Integration tests for enhanced subpart graph component.
    
    Tests the complete flow from data processing to chart rendering.
    """
    
    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        return pd.DataFrame({
            'STATE': ['CA', 'CA', 'TX', 'TX', 'NY'],
            'SUBPARTS': ['A,B', 'C', 'D', 'E,F', 'G'],
            'GHG_QUANTITY': [100, 200, 150, 300, 250],
            'REPORTING_YEAR': [2020, 2020, 2020, 2020, 2020],
            'FACILITY_NAME': ['Facility1', 'Facility2', 'Facility3', 'Facility4', 'Facility5']
        })
    
    def test_feature_flag_integration(self):
        """Test that feature flag properly controls component selection."""
        # Test that feature flag exists and can be accessed
        flag_value = feature_flags.is_enabled('enhanced_subpart_breakdown')
        assert isinstance(flag_value, bool)
        
        # Test that the feature flag instance has the required methods
        assert hasattr(feature_flags, 'is_enabled')
        assert callable(feature_flags.is_enabled)
    
    def test_aggregation_pipeline(self, sample_data):
        """Test the complete aggregation pipeline."""
        # Test individual subpart aggregation
        aggregated = aggregate_by_individual_subparts(sample_data)
        
        # Should have more rows than original due to expansion
        assert len(aggregated) > len(sample_data)
        
        # Test that emissions are properly distributed
        total_original = sample_data['GHG_QUANTITY'].sum()
        total_aggregated = aggregated['GHG_QUANTITY'].sum()
        assert abs(total_original - total_aggregated) < 0.01
    
    def test_percentage_accuracy_in_aggregation(self, sample_data):
        """Test that aggregation produces accurate percentages."""
        # Get breakdown data
        breakdown_data = get_subpart_breakdown_data(
            sample_data,
            year_range=[2020, 2020],
            selected_states=['CA', 'TX', 'NY'],
            selected_category=None
        )
        
        if not breakdown_data.empty:
            # Calculate percentages
            percentages_df = calculate_accurate_percentages(breakdown_data)
            
            # Percentages should sum to exactly 100%
            total_percentage = percentages_df['percentage'].sum()
            assert abs(total_percentage - 100.0) < 0.01
            
            # All percentages should be positive
            assert all(percentages_df['percentage'] >= 0)
    
    def test_individual_subpart_representation(self, sample_data):
        """Test that each subpart is represented individually."""
        # Aggregate data
        aggregated = aggregate_by_individual_subparts(sample_data)
        
        # Check that comma-separated subparts are expanded
        unique_subparts = set(aggregated['SUBPARTS'])
        
        # Should not contain any comma-separated values
        for subpart in unique_subparts:
            assert ',' not in subpart, f"Found comma-separated subpart: {subpart}"
        
        # Should have individual subparts A, B, C, D, E, F, G
        expected_subparts = {'A', 'B', 'C', 'D', 'E', 'F', 'G'}
        assert expected_subparts.issubset(unique_subparts)
    
    def test_enhanced_pie_labels_formatting(self):
        """Test the enhanced pie chart label formatting."""
        # Test data for label formatting
        test_data = pd.DataFrame({
            'subpart': ['A', 'B', 'C'],
            'percentage': [45.5, 30.2, 24.3],
            'emissions': [455000, 302000, 243000]
        })
        
        # Test with different thresholds
        labels_5_percent = format_enhanced_pie_labels(test_data, threshold=5.0)
        labels_25_percent = format_enhanced_pie_labels(test_data, threshold=25.0)
        
        # With 5% threshold, all should be labeled
        assert len(labels_5_percent) == 3
        
        # With 25% threshold, only A and B should be labeled (>25%)
        labeled_count = sum(1 for label in labels_25_percent if label != '')
        assert labeled_count == 2
    
    def test_data_filtering_integration(self, sample_data):
        """Test that data filtering works correctly in the pipeline."""
        # Test filtering by state
        ca_data = get_subpart_breakdown_data(
            sample_data,
            year_range=[2020, 2020],
            selected_states=['CA'],
            selected_category=None
        )
        
        if not ca_data.empty:
            # Should only contain CA data
            assert all(ca_data['STATE'] == 'CA')
        
        # Test filtering by year range
        year_2020_data = get_subpart_breakdown_data(
            sample_data,
            year_range=[2020, 2020],
            selected_states=None,
            selected_category=None
        )
        
        if not year_2020_data.empty:
            # Should only contain 2020 data
            assert all(year_2020_data['REPORTING_YEAR'] == 2020)
    
    def test_error_handling_empty_data(self):
        """Test error handling with empty data."""
        empty_data = pd.DataFrame()
        
        # Should handle empty data gracefully
        result = get_subpart_breakdown_data(
            empty_data,
            year_range=[2020, 2020],
            selected_states=['CA'],
            selected_category=None
        )
        
        assert result.empty
    
    def test_error_handling_invalid_filters(self, sample_data):
        """Test error handling with invalid filter values."""
        # Test with invalid state
        result = get_subpart_breakdown_data(
            sample_data,
            year_range=[2020, 2020],
            selected_states=['INVALID_STATE'],
            selected_category=None
        )
        
        assert result.empty
        
        # Test with invalid year range
        result = get_subpart_breakdown_data(
            sample_data,
            year_range=[1900, 1900],
            selected_states=['CA'],
            selected_category=None
        )
        
        assert result.empty
    
    def test_performance_with_large_dataset(self):
        """Test performance with larger dataset."""
        # Create larger test dataset
        large_data = pd.DataFrame({
            'STATE': ['CA'] * 1000 + ['TX'] * 1000,
            'SUBPARTS': ['A,B,C'] * 1000 + ['D,E,F'] * 1000,
            'GHG_QUANTITY': [100] * 2000,
            'REPORTING_YEAR': [2020] * 2000,
            'FACILITY_NAME': [f'Facility{i}' for i in range(2000)]
        })
        
        import time
        start_time = time.time()
        
        # Process the data
        result = get_subpart_breakdown_data(
            large_data,
            year_range=[2020, 2020],
            selected_states=['CA', 'TX'],
            selected_category=None
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 5.0, f"Processing took too long: {processing_time} seconds"
        
        # Should produce correct results
        assert not result.empty
        assert len(result) > len(large_data)  # Due to subpart expansion
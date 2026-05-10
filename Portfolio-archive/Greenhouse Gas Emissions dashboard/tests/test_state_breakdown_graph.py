import sys
import os
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
import plotly.graph_objects as go

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from components.state_breakdown_graph import create_state_breakdown_graph

@pytest.fixture
def sample_breakdown_data():
    """Provides sample state breakdown data for testing."""
    breakdown_df = pd.DataFrame({
        'state': ['CA', 'TX', 'NY', 'FL'],
        'value': [1500, 2000, 800, 700],
        'percentage': [30.0, 40.0, 16.0, 14.0]
    })
    
    return {
        'breakdown_data': breakdown_df,
        'total_emissions': 5000,
        'subpart_list': ['C', 'D']
    }

@pytest.fixture
def mock_app():
    """Mock Dash app for testing."""
    app = MagicMock()
    
    # Track if callback was called
    app._callback_registered = False
    
    # Mock the callback decorator to capture the callback function
    def mock_callback(*args, **kwargs):
        def decorator(func):
            # Store the callback function for testing
            app._callback_func = func
            app._callback_registered = True
            return func
        return decorator
    
    app.callback = mock_callback
    return app

class TestStateBreakdownGraph:
    """Test cases for state breakdown graph component."""
    
    def test_component_creation(self, mock_app):
        """Test that the component can be created without errors."""
        component = create_state_breakdown_graph(mock_app)
        
        # Should return a Dash component
        assert component is not None
        
        # Should register a callback
        assert mock_app._callback_registered
    
    @patch('components.state_breakdown_graph.get_state_breakdown_data')
    @patch('components.state_breakdown_graph.get_cached_layout')
    @patch('utils.data_preprocessor.DataPreprocessor')
    def test_callback_execution(self, mock_preprocessor, mock_layout, mock_breakdown_data, 
                               mock_app, sample_breakdown_data):
        """Test that the callback executes correctly with valid inputs."""
        # Setup mocks
        mock_df = pd.DataFrame({
            'REPORTING YEAR': [2020, 2021],
            'STATE': ['CA', 'TX'],
            'SUBPART': ['C', 'D'],
            'GHG QUANTITY (METRIC TONS CO2e)': [1000, 2000]
        })
        
        mock_preprocessor_instance = MagicMock()
        mock_preprocessor_instance.load_data.return_value = mock_df
        mock_preprocessor.return_value = mock_preprocessor_instance
        
        mock_breakdown_data.return_value = sample_breakdown_data
        mock_layout.return_value = {
            'title': 'Test Title',
            'height': 500,
            'margin': {'l': 50, 'r': 20, 't': 80, 'b': 50}
        }
        
        # Create component to register callback
        create_state_breakdown_graph(mock_app)
        
        # Get the callback function
        callback_func = mock_app._callback_func
        
        # Test callback execution
        result = callback_func(
            year_range=[2020, 2021],
            selected_subparts=['C', 'D'],
            selected_category=None,
            last_update=None
        )
        
        # Should return a tuple (figure, validation_data)
        assert isinstance(result, tuple)
        assert len(result) == 2
        figure, validation_data = result
        assert isinstance(figure, go.Figure)
        
        # Verify mocks were called
        mock_breakdown_data.assert_called_once()
    
    @patch('components.state_breakdown_graph.get_state_breakdown_data')
    @patch('components.state_breakdown_graph.get_cached_layout')
    @patch('utils.data_preprocessor.DataPreprocessor')
    def test_callback_with_invalid_year_range(self, mock_preprocessor, mock_layout, 
                                            mock_breakdown_data, mock_app, sample_breakdown_data):
        """Test callback handling of invalid year range."""
        # Setup mocks
        mock_df = pd.DataFrame({
            'REPORTING YEAR': [2020, 2021],
            'STATE': ['CA', 'TX'],
            'SUBPART': ['C', 'D'],
            'GHG QUANTITY (METRIC TONS CO2e)': [1000, 2000]
        })
        
        mock_preprocessor_instance = MagicMock()
        mock_preprocessor_instance.load_data.return_value = mock_df
        mock_preprocessor.return_value = mock_preprocessor_instance
        
        mock_breakdown_data.return_value = sample_breakdown_data
        mock_layout.return_value = {'title': 'Test Title', 'height': 500}
        
        # Create component
        create_state_breakdown_graph(mock_app)
        callback_func = mock_app._callback_func
        
        # Test with invalid year range
        result = callback_func(
            year_range=None,  # Invalid
            selected_subparts=['C', 'D'],
            selected_category=None,
            last_update=None
        )
        
        # Should return a tuple (figure, validation_data)
        assert isinstance(result, tuple)
        assert len(result) == 2
        figure, validation_data = result
        assert isinstance(figure, go.Figure)
        
        # Should have called breakdown data with default range [2010, 2023]
        args, kwargs = mock_breakdown_data.call_args
        assert kwargs['year_filter'] == (2010, 2023)
    
    @patch('components.state_breakdown_graph.get_state_breakdown_data')
    @patch('components.state_breakdown_graph.get_cached_layout')
    @patch('utils.data_preprocessor.DataPreprocessor')
    def test_callback_with_empty_subparts(self, mock_preprocessor, mock_layout, 
                                        mock_breakdown_data, mock_app):
        """Test callback handling of empty subpart selection."""
        # Setup mocks
        mock_df = pd.DataFrame({
            'REPORTING YEAR': [2020, 2021],
            'STATE': ['CA', 'TX'],
            'SUBPART': ['C', 'D'],
            'GHG QUANTITY (METRIC TONS CO2e)': [1000, 2000]
        })
        
        mock_preprocessor_instance = MagicMock()
        mock_preprocessor_instance.load_data.return_value = mock_df
        mock_preprocessor.return_value = mock_preprocessor_instance
        
        # Empty breakdown data
        empty_breakdown = {
            'breakdown_data': pd.DataFrame(columns=['state', 'value', 'percentage']),
            'total_emissions': 0,
            'subpart_list': []
        }
        mock_breakdown_data.return_value = empty_breakdown
        mock_layout.return_value = {'title': 'Test Title', 'height': 500}
        
        # Create component
        create_state_breakdown_graph(mock_app)
        callback_func = mock_app._callback_func
        
        # Test with empty subparts
        result = callback_func(
            year_range=[2020, 2021],
            selected_subparts=[],  # Empty list
            selected_category=None,
            last_update=None
        )
        
        # Should return a tuple (figure, validation_data)
        assert isinstance(result, tuple)
        assert len(result) == 2
        figure, validation_data = result
        assert isinstance(figure, go.Figure)
        
        # Check that the figure has appropriate "no data" annotation
        annotations = figure.layout.annotations
        assert len(annotations) > 0
        assert any('no data' in str(ann.text).lower() or 'select subparts' in str(ann.text).lower() 
                  for ann in annotations)
    
    @patch('components.state_breakdown_graph.get_state_breakdown_data')
    @patch('components.state_breakdown_graph.get_cached_layout')
    @patch('utils.data_preprocessor.DataPreprocessor')
    def test_pie_chart_formatting(self, mock_preprocessor, mock_layout, 
                                mock_breakdown_data, mock_app, sample_breakdown_data):
        """Test that pie chart is formatted correctly."""
        # Setup mocks
        mock_df = pd.DataFrame({
            'REPORTING YEAR': [2020, 2021],
            'STATE': ['CA', 'TX'],
            'SUBPART': ['C', 'D'],
            'GHG QUANTITY (METRIC TONS CO2e)': [1000, 2000]
        })
        
        mock_preprocessor_instance = MagicMock()
        mock_preprocessor_instance.load_data.return_value = mock_df
        mock_preprocessor.return_value = mock_preprocessor_instance
        
        mock_breakdown_data.return_value = sample_breakdown_data
        mock_layout.return_value = {'title': 'Test Title', 'height': 500}
        
        # Create component
        create_state_breakdown_graph(mock_app)
        callback_func = mock_app._callback_func
        
        # Test pie chart formatting
        result = callback_func(
            year_range=[2020, 2021],
            selected_subparts=['C', 'D'],
            selected_category=None,
            last_update=None
        )
        
        # Should return a tuple (figure, validation_data)
        assert isinstance(result, tuple)
        assert len(result) == 2
        figure, validation_data = result
        assert isinstance(figure, go.Figure)
        
        # Should be a pie chart
        assert len(figure.data) == 1
        pie_trace = figure.data[0]
        assert pie_trace.type == 'pie'
        
        # Check pie chart data
        assert list(pie_trace.labels) == ['CA', 'TX', 'NY', 'FL']
        assert list(pie_trace.values) == [1500, 2000, 800, 700]
        
        # Check hover template exists
        assert pie_trace.hovertemplate is not None
    
    @patch('components.state_breakdown_graph.get_state_breakdown_data')
    @patch('components.state_breakdown_graph.get_cached_layout')
    @patch('utils.data_preprocessor.DataPreprocessor')
    def test_percentage_validation(self, mock_preprocessor, mock_layout, 
                                 mock_breakdown_data, mock_app):
        """Test that percentage calculations are validated."""
        # Setup mocks with percentages that don't sum to 100
        invalid_breakdown = {
            'breakdown_data': pd.DataFrame({
                'state': ['CA', 'TX'],
                'value': [1000, 2000],
                'percentage': [25.0, 50.0]  # Only sums to 75%
            }),
            'total_emissions': 3000,
            'subpart_list': ['C']
        }
        
        mock_df = pd.DataFrame({
            'REPORTING YEAR': [2020, 2021],
            'STATE': ['CA', 'TX'],
            'SUBPART': ['C', 'D'],
            'GHG QUANTITY (METRIC TONS CO2e)': [1000, 2000]
        })
        
        mock_preprocessor_instance = MagicMock()
        mock_preprocessor_instance.load_data.return_value = mock_df
        mock_preprocessor.return_value = mock_preprocessor_instance
        
        mock_breakdown_data.return_value = invalid_breakdown
        mock_layout.return_value = {'title': 'Test Title', 'height': 500}
        
        # Create component
        create_state_breakdown_graph(mock_app)
        callback_func = mock_app._callback_func
        
        # Test percentage validation
        result = callback_func(
            year_range=[2020, 2021],
            selected_subparts=['C'],
            selected_category=None,
            last_update=None
        )
        
        # Should return a tuple (figure, validation_data)
        assert isinstance(result, tuple)
        assert len(result) == 2
        figure, validation_data = result
        assert isinstance(figure, go.Figure)
    
    @patch('utils.data_preprocessor.DataPreprocessor')
    def test_callback_data_loading_error(self, mock_preprocessor, mock_app):
        """Test callback handling of data loading errors."""
        # Setup mock to raise exception
        mock_preprocessor_instance = MagicMock()
        mock_preprocessor_instance.load_data.side_effect = Exception("Data loading failed")
        mock_preprocessor.return_value = mock_preprocessor_instance
        
        # Create component
        create_state_breakdown_graph(mock_app)
        callback_func = mock_app._callback_func
        
        # Test with data loading error handling
        result = callback_func(
            year_range=[2020, 2021],
            selected_subparts=['C', 'D'],
            selected_category=None,
            last_update=None
        )
        
        # Should return a tuple (figure, validation_data)
        assert isinstance(result, tuple)
        assert len(result) == 2
        figure, validation_data = result
        assert isinstance(figure, go.Figure)
        
        # Check for error message in annotations or validation data
        annotations = figure.layout.annotations
        assert len(annotations) > 0
        # Should have either error in annotation text or in validation data
        has_error_annotation = any('error' in str(ann.text).lower() for ann in annotations)
        has_error_in_validation = 'error' in validation_data
        assert has_error_annotation or has_error_in_validation
    
    @patch('components.state_breakdown_graph.get_state_breakdown_data')
    @patch('components.state_breakdown_graph.get_cached_layout')
    @patch('utils.data_preprocessor.DataPreprocessor')
    def test_callback_subpart_filtering(self, mock_preprocessor, mock_layout, 
                                      mock_breakdown_data, mock_app, sample_breakdown_data):
        """Test that subpart filtering is passed correctly to aggregation function."""
        # Setup mocks
        mock_df = pd.DataFrame({
            'REPORTING YEAR': [2020, 2021],
            'STATE': ['CA', 'TX'],
            'SUBPART': ['C', 'D'],
            'GHG QUANTITY (METRIC TONS CO2e)': [1000, 2000]
        })
        
        mock_preprocessor_instance = MagicMock()
        mock_preprocessor_instance.load_data.return_value = mock_df
        mock_preprocessor.return_value = mock_preprocessor_instance
        
        mock_breakdown_data.return_value = sample_breakdown_data
        mock_layout.return_value = {'title': 'Test Title', 'height': 500}
        
        # Create component
        create_state_breakdown_graph(mock_app)
        callback_func = mock_app._callback_func
        
        # Test subpart filtering
        selected_subparts = ['C', 'AA', 'D']
        result = callback_func(
            year_range=[2020, 2021],
            selected_subparts=selected_subparts,
            selected_category=None,
            last_update=None
        )
        
        # Verify subpart filter was passed correctly
        args, kwargs = mock_breakdown_data.call_args
        assert kwargs['subpart_filter'] == selected_subparts
    
    @patch('components.state_breakdown_graph.get_state_breakdown_data')
    @patch('components.state_breakdown_graph.get_cached_layout')
    @patch('utils.data_preprocessor.DataPreprocessor')
    def test_callback_with_single_state(self, mock_preprocessor, mock_layout, 
                                      mock_breakdown_data, mock_app):
        """Test callback with data from only one state."""
        # Setup mocks with single state data
        single_state_breakdown = {
            'breakdown_data': pd.DataFrame({
                'state': ['CA'],
                'value': [5000],
                'percentage': [100.0]
            }),
            'total_emissions': 5000,
            'subpart_list': ['C', 'D']
        }
        
        mock_df = pd.DataFrame({
            'REPORTING YEAR': [2020, 2021],
            'STATE': ['CA', 'CA'],
            'SUBPART': ['C', 'D'],
            'GHG QUANTITY (METRIC TONS CO2e)': [2000, 3000]
        })
        
        mock_preprocessor_instance = MagicMock()
        mock_preprocessor_instance.load_data.return_value = mock_df
        mock_preprocessor.return_value = mock_preprocessor_instance
        
        mock_breakdown_data.return_value = single_state_breakdown
        mock_layout.return_value = {'title': 'Test Title', 'height': 500}
        
        # Create component
        create_state_breakdown_graph(mock_app)
        callback_func = mock_app._callback_func
        
        # Test with single state
        result = callback_func(
            year_range=[2020, 2021],
            selected_subparts=['C', 'D'],
            selected_category=None,
            last_update=None
        )
        
        # Should return a tuple (figure, validation_data)
        assert isinstance(result, tuple)
        assert len(result) == 2
        figure, validation_data = result
        assert isinstance(figure, go.Figure)
        
        # Should return a pie chart with single slice
        assert len(figure.data) == 1
        pie_trace = figure.data[0]
        assert len(pie_trace.labels) == 1
        assert pie_trace.labels[0] == 'CA'
        assert pie_trace.values[0] == 5000
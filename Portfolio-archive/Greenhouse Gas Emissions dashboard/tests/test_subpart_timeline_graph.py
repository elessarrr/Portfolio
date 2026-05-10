import sys
import os
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock
import plotly.graph_objects as go

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from components.subpart_timeline_graph import create_subpart_timeline_graph

@pytest.fixture
def sample_timeline_data():
    """Provides sample timeline data for testing."""
    return pd.DataFrame({
        'subpart': ['C', 'C', 'D', 'D', 'AA', 'AA'],
        'year': [2020, 2021, 2020, 2021, 2020, 2021],
        'value': [1000, 1500, 2000, 2500, 800, 900],
        'display_name': ['General Stationary Fuel Combustion Sources'] * 2 + 
                       ['Electricity Generation'] * 2 + 
                       ['Fossil Fuel Supply'] * 2
    })

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

class TestSubpartTimelineGraph:
    """Test cases for subpart timeline graph component."""
    
    def test_component_creation(self, mock_app):
        """Test that the component can be created without errors."""
        component = create_subpart_timeline_graph(mock_app)
        
        # Should return a Dash component
        assert component is not None
        
        # Should register a callback
        assert mock_app._callback_registered
    
    @patch('components.subpart_timeline_graph.get_subpart_timeline_data')
    @patch('components.subpart_timeline_graph.get_cached_layout')
    @patch('utils.data_preprocessor.DataPreprocessor')
    def test_callback_execution(self, mock_preprocessor, mock_layout, mock_timeline_data, 
                               mock_app, sample_timeline_data):
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
        
        mock_timeline_data.return_value = sample_timeline_data
        mock_layout.return_value = {
            'title': 'Test Title',
            'height': 500,
            'margin': {'l': 50, 'r': 20, 't': 80, 'b': 50}
        }
        
        # Create component to register callback
        create_subpart_timeline_graph(mock_app)
        
        # Get the callback function
        callback_func = mock_app._callback_func
        
        # Test callback execution
        result = callback_func(
            year_range=[2020, 2021],
            selected_states=['CA', 'TX'],
            category=None,
            last_update=None
        )
        
        # Should return a plotly figure
        assert isinstance(result, go.Figure)
        
        # Verify mocks were called
        mock_preprocessor_instance.load_data.assert_called_once()
        mock_timeline_data.assert_called_once()
        mock_layout.assert_called_once_with('subpart_timeline')
    
    @patch('components.subpart_timeline_graph.get_subpart_timeline_data')
    @patch('components.subpart_timeline_graph.get_cached_layout')
    @patch('components.subpart_timeline_graph.DataPreprocessor')
    def test_callback_with_invalid_year_range(self, mock_preprocessor, mock_layout, 
                                            mock_timeline_data, mock_app, sample_timeline_data):
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
        
        mock_timeline_data.return_value = sample_timeline_data
        mock_layout.return_value = {'title': 'Test Title', 'height': 500}
        
        # Create component
        create_subpart_timeline_graph(mock_app)
        callback_func = mock_app._callback_func
        
        # Test with invalid year range
        result = callback_func(
            year_range=None,  # Invalid
            selected_states=['CA'],
            category=None,
            last_update=None
        )
        
        # Should still return a figure (with default year range)
        assert isinstance(result, go.Figure)
        
        # Should have called timeline data with default range [2010, 2023]
        args, kwargs = mock_timeline_data.call_args
        assert kwargs['year_filter'] == (2010, 2023)
    
    @patch('components.subpart_timeline_graph.get_subpart_timeline_data')
    @patch('components.subpart_timeline_graph.get_cached_layout')
    @patch('components.subpart_timeline_graph.DataPreprocessor')
    def test_callback_with_empty_data(self, mock_preprocessor, mock_layout, 
                                    mock_timeline_data, mock_app):
        """Test callback handling of empty data."""
        # Setup mocks with empty data
        mock_df = pd.DataFrame(columns=['REPORTING YEAR', 'STATE', 'SUBPART', 'GHG QUANTITY (METRIC TONS CO2e)'])
        
        mock_preprocessor_instance = MagicMock()
        mock_preprocessor_instance.load_data.return_value = mock_df
        mock_preprocessor.return_value = mock_preprocessor_instance
        
        # Empty timeline data
        empty_timeline = pd.DataFrame(columns=['subpart', 'year', 'value', 'display_name'])
        mock_timeline_data.return_value = empty_timeline
        mock_layout.return_value = {'title': 'Test Title', 'height': 500}
        
        # Create component
        create_subpart_timeline_graph(mock_app)
        callback_func = mock_app._callback_func
        
        # Test with empty data
        result = callback_func(
            year_range=[2020, 2021],
            selected_states=['CA'],
            category=None,
            last_update=None
        )
        
        # Should return a figure with no data message
        assert isinstance(result, go.Figure)
        
        # Check that the figure has appropriate "no data" annotation
        annotations = result.layout.annotations
        assert len(annotations) > 0
        assert any('no data' in str(ann.text).lower() for ann in annotations)
    
    @patch('utils.data_preprocessor.DataPreprocessor')
    def test_callback_data_loading_error(self, mock_preprocessor, mock_app):
        """Test callback handling of data loading errors."""
        # Setup mock to raise exception
        mock_preprocessor_instance = MagicMock()
        mock_preprocessor_instance.load_data.side_effect = Exception("Data loading failed")
        mock_preprocessor.return_value = mock_preprocessor_instance
        
        # Create component
        create_subpart_timeline_graph(mock_app)
        callback_func = mock_app._callback_func
        
        # Test with data loading error handling
        result = callback_func(
            year_range=[2020, 2021],
            selected_states=['CA'],
            category=None,
            last_update=None
        )
        
        # Should return an error figure
        assert isinstance(result, go.Figure)
        
        # Check for error message in annotations
        annotations = result.layout.annotations
        assert len(annotations) > 0
        assert any('error' in str(ann.text).lower() for ann in annotations)
    
    @patch('components.subpart_timeline_graph.get_subpart_timeline_data')
    @patch('components.subpart_timeline_graph.get_cached_layout')
    @patch('utils.data_preprocessor.DataPreprocessor')
    def test_callback_state_filtering(self, mock_preprocessor, mock_layout, 
                                    mock_timeline_data, mock_app, sample_timeline_data):
        """Test that state filtering is passed correctly to aggregation function."""
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
        
        mock_timeline_data.return_value = sample_timeline_data
        mock_layout.return_value = {'title': 'Test Title', 'height': 500}
        
        # Create component
        create_subpart_timeline_graph(mock_app)
        callback_func = mock_app._callback_func
        
        # Test with state filtering
        selected_states = ['CA', 'NY', 'TX']
        result = callback_func(
            year_range=[2020, 2021],
            selected_states=selected_states,
            category=None,
            last_update=None
        )
        
        # Verify state filter was passed correctly
        args, kwargs = mock_timeline_data.call_args
        assert kwargs['state_filter'] == selected_states
    
    @patch('components.subpart_timeline_graph.get_subpart_timeline_data')
    @patch('components.subpart_timeline_graph.get_cached_layout')
    @patch('utils.data_preprocessor.DataPreprocessor')
    def test_callback_empty_states(self, mock_preprocessor, mock_layout, 
                                 mock_timeline_data, mock_app, sample_timeline_data):
        """Test callback with empty state selection."""
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
        
        mock_timeline_data.return_value = sample_timeline_data
        mock_layout.return_value = {'title': 'Test Title', 'height': 500}
        
        # Create component
        create_subpart_timeline_graph(mock_app)
        callback_func = mock_app._callback_func
        
        # Test with empty states
        result = callback_func(
            year_range=[2020, 2021],
            selected_states=[],  # Empty list
            category=None,
            last_update=None
        )
        
        # Should still return a figure
        assert isinstance(result, go.Figure)
        
        # Verify None was passed as state filter
        args, kwargs = mock_timeline_data.call_args
        assert kwargs['state_filter'] is None
import unittest
from unittest.mock import Mock, patch
import pandas as pd
import plotly.graph_objects as go
from dash import Dash
from components.state_graph import create_state_emissions_graph

class TestStateEmissionsGraph(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test"""
        self.app = Dash(__name__)
        self.test_data = pd.DataFrame({
            'year': [2019, 2019, 2020, 2020],
            'state': ['CA', 'NY', 'CA', 'NY'],
            'value': [100, 200, 150, 250]
        })

    @patch('components.state_graph.get_cached_data')
    def test_update_graph_with_valid_input(self, mock_get_cached_data):
        """Test graph update with valid input parameters"""
        # Configure mock
        mock_get_cached_data.return_value = {'main_chart_data': self.test_data.to_dict('records')}
        
        # Create component
        graph_component = create_state_emissions_graph(self.app)
        
        # Get the callback function
        update_graph = None
        for callback in self.app.callback_map.values():
            if callback.output.component_id == 'state-emissions-graph':
                update_graph = callback.callback
                break
        
        # Test the callback
        result = update_graph([2019, 2020], ['CA', 'NY'], None)
        
        # Assertions
        self.assertIsInstance(result, go.Figure)
        self.assertEqual(len(result.data), 2)  # Should have 2 traces for CA and NY
        self.assertEqual(result.layout.title.text, 'State GHG Emissions Over Time')

    @patch('components.state_graph.get_cached_data')
    def test_update_graph_with_empty_states(self, mock_get_cached_data):
        """Test graph update with no states selected"""
        mock_get_cached_data.return_value = {'main_chart_data': []}
        
        graph_component = create_state_emissions_graph(self.app)
        
        # Get the callback function
        update_graph = None
        for callback in self.app.callback_map.values():
            if callback.output.component_id == 'state-emissions-graph':
                update_graph = callback.callback
                break
        
        result = update_graph([2019, 2020], [], None)
        
        # Assertions
        self.assertIsInstance(result, go.Figure)
        self.assertEqual(len(result.data), 0)  # Should have no traces

    @patch('components.state_graph.get_cached_data')
    def test_update_graph_with_invalid_year_range(self, mock_get_cached_data):
        """Test graph update with invalid year range"""
        mock_get_cached_data.return_value = {'main_chart_data': self.test_data.to_dict('records')}
        
        graph_component = create_state_emissions_graph(self.app)
        
        # Get the callback function
        update_graph = None
        for callback in self.app.callback_map.values():
            if callback.output.component_id == 'state-emissions-graph':
                update_graph = callback.callback
                break
        
        # Test with invalid year range
        result = update_graph(None, ['CA', 'NY'], None)
        
        # Assertions
        self.assertIsInstance(result, go.Figure)
        self.assertEqual(len(result.data), 2)  # Should still create traces
        # Should use default year range [2000, 2020]

if __name__ == '__main__':
    unittest.main()
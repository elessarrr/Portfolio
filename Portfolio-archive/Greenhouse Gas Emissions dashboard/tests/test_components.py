import unittest
from unittest.mock import patch, MagicMock
from dash.testing.application_runners import import_app
from pathlib import Path
import sys
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from components.state_graph import create_state_emissions_graph
from components.subpart_graph import create_subpart_breakdown

class TestComponents(unittest.TestCase):
    def setUp(self):
        """Set up test data and mock app instance"""
        self.mock_app = MagicMock()
        self.test_data = pd.DataFrame({
            'STATE': ['CA', 'NY'],
            'YEAR': [2019, 2019],
            'SUBPART': ['C', 'D'],
            'EMISSIONS': [100, 200],
            'FACILITY_ID': ['F1', 'F2']
        })

    def test_state_emissions_graph_creation(self):
        """Test state emissions graph component creation"""
        graph_component = create_state_emissions_graph(self.mock_app)
        self.assertIsNotNone(graph_component)
        self.assertEqual(graph_component.className, 'emissions-chart-container')

        # Verify callback registration
        self.mock_app.callback.assert_called_once()
        callback_args = self.mock_app.callback.call_args
        self.assertEqual(len(callback_args[0]), 4)  # Output + 3 Inputs

    @patch('components.state_graph.load_emissions_data')
    def test_state_emissions_graph_update(self, mock_load_data):
        """Test state emissions graph update logic"""
        # Mock data loading
        mock_load_data.return_value = self.test_data
        
        # Create graph component
        graph = create_state_emissions_graph(self.mock_app)
        
        # Get update function (first argument of the callback)
        update_func = self.mock_app.callback.call_args[0][0]
        
        # Test update with sample inputs
        figure = update_func([2019, 2020], ['CA'], 'all')
        
        self.assertIsNotNone(figure)
        self.assertEqual(figure.layout.title.text, 'State GHG Emissions Over Time')

    def test_subpart_breakdown_creation(self):
        """Test subpart breakdown component creation"""
        breakdown = create_subpart_breakdown(
            data=self.test_data.to_dict('records'),
            selected_states=['CA', 'NY'],
            year_range=[2019, 2020]
        )
        
        self.assertIsNotNone(breakdown)
        self.assertEqual(breakdown.figure.layout.title.text, 'Emissions by Subpart')

    def test_subpart_breakdown_empty_data(self):
        """Test subpart breakdown handling of empty data"""
        breakdown = create_subpart_breakdown(
            data=[],
            selected_states=['CA'],
            year_range=[2019, 2020]
        )
        
        self.assertIsInstance(breakdown, type(dash.html.Div()))
        self.assertEqual(
            breakdown.children,
            "No data available for breakdown chart"
        )

    def test_subpart_breakdown_filtering(self):
        """Test subpart breakdown data filtering"""
        breakdown = create_subpart_breakdown(
            data=self.test_data.to_dict('records'),
            selected_states=['CA'],
            year_range=[2019, 2019]
        )
        
        # Verify filtered data is reflected in the chart
        figure_data = breakdown.figure.data[0]
        self.assertEqual(len(figure_data.values), 1)  # Only CA data
        self.assertEqual(figure_data.values[0], 100)  # CA emissions value

if __name__ == '__main__':
    unittest.main()
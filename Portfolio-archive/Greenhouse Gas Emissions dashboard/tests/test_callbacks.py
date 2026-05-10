import unittest
from unittest.mock import patch, MagicMock
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
from dash.testing.application_runners import import_app
from pathlib import Path
import sys
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from callbacks.data_callbacks import register_data_callbacks

class TestCallbacks(unittest.TestCase):
    def setUp(self):
        """Set up test environment and mock data"""
        self.mock_app = MagicMock()
        self.test_data = pd.DataFrame({
            'year': [2019, 2019, 2020, 2020],
            'state': ['CA', 'NY', 'CA', 'NY'],
            'SUBPART': ['C', 'D', 'C', 'D'],
            'EMISSIONS': [100, 200, 150, 250]
        })

    def test_year_range_callback(self):
        """Test the year range slider callback"""
        callbacks = register_data_callbacks(self.mock_app)
        update_year_range = callbacks['update_year_range']

        # Test valid year selection
        result = update_year_range([2019, 2020])
        self.assertIsInstance(result, list)
        self.assertEqual(result, [2019, 2020])

        # Test invalid year range
        with self.assertRaises(PreventUpdate):
            update_year_range([2020, 2019])

    def test_state_selection_callback(self):
        """Test the state selection callback"""
        callbacks = register_data_callbacks(self.mock_app)
        update_states = callbacks['update_states']

        # Test single state selection
        result = update_states(['CA'])
        self.assertIsInstance(result, list)
        self.assertEqual(result, ['CA'])

        # Test multiple state selection
        result = update_states(['CA', 'NY'])
        self.assertEqual(len(result), 2)
        self.assertIn('CA', result)
        self.assertIn('NY', result)

    def test_data_loading_callback(self):
        """Test the data loading and caching callback"""
        with patch('callbacks.data_callbacks.load_emissions_data') as mock_load:
            mock_load.return_value = self.test_data
            
            callbacks = register_data_callbacks(self.mock_app)
            update_data = callbacks['update_data']

            # Test data loading with filters
            result = update_data([2019, 2020], ['CA', 'NY'])
            self.assertIsInstance(result, dict)
            self.assertIn('main_chart_data', result)
            
            # Verify data structure
            chart_data = pd.DataFrame(result['main_chart_data'])
            self.assertEqual(len(chart_data), 4)
            self.assertTrue(all(chart_data['year'].isin([2019, 2020])))

    def test_error_handling(self):
        """Test error handling in callbacks"""
        callbacks = register_data_callbacks(self.mock_app)
        
        # Test with None inputs
        with self.assertRaises(PreventUpdate):
            callbacks['update_year_range'](None)

        with self.assertRaises(PreventUpdate):
            callbacks['update_states'](None)

if __name__ == '__main__':
    unittest.main()
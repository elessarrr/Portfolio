import unittest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add the parent directory to Python path for imports
sys.path.append(str(Path(__file__).parent.parent))

from utils.aggregation import filter_and_aggregate_data

class TestDataValidation(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.test_data = pd.DataFrame({
            'year': [2019, 2019, 2020, 2020],
            'state': ['CA', 'NY', 'CA', 'NY'],
            'SUBPART': ['C', 'D', 'C', 'D'],
            'EMISSIONS': [100, 200, 150, 250]
        })

    def test_data_filtering(self):
        """Test data filtering by year range and states"""
        result = filter_and_aggregate_data(
            self.test_data,
            selected_states=['CA'],
            year_range=[2019, 2020]
        )
        
        filtered_data = pd.DataFrame(result['main_chart_data'])
        self.assertEqual(len(filtered_data), 2)
        self.assertTrue(all(filtered_data['state'] == 'CA'))
        self.assertTrue(all(filtered_data['year'].isin([2019, 2020])))

    def test_aggregation_calculation(self):
        """Test emissions aggregation calculations"""
        result = filter_and_aggregate_data(
            self.test_data,
            selected_states=['CA', 'NY'],
            year_range=[2019, 2020]
        )
        
        agg_data = pd.DataFrame(result['main_chart_data'])
        # Test total emissions for 2019
        emissions_2019 = agg_data[agg_data['year'] == 2019]['value'].sum()
        self.assertEqual(emissions_2019, 300)  # 100 + 200
        
        # Test total emissions for 2020
        emissions_2020 = agg_data[agg_data['year'] == 2020]['value'].sum()
        self.assertEqual(emissions_2020, 400)  # 150 + 250

    def test_invalid_inputs(self):
        """Test handling of invalid inputs"""
        # Test with invalid year range
        with self.assertRaises(ValueError):
            filter_and_aggregate_data(
                self.test_data,
                selected_states=['CA'],
                year_range=[2020, 2019]  # Invalid range
            )

        # Test with non-existent state
        result = filter_and_aggregate_data(
            self.test_data,
            selected_states=['TX'],  # Non-existent state
            year_range=[2019, 2020]
        )
        self.assertEqual(len(result['main_chart_data']), 0)

if __name__ == '__main__':
    unittest.main()
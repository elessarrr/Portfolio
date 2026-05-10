import unittest
import pandas as pd
from pathlib import Path
import sys

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from utils.aggregation import filter_by_subpart
from components.subpart_graph import update_subpart_breakdown

class TestSubpartFilter(unittest.TestCase):
    def setUp(self):
        """Set up test data"""
        self.test_data = pd.DataFrame({
            'YEAR': [2019, 2019, 2020, 2020],
            'STATE': ['CA', 'NY', 'CA', 'NY'],
            'SUBPART': ['C', 'D', 'C', 'D'],
            'GHG_QUANTITY': [100, 200, 150, 250],
            'FACILITY_ID': ['F1', 'F2', 'F1', 'F2']
        })

    def test_subpart_filtering(self):
        """Test filtering data by subpart"""
        filtered_data = filter_by_subpart(
            self.test_data,
            selected_subparts=['C']
        )
        
        self.assertEqual(len(filtered_data), 2)
        self.assertTrue(all(filtered_data['SUBPART'] == 'C'))
        
        # Test emissions values
        ca_emissions = filtered_data[filtered_data['STATE'] == 'CA']['GHG_QUANTITY'].sum()
        self.assertEqual(ca_emissions, 250)  # 100 + 150

    def test_multiple_subpart_filtering(self):
        """Test filtering with multiple subparts"""
        filtered_data = filter_by_subpart(
            self.test_data,
            selected_subparts=['C', 'D']
        )
        
        self.assertEqual(len(filtered_data), 4)
        self.assertTrue(all(filtered_data['SUBPART'].isin(['C', 'D'])))

    def test_empty_subpart_selection(self):
        """Test behavior with no subparts selected"""
        filtered_data = filter_by_subpart(
            self.test_data,
            selected_subparts=[]
        )
        
        self.assertEqual(len(filtered_data), 4)  # Should return all data
        
    def test_subpart_breakdown_update(self):
        """Test subpart breakdown visualization update"""
        figure = update_subpart_breakdown(
            data=self.test_data.to_dict('records'),
            selected_states=['CA', 'NY'],
            year_range=[2019, 2020]
        )
        
        self.assertIsNotNone(figure)
        self.assertEqual(figure.layout.title.text, 'Emissions by Subpart')
        self.assertEqual(len(figure.data), 2)  # Two subparts C and D

    def test_invalid_subpart_selection(self):
        """Test handling of invalid subpart selection"""
        filtered_data = filter_by_subpart(
            self.test_data,
            selected_subparts=['X']  # Non-existent subpart
        )
        
        self.assertEqual(len(filtered_data), 0)

if __name__ == '__main__':
    unittest.main()
import unittest
from unittest.mock import patch
from dash.testing.application_runners import import_app
from dash.testing.browser import Browser

class TestDashboardIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.driver = Browser()
        cls.driver.maximize_window()

    def setUp(self):
        self.app = import_app('app')
        self.app_runner = self.app.run_server(debug=True, port=8050)

    def tearDown(self):
        self.app_runner.stop()

    @classmethod
    def tearDownClass(cls):
        cls.driver.quit()

    def test_initial_layout(self):
        """Test that the dashboard loads with all expected components"""
        self.driver.get('http://localhost:8050')
        
        # Check header
        header = self.driver.find_element_by_css_selector('.dashboard-header')
        self.assertIsNotNone(header)
        
        # Check filters presence
        filters = self.driver.find_element_by_css_selector('.filters-container')
        self.assertIsNotNone(filters)
        
        # Check graphs presence
        state_graph = self.driver.find_element_by_id('state-emissions-graph')
        self.assertIsNotNone(state_graph)
        
        subpart_container = self.driver.find_element_by_id('subpart-breakdown-container')
        self.assertIsNotNone(subpart_container)

    @patch('utils.cache_utils.get_cached_data')
    def test_filter_interaction(self, mock_get_cached_data):
        """Test that filters interact correctly with graphs"""
        mock_data = {
            'main_chart_data': [
                {'year': 2019, 'state': 'CA', 'value': 100},
                {'year': 2020, 'state': 'CA', 'value': 150}
            ]
        }
        mock_get_cached_data.return_value = mock_data
        
        self.driver.get('http://localhost:8050')
        
        # Select state
        state_dropdown = self.driver.find_element_by_id('state-dropdown')
        state_dropdown.click()
        state_dropdown.send_keys('CA')
        state_dropdown.send_keys(Keys.ENTER)
        
        # Verify graph update
        state_graph = self.driver.find_element_by_id('state-emissions-graph')
        self.assertTrue('CA' in state_graph.text)

if __name__ == '__main__':
    unittest.main()
"""Tests for Sample Data Generator

This module tests the sample data generation functionality.
"""

import unittest
import pandas as pd
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.sample_data_generator import generate_ship_arrivals, generate_berth_schedule, generate_container_movements


class TestSampleDataGenerator(unittest.TestCase):
    """Test cases for sample data generator functions"""
    
    def test_generate_ship_arrivals(self):
        """Test ship arrivals generation"""
        # Test basic functionality
        ships_df = generate_ship_arrivals(5)
        
        # Check DataFrame structure
        self.assertIsInstance(ships_df, pd.DataFrame)
        self.assertEqual(len(ships_df), 5)
        
        # Check required columns
        required_columns = ['ship_id', 'ship_name', 'ship_type', 'size_teu', 
                          'arrival_time', 'containers_to_unload', 'containers_to_load']
        for col in required_columns:
            self.assertIn(col, ships_df.columns)
        
        # Check data types and ranges
        self.assertTrue(all(ships_df['ship_type'].isin(['container', 'bulk'])))
        self.assertTrue(all(ships_df['size_teu'] > 0))
        self.assertTrue(all(ships_df['containers_to_unload'] >= 0))
        self.assertTrue(all(ships_df['containers_to_load'] >= 0))
    
    def test_generate_berth_schedule(self):
        """Test berth schedule generation"""
        # Note: This test requires berths.csv to exist
        try:
            schedule_df = generate_berth_schedule(3)
            
            # Check DataFrame structure
            self.assertIsInstance(schedule_df, pd.DataFrame)
            self.assertGreater(len(schedule_df), 0)
            
            # Check required columns
            required_columns = ['date', 'berth_id', 'berth_name', 'occupied_hours', 
                              'utilization_rate', 'ships_served']
            for col in required_columns:
                self.assertIn(col, schedule_df.columns)
            
            # Check utilization rate is between 0 and 1
            self.assertTrue(all(schedule_df['utilization_rate'] >= 0))
            self.assertTrue(all(schedule_df['utilization_rate'] <= 1))
            
        except FileNotFoundError:
            self.skipTest("berths.csv not found - skipping berth schedule test")
    
    def test_generate_container_movements(self):
        """Test container movements generation"""
        movements_df = generate_container_movements(10)
        
        # Check DataFrame structure
        self.assertIsInstance(movements_df, pd.DataFrame)
        self.assertEqual(len(movements_df), 10)
        
        # Check required columns
        required_columns = ['movement_id', 'container_id', 'movement_type', 
                          'berth_id', 'timestamp', 'duration_minutes', 'crane_id']
        for col in required_columns:
            self.assertIn(col, movements_df.columns)
        
        # Check movement types
        valid_types = ['load', 'unload', 'transfer']
        self.assertTrue(all(movements_df['movement_type'].isin(valid_types)))
        
        # Check duration is positive
        self.assertTrue(all(movements_df['duration_minutes'] > 0))


if __name__ == '__main__':
    unittest.main()
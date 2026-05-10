#!/usr/bin/env python3
"""
Debug script to test the subpart timeline graph error handling.
"""

import sys
import os
from unittest.mock import patch, MagicMock
import plotly.graph_objects as go

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from components.subpart_timeline_graph import create_subpart_timeline_graph

def test_error_handling():
    """Test error handling in subpart timeline graph."""
    # Create mock app
    app = MagicMock()
    
    # Mock the callback decorator to capture the callback function
    def mock_callback(*args, **kwargs):
        def decorator(func):
            # Store the callback function for testing
            app._callback_func = func
            return func
        return decorator
    
    app.callback = mock_callback
    
    # Patch DataPreprocessor at the utils module level
    with patch('utils.data_preprocessor.DataPreprocessor') as mock_preprocessor:
        # Setup mock to raise exception
        mock_preprocessor_instance = MagicMock()
        mock_preprocessor_instance.load_data.side_effect = Exception("Data loading failed")
        mock_preprocessor.return_value = mock_preprocessor_instance
        
        # Create component
        create_subpart_timeline_graph(app)
        callback_func = app._callback_func
        
        # Test with data loading error handling
        try:
            result = callback_func(
                year_range=[2020, 2021],
                selected_states=['CA'],
                category=None,
                last_update=None
            )
            
            print(f"Result type: {type(result)}")
            print(f"Result: {result}")
            
            if hasattr(result, 'layout'):
                print(f"Layout: {result.layout}")
                if hasattr(result.layout, 'annotations'):
                    print(f"Annotations: {result.layout.annotations}")
                    print(f"Number of annotations: {len(result.layout.annotations)}")
                    for i, ann in enumerate(result.layout.annotations):
                        print(f"Annotation {i}: {ann.text}")
                else:
                    print("No annotations attribute")
            else:
                print("No layout attribute")
                
        except Exception as e:
            print(f"Exception raised: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_error_handling()
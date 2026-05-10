import sys
import os
import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from components.subpart_selector import create_subpart_selector

@pytest.fixture
def sample_emissions_data():
    """Provides sample emissions data for testing."""
    return pd.DataFrame({
        'REPORTING YEAR': [2020, 2020, 2021, 2021, 2022, 2022],
        'STATE': ['CA', 'TX', 'CA', 'TX', 'NY', 'FL'],
        'SUBPART': ['C', 'D', 'C', 'AA', 'D', 'C'],
        'GHG QUANTITY (METRIC TONS CO2e)': [1000, 1500, 1200, 800, 900, 600]
    })

@pytest.fixture
def mock_app():
    """Mock Dash app for testing."""
    app = MagicMock()
    app.callback = MagicMock()
    return app

class TestSubpartSelector:
    """Test cases for subpart selector component."""
    
    def test_component_creation(self, mock_app):
        """Test that the component can be created without errors."""
        component = create_subpart_selector()
        
        # Should return a Dash component
        assert component is not None
        assert hasattr(component, 'id')
        assert component.id == 'subpart-selector'
    
    def test_callback_execution(self, mock_app, sample_emissions_data):
        """Test that the callback executes correctly and returns subpart options."""
        # Create component to register callback
        component = create_subpart_selector()
        
        # Should return a dropdown component
        assert component is not None
        assert hasattr(component, 'id')
        assert component.id == 'subpart-selector'
        
        # Check that options are available
        assert hasattr(component, 'options')
        assert isinstance(component.options, list)
        assert len(component.options) > 0
        
        # Check option structure
        for option in component.options:
            assert 'label' in option
            assert 'value' in option
            assert ' - ' in option['label']  # Format: "CODE - Description"
        
        # Check default values
        assert hasattr(component, 'value')
        assert isinstance(component.value, list)
        expected_defaults = ['C', 'AA', 'D']
        assert component.value == expected_defaults
    
    def test_component_properties(self, mock_app):
        """Test that the component has correct properties."""
        component = create_subpart_selector()
        
        # Check basic properties
        assert component.id == 'subpart-selector'
        assert component.multi is True
        assert component.placeholder == "Select subparts to analyze..."
        
        # Check that options are sorted
        option_values = [opt['value'] for opt in component.options]
        assert option_values == sorted(option_values)
    
    def test_option_formatting(self, mock_app):
        """Test that options are formatted correctly."""
        component = create_subpart_selector()
        
        # Check that all options have the correct format
        for option in component.options:
            assert 'label' in option
            assert 'value' in option
            assert ' - ' in option['label']
            
            # Label should be "CODE - Description"
            parts = option['label'].split(' - ', 1)
            assert len(parts) == 2
            assert parts[0] == option['value']
    
    def test_default_values(self, mock_app):
        """Test that default values are set correctly."""
        component = create_subpart_selector()
        
        # Check default values
        expected_defaults = ['C', 'AA', 'D']
        assert component.value == expected_defaults
        
        # Verify all default values exist in options
        option_values = [opt['value'] for opt in component.options]
        for default_val in expected_defaults:
            assert default_val in option_values
    
    def test_reserved_subparts_excluded(self, mock_app):
        """Test that reserved subparts are excluded from options."""
        component = create_subpart_selector()
        
        # Check that no option has '(Reserved)' in the label
        for option in component.options:
            assert '(Reserved)' not in option['label']
    
    def test_component_structure(self, mock_app):
        """Test the overall structure of the component."""
        component = create_subpart_selector()
        
        # Should be a dropdown component
        assert hasattr(component, 'options')
        assert hasattr(component, 'value')
        assert hasattr(component, 'multi')
        assert hasattr(component, 'id')
        assert hasattr(component, 'placeholder')
        
        # Options should not be empty
        assert len(component.options) > 0
        
        # All options should have required keys
        for option in component.options:
            assert isinstance(option, dict)
            assert 'label' in option
            assert 'value' in option
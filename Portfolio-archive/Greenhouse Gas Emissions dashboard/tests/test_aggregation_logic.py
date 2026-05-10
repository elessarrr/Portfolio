import sys
import os
import pandas as pd
import pytest

# Add project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.aggregation_v2 import get_subpart_breakdown_data

@pytest.fixture
def sample_emissions_data():
    """Provides a sample DataFrame for testing."""
    data = {
        'REPORTING YEAR': [2023, 2023, 2023],
        'STATE': ['CA', 'TX', 'CA'],
        'SUBPARTS': ['C', 'W, D', 'D'],
        'GHG QUANTITY (METRIC TONS CO2e)': [1000, 2000, 500]
    }
    return pd.DataFrame(data)

def test_subpart_d_percentage(sample_emissions_data):
    """Tests if Subpart D receives the correct proportional emissions and percentage."""
    # In the sample data, one row has 'W, D' with 2000 emissions.
    # This means Subpart D should get 1000 (50% of 2000).
    # Another row has Subpart D with 500 emissions.
    # Total emissions for D = 1000 + 500 = 1500.
    # Total emissions for C = 1000.
    # Total emissions for W = 1000.
    # Grand total emissions = 1500 (D) + 1000 (C) + 1000 (W) = 3500.
    # Expected percentage for D = (1500 / 3500) * 100 = 42.857... which rounds to 42.9%.

    result = get_subpart_breakdown_data(sample_emissions_data)
    
    subpart_d_data = None
    for item in result['data']:
        if item['subpart'] == 'D':
            subpart_d_data = item
            break

    assert subpart_d_data is not None, "Subpart D not found in the result."
    
    # Check the emissions value for Subpart D
    expected_emissions_d = 1500
    assert subpart_d_data['emissions'] == expected_emissions_d, \
        f"Incorrect emissions for Subpart D. Expected {expected_emissions_d}, got {subpart_d_data['emissions']}"

    # Check the percentage for Subpart D
    expected_percentage_d = 42.9
    assert abs(subpart_d_data['percentage'] - expected_percentage_d) < 0.01, \
        f"Incorrect percentage for Subpart D. Expected {expected_percentage_d}, got {subpart_d_data['percentage']}"
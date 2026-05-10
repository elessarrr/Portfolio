import pytest
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager

@pytest.fixture(scope='session')
def dash_driver():
    """Fixture to initialize and quit a WebDriver instance for Dash tests."""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--remote-debugging-port=9222')
    
    try:
        # Try to use webdriver-manager to install chromedriver
        service = ChromeService(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        # Fallback: try to use chromedriver from PATH or skip test
        pytest.skip(f"Chrome WebDriver setup failed: {e}. Please install chromedriver manually.")
    
    yield driver
    driver.quit()

@pytest.fixture
def sample_emissions_data():
    """Fixture to provide sample emissions data for testing"""
    return pd.DataFrame({
        'year': [2019, 2019, 2020, 2020],
        'state': ['CA', 'NY', 'CA', 'NY'],
        'SUBPART': ['C', 'D', 'C', 'D'],
        'EMISSIONS': [100, 200, 150, 250]
    })

@pytest.fixture
def mock_cache_data(sample_emissions_data):
    """Fixture to provide mock cache data"""
    return {
        'main_chart_data': sample_emissions_data.to_dict('records')
    }
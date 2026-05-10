import streamlit as st
import pandas as pd
import requests
from typing import Dict, Optional
from datetime import datetime

# Error handling decorator
def handle_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            st.error(f"Error in {func.__name__}: {str(e)}")
            return None
    return wrapper

# Data loading with proper caching
@st.cache_data(ttl=86400)
@handle_exceptions
def load_crude_oil_data() -> Optional[Dict]:
    """Load and process EIA crude oil inventory data with dynamic date range"""
    try:
        #current_time = datetime.now().strftime('%H:%M:%S') - was debugging API call
        #st.sidebar.warning(f"🔄 Making API call at: {current_time}") - was debugging API call
        api_key = st.secrets["api_key"]
        url = f"https://api.eia.gov/v2/petroleum/stoc/wstk/data/"
        
        # Force cache clear for testing
        #st.cache_data.clear() - was debugging API call
        
        # First, get a small amount of the most recent data to find the latest date
        initial_params = {
            "frequency": "weekly",
            "data[0]": "value",
            "facets[product][]": "EPC0",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "offset": 0,
            "length": 5,  # Just get a few records to find the latest date
            "api_key": api_key
        }
        
        with st.spinner("Checking latest available data..."):
            initial_response = requests.get(url, params=initial_params, timeout=15)
            initial_response.raise_for_status()
            
            initial_data = initial_response.json()
            if not initial_data["response"]["data"]:
                st.error("No data available from EIA API")
                return None
            
            # Get the latest date available
            latest_date = pd.to_datetime(initial_data["response"]["data"][0]["period"])
            
            # Calculate date 2 years before the latest date
            start_date = (latest_date - pd.DateOffset(years=2)).strftime('%Y-%m-%d')
            end_date = latest_date.strftime('%Y-%m-%d')
            
            st.info(f"Loading data from {start_date} to {end_date} (latest available)")
        
        # Now fetch the full 2-year dataset
        params = {
            "frequency": "weekly",
            "data[0]": "value",
            "facets[product][]": "EPC0",
            "start": start_date,
            "end": end_date,
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "offset": 0,
            "length": 5000,
            "api_key": api_key
        }
        
        with st.spinner("Loading EIA data..."):
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data["response"]["data"])
            
            if df.empty:
                st.error("No data returned from EIA API")
                return None
            
            # Ensure numeric type conversion for inventory values
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            
            # Process the data
            df['period'] = pd.to_datetime(df['period'])
            df.rename(columns={'value': 'inventory', 'area-name': 'region'}, inplace=True)
            df['type'] = 'historical'
            
            # Filter out 'NA' region
            df = df[df['region'] != 'NA']
            
            return {
                'data': df.sort_values('period'),
                'full_data': df.sort_values('period'),
                'latest_date': latest_date,
                'start_date': pd.to_datetime(start_date),
                'regions': df['region'].unique().tolist()
            }
    
    except Exception as e:
        st.error(f"Error loading EIA data: {str(e)}")
        return None


@st.cache_data(ttl=86400)
@handle_exceptions
def load_wti_price_data(start_date: str, end_date: str) -> Optional[pd.DataFrame]:
    """Load WTI crude oil price data from EIA API"""
    try:
        api_key = 'nsH8duWHIP4GA3eL1RgSoWh8my1gGOBpfzqyIeKp'
        url = "https://api.eia.gov/v2/petroleum/pri/spt/data/"
        
        params = {
            "frequency": "weekly",
            "data[0]": "value",
            "facets[series][]": "RWTC",
            "start": start_date,
            "end": end_date,
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "offset": 0,
            "length": 5000,
            "api_key": api_key
        }
        
        with st.spinner("Loading WTI price data..."):
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            df = pd.DataFrame(data["response"]["data"])
            
            if df.empty:
                st.error("No WTI price data available from EIA API")
                return None
            
            # Process the data
            df['period'] = pd.to_datetime(df['period'])
            df.rename(columns={'value': 'price'}, inplace=True)
            df['price'] = pd.to_numeric(df['price'], errors='coerce')
            
            return df.sort_values('period')
    
    except Exception as e:
        st.error(f"Error loading WTI price data: {str(e)}")
        return None

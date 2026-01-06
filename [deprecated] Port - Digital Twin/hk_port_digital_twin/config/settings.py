"""Configuration settings for Hong Kong Port Digital Twin

This module contains all configuration parameters for the port simulation.
Modify these values to adjust simulation behavior without changing core logic.
"""

# Port Configuration
PORT_CONFIG = {
    'num_berths': 8,
    'berth_capacity': 5000,  # TEU (Twenty-foot Equivalent Units)
    'operating_hours': 24,   # Hours per day
}

# Ship Types and Characteristics
SHIP_TYPES = {
    'container': {
        'min_size': 1000,
        'max_size': 20000,
        'processing_rate': 100,  # TEU per hour
    },
    'bulk': {
        'min_size': 5000,
        'max_size': 50000,
        'processing_rate': 200,  # Tons per hour
    }
}

# Simulation Parameters
SIMULATION_CONFIG = {
    'time_unit': 'hours',
    'default_duration': 168,  # 1 week in hours
    'ship_arrival_rate': 2,   # Ships per hour
}
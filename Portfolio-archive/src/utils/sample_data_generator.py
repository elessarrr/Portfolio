"""Sample Data Generator for Hong Kong Port Digital Twin

This module generates realistic sample data for development and testing.
Use this when real APIs are unavailable or for offline development.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
from typing import List, Dict


def generate_ship_arrivals(num_ships: int = 50, start_date: datetime = None) -> pd.DataFrame:
    """Generate sample ship arrival data
    
    Args:
        num_ships: Number of ships to generate
        start_date: Starting date for arrivals (defaults to today)
        
    Returns:
        DataFrame with ship arrival data
    """
    if start_date is None:
        start_date = datetime.now()
    
    ships = []
    ship_types = ['container', 'bulk']
    
    for i in range(num_ships):
        ship_type = random.choice(ship_types)
        
        if ship_type == 'container':
            size = random.randint(1000, 20000)
            containers_unload = random.randint(100, 1000)
            containers_load = random.randint(50, 800)
        else:  # bulk
            size = random.randint(5000, 50000)
            containers_unload = 0
            containers_load = random.randint(500, 2000)
        
        # Generate arrival time (spread over several days)
        arrival_offset = timedelta(hours=random.uniform(0, 168))  # 1 week
        arrival_time = start_date + arrival_offset
        
        ship = {
            'ship_id': i + 1,
            'ship_name': f'{ship_type.upper()}_SHIP_{i+1:03d}',
            'ship_type': ship_type,
            'size_teu': size,
            'arrival_time': arrival_time.strftime('%Y-%m-%d %H:%M'),
            'containers_to_unload': containers_unload,
            'containers_to_load': containers_load
        }
        ships.append(ship)
    
    return pd.DataFrame(ships)


def generate_berth_schedule(num_days: int = 7) -> pd.DataFrame:
    """Generate sample berth scheduling data
    
    Args:
        num_days: Number of days to generate schedule for
        
    Returns:
        DataFrame with berth schedule data
    """
    berths = pd.read_csv('data/sample/berths.csv')
    schedule = []
    
    start_date = datetime.now()
    
    for day in range(num_days):
        current_date = start_date + timedelta(days=day)
        
        for _, berth in berths.iterrows():
            # Random occupancy throughout the day
            occupied_hours = random.randint(8, 20)  # 8-20 hours per day
            
            schedule_entry = {
                'date': current_date.strftime('%Y-%m-%d'),
                'berth_id': berth['berth_id'],
                'berth_name': berth['berth_name'],
                'occupied_hours': occupied_hours,
                'utilization_rate': occupied_hours / 24.0,
                'ships_served': random.randint(1, 3)
            }
            schedule.append(schedule_entry)
    
    return pd.DataFrame(schedule)


def generate_container_movements(num_records: int = 100) -> pd.DataFrame:
    """Generate sample container movement data
    
    Args:
        num_records: Number of movement records to generate
        
    Returns:
        DataFrame with container movement data
    """
    movements = []
    movement_types = ['load', 'unload', 'transfer']
    
    for i in range(num_records):
        movement = {
            'movement_id': i + 1,
            'container_id': f'CONT_{i+1:06d}',
            'movement_type': random.choice(movement_types),
            'berth_id': random.randint(1, 8),
            'timestamp': datetime.now() + timedelta(minutes=random.randint(0, 10080)),  # 1 week
            'duration_minutes': random.randint(15, 120),
            'crane_id': random.randint(1, 4)
        }
        movements.append(movement)
    
    return pd.DataFrame(movements)


if __name__ == '__main__':
    # Generate and save sample data
    print("Generating sample data...")
    
    # Generate ships
    ships_df = generate_ship_arrivals(20)
    ships_df.to_csv('data/sample/generated_ships.csv', index=False)
    print(f"Generated {len(ships_df)} ship records")
    
    # Generate berth schedule
    schedule_df = generate_berth_schedule(7)
    schedule_df.to_csv('data/sample/berth_schedule.csv', index=False)
    print(f"Generated {len(schedule_df)} berth schedule records")
    
    # Generate container movements
    movements_df = generate_container_movements(50)
    movements_df.to_csv('data/sample/container_movements.csv', index=False)
    print(f"Generated {len(movements_df)} container movement records")
    
    print("Sample data generation complete!")
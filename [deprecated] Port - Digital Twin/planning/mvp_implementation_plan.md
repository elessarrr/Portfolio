# Hong Kong Port Digital Twin - MVP Implementation Plan

## Overview
This document provides a conservative, step-by-step approach to implement the Hong Kong Port Digital Twin MVP. The plan prioritizes safety, modularity, and easy rollback capabilities.

## Core Principles
- **Conservative Development**: Never break existing functionality
- **Modular Design**: All new code in separate, importable modules
- **Easy Rollback**: Git-based version control with clear checkpoints
- **Minimal Code**: Write only what's necessary for MVP functionality
- **Safety First**: Test each component independently before integration

## MVP Scope (Weeks 1-4)
Build a working simulation with:
1. Basic port structure and configuration
2. Ship arrival and processing simulation
3. Simple berth allocation
4. Basic visualization dashboard
5. Sample data for offline development

## Pre-Implementation Checklist
- [ ] Initialize git repository in `/Port/` directory
- [ ] Create `.gitignore` file
- [ ] Set up virtual environment
- [ ] Document current state (baseline)

---

## Phase 1: Project Foundation (Week 1)

### Step 1.1: Directory Structure Setup (30 minutes)
**Goal**: Create the basic project structure without affecting existing files

**Actions**:
1. Navigate to `/Port/` directory
2. Create the following structure:
   ```
   hk_port_digital_twin/
   ├── data/
   │   ├── raw/
   │   ├── processed/
   │   └── sample/
   ├── src/
   │   ├── __init__.py
   │   ├── core/
   │   │   └── __init__.py
   │   ├── utils/
   │   │   └── __init__.py
   │   └── dashboard/
   │       └── __init__.py
   ├── tests/
   ├── config/
   └── docs/
   ```

**Safety Notes**:
- Keep existing `dev/` folder untouched
- All new code goes in `hk_port_digital_twin/` subdirectory
- Use relative imports within the new structure

**Validation**:
- Verify directory structure matches plan
- Ensure no existing files were modified
- Test that you can navigate to all new directories

### Step 1.2: Git Repository Initialization (15 minutes)
**Goal**: Set up version control for safe development

**Actions**:
1. Initialize git in `/Port/hk_port_digital_twin/`
2. Create `.gitignore` with:
   ```
   __pycache__/
   *.pyc
   *.pyo
   *.pyd
   .Python
   env/
   venv/
   .venv/
   .env
   .DS_Store
   *.log
   data/raw/*
   !data/raw/.gitkeep
   ```
3. Create initial commit: "Initial project structure"

**Safety Notes**:
- Only initialize git within the new project directory
- Don't affect any parent directory git settings
- Keep sensitive data out of version control

### Step 1.3: Requirements and Configuration (45 minutes)
**Goal**: Set up dependencies and basic configuration

**Actions**:
1. Create `requirements.txt`:
   ```
   streamlit==1.28.0
   plotly==5.17.0
   pandas==2.1.0
   numpy==1.24.0
   simpy==4.0.1
   requests==2.31.0
   python-dotenv==1.0.0
   ```

2. Create `config/settings.py`:
   ```python
   """
   Configuration settings for Hong Kong Port Digital Twin
   
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
   ```

3. Create `.env.example`:
   ```
   # API Keys (copy to .env and add real values)
   MARINE_TRAFFIC_API_KEY=your_api_key_here
   HK_MARINE_DEPT_API_KEY=your_api_key_here
   
   # Development Settings
   DEBUG=True
   LOG_LEVEL=INFO
   ```

**Safety Notes**:
- Use `.env` for secrets, never commit actual API keys
- Keep configuration separate from logic
- Use sensible defaults that work offline

**Validation**:
- Install requirements in virtual environment
- Import settings.py successfully
- Verify no syntax errors

### Step 1.4: Sample Data Creation (2 hours)
**Goal**: Create realistic sample data for offline development

**Actions**:
1. Create `data/sample/ships.csv`:
   ```csv
   ship_id,ship_name,ship_type,size_teu,arrival_time,containers_to_unload,containers_to_load
   1,HK_EXPRESS_001,container,15000,2024-01-01 08:00,800,600
   2,BULK_CARRIER_002,bulk,25000,2024-01-01 10:30,0,1200
   3,CONTAINER_003,container,8000,2024-01-01 14:15,400,300
   ```

2. Create `data/sample/berths.csv`:
   ```csv
   berth_id,berth_name,max_capacity_teu,crane_count,berth_type
   1,Berth_A1,20000,4,container
   2,Berth_A2,20000,4,container
   3,Berth_B1,30000,2,bulk
   4,Berth_B2,30000,2,bulk
   ```

3. Create `src/utils/sample_data_generator.py`:
   ```python
   """
   Sample Data Generator for Hong Kong Port Digital Twin
   
   This module generates realistic sample data for development and testing.
   Use this when real APIs are unavailable or for offline development.
   """
   
   import pandas as pd
   import numpy as np
   from datetime import datetime, timedelta
   import random
   
   def generate_ship_arrivals(num_ships=50, start_date=None):
       """Generate sample ship arrival data"""
       # Implementation details...
   
   def generate_berth_schedule(num_days=7):
       """Generate sample berth scheduling data"""
       # Implementation details...
   ```

**Safety Notes**:
- Keep sample data realistic but not based on real sensitive information
- Use clearly marked sample/test data
- Ensure sample data works without external dependencies

**Validation**:
- Load sample CSV files successfully
- Generate additional sample data programmatically
- Verify data formats match expected schemas

---

## Phase 2: Core Simulation Engine (Week 2)

### Step 2.1: Ship Management Module (2 hours)
**Goal**: Create ship entity system with state tracking

**Actions**:
1. Create `src/core/ship_manager.py`:
   ```python
   """
   Ship Management System for Hong Kong Port Digital Twin
   
   This module handles ship entities, their states, and queue management.
   Ships progress through states: arriving -> waiting -> docking -> processing -> departing
   """
   
   from enum import Enum
   from dataclasses import dataclass
   from typing import List, Optional
   import simpy
   
   class ShipState(Enum):
       """Possible states for ships in the port system"""
       ARRIVING = "arriving"
       WAITING = "waiting"
       DOCKING = "docking"
       PROCESSING = "processing"
       DEPARTING = "departing"
       DEPARTED = "departed"
   
   @dataclass
   class Ship:
       """Ship entity with all relevant attributes"""
       ship_id: str
       name: str
       ship_type: str
       size_teu: int
       arrival_time: float
       containers_to_unload: int
       containers_to_load: int
       state: ShipState = ShipState.ARRIVING
       assigned_berth: Optional[int] = None
       
   class ShipManager:
       """Manages ship entities and their lifecycle"""
       
       def __init__(self, env: simpy.Environment):
           self.env = env
           self.ships = {}
           self.waiting_queue = []
           
       def add_ship(self, ship: Ship):
           """Add a new ship to the system"""
           # Implementation...
           
       def update_ship_state(self, ship_id: str, new_state: ShipState):
           """Update ship state and handle transitions"""
           # Implementation...
   ```

**Safety Notes**:
- Use dataclasses for clear ship structure
- Implement state validation to prevent invalid transitions
- Keep ship logic separate from berth logic

**Testing**:
- Create ships with sample data
- Test state transitions
- Verify queue management works

**Completed Implementation Notes**:
- ✅ Ship Management Module implemented with comprehensive state management
- ✅ Used dataclasses with validation for Ship entity
- ✅ Implemented ShipState enum for clear state transitions
- ✅ Created comprehensive test suite with 21 test cases covering all functionality
- ✅ Requirements compatibility: Updated requirements.txt to use minimum versions (>=) instead of exact pins for better compatibility across Python environments
- ✅ All tests pass successfully

**Key Learnings**:
- Using minimum version requirements (>=) in requirements.txt provides better compatibility
- Comprehensive testing with dataclass validation prevents runtime errors
- State history tracking is valuable for debugging and metrics
- SimPy integration works well with object-oriented design

### Step 2.2: Berth Management Module (2 hours)
**Goal**: Create berth allocation and management system

**Actions**:
1. Create `src/core/berth_manager.py`:
   ```python
   """
   Berth Management System for Hong Kong Port Digital Twin
   
   This module handles berth allocation, availability tracking, and scheduling.
   Implements first-come-first-served allocation initially.
   """
   
   from dataclasses import dataclass
   from typing import List, Optional, Dict
   import simpy
   
   @dataclass
   class Berth:
       """Berth entity with capacity and status"""
       berth_id: int
       name: str
       max_capacity_teu: int
       crane_count: int
       berth_type: str
       is_occupied: bool = False
       current_ship: Optional[str] = None
       
   class BerthManager:
       """Manages berth allocation and utilization"""
       
       def __init__(self, env: simpy.Environment, berths_config: List[Dict]):
           self.env = env
           self.berths = {}
           self._initialize_berths(berths_config)
           
       def find_available_berth(self, ship_type: str, ship_size: int) -> Optional[int]:
           """Find suitable available berth for ship"""
           # Implementation...
           
       def allocate_berth(self, berth_id: int, ship_id: str) -> bool:
           """Allocate berth to ship"""
           # Implementation...
   ```

**Safety Notes**:
- Validate berth capacity before allocation
- Implement proper locking/resource management
- Keep allocation logic simple and predictable

**Step 2.2 Completion Notes** (✅ COMPLETED):
- Successfully implemented Berth dataclass with comprehensive validation
- Created BerthManager class with allocation, release, and scheduling logic
- Implemented berth type compatibility (container, bulk, mixed)
- Added statistics tracking and allocation history
- Created 25 comprehensive test cases with 100% pass rate
- Key learnings:
  - Import path issues in tests resolved with sys.path modification
  - Berth allocation algorithm prioritizes smaller suitable berths first
  - Mixed berths provide flexibility for different ship types
  - Statistics tracking essential for performance monitoring
  - Comprehensive validation prevents runtime errors

### Step 2.3: Container Handling Module (2 hours)
**Goal**: Simulate container loading/unloading operations

**Actions**:
1. Create `src/core/container_handler.py`:
   ```python
   """
   Container Handling System for Hong Kong Port Digital Twin
   
   This module simulates container loading/unloading operations,
   crane allocation, and processing time calculations.
   """
   
   import simpy
   from typing import Dict, List
   
   class ContainerHandler:
       """Handles container operations at berths"""
       
       def __init__(self, env: simpy.Environment):
           self.env = env
           self.processing_rates = {}  # TEU per hour by ship type
           
       def calculate_processing_time(self, ship_type: str, containers: int, crane_count: int) -> float:
           """Calculate time needed to process containers"""
           # Implementation...
           
       def process_ship(self, ship, berth):
           """Simulate container loading/unloading process"""
           # Implementation using simpy.timeout()
   ```

**Safety Notes**:
- Use realistic processing rates
- Handle edge cases (zero containers, equipment failures)
- Keep timing calculations simple and verifiable

---

## Phase 3: Simulation Integration (Week 3)

### Step 3.1: Main Simulation Engine (3 hours)
**Goal**: Integrate all components into working simulation

**Actions**:
1. Create `src/core/port_simulation.py`:
   ```python
   """
   Main Port Simulation Engine for Hong Kong Port Digital Twin
   
   This module orchestrates the entire port simulation using SimPy.
   It coordinates ships, berths, and container handling in discrete events.
   """
   
   import simpy
   from .ship_manager import ShipManager, Ship
   from .berth_manager import BerthManager
   from .container_handler import ContainerHandler
   
   class PortSimulation:
       """Main simulation controller"""
       
       def __init__(self, config: Dict):
           self.env = simpy.Environment()
           self.config = config
           self.ship_manager = ShipManager(self.env)
           self.berth_manager = BerthManager(self.env, config['berths'])
           self.container_handler = ContainerHandler(self.env)
           self.metrics = {}
           
       def run_simulation(self, duration: float):
           """Run simulation for specified duration"""
           # Implementation...
           
       def ship_arrival_process(self):
           """Generate ship arrivals over time"""
           # Implementation...
   ```

**Safety Notes**:
- Use dependency injection for all managers
- Implement proper error handling
- Keep simulation state isolated and resettable

### Step 3.2: Metrics Collection (1.5 hours)
**Goal**: Track key performance indicators

**Actions**:
1. Create `src/utils/metrics_collector.py`:
   ```python
   """
   Metrics Collection for Hong Kong Port Digital Twin
   
   This module tracks and calculates key performance indicators
   for port operations analysis.
   """
   
   from dataclasses import dataclass, field
   from typing import List, Dict
   import pandas as pd
   
   @dataclass
   class SimulationMetrics:
       """Container for all simulation metrics"""
       ship_waiting_times: List[float] = field(default_factory=list)
       berth_utilization: Dict[int, float] = field(default_factory=dict)
       container_throughput: List[int] = field(default_factory=list)
       queue_lengths: List[int] = field(default_factory=list)
       
   class MetricsCollector:
       """Collects and analyzes simulation metrics"""
       
       def __init__(self):
           self.metrics = SimulationMetrics()
           
       def record_ship_waiting_time(self, ship_id: str, waiting_time: float):
           """Record how long a ship waited for berth"""
           # Implementation...
   ```

### Step 3.3: Simulation Control (1.5 hours)
**Goal**: Add start/stop/reset functionality

**Actions**:
1. Create `src/core/simulation_controller.py`:
   ```python
   """
   Simulation Controller for Hong Kong Port Digital Twin
   
   This module provides high-level control over simulation execution,
   including start/stop/pause/reset functionality.
   """
   
   from enum import Enum
   import threading
   import time
   
   class SimulationState(Enum):
       STOPPED = "stopped"
       RUNNING = "running"
       PAUSED = "paused"
       COMPLETED = "completed"
   
   class SimulationController:
       """High-level simulation control"""
       
       def __init__(self, port_simulation):
           self.simulation = port_simulation
           self.state = SimulationState.STOPPED
           self.thread = None
           
       def start(self, duration: float):
           """Start simulation in separate thread"""
           # Implementation...
   ```

---

## Phase 4: Basic Dashboard (Week 4)

### Step 4.1: Visualization Utilities (2 hours)
**Goal**: Create reusable visualization functions

**Actions**:
1. Create `src/utils/visualization.py`:
   ```python
   """
   Visualization Utilities for Hong Kong Port Digital Twin
   
   This module provides reusable functions for creating charts and graphs
   to visualize port operations and simulation results.
   """
   
   import plotly.graph_objects as go
   import plotly.express as px
   import pandas as pd
   
   def create_port_layout_chart(berths_data: pd.DataFrame):
       """Create visual representation of port layout"""
       # Implementation...
       
   def create_ship_queue_chart(queue_data: List):
       """Visualize ship waiting queue"""
       # Implementation...
   ```

### Step 4.2: Streamlit Dashboard (3 hours)
**Goal**: Create interactive web interface

**Actions**:
1. Create `src/dashboard/streamlit_app.py`:
   ```python
   """
   Streamlit Dashboard for Hong Kong Port Digital Twin
   
   This is the main web interface for the port simulation.
   Users can control simulation parameters and view real-time results.
   """
   
   import streamlit as st
   import sys
   import os
   
   # Add src to path for imports
   sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
   
   from core.port_simulation import PortSimulation
   from utils.visualization import create_port_layout_chart
   
   def main():
       st.title("Hong Kong Port Digital Twin - MVP")
       
       # Sidebar controls
       st.sidebar.header("Simulation Controls")
       
       # Main dashboard
       col1, col2 = st.columns(2)
       
       with col1:
           st.subheader("Port Layout")
           # Port visualization
           
       with col2:
           st.subheader("Current Status")
           # Real-time metrics
   
   if __name__ == "__main__":
       main()
   ```

2. Create `run_demo.py` in project root:
   ```python
   """
   Demo Runner for Hong Kong Port Digital Twin
   
   This script launches the Streamlit dashboard for easy access.
   Run this file to start the demo.
   """
   
   import subprocess
   import sys
   import os
   
   def main():
       dashboard_path = os.path.join("src", "dashboard", "streamlit_app.py")
       subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])
   
   if __name__ == "__main__":
       main()
   ```

---

## Testing Strategy

### Unit Tests
Create tests for each module:
- `tests/test_ship_manager.py`
- `tests/test_berth_manager.py`
- `tests/test_container_handler.py`
- `tests/test_simulation.py`

### Integration Tests
- End-to-end simulation runs
- Data flow validation
- Performance benchmarks

### Manual Testing Checklist
- [ ] Ships arrive and queue properly
- [ ] Berths allocate correctly
- [ ] Container processing works
- [ ] Dashboard displays data
- [ ] Simulation can start/stop
- [ ] Metrics are collected

---

## Rollback Strategy

### Git Checkpoints
Commit after each major step:
1. "Phase 1 Complete: Project foundation"
2. "Phase 2 Complete: Core simulation engine"
3. "Phase 3 Complete: Simulation integration"
4. "Phase 4 Complete: Basic dashboard"

### Rollback Commands
```bash
# View commit history
git log --oneline

# Rollback to specific commit
git reset --hard <commit-hash>

# Create rollback branch
git checkout -b rollback-to-phase-2 <commit-hash>
```

### Safety Measures
- Keep original plan document untouched
- All new code in separate directory
- Use feature branches for experimental features
- Regular backups of working states

---

## Success Criteria for MVP

### Functional Requirements
- [ ] Ships arrive and process through berths
- [ ] Basic berth allocation works
- [ ] Container handling simulation runs
- [ ] Dashboard shows port status
- [ ] Simulation produces realistic metrics

### Technical Requirements
- [ ] Code is modular and well-documented
- [ ] All components have unit tests
- [ ] Easy to run demo (`python run_demo.py`)
- [ ] No external API dependencies for basic operation
- [ ] Clear separation between configuration and logic

### Quality Requirements
- [ ] Code follows Python best practices
- [ ] Comprehensive comments for junior developers
- [ ] Error handling for common failure cases
- [ ] Performance adequate for demo purposes
- [ ] Easy rollback to any previous state

---

## Next Steps After MVP

Once MVP is complete and tested:
1. Add real-time data integration (Week 5-6)
2. Implement AI optimization (Week 7-8)
3. Add advanced scenarios (Week 9)
4. Polish for production (Week 10)

---

## Notes for Junior Developers

### Key Concepts to Understand
- **Discrete Event Simulation**: Events happen at specific times
- **SimPy**: Python library for discrete event simulation
- **Streamlit**: Framework for creating web apps with Python
- **Modular Design**: Each component has a single responsibility

### Common Pitfalls to Avoid
- Don't modify existing files outside the project directory
- Always test components individually before integration
- Use configuration files instead of hardcoded values
- Keep functions small and focused
- Write tests as you develop, not after

### Getting Help
- Read the original plan document for context
- Check existing similar projects in the workspace
- Use print statements for debugging simulation flow
- Test with small datasets first
- Commit working code frequently

This plan provides a safe, step-by-step approach to building the Hong Kong Port Digital Twin MVP while maintaining the ability to rollback changes and ensuring code quality throughout the development process.
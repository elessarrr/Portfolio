"""Comments for context:
Berth Management System for Hong Kong Port Digital Twin

This module is part of Phase 2 (Core Simulation Engine) of the MVP implementation.
It handles berth allocation, availability tracking, and scheduling for the port simulation.

The system implements a first-come-first-served allocation strategy initially,
with proper validation for berth capacity and ship compatibility.

Key components:
- Berth dataclass: Represents individual berths with capacity and status
- BerthManager class: Manages all berth operations and allocation logic

This integrates with the ShipManager to provide complete port resource management.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set
from datetime import datetime
import simpy
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Berth:
    """Berth entity with capacity and operational status
    
    Represents a single berth in the port with all its characteristics
    and current operational state.
    """
    berth_id: int
    name: str
    max_capacity_teu: int
    crane_count: int
    berth_type: str  # 'container', 'bulk', 'mixed'
    is_occupied: bool = False
    current_ship: Optional[str] = None
    occupation_start_time: Optional[float] = None
    total_occupation_time: float = 0.0
    ships_served: int = 0
    
    def __post_init__(self):
        """Validate berth data after initialization"""
        if self.max_capacity_teu <= 0:
            raise ValueError(f"Berth {self.berth_id}: max_capacity_teu must be positive")
        if self.crane_count <= 0:
            raise ValueError(f"Berth {self.berth_id}: crane_count must be positive")
        if self.berth_type not in ['container', 'bulk', 'mixed']:
            raise ValueError(f"Berth {self.berth_id}: berth_type must be 'container', 'bulk', or 'mixed'")

class BerthManager:
    """Manages berth allocation and utilization for the port simulation
    
    This class handles:
    - Berth initialization from configuration
    - Finding available berths for ships
    - Allocating and releasing berths
    - Tracking berth utilization metrics
    - Validating ship-berth compatibility
    """
    
    def __init__(self, env: simpy.Environment, berths_config: List[Dict]):
        """Initialize the berth management system
        
        Args:
            env: SimPy environment for simulation
            berths_config: List of dictionaries containing berth configuration
        """
        self.env = env
        self.berths: Dict[int, Berth] = {}
        self.allocation_history: List[Dict] = []
        self._initialize_berths(berths_config)
        
        logger.info(f"BerthManager initialized with {len(self.berths)} berths")
    
    def _initialize_berths(self, berths_config: List[Dict]):
        """Initialize berths from configuration data
        
        Args:
            berths_config: List of berth configuration dictionaries
        """
        for config in berths_config:
            try:
                berth = Berth(
                    berth_id=config['berth_id'],
                    name=config['berth_name'],
                    max_capacity_teu=config['max_capacity_teu'],
                    crane_count=config['crane_count'],
                    berth_type=config['berth_type']
                )
                self.berths[berth.berth_id] = berth
                logger.info(f"Initialized berth {berth.berth_id}: {berth.name}")
            except (KeyError, ValueError) as e:
                logger.error(f"Failed to initialize berth from config {config}: {e}")
                raise
    
    def find_available_berth(self, ship_type: str, ship_size: int) -> Optional[int]:
        """Find the most suitable available berth for a ship
        
        Uses first-come-first-served with compatibility checking.
        Prioritizes berths by:
        1. Type compatibility (exact match preferred)
        2. Capacity efficiency (smallest suitable berth)
        3. Berth ID (for deterministic behavior)
        
        Args:
            ship_type: Type of ship ('container', 'bulk')
            ship_size: Size of ship in TEU
            
        Returns:
            Berth ID if suitable berth found, None otherwise
        """
        suitable_berths = []
        
        for berth in self.berths.values():
            if self._is_berth_suitable(berth, ship_type, ship_size):
                suitable_berths.append(berth)
        
        if not suitable_berths:
            logger.warning(f"No suitable berth found for {ship_type} ship of size {ship_size} TEU")
            return None
        
        # Sort by preference: exact type match, then by capacity efficiency, then by ID
        suitable_berths.sort(key=lambda b: (
            0 if b.berth_type == ship_type else 1,  # Exact type match first
            b.max_capacity_teu,  # Smaller capacity first (efficiency)
            b.berth_id  # Deterministic ordering
        ))
        
        selected_berth = suitable_berths[0]
        logger.info(f"Selected berth {selected_berth.berth_id} for {ship_type} ship of size {ship_size} TEU")
        return selected_berth.berth_id
    
    def _is_berth_suitable(self, berth: Berth, ship_type: str, ship_size: int) -> bool:
        """Check if a berth is suitable for a ship
        
        Args:
            berth: Berth to check
            ship_type: Type of ship
            ship_size: Size of ship in TEU
            
        Returns:
            True if berth is suitable, False otherwise
        """
        # Check if berth is available
        if berth.is_occupied:
            return False
        
        # Check capacity
        if ship_size > berth.max_capacity_teu:
            return False
        
        # Check type compatibility
        if berth.berth_type == 'mixed':
            return True  # Mixed berths can handle any ship type
        elif berth.berth_type == ship_type:
            return True  # Exact type match
        else:
            return False  # Type mismatch
    
    def allocate_berth(self, berth_id: int, ship_id: str) -> bool:
        """Allocate a berth to a ship
        
        Args:
            berth_id: ID of berth to allocate
            ship_id: ID of ship to allocate berth to
            
        Returns:
            True if allocation successful, False otherwise
        """
        if berth_id not in self.berths:
            logger.error(f"Berth {berth_id} does not exist")
            return False
        
        berth = self.berths[berth_id]
        
        if berth.is_occupied:
            logger.error(f"Berth {berth_id} is already occupied by ship {berth.current_ship}")
            return False
        
        # Allocate the berth
        berth.is_occupied = True
        berth.current_ship = ship_id
        berth.occupation_start_time = self.env.now
        
        # Record allocation in history
        self.allocation_history.append({
            'timestamp': self.env.now,
            'action': 'allocate',
            'berth_id': berth_id,
            'ship_id': ship_id
        })
        
        logger.info(f"Allocated berth {berth_id} to ship {ship_id} at time {self.env.now}")
        return True
    
    def release_berth(self, berth_id: int) -> bool:
        """Release a berth from its current ship
        
        Args:
            berth_id: ID of berth to release
            
        Returns:
            True if release successful, False otherwise
        """
        if berth_id not in self.berths:
            logger.error(f"Berth {berth_id} does not exist")
            return False
        
        berth = self.berths[berth_id]
        
        if not berth.is_occupied:
            logger.warning(f"Berth {berth_id} is not currently occupied")
            return False
        
        # Calculate occupation time
        if berth.occupation_start_time is not None:
            occupation_duration = self.env.now - berth.occupation_start_time
            berth.total_occupation_time += occupation_duration
        
        # Record release in history
        self.allocation_history.append({
            'timestamp': self.env.now,
            'action': 'release',
            'berth_id': berth_id,
            'ship_id': berth.current_ship
        })
        
        ship_id = berth.current_ship
        
        # Release the berth
        berth.is_occupied = False
        berth.current_ship = None
        berth.occupation_start_time = None
        berth.ships_served += 1
        
        logger.info(f"Released berth {berth_id} from ship {ship_id} at time {self.env.now}")
        return True
    
    def get_berth(self, berth_id: int) -> Optional[Berth]:
        """Get berth information by ID
        
        Args:
            berth_id: ID of berth to retrieve
            
        Returns:
            Berth object if found, None otherwise
        """
        return self.berths.get(berth_id)
    
    def get_available_berths(self) -> List[Berth]:
        """Get list of all available (unoccupied) berths
        
        Returns:
            List of available berth objects
        """
        return [berth for berth in self.berths.values() if not berth.is_occupied]
    
    def get_occupied_berths(self) -> List[Berth]:
        """Get list of all occupied berths
        
        Returns:
            List of occupied berth objects
        """
        return [berth for berth in self.berths.values() if berth.is_occupied]
    
    def get_berths_by_type(self, berth_type: str) -> List[Berth]:
        """Get berths filtered by type
        
        Args:
            berth_type: Type of berths to retrieve
            
        Returns:
            List of berths of specified type
        """
        return [berth for berth in self.berths.values() if berth.berth_type == berth_type]
    
    def get_berth_statistics(self) -> Dict:
        """Get comprehensive berth utilization statistics
        
        Returns:
            Dictionary containing various berth statistics
        """
        total_berths = len(self.berths)
        occupied_berths = len(self.get_occupied_berths())
        available_berths = total_berths - occupied_berths
        
        # Calculate utilization by type
        type_stats = {}
        for berth_type in ['container', 'bulk', 'mixed']:
            type_berths = self.get_berths_by_type(berth_type)
            type_occupied = sum(1 for b in type_berths if b.is_occupied)
            type_stats[berth_type] = {
                'total': len(type_berths),
                'occupied': type_occupied,
                'available': len(type_berths) - type_occupied,
                'utilization_rate': type_occupied / len(type_berths) if type_berths else 0
            }
        
        return {
            'total_berths': total_berths,
            'occupied_berths': occupied_berths,
            'available_berths': available_berths,
            'overall_utilization_rate': occupied_berths / total_berths if total_berths > 0 else 0,
            'by_type': type_stats,
            'total_ships_served': sum(berth.ships_served for berth in self.berths.values()),
            'allocation_history_length': len(self.allocation_history)
        }
    
    def get_allocation_history(self) -> List[Dict]:
        """Get the complete allocation history
        
        Returns:
            List of allocation/release events
        """
        return self.allocation_history.copy()
    
    def reset_statistics(self):
        """Reset all berth statistics and history
        
        Useful for starting fresh simulation runs
        """
        for berth in self.berths.values():
            berth.total_occupation_time = 0.0
            berth.ships_served = 0
        
        self.allocation_history.clear()
        logger.info("Berth statistics and history reset")
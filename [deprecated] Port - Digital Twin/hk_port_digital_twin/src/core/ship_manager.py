"""Ship Management System for Hong Kong Port Digital Twin

This module handles ship entities, their states, and queue management.
Ships progress through states: arriving -> waiting -> docking -> processing -> departing
"""

from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Dict
import simpy
from datetime import datetime


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
    actual_arrival_time: Optional[float] = None
    berth_assignment_time: Optional[float] = None
    processing_start_time: Optional[float] = None
    departure_time: Optional[float] = None
    
    def __post_init__(self):
        """Validate ship data after initialization"""
        if self.size_teu <= 0:
            raise ValueError(f"Ship {self.ship_id}: size_teu must be positive")
        if self.containers_to_unload < 0 or self.containers_to_load < 0:
            raise ValueError(f"Ship {self.ship_id}: container counts cannot be negative")
        if self.arrival_time < 0:
            raise ValueError(f"Ship {self.ship_id}: arrival_time cannot be negative")


class ShipManager:
    """Manages ship entities and their lifecycle"""
    
    def __init__(self, env: simpy.Environment):
        self.env = env
        self.ships: Dict[str, Ship] = {}
        self.waiting_queue: List[str] = []  # List of ship_ids waiting for berths
        self.state_history: List[Dict] = []  # Track state changes for metrics
        
    def add_ship(self, ship: Ship) -> bool:
        """Add a new ship to the system
        
        Args:
            ship: Ship object to add
            
        Returns:
            bool: True if ship was added successfully, False if ship_id already exists
        """
        if ship.ship_id in self.ships:
            return False
            
        # Set actual arrival time to current simulation time
        ship.actual_arrival_time = self.env.now
        
        # Add ship to system
        self.ships[ship.ship_id] = ship
        
        # Record state change
        self._record_state_change(ship.ship_id, ShipState.ARRIVING)
        
        # If ship arrives and needs to wait, add to queue
        if ship.state == ShipState.ARRIVING:
            self.update_ship_state(ship.ship_id, ShipState.WAITING)
            
        return True
    
    def update_ship_state(self, ship_id: str, new_state: ShipState) -> bool:
        """Update ship state and handle transitions
        
        Args:
            ship_id: ID of ship to update
            new_state: New state to transition to
            
        Returns:
            bool: True if state was updated successfully
        """
        if ship_id not in self.ships:
            return False
            
        ship = self.ships[ship_id]
        old_state = ship.state
        
        # Validate state transition
        if not self._is_valid_transition(old_state, new_state):
            raise ValueError(f"Invalid state transition for ship {ship_id}: {old_state.value} -> {new_state.value}")
        
        # Update ship state
        ship.state = new_state
        
        # Handle state-specific logic
        if new_state == ShipState.WAITING:
            if ship_id not in self.waiting_queue:
                self.waiting_queue.append(ship_id)
        elif new_state == ShipState.DOCKING:
            if ship_id in self.waiting_queue:
                self.waiting_queue.remove(ship_id)
            ship.berth_assignment_time = self.env.now
        elif new_state == ShipState.PROCESSING:
            ship.processing_start_time = self.env.now
        elif new_state == ShipState.DEPARTED:
            ship.departure_time = self.env.now
            
        # Record state change
        self._record_state_change(ship_id, new_state)
        
        return True
    
    def assign_berth(self, ship_id: str, berth_id: int) -> bool:
        """Assign a berth to a ship
        
        Args:
            ship_id: ID of ship to assign berth to
            berth_id: ID of berth to assign
            
        Returns:
            bool: True if berth was assigned successfully
        """
        if ship_id not in self.ships:
            return False
            
        ship = self.ships[ship_id]
        ship.assigned_berth = berth_id
        
        # Transition to docking state if currently waiting
        if ship.state == ShipState.WAITING:
            self.update_ship_state(ship_id, ShipState.DOCKING)
            
        return True
    
    def get_waiting_ships(self) -> List[Ship]:
        """Get list of ships currently waiting for berths
        
        Returns:
            List of Ship objects in waiting state
        """
        return [self.ships[ship_id] for ship_id in self.waiting_queue]
    
    def get_ship(self, ship_id: str) -> Optional[Ship]:
        """Get ship by ID
        
        Args:
            ship_id: ID of ship to retrieve
            
        Returns:
            Ship object if found, None otherwise
        """
        return self.ships.get(ship_id)
    
    def get_ships_by_state(self, state: ShipState) -> List[Ship]:
        """Get all ships in a specific state
        
        Args:
            state: State to filter by
            
        Returns:
            List of Ship objects in the specified state
        """
        return [ship for ship in self.ships.values() if ship.state == state]
    
    def get_queue_length(self) -> int:
        """Get current length of waiting queue
        
        Returns:
            Number of ships waiting for berths
        """
        return len(self.waiting_queue)
    
    def get_next_waiting_ship(self) -> Optional[Ship]:
        """Get the next ship in the waiting queue (FIFO)
        
        Returns:
            Ship object that has been waiting longest, None if queue is empty
        """
        if not self.waiting_queue:
            return None
        return self.ships[self.waiting_queue[0]]
    
    def remove_ship(self, ship_id: str) -> bool:
        """Remove ship from system (after departure)
        
        Args:
            ship_id: ID of ship to remove
            
        Returns:
            bool: True if ship was removed successfully
        """
        if ship_id not in self.ships:
            return False
            
        # Remove from waiting queue if present
        if ship_id in self.waiting_queue:
            self.waiting_queue.remove(ship_id)
            
        # Remove from ships dictionary
        del self.ships[ship_id]
        
        return True
    
    def get_ship_statistics(self) -> Dict:
        """Get statistics about ships in the system
        
        Returns:
            Dictionary with ship statistics
        """
        total_ships = len(self.ships)
        state_counts = {}
        
        for state in ShipState:
            state_counts[state.value] = len(self.get_ships_by_state(state))
            
        return {
            'total_ships': total_ships,
            'waiting_queue_length': self.get_queue_length(),
            'state_distribution': state_counts,
            'current_time': self.env.now
        }
    
    def _is_valid_transition(self, from_state: ShipState, to_state: ShipState) -> bool:
        """Check if state transition is valid
        
        Args:
            from_state: Current state
            to_state: Target state
            
        Returns:
            bool: True if transition is valid
        """
        valid_transitions = {
            ShipState.ARRIVING: [ShipState.WAITING],
            ShipState.WAITING: [ShipState.DOCKING],
            ShipState.DOCKING: [ShipState.PROCESSING],
            ShipState.PROCESSING: [ShipState.DEPARTING],
            ShipState.DEPARTING: [ShipState.DEPARTED],
            ShipState.DEPARTED: []  # Terminal state
        }
        
        return to_state in valid_transitions.get(from_state, [])
    
    def _record_state_change(self, ship_id: str, new_state: ShipState):
        """Record state change for metrics and debugging
        
        Args:
            ship_id: ID of ship that changed state
            new_state: New state of the ship
        """
        self.state_history.append({
            'timestamp': self.env.now,
            'ship_id': ship_id,
            'state': new_state.value
        })
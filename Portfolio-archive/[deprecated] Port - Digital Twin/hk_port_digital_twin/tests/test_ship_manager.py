"""Tests for Ship Management System

This module contains comprehensive tests for the ship_manager module,
including ship creation, state transitions, and queue management.
"""

import pytest
import simpy
from src.core.ship_manager import Ship, ShipManager, ShipState


class TestShip:
    """Test cases for Ship dataclass"""
    
    def test_ship_creation_valid(self):
        """Test creating a valid ship"""
        ship = Ship(
            ship_id="TEST001",
            name="Test Ship",
            ship_type="container",
            size_teu=10000,
            arrival_time=0.0,
            containers_to_unload=500,
            containers_to_load=300
        )
        
        assert ship.ship_id == "TEST001"
        assert ship.name == "Test Ship"
        assert ship.ship_type == "container"
        assert ship.size_teu == 10000
        assert ship.arrival_time == 0.0
        assert ship.containers_to_unload == 500
        assert ship.containers_to_load == 300
        assert ship.state == ShipState.ARRIVING
        assert ship.assigned_berth is None
    
    def test_ship_creation_invalid_size(self):
        """Test ship creation with invalid size"""
        with pytest.raises(ValueError, match="size_teu must be positive"):
            Ship(
                ship_id="TEST001",
                name="Test Ship",
                ship_type="container",
                size_teu=0,
                arrival_time=0.0,
                containers_to_unload=500,
                containers_to_load=300
            )
    
    def test_ship_creation_negative_containers(self):
        """Test ship creation with negative container counts"""
        with pytest.raises(ValueError, match="container counts cannot be negative"):
            Ship(
                ship_id="TEST001",
                name="Test Ship",
                ship_type="container",
                size_teu=10000,
                arrival_time=0.0,
                containers_to_unload=-1,
                containers_to_load=300
            )
    
    def test_ship_creation_negative_arrival_time(self):
        """Test ship creation with negative arrival time"""
        with pytest.raises(ValueError, match="arrival_time cannot be negative"):
            Ship(
                ship_id="TEST001",
                name="Test Ship",
                ship_type="container",
                size_teu=10000,
                arrival_time=-1.0,
                containers_to_unload=500,
                containers_to_load=300
            )


class TestShipManager:
    """Test cases for ShipManager class"""
    
    @pytest.fixture
    def env(self):
        """Create a SimPy environment for testing"""
        return simpy.Environment()
    
    @pytest.fixture
    def ship_manager(self, env):
        """Create a ShipManager instance for testing"""
        return ShipManager(env)
    
    @pytest.fixture
    def sample_ship(self):
        """Create a sample ship for testing"""
        return Ship(
            ship_id="TEST001",
            name="Test Ship",
            ship_type="container",
            size_teu=10000,
            arrival_time=0.0,
            containers_to_unload=500,
            containers_to_load=300
        )
    
    def test_ship_manager_initialization(self, ship_manager):
        """Test ShipManager initialization"""
        assert len(ship_manager.ships) == 0
        assert len(ship_manager.waiting_queue) == 0
        assert len(ship_manager.state_history) == 0
    
    def test_add_ship_success(self, ship_manager, sample_ship):
        """Test successfully adding a ship"""
        result = ship_manager.add_ship(sample_ship)
        
        assert result is True
        assert sample_ship.ship_id in ship_manager.ships
        assert sample_ship.state == ShipState.WAITING
        assert sample_ship.ship_id in ship_manager.waiting_queue
        assert sample_ship.actual_arrival_time == ship_manager.env.now
    
    def test_add_ship_duplicate_id(self, ship_manager, sample_ship):
        """Test adding ship with duplicate ID"""
        ship_manager.add_ship(sample_ship)
        
        # Try to add another ship with same ID
        duplicate_ship = Ship(
            ship_id="TEST001",
            name="Duplicate Ship",
            ship_type="bulk",
            size_teu=5000,
            arrival_time=1.0,
            containers_to_unload=0,
            containers_to_load=200
        )
        
        result = ship_manager.add_ship(duplicate_ship)
        assert result is False
        assert len(ship_manager.ships) == 1
    
    def test_update_ship_state_valid_transition(self, ship_manager, sample_ship):
        """Test valid state transition"""
        ship_manager.add_ship(sample_ship)
        
        # Ship should be in WAITING state after adding
        assert sample_ship.state == ShipState.WAITING
        
        # Transition to DOCKING
        result = ship_manager.update_ship_state(sample_ship.ship_id, ShipState.DOCKING)
        assert result is True
        assert sample_ship.state == ShipState.DOCKING
        assert sample_ship.ship_id not in ship_manager.waiting_queue
        assert sample_ship.berth_assignment_time == ship_manager.env.now
    
    def test_update_ship_state_invalid_transition(self, ship_manager, sample_ship):
        """Test invalid state transition"""
        ship_manager.add_ship(sample_ship)
        
        # Try invalid transition from WAITING to PROCESSING
        with pytest.raises(ValueError, match="Invalid state transition"):
            ship_manager.update_ship_state(sample_ship.ship_id, ShipState.PROCESSING)
    
    def test_update_ship_state_nonexistent_ship(self, ship_manager):
        """Test updating state of non-existent ship"""
        result = ship_manager.update_ship_state("NONEXISTENT", ShipState.WAITING)
        assert result is False
    
    def test_assign_berth(self, ship_manager, sample_ship):
        """Test berth assignment"""
        ship_manager.add_ship(sample_ship)
        
        result = ship_manager.assign_berth(sample_ship.ship_id, 1)
        assert result is True
        assert sample_ship.assigned_berth == 1
        assert sample_ship.state == ShipState.DOCKING
    
    def test_assign_berth_nonexistent_ship(self, ship_manager):
        """Test assigning berth to non-existent ship"""
        result = ship_manager.assign_berth("NONEXISTENT", 1)
        assert result is False
    
    def test_get_waiting_ships(self, ship_manager):
        """Test getting waiting ships"""
        # Add multiple ships
        ship1 = Ship("SHIP001", "Ship 1", "container", 10000, 0.0, 500, 300)
        ship2 = Ship("SHIP002", "Ship 2", "container", 8000, 1.0, 400, 200)
        ship3 = Ship("SHIP003", "Ship 3", "bulk", 15000, 2.0, 0, 600)
        
        ship_manager.add_ship(ship1)
        ship_manager.add_ship(ship2)
        ship_manager.add_ship(ship3)
        
        # All should be waiting initially
        waiting_ships = ship_manager.get_waiting_ships()
        assert len(waiting_ships) == 3
        
        # Assign berth to one ship
        ship_manager.assign_berth(ship1.ship_id, 1)
        
        # Should have 2 waiting ships now
        waiting_ships = ship_manager.get_waiting_ships()
        assert len(waiting_ships) == 2
        assert ship1 not in waiting_ships
    
    def test_get_ship(self, ship_manager, sample_ship):
        """Test getting ship by ID"""
        ship_manager.add_ship(sample_ship)
        
        retrieved_ship = ship_manager.get_ship(sample_ship.ship_id)
        assert retrieved_ship == sample_ship
        
        nonexistent_ship = ship_manager.get_ship("NONEXISTENT")
        assert nonexistent_ship is None
    
    def test_get_ships_by_state(self, ship_manager):
        """Test getting ships by state"""
        ship1 = Ship("SHIP001", "Ship 1", "container", 10000, 0.0, 500, 300)
        ship2 = Ship("SHIP002", "Ship 2", "container", 8000, 1.0, 400, 200)
        
        ship_manager.add_ship(ship1)
        ship_manager.add_ship(ship2)
        
        # Both should be waiting
        waiting_ships = ship_manager.get_ships_by_state(ShipState.WAITING)
        assert len(waiting_ships) == 2
        
        # Move one to docking
        ship_manager.assign_berth(ship1.ship_id, 1)
        
        waiting_ships = ship_manager.get_ships_by_state(ShipState.WAITING)
        docking_ships = ship_manager.get_ships_by_state(ShipState.DOCKING)
        
        assert len(waiting_ships) == 1
        assert len(docking_ships) == 1
        assert ship2 in waiting_ships
        assert ship1 in docking_ships
    
    def test_get_queue_length(self, ship_manager):
        """Test getting queue length"""
        assert ship_manager.get_queue_length() == 0
        
        ship1 = Ship("SHIP001", "Ship 1", "container", 10000, 0.0, 500, 300)
        ship2 = Ship("SHIP002", "Ship 2", "container", 8000, 1.0, 400, 200)
        
        ship_manager.add_ship(ship1)
        assert ship_manager.get_queue_length() == 1
        
        ship_manager.add_ship(ship2)
        assert ship_manager.get_queue_length() == 2
        
        ship_manager.assign_berth(ship1.ship_id, 1)
        assert ship_manager.get_queue_length() == 1
    
    def test_get_next_waiting_ship(self, ship_manager):
        """Test getting next waiting ship (FIFO)"""
        assert ship_manager.get_next_waiting_ship() is None
        
        ship1 = Ship("SHIP001", "Ship 1", "container", 10000, 0.0, 500, 300)
        ship2 = Ship("SHIP002", "Ship 2", "container", 8000, 1.0, 400, 200)
        
        ship_manager.add_ship(ship1)
        ship_manager.add_ship(ship2)
        
        # First ship added should be first in queue
        next_ship = ship_manager.get_next_waiting_ship()
        assert next_ship == ship1
        
        # Assign berth to first ship
        ship_manager.assign_berth(ship1.ship_id, 1)
        
        # Second ship should now be next
        next_ship = ship_manager.get_next_waiting_ship()
        assert next_ship == ship2
    
    def test_remove_ship(self, ship_manager, sample_ship):
        """Test removing ship from system"""
        ship_manager.add_ship(sample_ship)
        assert sample_ship.ship_id in ship_manager.ships
        assert sample_ship.ship_id in ship_manager.waiting_queue
        
        result = ship_manager.remove_ship(sample_ship.ship_id)
        assert result is True
        assert sample_ship.ship_id not in ship_manager.ships
        assert sample_ship.ship_id not in ship_manager.waiting_queue
        
        # Try to remove non-existent ship
        result = ship_manager.remove_ship("NONEXISTENT")
        assert result is False
    
    def test_get_ship_statistics(self, ship_manager):
        """Test getting ship statistics"""
        stats = ship_manager.get_ship_statistics()
        assert stats['total_ships'] == 0
        assert stats['waiting_queue_length'] == 0
        assert stats['current_time'] == ship_manager.env.now
        
        # Add ships in different states
        ship1 = Ship("SHIP001", "Ship 1", "container", 10000, 0.0, 500, 300)
        ship2 = Ship("SHIP002", "Ship 2", "container", 8000, 1.0, 400, 200)
        
        ship_manager.add_ship(ship1)
        ship_manager.add_ship(ship2)
        ship_manager.assign_berth(ship1.ship_id, 1)
        
        stats = ship_manager.get_ship_statistics()
        assert stats['total_ships'] == 2
        assert stats['waiting_queue_length'] == 1
        assert stats['state_distribution']['waiting'] == 1
        assert stats['state_distribution']['docking'] == 1
    
    def test_state_transition_sequence(self, ship_manager, sample_ship):
        """Test complete state transition sequence"""
        ship_manager.add_ship(sample_ship)
        
        # Should start in WAITING after adding
        assert sample_ship.state == ShipState.WAITING
        
        # Transition through all states
        ship_manager.update_ship_state(sample_ship.ship_id, ShipState.DOCKING)
        assert sample_ship.state == ShipState.DOCKING
        
        ship_manager.update_ship_state(sample_ship.ship_id, ShipState.PROCESSING)
        assert sample_ship.state == ShipState.PROCESSING
        assert sample_ship.processing_start_time == ship_manager.env.now
        
        ship_manager.update_ship_state(sample_ship.ship_id, ShipState.DEPARTING)
        assert sample_ship.state == ShipState.DEPARTING
        
        ship_manager.update_ship_state(sample_ship.ship_id, ShipState.DEPARTED)
        assert sample_ship.state == ShipState.DEPARTED
        assert sample_ship.departure_time == ship_manager.env.now
    
    def test_state_history_recording(self, ship_manager, sample_ship):
        """Test that state changes are recorded in history"""
        ship_manager.add_ship(sample_ship)
        
        # Should have recorded ARRIVING and WAITING states
        assert len(ship_manager.state_history) >= 2
        
        # Check that history contains expected entries
        arriving_entry = next((entry for entry in ship_manager.state_history 
                              if entry['ship_id'] == sample_ship.ship_id and entry['state'] == 'arriving'), None)
        waiting_entry = next((entry for entry in ship_manager.state_history 
                             if entry['ship_id'] == sample_ship.ship_id and entry['state'] == 'waiting'), None)
        
        assert arriving_entry is not None
        assert waiting_entry is not None
        assert arriving_entry['timestamp'] == ship_manager.env.now
        assert waiting_entry['timestamp'] == ship_manager.env.now
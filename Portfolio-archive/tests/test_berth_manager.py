"""Tests for the Berth Management System

This module contains comprehensive tests for the berth_manager module,
covering all functionality including berth initialization, allocation,
release, statistics, and edge cases.

Follows Test Driven Development (TDD) principles to ensure robust
berth management functionality.
"""

import pytest
import simpy
import sys
import os
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.berth_manager import Berth, BerthManager

class TestBerth:
    """Test cases for the Berth dataclass"""
    
    def test_berth_creation_valid(self):
        """Test creating a valid berth"""
        berth = Berth(
            berth_id=1,
            name="Test Berth",
            max_capacity_teu=20000,
            crane_count=4,
            berth_type="container"
        )
        
        assert berth.berth_id == 1
        assert berth.name == "Test Berth"
        assert berth.max_capacity_teu == 20000
        assert berth.crane_count == 4
        assert berth.berth_type == "container"
        assert berth.is_occupied == False
        assert berth.current_ship is None
        assert berth.occupation_start_time is None
        assert berth.total_occupation_time == 0.0
        assert berth.ships_served == 0
    
    def test_berth_creation_invalid_capacity(self):
        """Test berth creation with invalid capacity"""
        with pytest.raises(ValueError, match="max_capacity_teu must be positive"):
            Berth(
                berth_id=1,
                name="Test Berth",
                max_capacity_teu=0,
                crane_count=4,
                berth_type="container"
            )
    
    def test_berth_creation_invalid_crane_count(self):
        """Test berth creation with invalid crane count"""
        with pytest.raises(ValueError, match="crane_count must be positive"):
            Berth(
                berth_id=1,
                name="Test Berth",
                max_capacity_teu=20000,
                crane_count=0,
                berth_type="container"
            )
    
    def test_berth_creation_invalid_type(self):
        """Test berth creation with invalid berth type"""
        with pytest.raises(ValueError, match="berth_type must be"):
            Berth(
                berth_id=1,
                name="Test Berth",
                max_capacity_teu=20000,
                crane_count=4,
                berth_type="invalid_type"
            )

class TestBerthManager:
    """Test cases for the BerthManager class"""
    
    @pytest.fixture
    def env(self):
        """Create a SimPy environment for testing"""
        return simpy.Environment()
    
    @pytest.fixture
    def sample_berths_config(self):
        """Sample berth configuration for testing"""
        return [
            {
                'berth_id': 1,
                'berth_name': 'Berth_A1',
                'max_capacity_teu': 20000,
                'crane_count': 4,
                'berth_type': 'container'
            },
            {
                'berth_id': 2,
                'berth_name': 'Berth_A2',
                'max_capacity_teu': 18000,
                'crane_count': 3,
                'berth_type': 'container'
            },
            {
                'berth_id': 3,
                'berth_name': 'Berth_B1',
                'max_capacity_teu': 30000,
                'crane_count': 2,
                'berth_type': 'bulk'
            },
            {
                'berth_id': 4,
                'berth_name': 'Berth_C1',
                'max_capacity_teu': 25000,
                'crane_count': 3,
                'berth_type': 'mixed'
            }
        ]
    
    def test_berth_manager_initialization(self, env, sample_berths_config):
        """Test BerthManager initialization"""
        manager = BerthManager(env, sample_berths_config)
        
        assert len(manager.berths) == 4
        assert 1 in manager.berths
        assert 2 in manager.berths
        assert 3 in manager.berths
        assert 4 in manager.berths
        assert len(manager.allocation_history) == 0
    
    def test_berth_manager_initialization_invalid_config(self, env):
        """Test BerthManager initialization with invalid config"""
        invalid_config = [
            {
                'berth_id': 1,
                'berth_name': 'Berth_A1',
                # Missing required fields
            }
        ]
        
        with pytest.raises(KeyError):
            BerthManager(env, invalid_config)
    
    def test_find_available_berth_container_ship(self, env, sample_berths_config):
        """Test finding available berth for container ship"""
        manager = BerthManager(env, sample_berths_config)
        
        # Should find the smaller container berth first (berth 2)
        berth_id = manager.find_available_berth('container', 15000)
        assert berth_id == 2  # Smaller capacity berth preferred
    
    def test_find_available_berth_bulk_ship(self, env, sample_berths_config):
        """Test finding available berth for bulk ship"""
        manager = BerthManager(env, sample_berths_config)
        
        berth_id = manager.find_available_berth('bulk', 25000)
        assert berth_id == 3  # Only bulk berth
    
    def test_find_available_berth_mixed_compatibility(self, env, sample_berths_config):
        """Test that mixed berths can handle any ship type"""
        manager = BerthManager(env, sample_berths_config)
        
        # Occupy all container berths
        manager.allocate_berth(1, 'ship1')
        manager.allocate_berth(2, 'ship2')
        
        # Container ship should be able to use mixed berth
        berth_id = manager.find_available_berth('container', 20000)
        assert berth_id == 4  # Mixed berth
    
    def test_find_available_berth_no_suitable_berth(self, env, sample_berths_config):
        """Test when no suitable berth is available"""
        manager = BerthManager(env, sample_berths_config)
        
        # Ship too large for any berth
        berth_id = manager.find_available_berth('container', 50000)
        assert berth_id is None
    
    def test_find_available_berth_all_occupied(self, env, sample_berths_config):
        """Test when all suitable berths are occupied"""
        manager = BerthManager(env, sample_berths_config)
        
        # Occupy all container and mixed berths
        manager.allocate_berth(1, 'ship1')
        manager.allocate_berth(2, 'ship2')
        manager.allocate_berth(4, 'ship3')
        
        # No berth available for container ship
        berth_id = manager.find_available_berth('container', 15000)
        assert berth_id is None
    
    def test_allocate_berth_success(self, env, sample_berths_config):
        """Test successful berth allocation"""
        manager = BerthManager(env, sample_berths_config)
        
        result = manager.allocate_berth(1, 'ship123')
        assert result == True
        
        berth = manager.get_berth(1)
        assert berth.is_occupied == True
        assert berth.current_ship == 'ship123'
        assert berth.occupation_start_time == env.now
        assert len(manager.allocation_history) == 1
    
    def test_allocate_berth_nonexistent(self, env, sample_berths_config):
        """Test allocating nonexistent berth"""
        manager = BerthManager(env, sample_berths_config)
        
        result = manager.allocate_berth(999, 'ship123')
        assert result == False
    
    def test_allocate_berth_already_occupied(self, env, sample_berths_config):
        """Test allocating already occupied berth"""
        manager = BerthManager(env, sample_berths_config)
        
        # First allocation should succeed
        result1 = manager.allocate_berth(1, 'ship123')
        assert result1 == True
        
        # Second allocation should fail
        result2 = manager.allocate_berth(1, 'ship456')
        assert result2 == False
    
    def test_release_berth_success(self, env, sample_berths_config):
        """Test successful berth release"""
        manager = BerthManager(env, sample_berths_config)
        
        # Allocate first
        manager.allocate_berth(1, 'ship123')
        
        # Advance time
        env.run(until=10)
        
        # Release
        result = manager.release_berth(1)
        assert result == True
        
        berth = manager.get_berth(1)
        assert berth.is_occupied == False
        assert berth.current_ship is None
        assert berth.occupation_start_time is None
        assert berth.ships_served == 1
        assert berth.total_occupation_time == 10
        assert len(manager.allocation_history) == 2
    
    def test_release_berth_nonexistent(self, env, sample_berths_config):
        """Test releasing nonexistent berth"""
        manager = BerthManager(env, sample_berths_config)
        
        result = manager.release_berth(999)
        assert result == False
    
    def test_release_berth_not_occupied(self, env, sample_berths_config):
        """Test releasing berth that's not occupied"""
        manager = BerthManager(env, sample_berths_config)
        
        result = manager.release_berth(1)
        assert result == False
    
    def test_get_berth(self, env, sample_berths_config):
        """Test getting berth information"""
        manager = BerthManager(env, sample_berths_config)
        
        berth = manager.get_berth(1)
        assert berth is not None
        assert berth.berth_id == 1
        assert berth.name == 'Berth_A1'
        
        # Test nonexistent berth
        berth = manager.get_berth(999)
        assert berth is None
    
    def test_get_available_berths(self, env, sample_berths_config):
        """Test getting available berths"""
        manager = BerthManager(env, sample_berths_config)
        
        # Initially all berths should be available
        available = manager.get_available_berths()
        assert len(available) == 4
        
        # Occupy one berth
        manager.allocate_berth(1, 'ship123')
        available = manager.get_available_berths()
        assert len(available) == 3
        assert all(not berth.is_occupied for berth in available)
    
    def test_get_occupied_berths(self, env, sample_berths_config):
        """Test getting occupied berths"""
        manager = BerthManager(env, sample_berths_config)
        
        # Initially no berths should be occupied
        occupied = manager.get_occupied_berths()
        assert len(occupied) == 0
        
        # Occupy one berth
        manager.allocate_berth(1, 'ship123')
        occupied = manager.get_occupied_berths()
        assert len(occupied) == 1
        assert all(berth.is_occupied for berth in occupied)
    
    def test_get_berths_by_type(self, env, sample_berths_config):
        """Test getting berths by type"""
        manager = BerthManager(env, sample_berths_config)
        
        container_berths = manager.get_berths_by_type('container')
        assert len(container_berths) == 2
        assert all(berth.berth_type == 'container' for berth in container_berths)
        
        bulk_berths = manager.get_berths_by_type('bulk')
        assert len(bulk_berths) == 1
        assert all(berth.berth_type == 'bulk' for berth in bulk_berths)
        
        mixed_berths = manager.get_berths_by_type('mixed')
        assert len(mixed_berths) == 1
        assert all(berth.berth_type == 'mixed' for berth in mixed_berths)
    
    def test_get_berth_statistics(self, env, sample_berths_config):
        """Test berth statistics calculation"""
        manager = BerthManager(env, sample_berths_config)
        
        # Initial statistics
        stats = manager.get_berth_statistics()
        assert stats['total_berths'] == 4
        assert stats['occupied_berths'] == 0
        assert stats['available_berths'] == 4
        assert stats['overall_utilization_rate'] == 0.0
        assert stats['total_ships_served'] == 0
        
        # Occupy some berths
        manager.allocate_berth(1, 'ship1')
        manager.allocate_berth(3, 'ship2')
        
        stats = manager.get_berth_statistics()
        assert stats['total_berths'] == 4
        assert stats['occupied_berths'] == 2
        assert stats['available_berths'] == 2
        assert stats['overall_utilization_rate'] == 0.5
        
        # Check type-specific statistics
        assert stats['by_type']['container']['occupied'] == 1
        assert stats['by_type']['bulk']['occupied'] == 1
        assert stats['by_type']['mixed']['occupied'] == 0
    
    def test_get_allocation_history(self, env, sample_berths_config):
        """Test allocation history tracking"""
        manager = BerthManager(env, sample_berths_config)
        
        # Initially empty
        history = manager.get_allocation_history()
        assert len(history) == 0
        
        # Allocate and release
        manager.allocate_berth(1, 'ship123')
        env.run(until=5)
        manager.release_berth(1)
        
        history = manager.get_allocation_history()
        assert len(history) == 2
        assert history[0]['action'] == 'allocate'
        assert history[0]['berth_id'] == 1
        assert history[0]['ship_id'] == 'ship123'
        assert history[1]['action'] == 'release'
        assert history[1]['berth_id'] == 1
        assert history[1]['ship_id'] == 'ship123'
    
    def test_reset_statistics(self, env, sample_berths_config):
        """Test resetting berth statistics"""
        manager = BerthManager(env, sample_berths_config)
        
        # Create some activity
        manager.allocate_berth(1, 'ship123')
        env.run(until=10)
        manager.release_berth(1)
        
        # Verify statistics exist
        berth = manager.get_berth(1)
        assert berth.ships_served == 1
        assert berth.total_occupation_time == 10
        assert len(manager.allocation_history) == 2
        
        # Reset statistics
        manager.reset_statistics()
        
        # Verify reset
        assert berth.ships_served == 0
        assert berth.total_occupation_time == 0
        assert len(manager.allocation_history) == 0
    
    def test_berth_allocation_sequence(self, env, sample_berths_config):
        """Test complete berth allocation and release sequence"""
        manager = BerthManager(env, sample_berths_config)
        
        # Find and allocate berth
        berth_id = manager.find_available_berth('container', 15000)
        assert berth_id is not None
        
        success = manager.allocate_berth(berth_id, 'ship123')
        assert success == True
        
        # Verify allocation
        berth = manager.get_berth(berth_id)
        assert berth.is_occupied == True
        assert berth.current_ship == 'ship123'
        
        # Simulate processing time
        env.run(until=20)
        
        # Release berth
        success = manager.release_berth(berth_id)
        assert success == True
        
        # Verify release
        assert berth.is_occupied == False
        assert berth.current_ship is None
        assert berth.ships_served == 1
        assert berth.total_occupation_time == 20
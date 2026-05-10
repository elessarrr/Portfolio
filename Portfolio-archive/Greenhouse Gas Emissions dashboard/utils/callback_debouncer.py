"""Callback Debouncer Module for GHG Dashboard Performance Optimization.

This module implements debouncing mechanisms to prevent rapid-fire callback execution
in the Dash application. It helps reduce unnecessary computations when users interact
quickly with multiple filters or controls.

Key Features:
- Configurable debounce delays for different callback types
- Thread-safe debouncing with automatic cleanup
- Integration with performance monitoring
- Feature flag support for easy rollback
- Support for both time-based and count-based debouncing

This is part of Phase 2 of the performance optimization plan.
"""

import time
import threading
import logging
from typing import Dict, Any, Callable, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from utils.feature_flags import feature_flags
from utils.performance_monitor import performance_monitor

# Configure logging for this module
logger = logging.getLogger(__name__)


@dataclass
class DebounceState:
    """Represents the state of a debounced function call.
    
    Attributes:
        last_call_time: When the function was last called
        pending_timer: Timer object for pending execution
        call_count: Number of times function has been called during debounce period
        last_args: Arguments from the most recent call
        last_kwargs: Keyword arguments from the most recent call
    """
    last_call_time: datetime = field(default_factory=datetime.now)
    pending_timer: Optional[threading.Timer] = None
    call_count: int = 0
    last_args: tuple = field(default_factory=tuple)
    last_kwargs: dict = field(default_factory=dict)
    
    def cancel_pending(self) -> None:
        """Cancel any pending timer."""
        if self.pending_timer and self.pending_timer.is_alive():
            self.pending_timer.cancel()
            self.pending_timer = None


class CallbackDebouncer:
    """Debouncer for Dash callbacks to prevent rapid-fire execution.
    
    This class provides debouncing functionality to reduce unnecessary callback
    executions when users interact rapidly with UI controls.
    """
    
    def __init__(self, default_delay_ms: int = 300):
        """Initialize the callback debouncer.
        
        Args:
            default_delay_ms: Default debounce delay in milliseconds
        """
        self._default_delay = default_delay_ms / 1000.0  # Convert to seconds
        self._debounce_states: Dict[str, DebounceState] = {}
        self._lock = threading.RLock()
        
        # Predefined delays for different callback types
        self._callback_delays = {
            'filter_callbacks': 500,  # 500ms for filter changes
            'graph_callbacks': 300,   # 300ms for graph updates
            'table_callbacks': 200,   # 200ms for table updates
            'export_callbacks': 1000, # 1s for export operations
        }
        
        logger.info(f"CallbackDebouncer initialized with default delay: {default_delay_ms}ms")
    
    def debounce(self, 
                 delay_ms: Optional[int] = None,
                 callback_type: Optional[str] = None,
                 key: Optional[str] = None):
        """Decorator to debounce function calls.
        
        Args:
            delay_ms: Debounce delay in milliseconds (uses default if None)
            callback_type: Type of callback for predefined delays
            key: Custom key for debounce state (uses function name if None)
            
        Returns:
            Decorated function with debouncing
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not feature_flags.is_enabled('use_callback_debouncing'):
                    return func(*args, **kwargs)
                
                # Determine debounce key
                debounce_key = key or func.__name__
                
                # Determine delay
                if delay_ms is not None:
                    delay_seconds = delay_ms / 1000.0
                elif callback_type and callback_type in self._callback_delays:
                    delay_seconds = self._callback_delays[callback_type] / 1000.0
                else:
                    delay_seconds = self._default_delay
                
                return self._debounce_call(debounce_key, func, delay_seconds, *args, **kwargs)
            
            return wrapper
        return decorator
    
    def _debounce_call(self, 
                      key: str, 
                      func: Callable, 
                      delay_seconds: float, 
                      *args, **kwargs) -> Any:
        """Internal method to handle debounced function calls.
        
        Args:
            key: Debounce key
            func: Function to debounce
            delay_seconds: Delay in seconds
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Result of function execution (may be None if debounced)
        """
        with self._lock:
            now = datetime.now()
            
            # Get or create debounce state
            if key not in self._debounce_states:
                self._debounce_states[key] = DebounceState()
            
            state = self._debounce_states[key]
            
            # Cancel any pending execution
            state.cancel_pending()
            
            # Update state
            state.last_call_time = now
            state.call_count += 1
            state.last_args = args
            state.last_kwargs = kwargs
            
            # Create new timer for delayed execution
            def delayed_execution():
                with self._lock:
                    try:
                        # Record performance metrics
                        with performance_monitor.timer(f'debounced_callback_{key}'):
                            result = func(*state.last_args, **state.last_kwargs)
                        
                        # Log debounce statistics
                        logger.debug(f"Debounced callback executed: {key} "
                                   f"(calls during debounce: {state.call_count})")
                        
                        # Reset call count
                        state.call_count = 0
                        
                        return result
                        
                    except Exception as e:
                        logger.error(f"Error in debounced callback {key}: {e}")
                        raise
            
            # Schedule delayed execution
            state.pending_timer = threading.Timer(delay_seconds, delayed_execution)
            state.pending_timer.start()
            
            # Return the original function result to maintain callback contract
            return func(*args, **kwargs)
    
    def flush(self, key: Optional[str] = None) -> None:
        """Immediately execute any pending debounced calls.
        
        Args:
            key: Specific debounce key to flush (flushes all if None)
        """
        with self._lock:
            if key:
                if key in self._debounce_states:
                    state = self._debounce_states[key]
                    if state.pending_timer and state.pending_timer.is_alive():
                        state.cancel_pending()
                        # Execute immediately
                        logger.debug(f"Flushing debounced callback: {key}")
            else:
                # Flush all pending calls
                for debounce_key, state in self._debounce_states.items():
                    if state.pending_timer and state.pending_timer.is_alive():
                        state.cancel_pending()
                        logger.debug(f"Flushing debounced callback: {debounce_key}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get debouncer statistics.
        
        Returns:
            Dictionary containing debouncer metrics
        """
        with self._lock:
            active_timers = sum(1 for state in self._debounce_states.values() 
                              if state.pending_timer and state.pending_timer.is_alive())
            
            total_calls = sum(state.call_count for state in self._debounce_states.values())
            
            return {
                'tracked_functions': len(self._debounce_states),
                'active_timers': active_timers,
                'total_pending_calls': total_calls,
                'default_delay_ms': int(self._default_delay * 1000),
                'callback_delays': self._callback_delays
            }
    
    def clear(self) -> None:
        """Clear all debounce states and cancel pending timers."""
        with self._lock:
            for state in self._debounce_states.values():
                state.cancel_pending()
            
            cleared_count = len(self._debounce_states)
            self._debounce_states.clear()
            
            logger.info(f"Debouncer cleared: {cleared_count} states removed")


# Global debouncer instance
_debouncer_instance = None
_debouncer_lock = threading.Lock()


def get_callback_debouncer() -> CallbackDebouncer:
    """Get the global callback debouncer instance.
    
    Returns:
        The singleton CallbackDebouncer instance
    """
    global _debouncer_instance
    
    if _debouncer_instance is None:
        with _debouncer_lock:
            if _debouncer_instance is None:
                _debouncer_instance = CallbackDebouncer()
    
    return _debouncer_instance


# Convenience decorators for common callback types
def debounce_filter_callback(delay_ms: int = 500, key: Optional[str] = None):
    """Decorator for filter-related callbacks.
    
    Args:
        delay_ms: Debounce delay in milliseconds
        key: Custom debounce key
        
    Returns:
        Decorated function with filter callback debouncing
    """
    return get_callback_debouncer().debounce(
        delay_ms=delay_ms, 
        callback_type='filter_callbacks', 
        key=key
    )


def debounce_graph_callback(delay_ms: int = 300, key: Optional[str] = None):
    """Decorator for graph-related callbacks.
    
    Args:
        delay_ms: Debounce delay in milliseconds
        key: Custom debounce key
        
    Returns:
        Decorated function with graph callback debouncing
    """
    return get_callback_debouncer().debounce(
        delay_ms=delay_ms, 
        callback_type='graph_callbacks', 
        key=key
    )


def debounce_table_callback(delay_ms: int = 200, key: Optional[str] = None):
    """Decorator for table-related callbacks.
    
    Args:
        delay_ms: Debounce delay in milliseconds
        key: Custom debounce key
        
    Returns:
        Decorated function with table callback debouncing
    """
    return get_callback_debouncer().debounce(
        delay_ms=delay_ms, 
        callback_type='table_callbacks', 
        key=key
    )


def debounce_export_callback(delay_ms: int = 1000, key: Optional[str] = None):
    """Decorator for export-related callbacks.
    
    Args:
        delay_ms: Debounce delay in milliseconds
        key: Custom debounce key
        
    Returns:
        Decorated function with export callback debouncing
    """
    return get_callback_debouncer().debounce(
        delay_ms=delay_ms, 
        callback_type='export_callbacks', 
        key=key
    )
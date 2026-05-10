"""Performance monitoring utilities for the GHG Dashboard.

This module provides comprehensive performance monitoring capabilities including:
- Memory usage tracking
- Execution time measurement
- Data loading performance metrics
- Component rendering performance
- System resource monitoring

The module integrates with feature flags to enable/disable monitoring
and provides both real-time and historical performance data.
"""

import time
import psutil
import logging
from typing import Dict, Any, Optional, List, Callable
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime
from utils.feature_flags import feature_flags

# Configure logging for performance monitoring
logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Data class to store individual performance metrics.
    
    Attributes:
        name: Name of the metric (e.g., 'data_load_time', 'memory_usage')
        value: The measured value
        unit: Unit of measurement (e.g., 'seconds', 'MB', 'percent')
        timestamp: When the metric was recorded
        component: Which component/function generated this metric
        metadata: Additional context about the measurement
    """
    name: str
    value: float
    unit: str
    timestamp: datetime = field(default_factory=datetime.now)
    component: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


class TimerContext:
    """Context manager for timing operations with the PerformanceMonitor.
    
    This class provides a convenient way to time code blocks using the
    'with' statement, automatically starting and ending timers.
    """
    
    def __init__(self, monitor: 'PerformanceMonitor', operation_name: str, component: str):
        """Initialize the timer context.
        
        Args:
            monitor: The PerformanceMonitor instance to use
            operation_name: Name of the operation being timed
            component: Component or module performing the operation
        """
        self.monitor = monitor
        self.operation_name = operation_name
        self.component = component
        self.start_time = None
    
    def __enter__(self):
        """Start the timer when entering the context."""
        self.monitor.start_timer(self.operation_name, self.component)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """End the timer when exiting the context."""
        metadata = {}
        if exc_type is not None:
            metadata['status'] = 'error'
            metadata['error_type'] = exc_type.__name__
        else:
            metadata['status'] = 'success'
        
        self.monitor.end_timer(self.operation_name, self.component, metadata)
        return False  # Don't suppress exceptions


class PerformanceMonitor:
    """Singleton class for monitoring application performance.
    
    This class provides methods to track various performance metrics including:
    - Memory usage (RAM, process memory)
    - Execution times for functions and operations
    - Data loading performance
    - Component rendering times
    - System resource utilization
    
    The monitor can be enabled/disabled via feature flags and provides
    both real-time monitoring and historical data collection.
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Ensure only one instance of PerformanceMonitor exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the performance monitor.
        
        Only initializes once due to singleton pattern.
        Sets up metric storage and system monitoring.
        """
        if self._initialized:
            return
            
        self._metrics: List[PerformanceMetric] = []
        self._start_times: Dict[str, float] = {}
        self._process = psutil.Process()
        self._system_baseline = self._get_system_metrics()
        self._initialized = True
        
        logger.info("Performance monitor initialized")
    
    def is_enabled(self) -> bool:
        """Check if performance monitoring is enabled via feature flags.
        
        Returns:
            True if monitoring is enabled, False otherwise
        """
        return feature_flags.is_enabled('performance_monitoring')
    
    def start_timer(self, operation_name: str, component: str = "unknown") -> None:
        """Start timing an operation.
        
        Args:
            operation_name: Name of the operation being timed
            component: Component or module performing the operation
        """
        if not self.is_enabled():
            return
            
        timer_key = f"{component}:{operation_name}"
        self._start_times[timer_key] = time.time()
        logger.debug(f"Started timer for {timer_key}")
    
    def end_timer(self, operation_name: str, component: str = "unknown", 
                  metadata: Optional[Dict[str, Any]] = None) -> float:
        """End timing an operation and record the metric.
        
        Args:
            operation_name: Name of the operation that was timed
            component: Component or module that performed the operation
            metadata: Additional context about the operation
            
        Returns:
            The elapsed time in seconds, or 0.0 if monitoring is disabled
        """
        if not self.is_enabled():
            return 0.0
            
        timer_key = f"{component}:{operation_name}"
        start_time = self._start_times.pop(timer_key, None)
        
        if start_time is None:
            logger.warning(f"No start time found for {timer_key}")
            return 0.0
        
        elapsed_time = time.time() - start_time
        
        # Record the timing metric
        self.record_metric(
            name=f"{operation_name}_time",
            value=elapsed_time,
            unit="seconds",
            component=component,
            metadata=metadata or {}
        )
        
        logger.debug(f"Operation {timer_key} took {elapsed_time:.3f} seconds")
        return elapsed_time
    
    def timer(self, operation_name: str, component: str = "unknown"):
        """Context manager for timing operations.
        
        Args:
            operation_name: Name of the operation being timed
            component: Component or module performing the operation
            
        Returns:
            Context manager that automatically starts and ends timing
            
        Example:
            with performance_monitor.timer('data_processing', 'data_manager'):
                # Code to be timed
                process_data()
        """
        return TimerContext(self, operation_name, component)
    
    def record_metric(self, name: str, value: float, unit: str, 
                     component: str = "unknown", 
                     metadata: Optional[Dict[str, Any]] = None) -> None:
        """Record a performance metric.
        
        Args:
            name: Name of the metric
            value: The measured value
            unit: Unit of measurement
            component: Component that generated the metric
            metadata: Additional context
        """
        if not self.is_enabled():
            return
            
        metric = PerformanceMetric(
            name=name,
            value=value,
            unit=unit,
            component=component,
            metadata=metadata or {}
        )
        
        self._metrics.append(metric)
        
        # Log significant metrics
        if name.endswith('_time') and value > 1.0:  # Log operations taking > 1 second
            logger.info(f"Performance: {component}.{name} = {value:.3f} {unit}")
    
    def record_memory_usage(self, component: str = "system", 
                           operation: str = "current") -> Dict[str, float]:
        """Record current memory usage metrics.
        
        Args:
            component: Component requesting memory measurement
            operation: Operation context for the measurement
            
        Returns:
            Dictionary containing memory metrics in MB
        """
        if not self.is_enabled():
            return {}
            
        try:
            # Process memory
            process_memory = self._process.memory_info()
            process_mb = process_memory.rss / 1024 / 1024
            
            # System memory
            system_memory = psutil.virtual_memory()
            system_used_mb = (system_memory.total - system_memory.available) / 1024 / 1024
            system_percent = system_memory.percent
            
            memory_metrics = {
                'process_memory_mb': process_mb,
                'system_memory_used_mb': system_used_mb,
                'system_memory_percent': system_percent
            }
            
            # Record each metric
            for metric_name, value in memory_metrics.items():
                unit = "MB" if "_mb" in metric_name else "percent"
                self.record_metric(
                    name=metric_name,
                    value=value,
                    unit=unit,
                    component=component,
                    metadata={'operation': operation}
                )
            
            return memory_metrics
            
        except Exception as e:
            logger.error(f"Error recording memory usage: {e}")
            return {}
    
    def _get_system_metrics(self) -> Dict[str, float]:
        """Get baseline system metrics for comparison.
        
        Returns:
            Dictionary of system metrics
        """
        try:
            return {
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {e}")
            return {}
    
    def get_metrics_summary(self, component: Optional[str] = None, 
                           last_n_minutes: Optional[int] = None) -> Dict[str, Any]:
        """Get a summary of recorded performance metrics.
        
        Args:
            component: Filter metrics by component (optional)
            last_n_minutes: Only include metrics from last N minutes (optional)
            
        Returns:
            Dictionary containing metric summaries and statistics
        """
        if not self.is_enabled():
            return {'monitoring_disabled': True}
            
        filtered_metrics = self._metrics
        
        # Filter by component if specified
        if component:
            filtered_metrics = [m for m in filtered_metrics if m.component == component]
        
        # Filter by time if specified
        if last_n_minutes:
            cutoff_time = datetime.now().timestamp() - (last_n_minutes * 60)
            filtered_metrics = [
                m for m in filtered_metrics 
                if m.timestamp.timestamp() > cutoff_time
            ]
        
        if not filtered_metrics:
            return {'no_metrics': True}
        
        # Group metrics by name
        metric_groups = {}
        for metric in filtered_metrics:
            if metric.name not in metric_groups:
                metric_groups[metric.name] = []
            metric_groups[metric.name].append(metric.value)
        
        # Calculate statistics for each metric group
        summary = {
            'total_metrics': len(filtered_metrics),
            'metric_types': len(metric_groups),
            'time_range': {
                'start': min(m.timestamp for m in filtered_metrics).isoformat(),
                'end': max(m.timestamp for m in filtered_metrics).isoformat()
            },
            'metrics': {}
        }
        
        for name, values in metric_groups.items():
            summary['metrics'][name] = {
                'count': len(values),
                'min': min(values),
                'max': max(values),
                'avg': sum(values) / len(values),
                'unit': next(m.unit for m in filtered_metrics if m.name == name)
            }
        
        return summary
    
    def clear_metrics(self) -> None:
        """Clear all stored metrics.
        
        Useful for resetting monitoring data or managing memory usage.
        """
        if not self.is_enabled():
            return
            
        metrics_count = len(self._metrics)
        self._metrics.clear()
        self._start_times.clear()
        
        logger.info(f"Cleared {metrics_count} performance metrics")


def monitor_performance(operation_name: str, component: str = "unknown"):
    """Decorator to automatically monitor function performance.
    
    Args:
        operation_name: Name of the operation being monitored
        component: Component or module name
        
    Returns:
        Decorated function that records execution time
        
    Example:
        @monitor_performance("data_loading", "data_manager")
        def load_data():
            # Function implementation
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            monitor = PerformanceMonitor()
            
            if not monitor.is_enabled():
                return func(*args, **kwargs)
            
            # Record memory before operation
            memory_before = monitor.record_memory_usage(
                component=component, 
                operation=f"{operation_name}_start"
            )
            
            # Time the operation
            monitor.start_timer(operation_name, component)
            
            try:
                result = func(*args, **kwargs)
                
                # Record successful completion
                monitor.end_timer(
                    operation_name, 
                    component, 
                    metadata={'status': 'success', 'memory_before': memory_before}
                )
                
                # Record memory after operation
                monitor.record_memory_usage(
                    component=component, 
                    operation=f"{operation_name}_end"
                )
                
                return result
                
            except Exception as e:
                # Record failed completion
                monitor.end_timer(
                    operation_name, 
                    component, 
                    metadata={'status': 'error', 'error': str(e)}
                )
                raise
        
        return wrapper
    return decorator


# Global instance for easy access
performance_monitor = PerformanceMonitor()


# Convenience functions for common operations
def start_timer(operation_name: str, component: str = "unknown") -> None:
    """Start timing an operation using the global monitor instance."""
    performance_monitor.start_timer(operation_name, component)


def end_timer(operation_name: str, component: str = "unknown", 
              metadata: Optional[Dict[str, Any]] = None) -> float:
    """End timing an operation using the global monitor instance."""
    return performance_monitor.end_timer(operation_name, component, metadata)


def record_metric(name: str, value: float, unit: str, 
                 component: str = "unknown", 
                 metadata: Optional[Dict[str, Any]] = None) -> None:
    """Record a metric using the global monitor instance."""
    performance_monitor.record_metric(name, value, unit, component, metadata)


def get_performance_summary(component: Optional[str] = None, 
                           last_n_minutes: Optional[int] = None) -> Dict[str, Any]:
    """Get performance summary using the global monitor instance."""
    return performance_monitor.get_metrics_summary(component, last_n_minutes)
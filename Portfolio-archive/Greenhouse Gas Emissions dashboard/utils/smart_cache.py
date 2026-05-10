"""Smart Cache Module for GHG Dashboard Performance Optimization.

This module implements advanced caching strategies with TTL (Time To Live) and memory management
for the GHG emissions dashboard. It provides intelligent cache warming, hit/miss analytics,
and memory-aware cache sizing to optimize performance beyond basic LRU caching.

Key Features:
- Time-based cache expiration (TTL)
- Memory-aware cache sizing with automatic cleanup
- Cache warming strategies for common data patterns
- Cache hit/miss analytics and monitoring
- Integration with feature flags for easy rollback
- Thread-safe operations for multi-user environments

This is part of Phase 2 of the performance optimization plan.
"""

import time
import threading
import psutil
import logging
from typing import Dict, Any, Optional, Callable, Tuple, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import wraps
from collections import OrderedDict
from utils.feature_flags import feature_flags
from utils.performance_monitor import performance_monitor

# Configure logging for this module
logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Represents a single cache entry with metadata.
    
    Attributes:
        value: The cached value
        created_at: When the entry was created
        last_accessed: When the entry was last accessed
        access_count: Number of times this entry has been accessed
        size_bytes: Estimated memory size of the cached value
        ttl_seconds: Time to live in seconds (None for no expiration)
    """
    value: Any
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    size_bytes: int = 0
    ttl_seconds: Optional[int] = None
    
    def is_expired(self) -> bool:
        """Check if this cache entry has expired.
        
        Returns:
            True if the entry has expired, False otherwise
        """
        if self.ttl_seconds is None:
            return False
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)
    
    def update_access(self) -> None:
        """Update access statistics for this entry."""
        self.last_accessed = datetime.now()
        self.access_count += 1


class SmartCache:
    """Advanced caching system with TTL and memory management.
    
    This cache provides intelligent caching beyond basic LRU with features like:
    - Time-based expiration (TTL)
    - Memory usage monitoring and limits
    - Cache warming for common patterns
    - Hit/miss analytics
    - Automatic cleanup of expired entries
    """
    
    def __init__(self, 
                 max_size: int = 1000,
                 max_memory_mb: float = 500.0,
                 default_ttl_seconds: Optional[int] = 3600,  # 1 hour default
                 cleanup_interval_seconds: int = 300):  # 5 minutes
        """Initialize the smart cache.
        
        Args:
            max_size: Maximum number of entries to cache
            max_memory_mb: Maximum memory usage in MB
            default_ttl_seconds: Default TTL for entries (None for no expiration)
            cleanup_interval_seconds: How often to run cleanup (seconds)
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._max_size = max_size
        self._max_memory_bytes = max_memory_mb * 1024 * 1024
        self._default_ttl = default_ttl_seconds
        self._cleanup_interval = cleanup_interval_seconds
        
        # Analytics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._last_cleanup = datetime.now()
        
        logger.info(f"SmartCache initialized: max_size={max_size}, max_memory={max_memory_mb}MB")
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value if found and not expired, None otherwise
        """
        if not feature_flags.is_enabled('use_smart_cache'):
            return None
            
        with self._lock:
            # Run periodic cleanup
            self._maybe_cleanup()
            
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            
            # Check if expired
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                logger.debug(f"Cache entry expired: {key}")
                return None
            
            # Update access statistics and move to end (LRU)
            entry.update_access()
            self._cache.move_to_end(key)
            self._hits += 1
            
            return entry.value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl_seconds: TTL for this entry (uses default if None)
        """
        if not feature_flags.is_enabled('use_smart_cache'):
            return
            
        with self._lock:
            # Estimate memory size of the value
            size_bytes = self._estimate_size(value)
            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            
            # Create cache entry
            entry = CacheEntry(
                value=value,
                size_bytes=size_bytes,
                ttl_seconds=ttl
            )
            
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
            
            # Add new entry
            self._cache[key] = entry
            
            # Enforce size and memory limits
            self._enforce_limits()
            
            logger.debug(f"Cache entry added: {key} ({size_bytes} bytes, TTL: {ttl}s)")
    
    def delete(self, key: str) -> bool:
        """Delete a specific cache entry.
        
        Args:
            key: The cache key to delete
            
        Returns:
            True if the key was found and deleted, False otherwise
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                logger.debug(f"Cache entry deleted: {key}")
                return True
            return False
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            entry_count = len(self._cache)
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            logger.info(f"Cache cleared: {entry_count} entries removed")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary containing cache performance metrics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
            
            total_memory = sum(entry.size_bytes for entry in self._cache.values())
            
            return {
                'entries': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate_percent': round(hit_rate, 2),
                'evictions': self._evictions,
                'memory_usage_mb': round(total_memory / 1024 / 1024, 2),
                'max_memory_mb': round(self._max_memory_bytes / 1024 / 1024, 2),
                'memory_usage_percent': round(total_memory / self._max_memory_bytes * 100, 2)
            }
    
    def warm_cache(self, warm_functions: List[Callable[[], Tuple[str, Any]]]) -> None:
        """Warm the cache with common data patterns.
        
        Args:
            warm_functions: List of functions that return (key, value) tuples to cache
        """
        if not feature_flags.is_enabled('use_smart_cache'):
            return
            
        logger.info(f"Starting cache warming with {len(warm_functions)} functions")
        start_time = time.time()
        
        warmed_count = 0
        for warm_func in warm_functions:
            try:
                key, value = warm_func()
                if key and value is not None:
                    self.set(key, value)
                    warmed_count += 1
            except Exception as e:
                logger.warning(f"Cache warming function failed: {e}")
        
        elapsed_time = time.time() - start_time
        logger.info(f"Cache warming completed: {warmed_count} entries in {elapsed_time:.2f}s")
    
    def _estimate_size(self, value: Any) -> int:
        """Estimate the memory size of a value.
        
        Args:
            value: The value to estimate
            
        Returns:
            Estimated size in bytes
        """
        try:
            import sys
            return sys.getsizeof(value)
        except Exception:
            # Fallback estimation
            if isinstance(value, str):
                return len(value.encode('utf-8'))
            elif isinstance(value, (list, tuple)):
                return sum(self._estimate_size(item) for item in value)
            elif isinstance(value, dict):
                return sum(self._estimate_size(k) + self._estimate_size(v) for k, v in value.items())
            else:
                return 1024  # Default estimate
    
    def _enforce_limits(self) -> None:
        """Enforce cache size and memory limits by evicting entries."""
        # Remove expired entries first
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
        for key in expired_keys:
            del self._cache[key]
        
        # Enforce size limit (LRU eviction)
        while len(self._cache) > self._max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
            self._evictions += 1
        
        # Enforce memory limit (evict least recently used)
        total_memory = sum(entry.size_bytes for entry in self._cache.values())
        while total_memory > self._max_memory_bytes and self._cache:
            oldest_key = next(iter(self._cache))
            oldest_entry = self._cache[oldest_key]
            total_memory -= oldest_entry.size_bytes
            del self._cache[oldest_key]
            self._evictions += 1
    
    def _maybe_cleanup(self) -> None:
        """Run cleanup if enough time has passed since last cleanup."""
        now = datetime.now()
        if (now - self._last_cleanup).total_seconds() >= self._cleanup_interval:
            self._cleanup_expired()
            self._last_cleanup = now
    
    def _cleanup_expired(self) -> None:
        """Remove all expired entries from the cache."""
        expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


# Global smart cache instance
_smart_cache_instance = None
_smart_cache_lock = threading.Lock()


def get_smart_cache() -> SmartCache:
    """Get the global smart cache instance.
    
    Returns:
        The singleton SmartCache instance
    """
    global _smart_cache_instance
    
    if _smart_cache_instance is None:
        with _smart_cache_lock:
            if _smart_cache_instance is None:
                _smart_cache_instance = SmartCache()
    
    return _smart_cache_instance


def smart_cache_decorator(key_func: Callable = None, ttl_seconds: Optional[int] = None):
    """Decorator for caching function results with smart cache.
    
    Args:
        key_func: Function to generate cache key from function args
        ttl_seconds: TTL for cached results
        
    Returns:
        Decorated function with smart caching
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not feature_flags.is_enabled('use_smart_cache'):
                return func(*args, **kwargs)
            
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from cache
            cache = get_smart_cache()
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator
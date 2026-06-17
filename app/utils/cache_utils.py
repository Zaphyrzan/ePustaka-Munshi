"""
Query Result Caching Utilities
Simple in-memory caching for query results with TTL support
"""
import functools
import time
from typing import Any, Callable, Optional

# Global cache store (in production, use Redis)
_cache_store = {}


class CacheEntry:
    """A single cache entry with TTL"""
    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
    
    def is_expired(self) -> bool:
        """Check if this entry has expired"""
        return (time.time() - self.created_at) > self.ttl


def cache_query(ttl_seconds: int = 300):
    """
    Decorator to cache query results with TTL.
    
    Usage:
        @cache_query(ttl_seconds=600)  # 10 minute cache
        def get_book_categories():
            return db.session.query(Book.category).distinct().all()
    
    Args:
        ttl_seconds: Time to live in seconds (default: 5 minutes)
    """
    def decorator(func: Callable) -> Callable:
        cache_key = f"{func.__module__}.{func.__name__}"
        
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Skip caching if we have arguments (function-specific data)
            if args or kwargs:
                return func(*args, **kwargs)
            
            # Check if cached value exists and is valid
            if cache_key in _cache_store:
                entry = _cache_store[cache_key]
                if not entry.is_expired():
                    return entry.value
                else:
                    # Clean up expired entry
                    del _cache_store[cache_key]
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            _cache_store[cache_key] = CacheEntry(result, ttl_seconds)
            return result
        
        return wrapper
    return decorator


def invalidate_cache(func_name: str):
    """
    Manually invalidate cache for a specific function.
    
    Usage:
        invalidate_cache('get_book_categories')
    """
    # Try multiple cache key formats
    for module_prefix in ['app.utils.cache_utils', 'app.models', 'app.routes']:
        cache_key = f"{module_prefix}.{func_name}"
        if cache_key in _cache_store:
            del _cache_store[cache_key]
            return True
    return False


def invalidate_all_cache():
    """Clear all cached values"""
    global _cache_store
    _cache_store.clear()


def get_cache_stats():
    """Get cache statistics for debugging"""
    expired = sum(1 for entry in _cache_store.values() if entry.is_expired())
    valid = len(_cache_store) - expired
    return {
        'total': len(_cache_store),
        'valid': valid,
        'expired': expired
    }

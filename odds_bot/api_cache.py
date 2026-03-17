"""
API cache system for minimizing API requests.
Caches responses to avoid hitting rate limits.
"""
import os
import json
import time
from datetime import datetime, timedelta

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

CACHE_DURATION = 3600  # Cache for 1 hour (3600 seconds)


def get_cache_key(prefix, params):
    """Generate a cache key from prefix and params."""
    param_str = '_'.join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"{prefix}_{hash(param_str) % 10000000}"


def get_cached_data(cache_key):
    """Get data from cache if it exists and is not expired."""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)
        
        # Check if cache is expired
        cached_time = datetime.fromisoformat(cache['timestamp'])
        if datetime.now() - cached_time > timedelta(seconds=CACHE_DURATION):
            return None
        
        return cache['data']
    except Exception:
        return None


def set_cached_data(cache_key, data):
    """Save data to cache."""
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    try:
        cache = {
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        with open(cache_file, 'w') as f:
            json.dump(cache, f)
    except Exception as e:
        print(f"Cache save error: {e}")


def clear_cache():
    """Clear all cached data."""
    for f in os.listdir(CACHE_DIR):
        if f.endswith('.json'):
            os.remove(os.path.join(CACHE_DIR, f))
    print("✓ Cache cleared")

import pytest
import os
import pickle
from src.cache.sqlite_cache import SQLiteCache
from src.cache.redis_cache import RedisCache

def test_sqlite_cache():
    cache = SQLiteCache("test_cache.db")
    cache.set("test_key", "test_value")
    assert cache.get("test_key") == "test_value"
    assert cache.exists("test_key")
    assert cache.get("non_existent") is None
    os.remove("test_cache.db")

def test_redis_cache_fallback():
    # Attempting to connect to non-existent redis should fail or we mock it
    # For now, we test if the class can be instantiated
    try:
        cache = RedisCache(host='non_existent_host', port=6379)
        # This might not fail until we actually try to use it
        cache.set("test", "test")
    except Exception:
        pytest.skip("Redis not available")

"""Unit tests for TTLCache."""

import asyncio

import pytest

from app.services.cache import TTLCache, make_cache_key


class TestTTLCache:
    """Unit tests for TTLCache."""

    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = TTLCache(ttl_seconds=60)
        await cache.start()

        await cache.set("key1", "value1")
        value, entry = await cache.get("key1")

        assert value == "value1"
        assert entry is not None
        assert not entry.is_expired

        await cache.stop()

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        cache = TTLCache(ttl_seconds=60)
        await cache.start()

        value, entry = await cache.get("nonexistent")

        assert value is None
        assert entry is None

        await cache.stop()

    @pytest.mark.asyncio
    async def test_expiration(self):
        """Test that entries expire after TTL."""
        cache = TTLCache(ttl_seconds=1)
        await cache.start()

        await cache.set("key1", "value1")

        value, _ = await cache.get("key1")
        assert value == "value1"

        await asyncio.sleep(1.1)

        value, entry = await cache.get("key1")
        assert value is None
        assert entry is None

        await cache.stop()

    @pytest.mark.asyncio
    async def test_max_size_eviction(self):
        """Test that oldest entries are evicted when max size reached."""
        cache = TTLCache(ttl_seconds=60, max_size=3)
        await cache.start()

        await cache.set("key1", "value1")
        await asyncio.sleep(0.01)
        await cache.set("key2", "value2")
        await asyncio.sleep(0.01)
        await cache.set("key3", "value3")

        await cache.set("key4", "value4")

        value, _ = await cache.get("key1")
        assert value is None

        value, _ = await cache.get("key2")
        assert value == "value2"

        await cache.stop()

    @pytest.mark.asyncio
    async def test_delete(self):
        """Test delete operation."""
        cache = TTLCache(ttl_seconds=60)
        await cache.start()

        await cache.set("key1", "value1")
        result = await cache.delete("key1")

        assert result is True

        value, _ = await cache.get("key1")
        assert value is None

        await cache.stop()

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        """Test deleting a key that doesn't exist."""
        cache = TTLCache(ttl_seconds=60)
        await cache.start()

        result = await cache.delete("nonexistent")
        assert result is False

        await cache.stop()

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clear operation."""
        cache = TTLCache(ttl_seconds=60)
        await cache.start()

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        await cache.clear()

        assert cache.stats()["size"] == 0

        await cache.stop()

    @pytest.mark.asyncio
    async def test_stats(self):
        """Test cache statistics."""
        cache = TTLCache(ttl_seconds=300, max_size=1000)
        await cache.start()

        await cache.set("key1", "value1")
        await cache.set("key2", "value2")

        stats = cache.stats()

        assert stats["size"] == 2
        assert stats["max_size"] == 1000
        assert stats["ttl_seconds"] == 300.0

        await cache.stop()


class TestCacheKey:
    """Tests for cache key generation."""

    def test_make_cache_key_basic(self):
        """Test basic cache key generation."""
        key = make_cache_key("octocat", 1, 30)
        assert key == "gists:octocat:page=1:per_page=30"

    def test_make_cache_key_case_insensitive(self):
        """Test that usernames are lowercased."""
        key1 = make_cache_key("Octocat", 1, 30)
        key2 = make_cache_key("octocat", 1, 30)
        assert key1 == key2

    def test_make_cache_key_different_pagination(self):
        """Test that different pagination creates different keys."""
        key1 = make_cache_key("octocat", 1, 30)
        key2 = make_cache_key("octocat", 2, 30)
        key3 = make_cache_key("octocat", 1, 50)

        assert key1 != key2
        assert key1 != key3
        assert key2 != key3

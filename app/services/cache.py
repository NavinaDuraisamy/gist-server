"""In-memory TTL cache implementation."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Generic, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


@dataclass
class CacheEntry(Generic[T]):
    """A single cache entry with TTL tracking."""

    value: T
    expires_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return datetime.now(timezone.utc) >= self.expires_at


class TTLCache(Generic[T]):
    """
    Thread-safe in-memory cache with TTL support.

    Features:
    - Automatic expiration of entries
    - Maximum size limit with LRU-like eviction
    - Background cleanup task
    """

    def __init__(
        self,
        ttl_seconds: int = 300,
        max_size: int = 1000,
        cleanup_interval: int = 60,
    ):
        self._cache: dict[str, CacheEntry[T]] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        self._max_size = max_size
        self._cleanup_interval = cleanup_interval
        self._lock = asyncio.Lock()
        self._cleanup_task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start background cleanup task."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def get(self, key: str) -> tuple[T | None, CacheEntry[T] | None]:
        """
        Get value from cache.

        Returns (value, entry) or (None, None) if not found/expired.
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None, None
            if entry.is_expired:
                del self._cache[key]
                return None, None
            return entry.value, entry

    async def set(self, key: str, value: T) -> CacheEntry[T]:
        """Set value in cache with TTL."""
        async with self._lock:
            if len(self._cache) >= self._max_size:
                await self._evict_oldest_unlocked()

            entry = CacheEntry(
                value=value,
                expires_at=datetime.now(timezone.utc) + self._ttl,
            )
            self._cache[key] = entry
            return entry

    async def delete(self, key: str) -> bool:
        """Delete entry from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """Clear all entries."""
        async with self._lock:
            self._cache.clear()

    async def _evict_oldest_unlocked(self) -> None:
        """Evict oldest entry (by creation time). Must be called with lock held."""
        if not self._cache:
            return
        oldest_key = min(
            self._cache.keys(),
            key=lambda k: self._cache[k].created_at,
        )
        del self._cache[oldest_key]

    async def _cleanup_loop(self) -> None:
        """Background task to clean expired entries."""
        while True:
            await asyncio.sleep(self._cleanup_interval)
            async with self._lock:
                expired_keys = [k for k, v in self._cache.items() if v.is_expired]
                for key in expired_keys:
                    del self._cache[key]
                if expired_keys:
                    logger.debug(f"Cleaned {len(expired_keys)} expired entries")

    def stats(self) -> dict:
        """Return cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl.total_seconds(),
        }


def make_cache_key(username: str, page: int, per_page: int) -> str:
    """Generate cache key for gist requests."""
    return f"gists:{username.lower()}:page={page}:per_page={per_page}"

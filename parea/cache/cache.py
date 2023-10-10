from typing import Optional

from abc import ABC

from parea.schemas.models import CacheRequest, TraceLog


class Cache(ABC):
    def get(self, key: CacheRequest) -> Optional[TraceLog]:
        """
        Get a normal response from the cache.

        Args:
            key (CacheRequest): The cache key.

        Returns:
            The cached response, or None if the key was not found.
        """
        raise NotImplementedError

    async def aget(self, key: CacheRequest) -> Optional[TraceLog]:
        """
        Get a normal response from the cache.

        Args:
            key (CacheRequest): The cache key.

        Returns:
            The cached response, or None if the key was not found.
        """
        raise NotImplementedError

    def set(self, key: CacheRequest, value: TraceLog):
        """
        Set a normal response in the cache.

        Args:
            key (CacheRequest): The cache key.
            value (TraceLog): The response to cache.
        """
        raise NotImplementedError

    async def aset(self, key: CacheRequest, value: TraceLog):
        """
        Set a normal response in the cache.

        Args:
            key (CacheRequest): The cache key.
            value (TraceLog): The response to cache.
        """
        raise NotImplementedError

    def invalidate(self, key: CacheRequest):
        """
        Invalidate a key in the cache.

        Args:
            key (CacheRequest): The cache key.
        """
        raise NotImplementedError

    async def ainvalidate(self, key: CacheRequest):
        """
        Invalidate a key in the cache.

        Args:
            key (CacheRequest): The cache key.
        """
        raise NotImplementedError
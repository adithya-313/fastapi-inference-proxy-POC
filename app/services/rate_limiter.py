"""
app/services/rate_limiter.py

In-Memory Fixed Window Rate Limiter - "The Bouncer"

This module implements a rate limiter that protects our API from abuse.
Think of it like a nightclub bouncer who counts how many people enter.

Rules:
- Each user (identified by IP address) is allowed 5 requests per 60-second window
- After 5 requests, the user must wait for the window to reset
- The window resets automatically every 60 seconds

How it works:
1. We store a count for each client IP in a dictionary
2. Before each request, we check if the count is below 5
3. If allowed, we increment the count
4. If not allowed, we reject the request with a 429 error
"""

import asyncio
import time
from typing import Dict, Optional

from fastapi import HTTPException


class RateLimiter:
    """
    A simple in-memory rate limiter using the Fixed Window algorithm.

    This class tracks how many requests each client has made and
    blocks requests when the limit is exceeded.

    Attributes:
        max_requests: Maximum requests allowed per window (default: 5)
        window_seconds: Length of the time window in seconds (default: 60)
        requests: Dictionary storing request counts per client IP
        lock: asyncio.Lock to prevent race conditions in concurrent requests
    """

    def __init__(
        self,
        max_requests: int = 5,
        window_seconds: int = 60
    ):
        """
        Set up the rate limiter with default settings.

        Args:
            max_requests: Maximum requests allowed per window (default: 5)
            window_seconds: Length of the time window in seconds (default: 60)
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        self.requests: Dict[str, int] = {}

        self.lock = asyncio.Lock()

        self.cleanup_task: Optional[asyncio.Task] = None

    async def is_allowed(self, client_id: str) -> bool:
        """
        Check if a client is allowed to make a request.

        This method:
        1. Gets the lock (waits if another task is using it)
        2. Gets the current request count for this client
        3. Checks if the count is below the limit
        4. Increments the count if allowed
        5. Releases the lock automatically

        Args:
            client_id: The client's IP address

        Returns:
            True if the client is allowed to make a request
            False if the client has exceeded the rate limit
        """
        async with self.lock:
            current_count = self.requests.get(client_id, 0)

            if current_count >= self.max_requests:
                return False

            self.requests[client_id] = current_count + 1
            return True

    async def check_and_raise(self, client_id: str) -> None:
        """
        Check if a client is allowed, and raise an exception if not.

        This is a convenience method that combines checking and raising.
        Use this when you want to immediately reject a request that
        exceeds the limit.

        Args:
            client_id: The client's IP address

        Raises:
            HTTPException: If the client has exceeded the rate limit (429)
        """
        allowed = await self.is_allowed(client_id)

        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Rate limit exceeded. "
                    f"You can only make {self.max_requests} requests "
                    f"every {self.window_seconds} seconds. "
                    f"Please wait before trying again."
                ),
            )

    async def _cleanup_loop(self) -> None:
        """
        Background task that automatically resets the rate limiter.

        This method runs in an infinite loop and clears the requests
        dictionary every 60 seconds. This is the "window reset" mechanism.
        """
        while True:
            await asyncio.sleep(self.window_seconds)
            async with self.lock:
                self.requests.clear()

    def start_cleanup(self) -> None:
        """
        Start the background cleanup task.

        Call this when your FastAPI application starts up.
        It will create a background task that resets the window every 60 seconds.
        """
        if self.cleanup_task is None:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())

    def stop_cleanup(self) -> None:
        """
        Stop the background cleanup task.

        Call this when your FastAPI application shuts down.
        This prevents "task was never awaited" warnings.
        """
        if self.cleanup_task is not None:
            self.cleanup_task.cancel()
            self.cleanup_task = None


# Global instance - single rate limiter for the entire application
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get the global rate limiter instance.

    This function creates the rate limiter on first call (lazy loading),
    and returns the same instance on all subsequent calls.

    Returns:
        The global RateLimiter instance
    """
    global _rate_limiter

    if _rate_limiter is None:
        _rate_limiter = RateLimiter()

    return _rate_limiter
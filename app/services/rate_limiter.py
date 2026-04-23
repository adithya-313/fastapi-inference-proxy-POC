"""
In-Memory Fixed Window Rate Limiter - The Bouncer

This module implements a simple rate limiter using the Fixed Window algorithm.
It tracks how many requests each user (identified by IP) makes within a time window.

Rules:
- Maximum 5 requests per 60-second window per user
- When window expires, all counts reset to zero
"""

import asyncio
import time
from typing import Dict

from fastapi import HTTPException


class RateLimiter:
    """
    A simple in-memory rate limiter that tracks requests per client.
    
    Attributes:
        max_requests: Maximum requests allowed per window (default: 5)
        window_seconds: Length of the time window in seconds (default: 60)
        requests: Dictionary storing request counts per client IP
        lock: asyncio.Lock to prevent race conditions in concurrent requests
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        """
        Initialize the rate limiter with default settings.
        
        Args:
            max_requests: Maximum requests allowed per window (default: 5)
            window_seconds: Time window length in seconds (default: 60)
        """
        # Store configuration
        self.max_requests = max_requests
        self.window_seconds = window_seconds

        # Dictionary to store request counts: { "client_ip": count }
        # Example: { "192.168.1.1": 3, "10.0.0.1": 1 }
        self.requests: Dict[str, int] = {}

        # Lock to protect the dictionary from race conditions
        # Race conditions happen when multiple async tasks try to read/write
        # the dictionary at the same time
        self.lock = asyncio.Lock()

        # Background task handle (will be created when starting cleanup)
        self.cleanup_task = None

    async def is_allowed(self, client_id: str) -> bool:
        """
        Check if a client is allowed to make a request.
        
        This method:
        1. Acquires the lock (waits if another task is using it)
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
        # Step 1: Acquire the lock before accessing the shared dictionary
        # The 'async with' statement automatically releases the lock
        # when we exit the block (even if an error occurs)
        async with self.lock:
            
            # Step 2: Get the current request count for this client
            # If client has no record, default to 0
            current_count = self.requests.get(client_id, 0)
            
            # Step 3: Check if the client has exceeded the limit
            if current_count >= self.max_requests:
                # Client has exceeded the limit - do not allow
                return False
            
            # Step 4: Increment the request count for this client
            # We store the new count back in the dictionary
            self.requests[client_id] = current_count + 1
            
            # Step 5: Return True - client is allowed
            return True

    async def check_and_raise(self, client_id: str) -> None:
        """
        Check if a client is allowed, and raise an exception if not.
        
        This is a convenience method that combines checking and raising.
        Use this when you want to immediately reject a request that exceeds the limit.
        
        Args:
            client_id: The client's IP address
            
        Raises:
            HTTPException: If the client has exceeded the rate limit
        """
        # Check if the client is allowed to make a request
        allowed = await self.is_allowed(client_id)
        
        # If not allowed, raise an HTTPException with status code 429
        if not allowed:
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. You can only make {self.max_requests} "
                       f"requests every {self.window_seconds} seconds. Please wait "
                       f"before trying again."
            )

    async def _cleanup_loop(self) -> None:
        """
        Background task that automatically resets the rate limiter.
        
        This method runs in an infinite loop and clears the requests
        dictionary every 60 seconds. This is the "window reset" mechanism.
        
        Note: This runs as a background task and will keep running
        until the application is stopped or stop_cleanup() is called.
        """
        # Infinite loop - keep running forever
        while True:
            # Wait for 60 seconds (the window duration)
            await asyncio.sleep(self.window_seconds)
            
            # Acquire the lock before clearing the dictionary
            async with self.lock:
                # Clear all request counts - everyone starts fresh
                self.requests.clear()
                
                # Print a debug message (useful for development)
                print(f"Rate limiter window reset. Dictionary cleared.")

    def start_cleanup(self) -> None:
        """
        Start the background cleanup task.
        
        Call this when your FastAPI application starts up.
        It will create a background task that resets the window every 60 seconds.
        """
        # Only start if not already running
        if self.cleanup_task is None:
            # Create a background task
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            print("Rate limiter cleanup task started.")

    def stop_cleanup(self) -> None:
        """
        Stop the background cleanup task.
        
        Call this when your FastAPI application shuts down.
        This prevents "task was never awaited" warnings.
        """
        # Only stop if it was started
        if self.cleanup_task is not None:
            # Cancel the background task
            self.cleanup_task.cancel()
            # Set to None to indicate it's not running
            self.cleanup_task = None
            print("Rate limiter cleanup task stopped.")


# Global instance - single rate limiter for the entire application
# This ensures all requests share the same rate limit state
_rate_limiter = None


def get_rate_limiter() -> RateLimiter:
    """
    Get the global rate limiter instance.
    
    This function creates the rate limiter on first call (lazy loading),
    and returns the same instance on all subsequent calls.
    
    Returns:
        The global RateLimiter instance
    """
    global _rate_limiter
    
    # If the rate limiter hasn't been created yet, create it now
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    
    # Return the rate limiter instance
    return _rate_limiter


# Example usage (for testing purposes):
async def main():
    """
    Example function showing how to use the rate limiter.
    """
    # Create a new rate limiter
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    
    # Start the cleanup task
    limiter.start_cleanup()
    
    # Simulate 6 requests from a client
    client_ip = "192.168.1.100"
    
    print(f"\nTesting rate limiter for client: {client_ip}")
    print("-" * 50)
    
    for i in range(1, 7):
        # Check if request is allowed
        allowed = await limiter.is_allowed(client_ip)
        
        if allowed:
            print(f"Request {i}: ALLOWED")
        else:
            print(f"Request {i}: DENIED (rate limit exceeded)")
    
    print("-" * 50)
    
    # Stop cleanup when done
    limiter.stop_cleanup()


# Only run main() if this file is executed directly
if __name__ == "__main__":
    asyncio.run(main())
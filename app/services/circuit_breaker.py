"""
app/services/circuit_breaker.py

Circuit Breaker - "The Safety Switch"

This module implements the Circuit Breaker pattern, a design pattern that
prevents cascading failures in distributed systems.

Think of it like an electrical circuit breaker in your home:
- Normal operation: The circuit is "CLOSED" and electricity flows normally
- Problem detected: The circuit "OPENS" and cuts off power to protect the system
- Recovery attempt: The circuit goes "HALF_OPEN" to test if it's safe to restore power

Three States:
1. CLOSED (normal): Requests pass through to the backend normally.
                  If everything works, we stay in this state.
2. OPEN (failing): Requests are blocked and fail immediately with 503.
                   We enter this state after too many failures.
3. HALF_OPEN (testing): One or two test requests are allowed through.
                        If they succeed, we close the circuit.
                        If they fail, we open the circuit again.

How it works in our system:
1. We count failures every time the backend fails
2. After 3 failures, we OPEN the circuit and stop sending requests
3. We wait 20 seconds to give the backend time to recover
4. After 20 seconds, we go HALF_OPEN and try one test request
5. If the test succeeds, we CLOSE the circuit and resume normal operation
6. If the test fails, we OPEN the circuit again and wait another 20 seconds

This pattern is like a bouncer at a club:
- CLOSED: "Come on in!" - everyone is allowed
- OPEN: "Sorry, we're closed for cleaning" - no one can enter
- HALF_OPEN: "Let me check if it's ready" - one person at a time to test
"""

import asyncio
import time
from enum import Enum
from typing import Optional

from fastapi import HTTPException


class CircuitState(Enum):
    """
    Possible states for the circuit breaker.

    An Enum is like a list of named choices. Each choice is called a "member".
    We use enums to avoid magic numbers and make the code more readable.

    Example without Enum:
        CLOSED = 0
        OPEN = 1
        HALF_OPEN = 2

    Example with Enum:
        CircuitState.CLOSED
        CircuitState.OPEN
        CircuitState.HALF_OPEN
    """
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker to protect against cascading failures.

    This class watches our backend service and "trips" when too many
    failures happen. When tripped, it blocks new requests for a while
    to give the backend time to recover.

    Attributes:
        failure_threshold: How many failures before opening the circuit (default: 3)
        recovery_timeout: Seconds to wait before trying again (default: 20)
        state: Current state of the circuit (CLOSED, OPEN, or HALF_OPEN)
        failure_count: How many consecutive failures we've seen
        last_failure_time: When the last failure happened (for timing)
        lock: asyncio.Lock to prevent race conditions
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: int = 20
    ):
        """
        Set up the circuit breaker with default settings.

        Args:
            failure_threshold: How many failures before opening (default: 3)
            recovery_timeout: How long to wait before retrying (default: 20 seconds)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None

        self.lock = asyncio.Lock()

    async def check_state(self) -> None:
        """
        Check if we're in a state where we can handle requests.

        This method should be called before sending a request to the backend.
        It handles the timing-based transitions between states.

        If we're in OPEN state:
            - Check if enough time has passed (20 seconds)
            - If yes, move to HALF_OPEN and allow a test request
            - If no, raise HTTPException with 503 error

        If we're in CLOSED or HALF_OPEN:
            - Just return normally (we can handle requests)

        Raises:
            HTTPException: If state is OPEN and recovery timeout hasn't passed
        """
        async with self.lock:
            if self.state == CircuitState.OPEN:
                elapsed = time.time() - self.last_failure_time
                if elapsed >= self.recovery_timeout:
                    self.state = CircuitState.HALF_OPEN
                else:
                    remaining = self.recovery_timeout - elapsed
                    raise HTTPException(
                        status_code=503,
                        detail=f"Backend service is recovering. Please try again later. "
                               f"Retry in {int(remaining)} seconds."
                    )

    async def record_failure(self) -> None:
        """
        Record that a request to the backend failed.

        Call this method whenever the backend returns an error or times out.
        This method:
        1. Increments the failure counter
        2. If we've reached the threshold, opens the circuit
        3. Records the timestamp of the failure

        If the circuit is already OPEN, we stay OPEN.
        If the circuit is HALF_OPEN, a failure means we go back to OPEN.
        """
        async with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
            elif self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN

    async def record_success(self) -> None:
        """
        Record that a request to the backend succeeded.

        Call this method whenever the backend responds successfully.
        This method:
        1. Resets the failure counter to zero
        2. Sets the state to CLOSED (normal operation)

        If we're in HALF_OPEN, this means recovery was successful.
        If we're in CLOSED, this just keeps us healthy.
        """
        async with self.lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED

    def reset(self) -> None:
        """
        Manually reset the circuit breaker to CLOSED state.

        This is useful for administrators who want to force the
        system back to normal operation after fixing an issue.

        Note: This is a synchronous method because it's a manual operation.
        """
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None


# Global instance - one circuit breaker for the entire application
# This ensures all requests share the same circuit breaker state
_circuit_breaker: Optional[CircuitBreaker] = None


def get_circuit_breaker() -> CircuitBreaker:
    """
    Get the global circuit breaker instance.

    This function creates the circuit breaker on first call (lazy loading),
    and returns the same instance on all subsequent calls.

    This pattern is called "Singleton" - there's only one instance,
    no matter how many times you call this function.

    Usage in FastAPI:
        @router.post("/endpoint")
        async def my_endpoint(
            breaker: CircuitBreaker = Depends(get_circuit_breaker)
        ):
            ...

    Returns:
        The global CircuitBreaker instance
    """
    global _circuit_breaker

    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()

    return _circuit_breaker


# Example usage for testing:
async def main():
    """
    Example function showing how the circuit breaker works.
    """
    breaker = CircuitBreaker()

    print("Circuit Breaker Demo")
    print("=" * 50)

    print("\n1. Initial state:")
    print(f"   State: {breaker.state.value}")
    print(f"   Failure count: {breaker.failure_count}")

    print("\n2. Simulating 3 failures (threshold):")
    for i in range(1, 4):
        await breaker.record_failure()
        print(f"   Failure {i}: State = {breaker.state.value}, Count = {breaker.failure_count}")

    print("\n3. Trying to send a request (should be blocked):")
    try:
        await breaker.check_state()
        print("   Request allowed!")
    except HTTPException as e:
        print(f"   Request blocked: {e.detail}")

    print("\n4. Manually transitioning to HALF_OPEN (simulating time passage):")
    breaker.state = CircuitState.HALF_OPEN
    print(f"   State: {breaker.state.value}")

    print("\n5. Simulating a successful request after recovery:")
    await breaker.record_success()
    print(f"   State: {breaker.state.value}")
    print(f"   Failure count: {breaker.failure_count}")

    print("\n6. Circuit is back to normal operation!")


if __name__ == "__main__":
    asyncio.run(main())
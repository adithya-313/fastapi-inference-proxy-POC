"""
app/services/circuit_breaker.py

Circuit Breaker - "The Safety Switch"

This module implements the Circuit Breaker pattern, a design pattern that
prevents cascading failures in distributed systems.

Think of it like an electrical circuit breaker:
- Normal operation: The circuit is "closed" and electricity flows
- Problem detected: The circuit "opens" and cuts off power
- Recovery attempt: The circuit goes "half-open" to test if it's safe

States:
1. CLOSED (normal): Requests pass through normally
2. OPEN (failing): Requests fail immediately with 503
3. HALF-OPEN (testing): One test request is allowed through

How it works:
1. We count failures (errors from the backend)
2. After 5 failures, we open the circuit and stop sending requests
3. After 60 seconds, we try again (half-open state)
4. If requests succeed, we close the circuit
5. If requests fail, we open the circuit again
"""

import time
from enum import Enum
from threading import Lock
from typing import Optional


class CircuitState(Enum):
    """
    Possible states for the circuit breaker.

    An Enum is a set of named values. Each value here represents
    a state the circuit breaker can be in.
    """
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing - reject all requests
    HALF_OPEN = "half_open"  # Testing - allow one test request


class CircuitBreaker:
    """
    Circuit breaker to protect against cascading failures.

    This class implements the circuit breaker pattern:
    - Tracks failures to a backend service
    - Opens the circuit after too many failures
    - Attempts recovery after a timeout

    Attributes:
        failure_threshold: Number of failures before opening the circuit
        recovery_timeout: Seconds to wait before trying again
        success_threshold: Successes needed in half-open to close the circuit
        state: Current state of the circuit breaker
        failure_count: Number of consecutive failures
        success_count: Number of consecutive successes (in half-open)
        last_failure_time: Timestamp of the last failure
        lock: Lock to prevent race conditions
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2
    ):
        """
        Set up the circuit breaker with default settings.

        Args:
            failure_threshold: Failures before opening circuit (default: 5)
            recovery_timeout: Seconds before retry (default: 60)
            success_threshold: Successes needed to close (default: 2)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self.lock = Lock()

    def record_success(self) -> None:
        """
        Record a successful request.

        This should be called after each successful request to the backend.
        In CLOSED state: Reset failure count (things are working)
        In HALF_OPEN state: Count success, close circuit if threshold met
        """
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self._transition_to_closed()
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def record_failure(self) -> None:
        """
        Record a failed request.

        This should be called after each failed request to the backend.
        In CLOSED state: Count failure, open if threshold reached
        In HALF_OPEN state: Open circuit immediately
        """
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self._transition_to_open()
            elif self.failure_count >= self.failure_threshold:
                self._transition_to_open()

    def reset(self) -> None:
        """
        Manually reset the circuit breaker to closed state.

        This is useful for administrators to force the circuit closed
        after fixing an underlying issue.
        """
        with self.lock:
            self._transition_to_closed()

    def _transition_to_open(self) -> None:
        """
        Transition to the OPEN state.

        Called internally when too many failures have occurred.
        """
        self.state = CircuitState.OPEN
        self.failure_count = 0
        self.success_count = 0

    def _transition_to_half_open(self) -> None:
        """
        Transition to the HALF_OPEN state.

        Called internally when the recovery timeout has passed.
        """
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0

    def _transition_to_closed(self) -> None:
        """
        Transition to the CLOSED state.

        Called internally when the backend is healthy again.
        """
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    def _check_recovery(self) -> bool:
        """
        Check if we should attempt to recover.

        Returns:
            True if we transitioned to HALF_OPEN
            False if we're still in OPEN state
        """
        if self.state != CircuitState.OPEN:
            return False
        if self.last_failure_time is None:
            return False

        elapsed = time.time() - self.last_failure_time
        if elapsed >= self.recovery_timeout:
            self._transition_to_half_open()
            return True
        return False


# Global instance - one circuit breaker for the entire application
_circuit_breaker: Optional[CircuitBreaker] = None


def get_circuit_breaker() -> CircuitBreaker:
    """
    Get the global circuit breaker instance.

    Returns:
        The global CircuitBreaker instance
    """
    global _circuit_breaker

    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()

    return _circuit_breaker
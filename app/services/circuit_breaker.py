"""Circuit Breaker - The Safety Switch."""

import time
from enum import Enum
from threading import Lock


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: float | None = None
        self.lock = Lock()

    def record_success(self) -> None:
        with self.lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self._transition_to_closed()
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0

    def record_failure(self) -> None:
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.state == CircuitState.HALF_OPEN:
                self._transition_to_open()
            elif self.failure_count >= self.failure_threshold:
                self._transition_to_open()

    def reset(self) -> None:
        with self.lock:
            self._transition_to_closed()

    def _transition_to_open(self) -> None:
        self.state = CircuitState.OPEN
        self.failure_count = 0
        self.success_count = 0

    def _transition_to_half_open(self) -> None:
        self.state = CircuitState.HALF_OPEN
        self.success_count = 0

    def _transition_to_closed(self) -> None:
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None

    def _check_recovery(self) -> bool:
        if self.state != CircuitState.OPEN:
            return False
        if self.last_failure_time is None:
            return False

        elapsed = time.time() - self.last_failure_time
        if elapsed >= self.recovery_timeout:
            self._transition_to_half_open()
            return True
        return False


_circuit_breaker: CircuitBreaker | None = None


def get_circuit_breaker() -> CircuitBreaker:
    global _circuit_breaker
    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker()
    return _circuit_breaker
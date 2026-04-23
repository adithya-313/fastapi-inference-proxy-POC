"""
app/core/exceptions.py

This file defines custom exceptions and error handlers.

Exceptions are ways to handle errors in Python. When something goes wrong,
we "raise" an exception to stop normal execution and signal that an error occurred.

We also set up "exception handlers" to convert these exceptions into
nice HTTP error responses that clients can understand.
"""

# Import logging for tracking errors
import logging

# Import typing for type hints
from typing import Any

# Import FastAPI components
from fastapi import FastAPI          # The FastAPI app
from fastapi import Request          # The HTTP request object
from fastapi.responses import JSONResponse  # For returning JSON error responses


# Create a logger object for this module
logger = logging.getLogger(__name__)


# Define custom exception classes
# These are like custom error types we can raise when something goes wrong


class RateLimitExceeded(Exception):
    """
    Exception raised when a client exceeds their rate limit.

    This exception is raised by the rate limiter when a user tries
    to make too many requests in a short time period.
    """
    pass  # 'pass' means "do nothing" - we just need the class to exist


class CircuitOpenError(Exception):
    """
    Exception raised when the circuit breaker is open.

    This exception is raised when the backend service is failing
    and we need to "fail fast" to prevent cascading failures.
    """
    pass


def setup_exception_handlers(app: FastAPI) -> None:
    """
    Set up custom handlers for our exceptions.

    When these exceptions are raised in our code, FastAPI will
    automatically call these handler functions and return the
    appropriate HTTP response to the client.

    Args:
        app: The FastAPI application instance
    """
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        """
        Handle RateLimitExceeded exceptions.

        When this exception is raised, return a 429 Too Many Requests response.

        Args:
            request: The HTTP request that caused the error
            exc: The exception that was raised

        Returns:
            JSONResponse: A 429 response with error details
        """
        logger.warning(f"Rate limit exceeded: {exc}")
        return JSONResponse(
            status_code=429,  # HTTP 429 = Too Many Requests
            content={
                "error": "rate_limit_exceeded",
                "detail": str(exc)  # Convert exception to string
            },
        )

    @app.exception_handler(CircuitOpenError)
    async def circuit_open_handler(request: Request, exc: CircuitOpenError) -> JSONResponse:
        """
        Handle CircuitOpenError exceptions.

        When this exception is raised, return a 503 Service Unavailable response.

        Args:
            request: The HTTP request that caused the error
            exc: The exception that was raised

        Returns:
            JSONResponse: A 503 response with error details
        """
        logger.warning(f"Circuit breaker open: {exc}")
        return JSONResponse(
            status_code=503,  # HTTP 503 = Service Unavailable
            content={
                "error": "service_unavailable",
                "detail": str(exc)
            },
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
        """
        Handle any unhandled exceptions.

        This is a catch-all handler for unexpected errors.
        It logs the error and returns a 500 Internal Server Error.

        Args:
            request: The HTTP request that caused the error
            exc: The exception that was raised

        Returns:
            JSONResponse: A 500 response with error details
        """
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,  # HTTP 500 = Internal Server Error
            content={
                "error": "internal_server_error",
                "detail": "An unexpected error occurred"
            },
        )
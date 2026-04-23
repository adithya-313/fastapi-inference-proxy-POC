"""Custom exceptions and handlers."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    pass


class CircuitOpenError(Exception):
    pass


def setup_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
        logger.warning(f"Rate limit exceeded: {exc}")
        return JSONResponse(
            status_code=429,
            content={"error": "rate_limit_exceeded", "detail": str(exc)},
        )

    @app.exception_handler(CircuitOpenError)
    async def circuit_open_handler(request: Request, exc: CircuitOpenError) -> JSONResponse:
        logger.warning(f"Circuit breaker open: {exc}")
        return JSONResponse(
            status_code=503,
            content={"error": "service_unavailable", "detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "detail": "An unexpected error occurred"},
        )
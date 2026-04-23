"""API endpoints - The Conveyor Belt."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from app.services.rate_limiter import RateLimiter, get_rate_limiter
from app.services.circuit_breaker import CircuitBreaker, CircuitState, get_circuit_breaker
from app.core.exceptions import RateLimitExceeded, CircuitOpenError


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/proxy")
async def proxy_request(
    request: Request,
    payload: dict[str, Any],
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
) -> JSONResponse:
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Proxy request from {client_ip}")

    if not rate_limiter.is_allowed(client_ip):
        raise RateLimitExceeded("Rate limit exceeded. Please try again later.")

    if circuit_breaker.state == CircuitState.OPEN:
        raise CircuitOpenError("Circuit breaker is open. Service temporarily unavailable.")

    try:
        result = {"status": "success", "data": payload, "circuit_state": circuit_breaker.state.value}
        circuit_breaker.record_success()
        return JSONResponse(content=result)
    except Exception as e:
        circuit_breaker.record_failure()
        logger.error(f"Proxy request failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status")
async def status(
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
) -> dict[str, Any]:
    return {
        "circuit_state": circuit_breaker.state.value,
        "failure_count": circuit_breaker.failure_count,
        "success_count": circuit_breaker.success_count,
    }


@router.post("/reset-circuit")
async def reset_circuit(
    circuit_breaker: CircuitBreaker = Depends(get_circuit_breaker),
) -> dict[str, str]:
    circuit_breaker.reset()
    return {"status": "Circuit breaker reset successfully"}
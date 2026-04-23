"""
app/api/routes.py

This file contains all our API endpoints (also called "routes").
Think of it as a "conveyor belt" that takes incoming requests,
checks them with the rate limiter and circuit breaker, and sends
them to the LLM service.

Routes defined here:
- POST /generate: Stream LLM response to the client (with circuit breaker protection)
"""

import logging
from typing import AsyncGenerator

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.services.rate_limiter import RateLimiter
from app.services.rate_limiter import get_rate_limiter
from app.services.circuit_breaker import CircuitBreaker
from app.services.circuit_breaker import get_circuit_breaker
from app.services.mock_llm import generate_mock_response


logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateRequest(BaseModel):
    """
    This class defines the shape of data we expect from the client.

    Attributes:
        prompt: The text prompt to send to the LLM
        simulate_error: If True, simulates a backend failure (for testing circuit breaker)

    Example JSON body:
        {
            "prompt": "Write a story about a dragon",
            "simulate_error": false
        }
    """
    prompt: str
    simulate_error: bool = False


async def token_streamer(
    prompt: str,
    cb: CircuitBreaker,
    simulate_error: bool = False
) -> AsyncGenerator[str, None]:
    """
    This is a helper function that converts our LLM words into SSE format.

    SSE (Server-Sent Events) is a way to send data to the browser in chunks.
    Each chunk is formatted as "data: <content>\\n\\n"

    This function:
    1. Gets words from the LLM
    2. Wraps them in SSE format
    3. Records success or failure with the circuit breaker

    Args:
        prompt: The prompt to send to the LLM
        cb: The circuit breaker instance (for recording results)
        simulate_error: If True, will cause the mock to fail (for testing)

    Yields:
        str: SSE-formatted strings containing words from the LLM
    """
    try:
        async for word in generate_mock_response(prompt, simulate_error):
            yield f"data: {word}\n\n"

        await cb.record_success()
        logger.info("Streaming completed successfully - circuit closed")

    except Exception as e:
        await cb.record_failure()
        logger.error(f"Streaming failed with error: {e}")
        yield "data: [ERROR] System failure recorded.\n\n"


@router.post("/generate")
async def generate(
    request: Request,
    payload: GenerateRequest,
    limiter: RateLimiter = Depends(get_rate_limiter),
    cb: CircuitBreaker = Depends(get_circuit_breaker),
) -> StreamingResponse:
    """
    POST /generate endpoint - the main streaming inference endpoint.

    This endpoint:
    1. Gets the client's IP address
    2. Checks if the client is within their rate limit
    3. Checks if the circuit breaker allows requests
    4. If allowed, streams the LLM response back to the client
    5. Records success or failure to the circuit breaker

    Args:
        request: The FastAPI Request object (gives us access to client info)
        payload: The request body (contains the prompt and simulate_error flag)
        limiter: The rate limiter (injected automatically by FastAPI)
        cb: The circuit breaker (injected automatically by FastAPI)

    Returns:
        StreamingResponse: A streaming response with SSE data

    Raises:
        HTTPException (429): If rate limit is exceeded
        HTTPException (503): If circuit breaker is open
    """
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"Generate request from {client_ip} with prompt: {payload.prompt[:50]}...")

    await limiter.check_and_raise(client_ip)

    await cb.check_state()

    return StreamingResponse(
        token_streamer(payload.prompt, cb, payload.simulate_error),
        media_type="text/event-stream",
    )
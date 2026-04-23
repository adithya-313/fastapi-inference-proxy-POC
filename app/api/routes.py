"""
app/api/routes.py

This file contains all our API endpoints (also called "routes").
Think of it as a "conveyor belt" that takes incoming requests,
checks them with the rate limiter, and sends them to the LLM service.

Routes defined here:
- POST /generate: Stream LLM response to the client
"""

# Import Python's built-in logging module
import logging

# Import typing for type hints
from typing import AsyncGenerator

# Import FastAPI components
from fastapi import APIRouter      # Router groups related endpoints together
from fastapi import Depends        # Dependency injection
from fastapi import Request        # Access to the HTTP request object
from fastapi.responses import StreamingResponse  # For streaming data

# Import Pydantic for data validation
from pydantic import BaseModel

# Import our rate limiter
from app.services.rate_limiter import RateLimiter
from app.services.rate_limiter import get_rate_limiter

# Import our mock LLM function
from app.services.mock_llm import generate_mock_response


# Create a logger object for this module
logger = logging.getLogger(__name__)

# Create a router instance
# Routers help organize related endpoints
router = APIRouter()


# Define a Pydantic model for the request body
# Pydantic automatically validates the incoming data
class GenerateRequest(BaseModel):
    """
    This class defines the shape of data we expect from the client.

    Attributes:
        prompt: The text prompt to send to the LLM

    Example JSON body:
        {
            "prompt": "Write a story about a dragon"
        }
    """
    prompt: str


async def token_streamer(prompt: str) -> AsyncGenerator[str, None]:
    """
    This is a helper function that converts our LLM words into SSE format.

    SSE (Server-Sent Events) is a way to send data to the browser in chunks.
    Each chunk is formatted as "data: <content>\n\n"

    This function takes words from the LLM and wraps them in SSE format.

    Args:
        prompt: The prompt to send to the LLM

    Yields:
        str: SSE-formatted strings containing words from the LLM
    """
    # Loop through each word from the LLM
    async for word in generate_mock_response(prompt):
        # Format the word as a Server-Sent Event
        # 'data: ' is the SSE prefix, '\n\n' marks the end of the event
        yield f"data: {word}\n\n"

    # Send a special "done" event to tell the client we're finished
    yield "data: [DONE]\n\n"


@router.post("/generate")
async def generate(
    request: Request,
    payload: GenerateRequest,
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> StreamingResponse:
    """
    POST /generate endpoint - the main streaming inference endpoint.

    This endpoint:
    1. Gets the client's IP address
    2. Checks if the client is within their rate limit
    3. If allowed, streams the LLM response back to the client

    Args:
        request: The FastAPI Request object (gives us access to client info)
        payload: The request body (contains the prompt)
        limiter: The rate limiter (injected automatically by FastAPI)

    Returns:
        StreamingResponse: A streaming response with SSE data

    Raises:
        HTTPException (429): If rate limit is exceeded
    """
    # Get the client's IP address from the request
    # This is used to track how many requests each client makes
    client_ip = request.client.host if request.client else "unknown"

    # Log the request for debugging
    # We truncate the prompt to 50 characters to keep logs clean
    logger.info(f"Generate request from {client_ip} with prompt: {payload.prompt[:50]}...")

    # Check if this client is allowed to make a request
    # This will raise HTTPException (429) if limit exceeded
    await limiter.check_and_raise(client_ip)

    # Create a streaming response
    # The client will receive words one at a time as they are generated
    return StreamingResponse(
        # Our token_streamer function generates the SSE data
        token_streamer(payload.prompt),

        # Tell the client we're sending Server-Sent Events
        media_type="text/event-stream",
    )
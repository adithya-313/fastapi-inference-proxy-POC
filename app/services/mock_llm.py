"""Mock LLM Generator - Simulates a backend LLM inference service."""

import asyncio
from typing import AsyncGenerator


async def generate_mock_response(
    prompt: str,
    simulate_error: bool = False
) -> AsyncGenerator[str, None]:
    """
    Generate a mock streaming response simulating an LLM backend.

    This function simulates a streaming LLM response by yielding
    words one at a time with a small delay between each word.

    Args:
        prompt: The user's prompt (not used in mock, but included for interface compatibility)
        simulate_error: If True, raises a ConnectionError to test circuit breaker

    Yields:
        str: Individual words from the mock response, one at a time

    Raises:
        ConnectionError: If simulate_error is True

    Example:
        async for word in generate_mock_response("Hello"):
            print(word, end=" ")
    """
    if simulate_error:
        raise ConnectionError("Mock backend failure")

    hardcoded_response = (
        "This is a simulated streaming response from the backend system. "
        "The language model is processing your request and generating tokens "
        "in real-time. Each word you see here represents a token that would "
        "normally be produced by a large language model. The streaming "
        "infrastructure allows for immediate delivery of these tokens as "
        "they are generated, providing a smooth user experience without "
        "waiting for the entire response to be completed. This mock response "
        "demonstrates the streaming capability that will be integrated with "
        "our circuit breaker and rate limiter for a production-ready system."
    )

    words = hardcoded_response.split(" ")

    for word in words:
        yield word
        await asyncio.sleep(0.1)
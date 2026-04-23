"""
app/services/mock_llm.py

Mock LLM Generator - Simulates a backend LLM inference service.

This module contains a mock implementation of an LLM (Large Language Model)
backend. It simulates the behavior of a real LLM API for testing purposes.

Why do we need a mock?
- Real LLM APIs cost money and require API keys
- We want to test our rate limiter and circuit breaker without depending on a real backend
- We want fast, reliable tests that don't depend on external services

How it works:
1. We have a hardcoded response string
2. We split it into words
3. We yield one word at a time with a small delay
4. This simulates how a real streaming LLM returns tokens gradually
"""

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
        prompt: The user's prompt
                 (not used in mock, but included for interface compatibility)
        simulate_error: If True, raises a ConnectionError to test circuit breaker

    Yields:
        str: Individual words from the mock response, one at a time

    Raises:
        ConnectionError: If simulate_error is True

    Example:
        async for word in generate_mock_response("Hello world"):
            print(word, end=" ")

        # Output: This is a simulated streaming response from the backend system...
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
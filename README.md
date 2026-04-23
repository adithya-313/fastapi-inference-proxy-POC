# Resilient Streaming Inference Gateway

## Overview

This project is a Proof of Concept (POC) designed to bridge theoretical systems engineering concepts with practical implementation. It acts as a "Smart Middleman" (an API Gateway) between client requests and a backend LLM/inference engine.

Instead of relying heavily on external libraries for system resilience, the core mechanisms—rate limiting, circuit breaking, and observability—are implemented from scratch to deeply explore Python concurrency, memory management, and state manipulation in an asynchronous environment.

## Core Features

**Streaming Inference (The Conveyor Belt)**: A POST /generate endpoint utilizing Server-Sent Events (SSE) and asynchronous Python generators (yield) to stream token-by-token responses without blocking the FastAPI event loop.

**In-Memory Rate Limiter (The Bouncer)**: A custom-built Token Bucket/Fixed Window rate limiter protecting the API from abuse. It utilizes asyncio.Lock to guarantee thread-safe dictionary mutations and prevent race conditions under concurrent load.

**Circuit Breaker (The Safety Switch)**: A state machine (CLOSED, OPEN, HALF-OPEN) designed to protect the mock backend from cascading failures. It manages a global httpx connection pool and fails fast (returning 503 Service Unavailable) when the backend is degraded.

**Custom Observability (The Invisible Stopwatch)**: Zero-overhead request tracking implemented via custom Python context managers (__enter__ / __exit__) and decorators to inject timing logs and handle retries gracefully.

## Tech Stack

- **Framework**: FastAPI (Python)
- **Concurrency**: asyncio
- **Client**: httpx (for internal connection pooling)
- **Deployment**: Docker (Multi-stage build)

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
uvicorn app.main:app --reload
```

## Project Structure

```
resilient-ai-gateway/
├── app/
│   ├── __init__.py           # Package initialization
│   ├── main.py               # FastAPI entry point with lifespan
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py         # POST /generate streaming endpoint
│   ├── core/
│   │   ├── __init__.py
│   │   ├── logging.py        # Logging setup
│   │   └── exceptions.py     # Custom exception handlers
│   └── services/
│       ├── __init__.py
│       ├── rate_limiter.py   # In-memory rate limiter (5 req/60s)
│       ├── circuit_breaker.py # State machine (CLOSED/OPEN/HALF_OPEN)
│       └── mock_llm.py       # Mock LLM streaming response
├── requirements.txt
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/generate` | POST | Streaming inference (SSE) |

## Configuration

- `max_requests`: Rate limit (default: 5 requests)
- `window_seconds`: Rate limit window (default: 60 seconds)
- `failure_threshold`: Circuit breaker threshold (default: 5 failures)
- `recovery_timeout`: Recovery timeout (default: 60 seconds)
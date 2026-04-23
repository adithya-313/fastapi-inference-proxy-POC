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

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/v1/generate` | POST | Streaming inference (SSE) |
| `/api/v1/proxy` | POST | Proxy request (rate limited) |
| `/api/v1/status` | GET | Circuit breaker status |
| `/api/v1/reset-circuit` | POST | Reset circuit breaker |

## Configuration

- `REQUESTS_PER_MINUTE`: Rate limit (default: 60)
- `FAILURE_THRESHOLD`: Circuit breaker threshold (default: 5)
- `RECOVERY_TIMEOUT`: Recovery timeout in seconds (default: 60)
"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.logging import setup_logging
from app.core.exceptions import setup_exception_handlers


setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Resilient AI Gateway...")
    yield
    logger.info("Shutting down Resilient AI Gateway...")


app = FastAPI(
    title="Resilient AI Gateway",
    description="A fault-tolerant AI proxy with rate limiting and circuit breaking",
    version="1.0.0",
    lifespan=lifespan,
)

setup_exception_handlers(app)
app.include_router(router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
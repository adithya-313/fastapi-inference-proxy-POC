"""
app/main.py

This is the main entry point for our FastAPI application.
Think of it as the "front door" of our application.

When you run 'uvicorn app.main:app', FastAPI looks for the 'app' object
defined in this file and uses it to handle all incoming HTTP requests.
"""

# Import Python's built-in 'logging' module for tracking what's happening
import logging

# Import 'asynccontextmanager' - a decorator that helps us run code
# when the application starts and stops
from contextlib import asynccontextmanager

# Import FastAPI - our web framework
from fastapi import FastAPI

# Import our router from the routes module
# This connects our API endpoints to the main app
from app.api.routes import router

# Import our logging setup function
from app.core.logging import setup_logging

# Import our exception handlers
from app.core.exceptions import setup_exception_handlers

# Import the function to get our rate limiter
from app.services.rate_limiter import get_rate_limiter


# Set up logging so we can see what's happening in the console
setup_logging()

# Get a logger object for this module
# This lets us print messages that include the file name and line number
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    This is a special function that runs code when the app starts and stops.
    It's called the "lifespan" because it manages the entire life of the app.

    The 'asynccontextmanager' decorator lets us use 'yield' to separate
    startup code (before yield) from shutdown code (after yield).

    Args:
        app: The FastAPI application instance

    Yields:
        Control back to FastAPI so it can handle requests
    """
    # CODE THAT RUNS WHEN APP STARTS
    logger.info("Starting Resilient AI Gateway...")

    # Get the rate limiter (there's only one in the whole app)
    limiter = get_rate_limiter()

    # Start the cleanup task that resets the rate limit window every 60 seconds
    limiter.start_cleanup()

    # 'yield' pauses this function here - the startup code is done
    # FastAPI will now handle incoming requests
    yield

    # CODE THAT RUNS WHEN APP STOPS
    # Stop the cleanup task to prevent "task was never awaited" warnings
    limiter.stop_cleanup()
    logger.info("Shutting down Resilient AI Gateway...")


# Create the FastAPI application instance
# Think of 'app' as the main controller that directs all HTTP requests
app = FastAPI(
    # Title shown in API documentation (like Swagger UI)
    title="Resilient AI Gateway",

    # Description shown in API documentation
    description="A fault-tolerant AI proxy with rate limiting and streaming inference",

    # Version of our API
    version="1.0.0",

    # Connect our startup/shutdown code
    lifespan=lifespan,
)

# Set up custom error handlers for our exceptions
setup_exception_handlers(app)

# Include our API routes under the /api/v1 prefix
# Now all routes in router.py will start with /api/v1/
app.include_router(router, prefix="/api/v1")


# Simple health check endpoint - useful for load balancers and monitoring
@app.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns a simple JSON response indicating the app is running.
    This endpoint doesn't require any parameters or authentication.

    Returns:
        dict: A dictionary with status "healthy"
    """
    return {"status": "healthy"}
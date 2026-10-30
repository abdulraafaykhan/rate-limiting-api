"""Starts the app: creates FastAPI and connects every piece together.

Run with:  uvicorn app.main:app --port 8001
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.controllers import (
    analytics_controller,
    config_controller,
    data_controller,
    health_controller,
    status_controller,
    users_controller,
)
from app.error_handlers import register_error_handlers
from app.middleware import add_instance_header
from app.redis_client import close_redis_client, get_redis_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run code at startup (before yield) and shutdown (after yield)."""
    # Create the Redis client now, so the first burst of requests does
    # not race to create it several times.
    get_redis_client()
    yield
    # Close the Redis connection cleanly when the server stops.
    await close_redis_client()


def create_app() -> FastAPI:
    """Build and return the configured application."""
    app = FastAPI(title="Rate Limiting API", lifespan=lifespan)

    # Add the X-Served-By header to every response.
    app.middleware("http")(add_instance_header)

    # Turn our custom exceptions into proper HTTP replies.
    register_error_handlers(app)

    # Attach every endpoint group.
    app.include_router(data_controller.router)
    app.include_router(status_controller.router)
    app.include_router(config_controller.router)
    app.include_router(analytics_controller.router)
    app.include_router(health_controller.router)
    app.include_router(users_controller.router)

    # A Vite production build can be served from the same origin as the API.
    frontend = Path(__file__).resolve().parents[1] / "frontend" / "dist"
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="ui")

    return app


# The object that uvicorn looks for.
app = create_app()

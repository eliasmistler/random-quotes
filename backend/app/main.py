"""FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.services.websocket import manager

log = logging.getLogger(__name__)

# Heartbeat interval in seconds (sends ping to keep WebSocket connections alive)
HEARTBEAT_INTERVAL = 30


async def heartbeat_task() -> None:
    """Background task that sends periodic heartbeats to all WebSocket connections."""
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        await manager.send_heartbeat()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application lifespan events."""
    # Start heartbeat background task
    task = asyncio.create_task(heartbeat_task())
    log.info("WebSocket heartbeat task started")
    yield
    # Cancel heartbeat task on shutdown
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    log.info("WebSocket heartbeat task stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix=settings.api_prefix)

    return app


app = create_app()

"""LLM Manager with auto-scaling for Ollama container.

This module manages the lifecycle of the Ollama container:
- Starts the container when a bot is added to a game
- Automatically stops the container after 5 minutes of inactivity
- Tracks usage to determine when to scale down

Supports two modes:
1. Docker Compose mode: Ollama runs as a separate service (managed externally)
2. Standalone mode: Backend manages Ollama container via Docker SDK
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import AsyncGenerator

import httpx

logger = logging.getLogger(__name__)

# Configuration - can be overridden by environment variables
IDLE_TIMEOUT_SECONDS = int(os.environ.get("LLM_IDLE_TIMEOUT", "300"))  # 5 minutes
HEALTH_CHECK_INTERVAL = int(os.environ.get("LLM_HEALTH_CHECK_INTERVAL", "30"))  # seconds
CONTAINER_NAME = os.environ.get("LLM_CONTAINER_NAME", "random-quotes-ollama")
OLLAMA_IMAGE = os.environ.get("OLLAMA_IMAGE", "ollama/ollama:latest")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")

# Detect if we're running in Docker Compose (Ollama as separate service)
DOCKER_COMPOSE_MODE = os.environ.get("DOCKER_COMPOSE_MODE", "").lower() == "true"


@dataclass
class LLMManagerState:
    """State for the LLM manager."""

    last_activity: float = 0.0
    is_starting: bool = False
    is_running: bool = False
    container_id: str | None = None
    model_ready: bool = False
    _shutdown_task: asyncio.Task | None = field(default=None, repr=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)


# Global state
_state = LLMManagerState()


def _get_docker_client():
    """Get a Docker client instance."""
    try:
        import docker

        return docker.from_env()
    except ImportError:
        logger.debug("Docker SDK not installed - LLM auto-scaling disabled")
        return None
    except Exception as e:
        logger.debug(f"Failed to create Docker client: {e}")
        return None


async def record_activity():
    """Record that the LLM was used, updating the last activity timestamp."""
    _state.last_activity = time.time()
    logger.debug(f"LLM activity recorded at {_state.last_activity}")


async def check_ollama_health() -> bool:
    """Check if Ollama is available and responding."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


async def is_ollama_running() -> bool:
    """Check if Ollama is currently available."""
    # In Docker Compose mode, just check if the service is responding
    if DOCKER_COMPOSE_MODE:
        return await check_ollama_health()

    # In standalone mode, check the container status
    client = _get_docker_client()
    if client is None:
        # No Docker client - check if Ollama is responding anyway
        return await check_ollama_health()

    try:
        container = client.containers.get(CONTAINER_NAME)
        return container.status == "running"
    except Exception:
        return False


async def start_ollama() -> bool:
    """Start the Ollama service if not already running.

    In Docker Compose mode, this just checks if Ollama is available.
    In standalone mode, this manages the container lifecycle.

    Returns True if Ollama is available, False otherwise.
    """
    async with _state._lock:
        if _state.is_starting:
            logger.debug("Ollama is already starting, waiting...")
            # Wait for startup to complete
            for _ in range(60):
                await asyncio.sleep(1)
                if _state.is_running and not _state.is_starting:
                    return True
            return False

        if _state.is_running:
            await record_activity()
            return True

        _state.is_starting = True

    try:
        # In Docker Compose mode, Ollama should already be running as a service
        if DOCKER_COMPOSE_MODE:
            is_healthy = await check_ollama_health()
            if is_healthy:
                logger.info("Ollama service is available (Docker Compose mode)")
                _state.is_running = True
                await record_activity()
                await _ensure_model_available()
                return True
            else:
                logger.warning("Ollama service not available in Docker Compose mode")
                return False

        # Standalone mode - manage container with Docker SDK
        client = _get_docker_client()
        if client is None:
            # No Docker client - check if Ollama is responding anyway (maybe running externally)
            is_healthy = await check_ollama_health()
            if is_healthy:
                logger.info("Ollama is available (externally managed)")
                _state.is_running = True
                await record_activity()
                await _ensure_model_available()
                _ensure_shutdown_monitor()
                return True
            logger.warning("Docker client not available and Ollama not responding")
            return False

        # Check if container exists
        try:
            container = client.containers.get(CONTAINER_NAME)
            if container.status == "running":
                logger.info("Ollama container already running")
                _state.is_running = True
                _state.container_id = container.id
                await record_activity()
                await _wait_for_ollama_ready()
                await _ensure_model_available()
                _ensure_shutdown_monitor()
                return True
            elif container.status in ("exited", "created"):
                logger.info("Starting existing Ollama container")
                container.start()
                _state.container_id = container.id
        except Exception:
            # Container doesn't exist, create it
            logger.info("Creating new Ollama container")
            try:
                container = client.containers.run(
                    OLLAMA_IMAGE,
                    name=CONTAINER_NAME,
                    detach=True,
                    ports={"11434/tcp": 11434},
                    environment={"OLLAMA_HOST": "0.0.0.0"},
                    # Don't use restart policy for auto-scaling
                )
                _state.container_id = container.id
            except Exception as e:
                logger.error(f"Failed to create Ollama container: {e}")
                return False

        _state.is_running = True

        # Wait for Ollama to be ready
        logger.info("Waiting for Ollama to be ready...")
        ready = await _wait_for_ollama_ready()
        if not ready:
            logger.error("Ollama failed to become ready")
            return False

        # Pull the model if needed
        await _ensure_model_available()

        await record_activity()
        _ensure_shutdown_monitor()

        logger.info("Ollama container started and ready")
        return True

    except Exception as e:
        logger.error(f"Failed to start Ollama: {e}")
        return False
    finally:
        _state.is_starting = False


async def _wait_for_ollama_ready(timeout: float = 60.0) -> bool:
    """Wait for Ollama API to be ready."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        if await check_ollama_health():
            return True
        await asyncio.sleep(1)
    return False


async def _ensure_model_available():
    """Ensure the LLM model is downloaded."""
    if _state.model_ready:
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                if any(OLLAMA_MODEL in m for m in models):
                    _state.model_ready = True
                    logger.info(f"Model {OLLAMA_MODEL} is available")
                    return

                # Model not found, try to pull it
                logger.info(f"Pulling model {OLLAMA_MODEL}... (this may take a while)")
                async with httpx.AsyncClient(timeout=600.0) as pull_client:
                    pull_response = await pull_client.post(
                        f"{OLLAMA_URL}/api/pull",
                        json={"name": OLLAMA_MODEL, "stream": False},
                    )
                    if pull_response.status_code == 200:
                        _state.model_ready = True
                        logger.info(f"Model {OLLAMA_MODEL} pulled successfully")
                    else:
                        logger.warning(f"Failed to pull model: {pull_response.status_code}")
    except Exception as e:
        logger.warning(f"Failed to ensure model available: {e}")


async def stop_ollama():
    """Stop the Ollama container (standalone mode only)."""
    # Don't stop in Docker Compose mode - the service is managed externally
    if DOCKER_COMPOSE_MODE:
        logger.debug("Skipping stop in Docker Compose mode")
        _state.is_running = False
        return

    async with _state._lock:
        if not _state.is_running:
            return

        client = _get_docker_client()
        if client is None:
            _state.is_running = False
            return

        try:
            container = client.containers.get(CONTAINER_NAME)
            logger.info("Stopping Ollama container due to inactivity")
            container.stop(timeout=10)
            _state.is_running = False
            _state.container_id = None
            _state.model_ready = False
            logger.info("Ollama container stopped")
        except Exception as e:
            logger.warning(f"Failed to stop Ollama container: {e}")
            _state.is_running = False


def _ensure_shutdown_monitor():
    """Ensure the shutdown monitor task is running."""
    # Don't run shutdown monitor in Docker Compose mode
    if DOCKER_COMPOSE_MODE:
        return

    if _state._shutdown_task is None or _state._shutdown_task.done():
        _state._shutdown_task = asyncio.create_task(_shutdown_monitor())


async def _shutdown_monitor():
    """Background task that monitors for inactivity and shuts down Ollama."""
    logger.info(f"Starting Ollama shutdown monitor (timeout: {IDLE_TIMEOUT_SECONDS}s)")
    while _state.is_running:
        await asyncio.sleep(HEALTH_CHECK_INTERVAL)

        if not _state.is_running:
            break

        idle_time = time.time() - _state.last_activity
        if idle_time >= IDLE_TIMEOUT_SECONDS:
            logger.info(f"Ollama idle for {idle_time:.0f}s, shutting down")
            await stop_ollama()
            break
        else:
            remaining = IDLE_TIMEOUT_SECONDS - idle_time
            logger.debug(f"Ollama idle for {idle_time:.0f}s, {remaining:.0f}s until shutdown")

    logger.info("Ollama shutdown monitor stopped")


@asynccontextmanager
async def llm_context() -> AsyncGenerator[bool, None]:
    """Context manager for LLM operations.

    Ensures the LLM is running and records activity.
    Yields True if LLM is available, False otherwise.
    """
    available = await start_ollama()
    try:
        yield available
    finally:
        if available:
            await record_activity()


async def get_llm_status() -> dict:
    """Get the current status of the LLM manager."""
    idle_time = time.time() - _state.last_activity if _state.last_activity > 0 else 0
    return {
        "mode": "docker_compose" if DOCKER_COMPOSE_MODE else "standalone",
        "is_running": _state.is_running,
        "is_starting": _state.is_starting,
        "container_id": _state.container_id,
        "model_ready": _state.model_ready,
        "model": OLLAMA_MODEL,
        "ollama_url": OLLAMA_URL,
        "last_activity": _state.last_activity,
        "idle_seconds": idle_time,
        "shutdown_in_seconds": max(0, IDLE_TIMEOUT_SECONDS - idle_time) if _state.is_running else 0,
    }

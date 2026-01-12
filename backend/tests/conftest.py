"""Pytest fixtures for API testing."""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.store import clear_store


@pytest.fixture(autouse=True)
def clean_store():
    """Clear the game store before and after each test."""
    clear_store()
    yield
    clear_store()


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)

"""Tests for API endpoints."""

from fastapi.testclient import TestClient


def test_health_check_returns_healthy_status(client: TestClient) -> None:
    """Test that health check endpoint returns healthy status."""
    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"

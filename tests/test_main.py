"""Tests for foundation and health endpoints in DataGuard AI."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_root_endpoint() -> None:
    """Test that the root endpoint returns 200 OK and valid status payload."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert data["app"] == "DataGuard AI"
    assert "version" in data
    assert "message" in data


def test_health_check_endpoint() -> None:
    """Test that the health check endpoint returns 200 OK and healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "DataGuard AI"

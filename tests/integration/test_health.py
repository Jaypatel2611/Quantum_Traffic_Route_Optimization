import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_allows_cors_from_docker_compose_frontend_origin():
    response = client.get("/health", headers={"Origin": "http://localhost:4173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:4173"

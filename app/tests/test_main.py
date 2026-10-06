from fastapi.testclient import TestClient
from src.main import app, APP_VERSION

client = TestClient(app)


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to your minimal Python API!"}


def test_greet_user():
    response = client.get("/api/greet?name=Alice")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Hello, Alice!",
        "status": "success"
    }


def test_greet_user_default():
    response = client.get("/api/greet")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Hello, Guest!",
        "status": "success"
    }


def test_greet_bad_path():
    response = client.get("/greet")
    assert response.status_code == 404
    assert response.json() == {
        "detail": "Not Found"
    }


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "uptime_seconds" in data


def test_get_version():
    response = client.get("/api/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert data["status"] == "success"
    assert data["version"] == APP_VERSION


def test_get_metrics():
    response = client.get("/api/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "# HELP" in response.text

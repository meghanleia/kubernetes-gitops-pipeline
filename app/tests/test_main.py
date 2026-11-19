from types import SimpleNamespace
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from prometheus_client.parser import text_string_to_metric_families
import src.main as main
from src.main import app

client = TestClient(app)
COUNT = "http_requests_total"
OBSERVATIONS = "http_request_duration_seconds_count"
DURATION_SUM = "http_request_duration_seconds_sum"


def metric_value(name, endpoint):
    """Read a sample without creating a new label set; absent means zero."""
    labels = {"method": "GET", "endpoint": endpoint}
    return REGISTRY.get_sample_value(name, labels) or 0


def request_metrics_snapshot():
    """Capture only application request metrics, excluding process metrics."""
    return {
        (sample.name, tuple(sorted(sample.labels.items()))): sample.value
        for metric in (main.REQUEST_COUNT, main.HTTP_REQUEST_DURATION)
        for family in metric.collect()
        for sample in family.samples
    }


def recorded_endpoints():
    return {
        dict(label_pairs)["endpoint"]
        for _, label_pairs in request_metrics_snapshot()
    }


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
    assert data["version"] == main.APP_VERSION


def test_get_metrics():
    # Ensure both application metrics have samples to expose.
    assert client.get("/").status_code == 200
    before = request_metrics_snapshot()

    # Check after each scrape: instrumentation would run after generating
    # the response, so inspecting only that response can miss the bug.
    for _ in range(2):
        response = client.get("/api/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        samples = {
            (sample.name, tuple(sorted(sample.labels.items()))): sample.value
            for family in text_string_to_metric_families(response.text)
            for sample in family.samples
        }
        root_labels = tuple(sorted({"method": "GET", "endpoint": "/"}.items()))
        for name in (COUNT, OBSERVATIONS, DURATION_SUM):
            key = (name, root_labels)
            assert samples[key] == before[key]
        assert request_metrics_snapshot() == before


@pytest.mark.parametrize("path", ["/", "/api/greet", "/health", "/api/version"])
def test_each_request_is_recorded_once(path):
    # Compare deltas because the registry persists across tests.
    before = [metric_value(name, path) for name in (COUNT, OBSERVATIONS)]
    assert client.get(path).status_code == 200
    after = [metric_value(name, path) for name in (COUNT, OBSERVATIONS)]
    assert after == [number + 1 for number in before]


def test_missing_paths_share_one_label():
    before_labels = recorded_endpoints()
    before = [metric_value(name, "unmatched") for name in (COUNT, OBSERVATIONS)]
    for path in ("/missing-one", "/missing-two"):
        assert client.get(path).status_code == 404
    after = [metric_value(name, "unmatched") for name in (COUNT, OBSERVATIONS)]
    assert after == [number + 2 for number in before]
    assert recorded_endpoints() == before_labels | {"unmatched"}


def test_route_templates_and_duration(monkeypatch):
    test_app = FastAPI()
    test_app.middleware("http")(main.monitor_requests)

    @test_app.get("/items/{item_id}")
    def item(item_id: int):
        return {"id": item_id}

    # Patch this module's clock, not Python's shared time module.
    ticks = iter([10.0, 10.25, 20.0, 20.25])
    monkeypatch.setattr(main, "time", SimpleNamespace(perf_counter=lambda: next(ticks)))
    route = "/items/{item_id}"
    names = (COUNT, OBSERVATIONS, DURATION_SUM)
    before = [metric_value(name, route) for name in names]
    before_labels = recorded_endpoints()
    with TestClient(test_app) as test_client:
        assert test_client.get("/items/123").status_code == 200
        assert test_client.get("/items/456").status_code == 200
    after = [metric_value(name, route) for name in names]
    assert after == pytest.approx([before[0] + 2, before[1] + 2, before[2] + 0.5])
    assert recorded_endpoints() == before_labels | {route}


def test_unhandled_error_is_recorded():
    test_app = FastAPI()
    test_app.middleware("http")(main.monitor_requests)

    @test_app.get("/broken")
    def broken():
        raise RuntimeError("Example failure")

    before = [metric_value(name, "/broken") for name in (COUNT, OBSERVATIONS)]
    with TestClient(test_app, raise_server_exceptions=False) as test_client:
        assert test_client.get("/broken").status_code == 500
    after = [metric_value(name, "/broken") for name in (COUNT, OBSERVATIONS)]
    assert after == [number + 1 for number in before]

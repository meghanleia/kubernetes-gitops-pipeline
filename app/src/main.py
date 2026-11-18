import time
from fastapi import FastAPI, status, Response, Request
from fastapi.responses import JSONResponse
from datetime import UTC, datetime
from prometheus_client import Histogram, Counter, generate_latest, CONTENT_TYPE_LATEST

# Initialize the FastAPI application
app = FastAPI(title="Minimal Python API")

# Track application start time for the health check
START_TIME = datetime.now(UTC)

APP_VERSION = "1.0.0"

# Track for Prometheus metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total number of HTTP requests received for endpoint",
    ["method", "endpoint"]
)

# Track for Prometheus metrics
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

METRICS_PATH = "/api/metrics"
UNMATCHED_ENDPOINT = "unmatched"


@app.middleware("http")
async def monitor_requests(request: Request, call_next):

    if request.url.path == METRICS_PATH:
        return await call_next(request)

    start_time = time.perf_counter()
    try:
        return await call_next(request)
    finally:
        duration = time.perf_counter() - start_time
        route = request.scope.get("route")
        endpoint = getattr(route, "path", None) or UNMATCHED_ENDPOINT
        labels = {"method": request.method, "endpoint": endpoint}
 
        REQUEST_COUNT.labels(**labels).inc()
        HTTP_REQUEST_DURATION.labels(**labels).observe(duration)


@app.get("/")
def read_root():
    """Basic root landing endpoint."""
    return {"message": "Welcome to your minimal Python API!"}


@app.get("/api/greet")
def greet_user(name: str = "Guest"):
    """A basic functional endpoint that accepts a query parameter."""
    return {
        "message": f"Hello, {name}!",
        "status": "success"
    }


@app.get("/health", status_code=status.HTTP_200_OK)
def health_check():
    """
    Health check endpoint for monitoring tools or Kubernetes probes.
    Returns 200 OK if the application server is up and responsive.
    """
    uptime = datetime.now(UTC) - START_TIME

    return JSONResponse(
        content={
            "status": "healthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "uptime_seconds": round(uptime.total_seconds(), 2)
        }
    )


@app.get("/api/version")
def get_version():
    """Endpoint to return the current version of the API."""
    return {
        "version": APP_VERSION,
        "status": "success"
    }


@app.get(METRICS_PATH)
def get_metrics():
    """Endpoint to return API metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

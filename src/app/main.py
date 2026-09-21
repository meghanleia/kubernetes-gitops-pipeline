from fastapi import FastAPI, status, Response
from fastapi.responses import JSONResponse
from datetime import UTC, datetime
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

# Initialize the FastAPI application
app = FastAPI(title="Minimal Python API")

# Track application start time for the health check
START_TIME = datetime.now(UTC)

APP_VERSION = "0.1.0"

REQUEST_COUNT = Counter(
    "http_requests_total", 
    "Total number of HTTP requests received for endpoint", 
    ["method", "endpoint"]
)

@app.get("/")
def read_root():
    """Basic root landing endpoint."""
    REQUEST_COUNT.labels(method="GET", endpoint="/").inc()
    return {"message": "Welcome to your minimal Python API!"}

@app.get("/api/greet")
def greet_user(name: str = "Guest"):
    """A basic functional endpoint that accepts a query parameter."""
    REQUEST_COUNT.labels(method="GET", endpoint="/api/greet").inc()
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
    REQUEST_COUNT.labels(method="GET", endpoint="/health").inc()
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
    REQUEST_COUNT.labels(method="GET", endpoint="/api/version").inc()
    return {
        "version": APP_VERSION,
        "status": "success"
    }

@app.get("/api/metrics")
def get_metrics():
    """Endpoint to return API metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
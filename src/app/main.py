from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from datetime import UTC, datetime

# Initialize the FastAPI application
app = FastAPI(title="Minimal Python API")

# Track application start time for the health check
START_TIME = datetime.now(UTC)

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

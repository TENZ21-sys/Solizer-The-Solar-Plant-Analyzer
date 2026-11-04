"""
SoliZer Intelligence Platform - Health Check Router.

Provides a simple health check endpoint to verify the API is running
and report the current service version.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Health Check")
def health_check():
    """
    Return the current health status of the SoliZer backend service.

    Returns a JSON object with:
    - **status**: Always "healthy" if the service is reachable.
    - **version**: The current API version string.
    - **service**: The human-readable service name.
    """
    return {
        "status": "healthy",
        "version": "1.0.0-mvp",
        "service": "SoliZer Intelligence Platform",
    }

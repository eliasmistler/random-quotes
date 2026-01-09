"""Common Pydantic models used across the application."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    version: str

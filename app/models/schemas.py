"""Pydantic models for request/response validation."""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class GistFile(BaseModel):
    """Represents a single file within a gist."""

    filename: str
    type: str | None = None
    language: str | None = None
    raw_url: HttpUrl
    size: int


class GistOwner(BaseModel):
    """Simplified owner information."""

    login: str
    id: int
    avatar_url: HttpUrl
    html_url: HttpUrl


class Gist(BaseModel):
    """Represents a GitHub Gist."""

    id: str
    url: HttpUrl
    html_url: HttpUrl
    description: str | None = None
    public: bool
    created_at: datetime
    updated_at: datetime
    comments: int
    files: dict[str, GistFile]
    owner: GistOwner | None = None
    truncated: bool = False


class GistListResponse(BaseModel):
    """Response model for gist list endpoint."""

    username: str
    page: int
    per_page: int
    gists: list[Gist]
    total_count: int | None = None
    cached: bool = False
    cache_expires_at: datetime | None = None


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str
    message: str
    detail: str | None = None


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str = "1.0.0"
    github_api_reachable: bool = True

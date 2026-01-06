"""Custom exceptions and FastAPI exception handlers."""

from fastapi import Request
from fastapi.responses import JSONResponse


class GitHubUserNotFoundError(Exception):
    """Raised when GitHub user doesn't exist."""

    def __init__(self, username: str):
        self.username = username
        super().__init__(f"GitHub user '{username}' not found")


class GitHubAPIError(Exception):
    """Raised when GitHub API returns an error."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"GitHub API error ({status_code}): {message}")


class GitHubRateLimitError(Exception):
    """Raised when GitHub API rate limit is exceeded."""

    def __init__(self, reset_time: str | None = None):
        self.reset_time = reset_time
        super().__init__("GitHub API rate limit exceeded")


async def github_user_not_found_handler(
    request: Request,
    exc: GitHubUserNotFoundError,
) -> JSONResponse:
    """Handle GitHubUserNotFoundError."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "user_not_found",
            "message": f"GitHub user '{exc.username}' not found",
            "detail": "The specified username does not exist on GitHub",
        },
    )


async def github_api_error_handler(
    request: Request,
    exc: GitHubAPIError,
) -> JSONResponse:
    """Handle GitHubAPIError."""
    return JSONResponse(
        status_code=502,
        content={
            "error": "github_api_error",
            "message": "Error communicating with GitHub API",
            "detail": exc.message,
        },
    )


async def github_rate_limit_handler(
    request: Request,
    exc: GitHubRateLimitError,
) -> JSONResponse:
    """Handle GitHubRateLimitError."""
    headers = {}
    if exc.reset_time:
        headers["X-RateLimit-Reset"] = exc.reset_time

    return JSONResponse(
        status_code=429,
        headers=headers,
        content={
            "error": "rate_limit_exceeded",
            "message": "GitHub API rate limit exceeded",
            "detail": f"Rate limit resets at: {exc.reset_time}" if exc.reset_time else None,
        },
    )

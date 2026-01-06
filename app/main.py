"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.exceptions import (
    GitHubAPIError,
    GitHubRateLimitError,
    GitHubUserNotFoundError,
    github_api_error_handler,
    github_rate_limit_handler,
    github_user_not_found_handler,
)
from app.routers import gists, health
from app.services.cache import TTLCache
from app.services.github_client import GitHubClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

github_client: GitHubClient | None = None
cache: TTLCache | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles startup and shutdown of resources.
    """
    global github_client, cache

    settings = get_settings()
    logger.info(f"Starting {settings.app_name}")

    github_client = GitHubClient(settings)
    await github_client.start()

    cache = TTLCache(
        ttl_seconds=settings.cache_ttl_seconds,
        max_size=settings.cache_max_size,
    )
    await cache.start()

    logger.info("Services initialized successfully")

    yield

    logger.info("Shutting down services")
    await github_client.close()
    await cache.stop()


def create_app() -> FastAPI:
    """Application factory."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="A caching proxy for GitHub Gists API",
        version="1.0.0",
        lifespan=lifespan,
    )

    app.add_exception_handler(GitHubUserNotFoundError, github_user_not_found_handler)
    app.add_exception_handler(GitHubAPIError, github_api_error_handler)
    app.add_exception_handler(GitHubRateLimitError, github_rate_limit_handler)

    async def get_github_client_dep():
        return github_client

    async def get_cache_dep():
        return cache

    app.dependency_overrides[gists.get_github_client] = get_github_client_dep
    app.dependency_overrides[gists.get_cache] = get_cache_dep
    app.dependency_overrides[health.get_github_client] = get_github_client_dep
    app.dependency_overrides[health.get_cache] = get_cache_dep

    app.include_router(health.router)
    app.include_router(gists.router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )

"""Shared test fixtures and sample data."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from app.config import Settings
from app.main import app
from app.models.schemas import Gist, GistFile, GistOwner
from app.routers import gists, health
from app.services.cache import TTLCache
from app.services.github_client import GitHubClient

# Sample test data matching GitHub API response for octocat
SAMPLE_GIST_DATA = {
    "id": "6cad326836d38bd3a7ae",
    "url": "https://api.github.com/gists/6cad326836d38bd3a7ae",
    "html_url": "https://gist.github.com/octocat/6cad326836d38bd3a7ae",
    "description": "Hello world!",
    "public": True,
    "created_at": "2014-10-01T16:19:34Z",
    "updated_at": "2025-12-23T23:51:45Z",
    "comments": 291,
    "truncated": False,
    "files": {
        "hello_world.rb": {
            "filename": "hello_world.rb",
            "type": "application/x-ruby",
            "language": "Ruby",
            "raw_url": "https://gist.githubusercontent.com/octocat/6cad326836d38bd3a7ae/raw/hello_world.rb",
            "size": 175,
        }
    },
    "owner": {
        "login": "octocat",
        "id": 583231,
        "avatar_url": "https://avatars.githubusercontent.com/u/583231?v=4",
        "html_url": "https://github.com/octocat",
    },
}


@pytest.fixture
def settings():
    """Test settings."""
    return Settings(
        cache_ttl_seconds=60,
        cache_max_size=100,
        github_api_timeout=5.0,
    )


@pytest.fixture
def sample_gist_data():
    """Sample gist data for testing."""
    return SAMPLE_GIST_DATA


@pytest.fixture
def sample_gist(sample_gist_data) -> Gist:
    """Sample Gist model for testing."""
    return Gist(
        id=sample_gist_data["id"],
        url=sample_gist_data["url"],
        html_url=sample_gist_data["html_url"],
        description=sample_gist_data["description"],
        public=sample_gist_data["public"],
        created_at=sample_gist_data["created_at"],
        updated_at=sample_gist_data["updated_at"],
        comments=sample_gist_data["comments"],
        files={
            k: GistFile(**v) for k, v in sample_gist_data["files"].items()
        },
        owner=GistOwner(**sample_gist_data["owner"]),
        truncated=sample_gist_data["truncated"],
    )


@pytest_asyncio.fixture
async def cache(settings):
    """Fresh cache instance for each test."""
    cache = TTLCache(
        ttl_seconds=settings.cache_ttl_seconds,
        max_size=settings.cache_max_size,
    )
    await cache.start()
    yield cache
    await cache.stop()


@pytest.fixture
def mock_github_client(sample_gist):
    """Mocked GitHub client."""
    mock_client = AsyncMock(spec=GitHubClient)
    mock_client.get_user_gists.return_value = [sample_gist]
    mock_client.check_health.return_value = True
    return mock_client


@pytest_asyncio.fixture
async def test_client(mock_github_client, cache):
    """AsyncClient for testing with mocked dependencies."""
    app.dependency_overrides[gists.get_github_client] = lambda: mock_github_client
    app.dependency_overrides[gists.get_cache] = lambda: cache
    app.dependency_overrides[health.get_github_client] = lambda: mock_github_client
    app.dependency_overrides[health.get_cache] = lambda: cache

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()

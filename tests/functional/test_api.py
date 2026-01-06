"""Functional tests that make real HTTP calls to the running server."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import get_settings
from app.main import app
from app.routers import gists, health
from app.services.cache import TTLCache
from app.services.github_client import GitHubClient


class TestAPIFunctional:
    """
    Functional tests that make real HTTP calls to the running server.

    These tests hit the actual GitHub API.
    """

    @pytest_asyncio.fixture
    async def real_client(self):
        """Client configured to use real GitHub API."""
        settings = get_settings()

        github_client = GitHubClient(settings)
        await github_client.start()

        cache = TTLCache(
            ttl_seconds=settings.cache_ttl_seconds,
            max_size=settings.cache_max_size,
        )
        await cache.start()

        app.dependency_overrides[gists.get_github_client] = lambda: github_client
        app.dependency_overrides[gists.get_cache] = lambda: cache
        app.dependency_overrides[health.get_github_client] = lambda: github_client
        app.dependency_overrides[health.get_cache] = lambda: cache

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            yield client

        await github_client.close()
        await cache.stop()
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_octocat_gists(self, real_client):
        """Test fetching gists for the octocat user (real API call)."""
        response = await real_client.get("/octocat")

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "octocat"
        assert data["page"] == 1
        assert data["per_page"] == 30
        assert isinstance(data["gists"], list)
        assert len(data["gists"]) > 0

        gist = data["gists"][0]
        assert "id" in gist
        assert "html_url" in gist
        assert "files" in gist
        assert "public" in gist

    @pytest.mark.asyncio
    async def test_get_octocat_gists_with_pagination(self, real_client):
        """Test pagination parameters."""
        response = await real_client.get("/octocat?page=1&per_page=2")

        assert response.status_code == 200
        data = response.json()

        assert data["page"] == 1
        assert data["per_page"] == 2
        assert len(data["gists"]) <= 2

    @pytest.mark.asyncio
    async def test_caching_behavior(self, real_client):
        """Test that responses are cached."""
        response1 = await real_client.get("/octocat?per_page=1")
        data1 = response1.json()
        assert data1["cached"] is False

        response2 = await real_client.get("/octocat?per_page=1")
        data2 = response2.json()
        assert data2["cached"] is True
        assert data2["cache_expires_at"] is not None

    @pytest.mark.asyncio
    async def test_nonexistent_user(self, real_client):
        """Test error handling for non-existent user."""
        response = await real_client.get("/this-user-definitely-does-not-exist-12345")

        assert response.status_code == 404
        data = response.json()

        assert data["error"] == "user_not_found"
        assert "not found" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_invalid_pagination_per_page_too_high(self, real_client):
        """Test validation of per_page > 100."""
        response = await real_client.get("/octocat?per_page=101")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_pagination_page_zero(self, real_client):
        """Test validation of page < 1."""
        response = await real_client.get("/octocat?page=0")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_health_endpoint(self, real_client):
        """Test health check endpoint."""
        response = await real_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] in ["healthy", "degraded"]
        assert "version" in data
        assert "github_api_reachable" in data

    @pytest.mark.asyncio
    async def test_liveness_probe(self, real_client):
        """Test liveness probe endpoint."""
        response = await real_client.get("/health/live")

        assert response.status_code == 200
        assert response.json()["status"] == "alive"

    @pytest.mark.asyncio
    async def test_readiness_probe(self, real_client):
        """Test readiness probe endpoint."""
        response = await real_client.get("/health/ready")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"


class TestAPIWithMocks:
    """Tests using mocked GitHub client (from conftest)."""

    @pytest.mark.asyncio
    async def test_get_user_gists_mocked(self, test_client):
        """Test fetching gists with mocked GitHub client."""
        response = await test_client.get("/octocat")

        assert response.status_code == 200
        data = response.json()

        assert data["username"] == "octocat"
        assert len(data["gists"]) == 1
        assert data["gists"][0]["id"] == "6cad326836d38bd3a7ae"

    @pytest.mark.asyncio
    async def test_health_mocked(self, test_client):
        """Test health endpoint with mocked client."""
        response = await test_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["github_api_reachable"] is True

    @pytest.mark.asyncio
    async def test_caching_with_mock(self, test_client, mock_github_client):
        """Test caching behavior with mocked client."""
        response1 = await test_client.get("/testuser")
        assert response1.json()["cached"] is False

        response2 = await test_client.get("/testuser")
        assert response2.json()["cached"] is True

        assert mock_github_client.get_user_gists.call_count == 1

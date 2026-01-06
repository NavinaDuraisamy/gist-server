"""Unit tests for GitHubClient with mocked HTTP."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from app.config import Settings
from app.exceptions import (
    GitHubAPIError,
    GitHubRateLimitError,
    GitHubUserNotFoundError,
)
from app.services.github_client import GitHubClient


class TestGitHubClient:
    """Unit tests for GitHubClient with mocked HTTP."""

    @pytest.fixture
    def client_settings(self):
        """Settings for GitHub client."""
        return Settings(
            github_api_base_url="https://api.github.com",
            github_api_timeout=5.0,
        )

    @pytest.mark.asyncio
    async def test_get_user_gists_success(self, client_settings, sample_gist_data):
        """Test successful gist fetching."""
        client = GitHubClient(client_settings)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [sample_gist_data]

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        client._client = mock_http
        gists = await client.get_user_gists("octocat", page=1, per_page=30)

        assert len(gists) == 1
        assert gists[0].id == "6cad326836d38bd3a7ae"
        assert gists[0].description == "Hello world!"

        mock_http.get.assert_called_once_with(
            "/users/octocat/gists",
            params={"page": 1, "per_page": 30},
        )

    @pytest.mark.asyncio
    async def test_get_user_gists_user_not_found(self, client_settings):
        """Test handling of non-existent user."""
        client = GitHubClient(client_settings)

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        client._client = mock_http

        with pytest.raises(GitHubUserNotFoundError) as exc_info:
            await client.get_user_gists("nonexistent-user-12345")

        assert "nonexistent-user-12345" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_user_gists_rate_limited(self, client_settings):
        """Test handling of rate limit errors."""
        client = GitHubClient(client_settings)

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {
            "X-RateLimit-Remaining": "0",
            "X-RateLimit-Reset": "1234567890",
        }

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        client._client = mock_http

        with pytest.raises(GitHubRateLimitError) as exc_info:
            await client.get_user_gists("octocat")

        assert exc_info.value.reset_time == "1234567890"

    @pytest.mark.asyncio
    async def test_get_user_gists_forbidden_not_rate_limit(self, client_settings):
        """Test handling of 403 that's not rate limiting."""
        client = GitHubClient(client_settings)

        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.headers = {"X-RateLimit-Remaining": "100"}

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        client._client = mock_http

        with pytest.raises(GitHubAPIError) as exc_info:
            await client.get_user_gists("octocat")

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_get_user_gists_timeout(self, client_settings):
        """Test handling of timeout errors."""
        client = GitHubClient(client_settings)

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

        client._client = mock_http

        with pytest.raises(GitHubAPIError) as exc_info:
            await client.get_user_gists("octocat")

        assert exc_info.value.status_code == 504
        assert "timed out" in exc_info.value.message.lower()

    @pytest.mark.asyncio
    async def test_get_user_gists_connection_error(self, client_settings):
        """Test handling of connection errors."""
        client = GitHubClient(client_settings)

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )

        client._client = mock_http

        with pytest.raises(GitHubAPIError) as exc_info:
            await client.get_user_gists("octocat")

        assert exc_info.value.status_code == 502

    @pytest.mark.asyncio
    async def test_get_user_gists_server_error(self, client_settings):
        """Test handling of server errors."""
        client = GitHubClient(client_settings)

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        client._client = mock_http

        with pytest.raises(GitHubAPIError) as exc_info:
            await client.get_user_gists("octocat")

        assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_get_user_gists_not_initialized(self, client_settings):
        """Test error when client not initialized."""
        client = GitHubClient(client_settings)

        with pytest.raises(RuntimeError) as exc_info:
            await client.get_user_gists("octocat")

        assert "not initialized" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_check_health_success(self, client_settings):
        """Test successful health check."""
        client = GitHubClient(client_settings)

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        client._client = mock_http

        result = await client.check_health()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_health_failure(self, client_settings):
        """Test failed health check."""
        client = GitHubClient(client_settings)

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(side_effect=Exception("Connection failed"))

        client._client = mock_http

        result = await client.check_health()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_health_not_initialized(self, client_settings):
        """Test health check when client not initialized."""
        client = GitHubClient(client_settings)

        result = await client.check_health()
        assert result is False

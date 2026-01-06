"""Unit tests for Pydantic models."""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.models.schemas import (
    Gist,
    GistFile,
    GistListResponse,
    GistOwner,
    HealthResponse,
)


class TestGistFile:
    """Tests for GistFile model."""

    def test_valid_gist_file(self):
        """Test creating a valid GistFile."""
        file = GistFile(
            filename="test.py",
            type="application/x-python",
            language="Python",
            raw_url="https://gist.githubusercontent.com/user/123/raw/test.py",
            size=100,
        )
        assert file.filename == "test.py"
        assert file.language == "Python"
        assert file.size == 100

    def test_gist_file_optional_fields(self):
        """Test GistFile with optional fields as None."""
        file = GistFile(
            filename="test.txt",
            type=None,
            language=None,
            raw_url="https://gist.githubusercontent.com/user/123/raw/test.txt",
            size=50,
        )
        assert file.type is None
        assert file.language is None

    def test_gist_file_invalid_url(self):
        """Test GistFile with invalid URL."""
        with pytest.raises(ValidationError):
            GistFile(
                filename="test.py",
                raw_url="not-a-url",
                size=100,
            )


class TestGistOwner:
    """Tests for GistOwner model."""

    def test_valid_gist_owner(self):
        """Test creating a valid GistOwner."""
        owner = GistOwner(
            login="octocat",
            id=583231,
            avatar_url="https://avatars.githubusercontent.com/u/583231",
            html_url="https://github.com/octocat",
        )
        assert owner.login == "octocat"
        assert owner.id == 583231


class TestGist:
    """Tests for Gist model."""

    def test_valid_gist(self, sample_gist_data):
        """Test creating a valid Gist."""
        gist = Gist(
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
        assert gist.id == "6cad326836d38bd3a7ae"
        assert gist.public is True
        assert len(gist.files) == 1

    def test_gist_optional_description(self):
        """Test Gist with None description."""
        gist = Gist(
            id="123",
            url="https://api.github.com/gists/123",
            html_url="https://gist.github.com/123",
            description=None,
            public=True,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:00:00Z",
            comments=0,
            files={},
        )
        assert gist.description is None


class TestGistListResponse:
    """Tests for GistListResponse model."""

    def test_valid_response(self):
        """Test creating a valid GistListResponse."""
        response = GistListResponse(
            username="octocat",
            page=1,
            per_page=30,
            gists=[],
            cached=False,
        )
        assert response.username == "octocat"
        assert response.page == 1
        assert response.per_page == 30
        assert response.cached is False

    def test_response_with_cache_info(self):
        """Test GistListResponse with cache metadata."""
        expire_time = datetime.now(timezone.utc)
        response = GistListResponse(
            username="octocat",
            page=1,
            per_page=30,
            gists=[],
            cached=True,
            cache_expires_at=expire_time,
        )
        assert response.cached is True
        assert response.cache_expires_at == expire_time


class TestHealthResponse:
    """Tests for HealthResponse model."""

    def test_default_values(self):
        """Test HealthResponse default values."""
        response = HealthResponse()
        assert response.status == "healthy"
        assert response.version == "1.0.0"
        assert response.github_api_reachable is True

    def test_custom_values(self):
        """Test HealthResponse with custom values."""
        response = HealthResponse(
            status="degraded",
            version="2.0.0",
            github_api_reachable=False,
        )
        assert response.status == "degraded"
        assert response.github_api_reachable is False

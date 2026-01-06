"""Async GitHub API client using httpx."""

import logging
from typing import Any

import httpx

from app.config import Settings
from app.exceptions import (
    GitHubAPIError,
    GitHubRateLimitError,
    GitHubUserNotFoundError,
)
from app.models.schemas import Gist, GistFile, GistOwner

logger = logging.getLogger(__name__)


class GitHubClient:
    """Async client for GitHub Gists API."""

    def __init__(self, settings: Settings):
        self._base_url = settings.github_api_base_url
        self._timeout = settings.github_api_timeout
        self._token = settings.github_token
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "GitHubClient":
        await self.start()
        return self

    async def __aexit__(self, *args) -> None:
        await self.close()

    async def start(self) -> None:
        """Initialize the HTTP client."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=self._timeout,
        )

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_user_gists(
        self,
        username: str,
        page: int = 1,
        per_page: int = 30,
    ) -> list[Gist]:
        """
        Fetch public gists for a GitHub user.

        Args:
            username: GitHub username
            page: Page number (1-indexed)
            per_page: Number of results per page (max 100)

        Returns:
            List of Gist objects

        Raises:
            GitHubUserNotFoundError: If user doesn't exist
            GitHubRateLimitError: If rate limit exceeded
            GitHubAPIError: For other API errors
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Call start() first.")

        try:
            response = await self._client.get(
                f"/users/{username}/gists",
                params={"page": page, "per_page": per_page},
            )

            if response.status_code == 404:
                raise GitHubUserNotFoundError(username)

            if response.status_code == 403:
                remaining = response.headers.get("X-RateLimit-Remaining", "0")
                if remaining == "0":
                    reset_time = response.headers.get("X-RateLimit-Reset")
                    raise GitHubRateLimitError(reset_time)
                raise GitHubAPIError(status_code=403, message="Access forbidden")

            if response.status_code != 200:
                raise GitHubAPIError(
                    status_code=response.status_code,
                    message=response.text,
                )

            data = response.json()
            return [self._parse_gist(gist_data) for gist_data in data]

        except httpx.TimeoutException:
            raise GitHubAPIError(
                status_code=504,
                message="GitHub API request timed out",
            )
        except httpx.RequestError as e:
            raise GitHubAPIError(
                status_code=502,
                message=f"Failed to connect to GitHub API: {str(e)}",
            )

    async def check_health(self) -> bool:
        """Check if GitHub API is reachable."""
        if not self._client:
            return False
        try:
            response = await self._client.get("/rate_limit")
            return response.status_code == 200
        except Exception:
            return False

    def _parse_gist(self, data: dict[str, Any]) -> Gist:
        """Parse raw API response into Gist model."""
        files = {}
        for filename, file_data in data.get("files", {}).items():
            files[filename] = GistFile(
                filename=file_data["filename"],
                type=file_data.get("type"),
                language=file_data.get("language"),
                raw_url=file_data["raw_url"],
                size=file_data["size"],
            )

        owner = None
        if data.get("owner"):
            owner = GistOwner(
                login=data["owner"]["login"],
                id=data["owner"]["id"],
                avatar_url=data["owner"]["avatar_url"],
                html_url=data["owner"]["html_url"],
            )

        return Gist(
            id=data["id"],
            url=data["url"],
            html_url=data["html_url"],
            description=data.get("description"),
            public=data["public"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            comments=data["comments"],
            files=files,
            owner=owner,
            truncated=data.get("truncated", False),
        )

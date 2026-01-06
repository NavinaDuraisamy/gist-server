"""Gist-related endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.config import Settings, get_settings
from app.models.schemas import Gist, GistListResponse
from app.services.cache import TTLCache, make_cache_key
from app.services.github_client import GitHubClient

router = APIRouter(tags=["Gists"])


async def get_github_client() -> GitHubClient:
    """Placeholder - overridden in main.py."""
    raise NotImplementedError


async def get_cache() -> TTLCache:
    """Placeholder - overridden in main.py."""
    raise NotImplementedError


@router.get(
    "/{username}",
    response_model=GistListResponse,
    summary="Get user's public gists",
    description="Fetches public gists for a GitHub user with pagination and caching support.",
    responses={
        200: {"description": "Successfully retrieved gists"},
        404: {"description": "GitHub user not found"},
        429: {"description": "GitHub API rate limit exceeded"},
        502: {"description": "Error communicating with GitHub API"},
    },
)
async def get_user_gists(
    username: str,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    per_page: Annotated[int, Query(ge=1, le=100, description="Items per page")] = 30,
    github_client: GitHubClient = Depends(get_github_client),
    cache: TTLCache = Depends(get_cache),
    settings: Settings = Depends(get_settings),
) -> GistListResponse:
    """
    Get public gists for a GitHub user.

    - **username**: GitHub username (case-insensitive)
    - **page**: Page number for pagination (default: 1)
    - **per_page**: Number of gists per page (default: 30, max: 100)

    Results are cached for the configured TTL (default: 5 minutes).
    """
    cache_key = make_cache_key(username, page, per_page)

    cached_gists, cache_entry = await cache.get(cache_key)
    if cached_gists is not None:
        return GistListResponse(
            username=username,
            page=page,
            per_page=per_page,
            gists=cached_gists,
            cached=True,
            cache_expires_at=cache_entry.expires_at,
        )

    gists = await github_client.get_user_gists(
        username=username,
        page=page,
        per_page=per_page,
    )

    entry = await cache.set(cache_key, gists)

    return GistListResponse(
        username=username,
        page=page,
        per_page=per_page,
        gists=gists,
        cached=False,
        cache_expires_at=entry.expires_at,
    )

"""Health check endpoints."""

from fastapi import APIRouter, Depends

from app.models.schemas import HealthResponse
from app.services.cache import TTLCache
from app.services.github_client import GitHubClient

router = APIRouter(tags=["Health"])


async def get_github_client() -> GitHubClient:
    """Placeholder - overridden in main.py."""
    raise NotImplementedError


async def get_cache() -> TTLCache:
    """Placeholder - overridden in main.py."""
    raise NotImplementedError


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check endpoint",
)
async def health_check(
    github_client: GitHubClient = Depends(get_github_client),
) -> HealthResponse:
    """
    Check the health of the service.

    Verifies:
    - Service is running
    - GitHub API is reachable
    """
    github_healthy = await github_client.check_health()

    return HealthResponse(
        status="healthy" if github_healthy else "degraded",
        version="1.0.0",
        github_api_reachable=github_healthy,
    )


@router.get(
    "/health/live",
    summary="Liveness probe",
    description="Simple liveness check for container orchestration",
)
async def liveness():
    """Simple liveness check - returns 200 if service is running."""
    return {"status": "alive"}


@router.get(
    "/health/ready",
    summary="Readiness probe",
)
async def readiness(
    github_client: GitHubClient = Depends(get_github_client),
):
    """Readiness check - verifies external dependencies."""
    github_ok = await github_client.check_health()
    if not github_ok:
        return {"status": "not_ready", "reason": "GitHub API unreachable"}
    return {"status": "ready"}

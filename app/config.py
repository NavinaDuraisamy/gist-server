"""Application configuration using Pydantic Settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="GIST_SERVER_")

    app_name: str = "GitHub Gist Server"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8080

    # GitHub API settings
    github_api_base_url: str = "https://api.github.com"
    github_api_timeout: float = 10.0
    github_token: str | None = None

    # Cache settings
    cache_ttl_seconds: int = 300
    cache_max_size: int = 1000

    # Pagination defaults
    default_page: int = 1
    default_per_page: int = 30
    max_per_page: int = 100


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()

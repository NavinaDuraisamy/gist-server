# GitHub Gist Server

A FastAPI-based HTTP server that fetches GitHub user gists with caching and pagination support.

## Features

- Fetch public gists for any GitHub user
- In-memory caching with configurable TTL (default: 5 minutes)
- Pagination support
- Health check endpoints for container orchestration
- Docker support

## Quick Start

### Local Development

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

### Docker

```bash
# Build
docker build -t gist-server .

# Run
docker run -p 8080:8080 gist-server
```

## API Endpoints

### Get User Gists

```
GET /{username}
GET /{username}?page=1&per_page=10
```

**Parameters:**
- `username` (path) - GitHub username
- `page` (query, optional) - Page number (default: 1)
- `per_page` (query, optional) - Items per page (default: 30, max: 100)

**Example:**

```bash
curl http://localhost:8080/octocat?per_page=2
```

**Response:**

```json
{
  "username": "octocat",
  "page": 1,
  "per_page": 2,
  "gists": [
    {
      "id": "6cad326836d38bd3a7ae",
      "html_url": "https://gist.github.com/octocat/6cad326836d38bd3a7ae",
      "description": "Hello world!",
      "public": true,
      "files": {...},
      ...
    }
  ],
  "cached": false,
  "cache_expires_at": "2024-01-01T12:05:00Z"
}
```

### Health Checks

```
GET /health        # Full health check
GET /health/live   # Liveness probe
GET /health/ready  # Readiness probe
```

## Configuration

Environment variables (prefix: `GIST_SERVER_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `GIST_SERVER_HOST` | `0.0.0.0` | Server host |
| `GIST_SERVER_PORT` | `8080` | Server port |
| `GIST_SERVER_CACHE_TTL_SECONDS` | `300` | Cache TTL in seconds |
| `GIST_SERVER_CACHE_MAX_SIZE` | `1000` | Max cache entries |
| `GIST_SERVER_GITHUB_TOKEN` | `None` | GitHub token (for higher rate limits) |

## Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app
```

## Project Structure

```
gist-server/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Configuration settings
│   ├── exceptions.py        # Custom exceptions
│   ├── models/
│   │   └── schemas.py       # Pydantic models
│   ├── routers/
│   │   ├── gists.py         # /{username} endpoint
│   │   └── health.py        # Health endpoints
│   └── services/
│       ├── cache.py         # TTL cache implementation
│       └── github_client.py # GitHub API client
├── tests/
│   ├── unit/                # Unit tests with mocking
│   └── functional/          # Integration tests
├── Dockerfile
├── requirements.txt
└── requirements-dev.txt
```

## License

MIT

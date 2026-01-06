# Design Document

## Overview

This document describes the architecture and design decisions for the GitHub Gist Server.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI App                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐     │
│  │   Routers   │    │   Services  │    │   Models    │     │
│  │             │    │             │    │             │     │
│  │ - gists.py  │───▶│ - cache.py  │    │ - schemas.py│     │
│  │ - health.py │    │ - github_   │    │             │     │
│  │             │    │   client.py │    │             │     │
│  └─────────────┘    └──────┬──────┘    └─────────────┘     │
│                            │                                │
└────────────────────────────┼────────────────────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   GitHub API    │
                    │  api.github.com │
                    └─────────────────┘
```

## Components

### 1. Routers

**gists.py** - Main endpoint for fetching user gists
- Route: `GET /{username}`
- Checks cache first, falls back to GitHub API
- Returns paginated response with cache metadata

**health.py** - Health check endpoints
- `/health` - Full health check with GitHub API status
- `/health/live` - Simple liveness probe
- `/health/ready` - Readiness probe checking dependencies

### 2. Services

**cache.py** - In-memory TTL cache
- Thread-safe using `asyncio.Lock`
- Automatic expiration based on TTL
- LRU-like eviction when max size reached
- Background cleanup task for expired entries

**github_client.py** - Async GitHub API client
- Uses `httpx.AsyncClient` for non-blocking HTTP
- Handles rate limiting, 404s, and timeouts
- Parses API responses into Pydantic models

### 3. Models

**schemas.py** - Pydantic models for validation
- `Gist`, `GistFile`, `GistOwner` - GitHub data structures
- `GistListResponse` - API response with pagination/cache metadata
- `HealthResponse`, `ErrorResponse` - Standard responses

## Data Flow

### Request Flow (Cache Miss)

```
1. Request: GET /octocat?page=1&per_page=10

2. Router (gists.py):
   - Generate cache key: "gists:octocat:page=1:per_page=10"
   - Check cache → Miss

3. GitHub Client:
   - GET https://api.github.com/users/octocat/gists?page=1&per_page=10
   - Parse response into Gist models

4. Cache:
   - Store gists with TTL (5 min default)

5. Response:
   {
     "username": "octocat",
     "gists": [...],
     "cached": false,
     "cache_expires_at": "..."
   }
```

### Request Flow (Cache Hit)

```
1. Request: GET /octocat?page=1&per_page=10

2. Router (gists.py):
   - Generate cache key
   - Check cache → Hit (not expired)

3. Response:
   {
     "username": "octocat",
     "gists": [...],
     "cached": true,
     "cache_expires_at": "..."
   }
```

## Design Decisions

### 1. Why FastAPI?

- **Async support**: Native async/await for non-blocking I/O
- **Automatic validation**: Pydantic integration for request/response validation
- **OpenAPI docs**: Auto-generated API documentation
- **Performance**: One of the fastest Python frameworks

### 2. Why In-Memory Cache?

- **Simplicity**: No external dependencies (Redis, Memcached)
- **Low latency**: Sub-millisecond cache lookups
- **Sufficient for scope**: Single-instance deployment

**Trade-offs**:
- Cache lost on restart
- Not shared across multiple instances
- Memory-bound

For production with multiple instances, consider Redis.

### 3. Why httpx?

- **Async native**: Built for asyncio
- **API compatible**: Similar to `requests` library
- **Connection pooling**: Efficient for repeated requests

### 4. Cache Key Design

```
gists:{username}:page={page}:per_page={per_page}
```

- Username lowercased for case-insensitive matching
- Pagination params included so different pages are cached separately

### 5. Error Handling Strategy

| Error | HTTP Status | Handling |
|-------|-------------|----------|
| User not found | 404 | `GitHubUserNotFoundError` |
| Rate limited | 429 | `GitHubRateLimitError` with reset header |
| API error | 502 | `GitHubAPIError` (bad gateway) |
| Timeout | 502 | `GitHubAPIError` |
| Invalid params | 422 | FastAPI validation error |

### 6. Why Async Lock in Cache?

Even though the cache is in-memory, we use `asyncio.Lock` because:
- Multiple concurrent requests can modify the cache
- Prevents race conditions during read-modify-write operations
- Example: Two requests evicting entries simultaneously

## Testing Strategy

### Unit Tests
- **Mocked dependencies**: GitHub API mocked with `unittest.mock`
- **Fast execution**: No network calls
- **Isolated**: Test each component independently

### Functional Tests
- **Real HTTP calls**: Hit actual GitHub API
- **End-to-end**: Test full request/response cycle
- **Cache behavior**: Verify caching works correctly

## Future Improvements

1. **Redis cache** - For multi-instance deployments
2. **Rate limit handling** - Queue requests when rate limited
3. **Metrics** - Prometheus metrics for monitoring
4. **Authentication** - Optional API key for the server itself
5. **Webhooks** - Invalidate cache on gist updates
